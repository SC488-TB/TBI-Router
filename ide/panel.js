const LABELS = {
  cache: "cache",
  cheap: "low-cost model",
  retrieval: "retrieval",
  mid: "mid-tier",
  premium: "premium",
};

function displayLabel(value) {
  const text = String(value || "");
  if (LABELS[text]) return LABELS[text];
  return text.replace(/\bcheap\b/g, "low-cost");
}

function panelHtml(state) {
  const route = displayLabel(state.route_label || state.route || "—");
  const model = state.model || "—";
  const cost = Number(state.cost_usd || 0).toFixed(4);
  const answer = escapeHtml(state.answer || "(empty)");
  const escalated = state.escalated ? "Escalated once." : "";
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 16px; }
    .meta { font-size: 13px; margin-bottom: 12px; }
    .answer { white-space: pre-wrap; line-height: 1.45; }
    button { margin-top: 16px; }
  </style>
</head>
<body>
  <div class="meta">${escapeHtml(route)} · ${escapeHtml(model)} · $${cost}</div>
  <div class="meta">${escapeHtml(escalated)}</div>
  <div class="answer">${answer}</div>
  <button id="copy">Copy answer</button>
  <script>
    const vscode = acquireVsCodeApi();
    document.getElementById("copy").addEventListener("click", () => {
      vscode.postMessage({ type: "copy" });
    });
  </script>
</body>
</html>`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function showResult(panel, state) {
  panel.webview.html = panelHtml(state);
  panel.webview.onDidReceiveMessage((message) => {
    if (message && message.type === "copy") {
      require("vscode").env.clipboard.writeText(state.answer || "");
    }
  });
}

module.exports = { showResult };
