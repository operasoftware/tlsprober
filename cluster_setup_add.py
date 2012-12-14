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


"""
Add new servername entries to an existing run

CSV formats

   index, hostname, port, protocol
   index, hostname, port			# HTTPS assumed
   index, hostname  				# Port 443, HTTPS assumed; line starts with number
   hostname, port					# HTTPS assumed; line starts with letter; port may be empty

Options:

--input	<name>	: CSV File containing a list of hosts
--count <num>	: Only configure max <num> servers from the source   

--run-id <num>	: add the new entries to this job 

--verbose		: Print more information

--testbase2		: use the debug test database for this job

--threads <num>	: Use the specified number of threads when inserting the entries for the job


"""


from optparse import OptionParser
import probedb.standalone
import probedb.cluster.models as Cluster
import probedb.probedata2.models as Probe
import probedb.resultdb2.models as Results
import fileinput
from django.db import connection, transaction
import datetime
import threading
from multiprocessing import Process, JoinableQueue as Queue, Lock

def __ProgressCounter(run, queue, threads, options):
	i=0
	while True:
		queue.get()

		i += 1
		if i%100 == 0:
			if options.verbose:
				print "Queued ", i, "servers so far. Threads active ", sum([t.is_alive() for t in threads])

		queue.task_done()

def SetupQueueThread(tid, run, probe_servers, progress_queue, ):
	connection.close()
	try:
		while True:
			item = probe_servers.get()

			if isinstance(item, int):
				try:
					item = Probe.Server.objects.get(id=item)
				except:
					probe_servers.task_done()
					continue
					
				hostname = item.servername.strip()
				if (not hostname or 
						any([x in hostname for x in " \t%/&#\"'\\{[]}()*,;<>$"]) or 
						any([ord(x)>=128 or ord(x)<=32  for x in hostname])):
					item.enabled = False
					item.save()
					probe_servers.task_done()
					continue

				hostname = hostname.strip(".")
				while hostname.find("..")>=0:
					hostname = hostname.replace("..", ".")
				
				if hostname != item.servername:
					item.enabled = False
					item.save()
					item = "0," + hostname+","+str(item.port) # Convert to string to correct the list 

			if not isinstance(item, Probe.Server):
				hostname_line = item
				
				if not hostname_line.strip():
					probe_servers.task_done()
					continue
			
				split_line = hostname_line.strip().split(",")
			
				if len(split_line) > 2:
					(index, hostname, port) = split_line[:3]
				else: 
					port = ""
					(var1, var2) = split_line
					if var1.isdigit():
						(index, hostname) = (var1, var2)
					else:
						(hostname, port) =  (var1, var2)
						
				
				hostname = hostname.strip()
				if (not hostname or 
						any([x in hostname for x in " \t%/&#\"'\\{[]}()*,;<>$"]) or 
						any([ord(x)>=128 or ord(x)<=32  for x in hostname])):
					probe_servers.task_done()
					continue
				
				hostname = hostname.strip(".")
				while hostname.find("..")>=0:
					hostname = hostname.replace("..", ".")
					
				if not port:
					port = 443
				else:
					port = int(port)
	
				sn_t = "%s:%05d" % (hostname, port)
				(item, created) = Probe.Server.objects.get_or_create(
									full_servername = sn_t,
									defaults={'enabled':True,
											"alexa_rating":0,
											"servername":hostname, 
											"port": port, 
											}
									)

				if created:
					item.Construct()

			if item.enabled:
				try:	
					sid = transaction.savepoint()
					run_entry = Probe.ProbeQueue.objects.create(part_of_run=run,server=item,state=Probe.ProbeQueue.PROBEQ_IDLE)
					transaction.savepoint_commit(sid)
					progress_queue.put(True)
				except:
					transaction.savepoint_rollback(sid)
					pass

			probe_servers.task_done()
	except:
		pass

def setup_queue(options):	
	probe_servers = Queue()
	progress_queue = Queue()

	run = Probe.ProbeRun.objects.get(id = options.run_id)

	summary_top = Results.ResultSummaryList.objects.get(part_of_run=run)
	summary_top.setup()

	connection.close()
	
	threads = [] 
	for i in range(options.threads):
		new_thread = Process(target=SetupQueueThread, args=(i,run, probe_servers, progress_queue))
		new_thread.daemon = True
		new_thread.start()
		threads.append(new_thread)
		
	progress_thread = threading.Thread(target=__ProgressCounter, args=(run,  progress_queue, threads,options))
	progress_thread.daemon = True
	progress_thread.start()

	i = 0;
	if options.input_filename and (not options.count or i < options.count):
		for hostname_line in fileinput.input(options.input_filename, openhook=fileinput.hook_compressed):
			probe_servers.put(hostname_line)
			i+=1
			if options.count and i >= options.count:
				break;

	probe_servers.join()
	progress_queue.join()
	
	return run


def main():
	options_config = OptionParser()
	
	options_config.add_option("--input", action="store", type="string", dest="input_filename", default="testlist.csv")
	options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
	options_config.add_option("--threads", action="store", type="int", dest="threads", default=30)
	options_config.add_option("--verbose", action="store_true", dest="verbose")
	options_config.add_option("--count", action="store", type="int", dest="count", default=0)
	options_config.add_option("--run-id", action="store", type="int", dest="run_id", default=0)
	
	(options, args) = options_config.parse_args()
	
	started = datetime.datetime.now()
	
	run = setup_queue(options)
	
	if options.verbose:
		print "Run %d for %s/%s has been updated with more items. Total %d items" %(run.id, run.source_name, run.description, Probe.ProbeQueue.objects.filter(part_of_run=run).count())
	
	ended = datetime.datetime.now()
	
	if options.verbose:
		print "Time to run: ", (ended-started)

if __name__ == "__main__":
	main()