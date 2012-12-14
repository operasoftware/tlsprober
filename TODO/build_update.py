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

"""
This script is used to run updates of the database that can be performed
in parallel, by updating individual run results, on the nodes

The script perform updates using the script build_update_part.py on a specified 
proberun, selected by the node based on the ID of the run being even or odd,
depending on whether the --even or --odd flag was set.

The selection of run IDs can be limited by the --before parameter, for example
if the run performed with that ID or higher already perform the changes that the 
build_update_part script is implementing.

Multiple build_update_part instances can be run in parallel, based on the 
--threads parameter
"""

import sys,os,subprocess,time,os.path

sys.path.insert(1, os.path.join(".."))

import libinit

from optparse import OptionParser
import probedb.standalone
import probedb.probedata2.models as ProbeData
import probedb.resultdb2.models as Results
import probedb.batch.models as Batch

options_config = OptionParser()

options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--threads", action="store", type="int", dest="threads", default=1)
options_config.add_option("--odd", action="store_true", dest="summary_id_odd")
options_config.add_option("--even", action="store_true", dest="summary_id_even")
options_config.add_option("--verbose", action="store_true", dest="verbose")
options_config.add_option("--before", action="store", type="int", dest="before_id", default=0)


(options, args) = options_config.parse_args()

if not Batch.UpdateBatchStatus.IsActive():
	sys.exit()

if options.summary_id_even or options.summary_id_odd:
	
	if options.summary_id_even:
		f = lambda x: (x%2 == 0)
	else:
		f = lambda x: (x%2 != 0)
		
	q = Results.ResultSummaryList.objects.exclude(updatebatchitem = None)
	if options.before_id:
		q = q.filter(part_of_run__id__lt = options.before_id)

	main_result_list = [x for x in q.order_by("-part_of_run__id") if f(x.part_of_run_id)]
	
	processes = []
	
	print len(main_result_list)
	for summary in main_result_list:
		if not Batch.UpdateBatchStatus.IsActive():
			break
		if not summary.updatebatchitem.enabled:
			continue

		print "starting to process summary for run ", summary.part_of_run_id
		new_process = subprocess.Popen(
									(["nice"] if os.name == "posix" else []) +
									["python", "-O", 
										"build_update_part.py",
										"--id",  str(summary.part_of_run_id),
										"--threads", "10"
										]
										+ (["--testbase2"] if options.use_testbase2 else [])
										+ (["--verbose"] if options.verbose else [])
										, shell=False)
		
		if new_process:
			processes.append(new_process)
		time.sleep(0.5)

		while True:
			next_process_list = []
			
			for proc in processes:
				if proc.poll() == None:
					next_process_list.append(proc)
			
			processes = next_process_list
			if len(processes) >= options.threads:
				time.sleep(10)
				if not Batch.UpdateBatchStatus.IsActive():
					break
				continue;

			break
	
	print "wrapping up"
	
	while processes:
		time.sleep(10)
		next_process_list = []
		
		for proc in processes:
			if proc.poll() == None:
				next_process_list.append(proc)
		
		processes = next_process_list

	print "completed"
