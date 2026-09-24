import time
import json
import threading

# Records Input Stream
class InputRecorder:
    def __init__(self):
        self.start_time = None
        self.frames = []
        self._lock = threading.Lock()

    # Starts Clock Timer
    def start(self):
        with self._lock:
            self.start_time = time.perf_counter()
            self.frames = []

    # Appends Timestamped Frame
    def record(self, snapshot):
        with self._lock:
            if self.start_time is None:
                return

            timestamp = time.perf_counter() - self.start_time
            self.frames.append({
                "t": round(timestamp, 6),
                "buttons": snapshot["buttons"],
                "axes": snapshot["axes"]
            })

    # Returns Total Frames
    def get_frame_count(self):
        with self._lock:
            return len(self.frames)

    # Writes To Disk
    def save(self, filename="recording.json"):
        with self._lock:
            data = list(self.frames)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return len(data)