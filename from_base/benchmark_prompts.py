import time
import json
import os
from mlx_lm import load, stream_generate

# ── Models to compare ─────────────────────────────────────────────────────────
MODELS = {
    "OptiQ":  "/Users/eligross/models/Qwen3.5-4B-OptiQ-4bit",
    "Merged": "/Users/eligross/models/Qwen3.5-4B-merged-mlx-4bit",
}

# ── Benchmarks ────────────────────────────────────────────────────────────────
BENCHMARKS = [
    {
        "name": "multi_step_algebra",
        "category": "math",
        "difficulty": "hard",
        "prompt": (
            "Solve for x:\n"
            "(2x - 3)/(x + 1) + (x + 4)/(x - 1) = 3\n"
            "Give all valid real solutions and note any excluded values."
        ),
    },
    {
        "name": "functional_equation",
        "category": "math",
        "difficulty": "hard",
        "prompt": (
            "Find all functions f: R -> R such that:\n"
            "f(x + y) = f(x)f(y), and f(0) = 1.\n"
            "State any assumptions needed."
        ),
    },
    {
        "name": "logic_grid_puzzle",
        "category": "logic",
        "difficulty": "hard",
        "prompt": (
            "Three people (Alice, Bob, Carol) each have a different pet "
            "(cat, dog, fish) and a different drink (tea, coffee, juice).\n"
            "Clues:\n- Alice doesn't own the dog\n"
            "- The coffee drinker owns the fish\n"
            "- Bob drinks tea\n- Carol owns the cat\n"
            "Determine each person's pet and drink."
        ),
    },
    {
        "name": "bat_and_ball",
        "category": "logic",
        "difficulty": "medium",
        "prompt": (
            "A bat and a ball cost $1.10 total. "
            "The bat costs $1 more than the ball. "
            "How much does the ball cost?"
        ),
    },
    {
        "name": "longest_unique_substring",
        "category": "coding",
        "difficulty": "hard",
        "prompt": (
            "Write a Python function that returns the length of the longest "
            "substring without repeating characters. Aim for O(n) time complexity."
        ),
    },
    {
        "name": "debug_is_prime",
        "category": "coding",
        "difficulty": "medium",
        "prompt": (
            "Identify and fix all bugs in this Python function:\n\n"
            "def is_prime(n):\n"
            "    if n <= 1:\n        return True\n"
            "    for i in range(2, n):\n"
            "        if n % i == 0:\n            return False\n"
            "    return True\n"
        ),
    },
    {
        "name": "lru_cache_design",
        "category": "coding",
        "difficulty": "hard",
        "prompt": (
            "Design an LRU cache supporting get and put in O(1) average time. "
            "Explain the data structures used and provide Python code."
        ),
    },
    {
        "name": "profit_vs_revenue",
        "category": "reading_comprehension",
        "difficulty": "medium",
        "prompt": (
            "Read the passage:\n"
            "'The company reported a decline in revenue but an increase in profit "
            "due to aggressive cost-cutting measures.'\n"
            "Question: How can profit increase despite declining revenue?"
        ),
    },
    {
        "name": "expected_rolls_for_six",
        "category": "probability",
        "difficulty": "medium",
        "prompt": (
            "You roll a fair six-sided die until you get a 6. "
            "What is the expected number of rolls? Explain briefly."
        ),
    },
    {
        "name": "letter_pattern",
        "category": "pattern_reasoning",
        "difficulty": "hard",
        "prompt": (
            "Infer the pattern and complete the mapping:\n"
            "ABC -> DEF\nXYZ -> ABC\nMNO -> ?\nExplain the rule."
        ),
    },
]


# ── Inference ─────────────────────────────────────────────────────────────────
def run(model, tokenizer, prompt, max_tokens=2500, silent=False):
    messages = [{"role": "user", "content": prompt}]
    formatted = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    t0 = time.perf_counter()
    response = ""
    think_tokens = 0
    in_think = False

    for chunk in stream_generate(model, tokenizer, prompt=formatted, max_tokens=max_tokens):
        if "<|im_end|>" in chunk.text:
            break
        response += chunk.text
        if "<think>" in chunk.text:
            in_think = True
        if "</think>" in chunk.text:
            in_think = False
        if in_think:
            think_tokens += 1
        if not silent:
            print(chunk.text, end="", flush=True)

    elapsed = time.perf_counter() - t0
    tok_count = len(response.split())

    # Extract think block and answer separately
    think_block = ""
    answer = response
    if "<think>" in response and "</think>" in response:
        start = response.index("<think>")
        end = response.index("</think>") + len("</think>")
        think_block = response[start:end]
        answer = response[end:].strip()

    return {
        "response": response,
        "think_block": think_block,
        "answer": answer,
        "elapsed_sec": round(elapsed, 2),
        "approx_tokens": tok_count,
        "tok_per_sec": round(tok_count / elapsed, 1) if elapsed > 0 else 0,
        "did_think": bool(think_block),
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    results = {}  # results[model_label][bench_name] = {...}

    for label, model_path in MODELS.items():
        print(f"\n{'='*60}")
        print(f"  Loading model: {label}")
        print(f"{'='*60}")
        model, tokenizer = load(model_path)
        results[label] = {}

        for bench in BENCHMARKS:
            print(f"\n--- [{label}] {bench['name']} ({bench['category']}, {bench['difficulty']}) ---")
            result = run(model, tokenizer, bench["prompt"], silent=True)
            results[label][bench["name"]] = result
            print(f"  ✓ {result['elapsed_sec']}s | ~{result['tok_per_sec']} tok/s | thought: {result['did_think']}")

        # Free memory between models
        del model, tokenizer

    # ── Save full results ──────────────────────────────────────────────────────
    os.makedirs("benchmark_results", exist_ok=True)
    with open("benchmark_results/full_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # ── Print comparison table ─────────────────────────────────────────────────
    print(f"\n\n{'='*80}")
    print("  BENCHMARK COMPARISON SUMMARY")
    print(f"{'='*80}")

    labels = list(MODELS.keys())
    col_w = 26

    # Header
    print(f"\n{'Benchmark':<28} {'Category':<22} {'Difficulty':<10}", end="")
    for label in labels:
        print(f"  {label:>{col_w}}", end="")
    print()
    print("-" * (28 + 22 + 10 + len(labels) * (col_w + 2) + 4))

    for bench in BENCHMARKS:
        name = bench["name"]
        print(f"{name:<28} {bench['category']:<22} {bench['difficulty']:<10}", end="")
        for label in labels:
            r = results[label][name]
            cell = f"{r['elapsed_sec']}s | {r['tok_per_sec']}t/s | 🧠{'✓' if r['did_think'] else '✗'}"
            print(f"  {cell:>{col_w}}", end="")
        print()

    # ── Speed summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print("  SPEED AVERAGES")
    print(f"{'='*80}")
    for label in labels:
        speeds = [results[label][b["name"]]["tok_per_sec"] for b in BENCHMARKS]
        avg = round(sum(speeds) / len(speeds), 1)
        think_count = sum(1 for b in BENCHMARKS if results[label][b["name"]]["did_think"])
        print(f"  {label}: avg {avg} tok/s | reasoned on {think_count}/{len(BENCHMARKS)} benchmarks")

    # ── Save answers for manual review ────────────────────────────────────────
    with open("benchmark_results/answers.txt", "w") as f:
        for bench in BENCHMARKS:
            f.write(f"\n{'='*80}\n")
            f.write(f"BENCHMARK: {bench['name']} | {bench['category']} | {bench['difficulty']}\n")
            f.write(f"PROMPT: {bench['prompt']}\n")
            f.write(f"{'='*80}\n")
            for label in labels:
                r = results[label][bench["name"]]
                f.write(f"\n[{label}] ({r['elapsed_sec']}s)\n")
                f.write(f"{r['answer']}\n")
                f.write("-" * 40 + "\n")

    print(f"\n  Full results saved to benchmark_results/")
    print(f"  Answers saved to benchmark_results/answers.txt")
    print(f"  Raw JSON saved to benchmark_results/full_results.json")


if __name__ == "__main__":
    main()