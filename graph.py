# -*- coding: utf-8 -*-

# Generates graphs for .edf files in directory

import csv
import datetime
import json
import math
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import os
from pprint import pprint
import pyedflib
import sys

IN_DIR = "data"
OUT_DIR = "output"
SECONDS_PER_GRAPH = 3600

def stackplot(marray, filename, seconds=None, start_time=None, ylabels=None):

    tarray = np.transpose(marray)
    data = tarray
    numSamples, numRows = tarray.shape

    dpi = 72
    plt.figure(figsize=(1920.0/dpi, 1080.0/dpi), dpi=dpi)

    if seconds:
        t = seconds * np.arange(numSamples, dtype=float)/numSamples
        if start_time:
            t = t+start_time
            xlm = (start_time, start_time+seconds)
        else:
            xlm = (0,seconds)

    else:
        t = np.arange(numSamples, dtype=float)
        xlm = (0,numSamples)

    ticklocs = []
    ax = plt.subplot(111)
    plt.xlim(*xlm)
    dmin = data.min()
    dmax = data.max()
    dr = (dmax - dmin)*0.7  # Crowd them a bit.
    y0 = dmin
    y1 = (numRows-1) * dr + dmax
    plt.ylim(y0, y1)

    segs = []
    for i in range(numRows):
        segs.append(np.hstack((t[:,np.newaxis], data[:,i,np.newaxis])))
        ticklocs.append(i*dr)

    offsets = np.zeros((numRows,2), dtype=float)
    offsets[:,1] = ticklocs

    lines = LineCollection(segs, offsets=offsets, transOffset=None)

    ax.add_collection(lines)

    # set the yticks to use axes coords on the y axis
    ax.set_yticks(ticklocs)
    ax.set_yticklabels(ylabels)

    plt.xlabel('time (s)')
    plt.style.use('fivethirtyeight')
    plt.savefig(filename, dpi=dpi, bbox_inches='tight')
    # plt.show()

for filename in os.listdir(IN_DIR):
    if filename.endswith(".edf"):

        f = pyedflib.EdfReader(os.path.join(IN_DIR, filename))
        n = f.signals_in_file
        dur = f.file_duration
        d = f.getStartdatetime()
        labels = f.getSignalLabels()

        print "---------\nProcessing: %s" % filename
        print "    %s signals in file:" % n
        print "    %s" % ",".join(labels)

        samples = f.getNSamples()[0]
        sigbufs = np.zeros((n, samples))
        for i in np.arange(n):
            sigbufs[i, :] = f.readSignal(i)

        samplesPerSecond = samples / dur

        segmentStartTime = d
        seconds = 0
        while seconds < dur:
            sd = segmentStartTime
            sampleIndex0 = seconds * samplesPerSecond
            sampleIndex1 = min(sampleIndex0 + SECONDS_PER_GRAPH * samplesPerSecond, samples)
            segmentSeconds = (sampleIndex1 - sampleIndex0) / samplesPerSecond
            segmentName = "%s/%s_%s-%s-%s_%s-%s-%s.png" % (OUT_DIR,filename.split(".")[0],sd.year,sd.month,sd.day,sd.hour,sd.minute,sd.second)

            if os.path.isfile(segmentName):
                print "    Skipping graph: %s" % segmentName
            else:
                print "    Building graph: %s" % segmentName
                stackplot(sigbufs[:, sampleIndex0:sampleIndex1], segmentName, seconds=segmentSeconds, ylabels=labels)

            seconds += SECONDS_PER_GRAPH
            segmentStartTime += datetime.timedelta(seconds=segmentSeconds)
