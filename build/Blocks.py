import datetime
import tkinter as tk


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