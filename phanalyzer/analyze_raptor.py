#!/usr/bin/env python

from influxdb.influxdb08 import InfluxDBClient
from analyze import PerfDatum, TalosAnalyzer
import json
import re
import sys

RAPTOR_APPS = [ ('Clock', 'clock.gaiamobile.org'),
                ('Phone', 'communications.gaiamobile.org'),
                ('Contacts', 'communications.gaiamobile.org'),
                ('Calendar', 'calendar.gaiamobile.org'), # no data?
                ('E-Mail', 'email.gaiamobile.org'),
                ('FM Radio', 'fm.gaiamobile.org'),
                ('Gallery', 'gallery.gaiamobile.org'),
                ('Music', 'music.gaiamobile.org'),
                ('Settings', 'settings.gaiamobile.org'),
                ('Messages', 'sms.gaiamobile.org'),
                ('Video', 'video.gaiamobile.org') ]

class B2GPerfDatum(PerfDatum):

    def __init__(self, push_timestamp, value, gaia_revision=None, **kwargs):
        PerfDatum.__init__(self, push_timestamp, value, **kwargs)
        self.gaia_revision = gaia_revision

def get_alerts(client, appname, context):
    numbers = client.query("select time, mean(value) from coldlaunch.visuallyLoaded where appName = '%s' and context = '%s' and device='flame-kk' and branch='master' and memory='319' and time > '2015-03-31' group by time(1s) order ASC;" % (appname, context))
    revinfo = client.query("select time, text from events where device='flame-kk' and branch='master' and memory='319' and time > '2015-03-31' group by time(1s) order ASC;")

    sequence_rev_list = []
    for (timestamp, sequence_number, text) in revinfo[0]['points']:
        (gaia_revision, gecko_revision) = re.match("^Gaia: (.*)<br/>Gecko: (.*)$",
                                                   text).groups()
        sequence_rev_list.append((timestamp, gaia_revision, gecko_revision))

    perf_data = []
    values = []
    for (timestamp, value) in numbers[0]['points']:
        # we sometimes have duplicate test runs for the same timestamp? or
        # the revision info is otherwise missing. this is probably bad, and
        # resulting in inaccurate data...
        for (sequence_timestamp, gaia_revision, gecko_revision) in sequence_rev_list:
            if sequence_timestamp <= timestamp:
                revinfo = (sequence_timestamp, gaia_revision, gecko_revision)
            else:
                break
        perf_data.append(B2GPerfDatum(revinfo[0], value, gaia_revision=revinfo[1],
                                      revision=revinfo[2]))

    ta = TalosAnalyzer()
    ta.addData(perf_data)
    vals = ta.analyze_t()
    ret = []
    for (i, r) in enumerate(vals):
        if r.state == 'regression':
            prevr = vals[i-1]
            ret.append({ 'push_timestamp': r.push_timestamp,
                         'confidence': r.t,
                         'gecko_revision': r.revision,
                         'gaia_revision': r.gaia_revision,
                         'prev_gecko_revision': prevr.revision,
                         'prev_gaia_revision': prevr.gaia_revision,
                         'oldavg': r.historical_stats['avg'],
                         'newavg': r.forward_stats['avg'] })

    return ret

def cli():
    if len(sys.argv) < 4:
        print "USAGE: %s <host> <username> <password> [APP1] [APP2] ..." % sys.argv[0]
        sys.exit(1)

    (host, username, password) = sys.argv[1:4]
    apps_to_process = sys.argv[4:]
    all_raptor_apps = [r[0].lower() for r in RAPTOR_APPS]
    if not apps_to_process:
        apps_to_process = all_raptor_apps

    client = InfluxDBClient(host, 8086, username, password, 'raptor')

    resultdict = {}
    for app_to_process in apps_to_process:
        if app_to_process not in all_raptor_apps:
            print "ERROR: App %s does not exist?!" % app_to_process
            sys.exit(1)
        for (appname, context) in RAPTOR_APPS:
            if appname.lower() == app_to_process:
                resultdict[app_to_process] = get_alerts(client, appname, context)

    print json.dumps(resultdict)

if __name__ == "__main__":
    cli()
