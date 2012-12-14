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

import probedb.resultdb2.condition as Results
from django.db import transaction
import time
from django.db import DatabaseError
from django.db import IntegrityError

# Create your models here.

from probedb.probedata2.proberun import *

class CipherName(models.Model):
	"""
	List of cipher suites encountered 
	"""
	
	ciphername = models.CharField(max_length = 100, unique = True, db_index=True)
	ciphervalue = models.PositiveIntegerField()

	def __unicode__(self):
		return ("0x%04x "%(self.ciphervalue)) + self.ciphername

	def GetName(self):
		return self.ciphername
