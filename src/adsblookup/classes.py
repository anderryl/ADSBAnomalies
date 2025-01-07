from typing import List

class DotDict(dict):
    """Wrapper for dict enabling dot notation access to dictionary attributes"""

    def __getattr__(self, name) -> any:
        a = self.get(name)
        if a is not None:
            return a
        elif name in super().__getattribute__("__dict__"):
            return super().__getattribute__(self, name)
        else:
            return None

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Serializable(DotDict):
    def toJson(self):
        return json.dumps(self, indent=4)

    def __str__(self):
        return json.dumps(self, indent=4, ensure_ascii=False)

    def __repr__(self):
        return self.__str__()


class AdsbAircraft(Serializable):
    """Encapsulates data for a single aircraft at a single moment"""
    hex: str
    "24-bit ICAO aircraaircraft:ft address"
    seen_pos: float
    "how long ago since \'now\' timestamp position was updated"
    seen_pos: float
    "how long ago since last \'now\' timesetamp since message was received"
    lon: int
    "longitude in decimal degrees"
    lat: int
    "latitude in decimal degrees"
    baro_rate: float
    "Rate of change of barometric altitude, feet/minute"
    geom_rate: float
    "Rate of change of geometric (GNSS / INS) altitude, feet/minute"
    alt_baro: float
    "the aircraft barometric altitude in feet"
    alt_geom: float
    "geometric (GNSS / INS) altitude in feet referenced to the WGS84 ellipsoid"
    nav_altitude_mcp: float
    "selected altitude from the Mode Control Panel / Flight Control Unit (MCP/FCU) or equivalent equipment"
    nav_altitude_fms: float
    "selected altitude from the Flight Manaagement System (FMS) (2.2.3.2.7.1.3.3)"
    nav_heading: float
    "selected heading (True or Magnetic is not defined in DO-260B, mostly Magnetic as that is the de facto standard) (2.2.3.2.7.1.3.7)"
    gs: float
    "ground speed in knots"
    roll: float
    "Roll, degrees, negative is left roll"
    track: int
    "true track over ground in degrees (0-359)"
    track_rate: float
    "Rate of change of track, degrees/second"
    mag_heading: float
    "Heading, degrees clockwise from magnetic north"
    true_heading: float
    "Heading, degrees clockwise from true north (usually only transmitted on ground, in the air usually derived from the magnetic heading using magnetic model WMM2020)"
    wd: float
    "wind direction calculated from ground track, true heading, true airspeed and ground speed"
    ws: float
    "wind speed calculated from ground track, true heading, true airspeed and ground speed"
    oat: float
    "Outside Air Temperature in degrees Celsius"
    tat: float
    "Total Air Temperature in degrees Celsius"
    messageRate: int
    "number of messages received per second from this aircraft"
    category: str
    "emitter category to identify particular aircraft or vehicle classes (values A0 - D7) (2.2.3.2.5.2)"
    nic: str
    "Navigation Integrity Category (2.2.3.2.7.2.6) A-D"
    nav_modes: str
    "set of engaged automation modes: autopilot, vnav, althold, approach, lnav, tcas"


class AdsbSnapshot(Serializable):
    """Represents a snapshot taken from bincraft."""

    def __init__(self, data: dict) -> None:
        """Initialize Adsb_Header from bincraft data"""

        def load_dict(obj: object, data: dict):
            """Loads class's annotated attributes from dict"""
            for key in obj.__annotations__.keys():
                if key in data:
                    value = data[key]
                    obj.__setattr__(key, value)
                else:
                    print(f"Warning: Could not find {key} key in data")

        load_dict(self, data)
        aircraft = self.aircraft
        self.aircraft = []

        # Load aircrafts into AdsbAircraft
        for ac_data in data["aircraft"]:
            ac: AdsbAircraft = AdsbAircraft()
            load_dict(ac, ac_data)
            self.aircraft.append(ac)

    now: str
    "UNIX timestamp of the dataset that was pulled from adsbexchange"
    global_ac_count_withpos: int
    "number of aircraft with position"
    south: int
    "latitude of the south border of the box which contains all the planes"
    west: int
    "latitude of teh west border of the box which contains all the planes"
    north: int
    "latitude of the north border of the box which contains all the planes"
    east: int
    "latitude of the east border of the box which contains all the planes"
    messages: int
    "number of messages received"
    aircraft: List[AdsbAircraft]
    "Aircrafts in this snapshot"


class AdsbTrace(Serializable):
    """Encapsulates ADSB trace data from adsbexchange.com"""

    f_military: bool
    """Whether aircraft is military"""
    f_interesting: bool
    """Whether aircraft is interesting"""
    f_pia: bool
    """Whether aircraft uses PIA program"""
    f_ladd: bool
    """Whether aircraft uses LADD program"""

    desc: str
    """Description of aircraft"""
    icao: str
    """ICAO of aircraft"""
    owner: str
    """Owner or operator of aircraft"""
    registration_num: str
    """Registration number of aircraft"""
    model_num: str
    """Model number of aircraft"""
    timestamp: str
    """The timestamp of the Trace in Unix Epoch seconds"""

    states: list
    """List of states captured by trace"""

    def __init__(self, data) -> None:
        data = DotDict(data)
        self.f_military = data.dbFlags & 1;
        self.f_interesting = data.dbFlags & 2;
        self.f_pia = data.dbFlags & 4;
        self.f_ladd = data.dbFlags & 8;
        self.desc: str = data.desc
        self.icao = data.icao
        self.owner = data.ownOp
        self.registration_num = data.r
        self.model_num = data.t
        self.timestamp = data.timestamp
        self.states = []
        for state in data.trace:
            self.states.append(AdsbTraceState(state))


class AdsbTraceState(Serializable):
    """Encapsulates data from a single state in an ADSB trace from adsbexchange.com"""

    timedelta: float
    """Number of seconds since the trace's first timestamp"""
    latitude: float
    """the latitude in decimal degrees"""
    longitude: float
    """the longitude in decimal degrees"""
    altitude: float
    """the aircraft barometric altitude in feet"""
    gs: float
    """ground speed"""
    track: str
    """true track over ground in degrees (0-359)"""
    climb_rate: float
    """Rate of change of barometric altitude, feet/minute"""
    type: str
    """type of underlying messages / best source of current data for this position / aircraft. See https://www.adsbexchange.com/ads-b-data-field-explanations/"""
    geom_alt: float
    """geometric (GNSS / INS) altitude in feet referenced to the WGS84 ellipsoid"""
    geom_rate: float
    """Rate of change of geometric (GNSS / INS) altitude, feet/minute"""
    ias: float
    """indicated air speed in knots"""
    roll: float
    """Roll, degrees, negative is left roll"""

    def __init__(self, state):
        state = SafeList(state)
        self.timedelta = state[0]
        self.latitude = state[1];
        self.longitude = state[2];
        self.altitude = state[3];
        self.gs = state[4];
        self.track = state[5];
        has_geom_rate = state[6] & 4;
        has_geom_alt = state[6] & 8;
        self.climb_rate = state[7];
        self.data = state[8];
        self.type = state[9];
        self.geom_alt = state[10] if has_geom_alt else None;
        self.geom_rate = state[11] if has_geom_rate else None;
        self.ias = state[12];
        self.roll = state[13];
        # self.rId = state[14];


import json


def write_dict(dict, filename):
    with open(filename, "wt") as f:
        f.write(json.dumps(dict, indent=4))


class SafeList(list):
    """Wrapper for list that returns None if key is not found in list"""

    def __init__(self, l):
        self.l = l

    def __getitem__(self, key):
        return self.l[key] if (key >= 0 and key < len(self.l)) else None