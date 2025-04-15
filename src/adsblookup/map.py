import os
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
    os.path.dirname(__file__),
    "..", ".venv", "lib", "python3.9", "site-packages", "PyQt5", "Qt5", "plugins", "platforms"
)
import sys
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

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
    app = QApplication(sys.argv)
    flights = [
        {'ID': 'AO55', 'latitude': 37.7749, 'longitude': -122.4194, 'altitude': 3600, 'gradient': -50}, # San Francisco
        {'ID': "GE43", 'latitude': 34.0522, 'longitude': -118.2437, 'altitude': 4700, 'gradient': 0}, # Los Angeles
        {'ID': "DZ68", 'latitude': 40.7128, 'longitude': -74.0060, 'altitude': 5000, 'gradient': 25} # New York
        ]
    window = MainWindow(flights)
    window.show()
    sys.exit(app.exec_())
