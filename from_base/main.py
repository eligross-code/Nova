from pynput import keyboard
import subprocess
import gc
import mlx.core as mx
from mlx_lm import load, stream_generate
import time
import threading
import use_model
from use_model import load_model, unload_model, run
from live_activation import get_next_prompt

def main():
    while True:
        start = time.perf_counter()
        print("Listening...")
        
        # Block until trigger detected
        get_next_prompt(trigger_only=True)

        ### need some sort of trigger indicator to see when to load the model...
        # Phase 2: start loading model in background IMMEDIATELY
        model_container = {}
        load_done = threading.Event()

        def load_in_background():
            model_container["model"], model_container["tokenizer"] = load_model()
            # inject into use_model's globals so run() can find them
            use_model.model = model_container["model"]
            use_model.tokenizer = model_container["tokenizer"]
            load_done.set()  # signal that loading is complete

        loader = threading.Thread(target=load_in_background, daemon=True)
        loader.start()

        ### this still waits for model to load -->> slow. Ideally, we would want to load the model in the background as soon as trigger is detected, and then be ready to go by the time user finishes typing prompt.
        prompt = get_next_prompt(capture_only=True)

        if not load_done.is_set():
            print("Loading model, please wait...")
            load_done.wait()

        ### run result
        run(prompt)

        ### strategically unload the model for efficent resource use

        if start - time.perf_counter() > 60:
            unload_model(model_container["model"], model_container["tokenizer"])

main()