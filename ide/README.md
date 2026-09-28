# TBI Router command

One VS Code command. It posts the selection to `POST /route` and prints the answer. It does not pick a model and it does not replace Copilot. See ADR 0011 in `docs/adr/0011-ide-command-calls-the-router.md`.

## Install

1. Start the router: `python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8766`
2. In VS Code, run **Developer: Install Extension from Location…** and pick this `ide/` folder. Reload the window.
3. Select text. Run **TBI: Route selection** from the command palette.
4. Read the answer in the **TBI Router** panel beside the editor. The first line is the route, the model, and the cost. This is not the Copilot chat.

The default URL is `http://127.0.0.1:8766`. Change `tbi.routerUrl` if the router is on another port.

Code still goes to premium when the router says so. Do not add a model picker here.

## Chat

In Copilot or Cursor chat, type `@tbi` and the message, then send. The extension reads only that addressed message, posts it to `POST /route`, and opens the TBI panel. It does not read the previous Copilot or Cursor turn, and it does not call the chat model.
