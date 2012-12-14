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

from django.db import models, connection, transaction

import random
import os
import probedb.cluster.models as Cluster
import probedb.probedata2.models as ProbeData

# Create your models here.

class ScannerNode(models.Model):
	"""Nodes for the scanner, and their parameters"""
	hostname = models.SlugField(unique=True) # name of host, non-dotted, unique
	scan_parameters = models.CharField(max_length=300) # Commandline parameters to be used with this node 
	active_node = models.BooleanField() # Is this node active
	checked_last = models.DateTimeField(auto_now = True) # Last time the node checked in; should be max 10 minutes  
	
	def __unicode__(self):
		return (self.hostname+ (" Active " if self.active_node else " Idle ") + 
				unicode(self.checked_last) + " (" + self.scan_parameters + ")" )
	
class ScannerRun(models.Model):
	"""Entry for a defining a scanner run"""
	entered_date = models.DateTimeField(auto_now_add=True)
	source_name = models.CharField(max_length = 100, db_index=True)
	description = models.CharField(max_length=300)
	enabled = models.BooleanField()
	priority = models.PositiveIntegerField()
	branch = models.CharField(max_length=100, null=True, blank=True)
	
	def __unicode__(self):
		return self.source_name + " " + self.description+ " " + str(self.entered_date) + (" Enabled" if self.enabled else " Completed" )

class ScannerAction(models.Model):
	"""the specified scanner node in the run, completed a check, at this time"""
	scanner_run = models.ForeignKey(ScannerRun,db_index=True)
	scanner_node = models.ForeignKey(ScannerNode, db_index=True)
	completed_time = models.DateTimeField(auto_now_add = True, db_index=True) # when the process on the cluster node completed an action  

class ScannerQueue(models.Model):
	"""
	List of servers and IP addresses to check, can be 
	Idle, Started or Finished
	"""
	
	part_of_run = models.ForeignKey(ScannerRun, db_index=True)
	server = models.CharField(max_length = 300)
	port = models.PositiveIntegerField()
	protocol = models.CharField(max_length = 10, choices= ProbeData.Server.PROTOCOL_LIST, db_index=True, null=True)
	
	SCANQ_IDLE = "I"
	SCANQ_STARTED = "S"
	SCANQ_FINISHED = "F"
	SCANQ_VALUES = (
		(SCANQ_IDLE,"Not started"),
		(SCANQ_STARTED,"Started"),
		(SCANQ_FINISHED,"Finished"),
					)
	state = models.CharField(max_length=1, null=True, choices=SCANQ_VALUES)

	def __unicode__(self):
		return str(self.part_of_run)+" "+str(self.state)+ " "+ self.server+":"+str(self.port)
	
	class Meta:
		unique_together=[("part_of_run", "server","port")]		

	class Queue(object):
		"""Class for managing the queue"""
		def __init__(self, run, count, performance=False):
			from threading import Lock
			self.run = run
			self.last = None
			self.lock = Lock()
			self.index = 200 + random.randint(0,50000)
			if performance:
				self.computername =  os.environ.get('COMPUTERNAME',"any").lower()
				if self.computername == "any":
					self.computername =  os.environ.get('HOSTNAME',"any").lower()
				if self.computername == "any":
					raise Exception("Computername was empty")
				self.computername = self.computername.partition('.')[0]
				scanner_node,created = ScannerNode.objects.get_or_create(hostname = self.computername, defaults={
																				"scan_parameters":"--processes 40 --iterations 40",
																				"active_node":True,
																				})
				
				assert(run and scanner_node)
				
				self.performance={"scanner_run":run, "scanner_node":scanner_node}
			else:
				self.performance= None
				self.computername = None
				
			self.list_of_items=None
			if count:
				self.__setup_iteration_list(count)
				
		def log_performance(self):
			if self.performance:
				try:
					ScannerAction.objects.create(**self.performance)
				except:
					pass

		@transaction.commit_manually
		def __get_iteration_block(self, remaining):
			"""Grab a block of scan task items"""
			try:
				cursor = connection.cursor()
				
				cursor.execute("""UPDATE scanner_scannerqueue SET "state"=E'S'
								WHERE "state" = E'I'  AND id IN (SELECT id FROM scanner_scannerqueue 
								WHERE state = E'I'  AND part_of_run_id = %s 
								LIMIT %s OFFSET %s )
								RETURNING id""", [self.run.id, remaining, self.index])
	
				rows = cursor.fetchall();
				got_items_indexes = [x[0] for x in rows]
				transaction.commit()
			except:
				transaction.rollback()
				raise
			
			return got_items_indexes;
			
				
		def __get_iteration_list(self, max_count):
			"""Grab a block of scan task items"""
			attempts = 0
			got_items_indexes =[]
			while attempts < (10  if self.index else 4) and len(got_items_indexes) < max_count:
				attempts += 1
				if self.index>=10: 
					remaining = max_count -len(self.list_of_items);
				else:
					remaining = 1

				try:
					got_items_indexes += self.__get_iteration_block(remaining)
					
					if not got_items_indexes:
						if self.index > 200:
							self.index = 10 + random.randint(0,200)
						else: 
							self.index = 0
						continue
					
				except BaseException , err:
					raise
					if got_items_indexes:
						try:
							ScannerQueue.objects.filter(id__in = got_items_indexes).update(state=ScannerQueue.SCANQ_IDLE)
						except:
							pass

					raise err

			return got_items_indexes
		
		def __setup_iteration_list(self, max_count):
			"""Grab a block of scan task items"""

			self.list_of_items = []
			got_items_indexes = self.__get_iteration_list(max_count)
			try:
				self.list_of_items += list(ScannerQueue.objects.filter(id__in = got_items_indexes))
			except:
				raise
			
		def __del__(self):
			"""Release grabbed scan task items if the object is destroyed"""
			try:
				if self.last:
					self.last.state = ScannerQueue.SCANQ_IDLE
					self.last.save()
				if self.list_of_items != None:
					for x in self.list_of_items:
						x.state = ScannerQueue.SCANQ_IDLE
						x.save()
			except:
				pass #ignore errors
		

		def __iter__(self):
			return self
		
		def IsActive(self):
			"""Is the node active? If not, cancel the actions"""
			cluster_node = None
			main_cluster_node = None
			end_run = False
			try:
				if self.last:
					self.last.state = ScannerQueue.SCANQ_FINISHED
					self.last.save()
					self.last = None
				if self.computername:
					main_cluster_node = ScannerNode.objects.get(hostname="tlsprober-cluster")
					cluster_node = ScannerNode.objects.get(hostname=self.computername)
					cluster_master_configuration = Cluster.ClusterNode.objects.get(hostname = "tlsprober-cluster")
					cluster_configuration = Cluster.ClusterNode.objects.get(hostname = self.computername)
					if (cluster_master_configuration.active_node and cluster_configuration.active_node and 
						Cluster.ClusterRun.objects.filter(enabled=True).count()>0):
						end_run = True
			except:
				pass #ignore errors
			
			if (self.computername and not (main_cluster_node and cluster_node and main_cluster_node.active_node and cluster_node.active_node)) or end_run:
				if self.list_of_items != None:
					for x in self.list_of_items:
						x.state = ScannerQueue.SCANQ_IDLE
						x.save()
				return False
			
			the_run = ScannerRun.objects.get(id=self.run.id)
			if not the_run.enabled:
				return False
			return True
		
		def next(self):
			"""Get the next task item"""
			if not self.IsActive():
				if self.list_of_items != None:
					for x in self.list_of_items:
						x.state = ScannerQueue.SCANQ_IDLE
						x.save()
				raise StopIteration
			
			if self.list_of_items != None:
				self.lock.acquire()
				if len(self.list_of_items) == 0:
					self.lock.release()
					raise StopIteration
				self.last = self.list_of_items.pop(0)
				self.lock.release()
				return (self.last.server,self.last.port, self.last.protocol) 
			raise StopIteration
		def cancel(self):
			if self.last:
				self.list_of_items.append(self.last)
			self.last = None
			

class ScannerResults(models.Model):
	"""Posotive Results from the scan (we found a server on this server:port:protool configuration"""
	part_of_run = models.ForeignKey(ScannerRun, db_index=True)
	server = models.CharField(max_length = 300)
	port = models.PositiveIntegerField()
	protocol = models.CharField(max_length = 10, choices= ProbeData.Server.PROTOCOL_LIST, db_index=True, null=True)

	def __unicode__(self):
		return str(self.part_of_run)+" "+ str(self.server)+":"+str(self.port)+ ":" + str(self.protocol if self.protocol else ProbeData.Server.PROTOCOL_HTTPS)
	
	class Meta:
		unique_together=[("part_of_run", "server","port","protocol")]		
