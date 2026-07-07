# main_qt.py
#
# Entry point for the PyQt5 version of the measurement app.

import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox

from data_model import DataStore
from Sampler import Sampler
from Report import Report
from plotter_qt import PlotterQt
from gui_qt import MainWindow


def _handle_exception(exc_type, exc_value, exc_traceback):
    # PyQt does not have Tkinter's report_callback_exception - an unhandled
    # exception in a slot would otherwise just print to stderr (invisible in a
    # windowed build) and can abort the app outright. This is the safety net
    # for anything not already caught by a specific try/except.
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    QMessageBox.critical(None, "Unexpected Error", f"An unexpected error occurred:\n{exc_value}")


def main():
    app = QApplication(sys.argv)
    sys.excepthook = _handle_exception

    data_holder = DataStore()
    sampler = Sampler(None, data_holder)
    report = Report()
    plotter = PlotterQt(data_holder)

    window = MainWindow(sampler, plotter, report, data_holder)
    plotter.set_gui(window)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
