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

import probedb.probedata2.models as ProbeData
import probedb.resultdb2.models as Results

# Create your models here.

class UpdateBatchStatus(models.Model):
	batchname = models.CharField(max_length = 100, unique=True)
	enabled = models.BooleanField()

	def __unicode__(self):
		return "{0:s}: {1:s}".format(unicode(self.batchname), ("Active" if self.enabled else "Idle"))

	@classmethod
	def IsActive(cls, batchname = "wholebatch"):
		return bool(cls.objects.get(batchname=batchname).enabled)
