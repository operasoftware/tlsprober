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

# Create your models here.

class ProbeRunSort(models.Model):
	"""How to sort a specific run category"""
	sort_name = models.CharField(max_length = 100, db_index=True, unique = True)
	sort_rank = models.IntegerField()

	def __unicode__(self):
		return self.sort_name + " " + str(self.sort_rank) 

class ProbeRun(models.Model):
	"""
	Defines the source and description of batch run, 
	also the optional git branch to be used for the job
	"""
	date = models.DateTimeField(auto_now_add=True)
	source_name = models.CharField(max_length = 100, db_index=True)
	sort_rank = models.ForeignKey(ProbeRunSort, null=True)
	description = models.CharField(max_length=300)
	branch = models.CharField(max_length=100, null=True, blank=True)

	def __unicode__(self):
		return self.source_name + " " + self.description+ " " + str(self.date) 
