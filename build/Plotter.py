import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation


# from tkinter import simpledialog


class Plotter:
    def __init__(self, root, data):
        self.datas = data
        self.out_queue = data.queue
        self.fig1, self.ax1 = plt.subplots()
        self.fig2, self.ax2 = plt.subplots()
        self.line, = self.ax1.plot([], [])
        self.root = root
        self.gui = None
        self.ani = None
        self.x_data, self.y_data = [], []
        self.data = {}
        self.filtered = {}
        self.sample_cutoff = 100


    def set_axes(self):
        self.ax1.set_title('Live Data')
        self.ax1.set_xlabel('Distance (m)')
        self.ax1.set_ylabel('Displacement (µm)')
        self.ax2.set_title('Saved Data')
        self.ax2.set_xlabel('Distance (m)')
        self.ax2.set_ylabel('Displacement (µm)')


    def update_limit(self):  # Handles X-limit changes.
        if self.gui.manual_limit_var.get():
            try:
                x_min = float(self.gui.x_min_entry.get())
                x_max = float(self.gui.x_max_entry.get())
                self.ax1.set_xlim(x_min, x_max)
            except ValueError:
                pass
        else:
            self.ax1.set_xlim(auto=True)
            self.ax1.set_ylim(auto=True)
            self.ax1.relim()  # Recalculate limits
            self.ax1.autoscale_view()
        self.ax1.figure.canvas.draw()  # Redraw the WHOLE canvas

    def plot_data(self, selected_data, offset_entry, trend_vars):  # Plot selected data
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

    def clear_plot1(self):
        if self.ax1 is not None:
            self.ax1.clear()
            self.line, = self.ax1.plot([], [])
            self.x_data, self.y_data = [], []
            self.datas.clear_live_data()
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

    def updater(self, i):
        while not self.out_queue.empty():
            new_data = self.out_queue.get()
            self.x_data.append(new_data[0])
            self.y_data.append(new_data[1])
            print(new_data)
            self.datas.live_data.append((new_data[0], new_data[1]))

        if len(self.x_data) > self.sample_cutoff:
            self.x_data = self.x_data[-self.sample_cutoff:]
            self.y_data = self.y_data[-self.sample_cutoff:]

        self.line.set_data(self.x_data, self.y_data)
        self.ax1.relim()
        self.ax1.autoscale_view()
        print(self.line)
        return self.line,

    def start(self):
        print("start")
        while not self.out_queue.empty():
            try:
                self.out_queue.get_nowait()
            except self.out_queue.Empty:
                break

                # Create FuncAnimation when starting
        if self.ani is None:
            self.ani = FuncAnimation(self.fig1, self.updater, interval=100, blit=True, cache_frame_data=False)
        else:
            self.ani.event_source.start()

    def stop(self):
        if self.ani.event_source is not None:
            print("stop")
            self.ani.event_source.stop()


