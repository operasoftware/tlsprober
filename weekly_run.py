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


import libinit

import sys,os,subprocess,time,os.path
import datetime
from optparse import OptionParser

import probedb.standalone
import probedb.cluster.models as Cluster
import probedb.probedata2.models as Probe
from django.db import connection

#import config


options_config = OptionParser()

options_config.add_option("--verbose", action="store_true", dest="verbose")
options_config.add_option("--restart", action="store_true", dest="restart_last")
options_config.add_option("--tar", action="store_true", dest="tar_only")

(options, args) = options_config.parse_args()

job_source = "Main_prober"
job_description_prefix = "Main prober run" 
job_priority = 2
thread_count = 300
wait_period = 15*60
wait_cluster = 15

if options.tar_only:
	options.restart_last = True

job_item_id = None
if options.restart_last:
	if options.verbose:
		print "restarting"
	try:
		job = Probe.ProbeRun.objects.filter(source_name = job_source).latest('date')
		if job and Cluster.ClusterRun.objects.filter(perform_run = job).count():
			job_description = job.description
			job_item_id = job.id
			cluster_item_id = Cluster.ClusterRun.objects.get(perform_run = job_item_id).id
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

	#update from git
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
						"--queue","Weekly Run"
						] +
						(["--verbose"] if options.verbose else [])
						)
	
	job = Probe.ProbeRun.objects.get(source_name = job_source, description = job_description)
	job_item_id = job.id
	cluster_item_id = Cluster.ClusterRun.objects.get(perform_run = job_item_id).id
	
	if options.verbose:
		print "initialized job ", job_item_id, ": ", job_description

if not options.tar_only:
	if (Probe.ProbeQueue.objects.filter(part_of_run = job_item_id, state__in = [Probe.ProbeQueue.PROBEQ_STARTED, Probe.ProbeQueue.PROBEQ_IDLE])>0 or
			Cluster.ClusterRun.objects.get(id = cluster_item_id).enabled
			):
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
				try:
					connection.close()
				except:
					pass
				time.sleep(wait_period) # Sleep for 15 minutes while waiting for the cluster to complete the job, then recheck activity
		
			time.sleep(wait_period) # Sleep another 15 minutes while waiting for pending cluster processes.
	
	job.resultsummarylist_set.all()[0].migrate_server_aliases(report=options.verbose)
	
	if options.verbose:
		print "completed job ", job_item_id, ": ", job_description, ". Starting to generate summaries"
	
if not options.tar_only:
	subprocess.call("rm -r results/*", shell=True)
	subprocess.call(["python", "-O", 	
					"generate_security_view.py",
					"--id", str(job_item_id),
					"--threads", "4"
					])

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

tag_name = "main_prober_%d"%(job_item_id,)

if not options.tar_only:
	server = smtplib.SMTP(config.smtpserver)
	server.sendmail(config.sender, config.receivers, 
"""From: %s
To: %s
Subject: TLSProber run %d completed

The TLS Prober run #%d, %s/%s (%s) has completed.

The results are available from %s/results/%s

Sincerely,
The Prober
""" % (config.sender, ", ".join(config.receivers), job_item_id, job_item_id, job_source, job_description, tag_name, config.result_home, filename_base))


subprocess.call(["git", "pull",])
subprocess.call(["git", "submodule", "update", "--recursive"])
subprocess.call(["git", "tag", "-f", tag_name])
subprocess.call(["git", "push","origin", tag_name])

if options.verbose:
	print "Finished job ", job_item_id, ": ", job_description, ". Sent email."

