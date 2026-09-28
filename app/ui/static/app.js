const $ = (id) => document.getElementById(id);

const NOTES = "Summarize these notes: the launch slipped to 2026-10-03 because the billing cert expired. 42 minutes of errors. Owner Priya.";

const DEMOS = {
  summarize: NOTES,
  cache: "please " + NOTES,
  ticket: "What's the status of TICKET-123?",
  code: "Refactor this function so the baseline cost is computed in one place.",
  counted: "Can you turn the launch writeup into something the execs can skim",
};

const LABELS = {
  cache: "Cache hit",
  cheap: "Low-cost model",
  retrieval: "Retrieval first",
  mid: "Mid-tier",
  premium: "Premium",
};

const money = (n, digits = 4) => {
  const v = Number(n) || 0;
  return (v < 0 ? "-$" : "$") + Math.abs(v).toFixed(digits);
};

function routeKey(route) {
  return (route || "cheap").split(" ")[0].replace("→", "").trim();
}

function displayLabel(label, key) {
  const text = label || LABELS[key] || key || "";
  return text
    .replace(/\bcheap\b/gi, "low-cost")
    .replace(/\bCheapest-first\b/g, "Lowest-cost first");
}

function tag(route, label) {
  const key = routeKey(route);
  return `<span class="tag ${key}">${displayLabel(label, key)}</span>`;
}

function toolLine(data) {
  const line = (data && data.tool_line) || "";
  if (!line || /mcp/i.test(line)) return "";
  return line;
}

function decisionLine(data) {
  if (!data || data.route_label === "Routing…") return "";
  const reason = data.escalate_reason || "";
  if (reason === "user_override") return "You asked for the smart model.";
  if (reason.startsWith("quality_fail")) return "Low-cost answer failed the check · escalated once.";
  if (reason.endsWith("_unavailable")) return "Low-cost path was down · escalated once.";
  if (data.cache_hit) return "Same job as a recent answer · served from cache.";
  if (data.classifier_method === "small_model" && data.intent === "ambiguous") {
    return "No catalog match · sent to mid. Not a ticket lookup.";
  }
  if (data.classifier_method === "small_model") {
    return "Rules were unsure · small model labeled it. Not a catalog match.";
  }
  if (data.route === "premium" && data.intent === "code") return "Code stays on premium. Not a low-cost path.";
  if (data.notice) return data.notice;
  if (data.route === "retrieval") return "Known ticket or policy · fixture, no model call.";
  if (data.route === "cheap") return "Language chore · low-cost model. Gate still runs.";
  if (data.route === "mid") return "No low-cost route for this job · sent to mid.";
  if (data.escalated) return "Escalated once. Not sent again.";
  return "";
}

function clock(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(11, 19);
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function setRoute(route) {
  const key = routeKey(route);
  document.querySelectorAll("#routes li").forEach((li) => {
    li.classList.toggle("on", li.dataset.route === key);
  });
  document.querySelectorAll("#flow li[data-step]").forEach((li) => li.classList.add("on"));
  const path = document.querySelector('#flow li[data-step="path"]');
  if (path) path.textContent = displayLabel(LABELS[key], key);
}

function paintSavings(savings) {
  const requests = savings.requests || 0;
  $("x").textContent = money(savings.always_premium_usd, 4);
  $("y").textContent = money(savings.routed_usd, 4);
  $("pct").textContent = `${Number(savings.saved_pct || 0).toFixed(1)}%`;
  const saved = money(savings.saved_usd, 4);
  $("saved-line").textContent = `${saved} saved · ${requests} demo request${requests === 1 ? "" : "s"}`;
  $("mix").textContent = mixLine(savings);
}

const MIX_ROUTES = ["cache", "cheap", "retrieval", "mid", "premium"];

function mixLine(savings) {
  const requests = savings.requests || 0;
  if (!requests) return "no routes yet";
  const counts = savings.by_route || {};
  const parts = MIX_ROUTES.map((name) => `${counts[name] || 0} ${(LABELS[name] || name).toLowerCase()}`);
  const escalated = savings.escalated || 0;
  return `${parts.join(" · ")} · ${escalated} escalated`;
}

function paintActivity(logs) {
  const list = $("activity");
  if (!logs.length) {
    list.innerHTML = `<li class="empty">No requests yet. Paste a prompt or replay the eval set.</li>`;
    return;
  }
  list.innerHTML = logs.slice(0, 6).map((row) => {
    const key = routeKey(row.route_label || row.route);
    const prompt = (row.prompt || "").replace(/\s+/g, " ").slice(0, 72);
    const extra = row.escalated ? " · escalated" : "";
    return `<li>
      ${tag(key, row.route_label)}
      <div>
        <div class="what">${prompt}</div>
        <div class="sub">${row.model || ""} · ${money(row.cost_usd)} vs premium ${money(row.baseline_cost_usd)}${extra}</div>
      </div>
      <time>${clock(row.timestamp)}</time>
    </li>`;
  }).join("");
}

function paintTable(logs) {
  const body = $("rows");
  if (!logs.length) {
    body.innerHTML = `<tr><td class="empty" colspan="9">No requests yet. Paste a prompt or replay the eval set.</td></tr>`;
    return;
  }
  body.innerHTML = logs.map((row) => `
    <tr>
      <td>${clock(row.timestamp)}</td>
      <td>${row.intent}</td>
      <td>${tag(row.route, row.route_label || row.route)}</td>
      <td>${row.model}</td>
      <td>${row.cache_hit ? "hit" : "miss"}</td>
      <td>${row.escalated ? (row.escalate_reason || "yes") : ""}</td>
      <td>${money(row.cost_usd)}</td>
      <td>${money(row.baseline_cost_usd)}</td>
      <td>${money(row.saved_usd)}</td>
    </tr>`).join("");
}

async function refresh() {
  const mix = $("mix");
  const previous = mix.textContent;
  mix.dataset.state = "loading";
  if (!previous || previous === "no routes yet") mix.textContent = "loading routes…";
  try {
    const [savingsRes, logsRes] = await Promise.all([
      fetch("/savings?source=ui"),
      fetch("/logs?limit=50"),
    ]);
    if (!savingsRes.ok || !logsRes.ok) throw new Error("savings unavailable");
    const [savings, logs] = await Promise.all([savingsRes.json(), logsRes.json()]);
    paintSavings(savings);
    paintActivity(logs);
    paintTable(logs);
    mix.dataset.state = savings.requests ? "ready" : "empty";
  } catch (err) {
    mix.textContent = previous && previous !== "loading routes…" ? previous : "no routes yet";
    mix.dataset.state = "error";
    $("error").textContent = "Savings did not refresh. The last totals are still showing.";
  }
}

function fmtScore(value) {
  return value == null || value === "" ? "—" : Number(value).toFixed(2);
}

function showAnswer(data, loading) {
  $("error").textContent = "";
  $("empty-answer").hidden = true;
  $("ready-answer").hidden = false;
  const key = routeKey(data.route_label || data.route);
  $("badge").className = `tag ${key}`;
  $("badge").textContent = displayLabel(data.route_label, key);
  if (!loading) setRoute(data.route);
  const latency = data.latency_ms != null ? `${data.latency_ms} ms` : "—";
  $("meta").textContent = loading ? "Routing…" : (data.intent || "");
  const tool = loading ? "" : toolLine(data);
  const decision = loading ? "" : decisionLine(data);
  $("decision").textContent = [tool, decision].filter(Boolean).join(" · ");
  $("fact-model").textContent = loading ? "…" : (data.model || "—");
  $("fact-cost").textContent = loading ? "…" : money(data.cost_usd);
  $("fact-base").textContent = loading ? "…" : money(data.baseline_cost_usd);
  $("fact-latency").textContent = loading ? "…" : latency + (data.cache_hit ? " · cache hit" : "");
  $("fact-score").textContent = loading ? "…" : fmtScore(data.signal_score);
  $("fact-margin").textContent = loading ? "…" : fmtScore(data.signal_margin);
  $("fact-overlap").textContent = loading ? "…" : fmtScore(data.overlap_score);
  $("fact-why").textContent = loading ? "…" : (data.signal || "—");
  $("fact-overlap").parentElement.hidden = !loading && (data.overlap_score == null || data.overlap_score === "");
  $("fact-why").parentElement.hidden = !loading && !data.signal;
  $("answer").textContent = data.answer || "(empty model output)";
  $("notice").textContent = data.logger_ok === false
    ? "This call was not logged — savings total may be short."
    : (data.notice || "");
  const btn = $("escalate");
  btn.hidden = !data.can_escalate;
  btn.dataset.id = data.request_id || "";
  btn.disabled = false;
  btn.textContent = "Try the smart model";
}

async function submit() {
  const prompt = $("prompt").value.trim();
  $("error").textContent = "";
  if (!prompt) {
    $("error").textContent = "Paste a prompt first.";
    return;
  }
  $("go").disabled = true;
  $("prompt").disabled = true;
  showAnswer({ route: "cheap", route_label: "Routing…", answer: "Routing…", can_escalate: false }, true);
  document.querySelectorAll("#flow li[data-step]").forEach((li) => li.classList.add("on"));
  try {
    const res = await fetch("/route", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        prompt,
        source: "ui",
        force_premium: $("force").getAttribute("aria-pressed") === "true",
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      $("ready-answer").hidden = true;
      $("empty-answer").hidden = false;
      $("error").textContent = (data.detail && data.detail.error) || data.detail || "Request failed.";
      return;
    }
    showAnswer(data, false);
    await refresh();
  } catch (err) {
    $("error").textContent = String(err);
  } finally {
    $("go").disabled = false;
    $("prompt").disabled = false;
  }
}

async function escalate() {
  const btn = $("escalate");
  const previous = $("answer").textContent;
  btn.disabled = true;
  btn.textContent = "Asking the premium model…";
  try {
    const res = await fetch(`/route/${btn.dataset.id}/escalate`, { method: "POST" });
    const data = await res.json();
    if (res.status === 409) {
      showAnswer(data.detail, false);
    } else if (!res.ok) {
      $("answer").textContent = previous;
      $("error").textContent = (data.detail && data.detail.error) || "Premium call failed.";
      btn.disabled = false;
      btn.textContent = "Try the smart model";
      return;
    } else {
      showAnswer(data, false);
    }
    await refresh();
  } catch (err) {
    $("error").textContent = String(err);
  }
}

async function replay() {
  $("replay").disabled = true;
  $("replay").textContent = "Replaying…";
  try {
    const res = await fetch("/eval/replay", { method: "POST" });
    if (!res.ok) {
      $("error").textContent = "Replay failed.";
      return;
    }
    await refresh();
  } catch (err) {
    $("error").textContent = String(err);
  } finally {
    $("replay").disabled = false;
    $("replay").textContent = "Replay eval set";
  }
}

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("on"));
    chip.classList.add("on");
    $("prompt").value = DEMOS[chip.dataset.kind] || "";
    $("prompt").focus();
    scorePrompt();
  });
});

$("force").addEventListener("click", () => {
  const on = $("force").getAttribute("aria-pressed") !== "true";
  $("force").setAttribute("aria-pressed", String(on));
  $("force").classList.toggle("active", on);
  $("mode-pill").textContent = on ? "Force premium" : "Router on";
  $("mode-pill").classList.toggle("on", !on);
});

$("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.dataset.theme === "dark" ? "" : "dark";
  root.dataset.theme = next;
  $("theme").textContent = next ? "☾" : "☀";
});

$("go").addEventListener("click", submit);
$("escalate").addEventListener("click", escalate);
$("replay").addEventListener("click", replay);
$("prompt").addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submit();
});

let scoreTimer = 0;
function clearLiveScore() {
  $("score-method").textContent = "—";
  $("score-intent").textContent = "—";
  $("score-value").textContent = "—";
  $("score-margin").textContent = "—";
  $("score-note").textContent = "Type a prompt. This score does not call a model.";
}

async function scorePrompt() {
  const prompt = $("prompt").value.trim();
  if (prompt.length < 8) {
    clearLiveScore();
    return;
  }
  try {
    const res = await fetch("/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) return;
    const data = await res.json();
    $("score-method").textContent = data.method || "—";
    $("score-intent").textContent = data.intent || "—";
    $("score-value").textContent = fmtScore(data.signal_score);
    $("score-margin").textContent = fmtScore(data.margin);
    const bars = (data.ranked || [])
      .map((row) => `${row.intent} ${Number(row.score).toFixed(2)}`)
      .join(" · ");
    $("score-note").textContent = bars ? `${data.signal} · ${bars}` : (data.signal || "");
  } catch (_err) {
    $("score-note").textContent = "Score unavailable.";
  }
}

$("prompt").addEventListener("input", () => {
  clearTimeout(scoreTimer);
  scoreTimer = setTimeout(scorePrompt, 250);
});
refresh().catch((err) => {
  $("error").textContent = "Could not load savings. " + err;
});
