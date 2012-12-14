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
import probedb.batch.models as Batch
import datetime


if not Batch.UpdateBatchStatus.IsActive():
	sys.exit()

__threads_active = False

def __ProgressCounter(queue, text):
	"""Report progress about the ongoing task"""
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
		if i%100 == 0:
			if text:
				print text, i
			else:
				print i

def checkactive():
	"""Are we still active?"""
	return Batch.UpdateBatchStatus.IsActive()

def __do_action(self, action_func, n, queue, report_queue, lock):
	"""
	Get an item from the queue, have action_func process it,
	then report the action to the report_queue
	"""

	import Queue
	global __threads_active
	
	if not isinstance(action_func, list):
		action_func = [action_func]
	
	while __threads_active:
		try:
			item = queue.get(timeout=1)
		except Queue.Empty:
			continue
		
		for f in  action_func:
			try:
				f(self, item, lock)
			except:
				pass
			
		report_queue.put(True)
		queue.task_done()					

def update_action(self, queue_query, action_func, options, text=None):
	"""
	Perform an action by queuing the items from queue_query, then 
	performing action_func as a number of threads, which will perform
	actions on the queued items
	""" 

	import threading
	import Queue
	global __threads_active
	
	if not checkactive():
		sys.exit()
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

	new_thread = threading.Thread(target=__ProgressCounter, args=(result_tick,text))
	new_thread.daemon = True
	new_thread.start()
	threads.append(new_thread)
	
	print "Items (%d) %s"% (options.run_id, (text if text else "")),  queue_query.count()
	last_check = datetime.datetime.now()
	for result in queue_query.iterator():
		if (datetime.datetime.now() - last_check).seconds >= 10.0:
			last_check = datetime.datetime.now()
			if not checkactive():
				sys.exit()
		probe_results.put(result)
	
	while not probe_results.empty():
		if not checkactive():
			sys.exit()
		time.sleep(10)
		
	probe_results.join() # wait for the last items to be completed
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

(options, args) = options_config.parse_args()

if options.run_id:
	run = ProbeData.ProbeRun.objects.get(id = options.run_id)

	summary = Results.ResultSummaryList.objects.get(part_of_run=run)
	
######################################
# Add code and functions  below
#
#	@transaction.commit_on_success
# 	def user_foo(master, item, lock):
#   	bar()
#
#	update_action(summary, summary.query(), user_foo, options)
#####################################

class update_master:
	"""Put common data needed here"""
	def __init__(self):
		pass

common_update_master = update_master()



###### ALL CODE ABOVE THIS LINE. DO NOT REMOVE CODE BELOW ######

summary.updatebatchitem.enabled = False
summary.updatebatchitem.save()