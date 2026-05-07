import threading
import time

from moonshine_voice import (
    MicTranscriber,
    TranscriptEventListener,
    get_model_for_language,
)

class JarvisListener(TranscriptEventListener):
    def __init__(self):
        self.partial = ""
        self.final = ""
        self.error = None

        self._done = threading.Event()
        self._lock = threading.Lock()
        self._last_activity = None
        self._line_active = False

    def on_line_started(self, event):
        with self._lock:
            self._line_active = True
            self._last_activity = time.monotonic()

    def on_line_updated(self, event):
        # Track any activity on the current line so silence timing
        # is based on speech activity, not only text changes.
        with self._lock:
            self._line_active = True
            self._last_activity = time.monotonic()

    def on_line_text_changed(self, event):
        text = event.line.text.strip()
        if text:
            with self._lock:
                self.partial = text
            print(f"\r{text}", end="", flush=True)

    def on_line_completed(self, event):
        text = event.line.text.strip()
        with self._lock:
            self.final = text
            self.partial = text
            self._line_active = False
            self._last_activity = time.monotonic()

        # Print completed line cleanly
        print(f"\r{text}")
        self._done.set()

    def on_error(self, event):
        self.error = event.error
        self._done.set()

    def should_force_finalize(self, silence_sec: float) -> bool:
        with self._lock:
            if not self._line_active:
                return False
            if self._last_activity is None:
                return False
            return (time.monotonic() - self._last_activity) >= silence_sec

def transcribe_once(silence_sec: float = 2, update_interval: float = 0.1) -> str:
    model_path, model_arch = get_model_for_language("en")

    listener = JarvisListener()
    mic = MicTranscriber(
        model_path=model_path,
        model_arch=model_arch,
        update_interval=update_interval,
    )
    mic.add_listener(listener)

    stopped = False
    try:
        mic.start()
        print("Listening...", flush=True)

        while not listener._done.is_set():
            # If we already have an active utterance and it has gone quiet
            # for silence_sec, force Moonshine to finalize it.
            if listener.should_force_finalize(silence_sec):
                mic.stop()   # triggers on_line_completed for active line
                stopped = True
                break

            time.sleep(0.02)

        # Give the completion callback a moment to land after stop()
        listener._done.wait(timeout=1.0)

        if listener.error:
            raise RuntimeError(f"Moonshine transcription error: {listener.error}")

        return listener.final or listener.partial

    finally:
        if not stopped:
            try:
                mic.stop()
            except Exception:
                pass
        if getattr(mic, "_sd_stream", None) is not None:
            mic._sd_stream.stop()
            mic._sd_stream.close()
            mic._sd_stream = None
        mic.close()
        time.sleep(0.1)
        print(flush=True)


if __name__ == "__main__":
    text = transcribe_once(silence_sec=2, update_interval=0.05)
    print(f"FINAL: {text}")
