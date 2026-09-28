# Quality vs cost

Ten rows from a live replay of [app/eval/prompts.jsonl](../../app/eval/prompts.jsonl). Gate is the heuristic in the router, not a second model. One premium or escalated row is kept on purpose.

Regenerate with:

```bash
python3 -m app.eval.note
```

| # | Prompt | Route | Gate | Cost | Always premium |
|---|---|---|---|---:|---:|
| 1 | Summarize these notes: the launch slipped to 2026-10-03 because the billing cert expire... | cheap | pass | $0.0000 | $0.0007 |
| 2 | tl;dr the thread: design review approved the cache, rejected a custom classifier, and a... | cheap | pass | $0.0000 | $0.0005 |
| 3 | Make this shorter: The team spent three days on a gateway we do not need. LiteLLM alrea... | cheap | pass | $0.0000 | $0.0007 |
| 4 | Rewrite this email: hey team the vpn thing is still broken, can someone look before the... | cheap | pass | $0.0000 | $0.0005 |
| 5 | Draft a reply that sounds more professional: sorry I missed the review, I can send the ... | cheap | pass | $0.0000 | $0.0005 |
| 6 | Rephrase: we should not send every summary to the premium model just because the button... | cheap | pass | $0.0000 | $0.0005 |
| 7 | Say this differently: cache hits still have to pass the quality gate, or a bad answer g... | cheap | pass | $0.0000 | $0.0005 |
| 8 | Fix grammar: the router don't replace Copilot, it sit in front of the cheap work. | cheap | pass | $0.0000 | $0.0004 |
| 9 | Proofread: their is 40 to 60 prompts in the set and each one need a hand label. | cheap | pass | $0.0000 | $0.0005 |
| 10 | Write a function that computes Jaccard overlap for two token sets. | premium | skipped | $0.0003 | $0.0003 |
