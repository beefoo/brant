# -*- coding: utf-8 -*-

# Analyzes .edf files in a directory

import csv
import datetime
import json
import math
import numpy as np
import os
from pprint import pprint
import pyedflib
import sys

DIR = "data"
total = 0

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

        total += dur

print "----------\nTotal: %s" % datetime.timedelta(seconds=total)
