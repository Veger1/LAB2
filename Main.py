import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import numpy as np

from Sampler import Sampler
from Plotter import Plotter
from Report import Report


class MainApp:
    def __init__(self):
        self.root = tk.Tk()
        self.plotter = Plotter(self.root)  # Initialize the plotter
        self.sampler = Sampler(self.plotter)  # Initialize the sampler
        self.report = Report()
        self.gui = GUI(self.root, self.sampler, self.plotter, self.report)  # Initialize the GUI
        self.plotter.set_axes(self.gui.ax1, self.gui.ax2)  # Pass the axes to the plotter
        self.plotter.gui = self.gui  # Pass the GUI instance to the plotter

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def run(self):
        self.gui.show()

    def on_closing(self):  # Ensure the connection is closed before closing the app
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.sampler.sampling:  # Ensure sampling is stopped
                self.sampler.stop_sampling()
            if self.sampler.is_connected:
                self.sampler.disconnect()
            self.root.destroy()
            raise SystemExit


if __name__ == "__main__":
    app = MainApp()
    app.run()


class GUI:
    def __init__(self, window, sampler, plotter, report):
        self.root = window
        self.sampler = sampler
        self.plotter = plotter
        self.report = report
        self.connection_established = False

        self.root.title("Measurement App")

        self.style = ttk.Style()
        self.style.configure('TFrame', background='white')
        # self.style.configure('Disabled.TFrame', background='light gray')
        self.style.configure('TLabelframe', background='white')
        self.style.configure('TLabelframe.Label', background='white')
        # self.style.configure('Disabled.TLabelframe', background='light gray')
        self.style.configure('TCheckbutton', background='white')
        # self.style.configure('TFrame.Label', background='green')

        self.data = {}
        self.plot_vars = {}
        self.trend_vars = {}
        self.offset_vars = {}
        self.offset_entry = {}
        self.save_vars = {}
        self.datasets = []

        # Tkinter works with 'frames' which are containers for other widgets/frames.These widgets/frames can be
        # arranged using grid or pack geometry managers. The grid manager is used here to arrange the widgets in a
        # grid layout. The pack manager is used to place frames relative to each other.

        self.mainframe = ttk.Frame(self.root, padding="10 10 10 10", borderwidth=2, relief="groove")
        self.mainframe.grid(column=1, row=0, rowspan=2, sticky=tk.NSEW)

        self.plots = ttk.Labelframe(self.mainframe, text="Plot limits", padding="10 10 10 10", borderwidth=2, relief="groove")
        self.plots.grid(column=0, row=2, sticky=tk.NSEW)

        self.measure = ttk.Labelframe(self.mainframe, text="Sample", padding="10 10 10 10", borderwidth=2, relief="groove")
        self.measure.grid(column=0, row=1, sticky=tk.NSEW)

        self.store = ttk.Labelframe(self.mainframe, text="Save", padding="10 10 10 10", borderwidth=2, relief="groove")
        self.store.grid(column=0, row=3, sticky=tk.NSEW)

        self.visual = ttk.Labelframe(self.mainframe, text="Data", padding="10 10 10 10", borderwidth=2, relief="groove")
        self.visual.grid(column=0, row=5, sticky=tk.NSEW)

        self.filtering = ttk.Labelframe(self.mainframe, text="Filter", padding="10 10 10 10", borderwidth=2, relief="groove")
        self.filtering.grid(column=0, row=4, sticky=tk.NSEW)

        self.mainframe.grid_rowconfigure(5, weight=1)  # Make the visual frame expandable

        self.plot_frame1 = ttk.Frame(self.root, borderwidth=2, relief="groove")
        self.plot_frame1.grid(row=0, column=0, sticky=tk.NSEW)

        self.plot_frame2 = ttk.Frame(self.root, borderwidth=2, relief="groove")
        self.plot_frame2.grid(row=1, column=0, sticky=tk.NSEW)

        self.fig1, self.ax1 = plt.subplots()
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.plot_frame1)
        self.canvas1.draw()
        self.canvas1.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.ax1.set_title('Data')

        self.fig2, self.ax2 = plt.subplots()
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.plot_frame2)
        self.canvas2.draw()
        self.canvas2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.ax2.set_title('Saved Data')

        # Variables can be associated with widgets to store data. These variables can be used to store the state
        # of e.g. a button.

        self.manual_limit_var = tk.IntVar(value=0)
        self.manual_limit = ttk.Checkbutton(self.plots, text="Manual", variable=self.manual_limit_var)
        self.manual_limit.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.x_min_entry = ttk.Entry(self.plots, width=8)
        self.x_min_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.x_min_entry.bind("<FocusIn>", self.clear_placeholder)  # Bind the clear_placeholder function to the entry
        self.x_min_entry.bind("<FocusOut>", self.add_placeholder)  # Bind the add_placeholder function to the entry
        self.add_placeholder(event=None, widget=self.x_min_entry, placeholder="min")  # Add a placeholder to the
        # entry during initialization

        self.x_max_entry = ttk.Entry(self.plots, width=8)
        self.x_max_entry.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.x_max_entry.bind("<FocusIn>", self.clear_placeholder)
        self.x_max_entry.bind("<FocusOut>", self.add_placeholder)
        self.add_placeholder(event=None, widget=self.x_max_entry, placeholder="max")

        self.direction_var = tk.BooleanVar(value=False)
        self.toggle_direction = ttk.Checkbutton(self.plots, text="<->", width=3, variable=self.direction_var, command=self.update_flip_orientation)
        self.toggle_direction.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        self.zero_button = ttk.Button(self.plots, text="0", width=3, command=self.zero_measurement)
        self.zero_button.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)

        self.zero_entry = ttk.Entry(self.plots, width=10)
        self.zero_entry.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        self.zero_entry.bind("<FocusOut>", self.clear_zero_point)  # Bind the clear_zero_point function to the entry
        self.clear_zero_point(event=None)  # Clear the zero point entry during initialization

        self.connect_button = ttk.Button(self.measure, text="Connect", command=self.sampler.connect)
        self.connect_button.grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)

        self.start_button = ttk.Button(self.measure, text="Start", command=self.start_sampling)
        self.start_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.stop_button = ttk.Button(self.measure, text="Stop", command=self.stop_sampling, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)

        self.clear_button = ttk.Button(self.measure, text="Clear", command=self.clear_sampler)
        self.clear_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        self.add_data_button = ttk.Button(self.store, text="Add Data", command=self.add_data)
        self.add_data_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.load_data_button = ttk.Button(self.store, text="Load", width=8, command=self.load_data)
        self.load_data_button.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)

        self.save_button = ttk.Button(self.store, text="Save", width=8, command=self.save_data)
        self.save_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        self.plot_button = ttk.Button(self.store, text="Plot", width=8, command=self.plot_data)  # # #
        self.plot_button.grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)

        self.report_button = ttk.Button(self.store, text="Report", width=8, command=self.save_measurement_report)
        self.report_button.grid(row=1, column=5, padx=5, pady=5, sticky=tk.W)

        self.checkbox_frame = ttk.Frame(self.visual)
        self.checkbox_frame.grid(row=1, column=0, sticky=tk.NSEW)

        self.visual.grid_rowconfigure(1, weight=1)

        # Create a canvas and scrollbar to allow scrolling of the frame. A frame by itself cannot be scrolled but a
        # canvas can. So a frame is placed inside a canvas to circumvent this limitation.
        self.canvas = tk.Canvas(self.checkbox_frame, bg='white')
        self.scrollbar = tk.Scrollbar(self.checkbox_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Determines how the widgets are expanded when the window is resized.
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)

        self.header_widget = ttk.Frame(self.visual)
        self.header_widget.grid(column=0, row=0, sticky=tk.NSEW)

        # Configure the column width of the header widget to better match the checkboxes underneath. Since the
        # checkboxes and header widget are different widgets, they size differently.
        self.header_widget.grid_columnconfigure(0, minsize=80)
        self.header_widget.grid_columnconfigure(1, minsize=50)
        self.header_widget.grid_columnconfigure(2, minsize=50)
        self.header_widget.grid_columnconfigure(3, minsize=50)
        self.header_widget.grid_columnconfigure(4, minsize=50)
        self.header_widget.grid_columnconfigure(5, minsize=80)

        self.name_label = ttk.Label(self.header_widget, width=8, text="Name", background='white')
        self.name_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.plot_label = ttk.Label(self.header_widget, width=5, text="Plot", background='white')
        self.plot_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.trend_label = ttk.Label(self.header_widget, width=5, text="Trend", background='white')
        self.trend_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.offset_label = ttk.Label(self.header_widget, width=5, text="Offset", background='white')
        self.offset_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.save_label = ttk.Label(self.header_widget, width=5, text="Save", background='white')
        self.save_label.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.filter_button = ttk.Button(self.filtering, text="Filter", command=self.lowpass)
        self.filter_button.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        # Call here functions that are ran by default
        self.check_connection_status()  # Initialize connection checker

    def clear_placeholder(self, event):  # Clear the placeholder text when the entry is clicked
        if event.widget.get() in ["min", "max"]:
            event.widget.delete(0, tk.END)
            event.widget.config(foreground='black')

    def add_placeholder(self, event, widget=None, placeholder=None):  # Inserts a placeholder text when the entry is
        # empty for visual aid
        if widget is None:
            widget = event.widget
        if not widget.get():
            if placeholder is None:
                placeholder = "min" if widget == self.x_min_entry else "max"
            widget.insert(0, placeholder)
            widget.config(foreground='grey')

    def zero_measurement(self):  # Set the zero point to the current absolute value.
        self.sampler.set_zero_point()
        if self.sampler.data:
            self.zero_entry.delete(0, tk.END)
            self.zero_entry.insert(0, str(self.sampler.last_data))

    def clear_zero_point(self, event):
        if not self.zero_entry.get():
            self.sampler.zero_point = 0
            self.zero_entry.insert(0, '0')
            self.zero_entry.config(foreground='grey')

    def update_flip_orientation(self):  # Flips the orientation of the distance axis
        self.sampler.flip_orientation = self.direction_var.get()

    def check_connection_status(self):  # Check the connection with the arduino once every second, disables core
        # functions if not connected
        if self.sampler.is_connected():
            if not self.connection_established:
                self.start_button.config(state=tk.NORMAL)
                self.connection_established = True
            # self.measure.configure(style='TLabelframe')
        else:
            self.start_button.config(state=tk.DISABLED)
            self.connection_established = False
            # self.measure.configure(style='Disabled.TLabelframe')  # Indicate that there's no connection

        self.root.after(1000, self.check_connection_status)

    def start_sampling(self):
        if self.sampler.is_connected():
            self.sampler.start_sampling()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

    def stop_sampling(self):
        self.sampler.stop_sampling()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def clear_sampler(self):
        self.sampler.clear_data()

    def add_data(self):  # Add the data to the data dictionary, each name has an original dataset along with a 'None'
        # filtered set
        if self.sampler.get_data():
            name = simpledialog.askstring("Input", "Enter measurement name:")
            if not name:
                return

            if name in self.data:
                messagebox.showerror("Error", "Name already exists!")
                return

            x_data, y_data = zip(*self.sampler.get_data())
            # x_data = np.linspace(0, 10, 100)
            # y_data = np.sin(x_data) + np.random.normal(0, 0.1, x_data.shape)  # Sine wave with noise
            # Used to test filtering

            self.data[name] = {'original': (list(x_data), list(y_data)), 'filtered': None}
            self.add_checkbox(name)

    def add_checkbox(self, name):  # To dynamically add datasets to the data frame, each dataset is placed in a frame
        # along with its own checkboxes/entries. Pack manager is used since it is better at stacking widget without
        # having to remember the row/column.

        # Create dataset widget
        widget = tk.Frame(self.scrollable_frame, bg='lightgreen')
        widget.pack(pady=5)
        self.datasets.append(widget)

        # Configure the column width of the dataset widget to better match the header widget.
        widget.grid_columnconfigure(0, minsize=80)
        widget.grid_columnconfigure(1, minsize=50)
        widget.grid_columnconfigure(2, minsize=50)
        widget.grid_columnconfigure(3, minsize=50)
        widget.grid_columnconfigure(4, minsize=50)
        widget.grid_columnconfigure(5, minsize=80)

        # Store the dataset name as an attribute of the widget
        widget.name = name

        # Initialize variables.
        self.plot_vars[name] = tk.BooleanVar()
        self.trend_vars[name] = tk.BooleanVar()
        self.offset_entry[name] = tk.StringVar(value='0')
        self.save_vars[name] = tk.BooleanVar()

        # Add dataset name and buttons
        name_label = ttk.Label(widget, width=8, text=name)
        name_label.grid(row=0, column=0, padx=5, pady=0, sticky="w")

        check = ttk.Checkbutton(widget, width=1, variable=self.plot_vars[name])
        check.grid(row=0, column=1, padx=5, pady=0, sticky="w")

        trend_check = ttk.Checkbutton(widget, width=1, variable=self.trend_vars[name])
        trend_check.grid(row=0, column=2, padx=5, pady=0, sticky="w")

        offset_entry = ttk.Entry(widget, width=5, textvariable=self.offset_entry[name])
        offset_entry.grid(row=0, column=3, padx=5, pady=0, sticky="w")

        save_check = ttk.Checkbutton(widget, width=1, variable=self.save_vars[name])
        save_check.grid(row=0, column=4, padx=5, pady=0, sticky="w")

        # Remove button
        remove_button = ttk.Button(widget, width=8, text="Remove", command=lambda w=widget: self.remove_checkbox(w))
        remove_button.grid(row=0, column=5, padx=5, pady=0, sticky="w")

        # Add slider for filtering frequency
        slider_value = tk.IntVar(value=0)
        # slider = ttk.Scale(widget, from_=0, to=10, orient=tk.HORIZONTAL, variable=slider_value)
        slider = tk.Scale(widget, from_=0, to=50, orient=tk.HORIZONTAL, variable=slider_value, resolution=1)
        slider.grid(row=1, column=2, columnspan=5,padx=5, pady=0, sticky="w")
        slider_value_label = ttk.Label(widget, text="0")  # Redundant
        slider_value_label.grid(row=1, column=1, padx=5, pady=0, sticky="w")  # Redundant
        slider.config(command=lambda val, n=name, lbl=slider_value_label: self.update_filter_with_label(n, val, lbl))
        slider.bind("<ButtonRelease-1>", lambda event, n=name, val=slider_value: self.update_filter(n, val.get()))

    def update_filter_with_label(self, name, val, label):  # Redundant
        val = int(float(val))
        label.config(text=f"{val}")

    def remove_checkbox(self, widget):
        name = widget.name

        # Remove dataset from self.data
        if name in self.data:
            del self.data[name]

        # Destroy the widget and remove self.datasets
        widget.destroy()
        self.datasets.remove(widget)

        # Cleanup associated variables
        del self.plot_vars[name]
        del self.trend_vars[name]
        del self.offset_entry[name]
        del self.save_vars[name]

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
                    self.add_checkbox(name)
                    break
            else:  # If no duplicate name is found, add the dataset
                self.data[name] = datasets
                self.add_checkbox(name)

        messagebox.showinfo("Success", "Data loaded successfully!")

    def plot_data(self):  # Save the data whose 'plot' checkbox is checked.
        selected_data = {name: self.data[name] for name, var in self.plot_vars.items() if var.get()}
        if not selected_data:
            messagebox.showwarning("Warning", "No data selected!")
            return

        self.plotter.plot_data(selected_data, self.offset_entry, self.trend_vars)

    def lowpass(self):  # Outdated function, completely replaced by 'update_filter'. May still be useful for reference
        name = simpledialog.askstring("Input", f"Dataset:")
        if name in self.data:
            x, y = self.data[name]['original']
            dft = np.fft.fft(y)
            cutoff_freq = 10
            dft_filtered = dft.copy()
            dft_filtered[cutoff_freq:len(dft) - cutoff_freq] = 0
            y_filtered = np.real(np.fft.ifft(dft_filtered))

            # Store the filtered data
            self.data[name]['filtered'] = (x, y_filtered)

        else:
            messagebox.showwarning("Warning", "Dataset not found!")

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

    def save_measurement_report(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not save_path:
            return

        temp_plot_path = 'temp_plot.png'
        self.fig2.savefig(temp_plot_path, format='png')
        self.report.create_report(save_path)
        os.remove(temp_plot_path)

    def show(self):
        self.root.mainloop()
