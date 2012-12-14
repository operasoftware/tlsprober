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
from django import forms
import django
import os
from django.shortcuts import get_object_or_404, render_to_response
import probedb.resultdb2.models as Results
import probedb.probedata2.models as ProbeData

from django.db import connection
from django.db.models import Q
from django.http import HttpResponse

result_summaries_info = {
	"queryset"  	:	Results.ResultSummaryList.objects.all(),
	"allow_empty"	:	True,
	"paginate_by"	:	100,
	"template_name"	:	"summaries.html",
}

def result_summary_info(request,object_id):
	"""Present a result summary"""
	object = get_object_or_404(Results.ResultSummaryList, pk=object_id)
	
	protocolfields={}
	for (fieldname, text, cond) in [("version_intolerant", "Version Intolerant", Results.ResultCondition.RESULTC_VERSION_INTOLERANT), 
											("extension_intolerant","Extension Intolerant", Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT),
											("extension_and_version_intolerant","Extension and Version Intolerant", Results.ResultCondition.RESULTC_VERANDEXT_INTOLERANT), 
											("extension_or_version_intolerant","Extension or Version Intolerant", Results.ResultCondition.RESULTC_VEROREXT_INTOLERANT),
											("bad_version","Require Bad Version", Results.ResultCondition.RESULTC_BADVERSION),
											("bad_check","No Version check", Results.ResultCondition.RESULTC_NOVERSION),
											]:
		cond_item = object.conditions.get(condition = cond)
		for (ver) in [(3,0),(3,1),(3,2),(3,3),(3,4),(3,11),(4,1),(0,3),(0,4)]:
			if ver == (3,0):
				title = "SSL v3"
			elif ver[0] == 0:
				title = "Summary TLS %d.x" %(ver[1]-2,)
			else:
				title = "TLS %d.%d" %(ver[0]-2, (ver[1]-1 if ver[0]==3 else ver[1]))
			Q = cond_item.resultentryprotocol_set.filter(version_tested_major=ver[0],version_tested_minor=ver[1])
			protocolfields.setdefault(str(ver),{"title":title, "values":{}})["values"][fieldname]={"header":text, "count":Q.count()}
		
	summary_fields = []	
	for (fieldname, text, cond) in [("renego", "Renego Patched", Results.ResultCondition.RESULTC_RENEGO), 
								("renego_noncompliant", "Renego Patched but non-compliant", Results.ResultCondition.RESULTC_RENEGONONCOMPLIANT),
								("renego_unpatched", "Not Renego Patched", Results.ResultCondition.RESULTC_NONRENEGO),
								("renego_unstable", "Renego Patched, but unstable", Results.ResultCondition.RESULTC_RENEGOUNSTABLE),
								]:
		cond_item = object.conditions.get(condition = cond)
		Q = cond_item.resultentry_set.all()
		summary_fields.append({"header":text, "count":Q.count()})
	
	
	return render_to_response("summary.html", {
						"object":object,
						"protocolfields":protocolfields,
						"summary_fields":summary_fields,
						"debug_output":[x for x in connection.queries],
						})

class ResultForm(forms.Form):
	"""Result search form"""
	run_to_use = forms.ModelChoiceField(queryset=Results.ResultSummaryList.objects.order_by("part_of_run__sort_rank__sort_rank", "part_of_run__source_name", "-part_of_run__date"))
	protocol =  forms.MultipleChoiceField(required = False, choices=((("All","All"),)+ ProbeData.Server.PROTOCOL_LIST))
	conditions =  forms.MultipleChoiceField(required = False, choices=Results.ResultCondition.RESULTC_VALUES, widget=forms.SelectMultiple(attrs={"size":"20"}))
	alexagroup =  forms.ChoiceField(required = False, choices=Results.ResultSummaryList.ALEXA_TYPE_VALUES)
	summary = forms.ChoiceField(choices=(("Total", "Total"),)+ Results.ResultSummaryList.RESULT_TYPE_VALUES )

	run_to_limit = forms.ModelMultipleChoiceField(required = False,
												 queryset=Results.ResultSummaryList.objects.order_by("part_of_run__sort_rank__sort_rank", "part_of_run__source_name", "-part_of_run__date"),
												 widget=forms.SelectMultiple(attrs={"size":"10"}))
	
	ciphers = [
			("AES", "AES"),
			("RC4", "RC4"),
			("3DES", "3DES"),
			]
	for x in ProbeData.CipherName.objects.filter(ciphername__startswith="TLS").order_by("ciphername"):
		ciphers.append((x.ciphervalue, x.ciphername))
	
	
	ciphers_include = forms.MultipleChoiceField(required = False,
									choices = ciphers)
	ciphers_exclude = forms.MultipleChoiceField(required = False,
									choices = ciphers)

def SearchResults_doSearch(request):
	"""
	Search for number of results from a given run, matching given parameters
	Return the total, and optionally more detailed counts for specific
	elements (such as hostnames, IP domains, cipher suites, etc.)
	
	The actual search is done in summary_models
	""" 
	if request.method == 'POST': # If the form has been submitted...
		form = ResultForm(request.POST) # A form bound to the POST data
	elif request.method == 'GET': # If the form has been submitted...
		form = ResultForm(request.GET) # A form bound to the GET data
	if form.is_valid(): # All validation rules pass
		filter = {}
		summaries = {}
		
		summary = form.cleaned_data["run_to_use"]
		
		filters =  form.cleaned_data["conditions"]
		summary_entry = form.cleaned_data["summary"]
		protocol=  form.cleaned_data["protocol"]
		if "All" in protocol or not protocol:
			protocol = None

		ciphers = []		
		ciph =  form.cleaned_data["ciphers_include"]
		if ciph:
			for x in ciph:
				if x in ["AES", "RC4", "3DES"]:
					ciphers += ProbeData.CipherName.objects.filter(ciphername__startswith="TLS", ciphername__contains = "_"+x+"_").values_list("id",flat=True)
				else:
					ciphers += ProbeData.CipherName.objects.filter(ciphervalue = int(x)).values_list("id",flat=True)
			ciphers = ProbeData.CipherName.objects.filter(id__in = ciphers)

		ciphers_ex = []		
		ciph =  form.cleaned_data["ciphers_exclude"]
		if ciph:
			for x in ciph:
				if x in ["AES", "RC4", "3DES"]:
					ciphers_ex += ProbeData.CipherName.objects.filter(ciphername__startswith="TLS", ciphername__contains = "_"+x+"_").values_list("id",flat=True)
				else:
					ciphers_ex += ProbeData.CipherName.objects.filter(ciphervalue = int(x)).values_list("id",flat=True)
			ciphers_ex = ProbeData.CipherName.objects.filter(id__in = ciphers_ex)
		
		alexagroup = form.cleaned_data["alexagroup"]
		if not alexagroup:
			alexagroup = -1
		
		profile_q = None
		profile = int(request.GET.get("profile",0))
		if profile:
			profile_q = Q(result_entry__common_result=profile)
		else:
			profile = int(request.GET.get("bprofile",0)	)
			if profile:
				profile_q = Q(result_entry__common_result__basic_result=profile)
			else:
				profile = int(request.GET.get("fprofile",0))
				if profile:
					profile_q = Q(result_entry__common_result__fundamental_result=profile)
					
		extraparam = {}
		if profile_q:
			extraparam["limitresult"] = profile_q
			
		result = summary.GetAnalyze(filter=dict([(Results.ResultSummaryList.QUERY_CONDITION, form.cleaned_data["conditions"]),
										(Results.ResultSummaryList.QUERY_ALEXA_RESTRICT,alexagroup),
										] +
										 ([(Results.ResultSummaryList.QUERY_PROTOCOL_RESTRICT, protocol)] if protocol else [])+ 
										 ([(Results.ResultSummaryList.QUERY_RESTRICT_RUN,[x.part_of_run_id for x in form.cleaned_data["run_to_limit"]])] if form.cleaned_data["run_to_limit"] else [])+
										 ([(Results.ResultSummaryList.QUERY_CIPHER, ciphers)]  if ciphers else [])+
										 ([(Results.ResultSummaryList.QUERY_CIPHER_EXCLUDE, ciphers_ex)]  if ciphers_ex else [])
										), 
					summaries={
							"data":([summary_entry] if summary_entry != "Total" else []),
							 },
					**extraparam
					)
		
		value_fun = {
					Results.ResultSummaryList.RESULT_HOSTS:lambda x: x.servername.full_servername,
					Results.ResultSummaryList.RESULT_HOSTS_ALEXA:lambda x: x.servername.full_servername,
					Results.ResultSummaryList.RESULT_URLS_TEXT:lambda x: x.servername.full_servername,
					Results.ResultSummaryList.RESULT_HOST_RUNLIST:lambda x: (x.servername.servername, x.servername.port),
					Results.ResultSummaryList.RESULT_CONDITION:lambda x:dict(Results.ResultCondition.RESULTC_VALUES)[x.condition],
					Results.ResultSummaryList.RESULT_DOMAIN:lambda x: x.full_domain_name,
					Results.ResultSummaryList.RESULT_IP:lambda x: x.full_ip_mask,
					Results.ResultSummaryList.RESULT_PRIMARYAGENT:lambda x: x.agent_name,
					Results.ResultSummaryList.RESULT_SHORTPRIMARYAGENT:lambda x: x.agent_name,
					Results.ResultSummaryList.RESULT_SECONDARYAGENT:lambda x: x.agent_name,
					Results.ResultSummaryList.RESULT_SHORTSECONDARYAGENT:lambda x: x.agent_name,
					Results.ResultSummaryList.RESULT_CIPHER:lambda x: x.ciphername,
					Results.ResultSummaryList.RESULT_CIPHERGROUP:lambda x:  " ".join(sorted([y.ciphername for y in x.cipher_suites.cipher_suites.all()])),
					Results.ResultSummaryList.RESULT_PROTOCOLS:lambda x: dict(Results.ResultCondition.RESULTC_VALUES)[x.condition],
					Results.ResultSummaryList.RESULT_HOST_PROFILES:lambda x:x.key,
					Results.ResultSummaryList.RESULT_HOST_BASEPROFILES:lambda x:x.key,
					Results.ResultSummaryList.RESULT_HOST_FUNDPROFILES:lambda x:x.key,
					}[summary_entry] if summary_entry != "Total" else None
		data = result.get("data",[]) if summary_entry != "Total" else []
		if not data:
			data = []

						
		entries = [ (
						value_fun(x),
						x.filtered_count, 
						x.total_count, 
						(float(x.filtered_count)/float(x.total_count) if x.total_count else 0 )*100, 
						x,
						)						
						for x in data
					]
		if summary_entry in [Results.ResultSummaryList.RESULT_HOSTS_ALEXA, Results.ResultSummaryList.RESULT_URLS_TEXT, Results.ResultSummaryList.RESULT_HOST_RUNLIST]:
			entries.sort(key = lambda x:(x[-1].servername.alexa_rating if x[-1].servername.alexa_rating >0 else 100000000,x[-1].servername.full_servername))
		else:
			entries.sort(key = lambda x:(-x[1], x[0]))

		if summary_entry ==Results.ResultSummaryList.RESULT_URLS_TEXT:
			response = HttpResponse(mimetype="text/plain")
			response["Content-Disposition"] = "attachment; filename=urls.txt"
			
			for x in entries:
				response.write('https://'+x[-1].servername.servername+":"+str(x[-1].servername.port)+'/\n')
					
			return response  
		elif summary_entry ==Results.ResultSummaryList.RESULT_HOST_RUNLIST:
			response = HttpResponse(mimetype="text/csv")
			response["Content-Disposition"] = "attachment; filename=runlist.csv"
			
			import csv
			
			writer = csv.writer(response)
			i = 0
			for x in entries:
				i+=1
				writer.writerow([i] + list(x[0]))
					
			return response  
		elif summary_entry in [Results.ResultSummaryList.RESULT_HOST_PROFILES, Results.ResultSummaryList.RESULT_HOST_BASEPROFILES, Results.ResultSummaryList.RESULT_HOST_FUNDPROFILES]:
			return render_to_response('searchprofileresults.html', {
				"run":summary.part_of_run_id,
				"matching":result["_matching"],
				"total":result["_total"],
				"match_percentage":(float(result["_matching"])/float(result["_total"]) if result["_total"] else 0 )*100,
				"entries":entries,
				"debug_output":[x for x in connection.queries],
			
			})
				

		return render_to_response('searchresults.html', {
			"matching":result["_matching"],
			"total":result["_total"],
			"show_alexa":summary_entry == Results.ResultSummaryList.RESULT_HOSTS_ALEXA,
			"match_percentage":(float(result["_matching"])/float(result["_total"]) if result["_total"] else 0 )*100,
			"entries":entries,
			"debug_output":[x for x in connection.queries],
			
		})
	else:
		return 	SearchResults(request, method = request.method)
		
def SearchResults(request, method="POST"):
	"""Present form for searching results"""
	form = ResultForm() # An unbound form

	return render_to_response('searchform.html', {
		"root":os.environ.get("SCRIPT_NAME",""),
		"method": method if method in ["POST", "GET"] else "POST",
		'form': form,
	})