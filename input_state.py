import pygame

DEADZONE = 0.15

BUTTON_MAP = {
    "X": 0,
    "CIRCLE": 1,
    "SQUARE": 2,
    "TRIANGLE": 3,
    "SHARE": 4,
    "PS": 5,
    "OPTIONS": 6,
    "L3": 7,
    "R3": 8,
    "L1": 9,
    "R1": 10,
    "DPAD_UP": 11,
    "DPAD_DOWN": 12,
    "DPAD_LEFT": 13,
    "DPAD_RIGHT": 14,
    "TOUCHPAD": 15,
    "MUTE": 16,
}

AXIS_MAP = {
    "LX": 0,
    "LY": 1,
    "RX": 2,
    "RY": 3,
    "L2": 4,
    "R2": 5,
}

# Filters Small Inputs
def apply_deadzone(value, dz=DEADZONE):
    return 0.0 if abs(value) < dz else round(value, 3)

# Normalizes Trigger Range
def normalize_trigger(value):
    norm = (value + 1.0) / 2.0
    return round(max(0.0, min(1.0, norm)), 3)


# Tracks Controller State
class InputState:
    def __init__(self, joystick):
        self.js = joystick
        self.buttons = {}
        self.axes = {}

    # Reads Hardware Inputs
    def update(self):
        pygame.event.pump()
        num_buttons = self.js.get_numbuttons()

        # Reads Digital Buttons
        for name, idx in BUTTON_MAP.items():
            if idx < num_buttons:
                self.buttons[name] = bool(self.js.get_button(idx))
            else:
                self.buttons[name] = False

        # Maps Directional Pad
        if self.js.get_numhats() > 0:
            hat_x, hat_y = self.js.get_hat(0)
            self.buttons["DPAD_UP"] = self.buttons.get("DPAD_UP") or (hat_y == 1)
            self.buttons["DPAD_DOWN"] = self.buttons.get("DPAD_DOWN") or (hat_y == -1)
            self.buttons["DPAD_LEFT"] = self.buttons.get("DPAD_LEFT") or (hat_x == -1)
            self.buttons["DPAD_RIGHT"] = self.buttons.get("DPAD_RIGHT") or (hat_x == 1)

        # Reads Analog Axes
        num_axes = self.js.get_numaxes()
        for name, idx in AXIS_MAP.items():
            if idx < num_axes:
                raw_val = self.js.get_axis(idx)
                if name in ("LY", "RY"):
                    self.axes[name] = apply_deadzone(raw_val * -1)
                elif name in ("L2", "R2"):
                    self.axes[name] = normalize_trigger(raw_val)
                else:
                    self.axes[name] = apply_deadzone(raw_val)
            else:
                self.axes[name] = 0.0

    # Exports State Copy
    def snapshot(self):
        return {
            "buttons": self.buttons.copy(),
            "axes": self.axes.copy()
        }