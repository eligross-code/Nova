import gc
import time

import mlx.core as mx
from mlx_lm import load, stream_generate


MODEL_PATH = "/Users/eligross/models/Qwen3.5-4B-merged-mlx-4bit"

model = None
tokenizer = None


def load_model():
    print("Starting up...")
    start = time.perf_counter()
    loaded_model, loaded_tokenizer = load(MODEL_PATH)
    end = time.perf_counter()
    print(f"Startup time: {end - start:.2f} seconds")
    return loaded_model, loaded_tokenizer


def ensure_model_loaded():
    global model, tokenizer
    if model is None or tokenizer is None:
        model, tokenizer = load_model()
    return model, tokenizer


def unload_model(loaded_model, loaded_tokenizer):
    start = time.perf_counter()
    del loaded_model
    del loaded_tokenizer
    gc.collect()
    mx.clear_cache()
    end = time.perf_counter()
    print(f"Unload time: {end - start:.2f} seconds")


def unload_current_model():
    global model, tokenizer
    if model is None or tokenizer is None:
        return
    unload_model(model, tokenizer)
    model = None
    tokenizer = None


def _stream_response(loaded_model, loaded_tokenizer, formatted_prompt, max_tokens):
    print()
    response = ""
    started_response = False

    for chunk in stream_generate(
        loaded_model,
        loaded_tokenizer,
        prompt=formatted_prompt,
        max_tokens=max_tokens,
    ):
        if "<|im_end|>" in chunk.text:
            break
        if not started_response:
            started_response = True
            if not chunk.text.lstrip().startswith("<think>"):
                print("<think>", end="", flush=True)
                response += "<think>"
        print(chunk.text, end="", flush=True)
        response += chunk.text

    print()
    return response


def run_messages(messages, max_tokens=5000):
    loaded_model, loaded_tokenizer = ensure_model_loaded()
    formatted_prompt = loaded_tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    return _stream_response(loaded_model, loaded_tokenizer, formatted_prompt, max_tokens)


def run(prompt, max_tokens=5000):
    messages = [{"role": "user", "content": prompt}]
    return run_messages(messages, max_tokens=max_tokens)
