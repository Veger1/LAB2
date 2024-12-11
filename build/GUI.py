import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from tkinter.scrolledtext import ScrolledText
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
from functools import partial

class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        if message.strip():  # Avoid adding timestamps to blank lines
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
            message = f"{timestamp}{message}"
        self.text_widget.config(state=tk.NORMAL)  # Enable the Text widget
        self.text_widget.insert(tk.END, message)  # Insert the message
        self.text_widget.see(tk.END)  # Auto-scroll to the bottom
        self.text_widget.config(state=tk.DISABLED)
        # Auto-scroll to the bottom

    def flush(self):
        pass  # Required for compatibility with `sys.stdout`

class Tooltip:
    def __init__(self, widget, text=None, text_function= None):
        self.widget = widget
        self.text = text
        self.text_function = text_function
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip_window:
            return
        if callable(self.text_function):
            text = self.text_function()
        else:
            text = self.text
        if not text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()


class GUI:
    def __init__(self, window, sampler, plotter, report, data):
        self.root = window
        self.sampler = sampler
        self.plotter = plotter
        self.report = report
        self.data_holder = data
        self.connection_established = False
        self.sample_count = 0
        self.reference = None

        self.root.title("Measurement App")

        self.style = ttk.Style()
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabelframe', background='white')
        self.style.configure('TLabelframe.Label', background='white')
        self.style.configure('TCheckbutton', background='white')

        self.data = self.data_holder.data
        self.plot_vars = self.data_holder.plot_vars
        self.trend_vars = self.data_holder.trend_vars
        self.offset_vars = self.data_holder.offset_vars
        self.offset_entry = self.data_holder.offset_entry
        self.save_vars = self.data_holder.save_vars
        self.detrend_vars = self.data_holder.detrend_vars
        self.datasets = self.data_holder.datasets

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

        self.filtering = ttk.Labelframe(self.mainframe, text="Misc.", padding="10 10 10 10", borderwidth=2, relief="groove")
        self.filtering.grid(column=0, row=4, sticky=tk.NSEW)

        self.console_frame =ttk.Frame(self.mainframe, borderwidth=2, height=10, width=55, relief="groove")
        self.console_frame.grid(column=0, row=6)

        self.console = ScrolledText(self.console_frame, wrap=tk.WORD, height=3, width=50, state=tk.DISABLED,
                                    bg="lightgrey")
        self.console.grid(column=0, row=0, sticky=tk.NSEW)

        """ Redirect the console output to the text widget """
        sys.stdout = ConsoleRedirector(self.console)
        sys.stderr = ConsoleRedirector(self.console)

        self.mainframe.grid_rowconfigure(5, weight=1)  # Make the visual frame expandable

        self.plot_frame1 = ttk.Frame(self.root, borderwidth=2, relief="groove")
        self.plot_frame1.grid(row=0, column=0, sticky=tk.NSEW)

        self.plot_frame2 = ttk.Frame(self.root, borderwidth=2, relief="groove")
        self.plot_frame2.grid(row=1, column=0, sticky=tk.NSEW)

        self.fig1, self.ax1 = plotter.fig1, plotter.ax1
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.plot_frame1)
        self.canvas1.draw()
        self.canvas1.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.fig2, self.ax2 = plotter.fig2, plotter.ax2
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.plot_frame2)
        self.canvas2.draw()
        self.canvas2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

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

        self.start_button = ttk.Button(self.measure, text="Start", command=self.start_sampling)
        self.start_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.stop_button = ttk.Button(self.measure, text="Stop", command=self.stop_sampling, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)

        self.clear_button = ttk.Button(self.measure, text="Clear", command=self.clear_sampler)
        self.clear_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        self.connect_button = ttk.Button(self.measure, text="Connect", command=self.sampler.connect)
        self.connect_button.grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)

        self.sample_count_label = ttk.Label(self.measure, text="0")
        self.sample_count_label.grid(row=1, column=5, padx=5, pady=5, sticky=tk.W)

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
        self.header_widget.grid_columnconfigure(0, minsize=160)
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

        self.offset_label = ttk.Label(self.header_widget, width=6, text="Offset", background='white')
        self.offset_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.save_label = ttk.Label(self.header_widget, width=5, text="Save", background='white')
        self.save_label.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.reference_label = ttk.Label(self.filtering, text=f"Reference: {self.reference}")
        self.reference_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.reference_label.bind("<Double-1>", lambda event:  self.clear_reference())

        self.check_connection_status()  # Initialize connection checker

    def __del__(self):
        # Reset sys.stdout and sys.stderr when the GUI is destroyed
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    @staticmethod
    def clear_placeholder(event):  # Clear the placeholder text when the entry is clicked
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
        if self.sampler.last_data:
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
        else:
            self.start_button.config(state=tk.DISABLED)
            self.connection_established = False

        self.root.after(1000, self.check_connection_status)

    def start_sampling(self):
        if self.sampler.start_sampler():  # change to offline_sampler for testing
            print("started sampling")
            self.plotter.start()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

    def stop_sampling(self):
        self.sampler.stop_sampling()
        self.plotter.stop()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def clear_sampler(self):
        self.data_holder.clear_live_data()
        self.plotter.clear_plot1()
        self.update_sample_count(0, 0)

    def add_data(self):  # Add the data to the data dictionary, each name has an original dataset along with a 'None'
        # filtered set
        name = self.data_holder.add_data()
        if name is not None:
            self.add_checkbox(name)

    def save_data(self):
        self.data_holder.save_data()

    def add_checkbox(self, name):  # To dynamically add datasets to the data frame, each dataset is placed in a frame
        # along with its own checkboxes/entries. Pack manager is used since it is better at stacking widget without
        # having to remember the row/column.

        # Create dataset widget
        widget = tk.Frame(self.scrollable_frame, bg='lightgreen')
        widget.pack(pady=5)
        self.datasets.append(widget)

        # Configure the column width of the dataset widget to better match the header widget.
        widget.grid_columnconfigure(0, minsize=160)
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
        self.detrend_vars[name] = tk.BooleanVar()

        # Add dataset name and buttons
        name_label = ttk.Label(widget, width=20, text=name)
        name_label.grid(row=0, column=0, padx=5, pady=0, sticky="w")

        check = ttk.Checkbutton(widget, width=1, variable=self.plot_vars[name])
        check.grid(row=0, column=1, padx=5, pady=0, sticky="w")

        trend_check = ttk.Checkbutton(widget, width=1, variable=self.trend_vars[name])
        trend_check.grid(row=0, column=2, padx=5, pady=0, sticky="w")

        offset_entry = ttk.Entry(widget, width=5, textvariable=self.offset_entry[name])
        offset_entry.grid(row=0, column=3, padx=5, pady=0, sticky="w")

        save_check = ttk.Checkbutton(widget, width=1, variable=self.save_vars[name])
        save_check.grid(row=0, column=4, padx=5, pady=0, sticky="w")

        remove_button = ttk.Button(widget, width=8, text="Remove", command=lambda w=widget: self.remove_checkbox(w))
        remove_button.grid(row=0, column=5, padx=5, pady=0, sticky="w")

        # Add slider for filtering frequency
        slider_value = tk.IntVar(value=0)
        # slider = ttk.Scale(widget, from_=0, to=10, orient=tk.HORIZONTAL, variable=slider_value)
        slider = tk.Scale(widget, from_=0, to=50, orient=tk.HORIZONTAL, variable=slider_value, resolution=1)
        slider.grid(row=1, column=2, columnspan=5,padx=5, pady=0, sticky="w")

        detrend_check = ttk.Checkbutton(widget, variable= self.detrend_vars[name])
        detrend_check.grid(row=1, column=1, padx=5, pady=0, sticky="w")

        slider.bind("<ButtonRelease-1>", lambda event, n=name, val=slider_value: self.update_filter(n, val.get()))

        widget.bind("<Double-1>", lambda event, w=widget: self.on_widget_double_click(w))
        Tooltip(name_label, text_function=partial(self.get_results, name))
        """ Maybe bind this to the nametag instead of the widget"""

    def remove_checkbox(self, widget):
        self.data_holder.remove_associated_data(widget)
        if self.reference == widget.name:
            self.clear_reference()
        widget.destroy()

    def load_data(self):
        self.data_holder.load_data()

    def plot_data(self):  # Save the data whose 'plot' checkbox is checked.
        """ Maybe change this to any checkbox selected within the widget. To plot trendline only for example"""
        selected_data = {name: self.data[name] for name, var in self.plot_vars.items() if var.get()}
        if not selected_data:
            # messagebox.showwarning("Warning", "No data selected!")
            """ Maybe clear plot instead """
            return
        self.plotter.plot_data(selected_data, self.offset_entry, self.trend_vars)

    def update_filter(self, name, cutoff_freq):
        self.data_holder.update_filter(name, cutoff_freq)

    def save_measurement_report(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not save_path:
            return

        temp_plot_path = 'temp_plot.png'
        self.fig2.savefig(temp_plot_path, format='png')
        self.report.create_report(save_path)
        os.remove(temp_plot_path)

    def lowpass(self):
        return

    def update_sample_count(self, count, total_count):
        if total_count > count:
            self.sample_count_label.config(text=f"{total_count} ({count})")
        else:
            self.sample_count_label.config(text=f"{count}")

    def on_widget_double_click(self, widget):
        self.reference = widget.name
        self.reference_label.config(text=f"Reference: {self.reference}")
        self.data_holder.extend_data(widget.name)
        print(f"Replaced reference with: {self.reference}")

    def get_reference(self):
        return self.reference

    def get_results(self,name):
        ptp = self.data_holder.data[name]['results']['ptp']
        a = self.data_holder.data[name]['coefficients'][0]
        if self.get_reference() and self.get_reference() != name:
            ref_name = self.get_reference()
            a_ref= self.data_holder.data[ref_name]['coefficients'][0]
            delta_a = a - a_ref
            return f"slope: {a:.2f} relative {delta_a:.2f} (µm/m)\n ptp: {ptp:.2f} (µm)"
        return f"slope: {a:.2f} (µm)\n ptp: {ptp:.2f} (µm)"


    def clear_reference(self):
        self.reference = None
        self.reference_label.config(text=f"Reference: {self.reference}")

    def show(self):
        self.root.mainloop()
