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
This script perform changes to the data in the database that affect all runs,
and which cannot easily be performed in parallel by the build_update_part script
on multiple nodes; the updates may still be performed using multi-threading.
"""

import sys,os,subprocess,time,os.path

sys.path.insert(1, os.path.join(".."))

import libinit

from optparse import OptionParser
import probedb.standalone
import probedb.probedata2.models as ProbeData
import probedb.resultdb2.models as Results
from django.db import transaction
from django.db import DatabaseError
from django.db import IntegrityError
from django.db.models import Count, F

__threads_active = False

def __ProgressCounter(queue, step):
	"""
	Indicate progress by printing an update every step number of 
	'completed' messages transmitted via the queue from the activity process
	"""
	
	import Queue
	global __threads_active
	i=0

	while __threads_active:
		try:
			result = queue.get(timeout=1)
		except Queue.Empty:
			continue
		queue.task_done()
		
		i += 1
		if i%step == 0:
			print i

def __do_action(self, action_func, n, queue, report_queue, lock):
	"""
	Get an item from the queue, have action_func process it,
	then report the action to the report_queue
	"""

	import Queue
	global __threads_active

	while __threads_active:
		try:
			item = queue.get(timeout=1)
		except Queue.Empty:
			continue
		
		try:
			action_func(self, item, lock)
		except:
			pass
			
		report_queue.put(True)
		queue.task_done()					

def update_action(self, queue_query, action_func, options):
	"""
	Perform an action by queuing the items from queue_query, then 
	performing action_func as a number of threads, which will perform
	actions on the queued items
	""" 

	import threading
	import Queue
	global __threads_active
	
	__threads_active = True
	
	probe_results = Queue.Queue(100000)
	result_tick = Queue.Queue()
	lock = threading.Lock()

	num_probers = options.threads if options else 100
	threads = []
	for i in range(num_probers):
		new_thread = threading.Thread(target=__do_action, args=(self, action_func, i,probe_results,result_tick, lock))
		new_thread.daemon = True
		new_thread.start()
		threads.append(new_thread)

	if isinstance(queue_query, (list, tuple)):
		qlen = len(queue_query)
	else:
		qlen = queue_query.count()
	print "Items", qlen
	
	step = 100
	if qlen > 250000:
		step = 1000

	new_thread = threading.Thread(target=__ProgressCounter, args=(result_tick,step))
	new_thread.daemon = True
	new_thread.start()
	threads.append(new_thread)
	
	i = 0;
	if isinstance(queue_query, (list, tuple)):
		for result in queue_query:
			probe_results.put(result)
	else:
		for result in queue_query.iterator():
			probe_results.put(result)
	
	probe_results.join()
	result_tick.join()

	__threads_active = False
	
	for t in threads:
		t.join()
	print "Completed"


options_config = OptionParser()

options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--threads", action="store", type="int", dest="threads", default=20)
options_config.add_option("--id", action="store", type="int", dest="run_id", default=0)
options_config.add_option("--verbose", action="store_true", dest="verbose")
options_config.add_option("--odd", action="store_true", dest="summary_id_odd")
options_config.add_option("--even", action="store_true", dest="summary_id_even")

(options, args) = options_config.parse_args()

run = None
main_result_list = []

if options.run_id:
	run = ProbeData.ProbeRun.objects.get(id = options.run_id)
	main_result_list = list(Results.ResultSummaryList.objects.filter(part_of_run__id=run.id))

if options.summary_id_even:
	odd_even = lambda x: (x%2 == 0)
elif options.summary_id_odd:
	odd_even = lambda x: (x%2 != 0)
else:
	odd_even = lambda x: True
	
	
######################################
# Add code and functions  below
#
# 	def user_foo(master, item, lock):
#   	bar()

#	update_action(master, query(), user_foo, options)
#####################################

class update_master:
	"""Put common data needed here"""
	def __init__(self):
		pass

