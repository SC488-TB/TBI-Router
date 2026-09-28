# Lite ML signals — design note

Status: accepted and implemented. The 40-row set is still too small to fit a model.

Audience: the engineer extending the router. This is a counting exercise, not a training pipeline.

## Why not a fitted model

[app/eval/prompts.jsonl](../../app/eval/prompts.jsonl) has 40 rows. Intent counts are 2–7. That is too small to fit a classifier or a quality model. A fitted model would memorize these rows and report a fake accuracy. Both signals below are counted baselines. They do not train, and they do not call premium.

[ADR 0002](../adr/0002-rules-first-classifier.md) stays in force. Rules still decide every obvious prompt. [ADR 0004](../adr/0004-quality-gate-escalate-once.md) stays in force. The gate still does not run on premium, and it still escalates once. The decision record for this add-on is [ADR 0010](../adr/0010-counted-margin-not-a-fitted-model.md). The build steps are [plan 04](04-counted-score-implementation.md).

## Signal 1 — classifier margin

What it is: a bag-of-words score beside the keyword rules. Each intent keeps a small hand list of tokens. The score for an intent is the count of those tokens found in the prompt, divided by the number of tokens in the list. The margin is the top score minus the second score.

What it learns from: nothing fitted. The token lists are written by hand from the same phrases the rules already use. The 40-row file is a check, not training data. If a real prompt misses, add a token or a rule. Do not refit.

When it runs:

- A rule hit still wins. The score is computed and logged. It does not change the intent.
- No rule hit: if the top score is at least 0.34 and the margin is at least 0.17, take that intent and mark the method `counted`. This is the path that used to call the small model.
- Otherwise call the existing small-model fallback once. If that fails, `ambiguous`.

What it must not do:

- Must not run instead of a rule hit.
- Must not call a model to build the score.
- Must not add an intent that is not already in the catalog.
- Must not be described as measured accuracy. 40 rows cannot support that claim.

Worked example, not a measured result:

- "Summarize these notes" hits the summarize rule. Method stays `rules`. The counted score is logged and ignored.
- "Can you turn the launch writeup into something the execs can skim" hits no rule. Token overlap with summarize can clear the margin. Method is `counted`. No label-model call.
- "Thoughts?" has no rule and no margin. The existing small-model fallback runs once.

## Signal 2 — gate overlap score

What it is: the meaning check already computes token overlap and entity overlap. Today that is a pass/fail. Log the overlap as a number from 0 to 1 next to the existing reason. The pass/fail thresholds in config do not move in this change.

What it learns from: the prompt and the cheap answer on that request. No stored weights. No second model.

When it runs: only on cheap-path answers whose intent is summarize, email rewrite, rephrase, or grammar. Premium and mid skip the gate, as they do now. A direct retrieval fixture hit still checks non-empty only.

What it must not do:

- Must not call cheap, mid, or premium to judge the answer.
- Must not fail a answer that the current threshold would pass.
- Must not escalate twice.

## What the dashboard shows

One line on the answer, from fields already on the route response:

- Rule win: `rules: summarize · counted score 0.50 ignored`
- Counted win: `counted: summarize · margin 0.33 · no label-model call`
- Fallback: `small_model: ambiguous · counted margin 0.00`

The savings strip still comes from `GET /savings`. This line does not recompute it.

## Done check

- "Summarize these notes: …" never calls the label model. A test spies on the gateway and asserts the label call was not made.
- One no-rule prompt takes the `counted` method and shows the margin in the log.
- Premium answers still have no gate score.
- No train script. No new provider import.
