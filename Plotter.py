import matplotlib.pyplot as plt
import numpy as np
# from tkinter import simpledialog


class Plotter:
    def __init__(self, root):
        self.ax1 = None
        self.ax2 = None
        self.hl, = plt.plot([], [])  # Initialize the plot line
        self.root = root
        self.data = {}
        self.check_vars = {}  # Not needed
        self.trend_vars = {}  # Not needed
        self.offset_vars = {}  # Not needed
        self.filtered = {}

    def set_axes(self, ax1, ax2):
        self.ax1 = ax1
        self.ax2 = ax2
        self.hl, = self.ax1.plot([], [])  # Set the plot line on the axis
        self.ax1.set_title('Live Data')
        self.ax1.set_xlabel('Distance (m)')
        self.ax1.set_ylabel('Displacement (µm)')
        self.ax2.set_title('Saved Data')
        self.ax2.set_xlabel('Distance (m)')
        self.ax2.set_ylabel('Displacement (µm)')

    def update_plot(self, new_data):  # Schedule update_plot in the main thread.
        self.root.after(0, self._update_plot, new_data)

    def _update_plot(self, new_data):
        x, y = zip(*new_data)
        self.hl.set_xdata(x)
        self.hl.set_ydata(y)
        self.ax1.figure.canvas.draw()
        self.update_limit()

    def update_limit(self):
        if self.root.manual_limit_var.get():
            try:
                x_min = float(self.root.x_min_entry.get())
                x_max = float(self.root.x_max_entry.get())
                self.ax1.set_xlim(x_min, x_max)
            except ValueError:
                pass
        else:
            self.ax1.relim()  # Recalculate limits
            self.ax1.autoscale_view()
        self.ax1.figure.canvas.draw()

    def plot_data(self, selected_data, offset_entry, trend_vars):
        if self.ax2 is None:
            return

        self.clear_plot2()

        for name, datasets in selected_data.items():
            x, y = datasets['original']
            y = np.array(y)
            if offset_entry[name].get():
                y += float(offset_entry[name].get())
            self.ax2.plot(x, y, label=f"{name} (original)")
            if trend_vars[name].get():
                self.add_trend_line(x, y, name)

            # Plot filtered data if exists
            if 'filtered' in datasets and datasets['filtered'] is not None:
                xf, yf = datasets['filtered']
                self.ax2.plot(xf, np.array(yf), label=f"{name} (filtered)", linestyle='--')

        self.ax2.legend()
        self.ax2.grid(True)
        self.ax2.figure.canvas.draw()

    def add_trend_line(self, x, y, name):
        x = np.array(x)
        y = np.array(y)
        a, b = np.polyfit(x, y, 1)
        self.ax2.plot(x, a * x + b, label=f"Trend {name}: {a:.2f}x + {b:.2f}", linestyle='--')
        self.ax2.legend()
        self.ax2.figure.canvas.draw()

    def update_filter(self, name, slider, slider_name): #updaten
        dft = np.fft.fft(self.data[name][1])
        cutoff_freq = slider.get()
        dft_filtered = dft.copy()
        dft_filtered[cutoff_freq:len(dft) - cutoff_freq] = 0
        y_filtered = np.real(np.fft.ifft(dft_filtered))
        self.filtered[name][slider_name] = (self.data[name][0], y_filtered)

    def clear_plot1(self):
        if self.ax1 is not None:
            self.ax1.clear()
            self.hl, = self.ax1.plot([], [])
            self.ax1.set_title('Live Data')
            self.ax1.set_xlabel('Distance (m)')
            self.ax1.set_ylabel('Displacement (µm)')
            self.ax1.figure.canvas.draw()

    def clear_plot2(self):
        if self.ax2 is not None:
            self.ax2.clear()
            self.ax2.set_title('Saved Data')
            self.ax2.set_xlabel('Distance (m)')
            self.ax2.set_ylabel('Displacement (µm)')
            self.ax2.figure.canvas.draw()

