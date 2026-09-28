"""The only module that talks to a provider. Tests inject a fake."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from app.config import Settings
from app.schemas import GatewayResult


class GatewayError(Exception):
    def __init__(self, alias: str, message: str) -> None:
        self.alias = alias
        super().__init__(f"{alias}: {message}")


class Gateway(Protocol):
    def complete(
        self,
        alias: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float = 0.2,
    ) -> GatewayResult:
        ...


class StubGateway:
    """Offline generator. Used when no provider key is configured, and in tests.

    Deterministic. Keeps entities from the user text so the meaning check can pass.
    Set `fail_aliases` to simulate a provider outage.
    """

    def __init__(self, settings: Settings, fail_aliases: Optional[set[str]] = None) -> None:
        self._settings = settings
        self.fail_aliases = fail_aliases or set()
        self.calls: List[str] = []

    def complete(
        self,
        alias: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float = 0.2,
    ) -> GatewayResult:
        self.calls.append(alias)
        if alias in self.fail_aliases:
            raise GatewayError(alias, "provider unavailable")
        user = _last_user(messages)
        if _is_label_call(messages):
            text = _guess_label(user)
            return GatewayResult(
                text=text,
                prompt_tokens=_tokens(user),
                completion_tokens=1,
                model_id=self._model_id(alias),
                finish_reason="stop",
            )
        text = _draft(alias, user, max_tokens)
        return GatewayResult(
            text=text,
            prompt_tokens=_tokens(user),
            completion_tokens=_tokens(text),
            model_id=self._model_id(alias),
            finish_reason="length" if len(text) >= max_tokens else "stop",
        )

    def _model_id(self, alias: str) -> str:
        if alias == "premium":
            return self._settings.premium_model
        if alias == "mid" and self._settings.mid_model:
            return self._settings.mid_model
        return self._settings.cheap_model


class LiteLLMGateway:
    """Optional live provider. Imported only when TBI_GATEWAY=litellm.

    An alias whose model id still ends in ``-stub`` stays on the offline
    generator. That lets cheap/mid call Ollama while premium waits for a key.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stub = StubGateway(settings)
        try:
            import litellm  # type: ignore
        except ImportError as exc:
            raise GatewayError("gateway", "litellm is not installed") from exc
        self._litellm = litellm

    def complete(
        self,
        alias: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float = 0.2,
    ) -> GatewayResult:
        model = self._resolve(alias)
        if model.endswith("-stub"):
            return self._stub.complete(alias, messages, max_tokens, temperature)
        try:
            response = self._litellm.completion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self._settings.gateway_timeout_s,
                num_retries=1,
            )
        except Exception as exc:  # provider SDK raises many types
            raise GatewayError(alias, str(exc)) from exc
        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        text = choice.message.content or ""
        return GatewayResult(
            text=text,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            model_id=model,
            finish_reason=getattr(choice, "finish_reason", None) or "stop",
        )

    def _resolve(self, alias: str) -> str:
        if alias == "premium":
            return self._settings.premium_model
        if alias == "mid":
            if not self._settings.mid_model:
                raise GatewayError("mid", "MID_MODEL is not set")
            return self._settings.mid_model
        if alias == "embed":
            if not self._settings.embed_model:
                raise GatewayError("embed", "EMBED_MODEL is not set")
            return self._settings.embed_model
        return self._settings.cheap_model


def build_gateway(settings: Settings) -> Gateway:
    import os

    if os.environ.get("TBI_GATEWAY", "").lower() == "litellm":
        return LiteLLMGateway(settings)
    return StubGateway(settings)


def _last_user(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return messages[-1]["content"] if messages else ""


def _is_label_call(messages: List[Dict[str, str]]) -> bool:
    system = " ".join(m.get("content", "") for m in messages if m.get("role") == "system")
    return "Label the user job" in system


def _guess_label(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ("refactor", "debug", "function", "code")):
        return "code"
    if any(k in lowered for k in ("policy", "ticket", "where do i find")):
        return "lookup"
    if "email" in lowered:
        return "email_rewrite"
    if "rephrase" in lowered or "paraphrase" in lowered:
        return "rephrase"
    if "grammar" in lowered or "proofread" in lowered:
        return "grammar"
    if any(k in lowered for k in ("summar", "tl;dr", "tldr", "bullet")):
        return "summarize"
    if any(k in lowered for k in ("why", "compare", "should we")):
        return "reasoning"
    return "ambiguous"


def _draft(alias: str, user: str, max_tokens: int) -> str:
    body = user.strip()
    # Templates put the task before a blank line and the source after it.
    # A fetched document can contain its own blank line. Keep that text.
    if "\n\n" in body and not body.lower().startswith(("def ", "class ", "function ")):
        head, tail = body.split("\n\n", 1)
        if len(head) < 240:
            body = tail.strip()
    prefix = {
        "cheap": "Here is a concise version",
        "mid": "Here is a reasoned take",
        "premium": "Here is a thorough answer",
    }.get(alias, "Here is a concise version")
    text = f"{prefix}: {body}"
    if len(text) > max_tokens:
        return text[: max_tokens - 1]
    return text


def _tokens(text: str) -> int:
    return max(1, len(text.split()))
