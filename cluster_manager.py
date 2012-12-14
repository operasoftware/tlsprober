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
import probedb.scanner.models as Scanner
import os,time,subprocess,datetime
from optparse import OptionParser
from django.db import connection,transaction

@transaction.commit_manually
def main():
	"""Main management handler on each cluster, checks every 10 minutes for new tasks"""


	computername =  os.environ.get('COMPUTERNAME',"any").lower()
	if computername == "any":
		computername =  os.environ.get('HOSTNAME',"any").lower()
	if computername == "any":
		raise Exception("Computername was empty")
	
	computername = computername.partition('.')[0]
	
	options_config = OptionParser()
	
	options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
	options_config.add_option("--verbose", action="store_true", dest="verbose")
	options_config.add_option("--persistent", action="store_true", dest="persistent")
	options_config.add_option("--nogit", action="store_true", dest="nogit")
	
	
	(options, args) = options_config.parse_args()
	
	while True:
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
		transaction.commit()
		done_something = False
		if Cluster.ClusterRun.objects.filter(enabled=True).count() >0:
			"""Any enabled TLS Prober jobs?"""
			done_something = True
			if master_configuration.active_node and configuration.active_node:
				if not options.nogit:
					"""Check out the code to be used"""
					subprocess.call(["git", "pull",])
					subprocess.call(["git", "submodule", "update", "--recursive"])
					
					master_branch = "pincushion" if options.use_testbase2 else "master"
						
					run = Cluster.ClusterRun.objects.filter(enabled=True).order_by("-priority", "entered_date")[0]
					branch = run.perform_run.branch
					subprocess.call(["git", "checkout", branch if branch else master_branch])
					subprocess.call(["git", "submodule", "update", "--recursive"])
		
				try:
					connection.close()
				except:
					pass
				"""Start the prober on this cluster node for the job"""
				subprocess.call(["python", "-O", 
									"cluster_start.py",
										"--performance",
										"--managed"]
									+ (["--testbase2"] if options.use_testbase2 else [])
									+ (["--verbose"] if options.verbose else [])
								, shell=False)
			else:
				try:
					connection.close()
				except:
					pass
				time.sleep(30)
		else:
			master_configuration,created = Scanner.ScannerNode.objects.get_or_create(hostname = "tlsprober-cluster", defaults={
																						"scan_parameters":"not used",
																						"active_node":True,
																						})
			configuration,created = Scanner.ScannerNode.objects.get_or_create(hostname = computername, defaults={
																						"scan_parameters":"--processes 40 --iterations 40",
																						"active_node":True,
																						})
			configuration.save()
			transaction.commit()
	
			if (master_configuration.active_node and configuration.active_node and 
				Scanner.ScannerRun.objects.filter(enabled=True).count() >0):
				"""Any enabled Scanner jobs?"""
				done_something = True
				if master_configuration.active_node and configuration.active_node:
					if not options.nogit:
						"""Check out code to be used"""
						subprocess.call(["git", "pull",])
						subprocess.call(["git", "submodule", "update", "--recursive"])
						
						master_branch = "pincushion" if options.use_testbase2 else "master"
							
						run = Scanner.ScannerRun.objects.filter(enabled=True).order_by("-priority", "entered_date")[0]
						branch = run.branch
						subprocess.call(["git", "checkout", branch if branch else master_branch])
						subprocess.call(["git", "submodule", "update", "--recursive"])
						
					try:
						connection.close()
					except:
						pass
					"""Start the scanner on this node for the job"""
					subprocess.call(["python", "-O", 
										"scan_start.py",
											"--performance",
											"--managed"]
										+ (["--testbase2"] if options.use_testbase2 else [])
										+ (["--verbose"] if options.verbose else [])
									, cwd = "scan"
									, shell=False)
				else:
					try:
						connection.close()
					except:
						pass
					time.sleep(30)
			
		if not done_something :
			if not options.persistent:	
				break; # exit if nothing is going on, wait 20 minutes, then recheck
			try:
				connection.close()
			except:
				pass
			time.sleep(10*60) # if there are no runs, sleep for 10 minutes

main()
