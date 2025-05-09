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
        self.range = 500
        self.lat_min, self.lat_max = 36.0, 42.0
        self.lon_min, self.lon_max = -110.0, -100.0
        self.limits = [self.lat - self.range / 60, self.lat + self.range / 60,
                       self.lon - self.range / math.cos(self.latr), self.lon + self.range / math.cos(self.latr)]

        # Load US states
        url = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
        allStates = gpd.read_file(url)
        self.USStates = allStates[allStates["admin"] == "United States of America"]

        # Data to train model with
        df_DEN = pd.read_csv("KDEN.csv", usecols=[0,1,2,3], names=["lat", "lon", "alt", "grad"])
        df_DEN.dropna(inplace=True)
        df_COS = pd.read_csv("KCOS.csv", usecols=[0,1,2,3], names=["lat", "lon", "alt", "grad"])
        df_COS.dropna(inplace=True)

        # Extract only numerical features (not timestamp or icao24)
        X_train_DEN = df_DEN[["lat", "lon", "alt", "grad"]].values
        X_train_COS = df_COS[["lat", "lon", "alt", "grad"]].values
        self.X_train_DEN = X_train_DEN
        self.X_train_COS = X_train_COS

        # Train Isolation Forest
        self.model_DEN = IForest(contamination=0.01, max_samples="auto", random_state=42)
        self.model_DEN.fit(X_train_DEN)
        self.model_COS = IForest(contamination=0.01, max_samples="auto", random_state=42)
        self.model_COS.fit(X_train_COS)

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
        def distance_sq_nm(lat1, lon1, lat2, lon2):
            latr = math.radians((lat1 + lat2) / 2)
            return ((lat1 - lat2) ** 2 + ((lon1 - lon2) * math.cos(latr)) ** 2)

        den_lat, den_lon = self.denver
        cos_lat, cos_lon = self.cos

        valid_aircraft = []
        states = []
        colors = []

        for s in snap.aircraft:
            if s.get("lat") is None or s.get("lon") is None:
                continue
            if s["category"] not in ["A3", "A4", "A5"] or (s["gs"] or 0) < 50:
                continue

            lat, lon = s["lat"], s["lon"]
            alt = s["alt_baro"] if s["alt_baro"] != "ground" else 0
            grad = 60 * (0 if s["baro_rate"] is None else s["baro_rate"]) / (s["gs"] or 1)

            # Compute distances (squared) in nautical miles
            d_cos_sq = distance_sq_nm(lat, lon, cos_lat, cos_lon)
            d_den_sq = distance_sq_nm(lat, lon, den_lat, den_lon)
            in_cos_range = d_cos_sq < (25 / 60) ** 2
            in_den_range = d_den_sq < (25 / 60) ** 2

            if in_cos_range:
                outlier = self.model_COS.predict([[lat, lon, alt, grad]])[0]
                color = "red" if outlier else "blue"
            elif in_den_range:
                outlier = self.model_DEN.predict([[lat, lon, alt, grad]])[0]
                color = "red" if outlier else "blue"
            else:
                outlier = False
                color = "gray"

            states.append([lat, lon])
            colors.append(color)
            valid_aircraft.append({
                "lat": lat,
                "lon": lon,
                "alt": alt,
                "grad": grad,
                "icao": s["hex"],
                "outlier": outlier,
                "color": color
            })


        if states:
            xs = [lon for _, lon in states]
            ys = [lat for lat, _ in states]
            self.ax.scatter(xs, ys, c=colors)
            self.flights = valid_aircraft
        else:
            self.flights = []

        # Legend using dot markers
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Nominal', markerfacecolor='blue', markersize=8),
            Line2D([0], [0], marker='o', color='w', label='Anomalous', markerfacecolor='red', markersize=8),
            Line2D([0], [0], marker='o', color='w', label='Unmonitored (outside range)', markerfacecolor='gray', markersize=8),
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

        # Determine closest flight to click
        for flight in self.flights:
            dx = flight["lat"] - click_lat
            dy = flight["lon"] - click_lon
            dist = dx ** 2 + dy ** 2
            if dist < min_dist:
                min_dist = dist
                closest = flight

        # Determine altitude and gradient comparison depending on click point
        # if closest:
        #     dist_den = (closest["lat"] - self.denver[0])**2 + ((closest["lon"] - self.denver[1]) / math.cos(self.latr))**2
        #     dist_cos = (closest["lat"] - self.cos[0])**2 + ((closest["lon"] - self.cos[1]) / math.cos(self.latr))**2

        #     if dist_den < dist_cos and dist_den < (25 / 60)**2:
        #         X_train = self.X_train_DEN
        #     elif dist_cos < (25 / 60)**2:
        #         X_train = self.X_train_COS
        #     else:
        #         X_train = None

        #     if X_train is not None:
        #         alt_min, alt_max = X_train[:, 2].min(), X_train[:, 2].max()
        #         grad_min, grad_max = X_train[:, 3].min(), X_train[:, 3].max()
        #         extra_info = f"Altitude Range: {alt_min:.0f}–{alt_max:.0f} ft\nDescent Gradient Range: {grad_min:.2f}–{grad_max:.2f}"
        #     else:
        #         extra_info = "Not part of a model area."

        info = (
            f"{'Anomalous' if closest['outlier'] else 'Nominal'} Flight\n"
            f"ICAO24: {closest['icao']}\n"
            f"Lat: {closest['lat']:.4f}, Lon: {closest['lon']:.4f}\n"
            f"Altitude: {closest['alt']} ft\n"
            f"Descent Gradient: {closest['grad']:.2f}\n"
            #f"{extra_info}"
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
