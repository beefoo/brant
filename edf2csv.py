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

INFILE = "data/GUICHARD 081217.edf"
OUTFILE = "output/GUICHARD_081217.csv"
START_S = 21195
END_S = 21455

def mean(data):
    n = len(data)
    if n < 1:
      return 0
    else:
      return sum(data)/n

def stdev(data):
    var = variance(data)
    return math.sqrt(var)

def variance(data):
    if iter(data) is data:
      data = list(data)
    n = len(data)
    if n < 1:
      return 0
    else:
      c = mean(data)
      ss = sum((x-c)**2 for x in data)
      ss -= sum((x-c) for x in data)**2/len(data)
      return ss/n

def stackplot(marray, seconds=None, start_time=None, ylabels=None):

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
    plt.show()

f = pyedflib.EdfReader(INFILE)
n = f.signals_in_file
dur = f.file_duration
d = f.getStartdatetime()
labels = f.getSignalLabels()
labels = labels[:-1]

print "    %s signals in file:" % n
print "    %s" % ",".join(labels)

minSignal = f.getPhysicalMinimum(0)
maxSignal = f.getPhysicalMaximum(0)

samples = f.getNSamples()[0]
sigbufs = np.zeros((n, samples))
for i in np.arange(n):
    sigbufs[i, :] = f.readSignal(i)

samplesPerSecond = samples / dur
i0 = START_S * samplesPerSecond
i1 = END_S * samplesPerSecond

rows = np.transpose(sigbufs[:-1, i0:i1])
rows = rows.tolist()

# # normalize rows
# print "Normalizing rows"
# for i,row in enumerate(rows):
#     for j, col in enumerate(row):
#         rows[i][j] = round(1.0 * (col - minSignal) / (maxSignal - minSignal), 5)

# add seconds to rows
print "Adding time"
sStep = 1.0 / samplesPerSecond
for i, row in enumerate(rows):
    ms = int(round(i * sStep * 1000))
    rows[i] = [ms] + row[:]

# stackplot(sigbufs[:, i0:i1], seconds=END_S-START_S, ylabels=labels)

print "Writing to file"
with open(OUTFILE, 'wb') as f:
    w = csv.writer(f)
    w.writerow(["Time"] + labels[:])
    w.writerows(rows)
    print "Wrote %s rows to file" % len(rows)
