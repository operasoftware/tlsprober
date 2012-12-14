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

import probedb.probedata2.ciphers as ProbeDataCipher
				
# Create your models here.

class ResultCipherSuite(models.Model):
	"""Cipher suite result registered for a given run"""
	part_of_run = models.ForeignKey(ProbeDataCipher.ProbeRun)
	cipher_name = models.ForeignKey(ProbeDataCipher.CipherName)

	class Meta:
		unique_together=("part_of_run", "cipher_name")

	def __unicode__(self):
		return unicode(self.part_of_run) + unicode(self.cipher_name) 
	
	def GetName(self):
		return self.cipher_name.ciphername

class ResultDHEKeySize(models.Model):
	"""Ephemeral Dh (DHE) key size registered for a given run"""
	part_of_run = models.ForeignKey(ProbeDataCipher.ProbeRun)
	dhe_keysize = models.IntegerField()

	class Meta:
		unique_together=("part_of_run", "dhe_keysize")

	def __unicode__(self):
		return unicode(self.part_of_run) + "DHE " + unicode(self.dhe_keysize) + " bits" 
	
	def GetName(self):
		return str(self.dhe_keysize)

def _cmp_suites(x,y):
	"""Compare cipher suite names"""
	if x.startswith("SSLV2"):
		if not y.startswith("SSLV2"):
			return cmp(1,0)
	elif y.startswith("SSLV2"):
		return cmp(0,1)
	return cmp(x,y)

class CipherSuiteGroup(models.Model):
	"""List of unique groups of cipher suites"""
	cipher_suites_string = models.TextField(max_length = 1000, unique=True) 
	cipher_suites = models.ManyToManyField(ProbeDataCipher.CipherName, null=True)

	def __unicode__(self):
		return self.cipher_suites_string 

	def GetName(self):
		global _cmp_suites;
		return "%04d %s" %(self.cipher_suites.count(),  " ".join(sorted(list(self.cipher_suites.values_list("ciphername", flat=True)),cmp=_cmp_suites)))

class ResultCipherSuiteGroupEntry(models.Model):
	"""Entry for a unique group of cipher suites registered in a run"""
	
	part_of_run = models.ForeignKey(ProbeDataCipher.ProbeRun)
	cipher_suites = models.ForeignKey(CipherSuiteGroup)
	cipher_support = models.ManyToManyField(ResultCipherSuite, null=True)

	class Meta:
		unique_together=("part_of_run","cipher_suites")

	def __unicode__(self):
		return unicode(self.cipher_suites) + " "+ unicode(self.part_of_run) 

	def GetName(self):
		return self.cipher_suites.GetName()

