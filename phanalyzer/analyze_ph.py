# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import phclient
import sys

from analyze import PerfDatum, TalosAnalyzer

pc = phclient.Client()

(projectname, signature) = (sys.argv[1], sys.argv[2])

s = pc.get_series(projectname, signature, time_interval=phclient.TimeInterval.NINETY_DAYS)

perf_data = []
for (result_set_id, timestamp, geomean) in zip(
        s['result_set_id'], s['push_timestamp'], s['geomean']):
    perf_data.append(PerfDatum(result_set_id, 0, timestamp, geomean, None,
                               timestamp))

ta = TalosAnalyzer()
ta.addData(perf_data)
for r in ta.analyze_t(5, 5, 2):
    if r.state == 'regression':
        print (r.testrun_id, r.t, pc.get_revision(projectname, r.testrun_id)[0:12])
