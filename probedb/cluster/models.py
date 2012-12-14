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
from probedb.probedata2.models import ProbeRun

# Create your models here.

class ClusterNode(models.Model):
	"""
	Identifies a node in the cluster, whether it is active, 
	and what parameters its prober script should follow
	"""
	
	hostname = models.SlugField(unique=True) # name of host, non-dotted, unique
	probe_parameters = models.CharField(max_length=300) # Commandline parameters to be used with this node 
	active_node = models.BooleanField() # Is this node active
	checked_last = models.DateTimeField(auto_now = True) # Last time the node checked in; should be max 10 minutes  
	
	def __unicode__(self):
		return (self.hostname+ (" Active " if self.active_node else " Idle ") + 
				unicode(self.checked_last) + " (" + self.probe_parameters + ")")
	
class ClusterRun(models.Model):
	"""
	Registers a batch job for the cluster
	"""
	perform_run = models.ForeignKey(ProbeRun, unique=True)
	entered_date = models.DateTimeField(auto_now_add=True)
	enabled = models.BooleanField()
	priority = models.PositiveIntegerField()
	
	def __unicode__(self):
		return (unicode(self.perform_run)+ " "+unicode(self.entered_date) + " ") + (" Enabled" if self.enabled else " Completed" )

class ClusterAction(models.Model):
	"""
	Used to register a completed server probe for a given job and node.
	
	This information is used to measure progress of the job. 
	"""
	
	cluster_run = models.ForeignKey(ClusterRun,db_index=True)
	cluster_node = models.ForeignKey(ClusterNode, db_index=True)
	completed_time = models.DateTimeField(auto_now_add = True, db_index=True) # when the process on the cluster node completed an action  
