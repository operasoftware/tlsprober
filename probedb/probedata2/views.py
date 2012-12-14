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

# Create your views here.
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.views.generic import list_detail
from django.db import connection
		
import re
from models import *

import probedb.resultdb2.models as Results

run_list_info = {
	"queryset"  	:	ProbeRun.objects.all(),
	"allow_empty"	:	True,
	"paginate_by"	:	50,
	"template_name"	:	"runs.html",
}

def run_details_info(request, object_id):
	"""Paginated list of results for a given run"""
	run_item = get_object_or_404(ProbeRun, id=object_id)
 	return list_detail.object_list(
	 		request,
			queryset= ProbeResult.objects.filter(part_of_run = run_item),
			allow_empty=True,
			paginate_by=100,
			template_name="run_details.html",
			extra_context={"run_item":run_item}
		)


result_list_info = {
	"queryset"  	:	ProbeResult.objects.all(),
	"allow_empty"	:	True,
	"paginate_by"	:	100,
	"template_name"	:	"result_list.html",
}


def result_details_info(request,object_id): 
	"""Detailed presentation of a given probe result"""
	object = ProbeResult.objects.get(id=object_id)
	results = {"object" : object}
	for item in object.results.all():
		results["v%d%d_%s_%s"%(item.version_major, 
							item.version_minor, 
							("ext" if item.extensions else "noext"), 
							("bad" if item.badversion else "nobad"))] = item 
	
	return render_to_response("result_details.html", results)



def OK_No(value, collection):
	""" True -> "OK", green background ; False->"No",red, None to "-",no color """
	if value:
		return ("OK", "black; background-color:green;")
	if value == None:
		return ("-", "black")
	
	return ("No", "black; background-color:red;")

def Yes_No(value, collection):
	""" True -> "Yes", green background ; False->"No",red, None to "-",no color """
	if value:
		return ("Yes", "black; background-color:green;")
	if value == None:
		return ("-", "black")
	
	return ("No", "black; background-color:red;")

def Yes_No_reverse(value, collection):
	""" True -> "Yes", Red background ; False->"No",green, None to "-",no color """
	if value:
		return ("Yes", "black; background-color:red;")
	if value == None:
		return ("-", "black")
	
	return ("No", "black; background-color:green;")
	
	
def Tag_OK_No(value, link=None, reverse = False, yes_no = False):
	if reverse and not yes_no and value != None:
		value = not value
	return {"value":value, "textcolor":((Yes_No_reverse if reverse else Yes_No) if yes_no else OK_No), "link":link} 

def PresentProfile(request,object_id):
	"""Present a common result profile"""
	object = ProbeCommonResult.objects.get(id=object_id)
	
	run_id = request.GET.get("run", 0)
	
	version_status = {}
	
	for item in object.common_results.all():
		r = version_status.setdefault("{0:d}.{1:d}".format(item.version_major, item.version_minor), 
								{
								"version_name":"{0:s} {1:d}.{2:d}".format(
									*(["TLS", item.version_major-2, (item.version_minor -1 if item.version_major == 3 else item.version_minor)] 
											if (item.version_major, item.version_minor)>(3,0) else 
										["SSL", item.version_major, item.version_minor])
									),
								"version":(item.version_major, item.version_minor),
								"version_intolerant":None, 
								"extension_intolerant":None, 
								"no_version_check":None, 
								"require_bad_version_check":None
								}
								)
		
		if item.result == ProbeCommonResultEntry.PROBE_UNTESTED:
			raise
			continue;

		if item.extensions:
			if not item.badversion:
				r["extension_intolerant"] =  Tag_OK_No(item.result == ProbeCommonResultEntry.PROBE_PASSED)
		elif item.badversion:
			r["require_bad_version_check"] =  Tag_OK_No(item.result != ProbeCommonResultEntry.PROBE_PASSED)
			if (item.result_non_bad != ProbeCommonResultEntry.PROBE_UNTESTED and 
				item.result != ProbeCommonResultEntry.PROBE_PASSED):
				r["no_version_check"] =  Tag_OK_No(item.result == ProbeCommonResultEntry.PROBE_PASSED)
		else:
			r["version_intolerant"] =  Tag_OK_No(item.result == ProbeCommonResultEntry.PROBE_PASSED)

	version_status = [x for y,x in sorted(version_status.iteritems())]

	conds = object.result_summary_group.GetConditions()
			
	warn_details = []
	trouble_details = []

	support_20 = Results.ResultCondition.RESULTC_SUPPORT_SSLV2 in conds
		
	support_30 = Results.ResultCondition.RESULTC_SUPPORT_SSLV3 in conds
	support_31 = Results.ResultCondition.RESULTC_SUPPORT_TLS_1_0 in conds
	support_32 = Results.ResultCondition.RESULTC_SUPPORT_TLS_1_1 in conds
	support_33 = Results.ResultCondition.RESULTC_SUPPORT_TLS_1_2 in conds
	
	if not all([support_30, support_31, support_32, support_33]):
		warn_details.append("Does not support the most recent TLS protocol version")

	detected_mirror_version = Results.ResultCondition.RESULTC_VERSIONMIRROR in conds
	if detected_mirror_version:
		trouble_details.append("Responds with whatever version the client states, even if the server does not support it, causing connection failures")

	version_field_swap = Results.ResultCondition.RESULTC_CLVERSIONSWAP in conds
	if version_field_swap:
		trouble_details.append("Incorrectly using Record  Protocol Version field to negotiate  TLS version, instead of Client Hello Version field")
	
	support_renego = Results.ResultCondition.RESULTC_RENEGO in conds
	unstable_renego = Results.ResultCondition.RESULTC_RENEGOUNSTABLE in conds
	if not support_renego:
		trouble_details.append("Does not provide protection against renegotiation vulnerability")
		if Results.ResultCondition.RESULTC_ASKED_RENEGO in conds:
			trouble_details.append("The server requested TLS Renegotiation without using secure renegotiation. This allows MITM request injection attacks.")
			if Results.ResultCondition.RESULTC_NOTCOMLETED_REFUSED_RENEGO in conds:
				trouble_details.append("The server requested TLS Renegotiation without using secure renegotiation, and did not complete the action when the request was rejected. This causes usability problems for users.")
		if Results.ResultCondition.RESULTC_PERFORM_RENEGO in conds:
			trouble_details.append("The server accepted client initiated TLS Renegotiation without using secure renegotiation. This allows MITM request injection attacks.")
	elif unstable_renego:
		trouble_details.append("Variable protection against renegotiation vulnerability. A part of the server is not patched. Will cause intermittent connections failures in some clients")

	if support_renego:
		if Results.ResultCondition.RESULTC_RENEGOEXTSCSV_INTOL in conds: 
			trouble_details.append("The server supports the Renego patch, but refuses to accept Client Hellos with both Extension and the SCSV cipher suite. This can cause interoperability problems with some clients.")
		if Results.ResultCondition.RESULTC_PERFORM_RENEGO in conds:
			warn_details.append("The server accepted client initiated TLS Renegotiation. Secure Renegotiation was used, but is this support really necessary to have enabled?")
		if Results.ResultCondition.RESULTC_ACCEPT_FAKE_RENEGO in conds:
			trouble_details.append("The server accepted client initiated TLS Renegotiation using secure renegotiation, but did not check the finished information. This allows MITM request injection attacks.")
		
	if Results.ResultCondition.RESULTC_TOLERATE_SSLV2HAND in conds	and Results.ResultCondition.RESULTC_SUPPORT_SSLV2_CIPHERS in conds:
		if Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_SSLV2 in conds:
			trouble_details.append("Support only SSL v2, a 15 year old, unsecure protocol version, This version not supported by most modern browser clients")
		else:
			warn_details.append("Accept SSLv2-only connections. This support is unnecessary as most clients from 1996 and up support SSL v3 or later. Also, this 15 year old protocol version is unsecure")
		if Results.ResultCondition.RESULTC_SSLV2_WEAK_CIPHER in conds:
			trouble_details.append("Support SSL v2 exportable ciphers, which can be easily cracked. Modern clients also do not support either SSL v2 or exportable ciphers anymore.") 

	if Results.ResultCondition.RESULTC_PROBLEM_EXTRAPADDING in conds:
		warn_details.append("Does not support extra padding bytes in records.")
			
	if Results.ResultCondition.RESULTC_VERSION_INTOLERANT in conds:
		trouble_details.append("Version intolerant: Does not accept connections from clients that support some or all TLS versions newer than those supported by the server")
	if Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT in conds:
		trouble_details.append("Extension intolerant: Does not accept clients that support TLS Extensions")
		if Results.ResultCondition. RESULTC_INTOLERANT_SPECIFIC_EXTENSION in conds: 
			trouble_details.append("Extension intolerant: Does not accept specific TLS Extensions: " + ", ".join(sorted([str(x.GetName()) for x in object.common_result.intolerant_for_extension.all()])))
	if Results.ResultCondition.RESULTC_NOVERSION in conds:
		trouble_details.append("Does not check RSA Client Key Exchange Premaster Server version field to guard against version rollback attacks")
	if Results.ResultCondition.RESULTC_BADVERSION in conds:
		trouble_details.append(
							"""Require clients supporting newer TLS versions than the ones supported by the server to (incorrectly) 
							send the negotiated version, causing interoperability problems""")

	if object.used_dhe_key_size:		
		if object.used_dhe_key_size<600:
			trouble_details.append("The server uses temporary keys that are less than 600 bit long, specifically %d, which can be broken very quickly"%(object.used_dhe_key_size,))
		elif object.used_dhe_key_size<800:
			trouble_details.append("The server uses temporary keys that are less than 800 bit long, specifically %d, which can be broken in less than a year"%(object.used_dhe_key_size,))
		elif object.used_dhe_key_size<1024:
			warn_details.append("The server uses temporary keys that are less than 1024 bit long, specifically %d, which are in the dangerzone security-wise"%(object.used_dhe_key_size,))
	
	if Results.ResultCondition.RESULTC_SUPPORT_WEAK_CIPHER in conds:
		trouble_details.append("The server uses encryption methods that does not provide sufficient privacy for the connection")
		
	if Results.ResultCondition.RESULTC_SUPPORT_DEPRECATED_CIPHER in conds:
		warn_details.append("The server supports at least one cipher suite that is no longer allowed in the protocol version it selected.")

	if Results.ResultCondition.RESULTC_SUPPORT_TOONEW_CIPHER in conds:
		warn_details.append("The server supports at least one cipher suite that is only allowed to be used in protocol versions newer than the one supported by the server.")

	if Results.ResultCondition.RESULTC_CLVERSIONRECMATCH in conds:
		warn_details.append("The server seem to require that the Client Hello version requested must match the record protocol to select the requested version.")
		
	cipher_list = set(object.cipher_suites.cipher_suites.all().values_list("ciphername", flat=True)) if object.cipher_suites else set()
	supported_ciphers={}
	
	import tlslite.constants as constants
	for s in constants.CipherSuite.rsaSuites:
		st = constants.CipherSuite.toText.get(s,"")
		supported_ciphers[st] = Tag_OK_No((st in cipher_list),yes_no=True)
	for s in constants.CipherSuite.unsupportedSuites:
		st = constants.CipherSuite.toText.get(s,"")
		if st in cipher_list:
			if s in constants.CipherSuite.weakSuites:
				supported_ciphers[st] = Tag_OK_No(True,yes_no=True,reverse=True)
			else:
				supported_ciphers[st] = Tag_OK_No(True,yes_no=True)
		
	if constants.CipherSuite.toText.get(constants.CipherSuite.TLS_RSA_WITH_RC4_128_MD5, "") in cipher_list:
		if len(cipher_list) == 1:
			warn_details.append("The server only supports the RSA/RC4 with MD5 cipher, which might be weaker than desirable")
		
	if not any([constants.CipherSuite.toText.get(x,"") in cipher_list for x in constants.CipherSuite.aes128Suites + constants.CipherSuite.aes256Suites 
												if x in constants.CipherSuite.rsaSuites ]):
		warn_details.append("The server does not support the AES encryption method")
	
	if Results.ResultCondition.RESULTC_NONRESUMABLE_SESSIONS in conds:
		warn_details.append("The server does not offer resumable sessions; this will significantly increase load on the server")
	if Results.ResultCondition.RESULTC_NORESUME_SESSION in conds:
		warn_details.append("The server did not resume a resumable sessions; this will significantly increase load on the server")
		
	if Results.ResultCondition.RESULTC_NEW_SESSION_OVER in conds:
		warn_details.append("The server did not resume a resumable sessions when a higher version was used; this will significantly increase load on the server")
	if Results.ResultCondition.RESULTC_FAIL_RESUME_SESSION_OVER in conds:
		trouble_details.append("The server refused to resume a resumable sessions when a higher protocol version was used")
	
	if Results.ResultCondition.RESULTC_ACCEPT_FAKE_START_RENEGO in conds:
		trouble_details.append("Server supports Renego extension, but accepted a fake renegotition indication during the first handshake, which means a MITM injection attack is possible") 
	
	if Results.ResultCondition.RESULTC_ACCEPT_FAKE_RENEGO in conds:
		trouble_details.append("Server supports Renego extension, but accepted a wrong renegotition indication during a renegotation, which means a MITM injection attack is possible") 
	if Results.ResultCondition.RESULTC_ACCEPT_HIGH_PREM in conds:
		warn_details.append("Server supports renegotiation, but accepted the original version used during the first handshake. This could indicate that the premaster version is not checked")
	if Results.ResultCondition.RESULTC_ACCEPT_EHIGH_PREM in conds:
		trouble_details.append("Server supports renegotiation, but accepted a version higher than the original version used during the first handshake. This indicates that the premaster version is not checked")

	

	return render_to_response(
					"profilepresent.html",
					{
						"object" : object,
						"run":run_id,
						"summary_id":Results. ResultSummaryList.objects.get(part_of_run=run_id).id,
						"warn_details":warn_details,
						"trouble_details":trouble_details,
						"support_20":(Tag_OK_No(support_20, reverse = True) if support_20 else None),
						"support_30":Tag_OK_No(support_30),
						"support_31":Tag_OK_No(support_31),
						"support_32":Tag_OK_No(support_32),
						"support_33":Tag_OK_No(support_33),
						"version_status":version_status,
						"supported_ciphers":supported_ciphers,
						"conditions":([Results.ResultCondition.RESULTC_VALUES_dict[c] for c in conds] + 
									sorted(list(object.proberesult_set.filter(part_of_run__id=run_id).values_list("servername__full_servername")))+
									[str((x.version_major,x.version_minor,x.extensions, x.badversion, [x.result, x.result_non_bad] )) for x in object.common_results.all().order_by("version_major","version_minor","extensions", "badversion")]									
									),
						
						"debug_output":[x for x in connection.queries],							
					}
				)