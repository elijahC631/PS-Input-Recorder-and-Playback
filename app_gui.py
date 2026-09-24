import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pygame

from input_state import InputState
from recorder import InputRecorder
from playback_engine import PlaybackEngine

# Controls Graphical Interface
class PSControllerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PlayStation Input Recorder & Virtual Playback")
        self.geometry("640x520")
        self.minsize(580, 480)
        self.configure(bg="#1e1e24")

        # Initializes Subsystem Modules
        pygame.init()
        pygame.joystick.init()
        self.joystick = None
        self.input_state = None
        self.recorder = InputRecorder()
        self.playback_engine = PlaybackEngine()

        # Configures Initial Parameters
        self.recording_active = False
        self.recording_thread = None
        self.current_file_path = os.path.join(os.getcwd(), "recording.json")

        self._build_style()
        self._build_widgets()
        self._init_controller()

        # Schedules Connection Checks
        self.after(500, self._poll_controller_status)

    # Configures Interface Theme
    def _build_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        
        self.style.configure("TFrame", background="#1e1e24")
        self.style.configure("Card.TFrame", background="#2b2b36", relief="flat")
        self.style.configure("TLabel", background="#1e1e24", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background="#2b2b36", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background="#1e1e24", foreground="#61afef", font=("Segoe UI", 16, "bold"))
        self.style.configure("Status.TLabel", background="#2b2b36", foreground="#98c379", font=("Segoe UI", 10, "bold"))
        
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#3a3f4b", foreground="#ffffff")
        self.style.map("Primary.TButton", background=[("active", "#4b5263")])

    # Constructs Visual Layout
    def _build_widgets(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="DualShock 4 Virtual Controller Studio", style="Header.TLabel").pack(anchor="w", pady=(0, 15))

        # Renders Controller Details
        dev_card = ttk.Frame(container, style="Card.TFrame", padding=15)
        dev_card.pack(fill="x", pady=(0, 15))
        
        ttk.Label(dev_card, text="Hardware Controller:", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        self.lbl_device_name = ttk.Label(dev_card, text="Scanning...", style="Status.TLabel")
        self.lbl_device_name.grid(row=0, column=1, sticky="w", padx=(10, 0))

        ttk.Label(dev_card, text="Active File:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.lbl_active_file = ttk.Label(dev_card, text=os.path.basename(self.current_file_path), style="Card.TLabel", foreground="#e5c07b")
        self.lbl_active_file.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(5, 0))

        # Renders Control Buttons
        action_card = ttk.Frame(container, style="Card.TFrame", padding=15)
        action_card.pack(fill="x", pady=(0, 15))

        self.btn_record = tk.Button(
            action_card, text="Start Recording", bg="#98c379", fg="#1e1e24",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6,
            command=self._toggle_recording
        )
        self.btn_record.grid(row=0, column=0, padx=(0, 10))

        self.btn_play = tk.Button(
            action_card, text="Play Virtual DS4", bg="#61afef", fg="#1e1e24",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6,
            command=self._start_playback
        )
        self.btn_play.grid(row=0, column=1, padx=(0, 10))

        self.btn_stop_play = tk.Button(
            action_card, text="Stop Playback", bg="#e06c75", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6,
            state="disabled", command=self._stop_playback
        )
        self.btn_stop_play.grid(row=0, column=2, padx=(0, 10))

        btn_select_file = tk.Button(
            action_card, text="Browse File...", bg="#3a3f4b", fg="#ffffff",
            font=("Segoe UI", 10), relief="flat", padx=10, pady=6,
            command=self._browse_file
        )
        btn_select_file.grid(row=0, column=3)

        # Renders Telemetry Panel
        telemetry_card = ttk.Frame(container, style="Card.TFrame", padding=15)
        telemetry_card.pack(fill="both", expand=True)

        self.lbl_telemetry = ttk.Label(telemetry_card, text="System Ready.", style="Card.TLabel")
        self.lbl_telemetry.pack(anchor="w", pady=(0, 10))

        self.progress_bar = ttk.Progressbar(telemetry_card, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 10))

        self.lbl_frame_counter = ttk.Label(telemetry_card, text="Recorded Frames: 0", style="Card.TLabel")
        self.lbl_frame_counter.pack(anchor="w")

    # Connects Physical Controller
    def _init_controller(self):
        pygame.joystick.quit()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        if count > 0:
            target_idx = 0
            for i in range(count):
                js = pygame.joystick.Joystick(i)
                js.init()
                name = js.get_name().lower()
                if "virtual" not in name and "nefarius" not in name and "vigem" not in name:
                    target_idx = i
                    break

            self.joystick = pygame.joystick.Joystick(target_idx)
            self.joystick.init()
            self.input_state = InputState(self.joystick)
            self.lbl_device_name.config(text=f"{self.joystick.get_name()}", foreground="#98c379")
        else:
            self.joystick = None
            self.input_state = None
            self.lbl_device_name.config(text="No controller detected", foreground="#e06c75")

    # Monitors Hotplug Events
    def _poll_controller_status(self):
        if not self.recording_active:
            count = pygame.joystick.get_count()
            if count == 0 and self.joystick is not None:
                self._init_controller()
            elif count > 0 and self.joystick is None:
                self._init_controller()
        self.after(1000, self._poll_controller_status)

    # Toggles Capture Session
    def _toggle_recording(self):
        if not self.recording_active:
            if not self.joystick:
                messagebox.showwarning("Warning", "Cannot record: No physical controller connected.")
                return

            self.recording_active = True
            self.recorder.start()
            self.btn_record.config(text="Stop & Save", bg="#e06c75", fg="#ffffff")
            self.btn_play.config(state="disabled")
            self.lbl_telemetry.config(text="Recording controller inputs (~120Hz)...")

            self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.recording_thread.start()
            self._update_recorder_ui()
        else:
            self.recording_active = False
            saved_count = self.recorder.save(self.current_file_path)
            self.btn_record.config(text="Start Recording", bg="#98c379", fg="#1e1e24")
            self.btn_play.config(state="normal")
            self.lbl_telemetry.config(text=f"Recording saved: {saved_count} frames written.")
            self.lbl_frame_counter.config(text=f"Recorded Frames: {saved_count}")

    # Runs Polling Loop
    def _record_loop(self):
        while self.recording_active:
            if self.input_state:
                self.input_state.update()
                self.recorder.record(self.input_state.snapshot())
            time.sleep(0.008)

    # Refreshes Frame Counter
    def _update_recorder_ui(self):
        if self.recording_active:
            frames = self.recorder.get_frame_count()
            self.lbl_frame_counter.config(text=f"Recording Frames: {frames}")
            self.after(100, self._update_recorder_ui)

    # Initiates Playback Run
    def _start_playback(self):
        if not os.path.exists(self.current_file_path):
            messagebox.showerror("Error", f"File not found: {self.current_file_path}")
            return

        self.btn_play.config(state="disabled")
        self.btn_record.config(state="disabled")
        self.btn_stop_play.config(state="normal")
        self.lbl_telemetry.config(text="Replaying inputs to Virtual DualShock 4...")

        self.playback_engine.play_file(
            self.current_file_path,
            progress_callback=self._on_playback_progress,
            finished_callback=self._on_playback_finished
        )

    # Halts Virtual Replay
    def _stop_playback(self):
        self.playback_engine.stop()
        self.lbl_telemetry.config(text="Stopping virtual playback...")

    # Dispatches Progress Signal
    def _on_playback_progress(self, current, total):
        self.after(0, lambda: self._apply_progress(current, total))

    # Updates Progress Display
    def _apply_progress(self, current, total):
        self.progress_bar["maximum"] = total
        self.progress_bar["value"] = current
        self.lbl_frame_counter.config(text=f"Replaying Frame: {current} / {total}")

    # Dispatches Completion Signal
    def _on_playback_finished(self, success, message):
        self.after(0, lambda: self._reset_playback_ui(success, message))

    # Resets Window Controls
    def _reset_playback_ui(self, success, message):
        self.btn_play.config(state="normal")
        self.btn_record.config(state="normal")
        self.btn_stop_play.config(state="disabled")
        self.progress_bar["value"] = 0
        self.lbl_telemetry.config(text=message)
        if not success:
            messagebox.showerror("Playback Status", message)

    # Selects Storage Destination
    def _browse_file(self):
        chosen = filedialog.askopenfilename(
            title="Select Recording JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir=os.getcwd()
        )
        if chosen:
            self.current_file_path = chosen
            self.lbl_active_file.config(text=os.path.basename(chosen))

# Launches Desktop Program
if __name__ == "__main__":
    app = PSControllerApp()
    app.mainloop()