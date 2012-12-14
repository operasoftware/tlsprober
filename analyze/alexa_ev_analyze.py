#   Copyright 2010-2012 Opera Software ASA 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

'''
Created on 2. okt. 2010

@author: Yngve
'''

"""Report Renego patched/unpatched based on Alexa ranking only sites with EV certificates"""

import sys,os,subprocess,time,os.path

sys.path.insert(1, os.path.join(".."))

import libinit

from optparse import OptionParser
import probedb.standalone
import probedb.probedata2.models as ProbeData
import probedb.resultdb2.models as Results



options_config = OptionParser()

options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--threads", action="store", type="int", dest="threads", default=20)
options_config.add_option("--id", action="store", type="int", dest="run_id", default=0)
options_config.add_option("--verbose", action="store_true", dest="verbose")

(options, args) = options_config.parse_args()

if options.run_id:
	run = ProbeData.ProbeRun.objects.get(id = options.run_id)

	main_result_list = Results.ResultSummaryList.objects.filter(part_of_run__id=run.id)[0]

	patched = main_result_list.GetAnalyze(
				filter = {Results.ResultSummaryList.QUERY_CONDITION:[Results.ResultCondition.RESULTC_RENEGO, Results.ResultCondition.RESULTC_EXTENDED_VALIDATION_CERT]},
				summaries = {"hosts":[Results.ResultSummaryList.RESULT_HOSTS]}
						)
	unpatched_renego = main_result_list.GetAnalyze(
				filter = {Results.ResultSummaryList.QUERY_CONDITION:[Results.ResultCondition.RESULTC_NONRENEGO,Results.ResultCondition.RESULTC_PERFORM_RENEGO, Results.ResultCondition.RESULTC_EXTENDED_VALIDATION_CERT]},
				summaries = {"hosts":[Results.ResultSummaryList.RESULT_HOSTS]}
						)
	all = main_result_list.GetAnalyze(
				filter = {Results.ResultSummaryList.QUERY_CONDITION:[Results.ResultCondition.RESULTC_EXTENDED_VALIDATION_CERT]},
				summaries = {"hosts":[Results.ResultSummaryList.RESULT_HOSTS]}
						)
	
	summary = {}
	
	for (update_field, hostlist) in [("total", all),("patched",patched),("unpatched_renego", unpatched_renego)]:
		for x in hostlist["hosts"]:
			if x.servername.alexa_rating > 0:
				summary.setdefault(x.servername.alexa_rating, {"patched":0, "total":0, "unpatched_renego":0})[update_field]+=1
	
	total_patched = 0
	total = 0
	total_renego = 0
	import csv
	file = csv.writer(open("alexa_ev_renego_rating.csv","wb"))
	
	file.writerow(["ranking","site patched", "site total","total patched","total", "patched percent", "unpatched renego", "total unpatched renego", "unpatched renego percent"])
	for x,y in sorted(summary.iteritems()):
		total += y["total"]
		total_patched += y["patched"]
		total_renego += y["unpatched_renego"]
		file.writerow([x, y["patched"],  y["total"], 
					total_patched, total, ("%.2f%%" % ((float(total_patched)/float(total))*100.0 if total else 0,)),
					y["unpatched_renego"], total_renego,("%.2f%%" % ((float(total_renego)/float(total-total_patched))*100.0  if total-total_patched else 0,)),
					])
