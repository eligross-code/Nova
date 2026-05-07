import gc
import mlx.core as mx
from mlx_lm import load, stream_generate
import time

MODEL_PATH = "/Users/eligross/models/Qwen3.5-4B-merged-mlx-4bit"

def load_model():
    print("Starting up...")
    start = time.perf_counter()
    model, tokenizer = load(MODEL_PATH)
    end = time.perf_counter()
    total = end - start
    print(f"Startup time: {total:.2f} seconds")
    return model, tokenizer





def unload_model(model, tokenizer):
    start = time.perf_counter()
    del model
    del tokenizer
    gc.collect()
    mx.clear_cache()    
    end = time.perf_counter()
    print(f"Unload time: {end - start:.2f} seconds")


model, tokenizer = load_model()


def run(prompt, max_tokens=5000):
    
    messages = [{"role": "user", "content": prompt}]
    
    formatted_prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    print()
    response = ""
    for chunk in stream_generate(model, tokenizer, prompt=formatted_prompt, max_tokens=max_tokens):
        if "<|im_end|>" in chunk.text:
            break
        print(chunk.text, end="", flush=True)
        response += chunk.text
    print()
    return response


unload_model(model, tokenizer)
model = None
tokenizer = None