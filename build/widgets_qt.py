# widgets_qt.py
#
# Custom widgets for the PyQt measurement app: a per-dataset row (context-menu
# driven, no dedicated Remove button), a DAQ status badge, a line/scatter toggle
# button, and a thread-safe stdout-to-console redirector.

import datetime

from PyQt5.QtCore import Qt, QObject, QEvent, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QActionGroup, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMenu, QSlider, QToolButton, QToolTip, QWidget,
)


class DatasetRow(QFrame):
    """One row in the Data section. Right-click for rename/remove instead of a
    dedicated button; double-click sets this dataset as the reference."""

    rename_requested = pyqtSignal(str, str)   # old_name, requested_new_name
    remove_requested = pyqtSignal(str)
    filter_changed = pyqtSignal(str, int)     # name, cutoff_freq
    set_as_reference = pyqtSignal(str)

    COLUMN_WIDTHS = [160, 50, 50, 50, 50]

    def __init__(self, name, tooltip_provider=None, parent=None):
        super().__init__(parent)
        self.name = name
        self._tooltip_provider = tooltip_provider

        self.setStyleSheet("background-color: #90EE90;")
        self.setFrameShape(QFrame.NoFrame)
        self.setToolTip(" ")  # non-empty placeholder so Qt calls event() for QEvent.ToolTip

        layout = QGridLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        for col, width in enumerate(self.COLUMN_WIDTHS):
            layout.setColumnMinimumWidth(col, width)

        self.name_label = QLabel(name)
        self.name_label.setFixedWidth(self.COLUMN_WIDTHS[0])
        layout.addWidget(self.name_label, 0, 0, Qt.AlignLeft)

        self.plot_check = QCheckBox()
        layout.addWidget(self.plot_check, 0, 1, Qt.AlignLeft)

        self.trend_check = QCheckBox()
        layout.addWidget(self.trend_check, 0, 2, Qt.AlignLeft)

        self.offset_entry = QLineEdit("0")
        self.offset_entry.setFixedWidth(self.COLUMN_WIDTHS[3])
        layout.addWidget(self.offset_entry, 0, 3, Qt.AlignLeft)

        self.save_check = QCheckBox()
        layout.addWidget(self.save_check, 0, 4, Qt.AlignLeft)

        self.detrend_check = QCheckBox()
        layout.addWidget(self.detrend_check, 1, 1, Qt.AlignLeft)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 50)
        self.slider.setToolTip("Savitzky-Golay smoothing window (mm), 0 = off")
        self.slider.sliderReleased.connect(self._emit_filter_changed)
        layout.addWidget(self.slider, 1, 2, 1, 3)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _emit_filter_changed(self):
        self.filter_changed.emit(self.name, self.slider.value())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        rename_action = menu.addAction("Change name")
        remove_action = menu.addAction("Remove")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == rename_action:
            self._prompt_rename()
        elif action == remove_action:
            self.remove_requested.emit(self.name)

    def _prompt_rename(self):
        new_name, ok = QInputDialog.getText(self, "Change name", "Enter new name:", text=self.name)
        if ok:
            self.rename_requested.emit(self.name, new_name)

    def set_name(self, name):
        self.name = name
        self.name_label.setText(name)

    def mouseDoubleClickEvent(self, event):
        self.set_as_reference.emit(self.name)
        super().mouseDoubleClickEvent(event)

    def event(self, e):
        if e.type() == QEvent.ToolTip:
            text = self._tooltip_provider(self.name) if self._tooltip_provider else None
            if text:
                QToolTip.showText(e.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)


class DaqStatusIndicator(QWidget):
    """Small colored badge showing whether the DAQ is live / paused / disconnected."""

    STATUS_STYLE = {
        "live": ("#2ecc71", "Live"),
        "paused": ("#f39c12", "Paused"),
        "disconnected": ("#e74c3c", "Disconnected"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(5)

        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        layout.addWidget(self._dot)

        self._label = QLabel()
        layout.addWidget(self._label)

        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 210); border-radius: 4px;")
        self.set_status("disconnected")

    def set_status(self, status):
        color, text = self.STATUS_STYLE[status]
        self._dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self._label.setText(text)
        self.adjustSize()


class PlotTypeButton(QToolButton):
    """Icon button that toggles both plots between line and scatter. Uses an
    exclusive QActionGroup so exactly one of Line/Scatter is always checked -
    a plain pair of independently-checkable actions lets you uncheck the
    active one and end up with neither checked."""

    plot_type_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plot_type = "line"
        self.setPopupMode(QToolButton.InstantPopup)
        self.setToolTip("Plot type: Line")

        menu = QMenu(self)
        group = QActionGroup(self)
        group.setExclusive(True)

        self._line_action = menu.addAction("Line")
        self._line_action.setCheckable(True)
        self._line_action.setChecked(True)
        group.addAction(self._line_action)

        self._scatter_action = menu.addAction("Scatter")
        self._scatter_action.setCheckable(True)
        group.addAction(self._scatter_action)

        group.triggered.connect(self._on_action_triggered)
        self.setMenu(menu)

        self._update_icon()

    def plot_type(self):
        return self._plot_type

    def _on_action_triggered(self, action):
        plot_type = "line" if action is self._line_action else "scatter"
        if plot_type == self._plot_type:
            return
        self._plot_type = plot_type
        self.setToolTip(f"Plot type: {plot_type.capitalize()}")
        self._update_icon()
        self.plot_type_changed.emit(plot_type)

    def _update_icon(self):
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)
        if self._plot_type == "line":
            painter.drawLine(3, 15, 17, 5)
        else:
            painter.setBrush(Qt.black)
            for x in (4, 10, 16):
                painter.drawEllipse(x - 2, 9, 4, 4)
        painter.end()
        self.setIcon(QIcon(pixmap))


class QtConsoleRedirector(QObject):
    """Drop-in replacement for sys.stdout that is safe to write to from any
    thread: write() just emits a signal, and Qt marshals the queued connection
    to the console widget's thread automatically."""

    log_signal = pyqtSignal(str)

    def write(self, message):
        if message.strip():
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
            message = f"{timestamp}{message}"
        self.log_signal.emit(message)

    def flush(self):
        pass
