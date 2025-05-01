import sys
import os
# Set Qt plugin path manually to fix cocoa not found error
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = (
    "/Users/emmanualmathew/Desktop/ADSBAnomalies/src/.venv/lib/python3.9/site-packages/PyQt5/Qt5/plugins/platforms"
)
import math
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QMainWindow, QApplication
from PyQt5.QtCore import QTimer
from pyod.models.iforest import IForest

from bincraft import pull_snapshot

class FlightMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Static config
        self.lat = 38.8058
        self.lon = -104.701
        self.latr = self.lat / 57.3
        self.range = 100
        self.lat_min, self.lat_max = 36.0, 42.0
        self.lon_min, self.lon_max = -110.0, -100.0
        self.limits = [self.lat - self.range / 60, self.lat + self.range / 60,
                       self.lon - self.range / math.cos(self.latr), self.lon + self.range / math.cos(self.latr)]

        # Load US states
        url = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
        allStates = gpd.read_file(url)
        self.USStates = allStates[allStates["admin"] == "United States of America"]

        # Train IForest
        
        df = pd.read_csv("colorado_flights.csv")

        # Drop rows with any missing values (if any)
        df.dropna(inplace=True)

        # Extract only numerical features (not timestamp or icao24)
        X_train = df[["lat", "lon", "alt_baro", "gs", "baro_rate"]].values

        # Train Isolation Forest
        self.model = IForest(contamination=0.01, max_samples="auto", random_state=42)
        self.model.fit(X_train)

        # Airports
        self.denver = (39.8561, -104.6737)
        self.cos = (38.8058, -104.7005)

        # Set up UI
        self.label = QLabel("Click a flight to view details", self)
        self.label.setStyleSheet("font-size: 16px; padding: 5px;")

        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect("button_press_event", self.on_click)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Start update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_map)
        self.timer.start(1000)

    def update_map(self):
        self.ax.clear()

        self.ax.set_xlim(self.lon_min, self.lon_max)
        self.ax.set_ylim(self.lat_min, self.lat_max)

        # Base map and airports
        self.USStates.plot(ax=self.ax, color="white", edgecolor="black")
        for name, (lat, lon) in {
            "Denver (DEN)": self.denver,
            "Colorado Springs (COS)": self.cos
        }.items():
            self.ax.plot(lon, lat, marker='s', color='green', markersize=6)
            self.ax.text(lon + 0.2, lat, name, fontsize=9, color='green')

        # Pull flight data
        snap = pull_snapshot([self.lat_min, self.lat_max, self.lon_min, self.lon_max])
        valid_aircraft = [
            s for s in snap.aircraft
                if s["category"] in ["A3", "A4", "A5"] and (s["gs"] or 0) > 50 and s.get("lat") is not None and s.get("lon") is not None and self.lat is not None and self.lon is not None
                and ((s["lat"] - self.lat) ** 2 + ((s["lon"] - self.lon) / math.cos(self.latr)) ** 2) < (self.range / 60) ** 2
        ]
        states = [
            [
                s["lat"], s["lon"],
                (s["alt_baro"] if s["alt_baro"] != "ground" else 0),
                s["gs"],
                s["baro_rate"]
                #60 * (0 if s["baro_rate"] is None else s["baro_rate"]) / (s["gs"] or 1)
            ]
            for s in valid_aircraft
        ]

        if states:
            X = np.array(states)
            outliers = self.model.predict(X)
            xs = X[:, 1]
            ys = X[:, 0]
            colors = ['red' if o else 'blue' for o in outliers]
            self.ax.scatter(xs, ys, c=colors)

            # Store flight info for click detection
            self.flights = [
                {"lat": lat, "lon": lon, "outlier": out, "alt": alt, "grad": grad, "icao": s["hex"]}
                for s, (lat, lon, alt, grad), out in zip(valid_aircraft, states, outliers)
            ]
        else:
            self.flights = []

        # Legend using dot markers
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Nominal', markerfacecolor='blue', markersize=8),
            Line2D([0], [0], marker='o', color='w', label='Anomalous', markerfacecolor='red', markersize=8),
            Line2D([0], [0], marker='s', color='w', label='Airport', markerfacecolor='green', markersize=8),
        ]
        self.ax.legend(handles=legend_elements, loc='upper right')

        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")

        self.canvas.draw()

    def on_click(self, event):
        if not self.flights or event.xdata is None or event.ydata is None:
            return

        click_lon, click_lat = event.xdata, event.ydata
        min_dist = float("inf")
        closest = None

        for flight in self.flights:
            dx = flight["lat"] - click_lat
            dy = flight["lon"] - click_lon
            dist = dx ** 2 + dy ** 2
            if dist < min_dist:
                min_dist = dist
                closest = flight

        if closest and min_dist < 0.05:  # small distance threshold
            info = (
                f"{'Anomalous' if closest['outlier'] else 'Nominal'} Flight\n"
                f"ICAO24: {closest['icao']}\n"
                f"Lat: {closest['lat']:.4f}, Lon: {closest['lon']:.4f}\n"
                f"Altitude: {closest['alt']} ft\n"
                f"Descent Gradient: {closest['grad']:.2f}"
            )
            self.label.setText(info)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flight Tracker")
        self.setGeometry(100, 100, 900, 700)
        self.flight_map = FlightMap(self)
        self.setCentralWidget(self.flight_map)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
