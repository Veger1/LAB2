# gui_qt.py
#
# PyQt5 main window. Grown out of the approved GUI_pyqt_prototype.py layout,
# now wired to the real DataStore/Sampler/PlotterQt/Report backend. All
# dialogs and error messages live here - data_model.py never touches Qt.

import os
import sys

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from widgets_qt import DatasetRow, DaqStatusIndicator, PlotTypeButton, QtConsoleRedirector


class _ClickableLabel(QLabel):
    doubleClicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, sampler, plotter, report, data_holder):
        super().__init__()
        self.sampler = sampler
        self.plotter = plotter
        self.report = report
        self.data_holder = data_holder

        self.connection_established = False
        self.reference = None
        self.dataset_rows = []

        self.setWindowTitle("LaserTool")

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QGridLayout(central)

        live_frame = self._build_plot_frame(live=True)
        saved_frame = self._build_plot_frame(live=False)
        root_layout.addWidget(live_frame, 0, 0)
        root_layout.addWidget(saved_frame, 1, 0)

        controls = self._build_controls()
        root_layout.addWidget(controls, 0, 1, 2, 1)

        root_layout.setColumnStretch(0, 1)
        root_layout.setColumnStretch(1, 0)
        root_layout.setRowStretch(0, 1)
        root_layout.setRowStretch(1, 1)

        self.resize(1200, 800)

        self._console_redirector = QtConsoleRedirector()
        self._console_redirector.log_signal.connect(self._append_console)
        sys.stdout = self._console_redirector

        self._connection_timer = QTimer(self)
        self._connection_timer.timeout.connect(self._check_connection_status)
        self._connection_timer.start(1000)
        self._check_connection_status()

    # --- layout construction ----------------------------------------------------

    def _build_plot_frame(self, live):
        frame = QFrame()
        frame.setFrameShape(QFrame.Panel)
        frame.setLineWidth(2)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        fig = self.plotter.fig1 if live else self.plotter.fig2
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas)

        return frame

    def _build_controls(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self._build_sample_group())
        layout.addWidget(self._build_plot_limits_group())
        layout.addWidget(self._build_save_group())
        layout.addWidget(self._build_misc_group())
        layout.addWidget(self._build_data_group(), stretch=1)
        layout.addWidget(self._build_console())

        panel.setFixedWidth(560)
        return panel

    def _build_sample_group(self):
        group = QGroupBox("Sample")
        layout = QHBoxLayout(group)

        self.start_button = QPushButton("Start")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_sampling)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop_sampling)
        layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_sampler)
        layout.addWidget(self.clear_button)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.sampler.connect)
        layout.addWidget(self.connect_button)

        self.sample_count_label = QLabel("0")
        layout.addWidget(self.sample_count_label)

        layout.addStretch(1)

        self.daq_indicator = DaqStatusIndicator()
        layout.addWidget(self.daq_indicator)

        return group

    def _build_plot_limits_group(self):
        group = QGroupBox("Plot limits")
        layout = QHBoxLayout(group)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 4, 6, 4)

        self.manual_limit_check = QCheckBox("Manual")
        layout.addWidget(self.manual_limit_check)

        self.x_min_entry = QLineEdit()
        self.x_min_entry.setPlaceholderText("min")
        self.x_min_entry.setFixedWidth(45)
        layout.addWidget(self.x_min_entry)

        self.x_max_entry = QLineEdit()
        self.x_max_entry.setPlaceholderText("max")
        self.x_max_entry.setFixedWidth(45)
        layout.addWidget(self.x_max_entry)

        self.toggle_direction = QCheckBox("<->")
        self.toggle_direction.toggled.connect(self._update_flip_orientation)
        layout.addWidget(self.toggle_direction)

        self.zero_button = QPushButton("0")
        self.zero_button.setFixedWidth(24)
        self.zero_button.clicked.connect(self._zero_measurement)
        layout.addWidget(self.zero_button)

        self.zero_entry = QLineEdit("0")
        self.zero_entry.setFixedWidth(55)
        self.zero_entry.editingFinished.connect(self._clear_zero_point)
        layout.addWidget(self.zero_entry)

        layout.addStretch(1)
        return group

    def _build_save_group(self):
        group = QGroupBox("Save")
        layout = QHBoxLayout(group)

        self.add_data_button = QPushButton("Add")
        self.add_data_button.clicked.connect(self._add_data)
        layout.addWidget(self.add_data_button)

        self.load_data_button = QPushButton("Load")
        self.load_data_button.clicked.connect(self._load_data)
        layout.addWidget(self.load_data_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_data)
        layout.addWidget(self.save_button)

        self.report_button = QPushButton("Report")
        self.report_button.clicked.connect(self._save_measurement_report)
        layout.addWidget(self.report_button)

        self.png_button = QPushButton("PNG")
        self.png_button.clicked.connect(self._save_measurement_png)
        layout.addWidget(self.png_button)

        layout.addStretch(1)
        return group

    def _build_misc_group(self):
        group = QGroupBox("Misc.")
        layout = QHBoxLayout(group)

        self.reference_label = _ClickableLabel(f"Reference: {self.reference}")
        self.reference_label.setToolTip("Double-click a dataset row to set it as reference.\n"
                                         "Double-click here to clear it.")
        self.reference_label.doubleClicked.connect(self._clear_reference)
        layout.addWidget(self.reference_label)

        self.legend_check = QCheckBox("Legend")
        self.legend_check.setChecked(True)
        self.legend_check.toggled.connect(self.plotter.update_legend)
        layout.addWidget(self.legend_check)

        self.plot_type_button = PlotTypeButton()
        self.plot_type_button.plot_type_changed.connect(self.plotter.set_plot_type)
        layout.addWidget(self.plot_type_button)

        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self._plot_data)
        layout.addWidget(self.plot_button)

        layout.addStretch(1)
        return group

    def _build_data_group(self):
        group = QGroupBox("Data")
        outer_layout = QVBoxLayout(group)

        header = QWidget()
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(5, 0, 5, 0)
        for col, (text, width) in enumerate(zip(
                ["Name", "Plot", "Trend", "Offset", "Save"], DatasetRow.COLUMN_WIDTHS)):
            header_layout.setColumnMinimumWidth(col, width)
            header_layout.addWidget(QLabel(text), 0, col)
        outer_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.scrollable_frame = QWidget()
        self.scrollable_layout = QVBoxLayout(self.scrollable_frame)
        self.scrollable_layout.addStretch(1)
        scroll.setWidget(self.scrollable_frame)
        outer_layout.addWidget(scroll)

        return group

    def _build_console(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.addWidget(QLabel("Console"))
        header.addStretch(1)
        open_button = QPushButton("Open ⤤")
        open_button.setFixedWidth(60)
        open_button.setToolTip("Open the console in a separate window")
        open_button.clicked.connect(self._open_console_window)
        header.addWidget(open_button)
        layout.addLayout(header)

        console = QPlainTextEdit()
        console.setReadOnly(True)
        console.setFixedHeight(70)
        console.setStyleSheet("background-color: lightgrey;")
        self.console = console
        layout.addWidget(console)

        self._console_dialog = None
        self._console_view = None
        return container

    def _open_console_window(self):
        if self._console_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Console")
            dialog.resize(700, 400)
            layout = QVBoxLayout(dialog)
            view = QPlainTextEdit()
            view.setReadOnly(True)
            # Deliberately NOT sharing self.console's document: PyQt's QPlainTextEdit
            # miscalculates the scroll range for a second view of the same document when
            # that view has a different width (its scrollbar maximum() sticks at 0, so it
            # looks like you can't scroll at all). Keep two independent widgets in sync
            # instead - see _append_console.
            view.setPlainText(self.console.toPlainText())
            layout.addWidget(view)
            self._console_dialog = dialog
            self._console_view = view
        self._scroll_to_bottom(self._console_view)
        self._console_dialog.show()
        self._console_dialog.raise_()
        self._console_dialog.activateWindow()

    @staticmethod
    def _scroll_to_bottom(text_edit):
        scrollbar = text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # --- sampling ----------------------------------------------------------------

    def _start_sampling(self):
        if self.sampler.start_sampler():
            self.plotter.start()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self._update_daq_status()

    def _stop_sampling(self):
        self.sampler.stop_sampling()
        self.plotter.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._update_daq_status()

    def _clear_sampler(self):
        self.plotter.clear_plot1()  # also clears data_holder.live_data
        self.update_sample_count(0, 0)

    def _check_connection_status(self):
        if self.sampler.is_connected():
            if not self.connection_established:
                self.start_button.setEnabled(True)
                self.connection_established = True
        else:
            self.start_button.setEnabled(False)
            self.connection_established = False
        self._update_daq_status()

    def _update_daq_status(self):
        if not self.sampler.is_connected():
            self.daq_indicator.set_status("disconnected")
        elif self.sampler.sampling:
            self.daq_indicator.set_status("live")
        else:
            self.daq_indicator.set_status("paused")

    def _zero_measurement(self):
        self.sampler.set_zero_point()
        if self.sampler.last_data is not None:
            self.zero_entry.setText(str(self.sampler.last_data))

    def _clear_zero_point(self):
        if not self.zero_entry.text().strip():
            self.sampler.zero_point = 0
            self.zero_entry.setText('0')

    def _update_flip_orientation(self, checked):
        self.sampler.flip_orientation = checked

    def update_sample_count(self, count, total_count):  # called every animation frame by PlotterQt
        if total_count > count:
            self.sample_count_label.setText(f"{total_count} ({count})")
        else:
            self.sample_count_label.setText(f"{count}")

    # --- dataset management --------------------------------------------------------

    def _add_data(self):
        name, ok = QInputDialog.getText(self, "Input", "Enter measurement name:")
        if not ok:
            return
        try:
            measurement = self.data_holder.add_measurement(name)
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self._add_dataset_row(measurement.name)

    def _add_dataset_row(self, name):
        row = DatasetRow(name, tooltip_provider=self._get_results)
        row.rename_requested.connect(self._rename_dataset)
        row.remove_requested.connect(self._remove_dataset)
        row.filter_changed.connect(self._update_filter)
        row.set_as_reference.connect(self._set_reference)
        self.dataset_rows.append(row)
        self.scrollable_layout.insertWidget(self.scrollable_layout.count() - 1, row)

    def _row_by_name(self, name):
        for row in self.dataset_rows:
            if row.name == name:
                return row
        return None

    def _rename_dataset(self, old_name, new_name):
        try:
            resolved = self.data_holder.rename_measurement(old_name, new_name)
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        row = self._row_by_name(old_name)
        if row is not None:
            row.set_name(resolved)
        if self.reference == old_name:
            self.reference = resolved
            self.reference_label.setText(f"Reference: {self.reference}")

    def _remove_dataset(self, name):
        self.data_holder.remove_measurement(name)
        row = self._row_by_name(name)
        if row is not None:
            self.dataset_rows.remove(row)
            self.scrollable_layout.removeWidget(row)
            row.deleteLater()
        if self.reference == name:
            self._clear_reference()

    def _set_reference(self, name):
        try:
            self.data_holder.extend_data(name)
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Failed to set reference:\n{e}")
            return
        self.reference = name
        self.reference_label.setText(f"Reference: {self.reference}")

    def get_reference(self):
        return self.reference

    def _clear_reference(self):
        self.reference = None
        self.reference_label.setText(f"Reference: {self.reference}")

    def _update_filter(self, name, cutoff):
        try:
            self.data_holder.update_filter(name, cutoff)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update filter:\n{e}")

    def _get_results(self, name):
        measurement = self.data_holder.measurements.get(name)
        if measurement is None:
            return "No results available"
        try:
            ptp = measurement.results['ptp']
            a = measurement.coefficients[0]
        except (KeyError, TypeError):
            return "No results available"

        if self.reference and self.reference != name:
            ref_measurement = self.data_holder.measurements.get(self.reference)
            try:
                a_ref = ref_measurement.coefficients[0]
                delta_a = a - a_ref
                return (f"slope: {a:.2f} relative {delta_a:.2f} (µm/m)\n"
                        f"ptp: {ptp:.2f} (µm)")
            except (AttributeError, TypeError):
                pass
        return f"slope: {a:.2f} (µm/m)\nptp: {ptp:.2f} (µm)"

    # --- plotting --------------------------------------------------------------

    def _plot_data(self):
        rows = [row for row in self.dataset_rows if row.plot_check.isChecked()]
        if not rows:
            return
        self.plotter.plot_data(rows)

    # --- save / load / export ----------------------------------------------------

    def _save_data(self):
        names = [row.name for row in self.dataset_rows if row.save_check.isChecked()]
        if not names:
            QMessageBox.warning(self, "Warning", "No data selected!")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save data", "", "CSV files (*.csv)")
        if not save_path:
            return
        if not save_path.lower().endswith(".csv"):
            save_path += ".csv"

        try:
            result = self.data_holder.save(save_path, names)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to save data:\n{e}")
            return

        if not result.saved:
            QMessageBox.warning(self, "Warning", "Selected dataset(s) contain no data to save!")
            return

        if result.skipped_empty:
            QMessageBox.information(self, "Success", "Data saved successfully! Skipped empty dataset(s): "
                                                       f"{', '.join(result.skipped_empty)}")
        else:
            QMessageBox.information(self, "Success", "Data saved successfully!")

    def _load_data(self):
        load_path, _ = QFileDialog.getOpenFileName(self, "Load data", "", "CSV files (*.csv)")
        if not load_path:
            return

        try:
            parsed = self.data_holder.load(load_path)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to read file:\n{e}")
            return

        result = self.data_holder.import_measurements(parsed.measurements, self._resolve_name_conflict)
        for name in result.loaded:
            self._add_dataset_row(name)

        message_parts = []
        if result.loaded:
            message_parts.append(f"Loaded: {', '.join(result.loaded)}")
        if result.skipped:
            message_parts.append(f"Skipped: {', '.join(result.skipped)}")
        if parsed.skipped_rows:
            message_parts.append(f"{parsed.skipped_rows} malformed row(s) ignored")

        if result.loaded:
            QMessageBox.information(self, "Success", "\n".join(message_parts))
        else:
            QMessageBox.warning(self, "Warning", "\n".join(message_parts) if message_parts else "No data was loaded.")

    def _resolve_name_conflict(self, name):
        while True:
            new_name, ok = QInputDialog.getText(self, "Input", f"Name {name} already exists! Enter a new name:")
            if not ok:
                return None
            new_name = new_name.strip()
            if not new_name or new_name in self.data_holder.measurements:
                QMessageBox.warning(self, "Warning", "Invalid input. Please enter a unique name.")
                continue
            return new_name

    def _save_measurement_report(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save report", "", "PDF files (*.pdf)")
        if not save_path:
            return
        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        temp_plot_path = 'temp_plot.png'
        try:
            self.report.copy_and_resize_plot(self.plotter.fig2, self.plotter.ax2, temp_plot_path)
            self.report.create_report(save_path, temp_plot_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create report:\n{e}")
            return
        finally:
            if os.path.exists(temp_plot_path):
                os.remove(temp_plot_path)
        QMessageBox.information(self, "Success", "Report saved successfully!")

    def _save_measurement_png(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save plot", "", "PNG files (*.png)")
        if not save_path:
            return
        if not save_path.lower().endswith(".png"):
            save_path += ".png"

        try:
            self.report.copy_and_resize_plot(self.plotter.fig2, self.plotter.ax2, 'temp_plot.png', save=save_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save PNG:\n{e}")
            return
        QMessageBox.information(self, "Success", "Plot saved successfully!")

    # --- console / lifecycle -----------------------------------------------------

    def _append_console(self, message):
        text = message.rstrip('\n')
        self.console.appendPlainText(text)

        # Mirrored into the pop-out independently (see _open_console_window for why it
        # doesn't just share self.console's document). appendPlainText() auto-scrolls the
        # widget it's called on only, so we replicate that "stick to bottom unless the
        # user scrolled up to read history" behavior manually here.
        view = self._console_view
        if view is not None:
            scrollbar = view.verticalScrollBar()
            was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
            view.appendPlainText(text)
            if was_at_bottom:
                self._scroll_to_bottom(view)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Quit", "Do you want to quit?",
                                      QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
        if reply == QMessageBox.Ok:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            event.accept()
        else:
            event.ignore()
