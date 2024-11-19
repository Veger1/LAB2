from queue import Queue
from tkinter import simpledialog, messagebox

import numpy as np

class Data:
    def __init__(self):
        self.queue = Queue()
        self.gui = None
        self.live_data = []
        self.data = {}
        self.plot_vars = {}
        self.trend_vars = {}
        self.offset_vars = {}
        self.offset_entry = {}
        self.save_vars = {}
        self.datasets = []

    def set_gui(self, gui):
        self.gui = gui

    def clear_live_data(self):
        self.live_data = []

    def clear_data(self):
        pass

    def get_data(self):
        return self.data

    def get_live_data(self):
        return self.live_data

    def add_data(self):  # Add the data to the data dictionary, each name has an original dataset along with a 'None'
        # filtered set
        if self.get_data():
            name = simpledialog.askstring("Input", "Enter measurement name:")
            if not name:
                return None

            if name in self.data:
                messagebox.showerror("Error", "Name already exists!")
                return None

            x_data, y_data = zip(*self.get_live_data())
            # x_data = np.linspace(0, 10, 100)
            # y_data = np.sin(x_data) + np.random.normal(0, 0.1, x_data.shape)  # Sine wave with noise
            # Used to test filtering

            self.data[name] = {'original': (list(x_data), list(y_data)), 'filtered': None}
            return name
        return None

    def update_filter(self, name, cutoff_freq):  # Update the filter frequency for a dataset. Function is called when
        # slider is unclicked
        if cutoff_freq == 0:
            self.data[name]['filtered'] = None
            return
        x, y = self.data[name]['original']
        dft = np.fft.fft(y)
        dft_filtered = dft.copy()
        dft_filtered[cutoff_freq:len(dft) - cutoff_freq] = 0
        y_filtered = np.real(np.fft.ifft(dft_filtered))
        self.data[name]['filtered'] = (x, y_filtered)