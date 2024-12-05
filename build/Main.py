import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog


from Sampler import Sampler
from Plotter import Plotter
from Report import Report
from Data import Data
from GUI import GUI


class MainApp:
    def __init__(self):
        self.root = tk.Tk()
        self.data = Data()
        self.plotter = Plotter(self.root, self.data)
        self.sampler = Sampler(self.root, self.data)
        self.report = Report()
        self.gui = GUI(self.root, self.sampler, self.plotter, self.report, self.data)
        self.data.set_gui(self.gui)
        self.plotter.set_gui(self.gui)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def run(self):
        self.gui.show()

    def on_closing(self):  # Ensure the connection is closed before closing the app
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # Before exiting, close everything
            self.root.quit()
            self.root.destroy()

if __name__ == "__main__":
    app = MainApp()
    app.run()
