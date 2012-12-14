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
import base64, datetime
# Create your models here.

import probedb.probedata2.models as Prober
import probedb.resultdb2.condition as Results

import re

class CertHostNames(models.Model):
	hostname = models.CharField(max_length = 300, db_index=True, unique=True)
	wildcard = models.BooleanField(db_index=True)

	def __unicode__(self):
		return self.hostname

	def GetName(self):
		return self.hostname

class CertOIDs(models.Model):
	oid = models.CharField(max_length = 1000, db_index=True, unique=True)
	description = models.CharField(max_length = 300)

	known_ev_oids = {
		"2.16.578.1.26.1.3.3":"Buypass EV",
		"1.3.6.1.4.1.6449.1.2.1.5.1":"Comodo EV",
		"2.16.840.1.114412.2.1":"Digicert EV",
		"2.16.528.1.1001.1.1.1.12.6.1.1.1":"Diginotar EV",
		"2.16.840.1.114028.10.1.2":"Entrust EV",
		"1.3.6.1.4.1.14370.1.6":"Geotrust EV",
		"1.3.6.1.4.1.4146.1.1":"Globalsign EV",
		"2.16.840.1.114413.1.7.23.3":"Godaddy EV",
		"2.16.840.1.114414.1.7.24.3":"Godaddy EV",
		"1.3.6.1.4.1.14777.6.1.1":"Izenpe EV",
		"1.3.6.1.4.1.14777.6.1.2":"Izenpe EV",
		"1.3.6.1.4.1.8024.0.2.100.1.2":"Quovadis EV",
		"1.2.392.200091.100.721.1":"Secom EV",
		"2.16.756.1.89.1.2.1.1":"Swisssign EV",
		"2.16.840.1.113733.1.7.48.1":"Thawte EV",
		"2.16.840.1.113733.1.7.23.6":"Verisign EV",
		"2.16.840.1.114404.1.1.2.4.1":"Xramp EV",
		"1.3.6.1.4.1.23223.1.1.1":"Startcom EV"
			}

	known_oids = dict(known_ev_oids) 

	def __unicode__(self):
		return self.oid + ":"+self.description

	def GetName(self):
		return self.oid

class CertificateConditions(models.Model):
	
	CERTC_EXTENDED_VALIDATION_CERT = Results.ResultCondition.RESULTC_EXTENDED_VALIDATION_CERT
	CERTC_NOT_EXTENDED_VALIDATION_CERT = Results.ResultCondition.RESULTC_NOT_EXTENDED_VALIDATION_CERT
	
	CERTC_VALUES = [(x, Results.ResultCondition.RESULTC_VALUES_dict[x]) for x in [
									CERTC_EXTENDED_VALIDATION_CERT,
									CERTC_NOT_EXTENDED_VALIDATION_CERT,											
																				] 
				]
	CERTC_VALUES_dict = dict(CERTC_VALUES)

	condition = models.CharField(max_length=4, null=True, choices=CERTC_VALUES, db_index=True, unique=True)

	__values_set = {}
	for __result_var in dir():
		if not __result_var.startswith("CERTC_") or __result_var.startswith("CERTC_VALUES"):
			continue
		if eval(__result_var) not in CERTC_VALUES_dict:
			raise Exception("Entry %s was not present in CERTC__VALUES list" % (__result_var,))
		if eval(__result_var) in __values_set:
			print "Double entry in CERTC_* enum values: ", __result_var, ". Matches ", __values_set[ eval(__result_var)]
			raise Exception("Double entry in CERTC_* enum values: " + __result_var+ ". Matches "+ __values_set[ eval(__result_var)])
		__values_set[eval(__result_var)] = __result_var
			

	if any([len([__y for __y in CERTC_VALUES if __x[0] == __y[0]])>1 for __x in CERTC_VALUES]):
		print "Double entry in CERTC_* enum values"
		raise Exception("Double entry in CERTC_* enum values")
	if any([len([__y for __y in CERTC_VALUES if __x != __y and  __x[1] == __y[1]])>1 for __x in CERTC_VALUES]):
		print "Double explanation entry in CERTC_* enum values", str([__z for __z in [[(__x,__y) for __y in CERTC_VALUES if __x != __y and __x[1] == __y[1]] for __x in CERTC_VALUES] if len(__z) > 1])
		raise Exception("Double explanation entry in CERTC_* enum values" + str([__z for __z in [[(__x,__y) for __y in CERTC_VALUES if __x != __y and __x[1] == __y[1]] for __x in CERTC_VALUES] if len(__z) > 1]))

	def __unicode__(self):
		return self.condition

	def GetName(self):
		return self.condition

class CertAttributes(models.Model):
	
	NOT_VERIFIED = "N"
	VERIFIED_OK = "V"
	VERIFIED_FAILED = "F"
	VERIFIED_REVOKED = "R"
	
	VERIFIED_VALUES = (
					(NOT_VERIFIED, "Not Verified"),
					(VERIFIED_OK, "Verified OK"),
					(VERIFIED_FAILED, "Failed"),
					(VERIFIED_REVOKED, "Revoked"),
					)

	FAIL_UNDECIDED=""	
	FAIL_NO ="OK"
	FAIL_DECODE = "Decode"
	FAIL_SIG = "Sig"
	FAIL_UNKNOWN_SIGNER = "Unknown"
	
	FAIL_VALUES = (
				(FAIL_UNDECIDED,"Unknown status"),
				(FAIL_NO, "No failure"),
				(FAIL_DECODE,"Decoding of certificate failed"),
				(FAIL_SIG,"Signature failure"),
				(FAIL_UNKNOWN_SIGNER,"Unknown signer"),
				)
	
	CERT_UNKNOWN = "U"
	CERT_UNKNOWN_TESTED ="UT" # used by test code to classify an unknown certificate as visited
	CERT_SERVER = "S"
	CERT_INTERMEDIATE_CA = "I"
	CERT_XSIGN_CA = "X"
	CERT_TRUSTED_ROOT="T"
	CERT_SELFSIGNED = "SS"
	CERT_SELFSIGNED_SERVER = "SSS"
	
	CERT_TYPE_VALUES = (
					("", "Blank (Unknown)"),
					(CERT_UNKNOWN,"Unknown"),
					(CERT_UNKNOWN_TESTED, "Unknown tested"),
					(CERT_SERVER, "Server certificate"),
					(CERT_INTERMEDIATE_CA,"Intermediate CA certificate"),
					(CERT_XSIGN_CA, "Cross-signed Intermediate CA"),
					(CERT_TRUSTED_ROOT,"Trusted Root"),
					(CERT_SELFSIGNED,"SelfSigned Root (untrusted)"),
					(CERT_SELFSIGNED_SERVER,"Selfsigned server (untrusted)"),
					)

	CERT_KEY_OK = "O"
	CERT_KEY_WEAK_DEBIAN = "D"
	CERT_KEY_UNKNOWN = "U"
	
	CERT_KEY_VALUES = (
					(CERT_KEY_OK, "Key correctly generated AFIWK"),
					(CERT_KEY_WEAK_DEBIAN, "Generated using weak Debian generator (suspected)"),
					(CERT_KEY_UNKNOWN , "Unknown")
					)

	condition_list = {} 

	cert = models.OneToOneField(Prober.Certificate, db_index=True)
	
	keysize = models.IntegerField(db_index=True)
	keystrength = models.CharField(max_length=1, choices=CERT_KEY_VALUES, db_index=True, null=True)

	subject_oneline = models.TextField(db_index=True)
	issuer_oneline = models.TextField(db_index=True)
	
	serial_number = models.CharField(max_length=100, null=True, blank=True) 
	
	valid_from = models.DateTimeField(db_index=True)
	valid_to = models.DateTimeField(db_index=True)
	
	keyhash = models.CharField(max_length=64, db_index=True)
	sigalg = models.CharField(max_length=64, db_index=True)
	
	signers = models.ManyToManyField("CertAttributes", null=True, db_index=True)
	duplicates = models.ManyToManyField("CertAttributes", null=True, db_index=True)
	
	verification_result = models.CharField(max_length=1, choices=VERIFIED_VALUES, db_index=True)
	failure_cause = models.CharField(max_length=20, choices=FAIL_VALUES)

	CommonNameCount = models.IntegerField(db_index=True)
	SANCount = models.IntegerField(db_index=True)
	SANIPCount = models.IntegerField(db_index=True)
	IsNetscapeName = models.BooleanField(db_index=True)
	
	AllNames = models.ManyToManyField(CertHostNames, null=True)
	CommonNames = models.ManyToManyField(CertHostNames, null=True, related_name="common_name")
	SANNames = models.ManyToManyField(CertHostNames, null=True, related_name="san_name")
	NetscapeName = models.ForeignKey(CertHostNames, null=True, related_name="netscape_name")

	AllNamesInSAN = models.BooleanField(db_index=True)
	NetscapeInCommon = models.BooleanField(db_index=True)

	wildcards = models.BooleanField(db_index=True)
	wildcards_common = models.BooleanField(db_index=True)
	wildcards_san = models.BooleanField(db_index=True)
	wildcards_netscape = models.BooleanField(db_index=True)
	wildcards_nonleaf = models.BooleanField(db_index=True)
	wildcards_secondlevel = models.BooleanField(db_index=True)
	wildcards_full_label = models.BooleanField(db_index=True)

	cert_kind = models.CharField(max_length=3, choices=CERT_TYPE_VALUES, db_index=True)
	issuer_kind = models.CharField(max_length=3, choices=CERT_TYPE_VALUES, db_index=True)
	
	cert_oids = models.ManyToManyField(CertOIDs, null=True)
	cert_conditions =  models.ManyToManyField(CertificateConditions, null=True)
	
	def __unicode__(self):
		return self.cert_kind+ " " + self.subject_oneline+ self.cert.sha256_fingerprint 
	
	def Construct(self):
		#self.cert = None
		self.keysize = 0
		self.keystrength =CertAttributes.CERT_KEY_UNKNOWN
		
		self.valid_from = datetime.datetime.min
		self.valid_to = datetime.datetime.min
		
		self.CommonNameCount = 0
		self.SANCount = 0
		self.SANIPCount = 0
		self.IsNetscapeName = False
		
		self.wildcards =False
		self.wildcards_common =False
		self.wildcards_netscape =False
		self.wildcards_san =False
		self.wildcards_nonleaf =False
		self.wildcards_secondlevel =False
		self.wildcards_full_label =False
		
		self.AllNamesInSAN = False
		self.NetscapeInCommon  = False
		
		verification_result = CertAttributes.NOT_VERIFIED
		failure_cause = CertAttributes.FAIL_UNDECIDED
		
		self.cert_kind = CertAttributes.CERT_UNKNOWN
		self.issuer_kind = CertAttributes.CERT_UNKNOWN
	

	def GetConditions(self):
		return set(self.cert_conditions.values_list("condition",flat=True))
	
	def SetUpFromCert(self, certificate):
		import certhandler
	
		self.keystrength = CertAttributes.CERT_KEY_UNKNOWN 
		self.cert = certificate
		if isinstance(certificate, Prober.Certificate):
			cert = certhandler.Certificate(certificate.certificate_b64)
		else:
			raise
			
		if not cert:
			self.failure_cause = CertAttributes.FAIL_DECODE
			self.save()
			return
		
		self.keysize = cert.Keysize()
		self.sigalg = cert.SignatureMethod()
		self.keyhash = cert.KeyHash()
		#print self.signature
		
		self.subject_oneline = cert.SubjectNameLine()
		self.issuer_oneline = cert.IssuerNameLine()

		serial = str(cert.GetSerialNumber())
		if len(serial) >100:
			serial = "NaN"
			
		self.serial_number = serial
		
		self.valid_from = cert.GetValidFrom()
		self.valid_to = cert.GetValidTo()
		
		if cert.IsSelfSigned():
			self.cert_kind = CertAttributes.CERT_SELFSIGNED
		
		names = cert.ExtractHostnames()
		hlist_san = []
		hlist_com = []
		hlist_net = []
		if names:
			san_list = []
			total_list = []
			if "SAN_DNS" in names:
				self.SANCount = len(names["SAN_DNS"])
				san_list =[x.lower() for x in names["SAN_DNS"]]
				total_list+=san_list
				if any(["*" in name for name in san_list]):
					self.wildcards_san= True
				hlist_san = [CertHostNames.objects.get_or_create(hostname=x, defaults={"wildcard":("*" in x)})[0] for x in san_list]
			common = None
			if "Common Name" in names:
				common = [x.lower() for x in names["Common Name"] if re.match(r'^[\w\-*.]+$', x) and "." in x] 
				self.CommonNameCount = len(common)
				total_list += common
				if any(["*" in name for name in common]):
					self.wildcards_common= True
				hlist_com = [CertHostNames.objects.get_or_create(hostname=x, defaults={"wildcard":("*" in x)})[0] for x in common]
			if "SAN_IP" in names:
				self.SANIPCount = len(names["SAN_IP"])
			self.IsNetscapeName = ("Netscape ServerName" in names)
			if self.IsNetscapeName:
				name = names["Netscape ServerName"].lower()
				if "*" in name:
					self.wildcards_netscape = True
				total_list.append(name)
				self.NetscapeInCommon = (name in common) or ("." in name and "*."+name.partition(".")[2] in common) 
				hlist_net = [CertHostNames.objects.get_or_create(hostname=name, defaults={"wildcard":("*" in name)})[0]]

			all_in_san = False
			if len(san_list) > 0:
				all_in_san = True
				for name in total_list:
					if "*" in name:
						self.wildcards = True
						components = name.split(".")
						self.wildcards_nonleaf = (len(components) >1 and components[0] != "*.")
						self.wildcards_secondlevel = (len(components) <= 2 or any(["*" in x for x in components[-2:]]))
						self.wildcards_full_label = not any([x != "*" for x in components if "*" in x])
						if name not in san_list:
							all_in_san = False
					else:
						if name not in san_list:
							if "." not in name :
								all_in_san = False
							elif "*."+name.partition(".")[2] not in san_list:
								all_in_san = False
				
			if all_in_san:
				self.AllNamesInSAN = True 

		if hlist_net:
			self.NetscapeName = hlist_net[0];
			
		self.save()

		self.SANNames.add(*hlist_san);
		self.CommonNames.add(*hlist_com);
		self.AllNames.add(*(hlist_san +hlist_com + hlist_net));
		
		self.UpdateOIDs(cert)
		self.UpdateEV(cert)

	def UpdateOIDs(self, cert=None):
		import certhandler
		
		if not cert:
			cert = certhandler.Certificate(self.cert.certificate_b64)

		oids = cert.GetPolicyOIDs()
		oid_list = []
		for x in oids:
			oid_list.append(CertOIDs.objects.get_or_create(oid=x, defaults={"description":CertOIDs.known_oids.get(x,"")})[0])

		if oid_list:
			self.cert_oids.add(*oid_list)
		
		

	def  IsEV(self, cert=None):
		import certhandler
		
		if not cert:
			cert = certhandler.Certificate(self.cert.certificate_b64)

		oids = cert.GetPolicyOIDs()
		
		evoid = [x for x in oids if x in CertOIDs.known_ev_oids]
		ev_cas = [CertOIDs.known_ev_oids[x] for x in evoid]
		return ev_cas;
	
	def  UpdateEV(self, cert=None):
		if not CertAttributes.condition_list:
			CertAttributes.condition_list = dict([(c, CertificateConditions.objects.get_or_create(condition=c)[0]) for c in CertificateConditions.CERTC_VALUES_dict.iterkeys()])

		conds1 = self.GetConditions()
		conds = conds1 - set([CertificateConditions.CERTC_EXTENDED_VALIDATION_CERT, CertificateConditions.CERTC_NOT_EXTENDED_VALIDATION_CERT ])

		conds.add(CertAttributes.condition_list[CertificateConditions.CERTC_EXTENDED_VALIDATION_CERT if self.IsEV(cert) else CertificateConditions.CERTC_NOT_EXTENDED_VALIDATION_CERT ])
		if conds1 != conds:
			self.cert_conditions.remove(*[CertAttributes.condition_list[x] for x in [CertificateConditions.CERTC_EXTENDED_VALIDATION_CERT, CertificateConditions.CERTC_NOT_EXTENDED_VALIDATION_CERT ]] )
			self.cert_conditions.add(CertAttributes.condition_list[CertificateConditions.CERTC_EXTENDED_VALIDATION_CERT if self.IsEV(cert) else CertificateConditions.CERTC_NOT_EXTENDED_VALIDATION_CERT ])
