import json
import time
import threading
import vgamepad as vg

BUTTON_MAP = {
    "X": vg.DS4_BUTTONS.DS4_BUTTON_CROSS,
    "CIRCLE": vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,
    "SQUARE": vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,
    "TRIANGLE": vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,
    "L1": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,
    "R1": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT,
    "OPTIONS": vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,
    "SHARE": vg.DS4_BUTTONS.DS4_BUTTON_SHARE,
    "L3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT,
    "R3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,
}

SPECIAL_BUTTON_MAP = {
    "PS": vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS,
    "TOUCHPAD": vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD,
}

# Converts Stick Range
def stick_float_to_ds4_byte(value, invert_y=False):
    clamped = max(-1.0, min(1.0, float(value)))
    if invert_y:
        clamped = -clamped
    byte_val = int(round(((clamped + 1.0) / 2.0) * 255))
    return max(0, min(255, byte_val))

# Converts Trigger Range
def trigger_float_to_int(value):
    value = max(0.0, min(1.0, value))
    return int(value * 255)

# Resolves Directional State
def resolve_dpad_direction(buttons):
    u = buttons.get("DPAD_UP", False)
    d = buttons.get("DPAD_DOWN", False)
    l = buttons.get("DPAD_LEFT", False)
    r = buttons.get("DPAD_RIGHT", False)

    if u and r: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
    if u and l: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
    if d and r: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
    if d and l: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
    if u: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
    if d: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
    if l: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
    if r: return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
    return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE

# Synchronizes Frame Delay
def precise_sleep_until(target_time):
    while True:
        remaining = target_time - time.perf_counter()
        if remaining <= 0:
            break
        if remaining > 0.002:
            time.sleep(remaining - 0.001)


# Manages Virtual Playback
class PlaybackEngine:
    def __init__(self):
        self._is_playing = False
        self._stop_requested = threading.Event()
        self.gamepad = None

    # Starts Playback Thread
    def play_file(self, filename, progress_callback=None, finished_callback=None):
        thread = threading.Thread(
            target=self._run_playback,
            args=(filename, progress_callback, finished_callback),
            daemon=True
        )
        thread.start()
        return thread

    # Requests Playback Stop
    def stop(self):
        self._stop_requested.set()

    # Replays Virtual Frames
    def _run_playback(self, filename, progress_callback, finished_callback):
        self._is_playing = True
        self._stop_requested.clear()

        # Loads Recording File
        try:
            with open(filename, "r", encoding="utf-8") as f:
                frames = json.load(f)
        except Exception as err:
            self._is_playing = False
            if finished_callback:
                finished_callback(False, f"Load Error: {err}")
            return

        # Connects Virtual Device
        if not self.gamepad:
            self.gamepad = vg.VDS4Gamepad()

        total_frames = len(frames)
        start_time = time.perf_counter()
        last_buttons = {}
        last_special = {}

        try:
            for idx, frame in enumerate(frames):
                if self._stop_requested.is_set():
                    break

                # Delays Frame Output
                target_t = start_time + frame["t"]
                precise_sleep_until(target_t)

                buttons = frame["buttons"]
                axes = frame["axes"]

                # Applies Digital Buttons
                for name, btn_enum in BUTTON_MAP.items():
                    state = buttons.get(name, False)
                    prev = last_buttons.get(name, False)
                    if state and not prev:
                        self.gamepad.press_button(btn_enum)
                    elif not state and prev:
                        self.gamepad.release_button(btn_enum)
                    last_buttons[name] = state

                # Applies System Buttons
                for name, spec_enum in SPECIAL_BUTTON_MAP.items():
                    state = buttons.get(name, False)
                    prev = last_special.get(name, False)
                    if state and not prev:
                        self.gamepad.press_special_button(spec_enum)
                    elif not state and prev:
                        self.gamepad.release_special_button(spec_enum)
                    last_special[name] = state

                # Applies Directional Pad
                dpad_dir = resolve_dpad_direction(buttons)
                self.gamepad.directional_pad(dpad_dir)

                # Applies Analog Sticks
                self.gamepad.left_joystick(
                    x_value=stick_float_to_ds4_byte(axes.get("LX", 0.0)),
                    y_value=stick_float_to_ds4_byte(axes.get("LY", 0.0), invert_y=True)
                )
                self.gamepad.right_joystick(
                    x_value=stick_float_to_ds4_byte(axes.get("RX", 0.0)),
                    y_value=stick_float_to_ds4_byte(axes.get("RY", 0.0), invert_y=True)
                )

                # Applies Analog Triggers
                self.gamepad.left_trigger(trigger_float_to_int(axes.get("L2", 0.0)))
                self.gamepad.right_trigger(trigger_float_to_int(axes.get("R2", 0.0)))

                # Sends State Report
                self.gamepad.update()

                # Updates Playback Progress
                if progress_callback and idx % 10 == 0:
                    progress_callback(idx + 1, total_frames)

            # Resets Device State
            self.gamepad.reset()
            self.gamepad.update()

            self._is_playing = False
            if finished_callback:
                finished_callback(True, "Playback completed successfully")

        except Exception as ex:
            self._is_playing = False
            if finished_callback:
                finished_callback(False, f"Playback Error: {ex}")