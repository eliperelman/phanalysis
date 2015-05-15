#!/usr/bin/env python

from influxdb.influxdb08 import InfluxDBClient
from analyze import PerfDatum, TalosAnalyzer
import json
import re
import sys
import os
import requests

ALERT_HOST = os.getenv('ALERT_HOST', 'localhost')
ALERT_PORT = os.getenv('ALERT_PORT', '3000')
BRANCH = os.getenv('BRANCH', 'master')
DEVICE = os.getenv('DEVICE', 'flame-kk')
MEMORY = os.getenv('MEMORY', '319')


RAPTOR_APPS = [ ('Clock', 'clock.gaiamobile.org'),
                ('Phone', 'communications.gaiamobile.org'),
                ('Contacts', 'communications.gaiamobile.org'),
                ('Calendar', 'calendar.gaiamobile.org'),
                ('Camera', 'camera.gaiamobile.org'),
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

def get_revinfo(client):
    query = "select time, text from events where device='%s' and branch='%s' and memory='%s' and time > now() - 7d group by time(1000u) order asc;" % (DEVICE, BRANCH, MEMORY)
    results = client.query(query)

    revinfo = {}
    for (timestamp, sequence_number, text) in results[0]['points']:
        (gaia_revision, gecko_revision) = re.match("^Gaia: (.*)<br/>Gecko: (.*)$", text).groups()
        revinfo[timestamp] = (gaia_revision, gecko_revision)

    return revinfo

def get_alerts(client, revinfo, appname, context):
    numbers = client.query("select time, mean(value) from coldlaunch.visuallyLoaded where appName = '%s' and context = '%s' and device='%s' and branch='%s' and memory='%s' and time > now() - 7d group by time(1000u) order asc;" % (appname, context, DEVICE, BRANCH, MEMORY))

    perf_data = []
    values = []
    ret = []

    if not numbers:
        return ret

    for (timestamp, value) in numbers[0]['points']:
        if not timestamp in revinfo:
            continue
        else:
            gaia_rev = revinfo[timestamp][0]
            gecko_rev = revinfo[timestamp][1]
            perf_data.append(B2GPerfDatum(timestamp, value, gaia_revision=gaia_rev, revision=gecko_rev))

    ta = TalosAnalyzer()
    ta.addData(perf_data)
    vals = ta.analyze_t()
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
    all_raptor_apps = [re.sub('[ -]', '', r[0].lower()) for r in RAPTOR_APPS]

    if not apps_to_process:
        apps_to_process = all_raptor_apps

    client = InfluxDBClient(host, 8086, username, password, 'raptor')
    revinfo = get_revinfo(client)

    resultdict = ({
        'branch': BRANCH,
        'device': DEVICE,
        'memory': MEMORY,
        'results': {}
    })
    for app_to_process in apps_to_process:
        if app_to_process not in all_raptor_apps:
            print "ERROR: App %s does not exist?!" % app_to_process
            sys.exit(1)
        for (appname, context) in RAPTOR_APPS:
            if re.sub('[ -]', '', appname.lower()) == app_to_process:
                resultdict['results'][app_to_process] = get_alerts(client, revinfo, appname, context)

    url = 'http://%s:%s/' % (ALERT_HOST, ALERT_PORT)
    headers = {'Content-Type': 'application/json'}
    req = requests.post(url, data=json.dumps(resultdict), headers=headers)

    print req.status_code
    print req.content

if __name__ == "__main__":
    cli()
