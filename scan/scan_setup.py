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
Configure a scanner run to discover TLS capable servers
"""

import sys, os.path

sys.path.insert(1, os.path.join(".."))

import libinit

from optparse import OptionParser
import probedb.standalone
import probedb.probedata2.models as Probe
import probedb.scanner.models as Scanner
import fileinput
import threading
import Queue
from django.db import connection, transaction
import datetime
import csv

safe_stdout = threading.Lock()
visited_servers=set()
queued= 0
safe_visited_servers = threading.Lock()

def __ProgressCounter(queue, threads, options):
	global safe_stdout
	
	i=0
	while True:
		queue.get()

		i += 1
		if i%100 == 0:
			if options.verbose:
				safe_stdout.acquire()
				print "Queued ", i, "servers so far. Threads active ", sum([t.is_alive() for t in threads])
				safe_stdout.release()

		queue.task_done()

def SetupIPQueueThread(tid, run, probe_servers, progress_queue, options):
	"""Thread for specifiying a set of IP Queue entries, excluding special IP addresses"""

	global safe_stdout
	global queued
	global visited_servers
	global safe_visited_servers

	exclusionlist1 = ([
			0,
			10,
			127,
			] + 
			range(240,256) + 
			range(224,240) 
			)
	
	exclusionlist2 = ([
			[192,168],
			[169,254],
			[198,18],
			[198,19],
			] + 
			[[172,x] for x in range(16,32)]
			)

	exclusionlist3 = [
			[192,0,0],
			[192,0,2],
			[192,88,99],
			[169,254],
			[192,0,0],
			[198,51,100],
			[203,0,113],
			] 
	
	protocols = []
	if options.https_only:
		protocols.append(Probe.Server.PROTOCOL_HTTPS)
	if options.mail_only:
		protocols += [Probe.Server.PROTOCOL_IMAP,
					Probe.Server.PROTOCOL_POP,
					Probe.Server.PROTOCOL_SMTP,
					Probe.Server.PROTOCOL_IMAP_S,
					Probe.Server.PROTOCOL_POP_S,
					Probe.Server.PROTOCOL_SMTP_S,
					]

	while True:
		prefix, port = probe_servers.get()
		if (prefix[0] in exclusionlist1 or 
			any([ex_item == prefix for ex_item in exclusionlist2])):
			probe_servers.task_done();
			continue
		
		for x in range(256):
			item = prefix + [x]
			if any([ex_item == item for ex_item in exclusionlist3]):
				continue

			for protocol in protocols:
				try:
					print item, port, protocol
					port1 = port if port else Probe.Server.PROTOCOL_PORT_MAP.get(protocol,443)
					for port2 in port1:
						if options.dryrun:
							safe_stdout.acquire()
							print "Adding", ".".join([str(y) for y in item + [0]]) + "/24",":",port
							safe_stdout.release()
						else:
							sid = transaction.savepoint()
							cursor = connection.cursor()
							cursor.execute("""INSERT INTO scanner_scannerqueue (part_of_run_id, server, port, protocol, state)  
									VALUES (%s,%s,%s,%s,%s)""", [str(run.id), ".".join([str(y) for y in item + [0]]) + "/24", str(port2), protocol, Scanner.ScannerQueue.SCANQ_IDLE]
								)
							transaction.savepoint_commit(sid)
							transaction.commit_unless_managed()
		
					progress_queue.put(True)
				except:
					pass; # Ignore errors
					
		probe_servers.task_done();

def SetupQueueThread(tid, run, probe_servers, progress_queue, exclude, options):
	"""
	Setup general scan entries, check for validity, 
	passing IP addresses over to the IP address processing function
	"""

	global safe_stdout
	global queued
	global visited_servers
	global safe_visited_servers
	
	protocols = []
	if options.https_only:
		protocols.append(Probe.Server.PROTOCOL_HTTPS)
	if options.mail_only:
		protocols += [Probe.Server.PROTOCOL_IMAP,
					Probe.Server.PROTOCOL_POP,
					Probe.Server.PROTOCOL_SMTP,
					Probe.Server.PROTOCOL_IMAP_S,
					Probe.Server.PROTOCOL_POP_S,
					Probe.Server.PROTOCOL_SMTP_S,
					]

	try:
		while True:
			item = probe_servers.get()

			hostname_line = item
				
			if not hostname_line.strip():
				probe_servers.task_done()
				continue
		
			split_line = hostname_line.strip().split(",")
		
			if len(split_line) > 2:
				(index, hostname, port) = split_line[:3]
			elif len(split_line) == 1:
				port = ""
				index = 0
				hostname = split_line[0]
			else: 
				port = ""
				(var1, var2) = split_line
				if var1.isdigit():
					(index, hostname) = (var1, var2)
				else:
					(hostname, port) =  (var1, var2)
					
			hostname = hostname.strip(".")
			while hostname.find("..")>=0:
				hostname = hostname.replace("..", ".")

			if port:				
				port = int(port)
			
			hostname = hostname.strip()

			if (not hostname or 
					any([x in hostname for x in " \t%/&#\"'\\{[]}()*,;<>$"]) or 
					any([ord(x)>=128 or ord(x)<=32  for x in hostname])):
				if "/" in hostname and not any([y not in "0123456789./" for y in hostname]):
					for protocol in protocols:
						try:
							print hostname, port, protocol
							port1 = port if port else Probe.Server.PROTOCOL_PORT_MAP.get(protocol,443)
							for port2 in port1:
								if options.dryrun:
									safe_stdout.acquire()
									print "Adding", hostname,":",port2, ":",protocol
									safe_stdout.release()
								else:
									sid = transaction.savepoint()
									cursor = connection.cursor()
									cursor.execute("""INSERT INTO scanner_scannerqueue (part_of_run_id, server, port, protocol, state)  
											VALUES (%s,%s,%s,%s,%s)""", [str(run.id), hostname, str(port2), protocol, Scanner.ScannerQueue.SCANQ_IDLE]
										)
									transaction.savepoint_commit(sid)
									transaction.commit_unless_managed()
				
								progress_queue.put(True)
						except:
							transaction.savepoint_rollback(sid)
							pass; # Ignore errors
						
				probe_servers.task_done()
				continue
			

			if "-" in hostname and not any([y not in "0123456789.-" for y in hostname]):
				InsertIPRanges(run, hostname,port, progress_queue, options)
			elif hostname not in exclude:
				for protocol in protocols:
					try:
						port1 = [port] if port else Probe.Server.PROTOCOL_PORT_MAP.get(protocol,443)
						for port2 in port1:
							if options.dryrun:
								safe_stdout.acquire()
								print "Adding", hostname,":",port2, ":",protocol
								safe_stdout.release()
							else:
								sid = transaction.savepoint()
								print "insert:",run.id, hostname, port, port2, protocol
								cursor = connection.cursor()
								cursor.execute("""INSERT INTO scanner_scannerqueue (part_of_run_id, server, port, protocol, state)  
										VALUES (%s,%s,%s,%s,%s)""", [str(run.id), hostname, str(port2), protocol, Scanner.ScannerQueue.SCANQ_IDLE]
									)
								transaction.savepoint_commit(sid)
								transaction.commit_unless_managed()
								
							progress_queue.put(True)
					except:
						transaction.savepoint_rollback(sid)
						pass; # Ignore errors
			probe_servers.task_done()
	except:
		raise
		pass

def InsertIPRanges(run, iprange,port, progress_queue, exclude, options):
	"""
	Process IP address entries, passing ranges on to 
	special code to break them up into separate entires
	"""
	global safe_stdout

	protocols = []
	if options.https_only:
		protocols.append(Probe.Server.PROTOCOL_HTTPS)
	if options.mail_only:
		protocols += [Probe.Server.PROTOCOL_IMAP,
					Probe.Server.PROTOCOL_POP,
					Probe.Server.PROTOCOL_SMTP,
					Probe.Server.PROTOCOL_IMAP_S,
					Probe.Server.PROTOCOL_POP_S,
					Probe.Server.PROTOCOL_SMTP_S,
					]

	if "-" not in iprange:
		for protocol in protocols:
			try:
				port1 = [port] if port else Probe.Server.PROTOCOL_PORT_MAP.get(protocol,443)
				for port2 in port1:
					if options.dryrun:
						safe_stdout.acquire()
						print "Adding", iprange,":",port2, ":",protocol
						safe_stdout.release()
					else:
						item = Scanner.ScannerQueue.objects.create(
										part_of_run = run,
										server = iprange,
										port= port2,
										protocol=protocol,
										state = Scanner.ScannerQueue.SCANQ_IDLE 
										)
						sid = transaction.savepoint()
						print "insert:", iprange, port, port2, protocol
						cursor = connection.cursor()
						cursor.execute("""INSERT INTO scanner_scannerqueue (part_of_run_id, server, port, protocol, state)  
								VALUES (%s,%s,%s,%s,%s)""", [str(run.id), iprange, str(port2), protocol, Scanner.ScannerQueue.SCANQ_IDLE]
							)
						transaction.savepoint_commit(sid)
						transaction.commit_unless_managed()
		
					progress_queue.put(True)
			except:
				transaction.savepoint_rollback(sid)
				pass; # Ignore errors
			return
	
	prefix1,sep, postfix1 = iprange.partition("-")  
	
	prefix2 = prefix1.split(".") if prefix1 else ["0"]
	
	prefix = prefix2[:-1] if len(prefix2)>1 else []
	start = int(prefix2[-1]) if prefix2[-1] else 0 
	
	postfix2 = postfix1.split(".") if postfix1 else ["255"]
	postfix = postfix2[1:] if len(postfix2)>1 else []
	end = int(postfix2[0]) if postfix2[0] else 255 
	
	if not postfix and start == 0 and end == 255: 
		InsertIPRanges(run, ".".join(prefix + ["0"])+"/24", port, progress_queue, options)
	else:
		for i in range(start, end+1):
			InsertIPRanges(run, ".".join(prefix + [str(i)]+ postfix), port, progress_queue, options)

def setup_queue(options, args):
	"""Manage the process for setting up the scan queue""" 
	global visited_servers

	probe_servers = Queue.Queue()
	progress_queue = Queue.Queue()

	exclude = set()
	if options.exclude_filename:
		exfile = csv.reader(open(options.exclude_filename, "rb"))
		for ex in exfile:
			exclude.add(ex[1]) 

	if options.dryrun:
		run = None
	else:
		run = Scanner.ScannerRun.objects.create(enabled=False, 
									source_name=options.source_name.strip('"').strip(), 
									description=options.description.strip('"').strip(),
									branch = options.branch.strip('"').strip() if options.branch and options.branch.strip('"').strip() else None,
									priority = options.priority
									)

	threads = []
	thread_target =  SetupQueueThread if not options.generate_ipscan else SetupIPQueueThread
	for i in range(options.threads):
		new_thread = threading.Thread(target=thread_target, args=(i,run, probe_servers, progress_queue, exclude, options))
		new_thread.daemon = True
		new_thread.start()
		threads.append(new_thread)
		
	progress_thread = threading.Thread(target=__ProgressCounter, args=(progress_queue, threads, options))
	progress_thread.daemon = True
	progress_thread.start()

	i = 0;

	if options.generate_ipscan:
		for ip1 in range(256):
			for ip2 in range(256):
				probe_servers.put(([ip1, ip2], 443))
				i+=1
				if options.count and i >= options.count:
					break;
	else:
		for input_filename in args:
			for hostname_line in fileinput.input(input_filename):
				if options.verbose:
					safe_stdout.acquire()
					print hostname_line
					safe_stdout.release()
				probe_servers.put(hostname_line)
				i+=1
				if options.count and i >= options.count:
					break;

	probe_servers.join()
	progress_queue.join()

	for i in range(3):
		cursor = connection.cursor()
		cursor.execute("ANALYZE scanner_scannerqueue")
	
	if run:
		run.enabled = True
		run.save()
	
	return run


options_config = OptionParser()

options_config.add_option("--ipscan", action="store_true", dest="generate_ipscan");
options_config.add_option("--source", action="store", type="string", dest="source_name", default="TLSProber")
options_config.add_option("--description", action="store", type="string", dest="description",default="TLSProber")
options_config.add_option("--priority", action="store", dest="priority", default="5")
options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--threads", action="store", type="int", dest="threads", default=30)
options_config.add_option("--verbose", action="store_true", dest="verbose")
options_config.add_option("--branch", action="store", type="string", dest="branch")
options_config.add_option("--count", action="store", type="int", dest="count", default=0)
options_config.add_option("--dryrun", action="store_true", dest="dryrun")
options_config.add_option("--exclude", action="store", type="string", dest="exclude_filename")
options_config.add_option("--https", action="store_true", dest="https_only")
options_config.add_option("--mail", action="store_true", dest="mail_only")


(options, args) = options_config.parse_args()

if options.priority <1 :
	options.priority = 1

if not options.https_only and not options.mail_only:
	options.https_only = True 
	options.mail_only =True
		
started = datetime.datetime.now()

run = setup_queue(options, args)

if options.verbose:
	print "Run %d for %s/%s has been initiated. %d items" %(run.id, options.source_name, options.description, Scanner.ScannerQueue.objects.filter(part_of_run=run).count())

ended = datetime.datetime.now()

if options.verbose:
	print "Time to run: ", (ended-started)
