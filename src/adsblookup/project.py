#!/usr/bin/python3

from bincraft import *
from utils import find_airports


def pull_trace_raw(icao: str, recent: bool = False, verbose=False):
    """Pull raw JSON data from adsbexchange.com.
    @icao: The 6 digit hex code representing the aircraft's ICAO identifier.
    @recent: If True, retrieves only the last 1-2 hours of trace data (less data over the wire)
    @verbose: If True, print errors for debugging.
    """
    headers = {
        'referer': 'https://globe.adsbexchange.com',
    }
    icao = icao.lower()

    # ADSB provides trace data for individual aircraft in the following scheme
    # We can choose to pull the full trace (up to 25 hours of history) with "trace_full_{icao}.json"
    #   or the last hour
    # URL subdirectory uses last 2 characters of icao
    url_full = f'https://globe.adsbexchange.com/data/traces/{icao[-2:]}/trace_full_{icao}.json'
    url_recent = f'https://globe.adsbexchange.com/data/traces/{icao[-2:]}/trace_recent_{icao}.json'
    url = url_recent if recent else url_full
    response = requests.get(url, headers=headers)
    if response.status_code >= 400:
        if verbose: print(f"Received bad status code {response.status_code}.")
        return None

    try:
        return response.json()
    except json.JSONDecodeError:
        if verbose: print(
            f"Failed to get JSON data from adsbexchange.com for icao hex {icao}: [{response.status_code}] {response.content}")
        return None


def pull_trace(icao: str, recent: bool = False):
    """Pull and parse JSON data from adsbexchange.com
    @icao: The 6 digit hex code representing the aircraft's ICAO identifier.
    @recent: If True, retrieves only the last 1-2 hours of trace data (less data over the wire)
    """
    raw = pull_trace_raw(icao)
    if raw is None:
        return None
    return AdsbTrace(raw)


def extract(trace):
    extracted = []
    for state in trace.states:
        try:
            data = [state["latitude"], state["longitude"], state["altitude"], 60 * state["climb_rate"] / state["gs"]]
        except Exception:
            continue
        if not (state['altitude'] == 'ground' or None in data):
            extracted.append(data)
    return extracted


def filter(aclat, aclon, tlat, tlon, threshold):
    if aclat is None or aclon is None:
        return False
    ds = (aclat - tlat) ** 2 + ((math.cos((aclat + tlat) / 2 / 57.3)) * (aclon - tlon)) ** 2
    return ds < ((threshold / 60) ** 2)


def update(tlat, tlon, output):
    a = pull_snapshot()
    thresh = 25
    downsampling = 20
    acs = [
        ac.hex for ac in a.aircraft
        if filter(ac.lat, ac.lon, tlat, tlon, thresh) and ac.hex is not None and ac.category in ['A3', 'A4', 'A5']
    ]
    frames = []
    for ac in acs:
        frames += [
            frame for frame in extract(pull_trace(ac, recent=True))
            if filter(frame[0], frame[1], tlat, tlon, thresh)
        ][::downsampling]
    if len(frames) == 0:
        print("Not enough data")
        exit(0)
    file = open("./" + output + ".csv", "a")
    for frame in frames:
        for item in frame:
            file.write(str(item) + ",")
        file.write("\n")
    file.close()
    print(output + " updated with " + str(len(frames)) + " frames...")


if __name__ == '__main__':
    for name, lat, long in find_airports():
        update(lat, long, name)
    """
    print("Frames: ", len(frames), "Aircraft: ", len(acs))
    x = np.array(frames)
    forest = IForest(max_samples=len(x))
    forest.fit(x)
    outliers = forest.predict(x)
    print("Outlier Predictions:")
    plt.figure()
    plt.scatter(x[:, 0], x[:, 1],  c=outliers, cmap='coolwarm', s=50)
    plt.show()

    plt.figure()[:, 2], x[:, 3], c=outliers, cmap='coolwarm', s=50)
    plt.show()
    plt.scatter(x
    """
