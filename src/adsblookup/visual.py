from bincraft import pull_snapshot
from utils import pull_airport, find_airports

def extract(acs):
    return [
        [ac["lat"], ac["lon"], ac["alt_baro"], 60 * (ac["baro_rate"] if ac["baro_rate"] is not None else 0) / ac["gs"], ac["hex"]]
        for ac in acs
        if ac.category in ['A3', 'A4', 'A5']
    ]

ident = "KCOS"
lat, long = find_airports(preset=[ident])[0][1:]
print(lat, long)
print(pull_snapshot(box=(lat - 1, lat + 1, long - 1, long + 1)).aircraft[0:10])

print(extract(pull_snapshot(box=(lat - 1, lat + 1, long - 1, long + 1)).aircraft[0:10]))
