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

from probedb.resultdb2.condition import *
				
import probedb.probedata2.models as ProbeData

from probedb.resultdb2.ciphers import *

# Create your models here.


class ResultPrimaryServerAgentFamily(models.Model):
	"""Primary server agent shortname registered for this run"""
	 
	part_of_run = models.ForeignKey(ProbeData.ProbeRun)
	agent_name = models.ForeignKey(ProbeData.AgentShortName)

	AgentCache = {}

	class Meta:
		unique_together=("part_of_run","agent_name")

	def __unicode__(self):
		return unicode(self.agent_name) + " "+ unicode(self.part_of_run) 

	def GetName(self):
		return self.agent_name.GetName()

class ResultSecondaryServerAgentFamily(models.Model):
	"""Secondary server agent shortname registered for this run"""
	
	part_of_run = models.ForeignKey(ProbeData.ProbeRun)
	agent_name = models.ForeignKey(ProbeData.AgentShortName)

	AgentCache = {}

	class Meta:
		unique_together=("part_of_run","agent_name")

	def __unicode__(self):
		return unicode(self.agent_name) + " "+ unicode(self.part_of_run) 

	def GetName(self):
		return self.agent_name.GetName()

class ResultPrimaryServerAgent(models.Model):
	"""Primary server agent string registered for this run"""
	part_of_run = models.ForeignKey(ProbeData.ProbeRun)
	agent_name = models.ForeignKey(ProbeData.PrimaryServerAgent)
	short_name= models.ForeignKey(ResultPrimaryServerAgentFamily)
	
	AgentCache = {}

	class Meta:
		unique_together=("part_of_run","agent_name")

	def __unicode__(self):
		return unicode(self.agent_name) + " "+ unicode(self.part_of_run) 

	def GetName(self):
		return self.agent_name.GetName()

class ResultSecondaryServerAgent(models.Model):
	"""Secondary server agent string registered for this run"""
	part_of_run = models.ForeignKey(ProbeData.ProbeRun)
	agent_name = models.ForeignKey(ProbeData.SecondaryServerAgent)
	short_name= models.ForeignKey(ResultSecondaryServerAgentFamily)

	AgentCache = {}

	class Meta:
		unique_together=("part_of_run","agent_name")

	def __unicode__(self):
		return unicode(self.agent_name) + " "+ unicode(self.part_of_run) 

	def GetName(self):
		return self.agent_name.GetName()

class ResultCommonEntryProtocol(models.Model):
	"""
	Global result flags for a tested TLS Version, across extensions and
	incorrect version in the RSA Client Key Exchange.
	
	Results are cached 
	"""
	version_tested_major = models.PositiveIntegerField()
	version_tested_minor = models.PositiveIntegerField()

	result_summary_group =  models.ForeignKey(ResultCommonConditionSet, null=True)

	class Meta:
		unique_together=("version_tested_major","version_tested_minor","result_summary_group")


	__cache = {}

	@staticmethod
	@transaction.commit_on_success
	def FetchOrCreateItem(**params):
		"""Find an existing result entry, or create a new entry"""
 
		param1 = dict([(x,params[x]) for x in ["version_tested_major","version_tested_minor","result_summary_group"]])
		
		key = "{version_tested_major:d}{version_tested_minor:d}_{result_summary_group.id:x}".format(**param1)
		
		if key in ResultCommonEntryProtocol.__cache:
			return ResultCommonEntryProtocol.__cache[key];
		
		while True:
			try:
				sid = transaction.savepoint()
				item,created= ResultCommonEntryProtocol.objects.get_or_create(**param1)
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

		ResultCommonEntryProtocol.__cache[key] = item
		return item;

class ResultCommonEntryProtocolSet(models.Model):
	"""
	Global set of results for all tested protocol versions over extensions 
	and incorrect version for a given probe result
	
	Entries are cached, and keyed to the IDs of the result entries 
	"""
	key = models.CharField(max_length=300, unique = True) 
	protcol_result_summary =  models.ManyToManyField(ResultCommonEntryProtocol, null=True)

	__cache = {}

	@classmethod
	def _CalculateKey(cls, summary):
		return "{0:s}".format(
				"-".join(["{0:x}".format(x) for x in sorted([y.id for y in summary])]),
			)

	@staticmethod
	@transaction.commit_on_success
	def FetchOrCreateItem(summary):
		"""Find an exisiting entry of this result, or create a new entry""" 
		key = ResultCommonEntryProtocolSet._CalculateKey(summary)
		
		if key in ResultCommonEntryProtocolSet.__cache:
			return ResultCommonEntryProtocolSet.__cache[key];
		
		while True:
			try:
				sid = transaction.savepoint()
				item,created= ResultCommonEntryProtocolSet.objects.get_or_create(key=key)
				if created:
					item.protcol_result_summary.add(*summary)
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

		ResultCommonEntryProtocolSet.__cache[key] = item
		return item;

class ResultEntry(models.Model):
	"""A summary of results for a server in a given run"""
	
	part_of_run = models.ForeignKey(ProbeData.ProbeRun)
	servername = models.ForeignKey(ProbeData.Server)

	result_entry = models.ForeignKey(ProbeData.ProbeResult)

	ip_addresses = models.ManyToManyField(ProbeData.IP_Address, null=True)
	
	version_supported_major = models.PositiveIntegerField()
	version_supported_minor = models.PositiveIntegerField()

	result_summary_group =  models.ForeignKey(ResultConditionSet, null=True)
	protcol_result_summary_set =  models.ForeignKey(ResultCommonEntryProtocolSet, null=True)
	
	cipher_suite_group = models.ForeignKey(ResultCipherSuiteGroupEntry, null=True)	
	
	PrimaryShortServerAgentSummary = models.ForeignKey(ResultPrimaryServerAgentFamily, null=True)
	SecondaryShortServerAgentSummary = models.ManyToManyField(ResultSecondaryServerAgentFamily, null=True)
	PrimaryServerAgentSummary = models.ForeignKey(ResultPrimaryServerAgent, null=True)
	SecondaryServerAgentSummary = models.ManyToManyField(ResultSecondaryServerAgent, null=True)
	
	IPDomainSummary0 =  models.ManyToManyField(ProbeData.IPAddressDomain, null=True)
	DomainSummary0  =  models.ManyToManyField(ProbeData.ServerDomain, null=True)

	dhe_keysize = models.ForeignKey(ResultDHEKeySize, null=True, db_index = True)
	
	def GetConditions(self):
		"""Get result flags"""
		return self.result_summary_group.GetConditions()
	

from summary_models import *