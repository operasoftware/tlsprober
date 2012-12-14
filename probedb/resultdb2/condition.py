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
import probedb.probedata2.proberun as ProbeData
from django.db import DatabaseError
from django.db import IntegrityError
import probedb.manutrans as manutrans

import sys
import os.path

sys.path.insert(1, os.path.join(".."))

from tlscommon.test_results import *

# Create your models here.

class ResultCommonCondition(models.Model):
	"""A list of common flags for results, names in ResultCondition""" 
	condition = models.CharField(max_length=4, null=True, unique = True)
	

class ResultCondition(models.Model):
	"""A result flag used in a specific run"""
	part_of_run = models.ForeignKey(ProbeData.ProbeRun)

	RESULTC_COMPLIANT = 'CC'	# All compliant
	RESULTC_NON_COMPLIANT='NC'	# non compliant conditions exist
	RESULTC_NON_COMPLIANTv3='NC3'	# non compliant conditions exist v3.x
	RESULTC_NON_COMPLIANTv4='NC4'	# non compliant conditions exist v4.x

	RESULTC_RENEGO = 'R' 		# Renego patched
	RESULTC_NONRENEGO='NR'		# Not renego patched
	RESULTC_RENEGONONCOMPLIANT = 'RN' 	# Renego patched, but non-compliant
	RESULTC_RENEGONONCOMPLIANTv3 = 'RN3' 	# Renego patched, but non-compliant v3.x
	RESULTC_RENEGONONCOMPLIANTv4 = 'RN4' 	# Renego patched, but non-compliant v3.4
	RESULTC_RENEGOCOMPLIANT = 'RC' 	# Renego patched, but non-compliant
	RESULTC_RENEGOSTABLE = 'RS' 	# Renego patched, and stable
	RESULTC_RENEGOUNSTABLE = 'RU' 	# Renego patched, but not stable
	RESULTC_RENEGOEXTSCSV_ACCEPT = 'RESA' 	# Renego patched, and accept combined Renego extension and SCSV 
	RESULTC_RENEGOEXTSCSV_INTOL = 'RESI' 	# Renego patched, but not does not accept combined Renego extension and SCSV

	RESULTC_VERSION_INTOLERANT='VI'	# Version intolerance
	RESULTC_VERSION_INTOLERANT3='VI3'	# Version intolerance v3.x only
	RESULTC_VERSION_INTOLERANT4='VI4'	# Version intolerance v4.x only
	RESULTC_VERSION_INTOLERANT_FUTURE3="VIF3" #Version intolerant only for higher than TLS 1.2 for 1.x (future, currently undefined versions in the 3.x range)
	RESULTC_VERSION_INTOLERANT_CURRENT3="VIC3" #Version intolerant for exisiting TLS 1.x versions
	RESULTC_VERSION_TOLERANT_FUTURE3="VTF3" #Version tolerant for higher than TLS 1.2 for 1.x (future, currently undefined versions in the 3.x range)
	RESULTC_VERSION_TOLERANT_CURRENT3="VTC3" #Version tolerant for exisiting TLS 1.x versions
	RESULTC_VERSION_TOLERANT='VT'		# Version tolerant
	RESULTC_EXTENSION_INTOLERANT='EI'	# Extension intolerant
	RESULTC_EXTENSION_INTOLERANT30='EI30'	# Extension intolerant v3.0 only
	RESULTC_EXTENSION_INTOLERANTX='EIX'	# Extension intolerant more than v3.0
	RESULTC_EXTENSION_INTOLERANT_C3='EIC3'	# Extension intolerant in the current TLS 1.0-TLS 1.2 range
	RESULTC_EXTENSION_TOLERANT='ET'		# Extension tolerant 
	RESULTC_REVERSED_EXTENSION_INTOLERANT='EIR'	# Extension intolerance reversed for higher versions in TLS 1.0-1.2
	RESULTC_VERANDEXT_INTOLERANT='VEI'	# Version and extension intolerant
	RESULTC_VEROREXT_INTOLERANT='VOEI'	# Version or extension intolerant
	RESULTC_VEREXT_TOLERANT='VET'		# version and extension tolerant

	RESULTC_BADVERSION='BV'				# Bad version required
	RESULTC_GOODVERSION='GV'			# Good version required
	RESULTC_NOVERSION='NV'				# No version check performed by server
	RESULTC_VERSIONCHECK='VC'			# Versions is checked
	RESULTC_VERSIONMIRROR='VM'			# Server mirrors any version back to client.
	RESULTC_VERSIONCORRECT='VCNM'		# Correct version negotiation
	RESULTC_CLVERSIONSWAP='CVS'			# Record protocol field used instead of client hello during negotiation  
	RESULTC_CLVERSIONCORRECT='CV'		# Client hello version used during negotiation

	RESULTC_SUPPORT_SSLV2="S20"			# Support SSL v2
	RESULTC_SUPPORT_SSLV2_NO_CIPHER="S20N"	# Support SSL v2, but no SSL v2 ciphers enabled
	RESULTC_SUPPORT_SSLV2_CIPHERS="S20C"	# Support SSL v2, and SSL v2 ciphers are enabled
	RESULTC_SUPPORT_SSLV3="S30"			# Support SSL v3
	RESULTC_SUPPORT_TLS_1_0="S31"		# Support TLS 1.0
	RESULTC_SUPPORT_TLS_1_1="S32"		# Support TLS 1.1
	RESULTC_SUPPORT_TLS_1_2="S33"		# Support TLS 1.2
	RESULTC_NOSUPPORT_SSLv2="NS20"		# Does NOT Support SSL v2
	RESULTC_NOSUPPORT_SSLv3="NS30"		# Does NOT Support SSL v3
	RESULTC_NOSUPPORT_TLS_1_0="NS31"	# Does NOT Support TLS 1.0
	RESULTC_NOSUPPORT_TLS_1_1="NS32"	# Does NOT Support TLS 1.1
	RESULTC_NOSUPPORT_TLS_1_2="NS33"	# Does NOT Support TLS 1.2
	RESULTC_SUPPORT_HIGHEST_SSLV2="HS20"# Support SSL v2 as highest version
	RESULTC_SUPPORT_HIGHEST_SSLV3="HS30"# Support SSL v3 as highest version
	RESULTC_SUPPORT_HIGHEST_TLS_1_0="HS31"# Support TLS 1.0 as highest version
	RESULTC_SUPPORT_HIGHEST_TLS_1_1="HS32"# Support TLS 1.1 as highest version
	RESULTC_SUPPORT_HIGHEST_TLS_1_2="HS33"# Support TLS 1.2 as highest version
	RESULTC_SUPPORT_SSL_TLS="STLS"		# Support SSL 3.0 or higher

	RESULTC_SENT_SNI_EXT="SNI"			# Server sent the SNI extension
	RESULTC_SENT_SNI_WARN="SNIW"		# Server sent the SNI unrecognized_name warning
	RESULTC_NO_SNI_EXT="NSNI"			# Server did not send the SNI extension
	RESULTC_NO_SNI_WARN="NSNW"			# Server did not send the SNI unrecognized_name warning

	RESULTC_NO_CERT_STATUS="NCS"		# Server did not send the Certificate Status extension
	RESULTC_SENT_CERT_STATUS="SCS"		# Server sent the Certificate Status extension
	
	RESULTC_TOLERATE_SSLV2HAND="TS2H"	# Server Tolerates SSL v2 handshakes
	RESULTC_NOTOLERATE_SSLV2HAND="NS2H"	# Server Does Not Tolerate SSL v2 handshakes

	RESULTC_SSLV2_WEAK_CIPHER="S2WC"	# Server supports weak SSLv2 ciphers
	RESULTC_SSLV2_NOWEAK_CIPHER="S2NW"	# Server does not supports weak SSLv2 ciphers (if support SSL v2)

	RESULTC_SUPPORT_WEAK_CIPHER="SWC"	# Server supports weak v3+ ciphers
	RESULTC_NOSUPPORT_WEAK_CIPHER="NSWC"	# Server supports weak v3+ ciphers

	RESULTC_SUPPORT_DEPRECATED_CIPHER="SDC"	# Server supports ciphers supported only by older protocol versions 
	RESULTC_NOSUPPORT_DEPRECATED_CIPHER="NSDC"	# Server does not support ciphers supported only by older protocol versions
	
	RESULTC_SUPPORT_TOONEW_CIPHER="SNC"	# Server supports ciphers supported only by newer protocol versions 
	RESULTC_NOSUPPORT_TOONEW_CIPHER="NSNC"	# Server does not support ciphers supported only by newer protocol versions
	
	RESULTC_CLVERSIONRECMATCH="CRVM"		# Server require Client version and Record protocol version to match during negotiation
	RESULTC_CLRECVERSIONCORRECT="CRVC"		# Server accepts lower record protcol version than client hello version during negotiation
	
	RESULTC_PROBLEM_EXTRAPADDING="PEP"		# Server does not tolerate extra padding in block cipher modes
	RESULTC_NOPROBLEM_EXTRAPADDING="NPEP"	# Server tolerates extra padding in block cipher modes

	RESULTC_INTOLERANT_SPECIFIC_EXTENSION="ISE"		# Server does not tolerate specific TLS Extensions
	RESULTC_NOINTOLERANT_SPECIFIC_EXTENSION="NISE"	# Server tolerates all TLS Extensions (or none)
	
	RESULTC_RESUMABLE_SESSIONS="RS2"			# Resumable sessions returned
	RESULTC_NONRESUMABLE_SESSIONS="NRS2"		# Nonresumable sessions returned
	RESULTC_RESUME_SESSION="RS1"			# Resume sessions
	RESULTC_NORESUME_SESSION="NRS1"			# Does not resume sessions
	RESULTC_RESUME_SESSION_OVER="RSV"		# Allow resume of sessions when hello version is original, not negotiated version 
	RESULTC_NEW_SESSION_OVER="NSV"			# create new session when hello version is original, not negotiated version
	RESULTC_FAIL_RESUME_SESSION_OVER="RSVF"	# Connection fail when session is resume with hello version is original, not negotiated version
	
	RESULTC_SENT_SESSION_TICKETS="SST"		# TLS session ticket returned
	RESULTC_NOSEND_SESSION_TICKETS="NSST"		# TLS session ticket not returned

	RESULTC_RESUMED_SESSION_TICKETS="RST"		# TLS session ticket returned
	RESULTC_NORESUME_SESSION_TICKETS="NRST"		# TLS session ticket not returned
	
	RESULTC_CLIENT_CERT_REQUEST="CCR"		# Server requested Client Certificates
	RESULTC_NOCLIENT_CERT_REQUEST="NCCR"	# Server did not request Client Certificates
	
	RESULTC_CLIENT_CERT_REQUIRED="CCD"		# Server required client certificate for successful negotioation
	RESULTC_NOCLIENT_CERT_ACCEPTED="NCCA"	# Server asked for client cert, but accepted none
	
	RESULTC_NOCLIENT_CERT_ALERT="NCA"		# Client cert requested, needed to use No Cert alert
	RESULTC_NOCLIENT_CERT_NORMAL="NNCA"		# Client cert requested, normal no cert indication 
	
	RESULTC_ASKED_RENEGO="AR"				# Server requested renegotiation
	RESULTC_NOASK_RENEGO="NAR"				# Server did not ask for renegotiation
	
	RESULTC_ACCEPT_RENEGO="ACR"				# Server accepted client initiated renegotiation
	RESULTC_NOACCEPT_RENEGO="NACR"			# Server did not accept renegotiation attempt

	RESULTC_PERFORM_RENEGO="PR"				# Server performed renegotiation
	RESULTC_NOPERFORM_RENEGO="NPR"			# Server did not perform renegotiation 
	
	RESULTC_ACCEPT_FAKE_RENEGO="AFR"		# Server accepted a wrong renego extension value
	RESULTC_REFUSE_FAKE_RENEGO="RFR"		# Server refused to accept an incorrect renego extension value 

	RESULTC_ACCEPT_FAKE_START_RENEGO="AFSR"		# Server accepted a wrong renego extension value during start
	RESULTC_REFUSE_FAKE_START_RENEGO="RFSR"		# Server refused to accept an incorrect renego extension value during start 
	
	RESULTC_ACCEPT_HIGH_PREM="AHP"			# Accepted higher originally offered version than negotiated version when renegotiating
	RESULTC_NOACCEPT_HIGH_PREM="NAPH"		# Refused to accept higher than negotiated version when  renegotiating
	
	RESULTC_ACCEPT_EHIGH_PREM="AEP"			# Accepted higher than originally offered version when renegotiating
	RESULTC_NOACCEPT_EHIGH_PREM="NAEP"		# Refused to accept higher than originally offered version when  renegotiating
	
	RESULTC_EXTENDED_VALIDATION_CERT="EVC"	# Have Extended validation certificate
	RESULTC_NOT_EXTENDED_VALIDATION_CERT="NEVC"  # Does not have Extended validation certificate 
	
	RESULTC_COMLETED_REFUSED_RENEGO="CRR" 	# Completed connection even after client refused to accept renegotiation
	RESULTC_NOTCOMLETED_REFUSED_RENEGO="NCRR" 	# Did not complete connection even after client refused to accept renegotiation
	
	RESULTC_PARTREC_TESTED="PT"				# Partial apprecord Tested sending a partial or empty application record to counter CBC IV attack 
	RESULTC_PARTREC_NOTTESTED="PNT"			# Partial apprecord Not Tested sending a partial or empty application record to counter CBC IV attack 
	RESULTC_PARTREC_PASSED_ALL="PPA"		# Partial apprecord Passed All
	RESULTC_PARTREC_PASSED_SOME="PPS"		# Partial apprecord Passed Some
	RESULTC_PARTREC_FAILED="PF"				# Partial apprecord Failed
	RESULTC_PARTREC_FAILED_ALL="PFA"		# Partial apprecord Failed All
	RESULTC_PARTREC_FAILED_SOME="PFS"		# Partial apprecord failed Some
	RESULTC_PARTREC_PASSED_0="PP0"			# Partial apprecord Passed zero byte record
	RESULTC_PARTREC_FAILED_0="PF0"			# Partial apprecord Failed zero byte record
	RESULTC_PARTREC_PASSED_1="PP1"			# Partial apprecord Passed one byte record
	RESULTC_PARTREC_FAILED_1="PF1"			# Partial apprecord Failed one byte record
	RESULTC_PARTREC_PASSED_2="PP2"			# Partial apprecord Passed two byte record
	RESULTC_PARTREC_FAILED_2="PF2"			# Partial apprecord Failed two byte record
	RESULTC_PARTREC_PASSED_L1="PPL1"		# Partial apprecord Passed block less one byte record
	RESULTC_PARTREC_FAILED_L1="PFL1"		# Partial apprecord Failed block less one byte record
	RESULTC_PARTREC_PASSED_L2="PPL2"		# Partial apprecord Passed block less two byte record
	RESULTC_PARTREC_FAILED_L2="PFL2"		# Partial apprecord Failed block less two byte record

	RESULTC_PARTREC2_TESTED="QT"			# Partial apprecord combined Tested sending a partial or empty application record to counter CBC IV attack 
	RESULTC_PARTREC2_NOTTESTED="QNT"		# Partial apprecord combined Not Tested sending a partial or empty application record to counter CBC IV attack 
	RESULTC_PARTREC2_PASSED_ALL="QPA"		# Partial apprecord combined Passed All
	RESULTC_PARTREC2_PASSED_SOME="QPS"		# Partial apprecord combined Passed Some
	RESULTC_PARTREC2_FAILED="QF"			# Partial apprecord combined Failed
	RESULTC_PARTREC2_FAILED_ALL="QFA"		# Partial apprecord combined Failed All
	RESULTC_PARTREC2_FAILED_SOME="QFS"		# Partial apprecord combined failed Some
	RESULTC_PARTREC2_PASSED_0="QP0"			# Partial apprecord combined Passed zero byte record
	RESULTC_PARTREC2_FAILED_0="QF0"			# Partial apprecord combined Failed zero byte record
	RESULTC_PARTREC2_PASSED_1="QP1"			# Partial apprecord combined Passed one byte record
	RESULTC_PARTREC2_FAILED_1="QF1"			# Partial apprecord combined Failed one byte record
	RESULTC_PARTREC2_PASSED_2="QP2"			# Partial apprecord combined Passed two byte record
	RESULTC_PARTREC2_FAILED_2="QF2"			# Partial apprecord combined Failed two byte record
	RESULTC_PARTREC2_PASSED_L1="QPL1"		# Partial apprecord combined Passed block less one byte record
	RESULTC_PARTREC2_FAILED_L1="QFL1"		# Partial apprecord combined Failed block less one byte record
	RESULTC_PARTREC2_PASSED_L2="QPL2"		# Partial apprecord combined Passed block less two byte record
	RESULTC_PARTREC2_FAILED_L2="QFL2"		# Partial apprecord combined Failed block less two byte record
	
	RESULTC_FALSE_START_TESTED="FST"		# False Start Tested
	RESULTC_FALSE_START_NOTTESTED="FSNT"	# False Start Not Tested
	RESULTC_FALSE_START_FAILED="FSF"		# False Start Failed
	RESULTC_FALSE_START_ACCEPTED="FSA"		# False Start Accepted

	RESULTC_VALUES = (
					(RESULTC_COMPLIANT,"Compliant server"),
					(RESULTC_NON_COMPLIANT,"Noncompliant Server"),
					(RESULTC_NON_COMPLIANTv3,"Noncompliant Server for 3.x only"),
					(RESULTC_NON_COMPLIANTv4,"Noncompliant Server for 4.x+"),
					(RESULTC_RENEGO,"Renego patched server"),
					(RESULTC_NONRENEGO,"Not Renego patched"),
					(RESULTC_RENEGONONCOMPLIANT, "Renego patched, but not compliant"),
					(RESULTC_RENEGONONCOMPLIANTv3, "Renego patched, but not compliant for v3.x only"),
					(RESULTC_RENEGONONCOMPLIANTv4, "Renego patched, but not compliant for v4.x+"),
					(RESULTC_RENEGOCOMPLIANT, "Renego patched and compliant"),
					(RESULTC_RENEGOSTABLE, "Renego patched and stable"),
					(RESULTC_RENEGOUNSTABLE, "Renego patched, but unstable"),
					(RESULTC_RENEGOEXTSCSV_ACCEPT, "Renego patched, and accept combined Renego extension and SCSV "),
					(RESULTC_RENEGOEXTSCSV_INTOL, "Renego patched, but not does not accept combined Renego extension and SCSV"),
					(RESULTC_VERSION_INTOLERANT,"Version intolerant"),
					(RESULTC_VERSION_INTOLERANT3,"Version intolerant v3.x"),
					(RESULTC_VERSION_INTOLERANT4,"Version intolerant v4.x"),
					(RESULTC_VERSION_INTOLERANT_FUTURE3,"Version intolerant v3.x higher than 3.3"),
					(RESULTC_VERSION_INTOLERANT_CURRENT3,"Version intolerant TLS 1.0-TLS 1.2"),
					(RESULTC_VERSION_TOLERANT_FUTURE3,"Version Tolerant for v3.x higher than 3.3"),
					(RESULTC_VERSION_TOLERANT_CURRENT3,"Version tolerant TLS 1.0-TLS 1.2"),
					(RESULTC_VERSION_TOLERANT,"Version tolerant"),
					(RESULTC_EXTENSION_INTOLERANT,"Extension intolerant"),
					(RESULTC_EXTENSION_INTOLERANT30,"Extension intolerant v3.0 only"),
					(RESULTC_EXTENSION_INTOLERANTX,"Extension intolerant for non-v3.0"),
					(RESULTC_EXTENSION_INTOLERANT_C3, "Extension intolerant for TLS 1.0-TLS 1.2"),
					(RESULTC_EXTENSION_TOLERANT,"Extension tolerant"),
					(RESULTC_REVERSED_EXTENSION_INTOLERANT, "Extension intolerance reversed for higher versions in TLS 1.0-1.2"),
					(RESULTC_VERANDEXT_INTOLERANT,"Version and Extention intolerant"),
					(RESULTC_VEROREXT_INTOLERANT,"version or extension intolerant"),
					(RESULTC_VEREXT_TOLERANT,"version and extension tolerant"),
					(RESULTC_BADVERSION,"Require bad version"),
					(RESULTC_GOODVERSION,"Correct version requirement"),
					(RESULTC_NOVERSION,"No version checking done"),
					(RESULTC_VERSIONCHECK,"Correct version checking"),
					(RESULTC_VERSIONMIRROR,"Mirrors any version back"),
					(RESULTC_VERSIONCORRECT,"Version correctly negotiated"),
					(RESULTC_CLVERSIONSWAP,"Record Protcol version used instead of Client Hello version field for negotiation"),
					(RESULTC_CLVERSIONCORRECT,"Client Hello version correctly used for negotiation"),
					(RESULTC_SUPPORT_SSLV2,	"Support SSL v2"),
					(RESULTC_SUPPORT_SSLV2_NO_CIPHER,	"Support SSL v2, but no SSL v2 ciphers enabled"),
					(RESULTC_SUPPORT_SSLV2_CIPHERS,	"Support SSL v2, and SSL v2 ciphers are enabled"),
					(RESULTC_SUPPORT_SSLV3, "Support SSL v3"),
					(RESULTC_SUPPORT_TLS_1_0, "Support TLS 1.0"),
					(RESULTC_SUPPORT_TLS_1_1, "Support TLS 1.1"),
					(RESULTC_SUPPORT_TLS_1_2, "Support TLS 1.2"),
					(RESULTC_NOSUPPORT_SSLv2, "Does NOT Support SSL v2"),
					(RESULTC_NOSUPPORT_SSLv3, "Does NOT Support SSL v3"),
					(RESULTC_NOSUPPORT_TLS_1_0, "Does NOT Support TLS 1.0"),
					(RESULTC_NOSUPPORT_TLS_1_1, "Does NOT Support TLS 1.1"),
					(RESULTC_NOSUPPORT_TLS_1_2, "Does NOT Support TLS 1.2"),
					(RESULTC_SUPPORT_HIGHEST_SSLV2,	"Support SSL v2 as highest version"),
					(RESULTC_SUPPORT_HIGHEST_SSLV3, "Support SSL v3 as highest version"),
					(RESULTC_SUPPORT_HIGHEST_TLS_1_0, "Support TLS 1.0 as highest version"),
					(RESULTC_SUPPORT_HIGHEST_TLS_1_1, "Support TLS 1.1 as highest version"),
					(RESULTC_SUPPORT_HIGHEST_TLS_1_2, "Support TLS 1.2 as highest version"),
					(RESULTC_SUPPORT_SSL_TLS,		"Support SSL 3.0 or higher"),
					(RESULTC_SENT_SNI_EXT,		"Server sent the SNI extension"),
					(RESULTC_SENT_SNI_WARN,		"Server sent the SNI unrecognized_name warning"),
					(RESULTC_NO_SNI_EXT,		"Server did not send the SNI extension"),
					(RESULTC_NO_SNI_WARN,		"Server did not send the SNI unrecognized_name warning"),
					(RESULTC_SENT_CERT_STATUS,	"Server sent the Certificate Status extension"),
					(RESULTC_NO_CERT_STATUS,	"Server did not send the Certificate Status extension"),
					(RESULTC_TOLERATE_SSLV2HAND,			"Server Tolerates SSL v2 handshakes"),
					(RESULTC_NOTOLERATE_SSLV2HAND,			"Server Does Not Tolerate SSL v2 handshakes"),
					(RESULTC_SSLV2_WEAK_CIPHER,				"Server supports weak SSLv2 ciphers"),
					(RESULTC_SSLV2_NOWEAK_CIPHER,			"Server does not supports weak SSLv2 ciphers (if support SSL v2)"),
					(RESULTC_SUPPORT_WEAK_CIPHER,			"Server supports weak v3+ ciphers"),
					(RESULTC_NOSUPPORT_WEAK_CIPHER,			"Server does not supports weak v3+ ciphers"),
					(RESULTC_SUPPORT_DEPRECATED_CIPHER,		"Server supports ciphers supported only by older protocol versions"), 
					(RESULTC_NOSUPPORT_DEPRECATED_CIPHER,	"Server does not support ciphers supported only by older protocol versions"),
					(RESULTC_SUPPORT_TOONEW_CIPHER,			"Server supports ciphers supported only by older protocol versions"),
					(RESULTC_NOSUPPORT_TOONEW_CIPHER,		"Server does not support ciphers supported only by older protocol versions"),
					(RESULTC_CLVERSIONRECMATCH,				"Server require Client version and Record protocol version to match during negotiation"),
					(RESULTC_CLRECVERSIONCORRECT,			"Server accepts lower record protcol version than client hello version during negotiation"),
					(RESULTC_PROBLEM_EXTRAPADDING, 			"Server does not tolerate extra padding in block cipher modes"),
					(RESULTC_NOPROBLEM_EXTRAPADDING, 		"Server tolerates extra padding in block cipher modes"),
					(RESULTC_INTOLERANT_SPECIFIC_EXTENSION,	"Server does not tolerate specific TLS Extensions"),
					(RESULTC_NOINTOLERANT_SPECIFIC_EXTENSION,	"Server tolerates all TLS Extensions (or none)"),
					(RESULTC_RESUMABLE_SESSIONS,			"Resumable sessions returned"),
					(RESULTC_NONRESUMABLE_SESSIONS,			"Nonresumable sessions returned"),
					(RESULTC_RESUME_SESSION,				"Resume sessions"),
					(RESULTC_NORESUME_SESSION,				"Does not resume sessions"),
					(RESULTC_RESUME_SESSION_OVER,			"Allow resume of sessions when hello version is original, not negotiated version"), 
					(RESULTC_NEW_SESSION_OVER,				"create new session when hello version is original, not negotiated version"),
					(RESULTC_FAIL_RESUME_SESSION_OVER,		"Connection fail when session is resume with hello version is original, not negotiated version"),
					(RESULTC_CLIENT_CERT_REQUEST,			"Server requested Client Certificates"),
					(RESULTC_NOCLIENT_CERT_REQUEST,			"Server did not request Client Certificates"),
					(RESULTC_CLIENT_CERT_REQUIRED,			"Server required client certificate for successful negotioation"),
					(RESULTC_NOCLIENT_CERT_ACCEPTED,		"Server asked for client cert, but accepted none"),
					
					(RESULTC_NOCLIENT_CERT_ALERT,			"Client cert requested, needed to use No Cert alert"),
					(RESULTC_NOCLIENT_CERT_NORMAL,			"Client cert requested, normal no cert indication"), 
					
					(RESULTC_ASKED_RENEGO,					"Server requested renegotiation"),
					(RESULTC_NOASK_RENEGO,					"Server did not ask for renegotiation"),
					
					(RESULTC_COMLETED_REFUSED_RENEGO,		"Completed connection even after client refused to accept renegotiation"),
					(RESULTC_NOTCOMLETED_REFUSED_RENEGO,	"Did not complete connection even after client refused to accept renegotiation"),
					
					(RESULTC_ACCEPT_RENEGO,					"Server accepted client initiated renegotiation"),
					(RESULTC_NOACCEPT_RENEGO,				"Server did not accept client initiated renegotiation attempt"),
					
					(RESULTC_PERFORM_RENEGO,				"Server performed renegotiation"),
					(RESULTC_NOPERFORM_RENEGO,				"Server did not perform renegotiation"),

					(RESULTC_ACCEPT_FAKE_RENEGO,			"Server accepted a wrong renego extension value"),
					(RESULTC_REFUSE_FAKE_RENEGO,			"Server refused to accept an incorrect renego extension value"), 
					(RESULTC_ACCEPT_FAKE_START_RENEGO,		"Server accepted a wrong renego extension value during start"),
					(RESULTC_REFUSE_FAKE_START_RENEGO,		"Server refused to accept an incorrect renego extension value during start"),					
					(RESULTC_ACCEPT_HIGH_PREM,				"Accepted higher originally offered version than negotiated version when renegotiating"),
					(RESULTC_NOACCEPT_HIGH_PREM,			"Refused to accept higher than negotiated version when  renegotiating"),
					
					(RESULTC_ACCEPT_EHIGH_PREM,				"Accepted higher than originally offered version when renegotiating"),
					(RESULTC_NOACCEPT_EHIGH_PREM,				"Refused to accept higher than originally offered version when  renegotiating"),

					(RESULTC_EXTENDED_VALIDATION_CERT,		"Have Extended validation certificate"),
					(RESULTC_NOT_EXTENDED_VALIDATION_CERT,	"Does not have Extended validation certificate"), 

					(RESULTC_SENT_SESSION_TICKETS,			"TLS session ticket returned"),
					(RESULTC_NOSEND_SESSION_TICKETS,		"TLS session ticket not returned"),

					(RESULTC_RESUMED_SESSION_TICKETS,		"Resumed TLS session ticket"),
					(RESULTC_NORESUME_SESSION_TICKETS,		"Did not resume session ticket"),

					(RESULTC_PARTREC_TESTED,				"Partial apprecord Tested sending a partial or empty application record to counter CBC IV attack"), 
					(RESULTC_PARTREC_NOTTESTED,				"Partial apprecord Not tested sending a partial or empty application record to counter CBC IV attack"), 
					(RESULTC_PARTREC_PASSED_ALL,			"Partial apprecord Passed All"),
					(RESULTC_PARTREC_PASSED_SOME,			"Partial apprecord Passed Some"),
					(RESULTC_PARTREC_FAILED,				"Partial apprecord Failed"),
					(RESULTC_PARTREC_FAILED_ALL,			"Partial apprecord Failed All"),
					(RESULTC_PARTREC_FAILED_SOME,			"Partial apprecord failed Some"),
					(RESULTC_PARTREC_PASSED_0,				"Partial apprecord Passed zero byte record"),
					(RESULTC_PARTREC_FAILED_0,				"Partial apprecord Failed zero byte record"),
					(RESULTC_PARTREC_PASSED_1,				"Partial apprecord Passed one byte record"),
					(RESULTC_PARTREC_FAILED_1,				"Partial apprecord Failed one byte record"),
					(RESULTC_PARTREC_PASSED_2,				"Partial apprecord Passed two byte record"),
					(RESULTC_PARTREC_FAILED_2,				"Partial apprecord Failed two byte record"),
					(RESULTC_PARTREC_PASSED_L1,				"Partial apprecord Passed block less one byte record"),
					(RESULTC_PARTREC_FAILED_L1,				"Partial apprecord Failed block less one byte record"),
					(RESULTC_PARTREC_PASSED_L2,				"Partial apprecord Passed block less two byte record"),
					(RESULTC_PARTREC_FAILED_L2,				"Partial apprecord Failed block less two byte record"),

					(RESULTC_PARTREC2_TESTED,				"Partial apprecord Combined Tested sending a partial or empty application record to counter CBC IV attack"), 
					(RESULTC_PARTREC2_NOTTESTED,			"Partial apprecord Combined Not tested sending a partial or empty application record to counter CBC IV attack"), 
					(RESULTC_PARTREC2_PASSED_ALL,			"Partial apprecord Combined Passed All"),
					(RESULTC_PARTREC2_PASSED_SOME,			"Partial apprecord Combined Passed Some"),
					(RESULTC_PARTREC2_FAILED,				"Partial apprecord Combined Failed"),
					(RESULTC_PARTREC2_FAILED_ALL,			"Partial apprecord Combined Failed All"),
					(RESULTC_PARTREC2_FAILED_SOME,			"Partial apprecord Combined failed Some"),
					(RESULTC_PARTREC2_PASSED_0,				"Partial apprecord Combined Passed zero byte record"),
					(RESULTC_PARTREC2_FAILED_0,				"Partial apprecord Combined Failed zero byte record"),
					(RESULTC_PARTREC2_PASSED_1,				"Partial apprecord Combined Passed one byte record"),
					(RESULTC_PARTREC2_FAILED_1,				"Partial apprecord Combined Failed one byte record"),
					(RESULTC_PARTREC2_PASSED_2,				"Partial apprecord Combined Passed two byte record"),
					(RESULTC_PARTREC2_FAILED_2,				"Partial apprecord Combined Failed two byte record"),
					(RESULTC_PARTREC2_PASSED_L1,			"Partial apprecord Combined Passed block less one byte record"),
					(RESULTC_PARTREC2_FAILED_L1,			"Partial apprecord Combined Failed block less one byte record"),
					(RESULTC_PARTREC2_PASSED_L2,			"Partial apprecord Combined Passed block less two byte record"),
					(RESULTC_PARTREC2_FAILED_L2,			"Partial apprecord Combined Failed block less two byte record"),

					(RESULTC_FALSE_START_TESTED,			"TLS False Start Tested"),
					(RESULTC_FALSE_START_NOTTESTED,			"TLS False Start Not Tested"),
					(RESULTC_FALSE_START_FAILED,			"TLS False Start Failed"),
					(RESULTC_FALSE_START_ACCEPTED,			"TLS False Start Accepted"),
				
				)+ TRESULTC_VALUES
	
	RESULTC_VALUES_dict = dict(RESULTC_VALUES)
	
	# Check for duplicates, and enum flags without a description 
	__values_set = {}
	for __result_var in dir():
		if not __result_var.startswith("RESULTC_") or __result_var.startswith("RESULTC_VALUES"):
			continue
		if eval(__result_var) not in RESULTC_VALUES_dict:
			raise Exception("Entry %s was not present in RESULTC_VALUES list" % (__result_var,))
		if eval(__result_var) in __values_set:
			print "Double entry in RESULTC_* enum values: ", __result_var, ". Matches ", __values_set[ eval(__result_var)]
			raise Exception("Double entry in RESULTC_* enum values: " + __result_var+ ". Matches "+ __values_set[ eval(__result_var)])
		__values_set[eval(__result_var)] = __result_var
			

	if any([len([__y for __y in RESULTC_VALUES if __x[0] == __y[0]])>1 for __x in RESULTC_VALUES]):
		print "Double entry in RESULTC_* enum values"
		raise Exception("Double entry in RESULTC_* enum values")
	if any([len([__y for __y in RESULTC_VALUES if __x != __y and  __x[1] == __y[1]])>1 for __x in RESULTC_VALUES]):
		print "Double explanation entry in RESULTC_* enum values", str([__z for __z in [[(__x,__y) for __y in RESULTC_VALUES if __x != __y and __x[1] == __y[1]] for __x in RESULTC_VALUES] if len(__z) > 1])
		raise Exception("Double explanation entry in RESULTC_* enum values" + str([__z for __z in [[(__x,__y) for __y in RESULTC_VALUES if __x != __y and __x[1] == __y[1]] for __x in RESULTC_VALUES] if len(__z) > 1]))
	
	
	# Which conditions indicates compliance problems?
	RESULT_PROBLEMLIST = set([RESULTC_NON_COMPLIANT,
						RESULTC_NON_COMPLIANTv3,
						RESULTC_NON_COMPLIANTv4,
						RESULTC_VERSION_INTOLERANT,
						RESULTC_VERSION_INTOLERANT3,
						RESULTC_VERSION_INTOLERANT4,
						RESULTC_VERSION_INTOLERANT_FUTURE3,
						RESULTC_VERSION_INTOLERANT_CURRENT3,
						RESULTC_EXTENSION_INTOLERANT,
						RESULTC_EXTENSION_INTOLERANT30,
						RESULTC_EXTENSION_INTOLERANTX,
						RESULTC_EXTENSION_INTOLERANT_C3,
						RESULTC_VERANDEXT_INTOLERANT,
						RESULTC_VEROREXT_INTOLERANT,
						RESULTC_BADVERSION,
						RESULTC_NOVERSION,
						RESULTC_VERSIONMIRROR,
						RESULTC_CLVERSIONSWAP,
						RESULTC_SUPPORT_SSLV2,
						RESULTC_SUPPORT_HIGHEST_SSLV2,
						RESULTC_CLVERSIONRECMATCH,
						RESULTC_NOCLIENT_CERT_ALERT,
						RESULTC_ACCEPT_FAKE_RENEGO,
						RESULTC_ACCEPT_FAKE_START_RENEGO,
						RESULTC_ACCEPT_EHIGH_PREM,
						]
						)
	
	# Flags not counted in a basic profile, since they are controlled by configuration flags 
	RESULT_VALUE_CONFIGURATIONS = (
						RESULTC_RESUMABLE_SESSIONS,
						RESULTC_NONRESUMABLE_SESSIONS,
						RESULTC_RESUME_SESSION,
						RESULTC_NORESUME_SESSION,
						RESULTC_RESUME_SESSION_OVER,
						RESULTC_NEW_SESSION_OVER,
						RESULTC_FAIL_RESUME_SESSION_OVER,
						RESULTC_CLIENT_CERT_REQUEST,
						RESULTC_NOCLIENT_CERT_REQUEST,
						RESULTC_CLIENT_CERT_REQUIRED,
						RESULTC_NOCLIENT_CERT_ACCEPTED,
						RESULTC_NOCLIENT_CERT_ALERT,
						RESULTC_NOCLIENT_CERT_NORMAL,
						RESULTC_ASKED_RENEGO,
						RESULTC_NOASK_RENEGO,
						RESULTC_ACCEPT_RENEGO,
						RESULTC_NOACCEPT_RENEGO,
						RESULTC_PERFORM_RENEGO,
						RESULTC_NOPERFORM_RENEGO,
						RESULTC_EXTENDED_VALIDATION_CERT,
						RESULTC_NOT_EXTENDED_VALIDATION_CERT,
						RESULTC_SENT_SESSION_TICKETS,
						RESULTC_NOSEND_SESSION_TICKETS,
						RESULTC_RESUMED_SESSION_TICKETS,
						RESULTC_NORESUME_SESSION_TICKETS,
						)
	
	# Flags not counted in a fundamental profile, since they are controlled by configuration flags
	RESULT_VALUE_CONFIGURATIONS_CIPHER = RESULT_VALUE_CONFIGURATIONS + (
						RESULTC_SSLV2_WEAK_CIPHER,
						RESULTC_SSLV2_NOWEAK_CIPHER,
						RESULTC_SUPPORT_WEAK_CIPHER,
						RESULTC_NOSUPPORT_WEAK_CIPHER,
						RESULTC_SUPPORT_DEPRECATED_CIPHER,
						RESULTC_NOSUPPORT_DEPRECATED_CIPHER,
						RESULTC_SUPPORT_TOONEW_CIPHER,
						RESULTC_NOSUPPORT_TOONEW_CIPHER,
						)
	
	condition = models.CharField(max_length=4, null=True, choices=RESULTC_VALUES)
	common_condition = models.ForeignKey("ResultCommonCondition")
	
	@staticmethod
	def GetComplianceFlags(flag_item):
		"""
		Return subset of flags that idicates the kind of 
		compliance problems the result indicates
		"""
  
		extraflags = set()
		extraflags.add(ResultCondition.RESULTC_NON_COMPLIANT if flag_item & ResultCondition.RESULT_PROBLEMLIST else
							 ResultCondition.RESULTC_COMPLIANT)
		if ResultCondition.RESULTC_VERSION_INTOLERANT_FUTURE3 not in flag_item: 
			extraflags.add(ResultCondition.RESULTC_VERSION_TOLERANT_FUTURE3)
		if ResultCondition.RESULTC_VERSION_INTOLERANT_CURRENT3 not in flag_item: 
			extraflags.add(ResultCondition.RESULTC_VERSION_TOLERANT_CURRENT3)
		if ResultCondition.RESULTC_RENEGO in flag_item:
			extraflags.add(ResultCondition.RESULTC_RENEGONONCOMPLIANT if ResultCondition.RESULTC_NON_COMPLIANT in (flag_item | extraflags) else
								ResultCondition.RESULTC_RENEGOCOMPLIANT)

		return extraflags

class ResultCommonConditionSet(models.Model):
	"""
	A global set of flags, idenfied by their name concatenatd in a sorted list
	""" 
	result_summary_string = models.TextField(max_length = 1000, unique=True) 
	result_summary =  models.ManyToManyField(ResultCommonCondition, null=True)
	referred_by_main_result = models.BooleanField(default=False)

	def GetConditions(self):
		"""Get the set of flags"""
		return set(self.result_summary.values_list("condition",flat=True))

	@staticmethod
	@manutrans.commit_manually_if_unmanaged
	def FindSet(condition_group,create=None):
		"""Find the specified set of flags, or create a new entry""" 
		if isinstance(condition_group, set):
			if create == True:
				create = set(condition_group)
			elif create == False:
				create = None 
			condition_group = "_".join(sorted(list(condition_group)))

		item = None
		while not item:
			try:
				item = ResultCommonConditionSet.objects.get(result_summary_string=condition_group)
			except:
				item = None
			if not item:
				if create == None:
					break;		
				if isinstance(create, set):
					create = list(ResultCommonCondition.objects.filter(condition__in = list(create)))
				try:
					sid = transaction.savepoint()
					item = ResultCommonConditionSet.objects.create(result_summary_string=condition_group)
					item.result_summary.add(*create)
					transaction.savepoint_commit(sid)
					transaction.commit_unless_managed()
					#print "faa"
				except DatabaseError, excep:
					transaction.savepoint_rollback(sid)
					item = None
					time.sleep(0.1)
					continue
				except IntegrityError, excep:
					transaction.savepoint_rollback(sid)
					item = None
					time.sleep(0.1)
					continue
				except:
					transaction.savepoint_rollback(sid)
					transaction.rollback_unless_managed()
					item = None
					break;
			else:
				
				transaction.commit_unless_managed()
		return item

class ResultConditionSet(models.Model):
	"""
	A set of flags, unique for this specific run.
	""" 
	part_of_run = models.ForeignKey(ProbeData.ProbeRun)
	result_summary_string = models.TextField(max_length = 1000) 
	result_summary =  models.ManyToManyField(ResultCondition, null=True)
	common_conditionset = models.ForeignKey(ResultCommonConditionSet)
	
	__cache = {}

	class Meta:
		unique_together=[("part_of_run", "result_summary_string")]		
		
	def __unicode__(self):
		return str(self.part_of_run_id) + " " + self.result_summary_string

	def GetConditions(self):
		"""Get the set of flags"""
		if self.result_summary_string in ResultConditionSet.__cache:
			return ResultConditionSet.__cache[self.result_summary_string][1]
		
		s = set(self.result_summary.values_list("condition",flat=True))
		
		ResultConditionSet.__cache[self.result_summary_string] = (self, s)
		
		return s
	
	@staticmethod
	@manutrans.commit_manually_if_unmanaged
	def FindSet(run, condition_group,create=None):
		"""Find the specified set of flags, or create a new entry""" 
		
		cond_set = None
		if isinstance(condition_group, set):
			cond_set = set(condition_group)
			if create == True:
				create = set(condition_group)
			condition_group = "_".join(sorted(list(condition_group)))

		if condition_group in ResultConditionSet.__cache:
			# element (object, set)
			return ResultConditionSet.__cache[condition_group][0]

		item = None
		while not item:
			try:
				item = ResultConditionSet.objects.get(part_of_run=run, result_summary_string=condition_group)
			except:
				item = None
			if not item:
				if create == None or create == False:
					break;		
				if isinstance(create, set):
					create = list(ResultCondition.objects.filter(part_of_run=run, condition__in = create).select_related("common_condition"))
				if not cond_set:
					cond_set = set([x.condition for x in create])
				try:
					common_conditionset = ResultCommonConditionSet.FindSet(condition_group, create = [x.common_condition for x in create])
					sid = transaction.savepoint()
					item = ResultConditionSet.objects.create(part_of_run=run, result_summary_string=condition_group, common_conditionset=common_conditionset)
					item.result_summary.add(*create)
					transaction.savepoint_commit(sid)
					transaction.commit_unless_managed()
				except DatabaseError:
					transaction.savepoint_rollback(sid)
					item = None
					time.sleep(0.1)
					continue
				except IntegrityError:
					transaction.savepoint_rollback(sid)
					item = None
					time.sleep(0.1)
					continue
				except BaseException, error:
					print error
					raise
					transaction.savepoint_rollback(sid)
					transaction.rollback_unless_managed()
					item = None
					break;
			else:
				transaction.commit_unless_managed()
				
		if cond_set == None:
			cond_set = set([x.condition for x in item.result_summary.all()])
		ResultConditionSet.__cache[condition_group] = (item, cond_set)
		return item
