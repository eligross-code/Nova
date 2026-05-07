import queue
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_MS = 80
BLOCKSIZE = int(SAMPLE_RATE * BLOCK_MS / 1000)  # 1280 samples

audio_q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status)
    audio_q.put(indata.copy())

print("Available audio devices:")
print(sd.query_devices())

print("\nOpening microphone stream...")
with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="int16",
    blocksize=BLOCKSIZE,
    callback=callback,
):
    print("Mic is live. Speak into it. Press Ctrl+C to stop.\n")
    while True:
        chunk = audio_q.get()              # shape: (frames, channels)
        mono = chunk[:, 0].astype(np.int16)
        rms = np.sqrt(np.mean(mono.astype(np.float32) ** 2))
        peak = np.max(np.abs(mono))



        print(f"RMS={rms:8.1f}  PEAK={peak:6d}", end="\r")