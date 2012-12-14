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
from django.db import IntegrityError
from django.db import transaction
from django.db.models.signals import post_init
from django.db import transaction
from django.db import connection
from django.db.models import Q 
import time
from probedb.resultdb2.models import *
import probedb.probedata2.models as ProbeData
from django.db import DatabaseError
from django.db import IntegrityError
from django.views.decorators.http import condition
import datetime, sys


# Create your models here.


class ResultSummaryList(models.Model):
	"""Top result manager for a run
	Links to all results, condition (flag) sets, and other data
	
	Also perform searches on the results 
	"""
	part_of_run = models.ForeignKey(ProbeData.ProbeRun, unique=True, db_index = True)
	
	summaries = models.ManyToManyField(ResultEntry, null=True)
	
	conditions = models.ManyToManyField(ResultCondition,null=True)
	condition_groups = models.ManyToManyField(ResultConditionSet,null=True)
	
	IPDomainTopEntry0 =  models.ForeignKey(ProbeData.IPAddressDomain, null=True, related_name="IPDomainTopEntry0" ) #Ip top
	IPDomainEntries0 =  models.ManyToManyField(ProbeData.IPAddressDomain, null=True) #Ip top
	DomainTopEntry0 =  models.ForeignKey(ProbeData.ServerDomain, null=True, related_name="DomainTopEntry0") #TLDs
	DomainEntries0 =  models.ManyToManyField(ProbeData.ServerDomain, null=True) #TLDs
	CipherSuiteEntries = models.ManyToManyField(ResultCipherSuite, null=True)
	CipherSuiteGroupEntries = models.ManyToManyField(ResultCipherSuiteGroupEntry, null=True)

	PrimaryShortServerAgentSummary = models.ManyToManyField(ResultPrimaryServerAgentFamily, null=True)
	SecondaryShortServerAgentSummary = models.ManyToManyField(ResultSecondaryServerAgentFamily, null=True)
	PrimaryServerAgentSummary = models.ManyToManyField(ResultPrimaryServerAgent, null=True)
	SecondaryServerAgentSummary = models.ManyToManyField(ResultSecondaryServerAgent, null=True)

	ip_address_probed = models.ManyToManyField(ProbeData.ServerIPProbed, null=True)
	
	dhe_keysizes = models.ManyToManyField(ResultDHEKeySize, null=True)
	
	QUERY_CONDITION = "condition"

	QUERY_DOMAIN ="domains"
	QUERY_IP="ipdomain"
	
	QUERY_PRIMARYAGENT = "primaryagent"
	QUERY_SHORTPRIMARYAGENT = "shortprimaryagent"
	QUERY_SECONDARYAGENT = "secondaryagent"
	QUERY_SHORTSECONDARYAGENT = "shortsecondaryagent"
		
	QUERY_CIPHER = "cipher"
	QUERY_CIPHERGROUP = "ciphergroup"
	
	QUERY_SPECINTOL = "specintol"
	
	QUERY_DHEKEYSIZE = "dhekeysize"
	
	QUERY_ALEXA_RESTRICT = "alexa"
	
	QUERY_RESTRICT_RUN = "restrict_run"
	
	QUERY_PROTOCOL_RESTRICT = "protocol"
	
	QUERY_CIPHER_EXCLUDE = "cipher_exclude"

	QUERY_AUTO = "auto"
	
	QUERY_TYPES = (
				QUERY_CONDITION,
				QUERY_DOMAIN,
				QUERY_IP,
				QUERY_PRIMARYAGENT,
				QUERY_SHORTPRIMARYAGENT,
				QUERY_SECONDARYAGENT,
				QUERY_SHORTSECONDARYAGENT,
				QUERY_CIPHER,
				QUERY_CIPHERGROUP,
				QUERY_SPECINTOL,
				QUERY_DHEKEYSIZE,
				QUERY_RESTRICT_RUN,
				QUERY_PROTOCOL_RESTRICT,
				QUERY_CIPHER_EXCLUDE,
				)
	
	RESULT_ID = "id"
	RESULT_CONDITION = "condition"
	
	RESULT_DOMAIN ="domains"
	RESULT_IP="ipdomain"
	
	RESULT_PRIMARYAGENT = "primaryagent"
	RESULT_SHORTPRIMARYAGENT = "shortprimaryagent"
	RESULT_SECONDARYAGENT = "secondaryagent"
	RESULT_SHORTSECONDARYAGENT = "shortsecondaryagent"
	
	RESULT_CIPHER = "cipher"
	RESULT_CIPHERGROUP = "ciphergroup"
	
	RESULT_PROTOCOLS = "protocols"
	
	RESULT_HOSTS = "hosts"
	RESULT_HOSTS_ALEXA = "hosts_alexa"
	RESULT_URLS_TEXT = "urls_text"
	RESULT_HOST_RUNLIST = "run_urls_cvs"
	
	RESULT_HOST_PROFILES = "hosts_profiles"
	RESULT_HOST_BASEPROFILES = "hosts_baseprofiles"
	RESULT_HOST_FUNDPROFILES = "hosts_fundprofiles"
	
	RESULT_TYPES = (
				RESULT_CONDITION,
				RESULT_DOMAIN,
				RESULT_IP,
				RESULT_PRIMARYAGENT,
				RESULT_SHORTPRIMARYAGENT,
				RESULT_SECONDARYAGENT,
				RESULT_SHORTSECONDARYAGENT,
				RESULT_CIPHER,
				RESULT_CIPHERGROUP,
				RESULT_PROTOCOLS,
				RESULT_HOSTS,
				RESULT_HOSTS_ALEXA,
				RESULT_URLS_TEXT,
				RESULT_HOST_RUNLIST,
				RESULT_HOST_PROFILES,
				RESULT_HOST_BASEPROFILES,
				RESULT_HOST_FUNDPROFILES,
				)
	
	RESULT_TYPE_VALUES = (
				(RESULT_ID, "Result entry ID"),
				(RESULT_CONDITION,"Condition"),
				(RESULT_DOMAIN,"Domains"),
				(RESULT_IP,"IP Address"),
				(RESULT_PRIMARYAGENT,"Primary Agent"),
				(RESULT_SHORTPRIMARYAGENT,"Primary Agent Family"),
				(RESULT_SECONDARYAGENT,"Secondary Agent"),
				(RESULT_SHORTSECONDARYAGENT,"Secondary Agent Family"),
				(RESULT_CIPHER,"Cipher suite"),
				(RESULT_CIPHERGROUP,"Cipher Suite group"),
				(RESULT_PROTOCOLS,"Protocol versions supported"),
				(RESULT_HOSTS,"Hostnames"),
				(RESULT_HOSTS_ALEXA,"Hostnames sorted by Alexa"),
				(RESULT_URLS_TEXT,"URL textfile (Qouted)"),
				(RESULT_HOST_RUNLIST, "TLS Prober CSV run configuration file"),
				(RESULT_HOST_PROFILES, "Server profiles"),
				(RESULT_HOST_BASEPROFILES, "Server base profiles"),
				(RESULT_HOST_FUNDPROFILES, "Server fundamental profiles"),
				)

	NO_ALEXA_LIMIT = -1
	ALEXA_TOP_100 = 100
	ALEXA_TOP_1K = 1000
	ALEXA_TOP_10K = 10000
	ALEXA_TOP_100K = 100000
	ALEXA_TOP_1M = 1000000
	NONALEXA = 0
	ALEXA_TYPE_VALUES = (
			(NO_ALEXA_LIMIT,"All"),
			(ALEXA_TOP_100,"Alexa Top 100"),
			(ALEXA_TOP_1K,"Alexa Top 1K"),
			(ALEXA_TOP_10K,"Alexa Top 10K"),
			(ALEXA_TOP_100K,"Alexa Top 100K"),
			(ALEXA_TOP_1M,"Alexa Top 1M"),
			(NONALEXA,"Exclude Alexa sites"),
				) 
	
	def __unicode__(self):
		return unicode(self.part_of_run)
	
	def setup(self):
		"""Initiate a run, creating common resources, such as the flag database""" 
		for (c, t) in ResultCondition.RESULTC_VALUES:
			common_cond,created = ResultCommonCondition.objects.get_or_create(condition=c);
			self.conditions.get_or_create(part_of_run=self.part_of_run,condition=c, defaults = {"common_condition": common_cond})
		
		while True:
			try:
				self.DomainSummary0, created = ProbeData.ServerDomain.objects.get_or_create(domain_parent=None, domain_name="", full_domain_name="", level=0)
				self.DomainEntries0.add(self.DomainSummary0)
			except:
				time.sleep(.1)
				continue;
			break;
		
		while True:
			try:
				self.IPDomainTopEntry0, created = ProbeData.IPAddressDomain.objects.get_or_create(ip_parent=None, ip_domain=0, full_ip_mask="0.0.0.0", level=0)
				self.IPDomainEntries0.add(self.IPDomainTopEntry0)
			except:
				time.sleep(.1)
				continue;
			break;
		self.save();

	def check_condition(self,cond):
		"""Make sure all flags are available"""
		common_cond,created = ResultCommonCondition.objects.get_or_create(condition=cond);
		self.conditions.get_or_create(part_of_run=self.part_of_run,condition=cond, defaults = {"common_condition": common_cond})
	

	def ready(self):
		"""Check if the object is ready for use"""
		return (self.conditions.count() != 0 and
			self.DomainEntries0.filter(level=0).count() != 0 and
			self.IPDomainEntries0.filter(level=0).count()!= 0
			)

	def start(self):
		"""Start an object by loading the necessary resources from the database"""
		self.condition_list = {}
		for c in list(self.conditions.all()):
			self.condition_list[c.condition] = c
		self.condition_group_list = {}
		update = False
		if self.IPDomainTopEntry0:
			self.ipdomain_top0 = self.IPDomainTopEntry0
		else:
			try:
				self.ipdomain_top0 = self.IPDomainEntries0.get(level=0)
			except:
				while True:
					try:
						self.ipdomain_top0, created = ProbeData.IPAddressDomain.objects.get_or_create(ip_parent=None, ip_domain=0, full_ip_mask="0.0.0.0", level=0)
						self.IPDomainEntries0.add(self.ipdomain_top0)
					except:
						time.sleep(.1)
						continue;
					break;
			self.IPDomainTopEntry0 = self.ipdomain_top0
			update = True

		if self.DomainTopEntry0:
			self.domain_top = self.DomainTopEntry0 
		else :
			self.domain_top = self.DomainEntries0.get(level=0)
			self.DomainTopEntry0 = self.domain_top
			update = True

		if update:
			try:
				self.save();
			except:
				pass # ignore errors		

	@transaction.commit_on_success	
	def get_condition_group(self, run, condition_group, lock=None):
		"""Get a condition group, if necessary by creating it"""
		condition_string = "_".join(sorted(list(condition_group)))
		
		group = self.condition_group_list.get(condition_string,None)
		if group:
			return group
		
		try:
			group = self.condition_groups.get(result_summary_string = condition_string)
		except:
			group = None 
		
		if not group:
			group = ResultConditionSet.FindSet(run, condition_string,
										 create=[self.condition_list[c] for c in condition_group])
		if group:
			if lock:
				lock.acquire()
			if not lock or condition_string not in self.condition_group_list:
				self.condition_group_list[condition_string] = group
				while True:
					try:
						sid = transaction.savepoint()
						self.condition_groups.add(group);
					except:
						transaction.savepoint_rollback(sid)
						time.sleep(0.1)
						continue;
					transaction.savepoint_commit(sid)
					break;
			
			else:
				group = self.condition_group_list.get(condition_string,None)
			if lock:
				lock.release()
			
		return group;
		
	@transaction.commit_on_success	
	def GetResultAgents(self, agent, target_class, target_short_class, target_source_class):
		"""Get a Server agent entry, can be used for multiple classes"""
		if not agent:
			if target_source_class.NotAvailable:
				agent = target_source_class.NotAvailable
			else:
				while True:
					try:
						sid = transaction.savepoint()
						agent,created = target_source_class.objects.get_or_create(agent_name ="N/A", major_version="0", minor_version="0", patch_version="0")
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
					break;
		
		short_agent = agent.agent_shortname
		if not short_agent:
			name = agent.agent_name
			short_agent_name = name.strip('()').partition('/')[0] if name != "N/A" else name
			if not short_agent_name:
				name = "N/A"
			
			while True:
				try:
					sid = transaction.savepoint()
					if AgentShortName.NotAvailable:
						short_agent = AgentShortName.NotAvailable
					else:
						short_agent,created = AgentShortName.objects.get_or_create(agent_shortname ="N/A")
					agent.agent_shortname =short_agent
					agent.save()   
					transaction.savepoint_commit(sid)
					AgentShortName.NotAvailable = short_agent
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
				break;
		
		full_result = None
		short_result = None
		
		if agent.id in target_class.AgentCache:
			full_result = target_class.AgentCache[agent.id]

		if short_agent.id in target_short_class.AgentCache:
			short_result = target_short_class.AgentCache[short_agent.id]
		
		if full_result and short_result:
			return (full_result, short_result)
		
		if not short_result:
			while True:
				try:
					sid = transaction.savepoint()
					short_result, created = target_short_class.objects.get_or_create(part_of_run = self.part_of_run, 
																agent_name=short_agent)
					transaction.savepoint_commit(sid)
					target_short_class.AgentCache[short_agent.id] = short_result
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
				break;
		
		if not full_result:
			while True:
				try:
					sid = transaction.savepoint()
					full_result, created = target_class.objects.get_or_create(part_of_run = self.part_of_run, 
																agent_name=agent, 
																defaults={"short_name":short_result}
																)
					transaction.savepoint_commit(sid)
					target_class.AgentCache[agent.id] = full_result
				except DatabaseError:
					transaction.savepoint_rollback(sid)
					time.sleep(0.1)
					continue
				except IntegrityError:
					transaction.savepoint_rollback(sid)
					time.sleep(0.1)
					continue
				except:
					time.sleep(0.1)
					continue
				break;
		
		
		return (full_result, short_result)

	@transaction.commit_on_success	
	def _migrate_server_alias(self, x):
		"""
		Migrate a server alias set from the ServerIPProbed list to 
		CommonServerIPProbed, reducing overhead
		"""  
		result = None
		try:
			result = ResultEntry.objects.select_related("result_entry").get(part_of_run=self.part_of_run, servername = x.server).result_entry
		except:
			try:
				result = ProbeData.ProbeResult.objects.get(part_of_run=self.part_of_run, servername = x.server)
			except ProbeData.ProbeResult.DoesNotExist:
				pass
			except ProbeData.ProbeResult.MultipleObjectsReturned:
				result = None
				for y in ProbeData.ProbeResult.objects.select_related("result_summary_group").filter(part_of_run=self.part_of_run, servername = x.server):
					if result:
						if ((y.result_summary_group and y.result_summary_group.result_summary_string) or 
							( not y.result_summary_group and (not result.result_summary_group or (result.result_summary_group and not result.result_summary_group.result_summary_string)))):
							if y.date < result.date or (y.date == result.date and y.id < result.id):
								result = y
					else:
						result = y
					
		if result:
			alias = ProbeData.CommonServerIPProbed.FetchOrCreateItem(x)
			result.common_server_aliases.add(alias)
		x.delete()
	
	def __do_migrate_thread(self,migrate_queue,report_queue):
		"""Perform the migrate task for a given queue"""
		import Queue
		
		while self.__threads_active:
			try:
				item = migrate_queue.get(timeout=1)
			except Queue.Empty:
				continue
			
			try:
				self._migrate_server_alias(item)
			except:
				pass
			
			if report_queue:
				report_queue.put(True)
			migrate_queue.task_done()					

	def __report_migrate_thread(self,queue):
		"""report progress for the migration"""
		import Queue
		
		i=0
		
		while self.__threads_active:
			try:
				result = queue.get(timeout=1)
			except Queue.Empty:
				continue
			queue.task_done()
			
			i += 1
			if i%100 == 0:
				print "Migrate Aliases", i
	
	def migrate_server_aliases(self, report=False, checkactive = None):
		"""
		Migrate server aliases from the ServerIPProbed list to 
		CommonServerIPProbed, reducing overhead
		"""  
		import threading
		import Queue
		self.__threads_active = True

		migrate_queue = Queue.Queue(100000)
		report_queue = None

		num_probers = 40
		threads = []
		
		if report:
			report_queue = Queue.Queue(100000)
			new_thread = threading.Thread(target=self.__report_migrate_thread, args=(report_queue,))
			new_thread.daemon = True
			new_thread.start()
			threads.append(new_thread)

		for i in range(num_probers):
			new_thread = threading.Thread(target=self.__do_migrate_thread, args=(migrate_queue,report_queue))
			new_thread.daemon = True
			new_thread.start()
			threads.append(new_thread)
		
		last_check = datetime.datetime.now()
		if report:
			print "(",self.part_of_run_id, ") Migrate", ProbeData.ServerIPProbed.objects.filter(part_of_run=self.part_of_run).count() ,"aliases"
		for x in ProbeData.ServerIPProbed.objects.filter(part_of_run=self.part_of_run).select_related("server","ip_address"):
			if checkactive and callable(checkactive):
				if (datetime.datetime.now() - last_check).seconds >= 10.0:
					last_check = datetime.datetime.now()
					if not checkactive():
						sys.exit()
				
			migrate_queue.put(x)

		if checkactive and callable(checkactive):
			while not migrate_queue.empty():
				if not checkactive():
					sys.exit()
				time.sleep(10)
					
		migrate_queue.join()
		if report_queue:
			report_queue.join()
		self.__threads_active = False
		
		for t in threads:
			t.join()
		

	def __generatesummary(self, result_list, summary_items):
		"""
		Generate a result summary based on the requested datafields
		"""
		from django.db.models import Count

		if not summary_items:
			return None
		summary_name = summary_items[0]
		source = None
		source2 = None
		result_id_field = "resultentry"
		if summary_name == ResultSummaryList.RESULT_ID:
			return list(result_list) 
		elif summary_name == ResultSummaryList.RESULT_PRIMARYAGENT:
			source = self.PrimaryServerAgentSummary.all().filter(part_of_run=self.part_of_run)
			source2 = ResultPrimaryServerAgent.objects.select_related("agent_name").filter(part_of_run=self.part_of_run)
			result_entry_field = "PrimaryServerAgentSummary"
		elif summary_name == ResultSummaryList.RESULT_SECONDARYAGENT:
			source = ResultSecondaryServerAgent.objects.filter(part_of_run=self.part_of_run)
			source2 = ResultSecondaryServerAgent.objects.select_related("agent_name").filter(part_of_run=self.part_of_run)
			result_entry_field = "SecondaryServerAgentSummary"
		elif summary_name == ResultSummaryList.RESULT_DOMAIN: 
			source = ProbeData.ServerDomain.objects.filter(level__gt=0)
			source2 = ProbeData.ServerDomain.objects
			result_entry_field = "DomainSummary0"
		elif summary_name == ResultSummaryList.RESULT_CONDITION:
			source = ResultCondition.objects.filter(part_of_run=self.part_of_run)
			source2 = ResultCondition.objects.filter(part_of_run=self.part_of_run)
			result_id_field = "resultconditionset__resultentry"
		elif summary_name == ResultSummaryList.RESULT_SHORTPRIMARYAGENT:
			source = ResultPrimaryServerAgentFamily.objects.filter(part_of_run=self.part_of_run)
			source2 = ResultPrimaryServerAgentFamily.objects.select_related("agent_name").filter(part_of_run=self.part_of_run)
			result_entry_field = "PrimaryShortServerAgentSummary"
		elif summary_name == ResultSummaryList.RESULT_SHORTSECONDARYAGENT:
			source = ResultSecondaryServerAgentFamily.objects.filter(part_of_run=self.part_of_run)
			source2 = ResultSecondaryServerAgentFamily.objects.select_related("agent_name").filter(part_of_run=self.part_of_run)
			result_entry_field = "SecondaryShortServerAgentSummary"
		elif summary_name == ResultSummaryList.RESULT_CIPHER:
			source = ProbeData.CipherName.objects
			source2 = ProbeData.CipherName.objects
			result_id_field = "resultciphersuite__resultciphersuitegroupentry__resultentry"
		elif summary_name == ResultSummaryList.RESULT_CIPHERGROUP:
			source = ResultCipherSuiteGroupEntry.objects.filter(part_of_run=self.part_of_run)
			source2 = ResultCipherSuiteGroupEntry.objects.select_related("cipher_suites").filter(part_of_run=self.part_of_run)
			result_entry_field = "cipher_suite_group"
		elif summary_name == ResultSummaryList.RESULT_IP:
			source = ProbeData.IPAddressDomain.objects
			source2 = ProbeData.IPAddressDomain.objects
			result_entry_field = "IPDomainSummary0"
		elif summary_name  in [ResultSummaryList.RESULT_HOSTS, ResultSummaryList.RESULT_HOSTS_ALEXA, ResultSummaryList.RESULT_URLS_TEXT, ResultSummaryList.RESULT_HOST_RUNLIST]:
			source = ResultEntry.objects.filter(part_of_run=self.part_of_run)
			source2 = ResultEntry.objects.select_related("servername").filter(part_of_run=self.part_of_run)
			result_entry_field = None
		elif summary_name == ResultSummaryList.RESULT_PROTOCOLS:
			source = self.conditions.filter(condition__in = [ResultCondition.RESULTC_SUPPORT_HIGHEST_SSLV3,
														ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_0,
														ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_1,
														ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_2]).filter(part_of_run=self.part_of_run)
			source2 = ResultCondition.objects
			result_id_field = "resultconditionset__resultentry"
		elif summary_name == ResultSummaryList.RESULT_HOST_PROFILES:
			source = ProbeData.ProbeCommonResult.objects.filter(proberesult__part_of_run=self.part_of_run)
			source2 = ProbeData.ProbeCommonResult.objects.filter(proberesult__part_of_run=self.part_of_run)
			result_entry_field = "key"
			result_id_field = "proberesult__resultentry"
		elif summary_name == ResultSummaryList.RESULT_HOST_BASEPROFILES:
			source = ProbeData.ProbeCommonResult.objects.filter(probecommonresult__proberesult__part_of_run=self.part_of_run)
			source2 = ProbeData.ProbeCommonResult.objects.filter(probecommonresult__proberesult__part_of_run=self.part_of_run)
			result_entry_field = "key"
			result_id_field = "probecommonresult__proberesult__resultentry"
		elif summary_name == ResultSummaryList.RESULT_HOST_FUNDPROFILES:
			source = ProbeData.ProbeCommonResult.objects.filter(fundamental_commonresult__proberesult__part_of_run=self.part_of_run)
			source2 = ProbeData.ProbeCommonResult.objects.filter(fundamental_commonresult__proberesult__part_of_run=self.part_of_run)
			result_entry_field = "key"
			result_id_field = "fundamental_commonresult__proberesult__resultentry"
		else:
			raise Exception()
			

		if summary_name in [ResultSummaryList.RESULT_HOSTS, ResultSummaryList.RESULT_HOSTS_ALEXA, ResultSummaryList.RESULT_URLS_TEXT, ResultSummaryList.RESULT_HOST_RUNLIST]:
			q = list(source.filter(part_of_run= self.part_of_run,id__in = result_list).annotate(filtered_count=Count("id")).order_by("-filtered_count"))
		else:
			q = list(source.distinct().filter(**{result_id_field+"__in": result_list, result_id_field+"__part_of_run":self.part_of_run}).annotate(filtered_count=Count(result_id_field)).order_by("-filtered_count"))
		
		ids = [x.id for x in q]
		#print summary_name, " ", len(ids)
		
		if summary_name in [ResultSummaryList.RESULT_HOSTS, 
						ResultSummaryList.RESULT_HOSTS_ALEXA, 
						ResultSummaryList.RESULT_URLS_TEXT, 
						ResultSummaryList.RESULT_HOST_RUNLIST]:
			q1 = source2.filter(part_of_run= self.part_of_run).filter(id__in=ids).annotate(total_count=Count("id"))
		else:
			q1 = source2.filter(id__in=ids, **{result_id_field+"__part_of_run":self.part_of_run}).annotate(total_count=Count(result_id_field))
		
		q2 = dict(q1.values_list("id","total_count"))#[(x.id,x) for x in q1])

		for x in q:
			x.total_count = q2.get(x.id,0)
			#print x.id, ":",x.total_count
			x.subset_results = None
			if len(summary_items)>1:
				#print "-------------"
				if result_entry_field:
					item_results = list(set(ResultEntry.objects.filter(part_of_run= self.part_of_run, **{result_entry_field:x.id}).values_list("id", flat=True)) & set(result_list))
				else:
					#item_results = list(x.resultentry_set.filter(id__in = result_list).values_list("id", flat=True))
					item_results = list(set(x.resultentry_set.filter(part_of_run= self.part_of_run).values_list("id", flat=True)) & set(result_list))
				x.subset_results = self.__generatesummary(item_results, summary_items[1:])
				#print "-------------"

		return list(q)

	
	def __generatesummary_cached(self, result_list, summary_items, id=0):
		"""Generate a summary based on cached information and the requested information"""

		if not summary_items:
			return None
		if not hasattr(self, "prefilled"):
			self.prefilled = False
		timebase = time.clock()
		summary_name = summary_items[0]
		source = None
		extra_fields = []

		if summary_name == ResultSummaryList.RESULT_ID:
			return list(result_list) 
		elif summary_name == ResultSummaryList.RESULT_PRIMARYAGENT:
			if not self.prefilled: 
				source = ResultPrimaryServerAgent.objects.all().filter(part_of_run=self.part_of_run)
				result_entry_field = "PrimaryServerAgentSummary"
			extra_fields = ["agent_name__agent_name"]
		elif summary_name == ResultSummaryList.RESULT_SECONDARYAGENT:
			if not self.prefilled: 
				source = ResultSecondaryServerAgent.objects.all().filter(part_of_run=self.part_of_run)
				result_entry_field = "SecondaryServerAgentSummary"
			extra_fields = ["agent_name__agent_name"]
		elif summary_name == ResultSummaryList.RESULT_DOMAIN: 
			if not self.prefilled: 
				source = ProbeData.ServerDomain.objects.all().filter(level__gt=0)
				result_entry_field = "DomainSummary0"
			extra_fields = [ "level", "domain_name", "full_domain_name", "domain_parent_id"]
		elif summary_name == ResultSummaryList.RESULT_CONDITION:
			if not self.prefilled: 
				source = ResultCondition.objects.all().filter(part_of_run=self.part_of_run)
				result_entry_field = "result_summary_group"
			extra_fields = ["condition"]
		elif summary_name == ResultSummaryList.RESULT_SHORTPRIMARYAGENT:
			if not self.prefilled: 
				source = ResultPrimaryServerAgentFamily.objects.all().filter(part_of_run=self.part_of_run)
				result_entry_field = "PrimaryShortServerAgentSummary"
			extra_fields = ["agent_name__agent_shortname"]
		elif summary_name == ResultSummaryList.RESULT_SHORTSECONDARYAGENT:
			if not self.prefilled: 
				source = ResultSecondaryServerAgentFamily.objects.all().filter(part_of_run=self.part_of_run)
				result_entry_field = "SecondaryShortServerAgentSummary"
			extra_fields = ["agent_name__agent_shortname"]
		elif summary_name == ResultSummaryList.RESULT_CIPHER:
			if not self.prefilled: 
				source = ProbeData.CipherName.objects.all()
				result_entry_field = "resultciphersuite__resultciphersuitegroupentry__resultentry"
			extra_fields = ["ciphername"]
		elif summary_name == ResultSummaryList.RESULT_CIPHERGROUP:
			if not self.prefilled: 
				source = ResultCipherSuiteGroupEntry.objects.all().filter(part_of_run=self.part_of_run)
				result_entry_field = "cipher_suite_group"
			extra_fields = ["cipher_suites__cipher_suites__ciphername"]
		elif summary_name == ResultSummaryList.RESULT_IP:
			if not self.prefilled: 
				source = IPAddressDomain.objects.all()
				result_entry_field = "IPDomainSummary0"
			extra_fields = [ "level",  "ip_domain", "full_ip_mask", "ip_parent_id",]
		elif summary_name  in [ResultSummaryList.RESULT_HOSTS, ResultSummaryList.RESULT_HOSTS_ALEXA]:
			if not self.prefilled: 
				source = ResultEntry.objects.all().filter(part_of_run=self.part_of_run)
			result_entry_field = None
		elif summary_name == ResultSummaryList.RESULT_PROTOCOLS:
			if not self.prefilled: 
				source = self.conditions.filter(condition__in = [ResultCondition.RESULTC_SUPPORT_HIGHEST_SSLV3,
															ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_0,
															ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_1,
															ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_2]).filter(part_of_run=self.part_of_run)
				result_entry_field = None
			extra_fields = ["condition"]
		else:
			raise Exception()
		
		q = []
		if summary_name in [ResultSummaryList.RESULT_HOSTS, ResultSummaryList.RESULT_HOSTS_ALEXA]:
			cache = self.summary_cache.setdefault("entries", {})

			if not self.prefilled: 
				self.cache_lock.acquire()
				already_loaded = set(cache.iterkeys()) 
				to_be_loaded = set(result_list) - already_loaded
				for x in to_be_loaded:
					if x not in cache:
						cache[x] = None
				self.cache_lock.release()
				items = []
				try:
					items = list(source.filter(id__in = list(to_be_loaded)).values("id","servername__servername", "servername__port",*(extra_fields if extra_fields else [])));
				except:
					pass
				self.cache_lock.acquire()
				for x in items:
					if x["id"] not in cache or cache[x["id"]] == None:
						x.update({"name":x["servername__servername"] + ":" + str(x["servername__port"]),"_result_entry_list":[], "__cache__":cache})
						cache[x["id"]] = x 
				self.cache_lock.release()

				waiting = set(result_list)
				while waiting:
					waiting = set([x for x in waiting if cache[x] == None])
					if not waiting:
						break;
					time.sleep(1)
			def do_search3(q, result_list, cache):
				for x in result_list:
					if x in cache:
						q.append({"value":cache[x], "filtered_id":[x], "filtered_count":1, "total_count":1, "subset_results": None})
			do_search3(q, result_list, cache)
		else:
			cache = self.summary_cache.setdefault(summary_name, {})
			cache_host = self.summary_cache.setdefault("entries", {})

			already_loaded = set(cache.iterkeys())
			if not self.prefilled: 
				items = list(source.exclude(id__in=list(already_loaded)).filter(resultentry__part_of_run= self.part_of_run, resultentry__id__in = result_list).
								values("id", *(extra_fields if extra_fields else []))
							)

				if items or already_loaded:
					items2 = []
					if items:
						self.cache_lock.acquire()
						for x in items:
							already_loaded.add(x["id"])
							if x["id"] not in cache or cache[x["id"]] == None:
								cache[x["id"]] = None
								items2.append(x)
						self.cache_lock.release()
		
						for x in items2:
							try:
								x["_result_entry_list"]= set(ResultEntry.objects.filter(part_of_run= self.part_of_run, **{result_entry_field+"__id":x["id"]}).values_list("id",flat=True))
							except:
								raise
							
						self.cache_lock.acquire()
						for x in items2:
							if x["id"] not in cache or cache[x["id"]] == None:
								x.update({"__cache__":cache})
								cache[x["id"]] = x 
								for y in x["_result_entry_list"]:
									if y in cache_host:
										cache_host[y].setdefault(summary_name,set()).add(x["id"]) 
						self.cache_lock.release()
		
					while any([cache[x] == None for x in already_loaded]):
						time.sleep(1)
	
			result_list_set = set(result_list)
			if len(already_loaded) < len(result_list):
				def do_search(q,already_loaded,result_list_set, cache):
					for xi in already_loaded:
						x = cache[xi]
						match = x["_result_entry_list"] & result_list_set
						if match:
							add_item = {"value":x, "filtered_id":match, "filtered_count":len(match), "total_count":len(x["_result_entry_list"]),"subset_results": None}
							add_item["sort_key"] = [add_item["filtered_count"], add_item["total_count"]] + [x[z] for z in extra_fields]
							q.append(add_item)
				do_search(q,already_loaded,result_list_set, cache)
			else:
				def do_search2(self,q,already_loaded,result_list_set, cache, cache_host, summary_name):
					visited = set()
					timebase = time.clock()
					for xi1 in [xi2 for xi2 in result_list_set if xi2 in cache_host]:
						visited.update(cache_host[xi1].get(summary_name,[]))
					for xi in visited:
						timebase2 = time.clock()
						x = cache[xi]
						match = x["_result_entry_list"] & result_list_set
						if match:
							add_item = {"value":x, "filtered_id":match, "filtered_count":len(match), "total_count":len(x["_result_entry_list"]),"subset_results": None}
							add_item["sort_key"]  = [add_item["filtered_count"], add_item["total_count"]]+[x[z] for z in extra_fields]
							q.append(add_item)
				do_search2(self,q,already_loaded,result_list_set, cache, cache_host, summary_name)
				
	
			def sort_list(q,extra_fields):
				return sorted(q, reverse=True, key = lambda x: x["sort_key"])
			q = sort_list(q,extra_fields)
		
		if len(summary_items)>1:
			for x in q:
				#print "-------------"
				item_results = x["filtered_id"]
				x["subset_results"] = self.__generatesummary(item_results, summary_items[1:])
				#print "-------------"

		return list(q)


	def _pre_fill_cache(self, summary_name, entry_event, extra_query):
		"""Fill the cache with the requested information"""
		
		source = None
		source2 = None
		extra_fields = None
		if summary_name == ResultSummaryList.RESULT_PRIMARYAGENT:
			source = self.PrimaryServerAgentSummary.filter(part_of_run=self.part_of_run)
			result_entry_field = "PrimaryServerAgentSummary"
			extra_fields = ["agent_name__agent_name"]
		elif summary_name == ResultSummaryList.RESULT_SECONDARYAGENT:
			source = self.SecondaryServerAgentSummary.filter(part_of_run=self.part_of_run)
			result_entry_field = "SecondaryServerAgentSummary"
			extra_fields = ["agent_name__agent_name"]
		elif summary_name == ResultSummaryList.RESULT_DOMAIN: 
			source = self.DomainEntries0
			result_entry_field = "DomainSummary0"
			extra_fields = [ "level", "domain_name", "full_domain_name", "domain_parent_id"]
		elif summary_name == ResultSummaryList.RESULT_CONDITION:
			source = self.conditions
			result_entry_field = "result_summary_group"
			extra_fields = ["condition"]
		elif summary_name == ResultSummaryList.RESULT_SHORTPRIMARYAGENT:
			source = self.PrimaryShortServerAgentSummary.filter(part_of_run=self.part_of_run)
			result_entry_field = "PrimaryShortServerAgentSummary"
			extra_fields = ["agent_name__agent_shortname"]
		elif summary_name == ResultSummaryList.RESULT_SHORTSECONDARYAGENT:
			source = self.SecondaryShortServerAgentSummary.filter(part_of_run=self.part_of_run)
			result_entry_field = "SecondaryShortServerAgentSummary"
			extra_fields = ["agent_name__agent_shortname"]
		elif summary_name == ResultSummaryList.RESULT_CIPHER:
			source = ProbeData.CipherName.objects
			result_entry_field = "ciphersuitegroup__resultciphersuitegroupentry__resultentry"
			extra_fields = ["ciphername"]
		elif summary_name == ResultSummaryList.RESULT_CIPHERGROUP:
			source = self.CipherSuiteGroupEntries.filter(part_of_run=self.part_of_run)
			result_entry_field = "cipher_suite_group"
			extra_fields = ["cipher_suites__cipher_suites__ciphername"]
		elif summary_name == ResultSummaryList.RESULT_IP:
			source = self.IPDomainEntries0
			result_entry_field = "IPDomainSummary0"
			extra_fields = [ "level",  "ip_domain", "full_ip_mask", "ip_parent_id",]
		elif summary_name  in [ResultSummaryList.RESULT_HOSTS, ResultSummaryList.RESULT_HOSTS_ALEXA]:
			source = ResultEntry.objects.filter(part_of_run= self.part_of_run)
			if extra_query and summary_name in [ResultSummaryList.RESULT_HOSTS]:
				source = source.filter(extra_query)
			result_entry_field = None
		else:
			raise Exception()
			

		q = []
		if summary_name in [ResultSummaryList.RESULT_HOSTS, ResultSummaryList.RESULT_HOSTS_ALEXA]:
			cache = self.summary_cache.setdefault("entries", {})

			items = []
			temp_group = {}
			try:
				items = list(source.all().values("id","servername__servername", "servername__port",
												"result_summary_group_id",
												*(extra_fields if extra_fields else [])));
			except:
				pass
			#print summary_name, len(items)
			for x in items:
				temp_group.setdefault(x["result_summary_group_id"],set()).add(x["id"])
			
			try:
				cond_items = [{"id":x.id, "condition":x.condition, 
							"groups_id":list(x.resultconditionset_set.all().values_list("id",flat=True)),}
							for x in self.conditions.all()]
			except:
				raise
				pass
			
			for x in cond_items:
				result_items = set()
				for y in x["groups_id"]:
					if y in temp_group:
						result_items.update(temp_group[y])
				x["_result_entry_list"] = result_items
				
			self.cache_lock.acquire()
			for x in items:
				if x["id"] not in cache or cache[x["id"]] == None:
					x.update({"name":x["servername__servername"] + ":" + str(x["servername__port"]),"_result_entry_list":[], "__cache__":cache})
					cache[x["id"]] = x
			cond_cache = self.summary_cache.setdefault("conditions", {})
			for x in cond_items:
				if x["id"] not in cond_cache:
					cond_cache[x["id"]] = x
				if x["condition"] not in cond_cache:
					cond_cache[x["condition"]] = x

			self.cache_lock.release()
			entry_event.set()
		else:
			cache = self.summary_cache.setdefault(summary_name, {})

			items =  list(source.all().values("id", *(extra_fields if extra_fields else []))						)

			def fetch_data(summary_name, list_items, query, result_entry_field, cache, cache_lock, entry_event):
				
				#i = 0
				for x in list_items:
					try:
						x["_result_entry_list"]= set(query.filter(**{result_entry_field+"__id":x["id"]}).values_list("id",flat=True))
						#i+=1;
						#if i % 100 == 0:
						#	print summary_name, i,"/",len(list_items)
					except:
						raise
				
				entry_event.wait()
				cache_lock.acquire()
				cache_host = self.summary_cache["entries"] 
				for x in list_items:
					if x["id"] not in cache or cache[x["id"]] == None:
						x.update({"__cache__":cache})
						cache[x["id"]] = x 
						for y in x["_result_entry_list"]:
							if y in cache_host:
								cache_host[y].setdefault(summary_name,set()).add(x["id"]) 
				cache_lock.release()
			threads = []
			
			step = max((len(items)+20)/20, 50)
			import threading
			for i in range(0, len(items), step) :
				new_thread = threading.Thread(target=fetch_data, args=(summary_name,items[i:min(len(items),i+step)],
													ResultEntry.objects.filter(part_of_run= self.part_of_run),
													result_entry_field, cache, self.cache_lock, entry_event
															))
				new_thread.start()
				threads.append(new_thread)
	
			for x in threads:
				x.join()

		#print summary_name
				
	def init_cache(self, summaries, fQ=None):
		"""Initialize the cache"""
		import threading

		if not hasattr(self, "summary_cache"):
			self.summary_cache = {}
			self.cache_lock = threading.Lock()
		
		threads = []
		entry_event = threading.Event()
		
		for summary_name in summaries:
			new_thread = threading.Thread(target=self._pre_fill_cache, args=(summary_name,entry_event, fQ))
			new_thread.start()
			threads.append(new_thread)

		for x in threads:
			x.join()
		self.prefilled = True
			
	def GetAnalyze(self,filter=None,summaries=None, use_cache=False, id=0,limitresult = None):
		"""
		Analyze this specific result entry, by selecting entries from the run, limited by 
		the filter parameters, then produce the summaries specified
		
		filter is a dictionary of with QUERY_* as names for the entries with the following meaning. 
		An empty dictionary means all entries in the run is used.
		
			QUERY_CONDITION: List of ANDed ResultCondition conditions the entries must include (if present, this is the primary criteria) 

			The following are a list that can be specified in any combination using strings, 
			the associated database objects, or primary key ids for the table

			QUERY_DOMAIN, ProbeData.Server
			QUERY_IP,  ProbeData.IP_Address
			QUERY_PRIMARYAGENT,  ProbeData.PrimaryServerAgent
			QUERY_SECONDARYAGENT,  ProbeData.SecondaryServerAgent, ResultSecondaryServerAgent
			QUERY_SHORTPRIMARYAGENT,  ProbeData.AgentShortName
			QUERY_SHORTSECONDARYAGENT,  ProbeData.AgentShortName
			QUERY_CIPHER,  ProbeData.CipherName
			QUERY_CIPHERGROUP,  Resultdb2.CipherSuiteGroup
			QUERY_SPECINTOL,  ProbeData.CommonSpecificExtensionIntolerance
			
			QUERY_AUTO , discover the queries from each element class (one of the above, unknowns trigger exception)
			
			
		Summaries is a dictionary with caller specified names. Each value in the dictionary is a list 
		of RESULT_* enums, with the results using the associated resultdb2 class  
		
				RESULT_ID, id(ResultEntry)
				RESULT_CONDITION, ResultCondition,
				RESULT_DOMAIN, ProbeData.ServerDomain
				RESULT_IP, ProbeData.IPAddressDomain
				RESULT_PRIMARYAGENT, ResultPrimaryServerAgent
				RESULT_SHORTPRIMARYAGENT, ResultPrimaryServerAgentFamily
				RESULT_SECONDARYAGENT, ResultSecondaryServerAgent
				RESULT_SHORTSECONDARYAGENT, ResultSecondaryServerAgentFamily
				RESULT_CIPHER, ResultCipherSuite
				RESULT_CIPHERGROUP, ResultCipherSuiteGroupEntry
				RESULT_PROTOCOLS, ResultCondition: The highest supported TLS protocol
				RESULT_HOSTS, ResultEntry
				RESULT_HOSTS_ALEXA, ResultEntry
				RESULT_URLS_TEXT, URLs as a list of text entry
				RESULT_HOST_RUNLIST, (num,host,port) as a CSV file

		For each name in the dictionary, the returned result dictionary returns a list of objects 
		of the associated class that also contain these extra attributes:
		
			filtered_count: The number of entries in the run matching the filter that have this attribute
			total_count:	The number of total entries in the run that have this attribute
		
			subset_results : If the summaries list contained multiple entries this entry 
							is generated for each entry to do summaries for the next level. 
							Please note that specifying multiple levels of summaries can make
							the result generation phase take a long time.
		
		
		Additionally the dictionary contains these entries (which must not be specified by the caller)
		
		  "_total" : The total number of entries in the run
		  "_matching": The number of entries matching the filter.


		"""
		
		#from django.db.models import Count
			
		result_list = []
		extra_Q=None

		if not hasattr(self, "summary_cache"):
			self.summary_cache = {}
			import threading
			self.cache_lock = threading.Lock()
		
		if filter and ResultSummaryList.QUERY_AUTO in filter:
			for x in filter[ResultSummaryList.QUERY_AUTO]:
				found = False
				for name, type in [
							(ResultSummaryList.QUERY_DOMAIN, ProbeData.Server),
							(ResultSummaryList.QUERY_IP,  ProbeData.IP_Address),
							(ResultSummaryList.QUERY_PRIMARYAGENT,  ProbeData.PrimaryServerAgent),
							(ResultSummaryList.QUERY_SECONDARYAGENT,  ProbeData.SecondaryServerAgent),
							(ResultSummaryList.QUERY_SHORTPRIMARYAGENT,  ProbeData.AgentShortName),
							(ResultSummaryList.QUERY_SHORTSECONDARYAGENT,  ProbeData.AgentShortName),
							(ResultSummaryList.QUERY_CIPHER,  ProbeData.CipherName),
							(ResultSummaryList.QUERY_CIPHER,  ResultCipherSuite),
							(ResultSummaryList.QUERY_CIPHERGROUP,  CipherSuiteGroup),
							(ResultSummaryList.QUERY_CIPHERGROUP,  ResultCipherSuiteGroupEntry),
							(ResultSummaryList.QUERY_SPECINTOL, ProbeData.CommonSpecificExtensionIntolerance),
							(ResultSummaryList.QUERY_DHEKEYSIZE, ResultDHEKeySize)
								]: 
					if isinstance(x, type):
						found = True;
						filter.setdefault(name,[]).append(x)
						break;
				if not found:
					raise Exception("Unknown query type")
			del filter[ResultSummaryList.QUERY_AUTO]
			
			if not filter:
				raise Exception("No query")
				
		if not filter:
			q = ResultEntry.objects.filter(part_of_run= self.part_of_run)
			if limitresult:
				q = q.filter(limitresult)
			
			result_list = list(q.values_list("id", flat=True)) if not use_cache else self.summary_cache["entries"].iterkeys()
		else:
			while True:
				is_finished = False
				has_conditions = False

				extra_Q = None
				if limitresult:
					extra_Q = extra_Q & limitresult if  extra_Q else limitresult

				if ResultSummaryList.QUERY_ALEXA_RESTRICT in filter:
					limit = int(filter[ResultSummaryList.QUERY_ALEXA_RESTRICT])
					if limit > ResultSummaryList.NO_ALEXA_LIMIT:
						if limit ==  ResultSummaryList.NONALEXA:
							server_Q = Q(servername__alexa_rating = 0)
						else:
							server_Q = Q(servername__alexa_rating__gt = 0) & Q(servername__alexa_rating__lte = limit)
					
						extra_Q = extra_Q & server_Q if extra_Q else server_Q  

				if ResultSummaryList.QUERY_PROTOCOL_RESTRICT in filter:
					protocol = filter[ResultSummaryList.QUERY_PROTOCOL_RESTRICT]
					if protocol:
						server_Q = Q(servername__protocol__in = protocol)
						extra_Q = extra_Q & server_Q if extra_Q else server_Q  
						
				if ResultSummaryList.QUERY_RESTRICT_RUN in filter:
					q = ProbeData.IP_Address.objects.filter(resultentry__part_of_run__id__in = filter[ResultSummaryList.QUERY_RESTRICT_RUN]).distinct().values_list("id", flat=True)
					run_q = Q(ip_addresses__id__in = q)
					extra_Q = extra_Q & run_q if extra_Q else run_q
				
				qlist = []
				for f in filter.get(ResultSummaryList.QUERY_CONDITION, []):
					try:
						has_conditions = True
						if use_cache:
							condition = self.summary_cache["conditions"][f]
						else:
							condition = self.conditions.get(condition = f)
						qlist.append(condition)
					except:
						pass
						
				
				condition_list = None
				if qlist:
					for c in qlist:
						if use_cache:
							condition_list = condition_list & set(c["_result_entry_list"]) if condition_list else set(c["_result_entry_list"]) 
						else:
							q = c.resultconditionset_set.filter(id__in=condition_list) if condition_list else c.resultconditionset_set 
							condition_list =  list(q.values_list("id", flat=True))
						if not condition_list:
							break;
				
				if condition_list or not has_conditions:
					if use_cache:
						result_list = list(condition_list) if condition_list or has_conditions else list(self.summary_cache["entries"].iterkeys())
						if extra_Q:
							q = ResultEntry.objects.filter(extra_Q,id__in = result_list)
							result_list= list(q.distinct().values_list("id", flat=True))
					else: 
						q = ResultEntry.objects.filter(part_of_run= self.part_of_run, result_summary_group__in = condition_list) if condition_list or has_conditions else ResultEntry.objects.filter(part_of_run= self.part_of_run) 
						if extra_Q:
							q = q.filter(extra_Q)
										
						result_list = list(q.distinct().values_list("id", flat=True))
				else:
					result_list = []
					
				if not result_list:
					is_finished =True
				
				for (desc, query_mode, 
								filter_rec, filter_summary, 
								self_entries,
								entry_fieldname, fieldname, 
								f_fun, extra_cond) in [
						("Domain",ResultSummaryList.QUERY_DOMAIN,  
								ProbeData.Server, ProbeData.ServerDomain, 
								self.DomainEntries0, 
								"fullservername", "domainentries0", 
								lambda f:f.servername, None),
						("IP Domain",ResultSummaryList.QUERY_IP,  
								ProbeData.IP_Address, ProbeData.IPAddressDomain, 
								self.IPDomainEntries0, 
								"full_ip_mask", "ipdomainentries", 
								lambda f:f.ip_address, None),
						("Primary Agent",ResultSummaryList.QUERY_PRIMARYAGENT,  
								ProbeData.PrimaryServerAgent, (ResultPrimaryServerAgent, ResultPrimaryServerAgent.objects.filter(part_of_run=self.part_of_run)), 
								self.PrimaryServerAgentSummary.filter(part_of_run=self.part_of_run), 
								"agent_name", "primaryserveragentsummary", 
								lambda f:f.agent_name, None),
						("Secondary Agent",ResultSummaryList.QUERY_SECONDARYAGENT,
								ProbeData.SecondaryServerAgent, (ResultSecondaryServerAgent, ResultSecondaryServerAgent.objects.filter(part_of_run=self.part_of_run)), 
								self.SecondaryServerAgentSummary.filter(part_of_run=self.part_of_run), 
								"agent_name", "secondaryserveragentsummary", 
								lambda f:f.agent_name, None),
						("Primary Agent Family",ResultSummaryList.QUERY_SHORTPRIMARYAGENT,  
								ProbeData.AgentShortName, (ResultPrimaryServerAgentFamily, ResultPrimaryServerAgentFamily.objects.filter(part_of_run=self.part_of_run)), 
								self.PrimaryShortServerAgentSummary.filter(part_of_run=self.part_of_run), 
								"agent_shortname", "primaryshortserveragentsummary", 
								lambda f:f.agent_shortname, None),
						("Secondary Agent Family",ResultSummaryList.QUERY_SHORTSECONDARYAGENT, 
								ProbeData.AgentShortName, (ResultSecondaryServerAgentFamily, ResultSecondaryServerAgentFamily.objects.filter(part_of_run=self.part_of_run)), 
								self.SecondaryShortServerAgentSummary.filter(part_of_run=self.part_of_run), 
								"agent_shortname", "secondaryshortserveragentsummary", 
								lambda f:f.agent_shortname, None),
						("Cipher Suite",ResultSummaryList.QUERY_CIPHER,  
								ProbeData.CipherName, None, 
								self.CipherSuiteGroupEntries.filter(part_of_run = self.part_of_run), 
								"cipher_support__cipher_name", "cipher_suite_group", 
								lambda f:f.id, None),
						("Cipher Suite exclude",ResultSummaryList.QUERY_CIPHER_EXCLUDE,  
								ProbeData.CipherName, None, 
								self.CipherSuiteGroupEntries.filter(part_of_run = self.part_of_run), 
								"cipher_support__cipher_name", "cipher_suite_group", 
								lambda f:f.id, None),
						("Cipher Suite Group",ResultSummaryList.QUERY_CIPHERGROUP,
								CipherSuiteGroup, (ResultCipherSuiteGroupEntry, ResultCipherSuiteGroupEntry.objects.filter(part_of_run=self.part_of_run)), 
								self.CipherSuiteGroupEntries.filter(part_of_run = self.part_of_run), 
								"cipher_suites_string", "cipher_suite_group", 
								lambda f:f.cipher_suites_string, None),
						("Specific Intolerance",ResultSummaryList.QUERY_SPECINTOL, 
								None, ProbeData.CommonSpecificExtensionIntolerance, 
								None, 
								"intolerant_for_extension", "result_entry__common_result__intolerant_for_extension",
								 lambda f:f.intolerant_for_extension, {"result_entry__part_of_run":self.part_of_run}),
						("DHE Keysize",ResultSummaryList.QUERY_DHEKEYSIZE,  
								None, ResultDHEKeySize, 
								self.dhe_keysizes.filter(part_of_run=self.part_of_run), 
								"dhe_keysize", "dhe_keysize", 
								lambda f:f.dhe_keysize, None),
						]:
					if not is_finished and query_mode in filter: 
						serverids = []
						for f in filter.get(query_mode, []):
							if filter_rec and isinstance(f, filter_rec):
								param = {entry_fieldname:f_fun(f)}
								if extra_cond:
									param.update(extra_cond)
								serverids+=list(self_entries.filter(**param).values_list("id",flat=True))
							else:
								try:
									if filter_summary and isinstance(filter_summary, tuple) and isinstance(f, filter_summary[0]):
										serverids.append(f.id);
									if filter_summary and isinstance(f, filter_summary):
										serverids.append(f.id);
									elif isinstance(f, int):
										serverids.append(f);
									elif isinstance(f, str):
										param = {entry_fieldname:f}
										if extra_cond:
											param.update(extra_cond)
										serverids+=list(self_entries.filter(**param).values_list("id",flat=True))
									else:
										raise Exception("TypeError in %s query: %s" %(desc,f))
								except:
									print "a:",  filter_summary
									print "b:",f
									raise
							
						if not serverids:
							result_list = []
							is_finished =True
							break
						
						#q = (self.summaries.filter(id__in = result_list) if result_list else self.summaries)
						if query_mode in [ResultSummaryList.QUERY_CIPHER_EXCLUDE]:
							q = ResultEntry.objects.filter(part_of_run= self.part_of_run).filter(**{fieldname+"__in": list(set(serverids))})
							temp_list = set(result_list) - set(q.distinct().values_list("id", flat=True))
						else:  
							q = ResultEntry.objects.filter(part_of_run= self.part_of_run).filter(**{fieldname+"__in": serverids})
							temp_list = set(q.distinct().values_list("id", flat=True))
						
						result_list = list(temp_list & set(result_list)) if result_list else list(temp_list)
						
						if not result_list:
							is_finished =True
							break
					
				break #Single run

		tot_q = ResultEntry.objects.filter(part_of_run= self.part_of_run).filter(result_summary_group__id__gt=0)
		if extra_Q:
			tot_q = tot_q.filter(extra_Q)
		
		result = {"_total": tot_q.count(), "_matching":len(result_list)}
		
		if use_cache:
			for (summary_name, summary_items) in summaries.iteritems():
				result[summary_name] = self.__generatesummary_cached(result_list, summary_items, id)
		else:
			for (summary_name, summary_items) in summaries.iteritems():
				result[summary_name] = self.__generatesummary(result_list, summary_items)

		return result
		
		
