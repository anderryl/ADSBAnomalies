import sys
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import animation
from pyod.models.iforest import IForest

from bincraft import *

# os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
#     os.path.dirname(__file__),
#     "..", ".venv", "lib", "python3.9", "site-packages", "PyQt5", "Qt5", "plugins", "platforms"
# )

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class FlightMap(QWidget):
    def __init__(self, flights, parent=None,):
        super().__init__(parent)

        self.label = QLabel("Click a flight to view details", self)
        self.label.setStyleSheet("font-size: 16px; padding: 5px;")

        # Load world map
        url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
        world = gpd.read_file(url)

        # Flight data
        self.flights = flights
        df = pd.DataFrame(self.flights)
        self.gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326")

        # Create Matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        world.clip([-150, 25, -60, 50]).plot(ax=self.ax, color="white", edgecolor="black")
        self.scatter = self.gdf.plot(ax=self.ax, color="red")
        self.ax.set_title("Live Flight Tracking Map")

        # Embed into PyQt
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def on_click(self, event):
        if event.xdata is None or event.ydata is None:
            return
        
        click_lon, click_lat = event.xdata, event.ydata

        min_dist = float("inf")
        closest_flight = None

        for flight in self.flights:
            distx = flight["latitude"] - click_lat
            disty = flight["longitude"] - click_lon
            dist = distx**2 + disty**2
            if dist < min_dist:
                min_dist = dist
                closest_flight = flight
        
        if closest_flight != None and min_dist <=1:
            info = (
                f"Flight ID: {closest_flight['ID']}\n"
                f"Lat: {closest_flight['latitude']}, Lon: {closest_flight['longitude']}\n"
                f"Altitude: {closest_flight['altitude']} ft\n"
                f"Descent Gradient: {closest_flight['gradient']}"
            )
            self.label.setText(info)



class MainWindow(QMainWindow):
    def __init__(self, flights):
        super().__init__()
        self.setWindowTitle("Flight Tracker")
        self.setGeometry(100, 100, 800, 600)

        self.flight_map = FlightMap(flights, self)
        self.setCentralWidget(self.flight_map)


if __name__ == "__main__":

    lat = 38.8058
    latr = lat / 57.3
    lon = -104.701
    range = 25

    fig, ax = plt.subplots()
    #plt.show()
    limits = [lat - range / 60, lat + range / 60, lon - range / math.cos(latr), lon + range / math.cos(latr)]
    ax.set_xlim(limits[2], limits[3])
    ax.set_ylim(limits[0], limits[1])
    file = open("KCOS.csv")
    frames = file.read()
    file.close()
    frames = [np.array([float(col) for col in row.split(",") if len(col) > 0]) for row in frames.strip().split("\n")]
    frames = [frame for frame in frames if frame[2] < 20000]
    x = np.array(frames)
    forest = IForest(max_samples=len(x))
    forest.fit(x)

    while True:
        ax.clear()
        snap = pull_snapshot(limits)
        states = [
            [
                #state["hex"],
                state["lat"],
                state["lon"],
                (state["alt_baro"] if state["alt_baro"] != "ground" else 0),
                60 * (0 if state["baro_rate"] is None else state["baro_rate"]) / state["gs"]
            ]
            for state in snap.aircraft
            if state["category"] in ["A3", "A4", "A5"] and (state["gs"] or 1) > 50 and
               ((state["lat"] or 1) - lat) ** 2 + (((state["lon"] or 1) - lon) / math.cos(latr)) ** 2 < (
                           range / 60) ** 2
        ]
        ys = [state[0] for state in states]
        xs = [state[1] for state in states]
        outliers = forest.predict(np.array(states))
        print(outliers)
        ax.scatter(xs, ys, c=outliers, cmap="coolwarm")
        # Note that using time.sleep does *not* work here!
        plt.pause(0.1)
