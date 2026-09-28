const vscode = require("vscode");
const { showResult } = require("./panel");

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("tbi.routeSelection", routeSelection)
  );
  if (vscode.chat && typeof vscode.chat.createChatParticipant === "function") {
    const participant = vscode.chat.createChatParticipant("tbi.router", routeChatMessage);
    participant.iconPath = new vscode.ThemeIcon("git-compare");
    context.subscriptions.push(participant);
  }
}

async function routeSelection() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("TBI: open a file and select the text to route.");
    return;
  }
  const prompt = editor.document.getText(editor.selection).trim();
  if (!prompt) {
    vscode.window.showWarningMessage("TBI: select the text to route. This command does not pick a model.");
    return;
  }

  const base = vscode.workspace.getConfiguration("tbi").get("routerUrl", "http://127.0.0.1:8766");
  const panel = vscode.window.createWebviewPanel(
    "tbiRouter",
    "TBI Router",
    vscode.ViewColumn.Beside,
    { enableScripts: true }
  );
  panel.webview.html = "<p style='padding:16px'>Routing… the router picks the model.</p>";

  try {
    const response = await fetch(`${String(base).replace(/\/$/, "")}/route`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        prompt,
        source: "ide",
        looks_like_code: editor.document.languageId !== "plaintext",
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      panel.webview.html = `<p style="padding:16px">Request failed (${response.status}).</p>`;
      return;
    }
    showResult(panel, data);
  } catch (err) {
    panel.webview.html = `<p style="padding:16px">Could not reach the router at ${escapeHtml(base)}. Start it, then run the command again.</p>`;
  }
}

async function routeChatMessage(request, _context, stream) {
  const prompt = String(request.prompt || "").trim();
  if (!prompt) {
    stream.markdown("Type the message after `@tbi`. This does not read the Copilot or Cursor turn, and it does not use the chat model.");
    return;
  }
  stream.progress("Routing… the router picks the model.");
  const base = vscode.workspace.getConfiguration("tbi").get("routerUrl", "http://127.0.0.1:8766");
  try {
    const response = await fetch(`${String(base).replace(/\/$/, "")}/route`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt, source: "ide", looks_like_code: false }),
    });
    const data = await response.json();
    if (!response.ok) {
      stream.markdown(`Request failed (${response.status}).`);
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      "tbiRouter",
      "TBI Router",
      vscode.ViewColumn.Beside,
      { enableScripts: true }
    );
    showResult(panel, data);
    const route = data.route_label || data.route || "—";
    const cost = Number(data.cost_usd || 0).toFixed(4);
    stream.markdown(`Routed. ${route} · ${data.model || "—"} · $${cost}. The chat model was not called.`);
  } catch (err) {
    stream.markdown(`Could not reach the router at ${base}. Start it, then try again.`);
  }
}

function escapeHtml(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function deactivate() {}

module.exports = { activate, deactivate };
