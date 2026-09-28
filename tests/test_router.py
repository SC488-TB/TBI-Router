from app.gateway import GatewayError, StubGateway
from app.quality.gate import check
from app.schemas import RouteRequest


def test_summary_goes_cheap_and_code_stays_premium(client):
    cheap = client.post("/route", json={"prompt": "Summarize the Q3 launch notes for the team."})
    assert cheap.status_code == 200
    body = cheap.json()
    assert body["intent"] == "summarize"
    assert body["route"] == "cheap"
    assert body["can_escalate"] is True
    assert body["cost_usd"] < body["baseline_cost_usd"]

    code = client.post("/route", json={"prompt": "Refactor this function to take a settings object."})
    assert code.status_code == 200
    assert code.json()["intent"] == "code"
    assert code.json()["route"] == "premium"
    assert code.json()["can_escalate"] is False


def test_lookup_uses_fixture_and_skips_model(client, gateway):
    before = len(gateway.calls)
    res = client.post("/route", json={"prompt": "What's the status of TICKET-123?"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "lookup"
    assert body["route"] == "retrieval"
    assert "TICKET-123" in body["answer"]
    assert gateway.calls[before:] == []


def test_cache_hit_costs_zero(client):
    prompt = "Summarize these notes: billing cert expired, 42 minutes of errors, owner Priya."
    first = client.post("/route", json={"prompt": prompt}).json()
    assert first["cache_hit"] is False
    second = client.post("/route", json={"prompt": "please " + prompt}).json()
    assert second["cache_hit"] is True
    assert second["route"] == "cache"
    assert second["cost_usd"] == 0
    assert second["baseline_cost_usd"] > 0


def test_quality_fail_escalates_once(client, settings):
    class EmptyCheap(StubGateway):
        def complete(self, alias, messages, max_tokens, temperature=0.2):
            if alias == "cheap" and not any("Label the user job" in m.get("content", "") for m in messages):
                result = super().complete(alias, messages, max_tokens, temperature)
                result.text = ""
                return result
            return super().complete(alias, messages, max_tokens, temperature)

    from app.db import connect
    from app.factory import build_orchestrator
    from app.main import create_app

    conn = connect(":memory:")
    gateway = EmptyCheap(settings)
    app = create_app(build_orchestrator(settings=settings, gateway=gateway, conn=conn))
    local = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(app)
    res = local.post("/route", json={"prompt": "Summarize the launch notes for Friday."})
    body = res.json()
    assert body["escalated"] is True
    assert body["escalate_reason"].startswith("quality_fail")
    assert body["route"] == "premium"
    assert body["can_escalate"] is False
    again = local.post(f"/route/{body['request_id']}/escalate")
    assert again.status_code == 409


def test_user_override_joins_premium(client):
    first = client.post("/route", json={"prompt": "Rephrase: do not cache code answers."}).json()
    assert first["can_escalate"] is True
    up = client.post(f"/route/{first['request_id']}/escalate")
    assert up.status_code == 200
    assert up.json()["escalated"] is True
    assert up.json()["escalate_reason"] == "user_override"
    assert up.json()["can_escalate"] is False
    second = client.post(f"/route/{first['request_id']}/escalate")
    assert second.status_code == 409


def test_bad_log_text_does_not_break_savings(client, orchestrator):
    orchestrator._logger._conn.execute(
        "INSERT INTO cost_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "req_bad",
            "2026-09-25T00:00:00+00:00",
            "ui",
            "bad row",
            "code",
            "rules",
            "premium",
            "premium",
            "premium",
            "premium-stub",
            1,
            1,
            0.1,
            0.1,
            0,
            0.2,
            0,
            None,
            0.1,
            b"\xffe",
        ),
    )
    orchestrator._logger._conn.commit()
    savings = client.get("/savings")
    logs = client.get("/logs")
    assert savings.status_code == 200
    assert logs.status_code == 200
    assert savings.json()["requests"] >= 1


def test_savings_matches_log(client):
    client.post("/route", json={"prompt": "Summarize the retro notes."})
    client.post("/route", json={"prompt": "Write a function that adds two ints."})
    savings = client.get("/savings").json()
    logs = client.get("/logs").json()
    assert savings["requests"] == len(logs) == 2
    assert savings["always_premium_usd"] == round(sum(r["baseline_cost_usd"] for r in logs), 6)
    assert savings["routed_usd"] == round(sum(r["cost_usd"] for r in logs), 6)


def test_gate_rejects_refusal_and_keeps_entities(settings):
    refusal = check("summarize", "notes about Priya", "I'm sorry, but I can't help with that.", "stop", 512, settings, True)
    assert refusal.passed is False
    assert refusal.reason == "refusal"
    dropped = check(
        "email_rewrite",
        "Send receipts for TICKET-456 by 2026-08-02",
        "Please send the receipts when you can.",
        "stop",
        512,
        settings,
        True,
    )
    assert dropped.passed is False
    assert dropped.reason == "meaning"


def test_quality_note_keeps_a_premium_or_escalated_row(orchestrator):
    from app.eval.replay import quality_note

    rows = quality_note(orchestrator)
    assert len(rows) == 10
    assert any(row["route"] == "premium" or row["gate"] == "fail" for row in rows)
    assert all({"prompt", "route", "gate", "cost_usd", "baseline_cost_usd"} <= set(row) for row in rows)


def test_eval_accuracy_and_replay(orchestrator):
    from app.eval.replay import accuracy, replay_set

    report = accuracy(orchestrator._classifier.classify)
    assert report["accuracy"] >= 0.9, report["misses"]
    savings = replay_set(orchestrator)
    assert savings.requests == 40
    assert savings.always_premium_usd > savings.routed_usd


def test_unknown_escalate_is_404(client):
    assert client.post("/route/req_missing/escalate").status_code == 404


def test_cheap_gateway_failure_escalates(settings):
    from fastapi.testclient import TestClient

    from app.db import connect
    from app.factory import build_orchestrator
    from app.main import create_app

    conn = connect(":memory:")
    gateway = StubGateway(settings, fail_aliases={"cheap"})
    local = TestClient(create_app(build_orchestrator(settings=settings, gateway=gateway, conn=conn)))
    res = local.post("/route", json={"prompt": "Summarize the retro notes for the team standup."})
    # Rules classify without a model call; generation then fails over.
    assert res.status_code == 200
    assert res.json()["route"] == "premium"
    assert res.json()["escalated"] is True


def test_score_endpoint_does_not_call_a_model(settings):
    from fastapi.testclient import TestClient

    from app.db import connect
    from app.factory import build_orchestrator
    from app.main import create_app

    class Spy(StubGateway):
        def complete(self, alias, messages, max_tokens, temperature=0.2):
            raise AssertionError("scoring a prompt must not call a model")

    gateway = Spy(settings)
    local = TestClient(create_app(build_orchestrator(settings=settings, gateway=gateway, conn=connect(":memory:"))))
    res = local.post("/score", json={"prompt": "Turn the launch writeup into a shorter skim for the execs."})
    body = res.json()
    assert res.status_code == 200
    assert body["method"] == "counted"
    assert body["intent"] == "summarize"
    assert body["signal_score"] >= 0.34
    assert any(row["intent"] == "summarize" for row in body["ranked"])


def test_obvious_summary_never_calls_label_model(settings):
    """A rule hit must not spend a label call. The counted score is logged only."""
    from fastapi.testclient import TestClient

    from app.db import connect
    from app.factory import build_orchestrator
    from app.main import create_app

    class Spy(StubGateway):
        def __init__(self, settings):
            super().__init__(settings)
            self.label_calls = 0

        def complete(self, alias, messages, max_tokens, temperature=0.2):
            if any("Label the user job" in m.get("content", "") for m in messages):
                self.label_calls += 1
            return super().complete(alias, messages, max_tokens, temperature)

    gateway = Spy(settings)
    local = TestClient(create_app(build_orchestrator(settings=settings, gateway=gateway, conn=connect(":memory:"))))
    res = local.post("/route", json={"prompt": "Summarize these notes: the launch slipped and Priya owns the dry run."})
    body = res.json()
    assert body["classifier_method"] == "rules"
    assert body["intent"] == "summarize"
    assert "counted score" in body["signal"]
    assert "ignored" in body["signal"]
    assert gateway.label_calls == 0


def test_unsure_prompt_uses_counted_margin_without_label_call(settings):
    from fastapi.testclient import TestClient

    from app.db import connect
    from app.factory import build_orchestrator
    from app.main import create_app

    class Spy(StubGateway):
        def __init__(self, settings):
            super().__init__(settings)
            self.label_calls = 0

        def complete(self, alias, messages, max_tokens, temperature=0.2):
            if any("Label the user job" in m.get("content", "") for m in messages):
                self.label_calls += 1
            return super().complete(alias, messages, max_tokens, temperature)

    gateway = Spy(settings)
    local = TestClient(create_app(build_orchestrator(settings=settings, gateway=gateway, conn=connect(":memory:"))))
    # No rule phrase ("summarize", "tl;dr"). Counted tokens still clear the margin.
    prompt = "Turn the launch writeup into a shorter skim for the execs by Friday."
    res = local.post("/route", json={"prompt": prompt})
    body = res.json()
    assert body["classifier_method"] == "counted"
    assert body["intent"] == "summarize"
    assert "no label-model call" in body["signal"]
    assert gateway.label_calls == 0


def test_named_source_summarizes_fixture_not_raw_text(client, gateway):
    before = len(gateway.calls)
    res = client.post("/route", json={"prompt": "summarize the ticket JIRA-1234"})
    body = res.json()
    assert res.status_code == 200
    assert body["intent"] == "summarize"
    assert body["route"] == "cheap"
    assert "hotel wifi" in body["answer"].lower()
    assert body["model"] != "fixture"
    assert gateway.calls[before:]
    assert body["notice"] in (None, "")


def test_confluence_wiki_url_selects_the_page_id():
    from app.tools.router import decide

    prompt = (
        "summarize the confluence page "
        "https://tailored-prod.atlassian.net/wiki/spaces/2026Replatform/pages/"
        "1290207249/Sitemap+Generation+Flow+Replatform+Design"
    )
    decision = decide(prompt)
    assert decision.source == "confluence"
    assert decision.item_id == "1290207249"
    assert decision.ambiguous is False


def test_confluence_and_notion_fixtures_are_summarized(client):
    page = client.post(
        "/route",
        json={
            "prompt": (
                "summarize https://tailored-prod.atlassian.net/wiki/spaces/"
                "demo/pages/9000000042/Onboarding"
            )
        },
    ).json()
    assert "onboarding" in page["answer"].lower() or "laptop" in page["answer"].lower()
    assert page["model"] != "fixture"
    note = client.post(
        "/route",
        json={"prompt": "summarize https://www.notion.so/Launch-notes-7"},
    ).json()
    assert "priya" in note["answer"].lower()
    assert note["model"] != "fixture"


def test_notes_do_not_open_source_fixtures(client):
    res = client.post("/route", json={"prompt": "summarize these notes: the launch slipped and Priya owns the dry run."})
    body = res.json()
    assert body["intent"] == "summarize"
    assert "hotel wifi" not in body["answer"].lower()
    assert "onboarding checklist" not in body["answer"].lower()


def test_code_like_fixture_takes_premium_and_status_note_stays_cheap(client):
    code = client.post("/route", json={"prompt": "summarize the ticket JIRA-9999"}).json()
    assert code["intent"] == "code"
    assert code["route"] == "premium"
    note = client.post("/route", json={"prompt": "summarize the ticket JIRA-1234"}).json()
    assert note["intent"] == "summarize"
    assert note["route"] == "cheap"


def test_two_sources_call_neither_and_a_miss_does_not_escalate(client, gateway):
    before = len(gateway.calls)
    both = client.post(
        "/route",
        json={
            "prompt": (
                "summarize JIRA-1234 and "
                "https://tailored-prod.atlassian.net/wiki/spaces/demo/pages/9000000042"
            )
        },
    ).json()
    assert both["notice"] == "Name one source."
    assert both["answer"] == "Name one source."
    assert both["model"] == "none"
    assert both["escalated"] is False
    assert "hotel wifi" not in both["answer"].lower()
    assert both["tool_line"] in (None, "")
    missing = client.post("/route", json={"prompt": "summarize the ticket JIRA-404"}).json()
    assert missing["notice"] == "Document was not found."
    assert missing["answer"] == "Document was not found."
    assert missing["model"] == "none"
    assert missing["escalated"] is False
    assert missing["can_escalate"] is False
    assert missing["cost_usd"] == 0
    assert missing["tool_line"] in (None, "")
    assert len(gateway.calls) == before


def test_jira_url_miss_does_not_call_a_model(client, gateway, monkeypatch):
    monkeypatch.setattr("app.orchestrator.fetch_atlassian", lambda source, item_id: None)
    before = len(gateway.calls)
    body = client.post(
        "/route",
        json={"prompt": "Summarize the https://tailored-prod.atlassian.net/browse/RFW-6529"},
    ).json()
    assert body["notice"] == "Document was not found."
    assert body["answer"] == "Document was not found."
    assert body["model"] == "none"
    assert body["route"] == "retrieval"
    assert body["intent"] == "lookup"
    assert body["escalated"] is False
    assert body["can_escalate"] is False
    assert body["cost_usd"] == 0
    assert body["tool_line"] in (None, "")
    assert "RFW-6529" not in body["answer"]
    assert gateway.calls[before:] == []


def test_confluence_wiki_url_miss_does_not_call_a_model(client, gateway, monkeypatch):
    monkeypatch.setattr("app.orchestrator.fetch_atlassian", lambda source, item_id: None)
    before = len(gateway.calls)
    body = client.post(
        "/route",
        json={
            "prompt": (
                "summarize https://tailored-prod.atlassian.net/wiki/spaces/"
                "2026Replatform/pages/1290207249/Sitemap+Generation+Flow"
            )
        },
    ).json()
    assert body["notice"] == "Document was not found."
    assert body["model"] == "none"
    assert body["escalated"] is False
    assert body["tool_line"] in (None, "")
    assert gateway.calls[before:] == []


def test_fixture_hit_names_the_source_and_does_not_say_live(client, monkeypatch):
    def fail(source, item_id):
        raise AssertionError("a fixture hit must not call Atlassian")

    monkeypatch.setattr("app.orchestrator.fetch_atlassian", fail)
    page = client.post(
        "/route",
        json={
            "prompt": "summarize https://tailored-prod.atlassian.net/wiki/spaces/demo/pages/9000000042/Onboarding"
        },
    ).json()
    assert page["tool_line"] == "Confluence · 9000000042 · fixture"
    assert "mcp" not in (page["tool_line"] or "").lower()
    note = client.post("/route", json={"prompt": "summarize the ticket JIRA-1234"}).json()
    assert note["tool_line"] == "Jira · JIRA-1234 · fixture"


def test_fetched_body_is_capped_before_classify(client, monkeypatch):
    seen = {}

    def long_page(source, item_id):
        return {"id": item_id, "title": "Long", "body": "A" * 7000 + " https://secret.example/browse/RFW-1"}

    def capture(self, prompt, source=None, looks_like_code=None):
        seen["prompt"] = prompt
        from app.schemas import Classification
        return Classification(
            intent="summarize", confidence=0.9, method="rules", matched_rule="test"
        )

    monkeypatch.setattr("app.orchestrator.fetch_atlassian", long_page)
    monkeypatch.setattr("app.classifier.service.Classifier.classify", capture)
    body = client.post(
        "/route",
        json={"prompt": "Summarize the https://tailored-prod.atlassian.net/browse/RFW-1"},
    ).json()
    assert body["notice"] == "Document was truncated."
    assert body["tool_line"] == "Jira · RFW-1 · live"
    assert len(seen["prompt"]) == 6000
    assert "http" not in seen["prompt"]
    assert "RFW-1" not in seen["prompt"]


def test_pto_lookup_still_skips_the_model(client, gateway):
    before = len(gateway.calls)
    res = client.post("/route", json={"prompt": "What's our PTO policy?"})
    body = res.json()
    assert body["route"] == "retrieval"
    assert body["model"] == "fixture"
    assert body["tool_line"] in (None, "")
    assert gateway.calls[before:] == []
