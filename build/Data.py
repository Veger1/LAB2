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

    def get_number_live_data(self):
        return len(self.live_data)

    def remove_associated_data(self, widget):
        name = widget.name

        # Remove dataset from self.data
        if name in self.data:
            del self.data[name]

        # Destroy the widget and remove self.datasets
        self.datasets.remove(widget)

        # Cleanup associated variables
        del self.plot_vars[name]
        del self.trend_vars[name]
        del self.offset_entry[name]
        del self.save_vars[name]

    def add_data(self):  # Add the data to the data dictionary, each name has an original dataset along with a 'None'
        # filtered set
        if self.get_live_data():
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

            self.data[name] = {'original': (list(x_data), list(y_data)), 'filtered': None,
                               'extended': None, 'detrended': None, 'coefficients': None}
            self.extend_data(name)
            self.remove_trend(name)
            return name
        return None

    def update_filter(self, name, cutoff_freq):  # Update the filter frequency for a dataset. Function is called when
        # slider is unclicked
        if cutoff_freq <= 0:
            self.data[name]['filtered'] = None
            return
        x, y = self.data[name]['original']
        dft = np.fft.fft(y)
        dft_filtered = dft.copy()
        dft_filtered[cutoff_freq:len(dft) - cutoff_freq] = 0
        y_filtered = np.real(np.fft.ifft(dft_filtered))
        self.data[name]['filtered'] = (x, y_filtered)

    def save_data(self):  # Save the data whose 'save' checkbox is checked.
        selected_data = {name: self.data[name] for name, var in self.save_vars.items() if var.get()}
        if not selected_data:
            messagebox.showwarning("Warning", "No data selected!")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return

        with open(save_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for name, datasets in selected_data.items():
                x_orig, y_orig = datasets['original']
                writer.writerow([name, 'X'] + x_orig)
                writer.writerow([name, 'Y'] + y_orig)

                # Check if 'filtered' key exists and save it if present
                if 'filtered' in datasets and datasets['filtered']:
                    x_filt, y_filt = datasets['filtered']
                    writer.writerow([name, 'Filtered_X'] + x_filt)
                    writer.writerow([name, 'Filtered_Y'] + y_filt)

        messagebox.showinfo("Success", "Data saved successfully!")

    def extend_data(self, name):  # Extend the data to a uniform x-axis (1mm increments)
        if name in self.data:
            if self.data[name]['extended'] is not None:
                return
            x_data = np.array(self.data[name]['original'][0])
            y_data = np.array(self.data[name]['original'][1])
            unique_x_data = np.unique(x_data)  # We do this to remove duplicate x values since interpolation will fail
            compressed_x_data = unique_x_data
            compressed_y_data = [np.mean(y_data[np.isclose(x_data, x ,atol=1e-5)]) for x in unique_x_data]
            new_x_data = np.arange(min(compressed_x_data), max(compressed_x_data) + 0.001, 0.001)
            new_y_data = np.interp(new_x_data, compressed_x_data, compressed_y_data)
            self.data[name]['extended'] = (new_x_data, new_y_data)

    def calc_reference(self, new_data):
        name = self.gui.get_reference()
        if name not in self.data or 'extended' not in self.data[name]:
            return
        ref_x, ref_y = self.data[name]['extended']
        x, y = new_data

        index = np.where(np.isclose(ref_x, x, atol=1e-5))[0]
        if len(index) == 0:
            return
        ref_y_val = ref_y[index[0]]
        return (x, y - ref_y_val)

    def remove_trend(self, name):
        if name in self.data:
            if self.data[name]['extended'] is None:
                self.extend_data(name)

            a, b = self.calc_trend(name)  # We do not check if 'extended' is None since it is checked in calc_trend
            if a is not None:
                x_data, y_data = self.data[name]['extended']
                y_data -= a * x_data + b
                self.data[name]['detrended'] = (x_data, y_data)
                self.data[name]['coefficients'] = (a, b)

    def calc_trend(self, name):
        if name in self.data:
            if self.data[name]['extended'] is None:
                self.extend_data(name)
            x_data = np.array(self.data[name]['extended'][0])
            y_data = np.array(self.data[name]['extended'][1])
            a, b = np.polyfit(x_data, y_data, 1)
            return a, b
        return None, None


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
                    loaded_data[name] = {'original': [[], []], 'filtered': None,
                                         'extended': None, 'detrended': None, 'coefficients': None}
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
                loaded_data[name]['extended'] = None
                loaded_data[name]['detrended'] = None
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
            self.extend_data(name)
            self.remove_trend(name)

        messagebox.showinfo("Success", "Data loaded successfully!")