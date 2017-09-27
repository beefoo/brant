# -*- coding: utf-8 -*-

import csv
import datetime
import json
import math
import numpy as np
import os
from pprint import pprint
import pyedflib
from stacklineplot import stackplot
import sys

DIR = "data"

for filename in os.listdir(DIR):
    if filename.endswith(".edf"):

        f = pyedflib.EdfReader(os.path.join(DIR, filename))
        n = f.signals_in_file
        dur = f.file_duration
        d = f.getStartdatetime()
        labels = f.getSignalLabels()

        print "----------\n%s:" % filename

        print "    datetime: %i-%i-%i %i:%02i:%02i" % (d.day,d.month,d.year,d.hour,d.minute,d.second)
        print "    duration: %i seconds (%s)" % (dur, datetime.timedelta(seconds=dur))
        # print "    %s signals in file:" % n
        # print "    %s" % ",".join(labels)

        # sigbufs = np.zeros((n, f.getNSamples()[0]))
        # for i in np.arange(n):
        #     sigbufs[i, :] = f.readSignal(i)

        # stackplot(sigbufs, ylabels=labels)
        # stackplot(sigbufs[:, :2000], ylabels=labels)
