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

import smtplib

"""
Setup a cluster job

Default is to copy all enabled hostnames from the server list in 
the database.

CSV formats

   index, hostname, port, protocol
   index, hostname, port			# HTTPS assumed
   index, hostname  				# Port 443, HTTPS assumed; line starts with number
   hostname, port					# HTTPS assumed; line starts with letter; port may be empty

Options:

--input	<name>	: CSV File containing a list of hosts
--queue	<name>	: name of pre-configured list of hostnames
--queue-id <num>	: Database record ID for pre-configured list of hostnames
--file			: Do not use the server name list, only the provided
--count <num>	: Only configure max <num> servers from the source   

--branch <name>	: Name of git branch to check out when running the job

--source <name>	: Name of source for job
--description <text>	: Description of the job

--priority	<num>	: Higher number means being ahead in the queue, other jobs will be parked
--noreport		: Don't generate a report

--restart 		: restart the specied job in --run-id
--run-id <num>	: Perform restart actions for this existing job  
--tar			: Just tar.gz the result files

--verbose		: Print more information

--testbase2		: use the debug test database for this job

--threads <num>	: Use the specified number of threads when inserting the entries for the job
"""


import libinit

import sys,os,subprocess,time,os.path
import datetime
from optparse import OptionParser

import probedb.standalone
import probedb.cluster.models as Cluster
import probedb.probedata2.models as Probe
from django.db import connection

import config

options_config = OptionParser()

options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--verbose", action="store_true", dest="verbose")
options_config.add_option("--restart", action="store_true", dest="restart_last")
options_config.add_option("--tar", action="store_true", dest="tar_only")
options_config.add_option("--run-id", action="store", type="int", dest="run_id", default=0)
options_config.add_option("--input", action="store", type="string", dest="input_filename")
options_config.add_option("--description", action="store", type="string", dest="description",default="Special run")
options_config.add_option("--priority", action="store", dest="priority", default="5")
options_config.add_option("--branch", action="store", type="string", dest="branch")
options_config.add_option("--tag", action="store", type="string", dest="tag")
options_config.add_option("--noreport", action="store_true", dest="noreport")
options_config.add_option("--count", action="store", type="string", dest="count")
options_config.add_option("--queue-id", action="store", type="int", dest="input_queue_id")
options_config.add_option("--queue", action="store", type="string", dest="input_queue")


(options, args) = options_config.parse_args()

source_file = options.input_filename
job_source = "Special_probe"
job_description_prefix =options.description
job_priority = options.priority
thread_count = 300 if not options.use_testbase2 else 50
wait_period = 5*60
wait_cluster = 15

if options.branch and options.tag:
	options.tag = None

if options.tar_only:
	options.restart_last = True

job_item_id = None
if options.restart_last:
	if options.verbose:
		print "restarting"
	try:
		job_item_id = options.run_id
		if job_item_id:
			cluster_item = Cluster.ClusterRun.objects.get(perform_run = job_item_id)
			cluster_item_id = cluster_item.id
			job_description =cluster_item.perform_run.description
			if options.verbose:
				print "restarting job ", job_item_id, ": ", job_description
			
	except:
		pass

today_date = datetime.date.today()
job_duplicate = 0
	
if not job_item_id:
	
	job_description_base = job_description_prefix + " " +today_date.isoformat()
	job_description = job_description_base;
	
	while Probe.ProbeRun.objects.filter(source_name = job_source, description = job_description).count() > 0:
		job_duplicate += 1
		job_description = job_description_base + " #" + str(job_duplicate)

	#update from CVS
	subprocess.call(["git", "pull",])
	subprocess.call(["git", "submodule", "update", "--recursive"])
	
	
	if options.verbose:
		print "initializing job: ", job_description

	#initialize job
	subprocess.call(["python",
						"cluster_setup.py",
						"--source", job_source,
						"--description", '"'+job_description+'"',
						"--priority", str(job_priority),
						"--file",
						"--threads", str(thread_count),
						] +
						(["--input", source_file] if source_file else [])+ 
						(["--queue-id", str(options.input_queue_id)] if options.input_queue_id else [])+
						(["--queue", str(options.input_queue)] if options.input_queue else [])+
						(["--count", options.count] if options.count else [])+
						(["--testbase2", ] if options.use_testbase2 else []) +
						(["--branch", options.branch] if options.branch else []) +
						(["--branch", options.tag] if options.tag else []) +
						(["--verbose"] if options.verbose else [])
						)

	job = Probe.ProbeRun.objects.get(source_name = job_source, description = job_description)
	job_item_id = job.id
	cluster_item_id = Cluster.ClusterRun.objects.get(perform_run = job_item_id).id
	
	if options.verbose:
		print "initialized job ", job_item_id, ": ", job_description

if not options.tar_only:
	try:
		connection.close()
	except:
		pass
	time.sleep(30)
	
	delta = datetime.timedelta(minutes=wait_cluster)
	while True:
		try:
			while (
					Cluster.ClusterRun.objects.get(id = cluster_item_id).enabled or 
					Cluster.ClusterAction.objects.filter(cluster_run=job_item_id).filter(
												completed_time__range=(datetime.datetime.now()-delta,datetime.datetime.now())).count()
									):
				if Probe.ProbeQueue.objects.filter(part_of_run = job_item_id, state__in =[Probe.ProbeQueue.PROBEQ_STARTED, Probe.ProbeQueue.PROBEQ_IDLE]).count() == 0:
					break;
				try:
					connection.close()
				except:
					pass
				time.sleep(wait_period) # Sleep for 15 minutes while waiting for the cluster to complete the job, then recheck activity
		except:
			try:
				connection.close()
			except:
				pass
			time.sleep(wait_period) # Sleep for 15 minutes while waiting for the cluster to complete the job, then recheck activity
			
		break;
	
	try:
		connection.close()
	except:
		pass
	time.sleep(wait_period) # Sleep another 15 minutes while waiting for pending cluster processes.
	
	#restart queue items that somehow got lost 
	if Probe.ProbeQueue.objects.filter(part_of_run = job_item_id, state = Probe.ProbeQueue.PROBEQ_STARTED).update(state = Probe.ProbeQueue.PROBEQ_IDLE) > 0:
	
		if options.verbose:
			print "completed most of job ", job_item_id, ": ", job_description, " restarting"
	
		#re-enable job
		item = Cluster.ClusterRun.objects.get(perform_run = job_item_id)
		item.enabled = True
		item.save()
	
		try:
			connection.close()
		except:
			pass
		time.sleep(15*60) # Sleep 15 minutes while waiting for cluster processes to start.
		
		while (
				Cluster.ClusterRun.objects.get(id = cluster_item_id).enabled or 
				Cluster.ClusterAction.objects.filter(cluster_run=job_item_id).filter(
										completed_time__range=(datetime.datetime.now()-delta,datetime.datetime.now())).count()):
			if Probe.ProbeQueue.objects.filter(part_of_run = job_item_id, state__in =[Probe.ProbeQueue.PROBEQ_STARTED, Probe.ProbeQueue.PROBEQ_IDLE]).count() == 0:
				break;
			try:
				connection.close()
			except:
				pass
			time.sleep(wait_period) # Sleep for 15 minutes while waiting for the cluster to complete the job, then recheck activity
	
		try:
			connection.close()
		except:
			pass
		time.sleep(wait_period) # Sleep another 15 minutes while waiting for pending cluster processes.

	job.resultsummarylist_set.all()[0].migrate_server_aliases(report=options.verbose)
	
	if options.verbose:
		print "completed job ", job_item_id, ": ", job_description, ". Starting to generate summaries"

tag_name = ("testbase_"+today_date.isoformat()+"_" if options.use_testbase2 else "")+"special_run_%d"%(job_item_id,)

if not options.noreport:
	
	if not options.tar_only:
		subprocess.call("rm -r results/*", shell=True)
		subprocess.call(["python", "-O", 	
						"generate_security_view.py",
						"--id", str(job_item_id),
						"--threads", "4"
						]+
							(["--testbase2", ] if options.use_testbase2 else [])
						)
	
	filename_base = "tlsprober-"+today_date.isoformat() + ("-%d"%(job_duplicate,) if job_duplicate else "") + ".tar.gz"
	
	filename = "public_html/"+filename_base
	
	if options.verbose:
		print "completed job ", job_item_id, ": ", job_description, ". Compressing summaries"
		
	tar_job = " ".join(["tar", 
					"cvzf", filename,
					"results/*",
					])
		
	if options.verbose:
		print "performing :", tar_job 
	
	subprocess.call(tar_job, shell=True) 
	
	if not options.tar_only and not options.use_testbase2:
		server = smtplib.SMTP(config.smtpserver)
		server.sendmail(config.sender, config.receivers, 
"""From: %s
To: %s
Subject: TLSProber run %d completed

The TLS Prober run #%d, %s/%s (%s) has completed.

The results are available from %s/%s

Sincerely,
The Prober
""" % (config.sender, ", ".join(config.receivers), job_item_id, job_item_id, job_source, job_description, tag_name, config.result_home, filename_base))
	

subprocess.call(["git", "pull",])
subprocess.call(["git", "submodule", "update", "--recursive"])
subprocess.call(["git", "tag", tag_name]+ (["origin/" + options.branch] if options.branch else []) + ([options.tag] if options.tag else []))
subprocess.call(["git", "push", "origin", tag_name])

if options.verbose:
	print "Finished job ", job_item_id, ": ", job_description, ". Sent email."

