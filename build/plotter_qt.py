# plotter_qt.py
#
# Ports Plotter.py to the PyQt GUI: same two-figure setup (live + saved data)
# driven by the same matplotlib FuncAnimation loop, adapted to read state from
# Qt widgets (DatasetRow / checkboxes) instead of Tkinter Vars, and with a
# line/scatter toggle for the saved-data plot.

from queue import Empty

import numpy as np
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt


class PlotterQt:
    def __init__(self, data_holder):
        self.data_holder = data_holder
        self.out_queue = data_holder.queue
        self.fig1, self.ax1 = plt.subplots()
        self.fig2, self.ax2 = plt.subplots()
        self.line, = self.ax1.plot([], [])
        self.gui = None
        self.ani = None
        self.x_data, self.y_data = [], []
        self.sample_cutoff = 100000
        self.plot_type = "line"  # single source of truth, applies to both plots
        self._apply_line_style(self.line)
        self.set_ax1()
        self.set_ax2()

    def set_gui(self, gui):
        self.gui = gui

    def set_ax1(self):
        self.ax1.set_xlabel('Distance (m)')
        self.ax1.set_ylabel('Displacement (µm)')
        self.ax1.set_title('Live Data')
        self.ax1.grid(True)

    def set_ax2(self):
        self.ax2.set_xlabel('Distance (m)')
        self.ax2.set_ylabel('Displacement (µm)')
        self.ax2.set_title('Saved Data')
        self.ax2.grid(True)

    def set_plot_type(self, plot_type):
        self.plot_type = plot_type
        self._apply_line_style(self.line)
        self.ax1.figure.canvas.draw()

    def _apply_line_style(self, line):
        # A styled Line2D (marker-only for "scatter") keeps the live plot on the
        # same single-artist set_data()/blit update path regardless of mode.
        if self.plot_type == "scatter":
            line.set_linestyle('None')
            line.set_marker('o')
            line.set_markersize(4)
        else:
            line.set_linestyle('-')
            line.set_marker('None')

    def update_limit(self):  # Handles X-limit changes.
        if self.gui.manual_limit_check.isChecked():
            try:
                x_min = float(self.gui.x_min_entry.text())
                x_max = float(self.gui.x_max_entry.text())
                if (x_min, x_max) != self.ax1.get_xlim():
                    self.ax1.set_xlim(x_min, x_max)
                    self.ax1.figure.canvas.draw()
            except ValueError:
                pass  # Freezes limits if x_min/x_max aren't valid floats yet
        else:
            self.ax1.set_xlim(auto=True)
            self.ax1.set_ylim(auto=True)
            self.ax1.relim()
            self.ax1.autoscale_view()
            self.ax1.figure.canvas.draw()

    def plot_data(self, rows):  # rows: list[DatasetRow] with plot_check checked
        if self.ax2 is None:
            return

        self.clear_plot2()

        for row in rows:
            measurement = self.data_holder.measurements.get(row.name)
            if measurement is None:
                continue

            delta_y = self._parse_offset(row.offset_entry.text())
            detrended = row.detrend_check.isChecked()

            if detrended and measurement.detrended is not None:
                x, y = measurement.detrended
                label = f"{row.name} (detrended)"
            else:
                x, y = measurement.original
                label = f"{row.name} (original)"
            self._draw_series(x, np.array(y) + delta_y, label)

            if row.trend_check.isChecked() and measurement.coefficients is not None:
                self._add_trend_line(x, delta_y, row.name, measurement, detrended)

            if measurement.filtered is not None:
                xf, yf = measurement.filtered
                self.ax2.plot(xf, np.array(yf) + delta_y, label=f"{row.name} (filtered)", linestyle='--')

        self.add_legend()
        self.ax2.figure.canvas.draw()

    @staticmethod
    def _parse_offset(text):
        text = text.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _draw_series(self, x, y, label):
        # Same marker-only-Line2D trick as the live plot, so "what is what" stays
        # consistent between the two plots regardless of mode.
        if self.plot_type == "scatter":
            self.ax2.plot(x, y, label=label, linestyle='None', marker='o', markersize=4)
        else:
            self.ax2.plot(x, y, label=label)

    def _add_trend_line(self, x, delta_y, name, measurement, detrended):
        a, b = measurement.coefficients
        if detrended:
            a = 0
        x = np.array(x)
        self.ax2.plot(x, a * x + b + delta_y, label=f"Trend {name}: {a:.2f}x + {b:.2f}", linestyle='--')

    def add_legend(self):
        if self.gui.legend_check.isChecked():
            if self.ax2.has_data():
                self.ax2.legend()
        elif self.ax2.get_legend() is not None:
            self.ax2.get_legend().remove()

    def update_legend(self):
        self.add_legend()
        self.ax2.figure.canvas.draw()

    def clear_plot1(self):
        if self.ax1 is not None:
            self.ax1.clear()
            self.line, = self.ax1.plot([], [])
            self._apply_line_style(self.line)
            self.x_data, self.y_data = [], []
            self.data_holder.clear_live_data()
            self.set_ax1()
            self.ax1.figure.canvas.draw()

    def clear_plot2(self):
        if self.ax2 is not None:
            self.ax2.clear()
            self.set_ax2()
            self.ax2.figure.canvas.draw()

    def updater(self, i):
        while not self.out_queue.empty():
            new_data = self.out_queue.get()
            reference_name = self.gui.get_reference()
            if reference_name:
                new_data = self.data_holder.calc_reference(reference_name, new_data)
            if not new_data:
                continue
            self.x_data.append(new_data[0])
            self.y_data.append(new_data[1])
            self.data_holder.live_data.append((new_data[0], new_data[1]))

        if len(self.x_data) > self.sample_cutoff:
            self.x_data = self.x_data[-self.sample_cutoff:]
            self.y_data = self.y_data[-self.sample_cutoff:]

        self.line.set_data(self.x_data, self.y_data)
        self.update_limit()
        self.gui.update_sample_count(len(self.x_data), len(self.data_holder.live_data))
        return self.line,

    def start(self):
        while True:  # drain stale samples from before Start was pressed
            try:
                self.out_queue.get_nowait()
            except Empty:
                break

        if self.ani is None:
            # blit=False: a manual full redraw (e.g. from set_plot_type) would otherwise
            # desync blit's cached background, making the plot flash empty until the next
            # data point forces a re-capture. At this frame rate (10 Hz, one line) a full
            # redraw every frame costs nothing noticeable.
            self.ani = FuncAnimation(self.fig1, self.updater, interval=100, blit=False, cache_frame_data=False)
        # FuncAnimation only auto-arms its timer on the figure's first real draw event,
        # which normally comes from plt.show() - we embed the figure directly in Qt and
        # never call that, so the timer can simply never start on its own. Start it
        # explicitly every time instead of relying on that (this call is a no-op if
        # already running).
        self.ani.event_source.start()

    def stop(self):
        if self.ani is not None and self.ani.event_source is not None:
            self.ani.event_source.stop()
