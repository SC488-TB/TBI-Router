# TBI Router — Solution Write-up

A one-week hackathon proposal to cut AI spend without taking away the tools people actually use.

---

## The problem

AI cost is going up for a simple reason: almost every request is treated as a hard problem.

People use the same expensive models for very different jobs. Writing or debugging code is one job. Summarizing a ticket, rephrasing a paragraph, polishing an email, or turning notes into bullets is another. The second group is high volume and low difficulty. It does not need a frontier coding model. When it still goes there, we pay coding prices for language cleanup.

The result is familiar. Usage grows. Code generation grows. So do summaries, rewrites, and email drafts. The bill grows faster than the value, because cheap work and expensive work share the same path.

The TBI router exists to split those jobs. It does not try to make people use AI less. It tries to send each request to the cheapest path that is still good enough.

---

## What we are actually solving

We are not building a new chatbot. We are not replacing Copilot. We are not asking the company to change how it works in a week.

We are building a decision layer in front of the models.

Every incoming request gets classified, then routed:

- Cheap language work goes to a small model, a cache, or a template.
- Lookups go to search or existing systems first, and only call a model if needed.
- Real reasoning goes to a mid-tier model.
- Hard generation — code, refactors, multi-file edits, architecture — stays on the premium model.

If the cheap path fails a quality check, or the user asks for a better answer, the request is sent up once. That escalate path matters. Without it, people will not trust the router, and they will go around it.

The point of the week is not a production platform. The point is proof: on a set of real prompts, we can show what we would have spent on the premium model, what we spent after routing, and that the cheap answers were still usable.

---

## The idea in one sentence

Classify the job, route it to the cheapest capable model, cache the repeats, measure the savings, and escalate only when quality is not good enough.

---

## How the solution works

A request arrives with a prompt and, when we have it, a little context: where it came from, whether it looks like code, how long it is.

A classifier decides what kind of job it is. For the hackathon this can be simple. Start with rules and keywords for the obvious cases — “summarize,” “rephrase,” “rewrite this email,” “make this shorter,” “write a function,” “refactor,” “debug.” When the rules are unsure, ask a small model to label the intent. Do not train a custom model this week.

The router then picks a path.

Summaries, rephrasing, grammar, and email drafts go to a small, cheap model. If we have already answered a very similar request, we return the cached answer and spend almost nothing. Ticket or policy lookups should try retrieval first. Code and hard generation stay on the expensive model. Ambiguous work can go to a mid model, or to the cheap model with an easy retry.

Before we show a cheap answer, we run a light quality gate. The answer should not be empty, truncated, or a refusal. For summaries and emails, it should still mean roughly the same thing as the original. If it fails, we escalate once to the stronger model. The user should also be able to click “try the smart model” without fighting the system.

Every call is logged: intent, model used, tokens, cost, cache hit or miss, and what the same request would have cost on the premium model. That log is the demo. The savings number is not a guess. It is the difference between “always premium” and “what the router actually did.”

---

## Why this reduces cost

Cost falls when three things happen at once.

First, most non-code traffic never touches a premium model. In a lot of real usage, that is the majority of requests: summarize this, rewrite that, make it sound better, draft the email.

Second, near-duplicate work is answered from cache. The same Jira ticket gets summarized more than once. The same paragraph gets rephrased in Slack. Those should not be full model calls every time.

Third, premium models are reserved for work that actually needs them. Code generation can stay expensive. The waste is using that same path for language chores.

A useful target for the demo is that most non-code traffic is routed cheap, and the replay set shows a large cost drop — often in the 40 to 70 percent range if summaries and emails dominate — without making the cheap answers look sloppy.

---

## What we will build in one week

The MVP is small on purpose: one service, one simple UI, one eval set.

The service has a single route endpoint. You send a prompt. It returns the intent, the model it chose, the answer, the actual cost, the premium baseline cost, and whether it was a cache hit.

Two models are enough: one cheap and one premium. A third mid-tier model is optional. Caching is only required for the cheap intents, where repeats are common. The UI is a paste box. A person pastes a prompt and sees the route, the answer, the dollars, and a side-by-side comparison against the premium model.

The eval set is the heart of the week. Collect 40 to 60 real prompts from actual work: code, summaries, emails, rephrasing, a few lookups, a few messy ones. Label them by hand. That set is what we replay on Friday. If the router looks good on made-up examples and bad on real ones, it is not ready to show.

A practical stack for the week is Python, FastAPI, and a model gateway such as LiteLLM or OpenRouter, plus a single Streamlit or HTML page. Keep the classifier as rules plus one cheap classification call.

---

## Day-by-day plan

**Day 1.** Collect and label the prompt set. Agree on a short list of intents. Write down what “good enough” means for a summary and an email rewrite. This day is research, not engineering, and skipping it is how the demo falls apart.

**Day 2.** Build the classifier. Rules first, small model as fallback. Measure it against the labeled set. If it cannot get the obvious cases right, do not add features. Fix the labels and the rules.

**Day 3.** Build the router. Map each intent to a model. Wire cheap, premium, and the escalate path. Make the API return cost and baseline cost on every call.

**Day 4.** Add semantic cache for summaries and rewrites. Add the cost logger. Replay the prompt set against “always premium” versus “routed.”

**Day 5.** Build the tiny UI. Show intent, model, tokens, dollars, and the answer. Prepare ten side-by-side examples: five cheap tasks that look fine, a few code tasks that stayed premium, and one miss that escalated.

**Day 6.** Evaluate. Look at classification accuracy, share of traffic that stayed cheap, dollars saved, and the embarrassing misses. Fix the misses that a judge would notice. Do not chase a perfect framework.

**Day 7.** Pitch. State the problem in one minute. Show the live router. Show the savings number. Show one failure and the escalate path. End with what we would productionize if this were real.

Out of scope this week: replacing GitHub Copilot, company-wide SSO, fine-tuning, a full multi-team gateway, and treating security hardening as the product. Those are the next chapter, not the demo.

---

## What “done” looks like on Friday

A judge should be able to paste a real email and see it go to a cheap model, with a usable rewrite and a lower cost. They should paste a coding task and see it stay on the premium model. They should see a dashboard or table that says: this set would have cost X on the expensive model, it cost Y with the router, and here is the quality comparison.

They should also see that we are honest. One misclassified prompt, one escalate, and a sentence about what we would not ship yet. That makes the project look like a system, not a slide.

If we hit roughly 90 percent intent accuracy on the labeled set, send most non-code traffic away from premium models, and still produce answers people would actually send, the week succeeded.

---

## What we would do after the hackathon

If the idea holds, the router should sit in front of the real tools as a proxy, not as another chat app people have to remember.

Keep Copilot in the IDE for code. Put Slack, email, and docs traffic through the router first. That is where the cheap work lives. Add per-team budgets and a reason when someone forces the premium model. Cache common patterns across the org. Tighten quality gates with a small human review sample, not with another giant model on every call.

Shipped after this write-up, and not a proxy: a prompt that names one Jira key, one Confluence page link, or one Notion link loads that fixture, then the existing model router classifies the document. See [ADR 0012](../adr/0012-tool-router-names-the-source.md) and the [tool-router diagram](../architecture/tool-router-diagram.html). Live calls are still later. The paste box still works if those clients are unset.

The production version is a policy and a measurement system. The hackathon version is the proof that the policy is worth writing.

---

## Why this is a good hackathon bet

It is understandable in one minute. It maps to a pain every team already feels. It can be built in a week without waiting on platform access we do not have. And it produces a number — dollars not spent — instead of a vague claim that “we used AI better.”

The TBI router is not a cheaper model. It is a way to stop paying for the expensive one when the job never needed it.
