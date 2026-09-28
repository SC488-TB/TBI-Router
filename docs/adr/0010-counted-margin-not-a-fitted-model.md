# ADR 0010 — Counted margin beside the rules, not a fitted model

- **Status:** Accepted
- **Date:** 2026-09-25

## Context

[ADR 0002](0002-rules-first-classifier.md) classifies with rules first and calls a small model only when rules are unsure. [ADR 0004](0004-quality-gate-escalate-once.md) judges cheap answers with token overlap, not another model. [ADR 0009](0009-role-list-gaps.md) rejects training a routing classifier.

The labeled set is 40 rows, 2–7 per intent. That is too small to fit a classifier. A fitted model would memorize those rows and report a fake accuracy. The engineer still wanted one lite ML signal they could read, log, and show — without a train script and without a second provider client.

## Decision

Add two counted signals beside the existing rules. Neither is trained. Neither calls a model. Neither replaces a rule hit.

### Classifier margin

Each intent keeps a short hand list of tokens in [app/classifier/counted.py](../../app/classifier/counted.py). The score is hits in the prompt divided by the length of that list. The margin is the top score minus the second score.

Order, unchanged except for the middle step:

1. A rule hit wins. Method stays `rules`. The score and margin are logged and ignored.
2. A prompt shorter than 20 characters stays `ambiguous` with no label-model call.
3. No rule hit, and top score ≥ 0.34 and margin ≥ 0.17: take that intent. Method is `counted`. Do not call the label model.
4. Otherwise call the existing small-model fallback once. Failure or an unknown label is `ambiguous`.

`POST /score` runs steps 1 and 3 on the text in the box only. It does not call the gateway and does not write a cost row. The label model still runs only on submit, and only when both the rule and the margin miss.

### Gate overlap

[app/quality/meaning.py](../../app/quality/meaning.py) already counts overlap for summarize, rephrase, email rewrite, and grammar. Log that number from 0 to 1. Do not move the pass/fail floors in config. Do not run the gate on mid or premium. Do not escalate twice.

### What the page shows

Live tiles under the box, from `POST /score`: method, intent, counted score, margin.

Answer tiles, from the route response: counted score, margin, overlap (blank when the gate did not run), and the why line. The savings strip still comes only from `GET /savings`.

## Consequences

- An obvious "summarize this" prompt never calls the label model. A test spies on the gateway and asserts that.
- A no-rule prompt that clears 0.34 / 0.17 shows method `counted` and does not call the label model.
- One token in a 5-token list is 0.20 and does not clear. Two tokens in that list is 0.40 and does. Do not lower the floors to make a demo prompt look smarter.
- Adding a token is a catalog edit, not a refit. Do not describe the margin as measured accuracy.
- A later fitted model needs a new ADR that supersedes this one and [ADR 0002](0002-rules-first-classifier.md). This record does not authorize that.

## Rejected

- Training or fine-tuning a classifier on `prompts.jsonl`.
- Calling cheap, mid, or premium to score the prompt or to judge the answer.
- Letting the counted score override a rule hit.
- A second provider client, an Ollama client, or a Grok/Cursor client. See [ADR 0009](0009-role-list-gaps.md).

## Related

- [Lite ML plan](../plans/04-counted-score-implementation.md)
- [Design note](../plans/03-lite-ml-signals.md)
- [ADR 0002](0002-rules-first-classifier.md)
- [ADR 0004](0004-quality-gate-escalate-once.md)
