def pull_airport(ident, airports):
    minim = 0
    maxim = len(airports) - 1
    midpoint = 0
    real = None
    while minim != maxim and ident != real:
        midpoint = int((minim + maxim) / 2)
        real = airports[midpoint][0]
        if ident < real:
            maxim = midpoint - 1
        if ident > real:
            minim = midpoint + 1
    return airports[midpoint]


def find_airports(preset=[]):
    lines = preset
    if preset == []:
        file = open("./" + "airports.txt")
        lines = [line for line in file.read().split("\n") if len(line) > 0]
        file.close()
    file = open("./" + "database.csv")
    airports = [[part for part in line.split(",") if len(part) > 0] for line in file.read().split("\n") if len(line) > 0]
    molded = []
    for airport in airports:
        try:
            molded.append([airport[0], float(airport[1]), float(airport[2])])
        finally:
            continue
    file.close()

    print(lines)

    return [pull_airport(ident, molded) for ident in lines]

def build_database():
    locs = [
        [part[1:-1] for part in line.split(",") if len(part) > 0]
        for line in open("./" + "airports.csv").read().split("\n") if len(line) > 0
    ]
    filtered = [[loc[3], loc[5], loc[6]] for loc in locs]
    ordered = sorted(filtered, key=lambda x: x[0])
    file = open("./" + "database.csv", "w")
    for order in ordered:
        for part in order:
            file.write(part + ",")
        file.write("\n")
    file.close()
