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

'''
Created on 2. okt. 2010

@author: Yngve
'''

"""
Scan servers in domains from the scan task list, vary the 
hostname for each domain
"""

import sys,os,subprocess,time,os.path

sys.path.insert(1, os.path.join(".."))
sys.path.insert(1, os.path.join("..","tlslite"))

import libinit

from optparse import OptionParser
import probedb.standalone
import probedb.probedata2.models as ProbeData
import probedb.scanner.models as Scanner
import threading
import socket
from tlslite import TLSConnection, HandshakeSettings
from django.db import connection, transaction
import tlscommon.ssl_v2_test as SSLv2Test
import tlscommon.tls_test as TLSTest
import tlscommon.mail_test as MailTest


iterated_prefixes = [
	"www",
	"secure",
	"mail",
	"webmail",
	"ssl",
	"web",
		]
label_prefixes = [
	"www",
	"secure",
	"shop",
	"ssl",
	"online",
	"bank",
	"mail",
	"webmail",
	"owa",
	"my",
	"portal",
	"m",
	"email",
	"login",
	"store",
	"wap",
	"exchange",
	"intranet",
	"mobile",
	"support",
	"extranet",
	"admin",
	"web",
	"billing",
	"members",
	"stat",
	"jobs",
	"apps",
	"tickets",
	"outlook",
	"banking",
	"service",
	"services",
	"home",
	"reservations",
	"app",
	"register",
	"bankingportal",
	"myaccount",
	"forum",
	"ebill",
	"access",
	"blackboard",
	"wiki",
	"member",
	"connect",
	"vpn",
	"lists",
	"ibank",
	"order",
	"signup",
	"mymail",
	"careers",
	"campus",
	"account",
	"student",
	"clients",
	"customer",
	"client",
	"webaccess",
	"auth",
	"info",
	"forums",
	"apply",
	"booking",
	"go",
	"payment",
	"partners",
	"ebank",
	"accounts",
	"svn",
	"helpdesk",
	"bill",
	"community",
	"live",
	"affiliates",
	"onlinebanking",
	"gateway",
	"ebanking",
	"trade",
	"orders",
	"blog",
	"pay",
	"commerce",
	"folders",
	"help",
	"tls"
	]

protocol_prefixes_map = [
		("imap", [ProbeData.Server.PROTOCOL_IMAP, ProbeData.Server.PROTOCOL_IMAP_S]),
		("smtp", [ProbeData.Server.PROTOCOL_SMTP, ProbeData.Server.PROTOCOL_SMTP_S]),
		("pop", [ProbeData.Server.PROTOCOL_POP, ProbeData.Server.PROTOCOL_POP_S]),
		("mail", [ProbeData.Server.PROTOCOL_IMAP, ProbeData.Server.PROTOCOL_IMAP_S,
				ProbeData.Server.PROTOCOL_SMTP, ProbeData.Server.PROTOCOL_SMTP_S,
				ProbeData.Server.PROTOCOL_POP, ProbeData.Server.PROTOCOL_POP_S,
				]),
		
		]

protocol_prefixes = {}
for (pre, prots) in protocol_prefixes_map:
	for p in prots:
		protocol_prefixes.setdefault(p,[]).append(pre)

@transaction.commit_manually
def RegisterServer(queue, servername, port, protocol, options):
	"""Register a found server"""
	if options.just_test:
		print servername, ":", port, ":", protocol
		return
	try:
		Scanner.ScannerResults.objects.create(part_of_run = queue.run, server=servername, port = port, protocol=protocol)
		transaction.commit()
	except:
		transaction.rollback()
		pass # ignore errors

class DoTLSTest(object):
	"""Perform a scan test for the given servername"""
	def __init__(self, servername, port, protocol=ProbeData.Server.PROTOCOL_HTTPS):
		self.servername = servername
		self.port=port
		self.protocol = protocol
		self.debug = False
		self.available = False
		self.not_available = False
		self.ip_addresses = []
		self.tolerate_ssl_v2 = False
		self.only_ssl_v2 = False
		self.supported_versions= []
		self.support_v2_export_ciphers = False
		self.support_v2_ciphers = set()
		self.return_unexpected_v2_ciphers = False
		self.certificates = None
	
	def TestTLS(self):
		"""Perform smoke tests for SSL v3, SSL v2, and TLS 1.x on server:port:protocol"""
		if TLSTest.TestConnectionV3(self, (3,0), (3,0)):
			return True 

		if self.protocol == ProbeData.Server.PROTOCOL_HTTPS:
			settings = HandshakeSettings.HandshakeSettings()
			settings.maxVersion = (3,0)
	
			if SSLv2Test.TestConnectionV2(self, settings):
				return True
		
		for minor in [1,2,3]:
			if TLSTest.TestConnectionV3(self, (3,minor), (3,minor)):
				return True 
		
		return False
	


def TestServer(servername, port, protocol, verbose):
	"""Test this server, if it is found to be available on the net"""
	if verbose:
		print "testing server",servername, ":", port, ":",protocol
	
	sock = None

	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except socket.error, error:
		if verbose: 
			print "Probe: socket create error: ", error.message, "\n"
		return False
	except:
		if verbose:
			print "\tNo Connection", servername, ":", port
		return False 
	

	try:
		sock.settimeout(3)  #Only on python 2.3 or greater
		sock.connect((servername, port))
			
	except socket.error, error:
		if verbose: 
			print "Probe: ", servername, ":", port,  ":",protocol,": Connection Failed socket error: ", error.message, "\n"
		return False
	except:
		if verbose:
			print "\tNo Connection\n"
		return False

	try:
		s = sock.recv(10);
	except socket.timeout:
		sock.close()
		if protocol in ProbeData.Server.PROTOCOL_DIRECT_TLS:
			tester = DoTLSTest(servername, port, protocol)
			# Did not receive data, server is presumably a TLS server, but let's test it anyway
			if tester.TestTLS():
				return True
		return False
	except socket.error, error:
		if verbose: 
			print "Probe: ", servername, ":", port, ":",protocol, ": Connection Read socket error: ", error.message, "\n"
		return False
	except:
		if verbose:
			print "\tNo Connection\n"
		return False
	finally:
		sock.close();
		
	if s and protocol in ProbeData.Server.PROTOCOL_DIRECT_TLS:
		if verbose:
			print "\tNo Connection\n"
		return False # received data, server is likely not a server
	
	tester = DoTLSTest(servername, port)
	# Did not receive data (or received data on mail protocol), server is presumably a TLS server, but let's test it anyway
	if tester.TestTLS():
		return True
	return False

def TestIPRange(queue, hostname, port,protocol, verbose, options):
	"""Test all servers in an IP address range"""
	
	(ipaddr, sep, bits) = hostname.partition("/")
	if sep != "/" or any([y not in "0123456789." for y in ipaddr]):
		return
	
	iplabels = ipaddr.split(".")
	if len(iplabels) != 4:
		return
	
	for i in range(256):
		if not queue.IsActive():
			queue.cancel()
			return
		candidate = ".".join(iplabels[0:3]+[str(i)])
		if verbose:
			print "testing IP address:", candidate, ":", port, ":", protocol 
		if TestServer(candidate, port, protocol, verbose):
			try:
				(host, aliases, ip) = socket.gethostbyaddr(candidate)
				print (host, aliases, ip)
				if host or aliases:
					if host:
						RegisterServer(queue,host,port, protocol, options)
					for x in aliases:
						RegisterServer(queue,x,port, protocol, options)
				else:
					RegisterServer(queue,candidate,port, protocol, options)
			except:
				RegisterServer(queue,candidate,port, protocol, options)

def TestAName(tid,queue,verbose, options):
	"""Test a specific servername, hand IP addresses over to the IP address scanner"""
	for hostname, port, protocol in queue:
		if not hostname.strip():
			continue
	
		hostname = hostname.strip()
		hostname = hostname.strip(".")
		while hostname.find("..")>=0:
			hostname = hostname.replace("..", ".")
			
		if not port:
			port = 443
		else:
			port = int(port)

		if (not hostname or 
				any([x in hostname for x in " \t%/&#\"'\\{[]}()*,;<>$"]) or 
				any([ord(x)>=128 or ord(x)<=32  for x in hostname])):
			if "/" in hostname and not any([y not in "0123456789./" for y in hostname]):
				#IP range
				TestIPRange(queue, hostname, port, verbose, options)
				if not queue.IsActive():
					queue.cancel()
					return

			queue.log_performance()
			return
		
		if verbose:
			print tid,"testing domain",hostname, ":", port

		if TestServer(hostname, port, protocol, verbose):
			RegisterServer(queue,hostname,port, protocol, options)

		if any([y not in "0123456789./" for y in hostname]):
			#Non IP address
			
			if protocol == ProbeData.Server.PROTOCOL_HTTPS:
				for label in label_prefixes:
					name = label+"."+hostname
					if not queue.IsActive():
						queue.cancel()
						return
						
					if TestServer(name, port, protocol, verbose):
						RegisterServer(queue,name,port, protocol, options)
		
				for labelbase in iterated_prefixes:
					for i in range(10):
						if not queue.IsActive():
							queue.cancel()
							return
						label = "%s%d" %(labelbase, i)
						name = label+"."+hostname
						if TestServer(name, port, protocol, verbose):
							RegisterServer(queue,name,port, protocol, options)
						else:
							break
			else:
				for label in protocol_prefixes.get(protocol,[]):
					name = label+"."+hostname
					if not queue.IsActive():
						queue.cancel()
						return
						
					if TestServer(name, port, protocol, verbose):
						RegisterServer(queue,name,port, protocol, options)

		queue.log_performance()


def getQueue(run, options):
	queue = Scanner.ScannerQueue.Queue(run, options.max_tests,options.register_performance)

	return queue

options_config = OptionParser()

options_config.add_option("--run-id", action="store", type="int", dest="run_id", default=0)
options_config.add_option("--source", action="store", type="string", dest="source_name", default="TLSProber")
options_config.add_option("--description", action="store", type="string", dest="description",default="TLSProber")
options_config.add_option("-n", action="store", type="int", dest="index", default=1)
options_config.add_option("--threads", action="store", type="int", dest="threads", default=3)
options_config.add_option("--verbose", action="store_true", dest="verbose")
options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--performance", action="store_true", dest="register_performance")
options_config.add_option("--max", action="store", type="int", dest="max_tests",default=0)
options_config.add_option("--test", action="store_true", dest="just_test")

(options, args) = options_config.parse_args()


if options.just_test:
	class Queue:
		"""Local Queue implementation, that does not depend on the database"""
		def __init__(self,args):
			self.args = args

		def IsActive(self):
			return True
		
		def log_performance(self):
			pass
		
		def __iter__(self):
			def make_entry(x):
				ret = x.split(":") 
				if len(ret) <1:
					raise Exception()
				elif  len(ret) <2:
					ret += [443, ProbeData.Server.PROTOCOL_HTTPS]
				elif len(ret) < 3:
					ret[1] = int(ret[1])
					ret.append(ProbeData.Server.PROTOCOL_PORT.get(ret[1], ProbeData.Server.PROTOCOL_HTTPS))
				else:
					ret[1] = int(ret[1])
				return tuple(ret)
			return iter([make_entry(x) for x in args])
	queue = Queue(args)
	options.threads = 1
else:
	run = Scanner.ScannerRun.objects.filter(enabled=True).latest("entered_date")
	queue = getQueue(run, options)

threads = []
for i in range(options.threads):
	new_thread = threading.Thread(target=TestAName, args=(i,queue,options.verbose, options))
	new_thread.start()
	threads.append(new_thread)

for t in threads:
	t.join()
		
