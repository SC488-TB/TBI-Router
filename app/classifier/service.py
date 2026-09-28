"""Rules first. Small model only when unsure. Never picks a vendor model id."""

from __future__ import annotations

from typing import Optional

from app.classifier.counted import margin as counted_margin
from app.classifier.counted import confident, score_intents
from app.classifier.fallback import classify_with_model
from app.classifier.rules import match_rules
from app.config import Settings
from app.gateway import Gateway
from app.schemas import Classification, PromptScore
from app.textutil import looks_like_code as detect_code


class Classifier:
    def __init__(self, settings: Settings, gateway: Gateway) -> None:
        self._settings = settings
        self._gateway = gateway

    def classify(
        self,
        prompt: str,
        source: Optional[str],
        looks_like_code: Optional[bool],
    ) -> Classification:
        length = len(prompt)
        detected = looks_like_code if looks_like_code is not None else detect_code(prompt)
        hit = match_rules(prompt, detected, length)
        # Always count. A rule hit ignores the score but the dashboard shows it.
        top, score, gap = counted_margin(prompt)
        if hit is not None:
            rule, intent = hit
            return Classification(
                intent=intent,  # type: ignore[arg-type]
                confidence=0.9,
                method="rules",
                matched_rule=rule,
                signal=f"rules: {intent} · counted score {score:.2f} ignored",
                signal_score=round(score, 2),
                signal_margin=round(gap, 2),
            )
        if length < 20:
            return Classification(
                intent="ambiguous",
                confidence=0.4,
                method="rules",
                matched_rule="too-short",
                signal="rules: too short · no label-model call",
                signal_score=round(score, 2),
                signal_margin=round(gap, 2),
            )
        # No rule. A clear counted margin skips the label model.
        picked = confident(prompt)
        if picked is not None:
            intent, picked_score, picked_gap = picked
            return Classification(
                intent=intent,  # type: ignore[arg-type]
                confidence=0.6,
                method="counted",
                matched_rule=None,
                signal=f"counted: {intent} · margin {picked_gap:.2f} · no label-model call",
                signal_score=round(picked_score, 2),
                signal_margin=round(picked_gap, 2),
            )
        excerpt = prompt[: self._settings.classifier_max_chars]
        context = f"source={source or 'unknown'} looks_like_code={bool(detected)} length={length}"
        label = classify_with_model(self._gateway, excerpt, context)
        if label is None or label == "ambiguous":
            return Classification(
                intent="ambiguous",
                confidence=0.3,
                method="small_model",
                matched_rule=None,
                signal=f"small_model: ambiguous · counted margin {gap:.2f}",
                signal_score=round(score, 2),
                signal_margin=round(gap, 2),
            )
        return Classification(
            intent=label,
            confidence=0.7,
            method="small_model",
            matched_rule=None,
            signal=f"small_model: {label} · counted margin {gap:.2f}",
            signal_score=round(score, 2),
            signal_margin=round(gap, 2),
        )

    def score_prompt(self, prompt: str) -> PromptScore:
        """Score the box text. Rules and the counted margin only. No model."""
        text = (prompt or "").strip()
        if len(text) < 8:
            return PromptScore(
                method="rules",
                signal="keep typing",
                signal_score=0,
                margin=0,
            )
        ranked = [
            {"intent": intent, "score": round(value, 2)}
            for intent, value in score_intents(text)
            if value > 0
        ][:3]
        top, score, gap = counted_margin(text)
        hit = match_rules(text, detect_code(text), len(text))
        if hit is not None:
            _rule, intent = hit
            return PromptScore(
                method="rules",
                intent=intent,  # type: ignore[arg-type]
                signal=f"rules would win: {intent} · counted {score:.2f} ignored",
                signal_score=round(score, 2),
                margin=round(gap, 2),
                ranked=ranked,
            )
        picked = confident(text)
        if picked is not None:
            intent, picked_score, picked_gap = picked
            return PromptScore(
                method="counted",
                intent=intent,  # type: ignore[arg-type]
                signal=f"counted would pick: {intent} · margin {picked_gap:.2f}",
                signal_score=round(picked_score, 2),
                margin=round(picked_gap, 2),
                ranked=ranked,
            )
        return PromptScore(
            method="unsure",
            intent="ambiguous",
            signal=f"unsure · counted margin {gap:.2f} · label model only on submit",
            signal_score=round(score, 2),
            margin=round(gap, 2),
            ranked=ranked,
        )
