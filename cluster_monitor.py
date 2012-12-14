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


import libinit
import probedb.standalone
import probedb.cluster.models as Cluster
import probedb.probedata2.models as Probe
import probedb.resultdb2.models as Results
import os,time,subprocess,datetime
from optparse import OptionParser
from django.db import connection,transaction 

"""
Prints information about how many servers per hour the prober have checked
in the past minute, 10 minutes and one hour, as well as the total for the 
last 24 hours, per active node and in total.
"""

computername =  os.environ.get('COMPUTERNAME',"any").lower()
if computername == "any":
	computername =  os.environ.get('HOSTNAME',"any").lower()
if computername == "any":
	raise Exception("Computername was empty")

computername = computername.partition('.')[0]

options_config = OptionParser()

options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--verbose", action="store_true", dest="verbose")

(options, args) = options_config.parse_args()

start = time.clock() 
while True:
	try:
		@transaction.commit_on_success
		def check_performance():
			run = Cluster.ClusterRun.objects.filter(enabled=True).order_by("-priority", "entered_date")[0]
	
			print "=======Probe=============", run.perform_run_id
			Q = Cluster.ClusterAction.objects.filter(cluster_run=run)
			current_time = datetime.datetime.now()
		
			for node in Cluster.ClusterNode.objects.filter(active_node = True).iterator():
				delta = datetime.timedelta(hours=24)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				node_count_24hour = Q1.filter(cluster_node = node).count() 
			
				delta = datetime.timedelta(hours=1)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				node_count_hour = Q1.filter(cluster_node = node).count() 
			
				delta = datetime.timedelta(minutes=10)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				node_count_10min = Q1.filter(cluster_node = node).count()*6  #recalc to per hour
			
				delta = datetime.timedelta(minutes=1)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				node_count_1min = Q1.filter(cluster_node = node).count()*60  #recalc to per hour
				print "Node  %20s: %7d %7d %7d %7d" %(node.hostname, node_count_1min, node_count_10min, node_count_hour, node_count_24hour)
		
			delta = datetime.timedelta(hours=24)
			Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
			all_count_24hour = Q1.count() 
		
			delta = datetime.timedelta(hours=1)
			Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
			all_count_hour = Q1.count() 
		
			delta = datetime.timedelta(minutes=10)
			Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
			all_count_10min = Q1.count()*6 #recalc to per hour 
		
			delta = datetime.timedelta(minutes=1)
			Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
			all_count_1min = Q1.count()*60 #recalc to per hour 
			
			print "All:  %20s: %7d %7d %7d %7d" %(" ",all_count_1min, all_count_10min, all_count_hour, all_count_24hour), " (", Probe.ProbeQueue.objects.filter(part_of_run=run.perform_run_id, state=Probe.ProbeQueue.PROBEQ_IDLE).count(), " left/", Probe.ProbeResult.objects.filter(part_of_run=run.perform_run_id).count() ," Found)"
			print "==========================="
		check_performance()
	except:
		pass

	connection.close()
	time.sleep(30)
