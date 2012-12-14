# -*- Mode: python; tab-width: 4; indent-tabs-mode: nil; -*-
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
The prober engine, performs the actual probes, and insertion
into the database. Started by cluster_start.py
"""

import socket
import fileinput
import libinit
from optparse import OptionParser
from probe_server import ProbeServer
import time

import probedb.standalone
from db_list import db_list
import probedb.probedata2.models as Probe
import sys
from django.db import connection, transaction

class test_output:
	
	"""Test queue and result presenter"""
	def __init__(self, options, args, *other):
		self.args = args

	def log_performance(self):
		pass

	class Queue:
		def __init__(self,args):
			self.args = args

		def IsActive(self):
			return True
		
		def __iter__(self):
			def make_entry(x):
				ret = x.split(":") 
				if len(ret) <1:
					raise Exception()
				elif  len(ret) <2:
					ret += [443, Probe.Server.PROTOCOL_HTTPS]
				elif len(ret) < 3:
					ret[1] = int(ret[1])
					ret.append(Probe.Server.PROTOCOL_PORT.get(ret[1], Probe.Server.PROTOCOL_HTTPS))
				else:
					ret[1] = int(ret[1])

				(server, port,protocol) = ret[0:3]
				sn_t = "%s:%05d" % (server, port)
				class server_item_object:
					pass
				server_item = server_item_object();
				server_item.full_servername = sn_t
				server_item.enabled=True
				server_item.alexa_rating=0
				server_item.servername= server 
				server_item.port= port
				server_item.protocol= protocol
				server_item.id = 0

				return server_item
			return iter([make_entry(x) for x in args])

	def GetQueue(self):
		return test_output.Queue(self.args)

	def print_probe(self, prober):
		print str(prober)

options_config = OptionParser()

options_config.add_option("-n", action="store", type="int", dest="index", default=1)
options_config.add_option("--alone", action="store_true", dest="standalone")
options_config.add_option("--debug", action="store_true", dest="debug")
options_config.add_option("--verbose", action="store_true", dest="verbose")
options_config.add_option("--run-id", action="store", type="int", dest="run_id", default=0)
options_config.add_option("--source", action="store", type="string", dest="source_name", default="TLSProber")
options_config.add_option("--description", action="store", type="string", dest="description",default="TLSProber")
options_config.add_option("--file", action="store_true", dest="file_list_only")
options_config.add_option("--processes", action="store", dest="process_count", default=1)
options_config.add_option("--max", action="store", type="int", dest="max_tests",default=0)
options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--performance", action="store_true", dest="register_performance")
options_config.add_option("--large_run", action="store_true", dest="large_run")
options_config.add_option("--small_run", action="store_true", dest="small_run")
options_config.add_option("--test", action="store_true", dest="just_test")

(options, args) = options_config.parse_args()

if not options.standalone and options.index != 1:
	time.sleep(options.index % 10);

	
output_target = db_list if not options.just_test else test_output 

debug = options.debug
tested_count = 0;

out_files = output_target(options, args)
out_files.debug = options.verbose

hostlist = out_files.GetQueue()
	
for server_item in hostlist:
	if not server_item.enabled:
		continue
	
	sock = None
	try:
		if options.verbose:
			print "testing connection to ", server_item.servername
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		if not sock:
			if options.verbose:
				print "fail connect"
			time.sleep(0.1)
			out_files.log_performance()
			continue

		sock.settimeout(10)  #Only on python 2.3 or greater
		sock.connect((server_item.servername, server_item.port))
		if not sock.fileno():
			if options.verbose:
				print "fail connect"
			time.sleep(0.1)
			out_files.log_performance()
			continue
		ip_address = sock.getpeername()[0]
			
		sock.close()
		sock = None
		probedalready = False
		if not options.just_test:
			(probedalready,created) = Probe.ServerIPProbed.GetIPLock(out_files.run, ip_address, server_item) 
			if not created:
				try:
					probedalready.server_aliases.add(server_item)
				except:
					pass # COmpletely ignore problems in this add
				time.sleep(0.1)
				out_files.log_performance()
				continue; # don't probe, already tested this port on this IP address
				
			
		
	except socket.error, error:
		if options.verbose:
			print "Connection Failed socket error: ", error.message, "\n"
		if sock:
			sock.close()
			sock = None
		time.sleep(0.1)
		out_files.log_performance()

		continue
	except:
		raise 

	if options.verbose:
		print "Probing ",server_item.id, ",", server_item.servername, ":", server_item.port, ":", server_item.protocol
		
	prober = ProbeServer(server_item)
	if options.verbose:
		prober.debug = True
	
	if not options.just_test:
		prober.ip_address_rec.append(probedalready)
	prober.Probe(do_full_test=True)
	
	if options.verbose:
		print "Probed ",server_item.id, ",", server_item.servername, ":", server_item.port, ":", server_item.protocol

	if not options.just_test:
		for ip in prober.ip_addresses:
			if ip != ip_address:
				(probedalready,created) = Probe.ServerIPProbed.GetIPLock(out_files.run, ip_address, server_item)
				prober.ip_address_rec.append(probedalready)
	
				if not created:
					try:
						probedalready.server_aliases.add(server_item)
					except:
						pass # COmpletely ignore problems in this add
	
	out_files.print_probe(prober)
	
	tested_count += 1
	if int(options.max_tests)  and int(options.max_tests) <= tested_count:
		break

if options.verbose:
	print "Finished"
