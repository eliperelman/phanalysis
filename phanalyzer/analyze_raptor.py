#!/usr/bin/env python

from influxdb.influxdb08 import InfluxDBClient
from analyze import PerfDatum, TalosAnalyzer
import datetime
import re
import sys

class B2GPerfDatum(PerfDatum):

    def __init__(self, push_timestamp, value, gaia_revision=None, **kwargs):
        PerfDatum.__init__(self, push_timestamp, value, **kwargs)
        self.gaia_revision = gaia_revision

if len(sys.argv) != 4:
    print "USAGE: %s <host> <username> <password>" % sys.argv[0]
    sys.exit(1)

(host, username, password) = sys.argv[1:]

client = InfluxDBClient(host, 8086, username, password, 'raptor')
numbers = client.query("select time, mean(value) from coldlaunch.visuallyLoaded where appName = 'Clock' and context = 'clock.gaiamobile.org' and device='flame-kk' and branch='master' and memory='319' and time > '2015-03-31' group by time(1s) order ASC;")
revinfo = client.query("select time, text from events where device='flame-kk' and branch='master' and memory='319' and time > '2015-03-30' group by time(1s) order ASC;")

sequence_rev_list = []
for (timestamp, sequence_number, text) in revinfo[0]['points']:
    (gaia_revision, gecko_revision) = re.match("^Gaia: (.*)<br/>Gecko: (.*)$",
                                               text).groups()
    sequence_rev_list.append((timestamp, gaia_revision, gecko_revision))

perf_data = []
values = []
for (timestamp, value) in numbers[0]['points']:
    # we sometimes have duplicate test runs for the same timestamp? or
    # the revision info is otherwise missing
    for (sequence_timestamp, gaia_revision, gecko_revision) in sequence_rev_list:
        if sequence_timestamp <= timestamp:
            revinfo = (sequence_timestamp, gaia_revision, gecko_revision)
        else:
            break
    perf_data.append(B2GPerfDatum(revinfo[0], value, gaia_revision=revinfo[1],
                                  revision=revinfo[2]))

ta = TalosAnalyzer()
ta.addData(perf_data)
vals = ta.analyze_t(5, 5, 3)
for (i, r) in enumerate(vals):
    if r.state == 'regression':
        prevr = vals[i-1]
        print "date: %s" % datetime.datetime.fromtimestamp(
            r.push_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        print "confidence (higher is more confident): %s" % r.t
        print "gecko revision: %s" % r.revision
        print "prev gecko revision: %s" % prevr.revision
        print "gaia revision: %s" % r.gaia_revision
        print "prev gaia revision: %s" % prevr.gaia_revision
        print "old average: %s" % r.historical_stats['avg']
        print "new average: %s" % r.forward_stats['avg']
        print "================================="
