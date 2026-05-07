import queue
import time
import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_MS = 80
BLOCKSIZE = int(SAMPLE_RATE * BLOCK_MS / 1000)
THRESHOLD = 0.5
COOLDOWN_SEC = 1.5

audio_q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status)
    audio_q.put(indata.copy())

# Load once at module level
openwakeword.utils.download_models()
model = Model(vad_threshold=0.5)
model_names = list(model.models.keys())

def find_jarvis_key(keys):
    for k in keys:
        if "jarvis" in k.lower().replace("_", " ").strip():
            return k
    return None

jarvis_key = find_jarvis_key(model_names)
if jarvis_key is None:
    raise RuntimeError(f"Couldn't find a Jarvis model in: {model_names}")

print(f"Using wake word model: {jarvis_key}")


def is_awake() -> bool:
    """Blocks until 'hey jarvis' is detected, then returns True."""
    last_trigger_time = 0.0

    # Clear any stale audio in the queue before listening
    while not audio_q.empty():
        audio_q.get_nowait()

    print("Listening for 'hey Jarvis'...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=BLOCKSIZE,
        callback=callback,
    ):
        while True:
            chunk = audio_q.get()
            mono = chunk[:, 0].astype(np.int16)
            score = float(model.predict(mono).get(jarvis_key, 0.0))
            print(f"{jarvis_key}: {score:.3f}", end="\r")

            now = time.time()
            if score >= THRESHOLD and (now - last_trigger_time) > COOLDOWN_SEC:
                last_trigger_time = now
                print(f"\nWake word detected! ({score:.3f})\n")
                return True  # stream closes cleanly when `with` block exits
