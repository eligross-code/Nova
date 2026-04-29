# Aura

A local-first, private AI companion for macOS. Menu bar app with a glass
panel summoned from anywhere, talking to a Python MLX runtime over a single
stdin/stdout pipe — no server, no localhost ports.

```
HotKey ─┐
         ├─▶ AppDelegate ─▶ AuraPanel ─▶ ChatVM ◀──NDJSON over stdio──▶ runtime.py ─▶ agent.py ─▶ MLX
StatusItem ─┘                                                                          └─▶ tools.py
```

## Layout

- `aura_app/` – Swift Package, the macOS GUI.
- `aura_backend/` – Python: `runtime.py` (stdio bridge), `agent.py` (MLX +
  ReAct), `tools.py` (macOS automation).
- `start.sh` – dev runner. Just `swift run -c release`; the Python child
  is spawned by the app itself.
- `package.sh` – assembles a real `Aura.app` bundle in `build/`.

## Running (dev)

```bash
# Set up the Python deps once:
python3 -m venv venv && . venv/bin/activate
pip install -r aura_backend/requirements.txt

# Then:
./start.sh
```

The hotkey is **off by default**. Click the menu bar item to summon, or
enable a global shortcut from Settings.

## Building a real .app

```bash
./package.sh           # build/Aura.app
./package.sh --sign    # ad-hoc codesign (no notarisation)
./package.sh --open    # open after building
```

## Wire format (Swift ⇄ Python, NDJSON, one JSON object per line)

Inbound (stdin):

| `type`     | extra fields                              |
|------------|-------------------------------------------|
| `chat`     | `id`, `prompt`, `max_tokens?`             |
| `agent`    | `id`, `prompt`, `max_tokens?`, `max_steps?` |
| `cancel`   | `id`                                      |
| `preload`  | –                                         |
| `unload`   | –                                         |
| `ping`     | –                                         |
| `shutdown` | –                                         |

Outbound (stdout):

| `type`        | extra fields                       |
|---------------|------------------------------------|
| `ready`       | (lifecycle)                        |
| `loaded`      | (lifecycle)                        |
| `pong`        | `model_loaded`                     |
| `token`       | `id`, `text`                       |
| `thinking`    | `id`, `text`                       |
| `tool`        | `id`, `tool`, `args`               |
| `tool_result` | `id`, `tool`, `result`             |
| `final`       | `id`, `text`                       |
| `error`       | `id?`, `message`                   |
| `done`        | `id`                               |
| `goodbye`     | (lifecycle)                        |

## Logs

Python stderr and Swift `os.Logger` are appended to
`~/Library/Logs/Aura/aura.log`.
