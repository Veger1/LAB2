import serial
import serial.tools.list_ports
import threading
from tkinter import messagebox


class Sampler:
    def __init__(self, plotter):
        self.ser = None
        self.sampling = False
        self.data = []
        self.thread = None
        self.plotter = plotter
        self.zero_point = 0
        self.serial_available = False
        self.port = None
        self.connect()
        self.stop_event = threading.Event()

    def set_zero_point(self):
        if self.data:
            self.zero_point = self.data[-1][0]

    def find_arduino_port(self):
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in ports:
            # Check if the description or hardware ID matches Arduino
            if 'Arduino' in desc or 'VID:PID=2341' in hwid:
                return port
        return None

    def connect(self):
        if self.port is None:
            self.port = self.find_arduino_port()
            if self.port:
                try:
                    self.ser = serial.Serial(self.port, 19200, timeout=1)
                    self.serial_available = True
                    print("Serial port initialized")
                except serial.SerialException:
                    print("Serial port could not be opened: {e}")
                    self.serial_available = False
            else:
                print("Arduino not found on any port")
                self.serial_available = False

    def is_connected(self):
        if self.port is not None:
            ports = serial.tools.list_ports.comports()
            for port, desc, hwid in ports:
                if port == self.port and ('Arduino' in desc or 'VID:PID=2341' in hwid):
                    return True
        self.port = None
        return False

    def disconnect(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
            self.ser = None

    def start_sampling(self):
        try:
            self.ser.write(b'G')  # Send G to start mySerial
            print("succes")
        except AttributeError:
            messagebox.showinfo("Failed", "Not connected!")
            self.sampling = False
        except serial.serialutil.SerialException:
            messagebox.showinfo("Failed", "Not connected!")
            self.sampling = False
        else:
            self.sampling = True
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.sample_data, args=(self.stop_event,))
            self.thread.start()
        return self.sampling

    def stop_sampling(self):
        try:
            self.ser.write(b'S')  # Send S to stop mySerial
        except AttributeError:
            pass
        except serial.serialutil.SerialException:
            pass
        finally:
            self.sampling = False
            self.stop_event.set()
            if self.thread is not None:
                self.thread.join(timeout=2)
                live = self.thread.is_alive()
                if live:
                    print("live")
                else:
                    print("dead")

    def sample_data(self, duration=1):
        while not self.stop_event.is_set():
            if self.ser.in_waiting > 0:
                data = self.ser.read_until(b'\n')  # Read until newline character
                # data = ser.read(ser.in_waiting)  # Read all available bytes
                print(data)
                parts = data.split(b'\r')
                if parts[0].startswith(b'\x80\x06\x83') and len(parts) > 1:
                    xa = parts[0][3:-1].decode('ascii', errors='ignore')  # Skip first 3 and last byte
                    # Remove any unwanted characters (non-numeric)
                    cleaned_str = ''.join(filter(lambda x: x.isdigit() or x == '.', xa))
                    try:
                        xi = float(cleaned_str) - self.zero_point  # Convert to float and zero point
                    except ValueError:
                        print("Error:", cleaned_str)
                        continue  # Skip appending data if conversion fails

                    try:
                        bits = int(parts[1].strip())
                        voltage = 2 * float(bits) * 0.1875
                        yi = voltage / 50.0
                    except ValueError:
                        print("Error, no second part")
                        continue

                    try:
                        self.data.append((xi, yi))
                        self.plotter.update_plot(self.data)
                    except Exception as e:
                        print(f"Error in sampling thread: {e}")

    def get_data(self):
        return self.data

    def clear_data(self):
        self.data = []
        self.plotter.clear_plot1()
        print("Data cleared")
