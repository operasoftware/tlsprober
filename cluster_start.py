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
import os,os.path,time,subprocess,datetime
from optparse import OptionParser
from probedb.cluster.models import ClusterAction
from django.db import connection

"""Main handler on each cluster, checks every 10 minutes for new tasks"""

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


while True:
	terminate = False
	master_configuration,created = Cluster.ClusterNode.objects.get_or_create(hostname = "tlsprober-cluster", defaults={
																				"probe_parameters":"not used",
																				#"result_parameters":"not used",
																				"active_node":True,
																				})
	configuration,created = Cluster.ClusterNode.objects.get_or_create(hostname = computername, defaults={
																				"probe_parameters":"--processes 40 --iterations 40",
																				#"result_parameters":"--processes 10 --iterations 100",
																				"active_node":True,
																				})
	configuration.save()

	for run in Cluster.ClusterRun.objects.filter(enabled=True).order_by("-priority", "entered_date").iterator():
		"""Find the active job with the highest priority in the queue"""  
		if run.perform_run.probequeue_set.filter(state=Probe.ProbeQueue.PROBEQ_IDLE).count() == 0:
			run.enabled = False
			run.save()
			continue
		
		if run.perform_run.branch:
			terminate = True
		
		processes = []
		process_index = 0
		topped_out = False
		
		check_queue_frequency = 1
		checked_count = 0
		checked_count_git = 0
		last_count =Probe.ProbeQueue.objects.filter(part_of_run=run.perform_run_id,state=Probe.ProbeQueue.PROBEQ_IDLE).count()
		if last_count > 1000000:
			check_queue_frequency = 30			
		elif last_count > 50000:
			check_queue_frequency = 10			
		
		while (Cluster.ClusterRun.objects.filter(enabled=True, priority__gt=run.priority).count() == 0 and 
			Cluster.ClusterRun.objects.get(id = run.id).enabled):
			master_configuration = Cluster.ClusterNode.objects.get(hostname = "tlsprober-cluster")
			configuration= Cluster.ClusterNode.objects.get(hostname = computername)
			if not configuration.active_node or not master_configuration.active_node:
				break;
			configuration.save()

			if not processes:
				subprocess.call(["git", "pull",])
				subprocess.call(["git", "submodule", "update", "--recursive"])
				subprocess.call(["python", "build_certhandler.py", "build","--build-lib","."], cwd=os.path.join("probedb","certs"))

			checked_count += 1
			if checked_count >= check_queue_frequency:
				qlen =Probe.ProbeQueue.objects.filter(part_of_run=run.perform_run_id, state=Probe.ProbeQueue.PROBEQ_IDLE).count()
				if qlen <= 0 :
					break;
				if qlen < 50000:
					check_queue_frequency = 0
				elif qlen < 1000000:
					check_queue_frequency = 10
					
				last_count = qlen			

				checked_count = 0
				
			checked_count_git += 1;
			if checked_count_git>= 10:
				subprocess.call(["git", "pull",])
				subprocess.call(["git", "submodule", "update", "--recursive"])
				subprocess.call(["python", "build_certhandler.py", "build","--build-lib","."], cwd=os.path.join("probedb","certs"))
				checked_count_git = 0;

			
			run_config = OptionParser()
			
			run_config.add_option("--processes", action="store", type="int", dest="process_count", default=1)
			run_config.add_option("--iterations", action="store", type="int", dest="iteration_count", default=40)

			(run_options, args) = run_config.parse_args(configuration.probe_parameters.split())
			if int(run_options.process_count) == 0:
				break

			started_proc = 0;
			
			Q = Cluster.ClusterAction.objects.filter(cluster_run=run)
			current_time = datetime.datetime.now()
			delta = datetime.timedelta(minutes=10)

			# Calculate process and iteration limits based on the actual 
			# number of items left for the job
			# Early in the process the cluster will work slowly up to full 
			# number of processes, to avoid overloading the database
			# towards the end, the number of processes will be reduced,
			# in parallel to reducing the number of iterations per process
			# to reduce the risk that one process will continue for a long 
			# time while others have finished  
			Q3 = Q.filter(completed_time__range=(current_time-delta,current_time-datetime.timedelta(minutes=5)))
			all_count_5min = Q3.count()
			if all_count_5min > 4:
			
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				node_count_10min = Q1.filter(cluster_node = configuration).count()
				all_count_10min = Q1.count()
				
				if node_count_10min > 4:
					factor = all_count_10min/node_count_10min
					iterations = int((last_count * factor)/ int(run_options.process_count))

					if run_options.iteration_count > iterations:
						run_options.iteration_count = max(15, iterations)
						
			proc_limit = int(run_options.process_count)
			if last_count < 10000 and proc_limit > 20 and run_options.iteration_count >50 :
				run_options.iteration_count = 15
				
			if last_count < 100000 and proc_limit > 50:
				proc_limit /= 3
				proc_limit = max(40,proc_limit)
				if last_count < run_options.iteration_count * proc_limit:
					proc_limit = max(min(40,proc_limit), min(40,last_count/ run_options.iteration_count, proc_limit))

			if last_count < proc_limit*run_options.iteration_count:
				proc_limit = max(10, last_count/run_options.iteration_count)

			if proc_limit > 80 and len(processes) >0 and  len(processes)<80 and all_count_5min < 50:
				time.sleep(120);
				continue;

			start_proc = max(10,min(
								30 if proc_limit *0.75 > len(processes) or (proc_limit > 200 and len(processes) < 100)  else 50 , 
								proc_limit/10))
			if proc_limit >80 and len(processes)<30:
				start_proc = 5
			while len(processes) < proc_limit and started_proc<start_proc:
				process_index += 1
				new_process = subprocess.Popen(
											(["nice"] if os.name == "posix" else []) +
											["python", "-O", 
												"probe_lists.py",
												"-n",  str(process_index),
												"--run-id", str(run.perform_run.id),
												"--source", '"'+run.perform_run.source_name+'"',
												"--description", '"'+run.perform_run.description+'"',
												"--max", str(run_options.iteration_count),
												]+
												(["--performance"] if options.verbose  or options.register_performance else [])+
												(["--testbase2"] if options.use_testbase2 else [])+
												(["--large_run"] if last_count > 400000 else [])+
												(["--small_run"] if last_count < 50000 else [])
												, shell=False)
				
				started_proc += 1
				if new_process:
					processes.append(new_process)
					if options.verbose:
						print "started ", process_index, " count ", len(processes), "/", proc_limit
				time.sleep(0.5)
		
			try:
				connection.close()
			except:
				pass
			
			if not topped_out and len(processes) >= int(run_options.process_count):
				topped_out = True
			
			# Don't start too processes to quickly
			if (start_proc < 10 and not topped_out) or (proc_limit > 200 and len(processes) < proc_limit*0.90):
				time.sleep(300)
			elif last_count < 100000 and proc_limit > 20 and not topped_out:
				time.sleep(240)
			elif len(processes) >300 and len(processes) < proc_limit*0.95:
				time.sleep(300)
			elif len(processes) >200 and len(processes) < proc_limit*0.95:
				time.sleep(60)
			else:
				time.sleep(30 if len(processes) > proc_limit*0.95 else 15)
			
			if options.verbose:
				Q = ClusterAction.objects.filter(cluster_run=run)
				current_time = datetime.datetime.now()
				delta = datetime.timedelta(hours=1)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				all_count_hour = Q1.count() 
				node_count_hour = Q1.filter(cluster_node = configuration).count() 

				delta = datetime.timedelta(minutes=10)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				all_count_10min = Q1.count()*6 #recalc to per hour 
				node_count_10min = Q1.filter(cluster_node = configuration).count()*6  #recalc to per hour

				delta = datetime.timedelta(minutes=1)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				all_count_1min = Q1.count()*60 #recalc to per hour 
				node_count_1min = Q1.filter(cluster_node = configuration).count()*60  #recalc to per hour
				
				#clean up queue
				#Probe.ProbeQueue.objects.filter(part_of_run=run.perform_run_id, state=Probe.ProbeQueue.PROBEQ_FINISHED).delete()

				print "Node: ", node_count_1min, " ",  node_count_10min, " ", node_count_hour
				print "All: ", all_count_1min, " ",  all_count_10min, " ", all_count_hour, " (", Probe.ProbeQueue.objects.filter(part_of_run=run.perform_run_id,state=Probe.ProbeQueue.PROBEQ_IDLE).count(), " left)"
			
			next_process_list = []
			
			for proc in processes:
				if proc.poll() == None:
					next_process_list.append(proc)
			
			processes = next_process_list
				
			# Loop back and try the next one
		
		while processes:
			try:
				connection.close()
			except:
				pass
			time.sleep(30)
			if options.verbose:
				Q = ClusterAction.objects.filter(cluster_run=run)
				current_time = datetime.datetime.now()
				delta = datetime.timedelta(hours=1)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				all_count_hour = Q1.count() 
				node_count_hour = Q1.filter(cluster_node = configuration).count() 

				delta = datetime.timedelta(minutes=10)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				all_count_10min = Q1.count()*6 #recalc to per hour 
				node_count_10min = Q1.filter(cluster_node = configuration).count()*6  #recalc to per hour

				delta = datetime.timedelta(minutes=1)
				Q1 = Q.filter(completed_time__range=(current_time-delta,current_time))
				all_count_1min = Q1.count()*60 #recalc to per hour 
				node_count_1min = Q1.filter(cluster_node = configuration).count()*60  #recalc to per hour
				
				#clean up queue
				#Probe.ProbeQueue.objects.filter(part_of_run=run.perform_run_id, state=Probe.ProbeQueue.PROBEQ_FINISHED).delete()

				print "Node: ", node_count_1min, " ",  node_count_10min, " ", node_count_hour
				print "All: ", all_count_1min, " ",  all_count_10min, " ", all_count_hour, " (", Probe.ProbeQueue.objects.filter(part_of_run=run.perform_run_id, state=Probe.ProbeQueue.PROBEQ_IDLE).count(), " left)"

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
			
		break; # need to trigger a new database retrieval
	
	if terminate:
		break;
	
	master_configuration = Cluster.ClusterNode.objects.get(hostname = "tlsprober-cluster")
	configuration= Cluster.ClusterNode.objects.get(hostname = computername)
	configuration.save()
	run_config = OptionParser()
	
	run_config.add_option("--processes", action="store", dest="process_count", default=1)
	run_config.add_option("--iterations", action="store", dest="iteration_count", default=40)

	(run_options, args) = run_config.parse_args(configuration.probe_parameters.split())
	if (not master_configuration.active_node or not configuration.active_node or 
		int(run_options.process_count) == 0 or Cluster.ClusterRun.objects.filter(enabled=True).count() == 0):
		if options.managed and Cluster.ClusterRun.objects.filter(enabled=True).count() == 0:
			break;
		connection.close()
		time.sleep(60) # if there are no runs, sleep for 10 minutes
