"""One request through classify → route → gate → log. Routes do not call each other."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Optional
from uuid import uuid4

from app.classifier.service import Classifier
from app.config import Settings
from app.cost.logger import CostLogger
from app.cost.prices import baseline_cost_usd, cost_usd
from app.gateway import Gateway, GatewayError
from app.quality.gate import check
from app.router.service import Router
from app.routes.cache import SemanticCache
from app.routes.cheap import run_cheap
from app.routes.mid import run_mid
from app.routes.premium import run_premium
from app.routes.retrieval import Retriever, RetrievalResult
from app.schemas import CostEvent, RouteRequest, RouteResponse, Usage

_BODY_CAP = 6000
_MISS = "Document was not found."
from app.textutil import looks_like_code as detect_code
from app.tools.atlassian import fetch as fetch_atlassian
from app.tools.fixtures import read_fixture
from app.tools.router import decide as decide_tool


class AlreadyEscalated(Exception):
    def __init__(self, response: RouteResponse) -> None:
        self.response = response


class UnknownRequest(Exception):
    pass


@dataclass
class _Draft:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    alias: str
    cache_hit: bool = False
    cache_key: Optional[str] = None
    used_mid_stub: bool = False
    retrieval_fixture: bool = False


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        gateway: Gateway,
        classifier: Classifier,
        router: Router,
        cache: SemanticCache,
        retriever: Retriever,
        logger: CostLogger,
    ) -> None:
        self._settings = settings
        self._gateway = gateway
        self._classifier = classifier
        self._router = router
        self._cache = cache
        self._retriever = retriever
        self._logger = logger
        self._escalated: set[str] = set()

    def route(self, request: RouteRequest, source_override: Optional[str] = None) -> RouteResponse:
        started = perf_counter()
        request_id = f"req_{uuid4().hex[:12]}"
        tool = decide_tool(request.prompt)
        tool_notice: Optional[str] = None
        tool_line: Optional[str] = None
        model_prompt = request.prompt
        logged_source = source_override or request.source or "ui"
        if tool.ambiguous:
            # Two sources. Do not pick one, and do not call a model.
            return self._timed(
                started,
                self._named_miss(
                    request_id, request.prompt, logged_source, notice="Name one source."
                ),
            )
        elif tool.source and tool.item_id:
            item = read_fixture(tool.source, tool.item_id)
            from_fixture = item is not None
            if item is None and tool.source in ("jira", "confluence"):
                item = fetch_atlassian(tool.source, tool.item_id)
            body = (item or {}).get("body", "").strip()
            if item is None or not body:
                # Named source, no body. Do not classify the URL or call a model.
                return self._timed(started, self._named_miss(request_id, request.prompt, logged_source))
            if len(body) > _BODY_CAP:
                body = body[:_BODY_CAP].rstrip()
                tool_notice = "Document was truncated."
            model_prompt = body
            logged_source = tool.source
            kind = "fixture" if from_fixture else "live"
            tool_line = f"{tool.source.capitalize()} · {tool.item_id} · {kind}"
        classification = self._classifier.classify(
            model_prompt,
            logged_source,
            detect_code(model_prompt) if model_prompt is not request.prompt else request.looks_like_code,
        )
        # The user asked for a document. Summarize that text unless it is code.
        if model_prompt is not request.prompt:
            if detect_code(model_prompt):
                classification = classification.model_copy(
                    update={"intent": "code", "matched_rule": "fetched-code"}
                )
            else:
                classification = classification.model_copy(
                    update={"intent": "summarize", "matched_rule": "fetched-text"}
                )
        self._signal = classification.signal
        self._signal_score = classification.signal_score
        self._signal_margin = classification.signal_margin
        decision = self._router.decide(classification, request.force_premium)
        self._model_prompt = model_prompt
        try:
            draft = self._generate(decision.route, decision.cacheable, classification.intent, model_prompt)
        except GatewayError:
            if decision.route == "premium":
                raise
            # Cheap or mid provider is down. One premium hop, flagged as an escalate.
            premium = run_premium(
                self._gateway,
                model_prompt,
                self._settings.premium_max_output_tokens,
                f"{decision.route}_unavailable",
            )
            draft = _Draft(
                premium.text,
                premium.model_id,
                premium.prompt_tokens,
                premium.completion_tokens,
                premium.finish_reason,
                "premium",
            )
            return self._timed(
                started,
                self._finish(
                    request_id=request_id,
                    prompt=request.prompt,
                    source=logged_source,
                    intent=classification.intent,
                    method=classification.method,
                    first_route=decision.route,
                    draft=draft,
                    force_premium=request.force_premium,
                    provider_failover=True,
                    tool_notice=tool_notice,
                    tool_line=tool_line,
                ),
            )
        return self._timed(
            started,
            self._finish(
                request_id=request_id,
                prompt=request.prompt,
                source=logged_source,
                intent=classification.intent,
                method=classification.method,
                first_route=decision.route,
                draft=draft,
                force_premium=request.force_premium,
                tool_notice=tool_notice,
                tool_line=tool_line,
            ),
        )

    def _timed(self, started: float, response: RouteResponse) -> RouteResponse:
        return response.model_copy(update={"latency_ms": int((perf_counter() - started) * 1000)})

    def escalate(self, request_id: str) -> RouteResponse:
        started = perf_counter()
        existing = self._logger.get(request_id)
        if existing is None:
            raise UnknownRequest(request_id)
        if existing.escalated or request_id in self._escalated:
            self._escalated.add(request_id)
            raise AlreadyEscalated(self._to_response(existing, can_escalate=False))
        self._escalated.add(request_id)
        try:
            premium = run_premium(
                self._gateway,
                existing.prompt,
                self._settings.premium_max_output_tokens,
                "user_override",
            )
        except GatewayError as exc:
            self._escalated.discard(request_id)
            raise exc
        draft = _Draft(
            text=premium.text,
            model=premium.model_id,
            prompt_tokens=premium.prompt_tokens,
            completion_tokens=premium.completion_tokens,
            finish_reason=premium.finish_reason,
            alias="premium",
            cache_hit=existing.cache_hit,
        )
        return self._timed(started, self._log_escalation(existing, draft, "user_override"))

    def _generate(self, route: str, cacheable: bool, intent: str, prompt: str) -> _Draft:
        if cacheable:
            hit = self._cache.lookup(intent, prompt)
            if hit is not None:
                return _Draft(
                    text=hit.answer,
                    model="cache",
                    prompt_tokens=hit.prompt_tokens,
                    completion_tokens=hit.completion_tokens,
                    finish_reason="stop",
                    alias="cheap",
                    cache_hit=True,
                    cache_key=hit.cache_key,
                )
        if route == "premium":
            result = run_premium(self._gateway, prompt, self._settings.premium_max_output_tokens, "route")
            return _Draft(result.text, result.model_id, result.prompt_tokens, result.completion_tokens, result.finish_reason, "premium")
        if route == "retrieval":
            found = self._run_retrieval(prompt)
            return _Draft(
                found.result.text,
                found.result.model_id,
                found.result.prompt_tokens,
                found.result.completion_tokens,
                found.result.finish_reason,
                "cheap",
                retrieval_fixture=not found.model_called,
            )
        if route == "mid":
            mid = run_mid(self._gateway, self._settings, prompt, self._settings.cheap_max_output_tokens)
            return _Draft(
                mid.result.text,
                mid.result.model_id,
                mid.result.prompt_tokens,
                mid.result.completion_tokens,
                mid.result.finish_reason,
                mid.alias,
                used_mid_stub=mid.used_stub,
            )
        result = run_cheap(self._gateway, intent, prompt, self._settings.cheap_max_output_tokens)
        return _Draft(
            result.text,
            result.model_id,
            result.prompt_tokens,
            result.completion_tokens,
            result.finish_reason,
            "cheap",
        )

    def _run_retrieval(self, prompt: str) -> RetrievalResult:
        """Fixture hits never touch the model. A cheap-model miss fails over to premium."""
        hit = self._retriever.lookup(prompt)
        if hit is not None:
            from app.schemas import GatewayResult

            text = f"{hit['title']}: {hit['body']}"
            return RetrievalResult(
                result=GatewayResult(
                    text=text,
                    prompt_tokens=0,
                    completion_tokens=0,
                    model_id="fixture",
                    finish_reason="stop",
                ),
                model_called=False,
                retrieval_miss=False,
            )
        if "cheap" in getattr(self._gateway, "fail_aliases", set()):
            premium = run_premium(
                self._gateway,
                prompt,
                self._settings.premium_max_output_tokens,
                "retrieval_miss_and_cheap_unavailable",
            )
            return RetrievalResult(result=premium, model_called=True, retrieval_miss=True)
        return self._retriever.run(self._gateway, prompt, self._settings.cheap_max_output_tokens)

    def _finish(
        self,
        request_id: str,
        prompt: str,
        source: str,
        intent: str,
        method: str,
        first_route: str,
        draft: _Draft,
        force_premium: bool,
        provider_failover: bool = False,
        tool_notice: Optional[str] = None,
        tool_line: Optional[str] = None,
    ) -> RouteResponse:
        gate_applies = self._gate_applies(first_route, draft) and not provider_failover
        quality_passed: Optional[bool] = None
        quality_reason: Optional[str] = None
        signal, signal_score, signal_margin, overlap = self._signal_line(None)
        escalated = provider_failover
        escalate_reason: Optional[str] = f"{first_route}_unavailable" if provider_failover else None
        notice: Optional[str] = tool_notice
        if provider_failover:
            self._escalated.add(request_id)

        if gate_applies:
            gate = check(
                intent,
                getattr(self, "_model_prompt", prompt),
                draft.text,
                draft.finish_reason,
                self._settings.cheap_max_output_tokens,
                self._settings,
                check_meaning=not draft.retrieval_fixture,
            )
            quality_passed = gate.passed
            quality_reason = gate.reason
            signal, signal_score, signal_margin, overlap = self._signal_line(gate.score)
            if not gate.passed:
                if draft.cache_key:
                    self._cache.delete(draft.cache_key)
                self._escalated.add(request_id)
                try:
                    premium = run_premium(
                        self._gateway,
                        prompt,
                        self._settings.premium_max_output_tokens,
                        f"quality_fail:{gate.reason}",
                    )
                except GatewayError:
                    notice = "Premium escalate failed. Showing the cheap answer that failed quality."
                    escalated = False
                    self._escalated.discard(request_id)
                else:
                    cheap_cost = 0.0 if draft.cache_hit else cost_usd(
                        self._settings, draft.alias, draft.prompt_tokens, draft.completion_tokens
                    )
                    # Keep the premium hop's own token counts. The cheap hop is
                    # billed separately via extra_cost so prompt tokens are not priced twice.
                    draft = _Draft(
                        text=premium.text,
                        model=premium.model_id,
                        prompt_tokens=premium.prompt_tokens,
                        completion_tokens=premium.completion_tokens,
                        finish_reason=premium.finish_reason,
                        alias="premium",
                        cache_hit=False,
                    )
                    escalated = True
                    escalate_reason = f"quality_fail:{quality_reason}"
                    return self._persist(
                        request_id, prompt, source, intent, method, first_route, draft,
                        escalated, escalate_reason, quality_passed, quality_reason,
                        force_premium, notice, extra_cost=cheap_cost,
                        signal=signal, signal_score=signal_score,
                        signal_margin=signal_margin, overlap_score=overlap,
                        tool_line=tool_line,
                    )

        if (
            not draft.cache_hit
            and first_route == "cheap"
            and quality_passed is not False
            and intent in {"summarize", "email_rewrite", "rephrase", "grammar"}
        ):
            self._cache.store(
                intent, prompt, draft.text, draft.model, draft.prompt_tokens, draft.completion_tokens
            )

        return self._persist(
            request_id, prompt, source, intent, method, first_route, draft,
            escalated, escalate_reason, quality_passed, quality_reason,
            force_premium, notice, extra_cost=0.0,
            signal=signal, signal_score=signal_score,
            signal_margin=signal_margin, overlap_score=overlap,
            tool_line=tool_line,
        )

    def _named_miss(
        self,
        request_id: str,
        prompt: str,
        source: str,
        notice: str = _MISS,
    ) -> RouteResponse:
        """Named source, no body. Do not classify the URL or call a model."""
        event = CostEvent(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            prompt=prompt,
            intent="lookup",
            classifier_method="rules",
            route="retrieval",
            first_route="retrieval",
            route_label="retrieval",
            model="none",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            first_cost_usd=0.0,
            cache_hit=False,
            baseline_cost_usd=0.0,
            escalated=False,
            escalate_reason=None,
            saved_usd=0.0,
            answer=notice,
        )
        logger_ok = True
        try:
            self._logger.write(event)
        except Exception:
            logger_ok = False
        return RouteResponse(
            request_id=request_id,
            intent="lookup",
            classifier_method="rules",
            route="retrieval",
            route_label="retrieval",
            model="none",
            answer=notice,
            cache_hit=False,
            escalated=False,
            escalate_reason=None,
            can_escalate=False,
            usage=Usage(),
            cost_usd=0.0,
            baseline_cost_usd=0.0,
            saved_usd=0.0,
            quality_passed=None,
            logger_ok=logger_ok,
            notice=notice,
            tool_line=None,
        )

    def _persist(
        self,
        request_id: str,
        prompt: str,
        source: str,
        intent: str,
        method: str,
        first_route: str,
        draft: _Draft,
        escalated: bool,
        escalate_reason: Optional[str],
        quality_passed: Optional[bool],
        quality_reason: Optional[str],
        force_premium: bool,
        notice: Optional[str],
        extra_cost: float,
        signal: Optional[str] = None,
        signal_score: Optional[float] = None,
        signal_margin: Optional[float] = None,
        overlap_score: Optional[float] = None,
        tool_line: Optional[str] = None,
    ) -> RouteResponse:
        spent = extra_cost
        if not draft.cache_hit or escalated:
            alias = "premium" if escalated or draft.alias == "premium" else draft.alias
            hop = cost_usd(self._settings, alias, draft.prompt_tokens, draft.completion_tokens)
            spent = extra_cost + hop if escalated else hop
        baseline = baseline_cost_usd(self._settings, max(draft.prompt_tokens, 1), draft.completion_tokens)
        saved = baseline - spent
        final_route = "premium" if escalated or first_route == "premium" else (
            "cache" if draft.cache_hit else first_route
        )
        if draft.used_mid_stub and not escalated:
            final_route = "cheap"
        label = self._label(final_route, draft, escalated, first_route)
        event = CostEvent(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            prompt=prompt,
            intent=intent,  # type: ignore[arg-type]
            classifier_method=method,  # type: ignore[arg-type]
            route=final_route,  # type: ignore[arg-type]
            first_route=first_route,  # type: ignore[arg-type]
            route_label=label,
            model=draft.model,
            prompt_tokens=draft.prompt_tokens,
            completion_tokens=draft.completion_tokens,
            cost_usd=round(spent, 6),
            first_cost_usd=round(extra_cost if escalated else spent, 6),
            cache_hit=draft.cache_hit and not escalated,
            baseline_cost_usd=round(baseline, 6),
            escalated=escalated,
            escalate_reason=escalate_reason,
            saved_usd=round(saved, 6),
            answer=draft.text,
        )
        logger_ok = True
        try:
            self._logger.write(event)
        except Exception:
            logger_ok = False
            log_notice = "This call was not logged — savings total may be short."
            notice = f"{notice} {log_notice}" if notice else log_notice
        can_escalate = (
            not escalated
            and not force_premium
            and final_route != "premium"
            and request_id not in self._escalated
        )
        return RouteResponse(
            request_id=request_id,
            intent=intent,  # type: ignore[arg-type]
            classifier_method=method,  # type: ignore[arg-type]
            route=final_route,  # type: ignore[arg-type]
            route_label=label,
            model=draft.model,
            answer=draft.text,
            cache_hit=event.cache_hit,
            escalated=escalated,
            escalate_reason=escalate_reason,
            can_escalate=can_escalate,
            usage=Usage(prompt_tokens=draft.prompt_tokens, completion_tokens=draft.completion_tokens),
            cost_usd=event.cost_usd,
            baseline_cost_usd=event.baseline_cost_usd,
            saved_usd=event.saved_usd,
            quality_passed=quality_passed,
            quality_reason=quality_reason,
            signal=signal,
            signal_score=signal_score,
            signal_margin=signal_margin,
            overlap_score=overlap_score,
            logger_ok=logger_ok,
            notice=notice,
            tool_line=tool_line,
        )

    def _log_escalation(self, existing: CostEvent, draft: _Draft, reason: str) -> RouteResponse:
        premium_cost = cost_usd(self._settings, "premium", draft.prompt_tokens, draft.completion_tokens)
        spent = existing.first_cost_usd + premium_cost
        # Baseline is the premium hop alone. The cheap hop is already in `spent`.
        baseline = baseline_cost_usd(self._settings, draft.prompt_tokens, draft.completion_tokens)
        saved = baseline - spent
        label = f"{existing.first_route} → premium"
        event = existing.model_copy(
            update={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "route": "premium",
                "route_label": label,
                "model": draft.model,
                "prompt_tokens": draft.prompt_tokens,
                "completion_tokens": draft.completion_tokens,
                "cost_usd": round(spent, 6),
                "baseline_cost_usd": round(baseline, 6),
                "escalated": True,
                "escalate_reason": reason,
                "saved_usd": round(saved, 6),
                "answer": draft.text,
                "cache_hit": False,
            }
        )
        logger_ok = True
        notice = None
        try:
            self._logger.write(event)
        except Exception:
            logger_ok = False
            notice = "This call was not logged — savings total may be short."
        return self._to_response(event, can_escalate=False, logger_ok=logger_ok, notice=notice)

    def _to_response(
        self,
        event: CostEvent,
        can_escalate: bool,
        logger_ok: bool = True,
        notice: Optional[str] = None,
    ) -> RouteResponse:
        return RouteResponse(
            request_id=event.request_id,
            intent=event.intent,
            classifier_method=event.classifier_method,
            route=event.route,
            route_label=event.route_label,
            model=event.model,
            answer=event.answer,
            cache_hit=event.cache_hit,
            escalated=event.escalated,
            escalate_reason=event.escalate_reason,
            can_escalate=can_escalate,
            usage=Usage(prompt_tokens=event.prompt_tokens, completion_tokens=event.completion_tokens),
            cost_usd=event.cost_usd,
            baseline_cost_usd=event.baseline_cost_usd,
            saved_usd=event.saved_usd,
            logger_ok=logger_ok,
            notice=notice,
        )

    def _signal_line(self, gate_score: Optional[float]):
        """Dashboard line. Classifier score is logged; gate overlap is appended."""
        text = getattr(self, "_signal", None)
        score = getattr(self, "_signal_score", None)
        margin = getattr(self, "_signal_margin", None)
        if gate_score is None:
            return text, score, margin, None
        suffix = f"overlap {gate_score:.2f}"
        text = f"{text} · {suffix}" if text else suffix
        return text, score, margin, gate_score

    def _gate_applies(self, route: str, draft: _Draft) -> bool:
        if draft.alias == "premium" and not draft.used_mid_stub:
            return False
        if route == "premium":
            return False
        if route == "mid" and not draft.used_mid_stub:
            return False
        return True

    def _label(self, route: str, draft: _Draft, escalated: bool, first_route: str) -> str:
        if escalated:
            start = "cache" if draft.cache_hit else first_route
            return f"{start} → premium"
        if draft.used_mid_stub:
            return "low-cost (mid unavailable)"
        if route == "cache":
            return "cache"
        return route
