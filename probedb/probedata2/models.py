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


from django.db import models
#from django.db.models.fields.related import ForeignKey
import base64

from django.db import transaction
import time
from django.db import DatabaseError
from django.db import IntegrityError

# Create your models here.

from probedb.probedata2.proberun import *
from probedb.probedata2.ciphers import *
import probedb.resultdb2.ciphers as ResultCiphers
import probedb.resultdb2.condition as Results
import probedb.manutrans as manutrans

"""
Database of the detailed results found during the probing

There is one entry per protocol:IP:port server encountered per job.
Common results are aggregated into an underlying single entry 
referenced by the entry
"""


class ServerDomain(models.Model):
	"""Entry for a domain name, references its own parent domain, if any"""

	domain_parent = models.ForeignKey("self", null=True)
	domain_name = models.CharField(max_length = 300)
	full_domain_name = models.CharField(max_length = 300, db_index=True)
	level = models.PositiveIntegerField() # levels of domains, TLD is 1;    4.3.2.1 

	class Meta:
		unique_together=("domain_parent", "domain_name")

	def __unicode__(self):
		return unicode(self.domain_name) + " "+ unicode(self.domain_parent)+ " ,level " + unicode(self.level)  

	def GetName(self):
		return self.domain_name

class Server(models.Model):
	"""Protocol:Hostname:port of a server""" 

	PROTOCOL_HTTPS = "HTTPS"   # HTTPS
	PROTOCOL_IMAP = "IMAP"	# IMAP STARTTLS
	PROTOCOL_IMAP_S = "IMAPS" # IMAP direct TLS
	PROTOCOL_SMTP = "SMTP"	# SMTP STARTTLS
	PROTOCOL_SMTP_S = "SMTPS"	# SMTP direct TLS
	PROTOCOL_POP = "POP"	# POP STARTTLS
	PROTOCOL_POP_S = "POPS"	# POP direct TLS
	
	PROTOCOL_LIST = (
			(PROTOCOL_HTTPS, "HTTPS"),
			(PROTOCOL_IMAP, "IMAP"),
			(PROTOCOL_IMAP_S, "IMAPS"),
			(PROTOCOL_SMTP, "SMTP"),
			(PROTOCOL_SMTP_S, "SMTPS"),
			(PROTOCOL_POP, "POP"),
			(PROTOCOL_POP_S, "POPS"),
					)
	PROTOCOL_PORT = {
			443:PROTOCOL_HTTPS,
			143:PROTOCOL_IMAP,
			993:PROTOCOL_IMAP_S,
			25:PROTOCOL_SMTP,
			587:PROTOCOL_SMTP,
			586:PROTOCOL_SMTP_S,
			110:PROTOCOL_POP,
			995:PROTOCOL_POP_S, 
		}
	
	PROTOCOL_PORT_MAP = {}
	for __p1, __p2 in PROTOCOL_PORT.iteritems():
		PROTOCOL_PORT_MAP.setdefault(__p2, []).append(__p1)
	
	PROTOCOL_START_TLS = (PROTOCOL_IMAP, PROTOCOL_SMTP, PROTOCOL_POP)
	PROTOCOL_DIRECT_TLS = (PROTOCOL_HTTPS, PROTOCOL_IMAP_S, PROTOCOL_SMTP_S, PROTOCOL_POP_S)

	
	full_servername = models.CharField(max_length = 330, db_index=True,unique=True)
	servername = models.CharField(max_length = 300, db_index=True)
	port = models.PositiveIntegerField()
	protocol = models.CharField(max_length = 10, choices= PROTOCOL_LIST, db_index=True, null=True)
	alexa_rating = models.PositiveIntegerField()
	enabled = models.BooleanField()
	
	domain_parents = models.ManyToManyField(ServerDomain, null=True)
	
	domain_root = None
	
	def __unicode__(self):
		return self.servername + ":" + str(self.port)+ ":" + str(self.protocol if self.protocol else Server.PROTOCOL_HTTPS)

	def GetName(self):
		return self.full_servername

	def GetProtocol(self):
		return self.protocol if str(self.protocol) else Server.PROTOCOL_HTTPS

	def Construct(self):
		"""
		Construct the parent domain information based on the servername this 
		entry was intiated with
		"""
		
		domain_list = self.servername.split(".")
		if len(domain_list) < 2:
			return
		
		if not Server.domain_root:
			while True:
				try:
					Server.domain_root, created = ServerDomain.objects.get_or_create(domain_parent=None, domain_name="", full_domain_name="", level=0)
				except:
					time.sleep(.1)
					continue;
				break;
				
		
		level = 1
		domain_records = []
		domain_parent=self.domain_root
		domain_suffix = None
		for domain in reversed(domain_list[1:]): 
			full_name = domain+("."+domain_suffix if domain_suffix else "")
			while True:
				try:
					sid = transaction.savepoint()
					domain_item, created = ServerDomain.objects.get_or_create( 
										domain_parent=domain_parent,
										domain_name = domain,
										defaults = {
												"full_domain_name":full_name,
												"level":level
											}
										)
					transaction.savepoint_commit(sid)
					#print str(error)
					raise
				except DatabaseError:
					transaction.savepoint_rollback(sid)
					time.sleep(0.1)
					continue
				except IntegrityError:
					transaction.savepoint_rollback(sid)
					time.sleep(0.1)
					continue
				except Exception, error:
					time.sleep(0.1)
					continue
				
				break

			domain_suffix = full_name
			domain_records.append(domain_item)
			domain_parent  = domain_item;
			level += 1
		
		self.domain_parents.add(*domain_records)

class IPAddressDomain(models.Model):
	"""
	IP address "domains", chains to parent IP address domain, if any
	The part of the IP address on the left of the dot is the parent domain
	NOTE: Only tested for IPv4 addresses
	"""
	
	ip_parent = models.ForeignKey("self", null=True)
	ip_domain = models.PositiveIntegerField()
	full_ip_mask = models.IPAddressField(db_index=True)
	level = models.PositiveIntegerField() # levels of quaddot: 1.2.3.4

	class Meta:
		unique_together=("ip_parent", "ip_domain")

	def __unicode__(self):
		return unicode(self.ip_domain) 

	def GetName(self):
		return self.full_ip_mask
	
class IP_Address(models.Model):
	"""
	IP address, with link to IP address domain
	NOTE: Only tested for IPv4 addresses
	"""

	ip_address = models.IPAddressField(unique=True, db_index=True)
	ip_parents = models.ManyToManyField(IPAddressDomain, null=True)
	
	ip_root = None
	
	def Construct(self):
		"""
		Construct the IP address domain chain
		"""
		ipaddress = str(self.ip_address)
		
		if ':' in ipaddress:
			return  #TODO: ipv6
		
		if not IP_Address.ip_root:
			while True:
				try:
					sid = transaction.savepoint()
					IP_Address.ip_root = IPAddressDomain.objects.extra(where=['"probedata2_ipaddressdomain"."full_ip_mask" = INET(E\'0.0.0.0\')'])[0]
					transaction.savepoint_commit(sid)
				except IndexError:
					transaction.savepoint_rollback(sid)
					try:
						sid = transaction.savepoint()
						IP_Address.ip_root = IPAddressDomain.objects.create(full_ip_mask = "0.0.0.0", ip_parent = None,level=0, ip_domain = 0);
						transaction.savepoint_commit(sid)
					except DatabaseError:
						transaction.savepoint_rollback(sid)
						time.sleep(0.1)
						continue
					except IntegrityError:
						transaction.savepoint_rollback(sid)
						time.sleep(0.1)
						continue
					except:
						raise
				except:
					raise
				break;

		domain_list = ipaddress.split(".")
		if len(domain_list) != 4:
			return;
		
		domain_list = domain_list[:-1] 

		level = 1
		domain_records = []
		domain_parent=IP_Address.ip_root
		domain_prefix = []
		for domain in domain_list: 
			domain_prefix.append(domain)
			full_name = ".".join((domain_prefix + ["0","0","0", "0"])[0:4])
			while True:
				try:
					sid = transaction.savepoint()
					domain_item, created = IPAddressDomain.objects.get_or_create( 
										ip_parent=domain_parent,
										ip_domain = int(domain),
										defaults = {
												"full_ip_mask":full_name,
												"level":level
											}
										)
					transaction.savepoint_commit(sid)
				except AssertionError,error:
					#print str(error)
					raise
				except DatabaseError:
					transaction.savepoint_rollback(sid)
					time.sleep(0.1)
					continue
				except IntegrityError:
					transaction.savepoint_rollback(sid)
					time.sleep(0.1)
					continue
				except Exception, error:
					#print str(error)
					time.sleep(0.1)
					continue
				
				break

			self.ip_parents.add(domain_item)
			domain_records.append(domain_item)
			domain_parent  = domain_item;
			level += 1
			
	def __unicode__(self):
		return self.ip_address

	def GetName(self):
		return str(self.ip_address)

	
class ProbeQueue(models.Model):
	"""
	List of server entries for a particular batch job
	State of the entry can be Idle, Started, or Finished.
	"""
	part_of_run = models.ForeignKey(ProbeRun, db_index=True)
	server = models.ForeignKey(Server)
	
	PROBEQ_IDLE = "I"
	PROBEQ_STARTED = "S"
	PROBEQ_FINISHED = "F"
	PROBEQ_VALUES = (
		(PROBEQ_IDLE,"Not started"),
		(PROBEQ_STARTED,"Started"),
		(PROBEQ_FINISHED,"Finished"),
					)
	state = models.CharField(max_length=1, null=True, choices=PROBEQ_VALUES)

	def __unicode__(self):
		return str(self.part_of_run)+" "+str(self.state)+ " "+ str(self.server)
	
	class Meta:
		unique_together=[("part_of_run", "server")]

class PreparedQueueList(models.Model):
	"""
	Parent entry for a prepared batch job as a set of PreparedQueueItems
	
	NOTE: Activation is performed using direct SQL, for performance reasons.
	"""
	list_name = models.CharField(max_length=20, db_index=True, unique=True)
	list_description = models.CharField(max_length=200, null=True)
	
	@transaction.commit_on_success
	def InitQueue(self, run):
		from django.db import connection 
		
		cursor = connection.cursor()
		
		cursor.execute("""INSERT INTO probedata2_probequeue (part_of_run_id, server_id, state) 
				SELECT %s AS part_of_run_id, server_id, E'I' AS state FROM probedata2_preparedqueueitem
				WHERE part_of_queue_id = %s""", [str(run.id), str(self.id)]
			)
		transaction.set_dirty()

	def __unicode__(self):
		return self.list_name+": "+self.list_description

		
class PreparedQueueItem(models.Model):
	"""
	Entry for an individual server in a prepared list of servers to probe 
	"""

	part_of_queue = models.ForeignKey(PreparedQueueList, db_index=True)
	server = models.ForeignKey(Server)

	class Meta:
		unique_together=[("part_of_queue", "server")]

class ProbeCommonErrorString(models.Model):
	"""
	Table with unique error strings encountered during probing
	
	The class uses a cache to speed lookups
	"""
	error_string = models.TextField(unique=True)

	__cache = {}
	
	@classmethod
	def FetchOrCreate(cls,s):
		"""Find the error string, or create it; check cache first"""
		if s in cls.__cache:
			return cls.__cache[s];
		
		while True:
			created = False
			try:
				sid = transaction.savepoint()
				e, created = cls.objects.get_or_create(error_string = s)
				transaction.savepoint_commit(sid)
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;

		if not created:
			cls.__cache[s]=e
		return e;

class ProbeCommonResultEntry(models.Model):
	"""
	A common entry registering results for a test sending a specific
	combination of a TLS version, extensions and using incorrect version 
	in the RSA client key exchange.
	
	The entry is keyed on the fields, combined into a string
	
	A cache is used to speed up retrieval.  
	"""
	
	PROBE_UNTESTED = 'U'
	PROBE_PASSED ='P'
	PROBE_FAILED = 'F'
	PROBE_NON_COMPLIANT = 'N'
	PROBERESULTVALUES  = (
		(PROBE_UNTESTED, "Untested"),
		(PROBE_PASSED, "Passed"),
		(PROBE_FAILED, "Failed"),
		(PROBE_NON_COMPLIANT, "Non-compliant"),
		)

	key = models.CharField(max_length=100, unique = True) 
	
	version_major = models.PositiveIntegerField()
	version_minor = models.PositiveIntegerField()
	extensions = models.BooleanField()
	badversion = models.BooleanField()

	result = models.CharField(max_length=1, choices=PROBERESULTVALUES)
	negotiated_version_major = models.PositiveIntegerField()
	negotiated_version_minor = models.PositiveIntegerField()

	# this is used when bad_version == True and extensions == False and is a copy of version with no ext and no bad to simplify queries 
	result_non_bad = models.CharField(max_length=1, choices=PROBERESULTVALUES)

	error_string = models.ForeignKey(ProbeCommonErrorString, null=True);

	result_summary_group =  models.ForeignKey(Results.ResultCommonConditionSet)
	
	__cache = {}

	@classmethod
	def _CalculateKey(cls, **params):
		"""
		use the config&results in the params dictionary to create a key for 
		that combination
		""" 
		return "{0:d}{1:d}{2:s}{3:s}{4:d}{5:d}_{6:s}{7:s}_{8:d}_{9:d}".format(
							params["version_major"],
							params["version_minor"],
							("T" if params["extensions"] else "F"),
							("T" if params["badversion"] else "F"),
							params["negotiated_version_major"],
							params["negotiated_version_minor"],
							params["result"],
							params["result_non_bad"],
							(params["error_string"].id if params["error_string"] else 0),
							params["result_summary_group"].id,
										)

	@classmethod	
	def FetchOrCreateItem(cls,**params):
		"""
		Either find an existing entry matching the config & results in the
		params dictionary, or create a new entry.
		"""
		key = cls._CalculateKey(**params)
		
		if key in cls.__cache:
			return cls.__cache[key];
		
		params1 = dict(params)
		params1.pop("servername",None)
		params1.pop("part_of_run", None)
		
		while True:
			created =False
			try:
				sid = transaction.savepoint()
				item,created = ProbeCommonResultEntry.objects.get_or_create(key=key, defaults=params1)
				transaction.savepoint_commit(sid)
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;
		
		if not created:
			cls.__cache[key] = item
		return item

class ProbeResultEntry():
	"""Liast of enums for results"""
	PROBE_UNTESTED = 'U'
	PROBE_PASSED ='P'
	PROBE_FAILED = 'F'
	PROBE_NON_COMPLIANT = 'N'
	PROBERESULTVALUES  = (
		(PROBE_UNTESTED, "Untested"),
		(PROBE_PASSED, "Passed"),
		(PROBE_FAILED, "Failed"),
		(PROBE_NON_COMPLIANT, "Non-compliant"),
		)

class AgentShortName(models.Model):
	"""Server shortname (vendor name) entry""" 
	
	agent_shortname= models.CharField(max_length = 300,unique=True, db_index=True)
	
	NotAvailable = None # global reference to the "N/A" entry

	def __unicode__(self):
		return self.agent_shortname

	def GetName(self):
		return self.agent_shortname

class PrimaryServerAgent(models.Model):
	"""
	Full name of a primary server agent string (first name in the string), 
	and a link to the short name, and decoded version fields
	"""

	agent_name = models.CharField(max_length = 300, unique = True, db_index=True)
	agent_shortname= models.ForeignKey(AgentShortName,null=True)
	major_version = models.CharField(max_length = 300)
	minor_version = models.CharField(max_length = 300)
	patch_version = models.CharField(max_length = 300)
	
	NotAvailable = None # global reference to the "N/A" entry

	def __unicode__(self):
		return self.agent_name

	def GetName(self):
		return self.agent_name

class SecondaryServerAgent(models.Model):
	"""
	Full name of a secondary server agent string (the entries after the first field),
	 and a link to the short name, and decoded version fields
	"""

	agent_name = models.CharField(max_length = 300, unique = True, db_index=True)
	agent_shortname= models.ForeignKey(AgentShortName,null=True)
	major_version = models.CharField(max_length = 300)
	minor_version = models.CharField(max_length = 300)
	patch_version = models.CharField(max_length = 300)
	
	NotAvailable = None  # global reference to the "N/A" entry

	def __unicode__(self):
		return self.agent_name

	def GetName(self):
		return self.agent_name
	

class Certificate(models.Model):
	"""
	An entry with a Base64 encoded certificate, keyed to a SHA-256 fingerprint 
	of the binary certificate.
	
	Registers date when the certificate was recorded, the self signed status, and 
	the Base64 encoded issuer and subject name fields
	
	TODO: Add Authority and Subject Key information
	"""
	sha256_fingerprint = models.CharField(max_length = 64, unique = True, db_index=True)
	date = models.DateTimeField(auto_now_add=True)
	certificate_b64 = models.TextField() # Base64 encoded certificate
	self_signed = models.BooleanField()
	issuer_b64 = models.TextField(null=True, db_index=True) # Base64 encoded certificate issuer name
	subject_b64 = models.TextField(null=True, db_index=True) # Base64 encoded certificate subject name

	def SetCertificate(self,cert_binary):
		"""Set a binary certificate by converting it to Base64, splitting the lines first"""
		b64_cert =base64.b64encode(cert_binary)
		self.certificate_b64 = "\n".join([b64_cert[i:min(i+64, len(b64_cert))] for i in range(0,len(b64_cert),64)]) 
		
		
	def GetCertificate(self):
		"""Decode the Base64 encoded certificate to binary form and return it"""
		return base64.b64decode(self.certificate_b64)
	
	def __unicode__(self):
		return self.sha256_fingerprint

class CertificateSequence(models.Model):
	"""
	Certificate sequence item, keyed uniquely to the certificate and
	the sequence number	
	"""
	 
	certificate = models.ForeignKey(Certificate)
	sequence_number = models.IntegerField()
	
	class Meta:
		unique_together=[("certificate", "sequence_number")]		

class CommonServerGroup(models.Model):
	"""
	entry with a unique combination of servers that have been registered at
	a given IP address.
	
	Keyed to a SHA-256 hash of the ID numbers of the server entries.
	"""

	key = models.CharField(max_length = 100, unique=True)
	server_aliases = models.ManyToManyField(Server, null=True)

	@classmethod
	def _CalculateKey(cls, server_aliases):
		"""Calculate a key for the list of servers"""
		import hashlib

		return "{0:s}".format(
							(hashlib.sha256("-".join(["{0:x}".format(x) for x in sorted(list(set([y.id for y in server_aliases])))])).hexdigest() if server_aliases else ""),
							)

	@classmethod	
	def FetchOrCreateItem(cls,server_aliases):
		"""
		For a list of server, find an existing entry for it, or create a new entry 
		"""

		key = cls._CalculateKey(server_aliases = server_aliases)

		while True:
			try:
				sid = transaction.savepoint()
				item,created = CommonServerGroup.objects.get_or_create(key=key)
				if created and server_aliases:
					if len(server_aliases) < 200:
						item.server_aliases.add(*server_aliases)
					else:
						from django.db import connection 
						cursor = connection.cursor()
		
						server_ids = list(set([x.id for x in server_aliases]))
						n = len(server_ids)
						for i in range(0,n,500):
							print i,n
							values = ", ".join(["(%d, %d)"%(item.id, x) for x in server_ids[i:min(n,i+500)]])
							cursor.execute("INSERT INTO probedata2_commonservergroup_server_aliases (commonservergroup_id, server_id) VALUES "+values)
							
				transaction.savepoint_commit(sid)
			except DatabaseError:
				raise
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				raise
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;

		return item

class CommonServerIPProbed(models.Model):
	"""
	Entry for a specific combination of an IP address, protocol, port 
	and list of servernames
	
	Keyed two ways: The servername list ID or the key of the servername list,
	both in combination with the IP address id, port and protocol name.
	(This means that the entry can be looked up without first locating the server
	alias group, reducing time spent searching the database)  
	"""
	key = models.CharField(max_length = 100, unique=True)
	key_hash = models.CharField(max_length = 100, unique=True)
	ip_address = models.ForeignKey(IP_Address, null=True)
	port = models.PositiveIntegerField(null=True)
	protocol = models.CharField(max_length=10, choices=Server.PROTOCOL_LIST, null=True)
	server_group = models.ForeignKey(CommonServerGroup, null=True)

	@classmethod
	def _CalculateKey(cls, **params):
		"""Calculate the key based on the server alias group ID"""
		return "{0:x}:{1:x}:{2:s}:{3:x}".format(
							params["ip_address"].id,
							params["port"],
							params["protocol"],
							params["server_group"].id
										)

	@classmethod
	def _CalculateKeyHash(cls, **params):
		"""Calculate the key based on the server alias group key"""
		return "{0:x}:{1:x}:{2:s}_{3:s}".format(
							params["ip_address"].id,
							params["port"],
							params["protocol"],
							params["server_group"].key
										)

	@classmethod
	def _CalculateKeyAliases(cls, **params):
		"""Calculate the key based on the calculated server alias group key"""
		return "{0:x}:{1:x}:{2:s}_{3:s}".format(
							params["ip_address"].id,
							params["port"],
							params["protocol"],
							CommonServerGroup._CalculateKey(params["server_aliases"])
										)

	@classmethod	
	def FetchOrCreateItem(cls,probed):
		"""
		Locate the entry for this combination of IP address, port, protocol,
		and server names, based on the key_hash field
		"""

		server_aliases = [probed.server] + list(probed.server_aliases.all())
		assert(len(server_aliases) > 0) 

		params = dict(
					ip_address = probed.ip_address,
					port = (probed.port if probed.port else probed.server.port),
					protocol = (probed.protocol if probed.protocol else probed.server.protocol),
					)

		key_hash = cls._CalculateKeyAliases(server_aliases = server_aliases, **params)
		
		item = None
		try:
			sid = transaction.savepoint()
			item = CommonServerIPProbed.objects.get(key_hash = key_hash)
			transaction.savepoint_commit(sid)
			return item
		except:
			transaction.savepoint_rollback(sid)

		params["server_group"]=CommonServerGroup.FetchOrCreateItem(server_aliases)

		params["key_hash"]=cls._CalculateKeyHash(**params)
		assert(params["key_hash"] == key_hash)

		key = cls._CalculateKey(**params)
		
		while True:
			try:
				sid = transaction.savepoint()
				item,created = CommonServerIPProbed.objects.get_or_create(key=key, defaults=params)
				transaction.savepoint_commit(sid)
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;

		return item


class ServerIPProbed(models.Model):
	"""
	For the given run we have already probed the specific IP address, for a specified name, 
	port and protocol, and have registered other names as aliases
	"""
	
	part_of_run = models.ForeignKey(ProbeRun)
	server = models.ForeignKey(Server)
	server_aliases = models.ManyToManyField(Server, null=True, related_name="server_aliases_ip")
	ip_address = models.ForeignKey(IP_Address, null=True)
	port = models.PositiveIntegerField(null=True)
	protocol = models.CharField(max_length=10, choices=Server.PROTOCOL_LIST, null=True)
	

	class Meta:
		unique_together=[("part_of_run", "ip_address", "port", "protocol")]		

	def __unicode__(self):
		return self.server.servername+":" +str(self.server.port) + " run:" + str(self.part_of_run)
	
	@classmethod	
	def GetIPLock(cls,run, ip_address, server_item):
		"""
		Obtain a lock for this particular IP address in this run
		If an entry already exists, report that back, along with the entry  
		"""

		while True:
			try:
				ip = IP_Address.objects.extra(where=['"probedata2_ip_address"."ip_address" = INET(E\''+ip_address+'\')'])[0]
			except (IP_Address.DoesNotExist, IndexError):
				try:
					sid = transaction.savepoint()
					ip = IP_Address.objects.create(ip_address=ip_address);
					ip.Construct()
					sid = transaction.savepoint_commit(sid)
				except:
					sid = transaction.savepoint_rollback(sid)
					continue
			break;
		while True:
			try:
				sid = transaction.savepoint()
				(probedalready,created) = cls.objects.get_or_create(
													part_of_run=run, 
													ip_address=ip,
													port = server_item.port,
													protocol =server_item.protocol,
													defaults={"server":server_item})
				sid = transaction.savepoint_commit(sid)
			except:
				sid = transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue;
			break;
		return (probedalready,created)

class CommonSpecificExtensionIntolerance(models.Model):
	"""
	An entry for an identified TLS Extension intolerance that is keyed to
	specific entries, and not all of the supported extensions
	
	The class have a cache of known entries 
	"""
	intolerant_for_extension = models.CharField(max_length = 1024, unique=True)

	def __unicode__(self):
		return str(self.intolerant_for_extension)

	def GetName(self):
		return self.intolerant_for_extension

	__cache = {}
	
	@classmethod
	def FetchOrCreate(cls,s):
		"""
		Find an entry for this set of intolerances, check the cache first.
		Otherwise check the database, if necessary creating a new item.
		"""
		if s in cls.__cache:
			return cls.__cache[s];
		
		while True:
			created =False
			try:
				sid = transaction.savepoint()
				e, created = cls.objects.get_or_create(intolerant_for_extension = s)
				transaction.savepoint_commit(sid)
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;

		if not created:
			cls.__cache[s]=e
		return e;

class ProbeCommonResult(models.Model):
	"""
	Collection of a specific set of results that have been found from 
	a completed proberun for a server.
	
	Keyed to values and IDs of the referenced result fields.
	Known entries are cached
	
	References a more basic profile and a fundamental profile, too  
	"""

	key = models.CharField(max_length=300, unique = True) 

	# Set of result flags that define the test resulsts of this server
	result_summary_group =  models.ForeignKey(Results.ResultCommonConditionSet, null=True)

	cipher_suites = models.ForeignKey(ResultCiphers.CipherSuiteGroup, null=True)
	used_dhe_key_size = models.IntegerField()
	
	intolerant_for_extension = models.ManyToManyField(CommonSpecificExtensionIntolerance, null=True)
	
	common_results = models.ManyToManyField(ProbeCommonResultEntry, null=True)

	#shared results, not including the configuration controlled conditions
	basic_result = models.ForeignKey("self", null=True)
	fundamental_result = models.ForeignKey("self", null=True, related_name="fundamental_commonresult")

	__cache = {}
	
	@classmethod
	def _CalculateKey(cls, **params):
		"""Calculate the entry's key, based on the dictionary"""
		return "{0:x}_{1:x}_{2:x}_{3:s}_{4:s}".format(
				(params["cipher_suites"].id if params["cipher_suites"] else 0),
				params["used_dhe_key_size"],
				params["result_summary_group"].id,
				"-".join(["{0:x}".format(x) for x in sorted([y.id for y in params["intolerant_for_extension"]])]),
				"-".join(["{0:x}".format(x) for x in sorted([y.id for y in params["common_results"]])]),
			)


	@staticmethod
	@manutrans.commit_manually_if_unmanaged
	def FetchOrCreateItem(**params):
		"""Find an existing entry, or create it"""
		key = ProbeCommonResult._CalculateKey(**params)
		
		if key in ProbeCommonResult.__cache:
			return ProbeCommonResult.__cache[key];

		param1 = {"cipher_suites":params["cipher_suites"],
				"used_dhe_key_size":params["used_dhe_key_size"],
				"result_summary_group":params["result_summary_group"],
				}
		intol = params["intolerant_for_extension"]
		res = params["common_results"]
		
		while True:
			created = False
			try:
				sid = transaction.savepoint()
				item,created= ProbeCommonResult.objects.get_or_create(key=key, defaults=param1)
				if created:
					item.intolerant_for_extension.add(*intol)
					item.common_results.add(*res)
					c = params["result_summary_group"]
					if not c.referred_by_main_result:
						c.referred_by_main_result = True
						c.save()
					basic = item
					fundamental = item
					own_conds =c.GetConditions()
					basic_conds = own_conds - set(Results.ResultCondition.RESULT_VALUE_CONFIGURATIONS)
					fundamental_conds = basic_conds - set(Results.ResultCondition.RESULT_VALUE_CONFIGURATIONS_CIPHER)
					if own_conds != basic_conds:
						param2 = dict(param1)
						param2["intolerant_for_extension"] = intol
						param2["common_results"] = res
						param2["result_summary_group"] = Results.ResultCommonConditionSet.FindSet(basic_conds, create=True)
						basic = ProbeCommonResult.FetchOrCreateItem(**param2)
						fundamental = basic.fundamental_result
					elif param1["cipher_suites"] or param1["used_dhe_key_size"]!=0 or fundamental_conds != basic_conds:
						param2 = {
								"cipher_suites": None,
								"used_dhe_key_size": 0,
								"common_results": res,
								"result_summary_group": (param1["result_summary_group"] if fundamental_conds == basic_conds else Results.ResultCommonConditionSet.FindSet(fundamental_conds, create=True)),
								"intolerant_for_extension": intol,
								}
						fundamental = ProbeCommonResult.FetchOrCreateItem(**param2)

					item.basic_result = basic
					item.fundamental_result = fundamental
					item.save() 						
				transaction.savepoint_commit(sid)
				
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except:
				transaction.savepoint_rollback(sid)
				transaction.rollback_unless_managed()
				raise
			break;
		if not created:
			ProbeCommonResult.__cache[key] = item;
		transaction.commit_unless_managed()
		return item



class ProbeResult(models.Model):
	"""
	The result for a given server (with server/IP address aliases) in
	a given run.
	
	Links to certificates, common result profiles, and other results  
	"""
	
	part_of_run = models.ForeignKey(ProbeRun, db_index=True)
	servername = models.ForeignKey(Server)
	common_server_aliases = models.ManyToManyField(CommonServerIPProbed)
	ip_addresses = models.ManyToManyField(IP_Address, null=True)
	date = models.DateTimeField(auto_now_add=True)
	
	common_result = models.ForeignKey(ProbeCommonResult, null=True)

	server_cert = models.ForeignKey(Certificate, null=True, related_name="server_cert")
	certificates = models.ManyToManyField(Certificate, null=True)
	certificate_sequence = models.ManyToManyField(CertificateSequence, null=True)
	cert_status_response_b64= models.TextField(null=True)
	
	serveragent_string = models.CharField(max_length = 300, null=True)
	
	primary_agent = models.ForeignKey(PrimaryServerAgent, null=True)
	secondary_agents = models.ManyToManyField(SecondaryServerAgent, null=True)
	
	# Set of result flags that define the test resulsts of this server  
	result_summary_group =  models.ForeignKey(Results.ResultConditionSet, null=True)
	
	def __unicode__(self):
		return self.servername.servername+":" +str(self.servername.port) + " Date:" + str(self.date)

	def GetConditions(self):
		"""Return a set of the result flags for this probe results"""
		return self.result_summary_group.GetConditions()
