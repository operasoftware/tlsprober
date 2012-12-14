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

import standalone
import probedb.probedata2.models as Prober
import probedb.certs.models as Certs
import probedb.resultdb2.models as Results
from django.db.models import Q
import certhandler
import threading
import Queue

"""
Update the database so that the certificate attributes are set for all certificates

Used in case there is a failure in the automatic registration of certificates and
setting of attributes 
""" 

keys = {}
selfsigned_keys ={}	
failed=0
upgraded = 0

EV_conditions = set([
					Certs.CertificateConditions.CERTC_EXTENDED_VALIDATION_CERT, 
					Certs.CertificateConditions.CERTC_NOT_EXTENDED_VALIDATION_CERT 
					])

summaries = dict([(x.id, x) for x in  Results.ResultSummaryList.objects.all()])

i=0;

for x in summaries.itervalues():
	x.start()
	if 0:
		for c,d in Results.ResultCondition.RESULTC_VALUES:
			x.check_condition(c)

if 0:
	i=0;
	
	for certificate in Prober.Certificate.objects.filter(issuer_b64=None).iterator():
		cert = certhandler.Certificate(certificate.certificate_b64)
	
		if not cert:
			continue
		
		certificate.issuer_b64 = cert.IssuerNameDER() 
		certificate.subject_b64 = cert.SubjectNameDER()
		certificate.save() 
		i+=1
		if i%100 == 0:
			print i
		
	print "finished issuer" 	

if 0:
	i=0
	for certificate in Prober.Certificate.objects.filter(subject_b64=None).iterator():
		cert = certhandler.Certificate(certificate.certificate_b64)
	
		if not cert:
			continue
		
		certificate.issuer_b64 = cert.IssuerNameDER() 
		certificate.subject_b64 = cert.SubjectNameDER()
		certificate.save() 
	
		i+=1
		if i%100 == 0:
			print i

	print "finished subject" 	

if 0:
	i=0
	for certificate in Certs.CertAttributes.objects.filter(serial_number=None).iterator():
		cert = certhandler.Certificate(certificate.cert.certificate_b64)
	
		if not cert:
			continue
		
		serial = str(cert.GetSerialNumber())
		if len(serial) >100:
			serial = "NaN"
			
		certificate.serial_number = serial
		certificate.save()
	
		i+=1
		if i%100 == 0:
			print i
	
	print "finished serial numbers" 	

if 1:
	print "building database"

	def update_cert(x): 
		#try:
		if True:
			attr = Certs.CertAttributes()
			attr.Construct()
		
			attr.SetUpFromCert(x)
	
			condition_list = attr.GetConditions() & EV_conditions 
			for z in x.proberesult_set.filter(server_cert = x):
				if z.part_of_run_id not in summaries:
					continue
				summary = summaries.get(z.part_of_run_id)
				result_cond = z.GetConditions()
				result_cond1 = set(result_cond) 
				result_cond -= EV_conditions
				result_cond.update(condition_list)
				if result_cond1 != result_cond:
					z.result_summary_group = summary.get_condition_group(summary.part_of_run, result_cond)
					z.save()
				
				for y in z.resultentry_set.all():
					result_cond = y.GetConditions()
					result_cond1 = set(result_cond) 
					result_cond -= EV_conditions
					result_cond.update(condition_list)
					if result_cond1 != result_cond:
						y.result_summary_group = summary.get_condition_group(summary.part_of_run, result_cond)
						y.save()
	
		#except:
		#	raise
		#	pass
	
	def do_update_cert(queue, progress_queue, i):
		while True:
			k = queue.get()
			try:
				x = Prober.Certificate.objects.get(id=k)
				update_cert(x)
			except:
				pass
			progress_queue.put(True)
			queue.task_done()
		
	def __ProgressCounter(queue):
		i=0
		while True:
			queue.get()
	
			i += 1
			if i%100 == 0:
				print "Processed ", i, "servers so far"
	
			queue.task_done()
		

	update_queue = Queue.Queue()
	finished_queue = Queue.Queue()
	
	num_probers = 100
	threads = []
	for i in range(num_probers):
		new_thread = threading.Thread(target=do_update_cert, args=(update_queue,finished_queue, i))
		new_thread.daemon = True
		new_thread.start()
		threads.append(new_thread)
	
	progress_thread = threading.Thread(target=__ProgressCounter, args=(finished_queue,))
	progress_thread.daemon = True
	progress_thread.start()

	
	i=0;
	c_ids = list(Prober.Certificate.objects.filter(certattributes=None).values_list("id", flat=True))
	print len(c_ids)
	for k in c_ids:
	#for x in Prober.Certificate.objects.iterator():
		i+=1
		if i % 100 == 0:
			print i 
		update_queue.put(k)
	
	update_queue.join()
	finished_queue.join()


if 0:
	print "Marking site certificates" 
	i=0;
	#for k in list(Certs.CertAttributes.objects.filter(cert__server_cert__id__gt =0).distinct().values_list("id", flat=True)):
	c_ids = Certs.CertAttributes.objects.filter(cert_kind = Certs.CertAttributes.CERT_UNKNOWN).values_list("cert_id", flat=True)
	c_cids = list(Prober.ProbeResult.objects.exclude(server_cert__id__in = c_ids).filter(server_cert__id__gt =0).distinct().values_list("server_cert__id", flat=True))
	for k in c_ids :
		i+=1
		if i % 100 == 0:
			print i 
		try:
			x = Certs.CertAttributes.objects.get(cert__id = k)
			if x.cert_kind == Certs.CertAttributes.CERT_SELFSIGNED:
				x.cert_kind = Certs.CertAttributes.CERT_SELFSIGNED_SERVER
			else:
				x.cert_kind = Certs.CertAttributes.CERT_SERVER
			x.save()
		except:
			pass

if 0:	
	print "Locating intermediates"
	i=0;
	already_fixed = set()
	#for k in list(Certs.CertAttributes.objects.filter(cert__server_cert__id__gt =0).distinct().values_list("id", flat=True)):
	for k in list(Certs.CertAttributes.objects.exclude(cert_kind__in =[Certs.CertAttributes.CERT_SELFSIGNED,
													 		Certs.CertAttributes.CERT_SELFSIGNED_SERVER,
															Certs.CertAttributes.CERT_INTERMEDIATE_CA,
															Certs.CertAttributes.CERT_XSIGN_CA,
															Certs.CertAttributes.CERT_SERVER,] ).
												filter(cert__proberesult__server_cert__id__gt =0).
												distinct().
												values_list("id", flat=True)):
		i+=1
		if i % 100 == 0:
			print i 
		if k in already_fixed:
			continue;
		x = Certs.CertAttributes.objects.get(id = k)
		for y in x.cert.proberesult_set.filter(server_cert__id__gt =0):
			certs0 = [(z, certhandler.Certificate(z.certificate_b64)) for z in y.certificates.all()
						 if z.certattributes.cert_kind not in [Certs.CertAttributes.CERT_SELFSIGNED_SERVER, Certs.CertAttributes.CERT_SERVER]]
			if not certs0:
				continue;
			
			certs = {}
			for (z, c) in certs0:
				if not c:
					continue
				subject = c.SubjectNameLine()
				certs.setdefault(subject,[]).append((z,c))
			
			if not certs:
				 continue
			
			site = certhandler.Certificate(y.server_cert.certificate_b64)
			if not site:
				continue
			last = site
			
			while True:
				issuer = last.IssuerNameLine()
				if issuer not in certs:
					break;
				
				signer = None
				cert = None
				for (z,c) in certs[issuer]:
					if last.IsSignedBy(c):
						signer = z
						cert = c
						break;
	
				del certs[issuer] # prevent infinite loop
				
				if not signer:
					break;
				
				if signer.certattributes.cert_kind in [Certs.CertAttributes.CERT_SELFSIGNED, Certs.CertAttributes.CERT_TRUSTED_ROOT, ]:
					break; # Root, already set 
				
				if signer.certattributes.cert_kind == Certs.CertAttributes.CERT_UNKNOWN or signer.certattributes.cert_kind =="":
					signer.certattributes.cert_kind = Certs.CertAttributes.CERT_INTERMEDIATE_CA
					signer.certattributes.save()
					already_fixed.add(signer.id)
			
				last = cert
			break;

if 0:	
	print "Locating intermediates #2"
	i=0;
	already_fixed = set()
	name_matches = 0
	signed_by = 0
	#for k in list(Certs.CertAttributes.objects.filter(cert__server_cert__id__gt =0).distinct().values_list("id", flat=True)):
	for k in list(Certs.CertAttributes.objects.exclude(cert_kind__in =[Certs.CertAttributes.CERT_SELFSIGNED,
													 		Certs.CertAttributes.CERT_SELFSIGNED_SERVER,
															Certs.CertAttributes.CERT_INTERMEDIATE_CA,
															Certs.CertAttributes.CERT_XSIGN_CA,
															Certs.CertAttributes.CERT_SERVER,] ).
												distinct().
												values_list("id", flat=True)):
		i+=1
		if i % 100 == 0:
			print i 
		if k in already_fixed:
			continue;
		x = Certs.CertAttributes.objects.get(id = k)
		cert = certhandler.Certificate(x.cert.certificate_b64)
		if not cert:
			continue
		
		assert not cert.IsSelfSigned()
		subject = x.subject_oneline
		
		for y in Certs.CertAttributes.objects.filter(issuer_oneline=subject):
			name_matches += 1
			cert_cand = certhandler.Certificate(y.cert.certificate_b64)
			if not cert_cand:
				continue;
			
			if cert_cand.IsSignedBy(cert):
				signed_by += 1
				if x.cert_kind in [Certs.CertAttributes.CERT_UNKNOWN, ""]:
					x.cert_kind = Certs.CertAttributes.CERT_INTERMEDIATE_CA
					x.save()
					already_fixed.add(x.id)
			
				break
	
	print "Name matches: ", name_matches
	print "Signed by: ",signed_by

print "completed"