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

--verbose		: Print more information
--tag <name>	: tag the source code used by the run with this prefix 

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

def __ProgressCounter(run, cluster_task, queue, threads, options):
	i=0
	while True:
		queue.get()

		i += 1
		if i%100 == 0:
			if options.verbose:
				print "Queued ", i, "servers so far. Threads active ", sum([t.is_alive() for t in threads])

		if i>3000000 and not cluster_task.enabled:				
			cluster_task.enabled=True
			cluster_task.save

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
					item = "0," + hostname+","+str(item.port)+","+item.protocol # Convert to string to correct the list 

			if not isinstance(item, Probe.Server):
				hostname_line = item
				
				if not hostname_line.strip():
					probe_servers.task_done()
					continue
			
				split_line = hostname_line.strip().split(",")
			
				if len(split_line) > 3:
					(index, hostname, port, protocol) = split_line[:4]
					port = port.strip()
					protocol = protocol.strip()
					if not protocol or protocol.upper() not in Probe.Server.PROTOCOL_PORT_MAP:
						protocol = Probe.Server.PROTOCOL_PORT.get(int(port) if port else 443, Probe.Server.PROTOCOL_HTTPS) 
				elif len(split_line) > 2:
					(index, hostname, port) = split_line[:3]
					port = port.strip()

					protocol = Probe.Server.PROTOCOL_PORT.get(int(port) if port else 443, Probe.Server.PROTOCOL_HTTPS) 
				else: 
					port = ""
					(var1, var2) = split_line
					if var1.isdigit():
						(index, hostname) = (var1, var2)
					else:
						(hostname, port) =  (var1, var2)
						port=port.strip()
					protocol = Probe.Server.PROTOCOL_PORT.get(int(port) if port else 443, Probe.Server.PROTOCOL_HTTPS) 
						
				
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
	
				sn_t = "%s:%05d:%s" % (hostname, port,protocol)
				(item, created) = Probe.Server.objects.get_or_create(
									full_servername = sn_t,
									defaults={'enabled':True,
											"alexa_rating":0,
											"servername":hostname, 
											"port": port, 
											"protocol":protocol.upper(), 
											}
									)

				if created:
					item.Construct()

			if item.enabled:
				try:	
					#run_entry = Probe.ProbeQueue.objects.create(part_of_run=run,server=item,state=Probe.ProbeQueue.PROBEQ_IDLE)
					sid = transaction.savepoint()
					cursor = connection.cursor()
					cursor.execute("""INSERT INTO probedata2_probequeue (part_of_run_id, server_id, state)  
							VALUES (%s,%s,%s)""", [str(run.id), str(item.id), Probe.ProbeQueue.PROBEQ_IDLE]
						)
					transaction.savepoint_commit(sid)
					transaction.commit_unless_managed()
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
	
	source_name=options.source_name.strip('"').strip()
	
	sort_order = None
	sort_order_def = Probe.ProbeRunSort.objects.get_or_create(sort_name="__default__", defaults={"sort_rank":1000})[0]
	sort_order_q = Probe.ProbeRunSort.objects.filter(sort_name=source_name)
	if sort_order_q.count() > 0:
		sort_order = sort_order_q[0]
	else:
		sort_order = sort_order_def
	

	run = Probe.ProbeRun.objects.create(
									source_name=source_name, 
									description=options.description.strip('"').strip(),
									branch = options.branch.strip('"').strip() if options.branch and options.branch.strip('"').strip() else None,
									sort_rank = sort_order
									)

	summary_top = Results.ResultSummaryList(part_of_run=run)
	summary_top.save()
	summary_top.setup()

	cluster_task = Cluster.ClusterRun.objects.create(perform_run = run, enabled=True, priority=options.priority)
	
	if options.input_queue or options.input_queue_id:
		if options.input_queue_id:
			queue_list = Probe.PreparedQueueList.objects.get(id=options.input_queue_id)
		else:
			queue_list = Probe.PreparedQueueList.objects.get(list_name=options.input_queue)
			
		queue_list.InitQueue(run)
		
		cluster_task.enabled=True
		cluster_task.save()
		return run

	connection.close()
	
	threads = [] 
	for i in range(options.threads):
		new_thread = Process(target=SetupQueueThread, args=(i,run, probe_servers, progress_queue))
		new_thread.daemon = True
		new_thread.start()
		threads.append(new_thread)
		
	progress_thread = threading.Thread(target=__ProgressCounter, args=(run, cluster_task, progress_queue, threads,options))
	progress_thread.daemon = True
	progress_thread.start()

	i = 0;
	if not options.file_list_only:
		for host in Probe.Server.objects.filter(enabled = True).values_list("id",flat=True):
			probe_servers.put(host)
			i+=1
			if options.count and i >= options.count:
				break;

	if options.input_filename and (not options.count or i < options.count):
		for hostname_line in fileinput.input(options.input_filename, openhook=fileinput.hook_compressed):
			probe_servers.put(hostname_line)
			i+=1
			if options.count and i >= options.count:
				break;

	probe_servers.join()
	progress_queue.join()
	
	for i in range(0,3):
		connection.cursor().execute("ANALYZE "+ ("VERBOSE " if options.verbose else "")+"probedata2_probequeue")
	
	cluster_task.enabled=True
	cluster_task.save()
	
	return run


def main():
	options_config = OptionParser()
	
	options_config.add_option("--input", action="store", type="string", dest="input_filename", default="testlist.csv")
	options_config.add_option("--queue", action="store", type="string", dest="input_queue")
	options_config.add_option("--queue-id", action="store", type="int", dest="input_queue_id")
	options_config.add_option("--source", action="store", type="string", dest="source_name", default="TLSProber")
	options_config.add_option("--description", action="store", type="string", dest="description",default="TLSProber")
	options_config.add_option("--file", action="store_true", dest="file_list_only")
	options_config.add_option("--priority", action="store", dest="priority", default="5")
	options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
	options_config.add_option("--threads", action="store", type="int", dest="threads", default=30)
	options_config.add_option("--verbose", action="store_true", dest="verbose")
	options_config.add_option("--branch", action="store", type="string", dest="branch")
	options_config.add_option("--count", action="store", type="int", dest="count", default=0)
	
	(options, args) = options_config.parse_args()
	
	if options.priority <1 :
		options.priority = 1
	
	started = datetime.datetime.now()
	
	run = setup_queue(options)
	
	if options.verbose:
		print "Run %d for %s/%s has been initiated. %d items" %(run.id, options.source_name, options.description, Probe.ProbeQueue.objects.filter(part_of_run=run).count())
	
	ended = datetime.datetime.now()
	
	if options.verbose:
		print "Time to run: ", (ended-started)

if __name__ == "__main__":
	main()