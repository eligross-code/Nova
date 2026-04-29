"""Aura backend: MLX-backed agent with macOS tools.

Single self-contained file. Reads one prompt per line on stdin and emits a
line-prefixed event stream on stdout that the Swift GUI parses. Modeled after
`agent_infra_v1/agent_core.py` (JSON ReAct loop) but using local MLX inference
instead of Ollama, and your `from_base/use_model.py` style for model lifecycle.

Wire protocol (line-based, on stdout):
  __READY__              model loaded, ready for prompts
  [STEP] thinking|tool|final
  [TEXT] {one-line text} thought body
  [TOOL] {tool_name}
  [ARGS] {compact json}
  [RESULT] {one-line text}
  [FINAL]                begin streaming the final answer (plain text follows)
  ...plain text...       streamed final answer
  [ERROR] {message}
  __END__                turn complete
"""
from __future__ import annotations

import datetime as _dt
import gc
import json
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
from typing import Any, Callable, Dict

import mlx.core as mx
from mlx_lm import load, stream_generate


# ============================================================ model lifecycle

MODEL_PATH = "/Users/eligross/models/Qwen3.5-4B-merged-mlx-4bit"

_state: Dict[str, Any] = {"model": None, "tokenizer": None}


def _err(*parts) -> None:
    sys.stderr.write(" ".join(str(p) for p in parts) + "\n")
    sys.stderr.flush()


def load_model(path: str = MODEL_PATH) -> None:
    _err("Starting up...")
    t0 = time.perf_counter()
    m, tok = load(path)
    _state["model"] = m
    _state["tokenizer"] = tok
    _err(f"Startup time: {time.perf_counter() - t0:.2f} seconds")


def unload_model() -> None:
    t0 = time.perf_counter()
    _state["model"] = None
    _state["tokenizer"] = None
    gc.collect()
    mx.clear_cache()
    _err(f"Unload time: {time.perf_counter() - t0:.2f} seconds")


# ============================================================ macOS tools


def _osa(script: str) -> str:
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def open_app(app_name: str) -> str:
    subprocess.run(["open", "-a", app_name], check=True)
    return f"opened {app_name}"


def open_url(url: str) -> str:
    subprocess.run(["open", url], check=True)
    return f"opened {url}"


def list_running_apps() -> list[str]:
    out = _osa('''
    tell application "System Events"
        set appList to name of every application process whose background only is false
        set AppleScript's text item delimiters to linefeed
        return appList as text
    end tell
    ''')
    return [x.strip() for x in out.splitlines() if x.strip()]


def get_frontmost_app() -> str:
    return _osa('''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        return frontApp
    end tell
    ''')


def get_datetime() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_battery() -> str:
    return subprocess.run(
        ["pmset", "-g", "batt"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def notify(title: str, message: str) -> str:
    safe_t = title.replace('"', '\\"')
    safe_m = message.replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e", f'display notification "{safe_m}" with title "{safe_t}"'],
        check=True,
    )
    return f"notified: {title}"


def build_computer_state() -> str:
    front = get_frontmost_app()
    when = get_datetime()
    batt = get_battery().splitlines()[0] if get_battery() else ""
    apps = ", ".join(list_running_apps())
    return f"Frontmost: {front} | Time: {when} | Battery: {batt} | Running: {apps}"


TOOLS: Dict[str, Callable[..., Any]] = {
    "open_app": open_app,
    "open_url": open_url,
    "list_running_apps": list_running_apps,
    "get_frontmost_app": get_frontmost_app,
    "get_datetime": get_datetime,
    "get_battery": get_battery,
    "notify": notify,
    "build_computer_state": build_computer_state,
}

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "open_app": {
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
        "required": ["app_name"],
    },
    "open_url": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    "list_running_apps":    {"type": "object", "properties": {}, "required": []},
    "get_frontmost_app":    {"type": "object", "properties": {}, "required": []},
    "get_datetime":         {"type": "object", "properties": {}, "required": []},
    "get_battery":          {"type": "object", "properties": {}, "required": []},
    "notify": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "message": {"type": "string"}},
        "required": ["title", "message"],
    },
    "build_computer_state": {"type": "object", "properties": {}, "required": []},
}


# ============================================================ system prompt

SYSTEM_PROMPT = """You are Aura, an assistant running fully locally on a Mac.

You have access to the following tools (called via the user's terminal):
- open_app(app_name: str)
- open_url(url: str)
- list_running_apps()
- get_frontmost_app()
- get_datetime()
- get_battery()
- notify(title: str, message: str)
- build_computer_state()

Use build_computer_state() to get a snapshot instead of calling the smaller
context tools individually unless you have a specific reason. The initial
computer state is provided in the first user message.

NEVER expose tool names to the user. Always call tools yourself, then respond.

RESPOND IN JSON ONLY. Every reply must be a single JSON object with one of:

  {"type": "thinking", "thought": "..."}
  {"type": "tool_call", "tool": "<name>", "arguments": { ... }}
  {"type": "final",     "message": "..."}

Use "thinking" sparingly to plan a multi-step task. Use "tool_call" to act.
Use "final" to answer the user. After a tool result comes back, decide
whether to call another tool or finish.
"""


# ============================================================ LLM

_THINK_RE   = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_TAIL = re.compile(r".*?</think>",        re.DOTALL)  # Qwen3 sometimes omits opening tag
_MALFORMED_THINK_TOOL = re.compile(r"<tool_call>\s*(?:thinking|thought)\s*:.*?</think>\s*", re.DOTALL | re.IGNORECASE)
_TOOLCALL_XML = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_TOOLCALL_FNCALL = re.compile(r"^\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$", re.DOTALL)
_LEADING_LABEL = re.compile(r"^\s*(?:tool_call|final|thinking|thought)\s*:\s*", re.IGNORECASE)
_EOT = ("<|im_end|>", "<|endoftext|>")


def _format(messages: list[dict]) -> str:
    return _state["tokenizer"].apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )


def generate(messages: list[dict], max_tokens: int = 1024) -> str:
    """Run a single completion. Returns the full response with `<think>...</think>`
    blocks stripped. We don't stream this — we want a parseable JSON object.
    """
    prompt = _format(messages)
    out = []
    for chunk in stream_generate(
        _state["model"], _state["tokenizer"], prompt=prompt, max_tokens=max_tokens
    ):
        if STOP.is_set():
            break
        text = chunk.text
        if any(eot in text for eot in _EOT):
            break
        out.append(text)
    raw = "".join(out)
    return strip_model_noise(raw)


def strip_model_noise(raw: str) -> str:
    """Remove Qwen's visible reasoning leakage before parsing.

    The merged model often mixes native Qwen tool calls with fragments like:
      <tool_call>
      thinking: ...
      </think>

    That is not a real tool call. Strip it before the actual final/tool block
    so Swift never sees duplicated "thinking" rows.
    """
    raw = _MALFORMED_THINK_TOOL.sub("", raw)
    raw = _THINK_RE.sub("", raw)
    # Qwen3 frequently emits the closing </think> tag without the opening one.
    if "</think>" in raw and "<think>" not in raw:
        raw = _THINK_TAIL.sub("", raw, count=1)
    return raw.strip()


def _parse_kwargs(s: str) -> dict:
    """Best-effort parse of `key=value, key="..."` arg strings.
    Used as a fallback when the model emits Python-call style args.
    """
    s = s.strip()
    if not s:
        return {}
    # Try JSON first if it looks like a dict.
    if s.startswith("{") and s.endswith("}"):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    out: dict[str, Any] = {}
    # Split on commas not inside quotes.
    parts: list[str] = []
    depth = 0
    cur = ""
    in_str: str | None = None
    for ch in s:
        if in_str:
            cur += ch
            if ch == in_str and not cur.endswith("\\" + in_str):
                in_str = None
            continue
        if ch in ("\"", "'"):
            in_str = ch
            cur += ch
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    for p in parts:
        if "=" not in p:
            continue
        k, _, v = p.partition("=")
        k = k.strip()
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        else:
            try:
                v = json.loads(v)
            except (json.JSONDecodeError, ValueError):
                pass
        out[k] = v
    return out


def normalize_response(raw: str) -> dict:
    """Coerce whatever the model said into our JSON action shape.
    Handles three formats seen from Qwen3:
      1. Our JSON: {"type": "...", ...}
      2. Qwen native XML: <tool_call> open_app(app_name="...") </tool_call>
                       or <tool_call> {"name": "open_app", "arguments": {...}} </tool_call>
      3. Plain prose -> treat as final.
    """
    s = raw.strip()
    if not s:
        return {"type": "final", "message": ""}

    # 1. Try direct JSON.
    data = parse_json(s)
    if data and isinstance(data.get("type"), str):
        return data
    if data and isinstance(data.get("name"), str):
        # Looks like a Qwen-style {"name": ..., "arguments": ...} blob.
        return {"type": "tool_call", "tool": data["name"], "arguments": data.get("arguments", {})}
    if data and isinstance(data.get("tool"), str):
        return {"type": "tool_call", "tool": data["tool"], "arguments": data.get("arguments", {})}

    # 2. Try Qwen's <tool_call>...</tool_call> XML. Prefer the last block:
    # malformed outputs can leak an earlier fake "<tool_call> thinking:" block.
    matches = list(_TOOLCALL_XML.finditer(s))
    body = matches[-1].group(1).strip() if matches else ""
    # Sometimes streaming stops before Qwen closes </tool_call>; parse the open
    # block anyway if it contains a complete JSON/function call.
    if not body and "<tool_call>" in s:
        body = s.rsplit("<tool_call>", 1)[-1].strip()
    if body:
        body = _LEADING_LABEL.sub("", body).strip()
        # 2a. JSON inside.
        inner = parse_json(body)
        if inner:
            if "name" in inner:
                return {"type": "tool_call", "tool": inner["name"], "arguments": inner.get("arguments", {})}
            if "tool" in inner:
                return {"type": "tool_call", "tool": inner["tool"], "arguments": inner.get("arguments", {})}
        loose_final = _loose_final_from_body(body)
        if loose_final:
            return loose_final
        # 2b. Python-call style: open_app(app_name="calculator").
        m2 = _TOOLCALL_FNCALL.match(body)
        if m2:
            return {
                "type": "tool_call",
                "tool": m2.group(1),
                "arguments": _parse_kwargs(m2.group(2)),
            }

    # 3. Fallback: treat the (already think-stripped) text as the final answer.
    return {"type": "final", "message": s}


def _loose_final_from_body(body: str) -> dict | None:
    """Recover final(message=...) when Qwen writes JSON-ish text with raw
    newlines inside the string, which is invalid JSON but semantically clear."""
    if '"tool"' not in body or '"final"' not in body or '"message"' not in body:
        return None
    m = re.search(r'"message"\s*:\s*"', body)
    if not m:
        return None
    start = m.end()
    end = body.rfind('"')
    if end <= start:
        return None
    msg = body[start:end]
    try:
        msg = json.loads(f'"{msg}"')
    except json.JSONDecodeError:
        msg = msg.replace(r"\\n", "\n").replace(r"\\\"", '"')
    return {"type": "tool_call", "tool": "final", "arguments": {"message": msg}}


def _coerce_pseudo_tool(action: dict) -> dict:
    """Turn `tool_call` actions whose tool name is `final`/`thinking`/`message`/`respond`
    into the right pseudo-action. Qwen3 likes to wrap final answers in <tool_call>."""
    if action.get("type") != "tool_call":
        return action
    tool = (action.get("tool") or "").lower()
    args = action.get("arguments") or {}
    if tool in {"final", "respond", "answer", "reply", "message"}:
        msg = args.get("message") or args.get("text") or args.get("content") or ""
        if not msg and isinstance(args, dict) and len(args) == 1:
            msg = next(iter(args.values()))
        return {"type": "final", "message": str(msg)}
    if tool in {"thinking", "thought", "think"}:
        thought = args.get("thought") or args.get("text") or args.get("content") or ""
        return {"type": "thinking", "thought": str(thought)}
    return action


def parse_json(s: str) -> dict:
    """Lenient JSON parse: try whole, then first balanced object."""
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # find first {...} balanced object
    depth = 0
    start = -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(s[start:i + 1])
                except json.JSONDecodeError:
                    pass
                start = -1
    return {}


# ============================================================ output helpers

_OUT_LOCK = threading.Lock()


def emit(line: str) -> None:
    with _OUT_LOCK:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def _truncate(s: str, n: int = 400) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "\u2026"


def _stream_text(text: str, chunk: int = 6, delay: float = 0.012) -> None:
    """Animate a final answer to stdout in small chunks. Cheap synthetic
    streaming so the GUI doesn't dump the whole answer at once."""
    i = 0
    n = len(text)
    while i < n:
        if STOP.is_set():
            return
        end = min(i + chunk, n)
        with _OUT_LOCK:
            sys.stdout.write(text[i:end])
            sys.stdout.flush()
        i = end
        time.sleep(delay)
    with _OUT_LOCK:
        sys.stdout.write("\n")
        sys.stdout.flush()


# ============================================================ agent loop

STOP = threading.Event()


def run(user_input: str, max_steps: int = 8) -> None:
    """JSON ReAct agent. Streams events to stdout. This IS the new run."""
    initial_state = ""
    try:
        initial_state = build_computer_state()
    except Exception as e:
        _err("computer_state failed:", e)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps({
                "user_message": user_input,
                "computer_state": initial_state,
                "tool_schemas": TOOL_SCHEMAS,
            }),
        },
    ]

    for step in range(max_steps):
        if STOP.is_set():
            emit("[ERROR] cancelled")
            return

        try:
            raw = generate(messages, max_tokens=4000)
        except KeyboardInterrupt:
            emit("[ERROR] cancelled")
            return
        except Exception as e:
            _err("generate failed:", e)
            _err(traceback.format_exc())
            emit(f"[ERROR] generate: {e}")
            return

        data = _coerce_pseudo_tool(normalize_response(raw))
        kind = (data.get("type") or "").lower()

        if kind == "final":
            msg = (data.get("message") or "").strip()
            emit("[STEP] final")
            emit("[FINAL]")
            _stream_text(msg)
            return

        if kind == "thinking":
            thought = _truncate(data.get("thought") or "", 600)
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": json.dumps({"note": "continue", "internal_thought_seen": bool(thought)}),
            })
            continue

        if kind == "tool_call":
            tool = data.get("tool") or ""
            args = data.get("arguments") or {}
            if tool not in TOOLS:
                emit(f"[ERROR] unknown tool: {tool}")
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": json.dumps({"tool_error": f"unknown tool: {tool}. Respond in JSON only."}),
                })
                continue
            emit("[STEP] tool")
            emit(f"[TOOL] {tool}")
            try:
                emit(f"[ARGS] {json.dumps(args, ensure_ascii=False)}")
            except Exception:
                emit("[ARGS] {}")
            try:
                result = TOOLS[tool](**args)
                result_str = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                _err("tool failed:", tool, e)
                result_str = f"error: {e}"
            emit(f"[RESULT] {_truncate(result_str)}")
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": json.dumps({"tool_result": result_str}),
            })
            continue

        # Should be unreachable: normalize_response always returns one of the
        # three known kinds. Treat as a final answer just in case.
        emit("[STEP] final")
        emit("[FINAL]")
        _stream_text(raw.strip() or "(empty response)")
        return

    emit("[STEP] final")
    emit("[FINAL]")
    _stream_text("(stopped: max steps reached)")


# ============================================================ main


def _on_sigint(signum, frame) -> None:
    STOP.set()


def main() -> None:
    signal.signal(signal.SIGINT, _on_sigint)
    load_model()
    emit("__READY__")

    for line in sys.stdin:
        prompt = line.rstrip("\n").strip()
        if not prompt:
            continue
        STOP.clear()
        try:
            run(prompt)
        except Exception as e:
            _err("run failed:", e)
            _err(traceback.format_exc())
            emit(f"[ERROR] {e}")
        emit("__END__")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
