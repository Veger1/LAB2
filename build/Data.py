import csv
from queue import Queue
from tkinter import simpledialog, messagebox, filedialog

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

    def extend_data(self, name):
        if name in self.data:
            x_data = self.data[name]['original'][0]
            y_data = self.data[name]['filtered'][1]
            new_x_data = np.arange(min(x_data), max(x_data) + 0.001, 0.001)
            new_y_data = np.interp(new_x_data, x_data, y_data)
            self.data[name]['extended'] = (new_x_data, new_y_data)

    def load_data(self):
        load_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not load_path:
            return

        with open(load_path, 'r') as f:
            reader = csv.reader(f)
            loaded_data = {}
            for row in reader:
                if len(row) < 3:
                    continue
                name = row[0]
                if name not in loaded_data:
                    loaded_data[name] = {'original': [[], []], 'filtered': None}
                if row[1] == 'X':
                    loaded_data[name]['original'][0] = list(map(float, row[2:]))
                elif row[1] == 'Y':
                    loaded_data[name]['original'][1] = list(map(float, row[2:]))
                elif row[1] == 'Filtered_X':
                    if loaded_data[name]['filtered'] is None:
                        loaded_data[name]['filtered'] = [[], []]
                    loaded_data[name]['filtered'][0] = list(map(float, row[2:]))
                elif row[1] == 'Filtered_Y':
                    if loaded_data[name]['filtered'] is None:
                        loaded_data[name]['filtered'] = [[], []]
                    loaded_data[name]['filtered'][1] = list(map(float, row[2:]))

        for name, datasets in loaded_data.items():
            if name in self.data:
                # Keep prompting until a valid name is provided or the user cancels
                while True:
                    # Pass the parent window to the dialog
                    new_name = simpledialog.askstring("Input", f"Name {name} already exists! Enter a new name:",
                                                      parent=self.root)

                    # Handle case when dialog is canceled or closed
                    if new_name is None:
                        messagebox.showwarning("Warning", f"Dataset {name} was not loaded.")
                        break  # Exit the loop and continue with the next item

                    # Check for duplicate or empty input
                    if new_name in self.data or not new_name.strip():
                        messagebox.showwarning("Warning", f"Invalid input. Please enter a unique name.")
                        continue  # Prompt again for valid input

                    name = new_name  # Assign the new valid name
                    self.data[name] = datasets
                    self.gui.add_checkbox(name)
                    break
            else:  # If no duplicate name is found, add the dataset
                self.data[name] = datasets
                self.gui.add_checkbox(name)

        messagebox.showinfo("Success", "Data loaded successfully!")