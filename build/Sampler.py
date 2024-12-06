from time import sleep
import serial
import serial.tools.list_ports
import threading
from tkinter import messagebox
import numpy as np



class Sampler:
    def __init__(self, root, data):
        self.data_holder = data
        self.in_queue = data.queue
        self.ser = None
        self.sampling = False
        self.data = []
        self.last_data = None  # Last data point for setting zero point
        self.flip_orientation = False
        self.thread = None
        self.zero_point = 0
        self.serial_available = False
        self.port = None
        self.connect()
        self.stop_event = threading.Event()

    def set_zero_point(self):
        if self.data_holder.live_data:
            print("Zero point set", self.last_data)
            self.zero_point = self.last_data

    @staticmethod
    def find_arduino_port():  # Automatically find the Arduino port
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in ports:
            # Check if the description or hardware ID matches Arduino
            if 'Arduino' in desc or 'VID:PID=2341' in hwid:
                return port
        return None

    def connect(self):  # Connect to the Arduino if 'connect' button is pressed.
        if self.port is None:
            self.port = self.find_arduino_port()
            if self.port:
                try:
                    self.ser = serial.Serial(self.port, 19200, timeout=0.1)
                    self.serial_available = True
                    print("Serial port initialized")
                except serial.SerialException:
                    print("Serial port could not be opened: {e}")
                    self.serial_available = False
            else:
                print("Arduino not found on any port")
                self.serial_available = False

    def is_connected(self):  # Possibly redundant but works
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

    def start_sampler(self):
        try:
            self.ser.write(b'G')
        except AttributeError as e1:
            print(f"AttributeError: {e1}")
        except serial.serialutil.SerialException as e2:
            print(f"SerialException: {e2}")
        else:
            self.sampling = True
            self.stop_event.clear()  # Clear the stop event
            self.thread = threading.Thread(target=self.sample_data, args=(self.stop_event,), daemon=True)
            self.thread.start()
        return self.sampling

    def offline_sampler(self):
        self.sampling = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.sampler, args=(self.stop_event,), daemon=True)
        self.thread.start()
        return self.sampling

    def stop_sampling(self):
        try:
            self.ser.write(b'S')  # Send 'S' to stop Serial1 (hardware Serial with Laser)
        except AttributeError as e1:
            print(f"AttributeError: {e1}")
        except serial.serialutil.SerialException as e2:
            print(f"SerialException: {e2}")
        finally:
            self.sampling = False
            self.stop_event.set()
            if self.thread is not None:
                self.thread.join(timeout=0.2)  # Give the sampling thread 0.2 second to finish. GUI is unresponsive
                # during this time.
                # live = self.thread.is_alive()
                # if live:
                #     print("Sampler thread live")
                # else:
                #     print("Sampler thread dead")

    def sample_data(self, duration=1):  # Runs continuously until stop_event is set.
        while not self.stop_event.is_set():
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read_until(b'\n')  # Read until newline character
                    print(data)
                    parts = data.split(b'\r')
                    if parts[0].startswith(b'\x80\x06\x83') and len(parts) > 1:
                        xa = parts[0][3:-1].decode('ascii', errors='ignore')  # Skip first 3 and last byte
                        # Remove any unwanted characters (non-numeric)
                        cleaned_str = ''.join(filter(lambda x: x.isdigit() or x == '.', xa))
                        xi = self.convert_x_data(cleaned_str)
                        yi = self.convert_y_data(parts[1])
                        if xi is None or yi is None:
                            continue
                        self.in_queue.put((xi, yi))

            except serial.serialutil.SerialException:
                self.stop_event.set()
                """ Some extra handling needed here """
            except Exception:
                self.stop_event.set()

    def convert_x_data(self, cleaned_str):
        try:
            xi = float(cleaned_str)  # Convert to float
            """
            Add outlier detection here
            """
            if self.data_holder.ignore_limits:
                if xi < self.data_holder.get_min_x() or xi > self.data_holder.get_max_x():
                    return None
            self.last_data = xi
            xi = xi - self.zero_point  # Subtract zero point
            if self.flip_orientation:  # Flip orientation if needed
                xi = -xi
        except ValueError:
            print("Error:", cleaned_str)
            return None
        return xi

    @staticmethod
    def convert_y_data(part):
        try:
            bits = int(part.strip())
            voltage = 2 * float(bits) * 0.1875
            yi = voltage / 50.0
        except ValueError:
            print("Error, no second part")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
        return yi

    def sampler(self, duration=1):
        x = 0.0
        while not self.stop_event.is_set():
            y = np.sin(x) + x
            x += 0.1
            self.last_data = x
            xi = x - self.zero_point  # Subtract zero point
            if self.flip_orientation:  # Flip orientation if needed
                xi = -xi
            self.in_queue.put((xi, y))
            sleep(0.01)
