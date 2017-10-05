# -*- coding: utf-8 -*-

# Generates graphs for .edf files in directory

import csv
import datetime
import json
import math
import os
import sys
import time

INFILE = "output/GUICHARD_081217.csv"
OUTFILE = "output/GUICHARD_081217.csv"


# Config
BPM = 75 # Beats per minute, e.g. 60, 75, 100, 120, 150
DIVISIONS_PER_BEAT = 16 # e.g. 4 = quarter notes, 8 = eighth notes, etc
VARIANCE_MS = 10 # +/- milliseconds an instrument note should be off by to give it a little more "natural" feel
PRECISION = 6 # decimal places after 0 for reading value
GAIN = 0.2 # base gain
TEMPO = 0.25 # base tempo
LABELS = ['Fp1','Fp2','F3','F4','C3','C4','P3','P4','O1','O2','F7','F8','T3','T4','T5','T6','A1','A2','Fz',
          'Cz','Pz','T2','T1','Oz']

# Files
INSTRUMENTS_INPUT_FILE = 'data/instruments.csv'
EEG_INPUT_FILE = 'output/GUICHARD_081217.csv'
REPORT_SUMMARY_OUTPUT_FILE = 'data/report_summary.csv'
REPORT_SUMMARY_CHANNEL_OUTPUT_FILE = 'data/report_channel_summary.csv'
REPORT_SEQUENCE_OUTPUT_FILE = 'data/report_sequence.csv'
INSTRUMENTS_OUTPUT_FILE = 'data/ck_instruments.csv'
SEQUENCE_OUTPUT_FILE = 'data/ck_sequence.csv'
VISUALIZATION_OUTPUT_FILE = 'visualization/data/eeg.json'
INSTRUMENTS_DIR = 'instruments/'

# Output options
WRITE_SEQUENCE = True
WRITE_REPORT = True
WRITE_JSON = False

# Calculations
BEAT_MS = round(60.0 / BPM * 1000)
MEASURE_MS = BEAT_MS * 4.0
ROUND_TO_NEAREST = round(BEAT_MS/DIVISIONS_PER_BEAT)
CHANNEL_COUNT = len(LABELS)
RANGE = [-100, 100]

print('Building sequence at '+str(BPM)+' BPM ('+str(BEAT_MS)+'ms per beat)')

# Initialize Variables
instruments = []
eeg = []
eeg_min = []
eeg_max = []
measures = []
abs_min = 0
abs_max = 0
sequence = []
hindex = 0
total_ms = 0

# For creating pseudo-random numbers
def halton(index, base):
  result = 0.0
  f = 1.0 / base
  i = 1.0 * index
  while(i > 0):
    result += f * (i % base)
    i = math.floor(i / base)
    f = f / base
  return result

# Mean of list
def mean(data):
    if iter(data) is data:
      data = list(data)
    n = len(data)
    if n < 1:
      return 0
    else:
      return sum(data)/n

# Variance of list
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

# Standard deviation of list
def stdev(data):
    var = variance(data)
    return math.sqrt(var)

# Find index of first item that matches value
def findInList(list, key, value):
  found = -1
  for index, item in enumerate(list):
    if item[key] == value:
      found = index
      break
  return found

# round {n} to nearest {nearest}
def roundToNearest(n, nearest):
  return 1.0 * round(1.0*n/nearest) * nearest

# Read instruments from file
with open(INSTRUMENTS_INPUT_FILE, 'rb') as f:
  r = csv.reader(f, delimiter=',')
  next(r, None) # remove header
  for name,channel,amp_min,amp_max,freq_min,freq_max,sync_min,sync_max,filename,from_gain,to_gain,tempo,tempo_offset,interval_phase,interval,interval_offset,active in r:
    if int(active):
      index = len(instruments)
      # build instrument object
      instrument = {
        'index': index,
        'name': name,
        'channel': channel,
        'amp_min': float(amp_min),
        'amp_max': float(amp_max),
        'freq_min': float(freq_min),
        'freq_max': float(freq_max),
        'sync_min': float(sync_min),
        'sync_max': float(sync_max),
        'file': INSTRUMENTS_DIR + filename,
        'from_gain': float(from_gain),
        'to_gain': float(to_gain),
        'tempo': float(tempo),
        'tempo_offset': float(tempo_offset),
        'interval_ms': int(int(interval_phase)*BEAT_MS),
        'interval': int(interval),
        'interval_offset': int(interval_offset)
      }
      # add instrument to instruments
      instruments.append(instrument)

# Count the number of waves in a given list of values
def getFrequency(data, _min, _max, _stdev):
  waves = 0.0
  threshold = _stdev / 2.0
  last_peak_value = None
  for i, value in enumerate(data):
    if i > 0 and i < len(data)-1:
      # Look for a peak that has a value that is more than a {threshold} than the last peak value
      if (value > data[i-1] and value > data[i+1] or value < data[i-1] and value < data[i+1]) and (last_peak_value is None or abs(value-last_peak_value) > threshold):
        last_peak_value = value
        waves += 1
  # wave(s) found
  return waves

def norm(value, a, b):
    n = 1.0 * (value - a) / (b - a)
    n = min(n, 1)
    n = max(n, 0)
    return n

def parseNumber(string):
    try:
        num = float(string)
        if "." not in string:
            num = int(string)
        return num
    except ValueError:
        return string

def parseRows(arr):
    for i, item in enumerate(arr):
        for key in item:
            arr[i][key] = parseNumber(item[key])
    return arr

def readCSV(filename):
    rows = []
    if os.path.isfile(filename):
        with open(filename, 'rb') as f:
            lines = [line for line in f if not line.startswith("#")]
            reader = csv.DictReader(lines, skipinitialspace=True)
            rows = list(reader)
            rows = parseRows(rows)
    return rows

eegData = readCSV(EEG_INPUT_FILE)
last_ms = 0
measure = []
next_measure = MEASURE_MS

# normalize data
for i,d in enumerate(eegData):
    for l in LABELS:
        val = eegData[i][l]
        eegData[i][l] = norm(val, RANGE[0], RANGE[1])

for d in eegData:
    ms = d['Time']
    if ms >= next_measure:
      measures.append({
        "readings": measure,
        "channels": [],
        "duration": MEASURE_MS
      })
      measure = []
      next_measure += MEASURE_MS
    else:
      measure.append([d[l] for l in LABELS])
    total_ms += (ms - last_ms)
    last_ms = ms

# Add the last measure
if len(measure) > 0:
    measures.append({
      "readings": measure,
      "channels": [],
      "duration": total_ms - MEASURE_MS * len(measures)
    })

# Report EEG data
print('Retrieved EEG data with '+ str(len(LABELS)) + ' channels')
print(str(len(measures)) + ' total measures created, ' + str(MEASURE_MS) + 'ms each')

# Keep track of min/max stdev for normalization
min_amp = None
max_amp = None
min_mean_amp = None
max_mean_amp = None
min_freq = None
max_freq = None
min_mean_freq = None
max_mean_freq = None
min_sync = None
max_sync = None

# Go through each measure
for mindex, measure in enumerate(measures):
  channels = []
  amps = []
  maxs = []
  freqs = []
  # Create an array of channel-value arrays
  for channel in range(CHANNEL_COUNT):
    channels.append([])
  for reading in measure["readings"]:
    for channel, value in enumerate(reading):
      channels[channel].append(value)
  # For each channel
  for cindex, channel in enumerate(channels):
    # Calculate stdev, min/max, freq
    _stdev = stdev(channel)
    _min = min(channel)
    _max = max(channel)
    _freq = getFrequency(channel, _min, _max, _stdev)
    amps.append(_stdev)
    freqs.append(_freq)
    maxs.append(_max)
    # Keep track of max/mins
    if _stdev > max_amp or max_amp is None:
      max_amp = _stdev
    if _stdev < min_amp or min_amp is None:
      min_amp = _stdev
    if _freq > max_freq or max_freq is None:
      max_freq = _freq
    if _freq < min_freq or min_freq is None:
      min_freq = _freq
    # Add to channel list to measure
    measures[mindex]["channels"].append({
      "index": cindex,
      "name": LABELS[cindex],
      "amp": _stdev,
      "max": _max,
      "freq": _freq
    })
  # Calculate max/means/stdevs
  mean_amp = mean(amps)
  sync = (stdev(amps) + stdev(freqs))/2.0
  mean_freq = mean(freqs)
  measures[mindex]["max"] = max(maxs)
  measures[mindex]["mean_amp"] = mean_amp
  measures[mindex]["mean_freq"] = mean_freq
  measures[mindex]["sync"] = sync
  # Keep track of min/max
  if mean_amp > max_mean_amp or max_mean_amp is None:
    max_mean_amp = mean_amp
  if mean_amp < min_mean_amp or min_mean_amp is None:
    min_mean_amp = mean_amp
  if mean_freq > max_mean_freq or max_mean_freq is None:
    max_mean_freq = mean_freq
  if mean_freq < min_mean_freq or min_mean_freq is None:
    min_mean_freq = mean_freq
  if sync > max_sync or max_sync is None:
    max_sync = sync
  if sync < min_sync or min_sync is None:
    min_sync = sync

# Normalize all values in measures
for mindex, measure in enumerate(measures):
  amp_delta = max_amp - min_amp
  amp_mean_delta = max_mean_amp - min_mean_amp
  freq_delta = max_freq - min_freq
  freq_mean_delta = max_mean_freq - min_mean_freq
  sync_delta = max_sync - min_sync
  # Normalize all values to between 0 and 1
  measures[mindex]["mean_amp"] = 1.0 * (measure["mean_amp"]-min_mean_amp) / amp_mean_delta
  measures[mindex]["mean_freq"] = 1.0 * (measure["mean_freq"]-min_mean_freq) / freq_mean_delta
  measures[mindex]["sync"] = 1.0 - 1.0 * (measure["sync"]-min_sync) / sync_delta
  # measures[mindex]["gain"] = measures[mindex]["mean_amp"] * (MAX_GAIN-MIN_GAIN) + MIN_GAIN
  for cindex, channel in enumerate(measure["channels"]):
    measures[mindex]["channels"][cindex]["amp"] = 1.0 * (channel["amp"]-min_amp) / amp_delta
    measures[mindex]["channels"][cindex]["freq"] = 1.0 * (channel["freq"]-min_freq) / freq_delta

# Returns list of valid instruments given measure data
def getInstruments(_instruments, _measure):
  valid_instruments = []
  for instrument in _instruments:
    if instrument["channel"]=="all" and _measure["mean_amp"]>=instrument["amp_min"] and _measure["mean_amp"]<instrument["amp_max"] and _measure["mean_freq"]>=instrument["freq_min"] and _measure["mean_freq"]<instrument["freq_max"] and _measure["sync"]>=instrument["sync_min"] and _measure["sync"]<instrument["sync_max"]:
      _instrument = instrument.copy()
      valid_instruments.append(_instrument)
  return valid_instruments

# Returns list of valid instruments given channel data
def getChannelInstruments(_instruments, _channel):
  valid_instruments = []
  for instrument in _instruments:
    if instrument["channel"]==_channel["name"] and _channel["amp"]>=instrument["amp_min"] and _channel["amp"]<instrument["amp_max"] and _channel["freq"]>=instrument["freq_min"] and _channel["freq"]<instrument["freq_max"]:
      _instrument = instrument.copy()
      valid_instruments.append(_instrument)
  return valid_instruments

# Determine instruments
for mindex, measure in enumerate(measures):
  _instruments = []
  _instruments.extend(getInstruments(instruments, measure))
  for cindex, channel in enumerate(measure["channels"]):
    # Add instruments based on channel, phase, measure
    _instruments.extend(getChannelInstruments(instruments, channel))
  measures[mindex]["instruments"] = _instruments

# Return if the instrument should be played in the given interval
def isValidInterval(instrument, elapsed_ms):
  interval_ms = instrument['interval_ms']
  interval = instrument['interval']
  interval_offset = instrument['interval_offset']
  return int(math.floor(1.0*elapsed_ms/interval_ms)) % interval == interval_offset

# Multiplier based on sine curve
def getMultiplier(percent_complete):
  radians = percent_complete * (math.pi / 2.0)
  multiplier = math.sin(radians)
  if multiplier < 0:
    multiplier = 0.0
  elif multiplier > 1:
    multplier = 1.0
  return multiplier

# Retrieve gain based on current beat
def getGain(instrument, total_ms, elapsed_ms):
  percent_complete = elapsed_ms / total_ms
  multiplier = getMultiplier(percent_complete)
  from_gain = instrument['from_gain']
  to_gain = instrument['to_gain']
  min_gain = min(from_gain, to_gain)
  gain = multiplier * (to_gain - from_gain) + from_gain
  gain = max(min_gain, round(gain, 2))
  return gain

# Add beats to sequence
def addBeatsToSequence(_instrument, _duration, _ms, _beat_ms, _round_to):
  global sequence
  global hindex
  beat_ms = int(roundToNearest((1.0/_instrument['tempo']) * _beat_ms, _round_to))
  offset_ms = int(_instrument['tempo_offset'] * beat_ms)
  ms = _ms + offset_ms
  previous_ms = int(ms)
  remaining_duration = int(_duration)
  elapsed_duration = offset_ms
  while remaining_duration >= beat_ms:
    elapsed_ms = int(ms)
    elapsed_beat = int((elapsed_ms-previous_ms) / beat_ms)
    # add to sequence if in valid interval
    if isValidInterval(_instrument, elapsed_ms):
      h = halton(hindex, 3)
      variance = int(h * VARIANCE_MS * 2 - VARIANCE_MS)
      sequence.append({
        'instrument_index': _instrument['index'],
        'instrument': _instrument,
        'position': 0,
        'gain': getGain(_instrument, _duration, elapsed_ms),
        'rate': 1,
        'elapsed_ms': max([elapsed_ms + variance, 0])
      })
      hindex += 1
    remaining_duration -= beat_ms
    elapsed_duration += beat_ms
    ms += beat_ms

# Build main sequence
ms = 0
for measure in measures:
  # measure_gain = sum(instrument['gain'] for instrument in measure['instruments'])
  for instrument in measure['instruments']:
    instrument['from_gain'] = 1.0 * instrument['from_gain'] * GAIN
    instrument['to_gain'] = 1.0 * instrument['to_gain'] * GAIN
    instrument['tempo'] = 1.0 * instrument['tempo'] * TEMPO
    addBeatsToSequence(instrument, measure['duration'], ms, BEAT_MS, ROUND_TO_NEAREST)
  ms += measure['duration']

# Calculate total time
total_seconds = int(1.0*total_ms/1000)
print('Total sequence time: '+time.strftime('%M:%S', time.gmtime(total_seconds)) + '(' + str(total_seconds) + 's)')

# Sort sequence
sequence = sorted(sequence, key=lambda k: k['elapsed_ms'])

# Add milliseconds to sequence
elapsed = 0
for index, step in enumerate(sequence):
  sequence[index]['milliseconds'] = step['elapsed_ms'] - elapsed
  elapsed = step['elapsed_ms']

# Write instruments to file
if WRITE_SEQUENCE and len(instruments) > 0:
  with open(INSTRUMENTS_OUTPUT_FILE, 'wb') as f:
    w = csv.writer(f)
    for index, instrument in enumerate(instruments):
      w.writerow([index])
      w.writerow([instrument['file']])
    f.seek(-2, os.SEEK_END) # remove newline
    f.truncate()
    print('Successfully wrote instruments to file: '+INSTRUMENTS_OUTPUT_FILE)

# Write sequence to file
if WRITE_SEQUENCE and len(sequence) > 0:
  with open(SEQUENCE_OUTPUT_FILE, 'wb') as f:
    w = csv.writer(f)
    for step in sequence:
      w.writerow([step['instrument_index']])
      w.writerow([step['position']])
      w.writerow([step['gain']])
      w.writerow([step['rate']])
      w.writerow([step['milliseconds']])
    f.seek(-2, os.SEEK_END) # remove newline
    f.truncate()
    print('Successfully wrote sequence to file: '+SEQUENCE_OUTPUT_FILE)

# Write summary files
if WRITE_REPORT:
  with open(REPORT_SUMMARY_OUTPUT_FILE, 'wb') as f:
    w = csv.writer(f)
    w.writerow(['Time', 'Amplitude', 'Frequency', 'Synchrony', 'Duration'])
    for mindex, measure in enumerate(measures):
      elapsed = mindex * MEASURE_MS
      elapsed_f = time.strftime('%M:%S', time.gmtime(int(elapsed/1000)))
      ms = int(elapsed % 1000)
      elapsed_f += '.' + str(ms)
      w.writerow([elapsed_f, measure['mean_amp'], measure['mean_freq'], measure['sync'], int(measure['duration'])])
    print('Successfully wrote summary file: '+REPORT_SUMMARY_OUTPUT_FILE)
  with open(REPORT_SUMMARY_CHANNEL_OUTPUT_FILE, 'wb') as f:
    w = csv.writer(f)
    w.writerow(LABELS)
    for mindex, measure in enumerate(measures):
      elapsed = mindex * MEASURE_MS
      elapsed_f = time.strftime('%M:%S', time.gmtime(int(elapsed/1000)))
      ms = int(elapsed % 1000)
      elapsed_f += '.' + str(ms)
      channels = [elapsed_f]
      for channel in measure["channels"]:
        channels.append(channel["amp"])
      w.writerow(channels)
    print('Successfully wrote channel summary file: '+REPORT_SUMMARY_CHANNEL_OUTPUT_FILE)

# Write sequence report to file
if WRITE_REPORT and len(sequence) > 0:
  with open(REPORT_SEQUENCE_OUTPUT_FILE, 'wb') as f:
    w = csv.writer(f)
    w.writerow(['Time', 'Instrument', 'Gain'])
    for step in sequence:
      instrument = instruments[step['instrument_index']]
      elapsed = step['elapsed_ms']
      elapsed_f = time.strftime('%M:%S', time.gmtime(int(elapsed/1000)))
      ms = int(elapsed % 1000)
      elapsed_f += '.' + str(ms)
      w.writerow([elapsed_f, instrument['file'], step['gain']])
    f.seek(-2, os.SEEK_END) # remove newline
    f.truncate()
    print('Successfully wrote sequence report to file: '+REPORT_SEQUENCE_OUTPUT_FILE)

# Write JSON data for the visualization
if WRITE_JSON:
  json_data = eeg
  json_data.insert(0, eeg_max)
  json_data.insert(0, eeg_min)
  json_data.insert(0, LABELS)
  with open(VISUALIZATION_OUTPUT_FILE, 'w') as outfile:
    json.dump(json_data, outfile)
  print('Successfully wrote to JSON file: '+VISUALIZATION_OUTPUT_FILE)
