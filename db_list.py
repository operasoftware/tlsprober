# -*- Mode: c++; tab-width: 4; indent-tabs-mode: nil; -*-
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


import libinit
from tlslite import constants
from django.db import transaction
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from probedb.probedata2.models import *
from probedb.cluster.models import *
from django.db import IntegrityError
import tlscommon.probe_server as Prober
import fileinput, re, time,os,random
from django.db import transaction
from django.db import DatabaseError
from django.db import IntegrityError
from django.db import connection
import probedb.resultdb2.models as Results
import tlscommon.ssl_v2_test as SSLv2Test
import probedb.certs.models as Certs

import probedb.certs.certhandler as certhandler


class db_list:
	"""
	Manages the queue for a given process, and inserts the results into
	the database
	""" 
	
	EV_conditions = set([
					Certs.CertificateConditions.CERTC_EXTENDED_VALIDATION_CERT, 
					Certs.CertificateConditions.CERTC_NOT_EXTENDED_VALIDATION_CERT 
					])



	def __init__(self, options, *args):
		self.debug=False
		
		self.run = None
		self.index = options.index
		self.max_count = int(options.max_tests)
		if options.small_run and self.max_count >80:
			self.max_count = 80
		self.queue_field = (150000 if options.large_run else 50000) if not options.small_run else 1000
		if options.run_id:
			self.run = ProbeRun.objects.get(id=options.run_id)
		else:
			runcandidate = ProbeRun.objects.filter(source_name=options.source_name.strip('"'), description=options.description.strip('"'), clusterrun__enabled=True).select_related("perform_run")
			if runcandidate.count() == 0:
				raise
			self.run = runcandidate.latest('date').perform_run

		self.performance = None
		if options.register_performance:
			try:
				cluster_run = ClusterRun.objects.get(perform_run=self.run)
				self.computername =  os.environ.get('COMPUTERNAME',"any").lower()
				if self.computername == "any":
					self.computername =  os.environ.get('HOSTNAME',"any").lower()
				if self.computername == "any":
					raise Exception("Computername was empty")
				self.computername = self.computername.partition('.')[0]
				cluster_node,created = ClusterNode.objects.get_or_create(hostname = self.computername, defaults={
																				"probe_parameters":"--processes 40 --iterations 40",
																				#"result_parameters":"--processes 10 --iterations 100",
																				"active_node":True,
																				})
				
				assert(cluster_run and cluster_node)
				
				self.performance={"cluster_run":cluster_run, "cluster_node":cluster_node}
								
			except:
				pass # ignore errors here
			
		self.summary_list = Results.ResultSummaryList.objects.get(part_of_run = self.run)
		self.summary_list.start()
		
		self.cipher_list={}
		self.result_cipher_list={}
		self.result_cipher_group_list={}
		self.dhekeysize_list={}
		self.primary_agent_list={}
		self.secondary_agent_list={}
		self.short_agent_list={}

	def log_performance(self):
		if self.performance:
			try:
				ClusterAction.objects.create(**self.performance)
			except:
				pass


	def get_condition_group(self, condition_group):
		
		return self.summary_list.get_condition_group(self.run, condition_group)

	def get_primary_agent(self,agent):
		if agent in self.primary_agent_list:
			return self.primary_agent_list[agent]

		#quick check to see if it is in the database already
		try:
			sid = transaction.savepoint()
			agent_rec = PrimaryServerAgent.objects.get(agent_name=agent)
			transaction.savepoint_commit(sid)
			self.primary_agent_list[agent] = agent_rec
			if agent_rec.agent_shortname not in self.short_agent_list:
				self.short_agent_list[agent_rec.agent_shortname.agent_shortname] = agent_rec.agent_shortname
				
			return agent_rec
		except:
			transaction.savepoint_rollback(sid)
			pass #ignore errors here

		major_version = 0
		minor_version = 0
		patch_version = 0
		if not agent.startswith("(") and agent.find("/") >=0 :
			(agent_shortname, sep, ver) = agent.partition("/")
			versions = ver.split(".")
			if len(versions) >= 1:
				major_version = versions[0]
				if len(versions) >1:
					minor_version = versions[1]
					if len(versions) >2:
						patch_version = versions[2]
		else:
			agent_shortname = agent
		agent_shortname_rec = self.get_short_agent(agent_shortname)
		while True:
			try:
				sid = transaction.savepoint()
				(agent_rec, created) = PrimaryServerAgent.objects.get_or_create(
										agent_name=agent,
										defaults = {"agent_shortname":agent_shortname_rec,
													"major_version":major_version, 
													"minor_version":minor_version,
													"patch_version":patch_version})
				transaction.savepoint_commit(sid)
				self.primary_agent_list[agent] = agent_rec
				return agent_rec
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue

	def get_secondary_agent(self,agent):
		if agent in self.secondary_agent_list:
			return self.secondary_agent_list[agent]

		#quick check to see if it is in the database already
		try:
			sid = transaction.savepoint()
			agent_rec = SecondaryServerAgent.objects.get(agent_name=agent)
			transaction.savepoint_commit(sid)
			self.secondary_agent_list[agent] = agent_rec
			if agent_rec.agent_shortname not in self.short_agent_list:
				self.short_agent_list[agent_rec.agent_shortname.agent_shortname] = agent_rec.agent_shortname
			return agent_rec
		except:
			transaction.savepoint_rollback(sid)
			pass #ignore errors here

		major_version = 0
		minor_version = 0
		patch_version = 0
		if not agent.startswith("(") and agent.find("/") >=0 :
			(agent_shortname, sep, ver) = agent.partition("/")
			versions = ver.split(".")
			if len(versions) >= 1:
				major_version = versions[0]
				if len(versions) >1:
					minor_version = versions[1]
					if len(versions) >2:
						patch_version = versions[2]
		else:
			agent_shortname = agent
		agent_shortname_rec = self.get_short_agent(agent_shortname)
		while True:
			try:
				sid = transaction.savepoint()
				(agent_rec, created) = SecondaryServerAgent.objects.get_or_create(
										agent_name=agent,
										defaults = {"agent_shortname":agent_shortname_rec,
													"major_version":major_version, 
													"minor_version":minor_version,
													"patch_version":patch_version})
				transaction.savepoint_commit(sid)
				self.secondary_agent_list[agent] = agent_rec
				return agent_rec
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
		
	def get_short_agent(self,agent):
		if agent in self.short_agent_list:
			return self.short_agent_list[agent]
		while True:
			try:
				sid = transaction.savepoint()
				(agent_rec, created) = AgentShortName.objects.get_or_create(
										agent_shortname = agent)
				transaction.savepoint_commit(sid)
				self.short_agent_list[agent] = agent_rec
				return agent_rec
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break

	def get_specific_intolerance(self,extension):
		return CommonSpecificExtensionIntolerance.FetchOrCreate(extension)
	
	def get_cipher(self,ciphername):
		if ciphername in self.cipher_list:
			return self.cipher_list[ciphername]
		cipherid = constants.CipherSuite.fromText.get(ciphername,0)
		while True:
			try:
				sid = transaction.savepoint()
				(cipher_entry, created) = CipherName.objects.get_or_create(
										ciphername=ciphername,
										defaults={"ciphervalue":cipherid})
				transaction.savepoint_commit(sid)
				self.cipher_list[ciphername] = cipher_entry
				return cipher_entry;
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;

	def get_v2cipher(self,ciphername):
		if ciphername in self.cipher_list:
			return self.cipher_list[ciphername]
		cipherid = SSLv2Test.SSLv2_ClientHello.SSL_v2_CIPHERS_fromText.get(ciphername,0)
		while True:
			try:
				sid = transaction.savepoint()
				(cipher_entry, created) = CipherName.objects.get_or_create(
										ciphername=ciphername,
										defaults={"ciphervalue":cipherid})
				transaction.savepoint_commit(sid)
				self.cipher_list[ciphername] = cipher_entry
				return cipher_entry;
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;

	def get_result_cipher(self,cipher):
		if cipher.id in self.result_cipher_list:
			return self.result_cipher_list[cipher.id]
		while True:
			try:
				sid = transaction.savepoint()
				cipher_entry,created = Results.ResultCipherSuite.objects.get_or_create(part_of_run=self.run, 
																cipher_name = cipher)
				if created:
					self.summary_list.CipherSuiteEntries.add(cipher_entry)
				
				transaction.savepoint_commit(sid)
				self.result_cipher_list[cipher.id] = cipher_entry
				return cipher_entry;
										
			except AssertionError,error:
				print str(error)
				raise
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;

	def get_result_cipher_group(self,cipher_list):
		ciph_idlist = " ".join(["%04x"%(c,) for c in sorted([ciph.ciphervalue for ciph in cipher_list])])
		if ciph_idlist in self.result_cipher_group_list:
			return self.result_cipher_list[ciph_idlist]

		result_cipher_list = [self.get_result_cipher(ciph) for ciph in cipher_list]

		while True:
			try:
				sid = transaction.savepoint()
				group, created= Results.CipherSuiteGroup.objects.get_or_create(cipher_suites_string = ciph_idlist)
				if created:
					group.cipher_suites.add(*cipher_list)
					#group.save()
				transaction.savepoint_commit(sid)
			except AssertionError,error:
				print str(error)
				raise
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				continue;
			break;

		while True:
			try:
				sid = transaction.savepoint()
				suite_list, created = Results.ResultCipherSuiteGroupEntry.objects.get_or_create(cipher_suites = group, 
																			part_of_run=self.run 
															)
				if created:
					suite_list.cipher_support.add(*result_cipher_list)
					self.summary_list.CipherSuiteGroupEntries.add(suite_list)
				transaction.savepoint_commit(sid)
				self.result_cipher_list[ciph_idlist] = suite_list
				return suite_list;
			except AssertionError,error:
				print str(error)
				raise
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;
		
	def get_dhekeysize(self,dhe_keylen):
		if dhe_keylen in self.dhekeysize_list:
			return self.dhekeysize_list[dhe_keylen]

		while True:
			try:
				sid = transaction.savepoint()
				dhe_keysize,created = Results.ResultDHEKeySize.objects.get_or_create(part_of_run=self.run, 
																dhe_keysize = dhe_keylen)
				if created:
					self.summary_list.dhe_keysizes.add(dhe_keysize)
				transaction.savepoint_commit(sid)
				self.dhekeysize_list[dhe_keylen] = dhe_keysize
				return dhe_keysize
			except AssertionError,error:
				print str(error)
				raise
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			break;
	
	@transaction.commit_on_success
	def __del__(self):
		pass
	
	class Queue:
		"""Iterator for pending tasks"""
		def __init__(self, source):
			self.run = source.run
			self.last = None
			self.index = 200 + random.randint(0,source.queue_field)
			if source.performance:
				self.computername = source.computername
			else:
				self.computername = None
				
			self.list_of_items=None
			if source.max_count:
				self.__setup_iteration_list(source.max_count)
				
		@transaction.commit_manually
		def __get_iteration_block(self, remaining):
			try:
				cursor = connection.cursor()
				cursor.execute("""SELECT id FROM probedata2_probequeue 
								WHERE state = E'I'  AND part_of_run_id = %s 
								LIMIT %s OFFSET %s""", [self.run.id, remaining, self.index])
				
				rows = cursor.fetchall();
				id_list = ", ".join(["%d" %(int(x[0]),) for x in rows])
				
				if not id_list:
					return []
				
				cursor.execute("""UPDATE probedata2_probequeue SET "state"=E'S'
								WHERE "state" = E'I'  AND id IN ("""+ 
								id_list + 
								""")
								RETURNING id""")
	
				rows = cursor.fetchall();
				got_items_indexes = [x[0] for x in rows]
				transaction.commit()
			except:
				transaction.rollback()
				raise
			
			return got_items_indexes;
			
				
		def __get_iteration_list(self, max_count):
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
					if got_items_indexes:
						try:
							ProbeQueue.objects.filter(id__in = got_items_indexes).update(state=ProbeQueue.PROBEQ_IDLE)
						except:
							pass

					raise err

			return got_items_indexes
		
		def __setup_iteration_list(self, max_count):
			self.list_of_items = []
			got_items_indexes = self.__get_iteration_list(max_count)
			try:
				self.list_of_items += list(ProbeQueue.objects.filter(id__in = got_items_indexes))
			except:
				raise
			
		def __del__(self):
			try:
				if self.last:
					self.last.state = ProbeQueue.PROBEQ_FINISHED
					self.last.save()
				if self.list_of_items != None:
					for x in self.list_of_items:
						x.state = ProbeQueue.PROBEQ_IDLE
						x.save()
			except:
				pass #ignore errors
		

		def __iter__(self):
			return self
		def next(self):
			cluster_node = None
			main_cluster_node = None
			try:
				if self.last:
					self.last.state = ProbeQueue.PROBEQ_FINISHED
					self.last.save()
					self.last = None
				if self.computername:
					main_cluster_node = ClusterNode.objects.get(hostname="tlsprober-cluster")
					cluster_node = ClusterNode.objects.get(hostname=self.computername)
			except:
				pass #ignore errors
			if self.computername and not (main_cluster_node and cluster_node and main_cluster_node. active_node and cluster_node.active_node):
				if self.list_of_items != None:
					for x in self.list_of_items:
						x.state = ProbeQueue.PROBEQ_IDLE
						x.save()
				raise StopIteration
			
			if self.list_of_items != None:
				if len(self.list_of_items) == 0:
					raise StopIteration
				self.last = self.list_of_items.pop(0)
				return self.last.server 
			raise StopIteration
		
	def GetQueue(self):
		return db_list.Queue(self)

	def print_probe(self, prober):
		"""Insert the prober results into the database for this server"""
		
		server = prober.servername_item
	
		cert_status_b64 = None
		
		if prober.certificate_status:
			b64_cert_status =base64.b64encode(prober.certificate_status)
			cert_status_b64 = "\n".join([b64_cert_status[i:min(i+64, len(b64_cert_status))] for i in range(0,len(b64_cert_status),64)]) 

		results = {
					"servername": server,
					"part_of_run": self.run,
					"serveragent_string": "N/A",
					"cert_status_response_b64": cert_status_b64, 
					"used_dhe_key_size": prober.dhe_keysize,
					}
					
		global_flags = set(
				([Results.ResultCondition.RESULTC_VERSIONMIRROR if any([x not in prober.supported_versions for x in prober.detected_versions]) else Results.ResultCondition.RESULTC_VERSIONCORRECT])+
				([Results.ResultCondition.RESULTC_CLVERSIONSWAP if prober.detected_ch_version_swap else Results.ResultCondition.RESULTC_CLVERSIONCORRECT])+
				([Results.ResultCondition.RESULTC_CLVERSIONRECMATCH if prober.detected_ch_rec_sameversion else Results.ResultCondition.RESULTC_CLRECVERSIONCORRECT])+
				([Results.ResultCondition.RESULTC_PROBLEM_EXTRAPADDING if prober.extra_padding_problems else Results.ResultCondition.RESULTC_NOPROBLEM_EXTRAPADDING])+
				
				([Results.ResultCondition.RESULTC_RENEGO if prober.have_renego else Results.ResultCondition.RESULTC_NONRENEGO])+
				([Results.ResultCondition.RESULTC_RENEGOUNSTABLE if prober.renego_unstable else Results.ResultCondition.RESULTC_RENEGOSTABLE] if prober.have_renego else [])+
				([Results.ResultCondition.RESULTC_RENEGOEXTSCSV_ACCEPT if prober.accepted_renego_ext_and_scsv else Results.ResultCondition.RESULTC_RENEGOEXTSCSV_INTOL] if prober.have_renego else [])+
			 	([Results.ResultCondition.RESULTC_ACCEPT_FAKE_START_RENEGO if prober.accepted_start_fake_renego else Results.ResultCondition.RESULTC_REFUSE_FAKE_START_RENEGO] if prober.have_renego else []) +
				
				([Results.ResultCondition.RESULTC_SENT_SNI_EXT if prober.have_SNI else Results.ResultCondition.RESULTC_NO_SNI_EXT])+
				([Results.ResultCondition.RESULTC_SENT_SNI_WARN if prober.sent_SNI_Alert else Results.ResultCondition.RESULTC_NO_SNI_WARN])+
				([Results.ResultCondition.RESULTC_SENT_CERT_STATUS if cert_status_b64  else Results.ResultCondition.RESULTC_NO_CERT_STATUS])+
				([Results.ResultCondition.RESULTC_REVERSED_EXTENSION_INTOLERANT] if prober.reversed_extension_intolerance else [])+
				
				([Results.ResultCondition.RESULTC_TOLERATE_SSLV2HAND if prober.tolerate_ssl_v2 else Results.ResultCondition.RESULTC_NOTOLERATE_SSLV2HAND])+
				([Results.ResultCondition.RESULTC_SUPPORT_WEAK_CIPHER if prober.support_weak_ciphers else Results.ResultCondition.RESULTC_NOSUPPORT_WEAK_CIPHER])+
				([Results.ResultCondition.RESULTC_SSLV2_WEAK_CIPHER if prober.support_v2_export_ciphers else Results.ResultCondition.RESULTC_SSLV2_NOWEAK_CIPHER])+
				([Results.ResultCondition.RESULTC_SUPPORT_DEPRECATED_CIPHER if prober.selected_deprecated_cipher else Results.ResultCondition.RESULTC_NOSUPPORT_DEPRECATED_CIPHER])+
				([Results.ResultCondition.RESULTC_SUPPORT_TOONEW_CIPHER if prober.selected_cipher_later_version else Results.ResultCondition.RESULTC_NOSUPPORT_TOONEW_CIPHER])+

				([Results.ResultCondition.RESULTC_RESUMABLE_SESSIONS if prober.resumable_session else Results.ResultCondition.RESULTC_NONRESUMABLE_SESSIONS] if prober.tested_session else [])+
				([Results.ResultCondition.RESULTC_RESUME_SESSION if prober.resumed_session else Results.ResultCondition.RESULTC_NORESUME_SESSION] if prober.tested_session else [])+
				([Results.ResultCondition.RESULTC_RESUME_SESSION_OVER] if prober.resumed_session_with_original else [])+
				([Results.ResultCondition.RESULTC_NEW_SESSION_OVER] if prober.new_session_with_original else [])+
				([Results.ResultCondition.RESULTC_FAIL_RESUME_SESSION_OVER] if prober.fail_resumed_session_with_original else [])+

				([Results.ResultCondition.RESULTC_SENT_SESSION_TICKETS if prober.sent_session_ticket else Results.ResultCondition.RESULTC_NOSEND_SESSION_TICKETS])+
				([Results.ResultCondition.RESULTC_RESUMED_SESSION_TICKETS if prober.resumed_session_ticket else Results.ResultCondition.RESULTC_NORESUME_SESSION_TICKETS] if prober.sent_session_ticket else [])+

				
				([Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_SSLV2] if prober.supported_versions and max(prober.supported_versions) == (2,0) else [])+
				([Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_SSLV3] if prober.supported_versions and max(prober.supported_versions) == (3,0) else [])+
				([Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_0] if prober.supported_versions and max(prober.supported_versions) == (3,1) else [])+
				([Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_1] if prober.supported_versions and max(prober.supported_versions) == (3,2) else [])+
				([Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_TLS_1_2] if prober.supported_versions and max(prober.supported_versions) == (3,3) else [])+
				
				([Results.ResultCondition.RESULTC_CLIENT_CERT_REQUEST if prober.clientcertificate_requested else Results.ResultCondition.RESULTC_NOCLIENT_CERT_REQUEST]) +

				([Results.ResultCondition.RESULTC_CLIENT_CERT_REQUIRED if prober.clientcertificate_required else Results.ResultCondition.RESULTC_NOCLIENT_CERT_ACCEPTED] if prober.clientcertificate_requested else []) +
				([Results.ResultCondition.RESULTC_NOCLIENT_CERT_ALERT if prober.clientcertificate_required else Results.ResultCondition.RESULTC_NOCLIENT_CERT_NORMAL] if  prober.clientcertificate_requested and prober.clientcertificate_required else []) +

				([Results.ResultCondition.RESULTC_ASKED_RENEGO if prober.requested_renegotiation else Results.ResultCondition.RESULTC_NOASK_RENEGO]) +
				([Results.ResultCondition.RESULTC_ACCEPT_RENEGO if prober.accepted_renegotiation else Results.ResultCondition.RESULTC_NOACCEPT_RENEGO]) +
				((
				 ([Results.ResultCondition.RESULTC_ACCEPT_FAKE_RENEGO if prober.accepted_renegotiation_fake_renego else Results.ResultCondition.RESULTC_REFUSE_FAKE_RENEGO] if prober.have_renego else []) +
				 ([Results.ResultCondition.RESULTC_ACCEPT_HIGH_PREM if prober.accepted_renegotiation_higher_premaster else Results.ResultCondition.RESULTC_NOACCEPT_HIGH_PREM]) +
				 ([Results.ResultCondition.RESULTC_ACCEPT_EHIGH_PREM if prober.accepted_renegotiation_even_higher_premaster else Results.ResultCondition.RESULTC_NOACCEPT_EHIGH_PREM])+
				 ([Results.ResultCondition.RESULTC_COMLETED_REFUSED_RENEGO if prober.completed_renegotiation else Results.ResultCondition.RESULTC_NOTCOMLETED_REFUSED_RENEGO] if prober.completed_renegotiation != None else [])+
				  [Results.ResultCondition.RESULTC_PERFORM_RENEGO]) if prober.requested_renegotiation or prober.accepted_renegotiation else [Results.ResultCondition.RESULTC_NOPERFORM_RENEGO]) +

				#new lines above
				list(prober.test_results)
			)

		if prober.accept_false_start != None:
			global_flags.add(Results.ResultCondition.RESULTC_FALSE_START_TESTED)
			global_flags.add(Results.ResultCondition.RESULTC_FALSE_START_ACCEPTED if prober.accept_false_start else Results.ResultCondition.RESULTC_FALSE_START_FAILED)
		else:
			global_flags.add(Results.ResultCondition.RESULTC_FALSE_START_NOTTESTED)

		if prober.working_part_record != None:
			global_flags.add(Results.ResultCondition.RESULTC_PARTREC_TESTED)
			have_passed = False
			have_failed = False
			for s, p, f in [
						(0, Results.ResultCondition.RESULTC_PARTREC_PASSED_0, Results.ResultCondition.RESULTC_PARTREC_FAILED_0),
						(1, Results.ResultCondition.RESULTC_PARTREC_PASSED_1, Results.ResultCondition.RESULTC_PARTREC_FAILED_1),
						(2, Results.ResultCondition.RESULTC_PARTREC_PASSED_2, Results.ResultCondition.RESULTC_PARTREC_FAILED_2),
						(-1, Results.ResultCondition.RESULTC_PARTREC_PASSED_L1, Results.ResultCondition.RESULTC_PARTREC_FAILED_L1),
						(-2, Results.ResultCondition.RESULTC_PARTREC_PASSED_L2, Results.ResultCondition.RESULTC_PARTREC_FAILED_L2),
						]:
				passed = s in prober.working_part_record
				if passed:
					have_passed = True
				else:
					have_failed = True
					
				global_flags.add(p if passed else f)
			if have_passed:
				global_flags.add(Results.ResultCondition.RESULTC_PARTREC_PASSED_SOME if have_failed else Results.ResultCondition.RESULTC_PARTREC_PASSED_ALL)
				if have_failed:
					global_flags.add(Results.ResultCondition.RESULTC_PARTREC_FAILED_SOME)
					global_flags.add(Results.ResultCondition.RESULTC_PARTREC_FAILED)
			else:
				global_flags.add(Results.ResultCondition.RESULTC_PARTREC_FAILED_ALL)
				global_flags.add(Results.ResultCondition.RESULTC_PARTREC_FAILED)
		else: 
			global_flags.add(Results.ResultCondition.RESULTC_PARTREC_NOTTESTED)
	
		if prober.working_part_record_collect != None:
			global_flags.add(Results.ResultCondition.RESULTC_PARTREC2_TESTED)
			have_passed = False
			have_failed = False
			for s, p, f in [
						(0, Results.ResultCondition.RESULTC_PARTREC2_PASSED_0, Results.ResultCondition.RESULTC_PARTREC2_FAILED_0),
						(1, Results.ResultCondition.RESULTC_PARTREC2_PASSED_1, Results.ResultCondition.RESULTC_PARTREC2_FAILED_1),
						(2, Results.ResultCondition.RESULTC_PARTREC2_PASSED_2, Results.ResultCondition.RESULTC_PARTREC2_FAILED_2),
						(-1, Results.ResultCondition.RESULTC_PARTREC2_PASSED_L1, Results.ResultCondition.RESULTC_PARTREC2_FAILED_L1),
						(-2, Results.ResultCondition.RESULTC_PARTREC2_PASSED_L2, Results.ResultCondition.RESULTC_PARTREC2_FAILED_L2),
						]:
				passed = s in prober.working_part_record_collect
				if passed:
					have_passed = True
				else:
					have_failed = True
					
				global_flags.add(p if passed else f)
			if have_passed:
				global_flags.add(Results.ResultCondition.RESULTC_PARTREC2_PASSED_SOME if have_failed else Results.ResultCondition.RESULTC_PARTREC2_PASSED_ALL)
				if have_failed:
					global_flags.add(Results.ResultCondition.RESULTC_PARTREC2_FAILED_SOME)
					global_flags.add(Results.ResultCondition.RESULTC_PARTREC2_FAILED)
			else:
				global_flags.add(Results.ResultCondition.RESULTC_PARTREC2_FAILED_ALL)
				global_flags.add(Results.ResultCondition.RESULTC_PARTREC2_FAILED)
		else: 
			global_flags.add(Results.ResultCondition.RESULTC_PARTREC2_NOTTESTED)
	
		intolerant_for_extension_list = []		
		if prober.intolerant_for_extension and sorted(prober.intolerant_for_extension) != sorted(Prober.ProbeServer.EXTENSION_SET_LIST_CHECKED):
			intolerant_for_extension_list = [self.get_specific_intolerance("+".join(sorted(x))) for x in prober.intolerant_for_extension]
			global_flags.add(Results.ResultCondition.RESULTC_INTOLERANT_SPECIFIC_EXTENSION)
		else:
			global_flags.add(Results.ResultCondition.RESULTC_NOINTOLERANT_SPECIFIC_EXTENSION)

		major_flag = {3:set(global_flags), 4:set(global_flags)}

		global_flags.update(set(
				([Results.ResultCondition.RESULTC_SUPPORT_SSLV2 if (2,0) in prober.supported_versions else Results.ResultCondition.RESULTC_NOSUPPORT_SSLv2])+
				([Results.ResultCondition.RESULTC_SUPPORT_SSLV2_NO_CIPHER  if not prober.support_v2_ciphers else Results.ResultCondition.RESULTC_SUPPORT_SSLV2_CIPHERS] if (2,0) in prober.supported_versions else [])+
				([Results.ResultCondition.RESULTC_SUPPORT_SSLV3 if (3,0) in prober.supported_versions else Results.ResultCondition.RESULTC_NOSUPPORT_SSLv3])+
				([Results.ResultCondition.RESULTC_SUPPORT_TLS_1_0 if (3,1) in prober.supported_versions else Results.ResultCondition.RESULTC_NOSUPPORT_TLS_1_0])+
				([Results.ResultCondition.RESULTC_SUPPORT_TLS_1_1 if (3,2) in prober.supported_versions else Results.ResultCondition.RESULTC_NOSUPPORT_TLS_1_1])+
				([Results.ResultCondition.RESULTC_SUPPORT_TLS_1_2 if (3,3) in prober.supported_versions else Results.ResultCondition.RESULTC_NOSUPPORT_TLS_1_2])+
				([Results.ResultCondition.RESULTC_SUPPORT_SSL_TLS] if any([(3,x) in prober.supported_versions for x in [0,1,2,3]]) else [])
			))
				
		
		ver_resultlist = {3:{}, 4:{}}
		records = []
		result_list = {}
		rec_seen = set()
		
		for (mode_source, result_cand) in [
				(prober.non_compliant_modes, ProbeResultEntry.PROBE_NON_COMPLIANT),
				(prober.failed_modes, ProbeResultEntry.PROBE_FAILED),
				(prober.passed_modes, ProbeResultEntry.PROBE_PASSED),
				]:
			for x in mode_source:
				if "long_text" in x:
					fail_text = x["long_text"]
				else:
					fail_text = " ".join([y for (n,y) in x.iteritems() if n.endswith("-error")])
				if not fail_text:
					fail_text = ""
				ver = x["version"]
				ext = x["extensions"]
				bad = x["bad_version"]
				
				temp = str((ver,ext,bad))
				if temp in rec_seen:
					continue
				rec_seen.add(temp)
				
				r ={		
					"servername": server,
					"part_of_run": self.run,
					"version_major":ver[0],
					"version_minor":ver[1],
					"negotiated_version_major":0,
					"negotiated_version_minor":0,
					"extensions":ext,
					"badversion":bad,
					"result":result_cand,
					"result_non_bad":ProbeResultEntry.PROBE_UNTESTED,
					"error_string":fail_text
					}
				if not ext:
					if bad:
						if ver[1] in ver_resultlist[ver[0]]:
							r["result_non_bad"] = ver_resultlist[ver[0]][ver[1]]["result"]
							del ver_resultlist[ver[0]][ver[1]]
						else:
							ver_resultlist[ver[0]][ver[1]]= r
					else:
						if ver[1] in ver_resultlist[ver[0]]:
							ver_resultlist[ver[0]][ver[1]]["result_non_bad"] = r["result"]
						else:
							ver_resultlist[ver[0]][ver[1]]= r

				version_tolerant = True
				extension_tolerant = True
				bad_version = False
				bad_check = False
				
				if result_cand == ProbeResultEntry.PROBE_NON_COMPLIANT or result_cand == ProbeResultEntry.PROBE_FAILED:
					has_bad_check = False
					if bad and any([True for x1 in prober.passed_modes if x1["version"] >= ver and x1["extensions"] == False and x1["bad_version"] == False]):
						has_bad_check = True
					if has_bad_check:
						if ver > (3,0):
							bad_check = True
					elif bad:
						bad_version = True
					elif ext:
						extension_tolerant = False
					elif ver > (3,0):
						version_tolerant = False
							
				flags = set()
	
				if ver in prober.supported_versions: 
					if ver == (3,0):
						flags.add(Results.ResultCondition.RESULTC_SUPPORT_SSLV3)
					elif ver == (3,1):
						flags.add(Results.ResultCondition.RESULTC_SUPPORT_TLS_1_0)
					elif ver == (3,2):
						flags.add(Results.ResultCondition.RESULTC_SUPPORT_TLS_1_1)
					elif ver == (3,3):
						flags.add(Results.ResultCondition.RESULTC_SUPPORT_TLS_1_2)
				else:
					if ver == (3,0):
						flags.add(Results.ResultCondition.RESULTC_NOSUPPORT_SSLv3)
					elif ver == (3,1):
						flags.add(Results.ResultCondition.RESULTC_NOSUPPORT_TLS_1_0)
					elif ver == (3,2):
						flags.add(Results.ResultCondition.RESULTC_NOSUPPORT_TLS_1_1)
					elif ver == (3,3):
						flags.add(Results.ResultCondition.RESULTC_NOSUPPORT_TLS_1_2)
				
				if not version_tolerant:
					flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT)
				
				if not extension_tolerant:
					flags.add(Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT)
				
				if bad_version:
					flags.add(Results.ResultCondition.RESULTC_BADVERSION)
				
				if bad_check:
					flags.add(Results.ResultCondition.RESULTC_NOVERSION)
	
				if Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT in flags:
					flags.add(Results.ResultCondition.RESULTC_VEROREXT_INTOLERANT)
					if Results.ResultCondition.RESULTC_VERSION_INTOLERANT in flags:
						flags.add(Results.ResultCondition.RESULTC_VERANDEXT_INTOLERANT)
						flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT3 if ver[0] == 3 else
								Results.ResultCondition.RESULTC_VERSION_INTOLERANT4)
						if ver <= (3,3):
							flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT_CURRENT3)
						elif ver < (4,0):
							flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT_FUTURE3)
					flags.add(Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT30 if ver == (3,0) else
							Results.ResultCondition.RESULTC_EXTENSION_INTOLERANTX)
					if  ver> (3,0) and ver<=(3,3): # TLS 1.0 to TLS 1.2
						flags.add(Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT_C3)
				elif Results.ResultCondition.RESULTC_VERSION_INTOLERANT in flags:
					flags.add(Results.ResultCondition.RESULTC_VEROREXT_INTOLERANT)
					flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT3 if ver[0] == 3 else
							Results.ResultCondition.RESULTC_VERSION_INTOLERANT4)
					if ver <= (3,3):
						flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT_CURRENT3)
					elif ver < (4,0):
						flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT_FUTURE3)
	
				global_flags.update(flags)
				
				major_flag[ver[0]].update(flags)
				
				r["flags"] = set(flags)
				index = str(ver) 
				if index in result_list:
					result_list[index][1].update(flags)
				else:
					result_list[index] = (ver, set(flags))

				records.append(r)

		for (idx, item) in result_list.iteritems():
			ver = item[0]
			flags = set(item[1])
			if (Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT in flags and
				Results.ResultCondition.RESULTC_VERSION_INTOLERANT in flags):
				flags.add(Results.ResultCondition.RESULTC_VERANDEXT_INTOLERANT)
				flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT3 if ver[0] == 3 else
						Results.ResultCondition.RESULTC_VERSION_INTOLERANT4)
				if ver <= (3,3):
					flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT_CURRENT3)
				elif ver < (4,0):
					flags.add(Results.ResultCondition.RESULTC_VERSION_INTOLERANT_FUTURE3)

			global_flags.update(flags)
			
			major_flag[ver[0]].update(flags)


			if Results.ResultCondition.RESULTC_VERSION_INTOLERANT not in flags:
				flags.add(Results.ResultCondition.RESULTC_VERSION_TOLERANT) 

			if Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT not in flags:
				flags.add(Results.ResultCondition.RESULTC_EXTENSION_TOLERANT)

			if Results.ResultCondition.RESULTC_BADVERSION not in flags:
				flags.add(Results.ResultCondition.RESULTC_GOODVERSION)

			if Results.ResultCondition.RESULTC_NOVERSION not in flags:
				flags.add(Results.ResultCondition.RESULTC_VERSIONCHECK)

			flags.add(Results.ResultCondition.RESULTC_NON_COMPLIANT if flags & Results.ResultCondition.RESULT_PROBLEMLIST else
					 Results.ResultCondition.RESULTC_COMPLIANT)

			result_list[idx][1].update(flags)


		if Results.ResultCondition.RESULTC_VERSION_INTOLERANT not in global_flags:
			global_flags.add(Results.ResultCondition.RESULTC_VERSION_TOLERANT) 
		
		if Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT not in global_flags:
			global_flags.add(Results.ResultCondition.RESULTC_EXTENSION_TOLERANT) 
		
		if (Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT30 in global_flags and
			Results.ResultCondition.RESULTC_EXTENSION_INTOLERANTX in global_flags):
			global_flags.discard(Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT30)
			major_flag[3].discard(Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT30)
			result_list[str((3,0))][1].discard(Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT30)
			result_list[str((3,0))][1].add(Results.ResultCondition.RESULTC_EXTENSION_INTOLERANTX)

		if Results.ResultCondition.RESULTC_BADVERSION not in global_flags:
			global_flags.add(Results.ResultCondition.RESULTC_GOODVERSION)

		if Results.ResultCondition.RESULTC_NOVERSION not in global_flags:
			global_flags.add(Results.ResultCondition.RESULTC_VERSIONCHECK)

		global_flags |= Results.ResultCondition.GetComplianceFlags(global_flags)
		major_flag[3] |= Results.ResultCondition.GetComplianceFlags(major_flag[3])
		major_flag[4] |= Results.ResultCondition.GetComplianceFlags(major_flag[4])
		
		if Results.ResultCondition.RESULTC_NON_COMPLIANT in major_flag[3]:
			major_flag[3].add(Results.ResultCondition.RESULTC_NON_COMPLIANTv3)
			global_flags.add(Results.ResultCondition.RESULTC_NON_COMPLIANTv3)
		if Results.ResultCondition.RESULTC_NON_COMPLIANT in major_flag[4]:
			major_flag[3].add(Results.ResultCondition.RESULTC_NON_COMPLIANTv4)
			global_flags.add(Results.ResultCondition.RESULTC_NON_COMPLIANTv4)
		
		if Results.ResultCondition.RESULTC_RENEGONONCOMPLIANT in major_flag[3]:
			major_flag[3].add(Results.ResultCondition.RESULTC_RENEGONONCOMPLIANTv3)
			global_flags.add(Results.ResultCondition.RESULTC_RENEGONONCOMPLIANTv3)
		if Results.ResultCondition.RESULTC_RENEGONONCOMPLIANT in major_flag[4]:
			major_flag[3].add(Results.ResultCondition.RESULTC_RENEGONONCOMPLIANTv4)
			global_flags.add(Results.ResultCondition.RESULTC_RENEGONONCOMPLIANTv4)

		ip_entries = []
		while True:
			try:
				for ip in prober.ip_addresses:
					while True:
						produce_entry = False
						try:
							ip_entry = IP_Address.objects.extra(where=['"probedata2_ip_address"."ip_address" = INET(E\''+ip+'\')'])[0]
						except IP_Address.DoesNotExist:
							produce_entry =True
						except IndexError:
							produce_entry =True
						try:
							sid = transaction.savepoint()
							if produce_entry:
								ip_entry = IP_Address.objects.create(ip_address=ip);
								ip_entry.Construct()
								produce_entry = False
							ip_entries.append(ip_entry)
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
						
			except IntegrityError:
				continue
			break;

		ciphlist = [self.get_cipher(ciphername) for ciphername in prober.ciphers_supported]
		ciphlist += [self.get_v2cipher(ciphername) for ciphername in prober.support_v2_ciphers]

		suite_list = self.get_result_cipher_group(ciphlist)

		dhe_keysize = self.get_dhekeysize(prober.dhe_keysize)
		
		primary_agent = None
		secondary_agent_list = []
		if prober.server_agent and prober.server_agent.strip():
			if any([x>127 for x in prober.server_agent]):
				prober.server_agent = "".join([x if ord(x)<128 else "\\%02x"%(ord(x),) for x in prober.server_agent])
			results["serveragent_string"] = prober.server_agent
			server_items1 = re.split("(\s+|[\(\)])", prober.server_agent)
			#prober.server_agent.split()
			server_items = []
			val = server_items1.pop(0)
			if val:
				server_items.append(val)
			while server_items1:
				sep = server_items1.pop(0)
				if not server_items1:
					continue
				val = server_items1.pop(0)
				if sep == '(':
					par = 1
					val = sep+ val;
					while par > 0 and server_items1:
						if server_items1[0] == ')' and par == 1:
							val += server_items1[0];
							par -= 1;
							continue
						
						sep = server_items1.pop(0)
						if server_items1:
							val1 = server_items1.pop(0)
						if sep == '(':
							par += 1
						elif sep == ')':
							par -= 1
						
						val += sep + val1

				if val:	
					server_items.append(val)
		else:
			server_items=["N/A"]
			
		primary_agent = self.get_primary_agent(server_items[0]);
		results["primary_agent"] = primary_agent
		
		if len(server_items)>1:
			secondary_agent_list = [self.get_secondary_agent(agentname) for agentname in server_items]
			
		(primary_agent2, primary_short_agent) = self.summary_list.GetResultAgents(
													primary_agent, 
													Results.ResultPrimaryServerAgent, 
													Results.ResultPrimaryServerAgentFamily,
													PrimaryServerAgent)
		while True:
			try:
				sid = transaction.savepoint()
				self.summary_list.PrimaryServerAgentSummary.add(primary_agent2)
				self.summary_list.PrimaryShortServerAgentSummary.add(primary_short_agent)
			except DatabaseError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			except IntegrityError:
				transaction.savepoint_rollback(sid)
				time.sleep(0.1)
				continue
			transaction.savepoint_commit(sid)
			break;

		short_list = []
		agent_list = []		
		for agent in  secondary_agent_list:
			(secondary_agent, secondary_short_agent) = self.summary_list.GetResultAgents(agent, 
													Results.ResultSecondaryServerAgent, Results.ResultSecondaryServerAgentFamily,SecondaryServerAgent)
			if secondary_agent not in agent_list:
				agent_list.append(secondary_agent)
			if secondary_short_agent not in short_list:
				short_list.append(secondary_short_agent)

		cert_list = []
		cert_seq_list = [] 				
		if isinstance(prober.certificates, dict):
			first_cert_set = False
			cert_item = 0;
			for x in prober.certificates["certificate_list"]:
				condition_list = set()
				cert_item +=1
				fingerprint = x["finger-print"]
				while True:
					try:
						sid = transaction.savepoint()
						(cert_rec, created) = Certificate.objects.get_or_create(
											sha256_fingerprint=fingerprint,
											defaults={"certificate_b64":"", "self_signed":False})
					except DatabaseError:
						transaction.savepoint_rollback(sid)
						time.sleep(0.1)
						continue
					except IntegrityError:
						transaction.savepoint_rollback(sid)
						time.sleep(0.1)
						continue
					transaction.savepoint_commit(sid)
					break
				if created:
					cert_rec.SetCertificate(x["binary certificate"])
					cert = certhandler.Certificate(cert_rec.certificate_b64)
					if cert:
					
						cert_rec.issuer_b64 = cert.IssuerNameDER() 
						cert_rec.subject_b64 = cert.SubjectNameDER()
						
						try:
							sid = transaction.savepoint()
							attr = Certs.CertAttributes()
							attr.Construct()
						
							attr.SetUpFromCert(x)
							if not first_cert_set:
								attr.cert_kind = (Certs.CertAttributes.CERT_SERVER 
												if attr.cert_kind not in [
													Certs.CertAttributes.CERT_SELFSIGNED,
													Certs.CertAttributes.CERT_SELFSIGNED_SERVER,
													]
												else
													Certs.CertAttributes.CERT_SELFSIGNED_SERVER)
					
							condition_list = attr.GetConditions() & db_list.EV_conditions 
							transaction.savepoint_commit(sid)
						except:
							transaction.savepoint_rollback(sid)
							pass
						#print "created attribute", condition_list
					
					cert_rec.save()
				elif cert_rec.GetCertificate == x["binary certificate"]:
					raise AssertionError("Two certificates with the same fingerprint: Hostname %s:%d. Certificate ID %d. Fingerprint %s" % prober.servername, prober.port, cert_rec.id, cert_rec.fingerprint_b64)
				else:
					for attr in Certs.CertAttributes.objects.filter(cert = cert_rec):
						condition_list = attr.GetConditions() & db_list.EV_conditions
						if not condition_list:
							attr.UpdateOIDs()
							if not first_cert_set:
								attr.UpdateEV()
							condition_list = attr.GetConditions() & db_list.EV_conditions
							#print "fixed attribute", condition_list
						#print "found attribute", condition_list
						break 
				
				while True:
					try:
						sid = transaction.savepoint()
						cert_seq, created = CertificateSequence.objects.get_or_create(certificate = cert_rec, sequence_number = cert_item)
					except DatabaseError:
						transaction.savepoint_rollback(sid)
						time.sleep(0.1)
						continue
					except IntegrityError:
						transaction.savepoint_rollback(sid)
						time.sleep(0.1)
						continue
					transaction.savepoint_commit(sid)
					break
	
				
				cert_list.append(cert_rec)
				cert_seq_list.append(cert_seq)
				if not first_cert_set:
					#print "updating ",  condition_list
					results["server_cert"] = cert_rec
					first_cert_set = True
					global_flags.update(condition_list)

		for (major, flags1) in major_flag.iteritems():
			flags = set(flags1)
			if Results.ResultCondition.RESULTC_VERSION_INTOLERANT not in flags:
				flags.add(Results.ResultCondition.RESULTC_VERSION_TOLERANT) 

			if Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT not in flags:
				flags.add(Results.ResultCondition.RESULTC_EXTENSION_TOLERANT)

			if Results.ResultCondition.RESULTC_BADVERSION not in flags:
				flags.add(Results.ResultCondition.RESULTC_GOODVERSION)

			if Results.ResultCondition.RESULTC_NOVERSION not in flags:
				flags.add(Results.ResultCondition.RESULTC_VERSIONCHECK)

			result_list[str((0,major))]=((0,major),set(flags))

		domain_list = list(server.domain_parents.all())
		ip_address_list0 = []
		for ip in ip_entries:
			items = ip.ip_parents.all()
			items_id = set([x.id for x in ip_address_list0])
			for item in items:
				if item.id not in items_id:
					ip_address_list0.append(item)

		results["result_summary_group"] = self.get_condition_group(global_flags)
		for r in records:
			flags = r.pop("flags",set())
			r["result_summary_group"] = self.get_condition_group(flags)

		def __SaveProber(results, records, ip_entries,ciphlist,secondary_agent_list,cert_list,cert_seq_list,intolerant_for_extension_list, suite_list):
			"""Save the prober entry"""
			
			common_res = [];
			for r in records:
				r1 = dict(r);
				r1["error_string"] = ProbeCommonErrorString.FetchOrCreate(r["error_string"]) if r["error_string"] else None
				r1["result_summary_group"] = r["result_summary_group"].common_conditionset 
				c = ProbeCommonResultEntry.FetchOrCreateItem(**r1)
				common_res.append(c);
				r["common_result"] = c; 

			results1  = dict(results)
			results1["cipher_suites"] = suite_list.cipher_suites;
			results1["intolerant_for_extension"] = intolerant_for_extension_list;
			results1["common_results"] = common_res;
			results1["result_summary_group"] = results["result_summary_group"].common_conditionset 
			c = ProbeCommonResult.FetchOrCreateItem(**results1);
			
			results.pop("used_dhe_key_size")
			result = ProbeResult.objects.create(common_result = c, **results)
			
			for target, source_list in [
					(result.ip_addresses,ip_entries),
					(result.secondary_agents,secondary_agent_list),
					(result.certificates,cert_list),
					(result.certificate_sequence,cert_seq_list),
									]:
				while True:
					try:
						sid = transaction.savepoint()
						target.add(*source_list)
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
			
			return result;
	
		def __SaveResults(self,results,result_list, ver, agent_list,short_list,domain_list,ip_entries, 
						ip_address_list0,primary_short_agent,primary_agent2, suite_list, dhe_keysize, ip_address_rec):
			"""Save results for the protocol version/extention tolerance tests"""
			common_prot = Results.ResultCommonEntryProtocolSet.FetchOrCreateItem([
								Results.ResultCommonEntryProtocol.FetchOrCreateItem(version_tested_major = ver[0],
									version_tested_minor = ver[1],
			 						result_summary_group = self.get_condition_group(flags).common_conditionset)
							for (ver, flags) in result_list.itervalues()])
					
			result = self.summary_list.summaries.create(part_of_run=self.run, 
								 servername = results.servername,
								 result_entry = results,
								 version_supported_major=ver[0], 
								 version_supported_minor=ver[1],
								 cipher_suite_group = suite_list,
								 PrimaryShortServerAgentSummary=primary_short_agent,
								 PrimaryServerAgentSummary=primary_agent2,
								 dhe_keysize = dhe_keysize,
								 result_summary_group = results.result_summary_group,
								 protcol_result_summary_set = common_prot,
								 )
			
			for target, source_list in [
					(result.SecondaryServerAgentSummary,agent_list),
					(result.SecondaryShortServerAgentSummary,short_list),
					(result.DomainSummary0,domain_list),
					(result.ip_addresses,ip_entries),
					(result.IPDomainSummary0,ip_address_list0),
					(self.summary_list.SecondaryServerAgentSummary, agent_list),
					(self.summary_list.SecondaryShortServerAgentSummary,short_list),
					(self.summary_list.ip_address_probed,ip_address_rec),
					(self.summary_list.IPDomainEntries0,ip_address_list0),
					(self.summary_list.DomainEntries0, domain_list),
									]:
				while True:
					try:
						sid = transaction.savepoint()
						target.add(*source_list)
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

		@transaction.commit_on_success
		def __do_store(self, prober, results, records, ip_entries,ciphlist,secondary_agent_list,cert_list,cert_seq_list,intolerant_for_extension_list,
					result_list,agent_list,short_list,domain_list,ip_address_list0,primary_short_agent,primary_agent2,suite_list, dhe_keysize
					):
			"""Perform the storing operation"""
			results = __SaveProber(results, records, ip_entries,ciphlist,secondary_agent_list,cert_list,cert_seq_list,intolerant_for_extension_list,suite_list)
					
			if prober.supported_versions:			
				__SaveResults(self,results,result_list,
							(max(prober.supported_versions) if prober.supported_versions else (0,0)),
							agent_list,short_list,domain_list,ip_entries,
							ip_address_list0,primary_short_agent,primary_agent2,
							suite_list, dhe_keysize,
							prober.ip_address_rec
							)
			
			self.log_performance()

		__do_store(self, prober, results, records, ip_entries,ciphlist,secondary_agent_list,cert_list,cert_seq_list,intolerant_for_extension_list,
				result_list,agent_list,short_list,domain_list,ip_address_list0,primary_short_agent,primary_agent2,suite_list, dhe_keysize)