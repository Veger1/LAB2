# settings_tab.py
import tkinter as tk
from tkinter import ttk

class StoreSettings:
    def __init__(self, root):
        self.root = root
        self.fig_size = (10, 6)

    def open_store_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")

        checkbutton1 = ttk.Checkbutton(settings_window, text="Option 1")
        checkbutton1.grid(row=0, column=0, padx=5, pady=5)
        checkbutton2 = ttk.Checkbutton(settings_window, text="Option 2")
        checkbutton2.grid(row=1, column=0, padx=5, pady=5)

        entry1 = ttk.Entry(settings_window)
        entry1.grid(row=0, column=1, padx=5, pady=5)
        entry2 = ttk.Entry(settings_window)
        entry2.grid(row=1, column=1, padx=5, pady=5)

        close_button = ttk.Button(settings_window, text="Close", command=settings_window.destroy)
        close_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

class SettingsTab:
    def __init__(self, notebook,gui):
        self.gui = gui
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Settings")
        self.selected_var = tk.IntVar(value=1)
        self.create_widgets()
        self.active_sensor = "laser"

    def create_widgets(self):
        settings_label = ttk.Label(self.frame, text="Settings Options", font=("Arial", 14))
        settings_label.pack(pady=20)

        options = ["Laser", "Digital Incremental", "Analog Incremental","Demo"]
        for idx, option in enumerate(options, start=1):
            checkbox = ttk.Checkbutton(self.frame, text=option, variable=self.selected_var,
                                       onvalue=idx, offvalue=0, command=self.on_checkbox_select)
            checkbox.pack(pady=20)
    def on_checkbox_select(self):
        if self.selected_var.get() == 1:
            self.handle_laser()
        elif self.selected_var.get() == 2:
            self.handle_digital_incremental()
        elif self.selected_var.get() == 3:
           self.handle_analog_incremental()
        elif self.selected_var.get() == 4:
            self.handle_demo()

    """ Functions can be combined into one function with a parameter to determine the sensor type"""
    def handle_laser(self):
        if self.gui.sampler.sampling:
            self.gui.stop_sampling()
        self.gui.root.after(100, self.switch_distance_sensor(sensor="laser"))

    def handle_digital_incremental(self):
        if self.gui.sampler.sampling:
            self.gui.stop_sampling()
        self.gui.root.after(100, self.switch_distance_sensor(sensor="digital"))

    def handle_analog_incremental(self):
        if self.gui.sampler.sampling:
            self.gui.stop_sampling()
        self.gui.root.after(100, self.switch_distance_sensor(sensor="analog"))

    def handle_demo(self):
        if self.gui.sampler.sampling:
            self.gui.stop_sampling()
        self.switch_distance_sensor(sensor="demo")

    def switch_distance_sensor(self,sensor):
        if not self.gui.sampler.is_connected():
            if sensor == "demo":
                self.active_sensor = sensor
                self.gui.start_button.config(state=tk.NORMAL)
            elif sensor == "laser":
                print("Not connected, will initialize as laser")
                self.gui.start_button.config(state=tk.DISABLED)
            else:
                self.gui.start_button.config(state=tk.DISABLED)
                self.selected_var.set(1)
        else:

            self.gui.sampler.set_mode(sensor)
            self.active_sensor = sensor
            print(f"Sensor switched to {sensor}")
