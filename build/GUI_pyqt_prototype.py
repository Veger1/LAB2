# GUI_pyqt_prototype.py
#
# Standalone layout replica of GUI.py, built in PyQt5, for comparing the
# migration's visual/UX impact side by side with the Tkinter version.
# No backend wiring (Data/Sampler/Report/Plotter) - buttons are stubs that
# print to the console widget so the layout can be exercised interactively.

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QCheckBox, QScrollArea, QFrame,
    QSlider, QPlainTextEdit, QSizePolicy, QMenu, QInputDialog, QMessageBox
)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class DatasetRow(QFrame):
    """Mirrors the per-dataset widget created in GUI.add_checkbox()."""

    COLUMN_WIDTHS = [160, 50, 50, 50, 50, 80]

    def __init__(self, name, on_remove, on_rename):
        super().__init__()
        self.name = name
        self._on_remove = on_remove
        self._on_rename = on_rename

        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: #90EE90;")  # lightgreen, matches tk.Frame(bg='lightgreen')

        layout = QGridLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        for col, width in enumerate(self.COLUMN_WIDTHS):
            layout.setColumnMinimumWidth(col, width)

        self.name_label = QLabel(name)
        self.name_label.setFixedWidth(160)
        layout.addWidget(self.name_label, 0, 0, Qt.AlignLeft)

        self.plot_check = QCheckBox()
        layout.addWidget(self.plot_check, 0, 1, Qt.AlignLeft)

        self.trend_check = QCheckBox()
        layout.addWidget(self.trend_check, 0, 2, Qt.AlignLeft)

        self.offset_entry = QLineEdit("0")
        self.offset_entry.setFixedWidth(50)
        layout.addWidget(self.offset_entry, 0, 3, Qt.AlignLeft)

        self.save_check = QCheckBox()
        layout.addWidget(self.save_check, 0, 4, Qt.AlignLeft)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setFixedWidth(80)
        self.remove_button.clicked.connect(lambda: self._on_remove(self))
        layout.addWidget(self.remove_button, 0, 5, Qt.AlignLeft)

        self.detrend_check = QCheckBox()
        layout.addWidget(self.detrend_check, 1, 1, Qt.AlignLeft)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 50)
        layout.addWidget(self.slider, 1, 2, 1, 5)

        # Right-click rename menu (see earlier discussion on Tk vs Qt context menus)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == rename_action:
            self._rename()

    def _rename(self):
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=self.name)
        if not ok:
            return
        try:
            new_name = self._on_rename(self.name, new_name)
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.name = new_name
        self.name_label.setText(new_name)


class MeasurementAppPyQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Measurement App (PyQt prototype)")
        self.reference = None
        self.dataset_rows = []
        self._dataset_names = set()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QGridLayout(central)

        # --- Left column: the two stacked plots -----------------------------------
        plot_frame1 = self._build_plot_frame()
        plot_frame2 = self._build_plot_frame()
        root_layout.addWidget(plot_frame1, 0, 0)
        root_layout.addWidget(plot_frame2, 1, 0)

        # --- Right column: control panel (mirrors "mainframe") --------------------
        controls = self._build_controls()
        root_layout.addWidget(controls, 0, 1, 2, 1)  # rowspan=2, matches Tk mainframe

        # Column/row stretch mirrors root.columnconfigure/rowconfigure in GUI.py:
        # plot column stretches (weight=1), control column is fixed (weight=0).
        root_layout.setColumnStretch(0, 1)
        root_layout.setColumnStretch(1, 0)
        root_layout.setRowStretch(0, 1)
        root_layout.setRowStretch(1, 1)

        self.resize(1200, 800)

    def _build_plot_frame(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.Panel)
        frame.setLineWidth(2)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        ax.grid(True)
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

        data_group = self._build_data_group()
        layout.addWidget(data_group, stretch=1)  # "Data" group expands, matches visual.grid_rowconfigure(1, weight=1)

        layout.addWidget(self._build_console())

        panel.setFixedWidth(560)  # mirrors the fixed-width control column in the Tk grid
        return panel

    def _build_plot_limits_group(self):
        group = QGroupBox("Plot limits")
        layout = QGridLayout(group)

        self.manual_limit_check = QCheckBox("Manual")
        layout.addWidget(self.manual_limit_check, 0, 0)

        self.x_min_entry = QLineEdit()
        self.x_min_entry.setPlaceholderText("min")
        self.x_min_entry.setFixedWidth(60)
        layout.addWidget(self.x_min_entry, 0, 1)

        self.x_max_entry = QLineEdit()
        self.x_max_entry.setPlaceholderText("max")
        self.x_max_entry.setFixedWidth(60)
        layout.addWidget(self.x_max_entry, 0, 2)

        self.toggle_direction = QCheckBox("<->")
        layout.addWidget(self.toggle_direction, 0, 3)

        self.zero_button = QPushButton("0")
        self.zero_button.setFixedWidth(30)
        layout.addWidget(self.zero_button, 0, 4)

        self.zero_entry = QLineEdit("0")
        self.zero_entry.setFixedWidth(70)
        layout.addWidget(self.zero_entry, 0, 5)

        return group

    def _build_sample_group(self):
        group = QGroupBox("Sample")
        layout = QGridLayout(group)

        self.start_button = QPushButton("Start")
        layout.addWidget(self.start_button, 0, 0)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button, 0, 1)

        self.clear_button = QPushButton("Clear")
        layout.addWidget(self.clear_button, 0, 2)

        self.connect_button = QPushButton("Connect")
        layout.addWidget(self.connect_button, 0, 3)

        self.sample_count_label = QLabel("0")
        layout.addWidget(self.sample_count_label, 0, 4)

        return group

    def _build_save_group(self):
        group = QGroupBox("Save")
        layout = QHBoxLayout(group)  # matches the pack(side=LEFT) row of buttons

        self.add_data_button = QPushButton("Add")
        self.add_data_button.clicked.connect(self._add_dummy_dataset)
        layout.addWidget(self.add_data_button)

        self.load_data_button = QPushButton("Load")
        layout.addWidget(self.load_data_button)

        self.save_button = QPushButton("Save")
        layout.addWidget(self.save_button)

        self.report_button = QPushButton("Report")
        layout.addWidget(self.report_button)

        self.png_button = QPushButton("PNG")
        layout.addWidget(self.png_button)

        layout.addStretch(1)
        return group

    def _build_misc_group(self):
        group = QGroupBox("Misc.")
        layout = QHBoxLayout(group)

        self.reference_label = QLabel(f"Reference: {self.reference}")
        layout.addWidget(self.reference_label)

        self.legend_check = QCheckBox("Legend")
        self.legend_check.setChecked(True)
        layout.addWidget(self.legend_check)

        self.plot_button = QPushButton("Plot")
        layout.addWidget(self.plot_button)

        layout.addStretch(1)
        return group

    def _build_data_group(self):
        group = QGroupBox("Data")
        outer_layout = QVBoxLayout(group)

        # Header row, mirrors header_widget in GUI.py
        header = QWidget()
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(5, 0, 5, 0)
        for col, (text, width) in enumerate([
            ("Name", 160), ("Plot", 50), ("Trend", 50), ("Offset", 50), ("Save", 50)
        ]):
            label = QLabel(text)
            header_layout.setColumnMinimumWidth(col, width)
            header_layout.addWidget(label, 0, col)
        outer_layout.addWidget(header)

        # Scrollable dataset list, mirrors the canvas+scrollbar+scrollable_frame combo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.scrollable_frame = QWidget()
        self.scrollable_layout = QVBoxLayout(self.scrollable_frame)
        self.scrollable_layout.addStretch(1)
        scroll.setWidget(self.scrollable_frame)
        outer_layout.addWidget(scroll)

        return group

    def _build_console(self):
        console = QPlainTextEdit()
        console.setReadOnly(True)
        console.setFixedHeight(60)
        console.setStyleSheet("background-color: lightgrey;")
        self.console = console
        return console

    # --- Stub behaviour, just enough to exercise the layout interactively ---------

    def _add_dummy_dataset(self):
        name, ok = QInputDialog.getText(self, "Input", "Enter measurement name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.critical(self, "Error", "Name cannot be empty!")
            return
        if name in self._dataset_names:
            QMessageBox.critical(self, "Error", "Name already exists!")
            return
        self._dataset_names.add(name)
        row = DatasetRow(name, self._remove_dataset, self._rename_dataset)
        self.dataset_rows.append(row)
        self.scrollable_layout.insertWidget(self.scrollable_layout.count() - 1, row)
        self.console.appendPlainText(f"Added dataset: {name}")

    def _remove_dataset(self, row):
        self._dataset_names.discard(row.name)
        self.dataset_rows.remove(row)
        self.scrollable_layout.removeWidget(row)
        row.deleteLater()
        self.console.appendPlainText(f"Removed dataset: {row.name}")

    def _rename_dataset(self, old_name, new_name):
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Name cannot be empty!")
        if new_name == old_name:
            return old_name
        if new_name in self._dataset_names:
            raise ValueError("Name already exists!")
        self._dataset_names.discard(old_name)
        self._dataset_names.add(new_name)
        self.console.appendPlainText(f"Renamed dataset: {old_name} -> {new_name}")
        return new_name


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeasurementAppPyQt()
    window.show()
    sys.exit(app.exec_())
