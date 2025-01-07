#!/usr/bin/python3
"""Pulls trace data for all aircraft and outputs to files in ./traceall_out"""

from adsblookup import bincraft, classes, adsb_trace
from adsblookup.classes import *

from tqdm import tqdm
import pandas as pd
import threading
import os
import concurrent.futures
import re
import types
import json

def __pull_all(hexes:list):
    """Pull traces for every hex with multithread."""
    output_folder = "traceall_out"
    def pull(hex:str):
        """Pull a single aircraft trace"""
        trace = adsb_trace.pull_trace(hex)
        return trace
    
    def write(future):
        """Callback function to write trace data to file"""
        result = future.result()
        pbar.update(1)
        if result == None:
            return
        icao = result.icao
        path = os.path.join(output_folder, icao)
        with open (path, 'wt') as f:
            f.write(json.dumps(result,indent=4))    

    # Create the output folder
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    pbar = None
    with tqdm(total=len(hexes)) as _pbar:
        pbar = _pbar
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for i in range(len(hexes)):
                # Queue the trace pull for multithread execution
                future:concurrent.futures.Future = executor.submit(pull, hex=hexes[i])
                # Note: use callback function to prevent memory leak from holding reference to futures
                future.add_done_callback(write)

def pull_all():
    snapshot = bincraft.pull_snapshot()
    
    # Get all ICAO hexes
    hexes = []
    for ac in snapshot.aircraft:
        ac:AdsbAircraft
        hex = ac.hex
        hex = re.sub('[^A-Za-z0-9]+', '', hex)
        hexes.append(hex)
    
    #get trace of all aircraft
    __pull_all(hexes)
    
if __name__=="__main__":
    pull_all()