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


import sys, os.path

sys.path.insert(1, os.path.join(".."))

import libinit
import probedb.standalone
import probedb.cluster.models as Cluster
import probedb.scanner.models as Scanner
import os,time,subprocess,datetime
from optparse import OptionParser
from django.db import transaction,connection

"""Main handler on each cluster, checks every 10 minutes for new tasks"""

def getPerformance(run, configuration): 

	Q = Scanner.ScannerAction.objects.filter(scanner_run=run)
	current_time = datetime.datetime.now()
	
	delta = datetime.timedelta(hours=1)
	Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
	all_count_24hour = Q1.count() 
	node_count_24hour = Q1.filter(scanner_node = configuration).count() 

	delta = datetime.timedelta(hours=1)
	Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
	all_count_hour = Q1.count() 
	node_count_hour = Q1.filter(scanner_node = configuration).count() 

	delta = datetime.timedelta(minutes=10)
	Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
	all_count_10min = Q1.count()*6 #recalc to per hour 
	node_count_10min = Q1.filter(scanner_node = configuration).count()*6  #recalc to per hour

	delta = datetime.timedelta(minutes=1)
	Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
	all_count_1min = Q1.count()*60 #recalc to per hour 
	node_count_1min = Q1.filter(scanner_node = configuration).count()*60  #recalc to per hour
	
	print "Node: ", node_count_1min, " ",  node_count_10min, " ", node_count_hour," ", node_count_24hour  
	print "All: ", all_count_1min, " ",  all_count_10min, " ", all_count_hour, " ", all_count_24hour, " (", Scanner.ScannerQueue.objects.filter(part_of_run=run,state=Scanner.ScannerQueue.SCANQ_IDLE).count(), " left)"


@transaction.commit_manually
def main():

	computername =  os.environ.get('COMPUTERNAME',"any").lower()
	if computername == "any":
		computername =  os.environ.get('HOSTNAME',"any").lower()
	if computername == "any":
		raise Exception("Computername was empty")
	
	computername = computername.partition('.')[0]
	
	options_config = OptionParser()
	
	options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
	options_config.add_option("--verbose", action="store_true", dest="verbose")
	options_config.add_option("--managed", action="store_true", dest="managed")
	options_config.add_option("--performance", action="store_true", dest="register_performance")
	
	(options, args) = options_config.parse_args()
	
	
	master_configuration,created = Scanner.ScannerNode.objects.get_or_create(hostname = "tlsprober-cluster", defaults={
																				"scanner_parameters":"not used",
																				"active_node":True,
																				})
	configuration,created = Scanner.ScannerNode.objects.get_or_create(hostname = computername, defaults={
																				"scanner_parameters":"--processes 4 --iterations 10",
																				"active_node":True,
																				})
	configuration.save()
	transaction.commit()
	
	for run in Scanner.ScannerRun.objects.filter(enabled=True).order_by("-priority", "entered_date").iterator():
		if not run.enabled or run.scannerqueue_set.filter(state=Scanner.ScannerQueue.SCANQ_IDLE).count() == 0:
			run.enabled = False
			run.save()
			continue
		
		if run.branch:
			terminate = True
		
		processes = []
		process_index = 0
		
		check_queue_frequency = 1
		checked_count = 0
		checked_count_git = 0
		last_count =Scanner.ScannerQueue.objects.filter(part_of_run=run,state=Scanner.ScannerQueue.SCANQ_IDLE).count()
	
		while (Scanner.ScannerRun.objects.filter(enabled=True, priority__gt=run.priority).count() == 0 and
			Scanner.ScannerRun.objects.get(id = run.id).enabled):
			cluster_master_configuration,created = Cluster.ClusterNode.objects.get_or_create(hostname = "tlsprober-cluster", defaults={
																						"probe_parameters":"not used",
																						#"result_parameters":"not used",
																						"active_node":True,
																						})
			cluster_configuration,created = Cluster.ClusterNode.objects.get_or_create(hostname = computername, defaults={
																						"probe_parameters":"--processes 40 --iterations 40",
																						#"result_parameters":"--processes 10 --iterations 100",
																						"active_node":True,
																						})
			cluster_configuration.save()
			if (cluster_master_configuration.active_node and cluster_configuration.active_node and 
				Cluster.ClusterRun.objects.filter(enabled=True).count()>0):
				break
	
			master_configuration = Scanner.ScannerNode.objects.all().get(hostname = "tlsprober-cluster")
			configuration= Scanner.ScannerNode.objects.all().get(hostname = computername)
			if not configuration.active_node or not master_configuration.active_node:
				break;
			configuration.save()
			transaction.commit()
	
			if not processes:
				subprocess.call(["git", "pull",])
				subprocess.call(["git", "submodule", "update", "--recursive"], cwd = "..")
	
			checked_count += 1
			if checked_count >= check_queue_frequency:
				qlen =Scanner.ScannerQueue.objects.filter(part_of_run=run.id, state=Scanner.ScannerQueue.SCANQ_IDLE).count()
				if qlen <= 0 :
					break;
				if qlen < 50000:
					check_queue_frequency = 0
				checked_count =0
	
			checked_count_git += 1;
			if checked_count_git>= 10:
				subprocess.call(["git", "pull",])
				subprocess.call(["git", "submodule", "update", "--recursive"], cwd = "..")
				checked_count_git = 0;
			
			run_config = OptionParser()
			
			run_config.add_option("--processes", action="store", type="int", dest="process_count", default=1)
			run_config.add_option("--iterations", action="store", type="int", dest="iteration_count", default=40)
	
			(run_options, args) = run_config.parse_args(configuration.scan_parameters.split())
			if int(run_options.process_count) == 0:
				break
	
			started_proc = 0;
			
			proc_limit = int(run_options.process_count)
	
			while len(processes) < proc_limit and started_proc<max(10,min(30, proc_limit/10)):
				process_index += 1
				new_process = subprocess.Popen(
											(["nice"] if os.name == "posix" else []) +
											["python", "-O", 
												"scan_hostnames.py",
												"-n",  str(process_index),
												"--run-id", str(run.id),
												"--source", '"'+run.source_name+'"',
												"--description", '"'+run.description+'"',
												"--max", str(run_options.iteration_count),
												]+
												(["--performance"] if options.verbose  or options.register_performance else [])+
												(["--verbose"] if options.verbose else [])+
												(["--testbase2"] if options.use_testbase2 else []),
												shell=False)
				
				started_proc += 1
				if new_process:
					processes.append(new_process)
					if options.verbose:
						print "started ", process_index, " count ", len(processes), "/", proc_limit
				time.sleep(0.5)
		
			if len(processes) >400 and len(processes) < proc_limit*0.95:
				time.sleep(120)
			else:
				time.sleep(30 if len(processes) > proc_limit*0.95 else 15)
			
			if options.verbose:
				getPerformance(run, configuration)
			
			next_process_list = []
			
			for proc in processes:
				if proc.poll() == None:
					next_process_list.append(proc)
			
			processes = next_process_list
				
			# Loop back and try the next one
		
		while processes:
			time.sleep(30)
			if options.verbose:
				getPerformance(run, configuration)
	
			next_process_list = []
			
			for proc in processes:
				if proc.poll() == None:
					next_process_list.append(proc)
			
			processes = next_process_list
			
			if options.verbose:
				print "closing down: count ", len(processes), "/",  run_options.process_count
				
			# Loop back and see if all has ended now
		
		
		if options.verbose:
			print "closed down:"
			
		break; 
	transaction.commit()
	
main()
