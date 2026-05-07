import json
import random
from pathlib import Path
from datasets import load_dataset

DATA_DIR = Path(__file__).resolve().parent

# --- local source ---
local_json = Path("/Users/eligross/Downloads/Opus4.6 + opus4.5_reasoning_927x.jsonl")

# --- outputs ---
out_train = DATA_DIR / "train_merged.jsonl"
out_eval = DATA_DIR / "eval_merged.jsonl"

# --- sample sizes ---
max_traces = 4000              # smolagents/training-traces
max_glaive = 6000              # glaiveai/glaive-function-calling-v2
max_ultrachat = 6000           # HuggingFaceH4/ultrachat_200k

# --- split ---
eval_fraction = 0.1

random.seed(42)


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_local_rows(path: Path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if "messages" in obj and isinstance(obj["messages"], list):
                rows.append({"messages": normalize_messages(obj["messages"])})
    return rows


def normalize_messages(messages):
    cleaned = []

    for m in messages:
        if not isinstance(m, dict):
            continue

        role = m.get("role")
        content = m.get("content", "")

        # keep only roles we can train on cleanly
        if role not in {"system", "user", "assistant", "tool"}:
            continue

        # normalize content to string
        if isinstance(content, list):
            # flatten content parts if present
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        parts.append(str(item["text"]))
                    else:
                        parts.append(json.dumps(item, ensure_ascii=False))
                else:
                    parts.append(str(item))
            content = "\n".join(parts)
        elif not isinstance(content, str):
            content = str(content)

        content = content.strip()

        # skip empty non-system messages
        if not content and role != "system":
            continue

        cleaned.append({"role": role, "content": content})

    return cleaned


def has_user_and_assistant(messages):
    roles = [m.get("role") for m in messages]
    return "user" in roles and "assistant" in roles


def dedupe_key(messages):
    return json.dumps(messages, ensure_ascii=False, sort_keys=True)


def normalize_trace_example(ex):
    """
    Conservative normalization for smolagents/training-traces.
    """
    if "messages" in ex and isinstance(ex["messages"], list):
        msgs = normalize_messages(ex["messages"])
        if msgs and has_user_and_assistant(msgs):
            return {"messages": msgs}

    if "prompt" in ex and "completion" in ex:
        msgs = [
            {"role": "user", "content": str(ex["prompt"]).strip()},
            {"role": "assistant", "content": str(ex["completion"]).strip()},
        ]
        msgs = normalize_messages(msgs)
        if has_user_and_assistant(msgs):
            return {"messages": msgs}

    return None


def normalize_ultrachat_example(ex):
    """
    UltraChat already uses conversational messages in its SFT split.
    """
    if "messages" in ex and isinstance(ex["messages"], list):
        msgs = normalize_messages(ex["messages"])
        if msgs and has_user_and_assistant(msgs):
            return {"messages": msgs}

    if "prompt" in ex and "messages" not in ex:
        # rare fallback
        prompt = str(ex["prompt"]).strip()
        if prompt:
            return {"messages": [{"role": "user", "content": prompt}]}

    return None


def flatten_glaive_chat(text):
    """
    Glaive often stores a whole multi-turn conversation in a single string like:
    USER: ...
    ASSISTANT: ...
    TOOL_CALLS: ...
    TOOL_RESPONSE: ...
    We convert that into message objects conservatively.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    markers = ["USER:", "ASSISTANT:", "TOOL_CALLS:", "TOOL_RESPONSE:", "FUNCTION RESPONSE:"]
    lines = text.splitlines()

    chunks = []
    current_role = None
    current_lines = []

    def flush():
        nonlocal current_role, current_lines, chunks
        if current_role and current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                if current_role == "USER":
                    chunks.append({"role": "user", "content": content})
                elif current_role == "ASSISTANT":
                    chunks.append({"role": "assistant", "content": content})
                elif current_role in {"TOOL_CALLS", "TOOL_RESPONSE", "FUNCTION RESPONSE"}:
                    chunks.append({"role": "tool", "content": content})
        current_role = None
        current_lines = []

    for line in lines:
        stripped = line.strip()

        matched = None
        for marker in markers:
            if stripped.startswith(marker):
                matched = marker[:-1]  # drop :
                break

        if matched:
            flush()
            current_role = matched
            remainder = stripped[len(matched) + 1 :].strip()
            if remainder:
                current_lines.append(remainder)
        else:
            current_lines.append(line)

    flush()

    chunks = normalize_messages(chunks)
    if chunks and has_user_and_assistant(chunks):
        return {"messages": chunks}

    return None


def normalize_glaive_example(ex):
    """
    Handle common Glaive layouts.
    """
    if "messages" in ex and isinstance(ex["messages"], list):
        msgs = normalize_messages(ex["messages"])
        if msgs and has_user_and_assistant(msgs):
            return {"messages": msgs}

    # Common text-style fields
    for key in ["chat", "conversation", "text"]:
        if key in ex and isinstance(ex[key], str):
            row = flatten_glaive_chat(ex[key])
            if row is not None:
                return row

    # prompt/completion fallback
    if "prompt" in ex and "completion" in ex:
        msgs = normalize_messages([
            {"role": "user", "content": str(ex["prompt"])},
            {"role": "assistant", "content": str(ex["completion"])},
        ])
        if has_user_and_assistant(msgs):
            return {"messages": msgs}

    if "system" in ex and "chat" in ex:
        full = f"SYSTEM: {ex['system']}\n{ex['chat']}"
        row = flatten_glaive_chat(full)
        if row is not None:
            return row

    return None


def collect_streamed_rows(dataset_name, split, limit, normalizer):
    rows = []
    streamed = load_dataset(dataset_name, split=split, streaming=True)

    for ex in streamed:
        row = normalizer(ex)
        if row is None:
            continue
        rows.append(row)
        if len(rows) >= limit:
            break

    return rows


def main():
    all_rows = []
    seen = set()

    # 1) local reasoning data
    print("Loading local JSONL...")
    local_rows = load_local_rows(local_json)
    print(f"Loaded local rows: {len(local_rows)}")

    # 2) smolagents traces
    print("Streaming smolagents/training-traces...")
    trace_rows = collect_streamed_rows(
        "smolagents/training-traces",
        "train",
        max_traces,
        normalize_trace_example,
    )
    print(f"Loaded smolagents rows: {len(trace_rows)}")

    # 3) glaive function calling
    print("Streaming glaiveai/glaive-function-calling-v2...")
    glaive_rows = collect_streamed_rows(
        "glaiveai/glaive-function-calling-v2",
        "train",
        max_glaive,
        normalize_glaive_example,
    )
    print(f"Loaded glaive rows: {len(glaive_rows)}")

    # 4) general chat dataset
    print("Streaming HuggingFaceH4/ultrachat_200k...")
    ultrachat_rows = collect_streamed_rows(
        "HuggingFaceH4/ultrachat_200k",
        "train_sft",
        max_ultrachat,
        normalize_ultrachat_example,
    )
    print(f"Loaded ultrachat rows: {len(ultrachat_rows)}")

    # merge + dedupe
    for source_rows in [local_rows, trace_rows, glaive_rows, ultrachat_rows]:
        for row in source_rows:
            msgs = row["messages"]
            if not msgs or not has_user_and_assistant(msgs):
                continue

            key = dedupe_key(msgs)
            if key in seen:
                continue

            seen.add(key)
            all_rows.append({"messages": msgs})

    print(f"Merged unique rows: {len(all_rows)}")

    random.shuffle(all_rows)

    n_eval = max(1, int(len(all_rows) * eval_fraction))
    eval_rows = all_rows[:n_eval]
    train_rows = all_rows[n_eval:]

    write_jsonl(out_train, train_rows)
    write_jsonl(out_eval, eval_rows)

    print(f"Wrote train: {out_train} ({len(train_rows)} rows)")
    print(f"Wrote eval:  {out_eval} ({len(eval_rows)} rows)")


if __name__ == "__main__":
    main()
