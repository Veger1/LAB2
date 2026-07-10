# data_model.py
#
# UI-toolkit-agnostic data layer for the measurement app. Replaces the parallel
# name-keyed dicts in Data.py (data/plot_vars/trend_vars/offset_entry/save_vars/
# detrend_vars) with a single Measurement object per dataset. Never shows a
# dialog or touches a widget - callers (gui_qt.py) catch ValueError/OSError and
# decide how to present them.

import csv
import unicodedata
from dataclasses import dataclass, field
from queue import Queue
from typing import Callable, Optional

import numpy as np
from scipy.signal import savgol_filter


@dataclass
class Measurement:
    name: str
    original: tuple  # (list[float], list[float])
    extended: Optional[tuple] = None
    detrended: Optional[tuple] = None
    coefficients: Optional[tuple] = None
    results: dict = field(default_factory=dict)
    filtered: Optional[tuple] = None  # transient - recomputed on demand, never saved/loaded


@dataclass
class SaveResult:
    saved: list
    skipped_empty: list


@dataclass
class LoadResult:
    measurements: dict  # name -> Measurement, not yet merged into the store
    skipped_rows: int  # malformed/short rows that were ignored


@dataclass
class ImportResult:
    loaded: list
    skipped: list


class DataStore:
    def __init__(self):
        self.queue = Queue()  # Sampler pushes (x, y) tuples in here directly
        self.live_data = []
        self.measurements = {}

    # --- live data (acquisition buffer, not yet a named Measurement) ----------

    def clear_live_data(self):
        self.live_data = []

    def get_live_data(self):
        return self.live_data

    def get_number_live_data(self):
        return len(self.live_data)

    # --- measurement lifecycle -------------------------------------------------

    @staticmethod
    def _validate_name(name, existing_names):
        # Drop control/format characters (e.g. zero-width space U+200B) that
        # can be pasted in invisibly, pass a plain .strip(), and later fail to
        # encode when writing the save file.
        name = "".join(ch for ch in (name or "") if unicodedata.category(ch) not in ("Cc", "Cf"))
        name = name.strip()
        if not name:
            raise ValueError("Name cannot be empty.")
        if name in existing_names:
            raise ValueError(f"Name '{name}' already exists.")
        return name

    def add_measurement(self, name):
        if not self.live_data:
            raise ValueError("No live data captured yet - start sampling first.")
        name = self._validate_name(name, self.measurements)

        x_data, y_data = zip(*self.live_data)
        measurement = Measurement(name=name, original=(list(x_data), list(y_data)))
        self.measurements[name] = measurement
        self.extend_data(name)
        self.remove_trend(name)
        self.calc_ptp(name)
        return measurement

    def remove_measurement(self, name):
        self.measurements.pop(name, None)

    def rename_measurement(self, old_name, new_name):
        if old_name not in self.measurements:
            raise ValueError(f"Dataset '{old_name}' no longer exists.")
        new_name = new_name.strip()
        if new_name == old_name:
            return old_name
        new_name = self._validate_name(new_name, self.measurements)
        measurement = self.measurements.pop(old_name)
        measurement.name = new_name
        self.measurements[new_name] = measurement
        return new_name

    # --- numeric processing (ported from Data.py, with the guards added earlier) --

    _FILTER_POLYORDER = 2  # quadratic local fit - a reasonable default for smoothing profile data

    def update_filter(self, name, window_length):
        # Savitzky-Golay on the uniform 1mm-gridded `extended` data (not `original`,
        # which can be irregularly spaced / contain duplicate x - meaningless as input
        # to a filter that assumes uniform sampling). window_length is in mm/points
        # since the grid step is 1mm, so it has a direct physical meaning.
        measurement = self.measurements[name]
        if window_length <= 0:
            measurement.filtered = None
            return
        if measurement.extended is None:
            self.extend_data(name)
        x, y = measurement.extended

        window_length = max(int(window_length), self._FILTER_POLYORDER + 1)
        if window_length % 2 == 0:
            window_length += 1
        window_length = min(window_length, len(y) if len(y) % 2 else len(y) - 1)

        if window_length <= self._FILTER_POLYORDER:
            measurement.filtered = None  # not enough points to filter meaningfully
            return

        y_filtered = savgol_filter(y, window_length, self._FILTER_POLYORDER)
        measurement.filtered = (x, y_filtered)

    def extend_data(self, name):
        measurement = self.measurements.get(name)
        if measurement is None:
            return
        if measurement.extended is not None:
            return
        x_data = np.array(measurement.original[0])
        y_data = np.array(measurement.original[1])
        if len(x_data) == 0:
            raise ValueError(f"Dataset '{name}' has no data points.")
        unique_x_data = np.unique(x_data)  # remove duplicate x values, interpolation would fail otherwise
        compressed_y_data = [np.mean(y_data[np.isclose(x_data, x, atol=1e-5)]) for x in unique_x_data]
        new_x_data = np.arange(min(unique_x_data), max(unique_x_data) + 0.001, 0.001)
        new_y_data = np.interp(new_x_data, unique_x_data, compressed_y_data)
        measurement.extended = (new_x_data, new_y_data)

    def remove_trend(self, name):
        measurement = self.measurements.get(name)
        if measurement is None:
            return
        if measurement.extended is None:
            self.extend_data(name)

        a, b = self.calc_trend(name)
        if a is not None:
            x_data, y_data = measurement.extended
            y_data = y_data - (a * x_data + b)
            measurement.detrended = (x_data, y_data)
            measurement.coefficients = (a, b)

    def calc_trend(self, name):
        measurement = self.measurements.get(name)
        if measurement is None:
            return None, None
        if measurement.extended is None:
            self.extend_data(name)
        x_data = np.array(measurement.extended[0])
        y_data = np.array(measurement.extended[1])
        if len(x_data) < 2:  # polyfit needs at least 2 points for a linear fit
            return None, None
        a, b = np.polyfit(x_data, y_data, 1)
        return a, b

    def calc_ptp(self, name):
        measurement = self.measurements.get(name)
        if measurement is None:
            return
        if measurement.extended is None:
            self.extend_data(name)
        y_data = np.array(measurement.extended[1])
        measurement.results['ptp'] = np.ptp(y_data)  # raw Y range, linear trend included

    def compare_slope(self, name1, name2):
        if name1 not in self.measurements or name2 not in self.measurements:
            return None, None
        m1, m2 = self.measurements[name1], self.measurements[name2]
        if m1.coefficients is None:
            self.remove_trend(name1)
        if m2.coefficients is None:
            self.remove_trend(name2)
        if m1.coefficients is None or m2.coefficients is None:
            return None, None
        a1, _ = m1.coefficients
        a2, _ = m2.coefficients
        return a1, a2

    def calc_reference(self, reference_name, new_data):
        measurement = self.measurements.get(reference_name)
        if measurement is None or measurement.extended is None:
            return None
        ref_x, ref_y = measurement.extended
        x, y = new_data

        index = np.where(np.isclose(ref_x, x, atol=1e-5))[0]
        if len(index) == 0:
            return None
        return x, y - ref_y[index[0]]

    # --- persistence: original data only, filtered/extended are never saved/loaded --

    def save(self, path, names):
        selected = {name: self.measurements[name] for name in names if name in self.measurements}
        skipped_empty = [name for name, m in selected.items() if not m.original[0]]
        for name in skipped_empty:
            del selected[name]

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for name, measurement in selected.items():
                x_orig, y_orig = measurement.original
                writer.writerow([name, 'X'] + list(x_orig))
                writer.writerow([name, 'Y'] + list(y_orig))

        return SaveResult(saved=list(selected.keys()), skipped_empty=skipped_empty)

    def load(self, path):
        skipped_rows = 0
        loaded = {}
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 3 or row[1] not in ('X', 'Y'):  # only original data is ever loaded
                    skipped_rows += 1
                    continue
                name = row[0]
                if name not in loaded:
                    loaded[name] = Measurement(name=name, original=([], []))
                try:
                    values = list(map(float, row[2:]))
                except ValueError:
                    skipped_rows += 1
                    continue
                if row[1] == 'X':
                    loaded[name].original = (values, loaded[name].original[1])
                else:
                    loaded[name].original = (loaded[name].original[0], values)

        return LoadResult(measurements=loaded, skipped_rows=skipped_rows)

    def import_measurements(self, loaded, resolve_conflict: Callable[[str], Optional[str]]):
        loaded_names = []
        skipped_names = []

        for name, measurement in loaded.items():
            if not measurement.original[0] or not measurement.original[1]:
                skipped_names.append(name)
                continue

            if name in self.measurements:
                new_name = resolve_conflict(name)
                if new_name is None:
                    skipped_names.append(name)
                    continue
                name = new_name
                measurement.name = name

            try:
                self.measurements[name] = measurement
                self.extend_data(name)
                self.remove_trend(name)
                self.calc_ptp(name)
                loaded_names.append(name)
            except Exception:
                self.measurements.pop(name, None)
                skipped_names.append(name)

        return ImportResult(loaded=loaded_names, skipped=skipped_names)
