# -*- Mode: python; tab-width: 4; indent-tabs-mode: nil; -*-
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

"""
Process the results for a given run and create a list of HTML 
summaries.
"""

from optparse import OptionParser
import time

import probedb.standalone
import os, os.path
import probedb.probedata2.models as Probe
from django.db import connection
from django.db.models import Q,Count, Manager, Aggregate

from django.db.models.query import QuerySet

import probedb.resultdb2.models as Results
from django.template.loader import get_template
from django.template import Context

from probedb.probedata2.present_security_view import render

from probedb.probedata2 import percent
import threading
import Queue

debug = False# True

class WritePage:
	def __init__(self, filenum = 1, fixed = False,folder = None):
		self.filenum = filenum
		self.sub_filenum = 0
		self.fixed = fixed
		self.base_folder = folder
		self.folder = os.path.join("results",folder) if folder else "results"
		try:
			os.makedirs(self.folder)
		except:
			pass 

	def write_page(self, item):
		if self.sub_filenum:
			name = "security_summary_%03d_%03d.html" % (self.filenum,self.sub_filenum)
		else:
			name = "security_summary_%03d.html" % (self.filenum,)
			
		print "writing ", self.folder, name
		f = open(os.path.join(self.folder,name), "wt")
		print >> f, item
		f.close()
		self.sub_filenum+=1
	
	def GetPageWriter(self):
		if self.fixed:
			raise Exception("Can't create new writer; this is a fixed writer")
		writer = WritePage(self.filenum, True, self.base_folder)
		self.filenum +=1
		self.sub_filenum = 0
		return writer
	
	def inc_file(self):
		if not self.fixed:
			self.filenum+=1
			self.sub_filenum = 0

def get_percentage(match, total, non_zero_is_fail=False, link=None, no_color=True ):
	return percent.setup_redgreen_percent(
								match,
								total,
								non_zero_is_fail = non_zero_is_fail,
								no_color= no_color,
								link = link)

def get_domain_parents(domain):
	if domain["level"] <=1: 
		return []
	return [domain["domain_parent_id"]] + get_domain_parents(domain["__cache__"][domain["domain_parent_id"]])

def get_ip_parents(domain):
	if domain["level"] <=1: 
		return []
	return [domain["ip_parent_id"]] + get_ip_parents(domain["__cache__"][domain["ip_parent_id"]])

def list_domains(list_of_domains, matching, total, non_zero_is_fail=True):
	
	domains = {}
	domains["top"] = {"count":0, "children": []}
	for x in list_of_domains :
		id = x["value"]["domain_parent_id"] if x["value"]["level"] > 1 else "top"
		item = domains.setdefault(id, {"count":0, "children": []})
		item["children"].append(x)
		for id in get_domain_parents(x["value"]):
			item = domains.setdefault(id, {"count":0, "children": []})
			item["count"]+=1

	return list_domains_engine(list_of_domains, domains, matching, total,
									non_zero_is_fail = non_zero_is_fail)

def list_ipdomains(list_of_domains, matching, total, non_zero_is_fail=True):
	
	domains = {}
	domains["top"] = {"count":0, "children": []}
	table = []
	for x in list_of_domains :
		id = x["value"]["ip_parent_id"] if x["value"]["level"] > 1 else "top"
		item = domains.setdefault(id, {"count":0, "children": []})
		item["children"].append(x)
		for id in get_ip_parents(x["value"]):
			item = domains.setdefault(id, {"count":0, "children": []})
			item["count"]+=1

	return table + list_ipdomains_engine(list_of_domains, domains, matching, total,
									non_zero_is_fail = non_zero_is_fail)

def compare_domains(x,y):
	return cmp(x["value"]["domain_name"], y["value"]["domain_name"])

def compare_ipdomains(x,y):
	return cmp(x["value"]["ip_domain"], y["value"]["ip_domain"])

def list_domains_engine(list_of_domains, domains, matching, total, tab_prefix=[], parent = None, non_zero_is_fail=True):
	minimum = (matching*2)/100 if  matching > 500 else 0
	if minimum and matching < minimum:
		return []

	top_label = parent["value"]["full_domain_name"] if parent else None
	domain_item = None
	if not parent or parent["value"]["id"] in domains:
		domain_item = domains[parent["value"]["id"] if parent else "top"]
		
	table = [[None, tab_prefix+[top_label, get_percentage(parent["filtered_count"], total,
									non_zero_is_fail = non_zero_is_fail)]]] if top_label else []
	if domain_item:
		for x in sorted(domain_item["children"], cmp = compare_domains ):
			if x["filtered_count"] > minimum:
				table += list_domains_engine(list_of_domains, domains, matching, total,
										parent = x, 
										tab_prefix = tab_prefix + [None], 
										non_zero_is_fail = non_zero_is_fail)
	return table

def list_ipdomains_engine(list_of_domains, domains, matching, total, tab_prefix=[], parent = None, non_zero_is_fail=True):
	minimum = (matching*2)/100 if  matching > 500 else 0
	if minimum and matching < minimum:
		return []

	top_label = parent["value"]["full_ip_mask"] if parent else None
	domain_item = None
	if not parent or parent["value"]["id"] in domains:
		domain_item = domains[parent["value"]["id"] if parent else "top"]
		
	table = [[None, tab_prefix+[top_label, get_percentage(parent["filtered_count"], total,
									non_zero_is_fail = non_zero_is_fail)]]] if top_label else []
	if domain_item:
		for x in sorted(domain_item["children"], cmp = compare_ipdomains ):
			if x["filtered_count"] > minimum:
				table += list_ipdomains_engine(list_of_domains, domains, matching, total,
										parent = x, 
										tab_prefix = tab_prefix + [None], 
										non_zero_is_fail = non_zero_is_fail)
	return table

def compare_short_agents(x,y):
	return cmp((-x["filtered_count"], x["value"]["agent_name__agent_shortname"]), (-y["filtered_count"], y["value"]["agent_name__agent_shortname"]))

def list_short_agents(results, total, non_zero_is_fail=True, tab_prefix=[]):
	table = []
	for x in sorted(results, cmp = compare_short_agents ):
		table.append([None, tab_prefix+  [x["value"]["agent_name__agent_shortname"]] + [get_percentage(x["filtered_count"], total, non_zero_is_fail = non_zero_is_fail), 
							get_percentage(x["filtered_count"], x["total_count"])]])
		if x["subset_results"]:
			table += list_agents(x["subset_results"], x["filtered_count"], tab_prefix =  tab_prefix+ [None],non_zero_is_fail = non_zero_is_fail)
	return table

def compare_agents(x,y):
	return cmp((-x["filtered_count"], x["value"]["agent_name__agent_name"]), (-y["filtered_count"], y["value"]["agent_name__agent_name"]))

def list_agents(results, total, non_zero_is_fail=True, tab_prefix=[]):
	table = []
	for x in sorted(results, cmp = compare_agents ):
		table.append([None,  tab_prefix+ [x["value"]["agent_name__agent_name"]] + [get_percentage(x["filtered_count"], total, non_zero_is_fail = non_zero_is_fail), 
							get_percentage(x["filtered_count"], x["total_count"])]])
		if x["subset_results"]:
			table += list_agents(x["subset_results"], x["filtered_count"], tab_prefix =  tab_prefix+ [None],non_zero_is_fail = non_zero_is_fail)
	return table


def perform_detailed_presentation(title, sub_title,  results):
	
	
	presenter = []
	
	if Results.ResultSummaryList.RESULT_PRIMARYAGENT in results:
		presenter.append([None,[None]])
		presenter.append(["Primary agents", [None]])
		presenter += list_agents(results[Results.ResultSummaryList.RESULT_PRIMARYAGENT], results["_total"])

	if Results.ResultSummaryList.RESULT_SHORTPRIMARYAGENT in results:
		presenter.append([None,[None]])
		presenter.append(["Primary agents (by app)", [None]])
		presenter += list_short_agents(results[Results.ResultSummaryList.RESULT_SHORTPRIMARYAGENT], results["_total"])
	
	if Results.ResultSummaryList.RESULT_SECONDARYAGENT in results:
		presenter.append([None,[None]])
		presenter.append(["Secondary agents", [None]])
		presenter += list_agents(results[Results.ResultSummaryList.RESULT_SECONDARYAGENT], results["_total"])
	
	if Results.ResultSummaryList.RESULT_SHORTSECONDARYAGENT in results:
		presenter.append([None,[None]])
		presenter.append(["Secondary agents (by app)", [None]])
		presenter += list_short_agents(results[Results.ResultSummaryList.RESULT_SHORTSECONDARYAGENT], results["_total"])
	
	if Results.ResultSummaryList.RESULT_DOMAIN in results:
		presenter.append([None,[None]])
		presenter.append(["Domain names", [None]])
		presenter += list_domains(results[Results.ResultSummaryList.RESULT_DOMAIN], results["_matching"], results["_total"])
	
	if Results.ResultSummaryList.RESULT_IP in results:
		presenter.append([None,[None]])
		presenter.append(["IP addresses", [None]])
		presenter += list_ipdomains(results[Results.ResultSummaryList.RESULT_IP], results["_matching"], results["_total"])

	if (Results.ResultSummaryList.RESULT_HOSTS in results and 
		len(results[Results.ResultSummaryList.RESULT_HOSTS]) < 500):
		presenter.append([None,[None]])
		presenter.append(["All results", [None]])
		for x in results[Results.ResultSummaryList.RESULT_HOSTS]:
			presenter.append([None, [x["value"]["servername__servername"] + ":" + str(x["value"]["servername__port"])]])
		pass

	return(
		[(title, [sub_title, " ".join(["Matching :", str(results["_matching"]), 
				"of", str(results["_total"]), ":",get_percentage(results["_matching"],results["_total"])["value"]])]),
			presenter
		 ])

def execute_query(query_queue, num, multiple_pages_writer, summary_base, query_conf, extra_query):
	query = iter(query_conf)
	title = query.next()
	headers = query.next()
	if not isinstance(headers, list):
		headers = [headers]
	
	count = 0
	item = query.next()
	preconditions = [[]]
	if isinstance(item, tuple):
		preconditions = [(x if x is not isinstance(x, str) else [x]) for x in item];
		item = query.next()

	if len(preconditions) == 1 and len(headers) > 1:
		preconditions = preconditions * len(headers)
	elif len(preconditions) != len(headers):
		raise Exception("Length of pre-condition list did not match list of headers")
	
	
	queries = item

	present_details = [[Results.ResultSummaryList.RESULT_HOSTS],
					[Results.ResultSummaryList.RESULT_DOMAIN],
					[Results.ResultSummaryList.RESULT_IP],
					]+ ([
					[Results.ResultSummaryList.RESULT_PRIMARYAGENT, 
						#Results.ResultSummaryList.RESULT_SECONDARYAGENT
						],
					[Results.ResultSummaryList.RESULT_SHORTPRIMARYAGENT,
						#Results.ResultSummaryList.RESULT_PRIMARYAGENT
						],
					[Results.ResultSummaryList.RESULT_SECONDARYAGENT],
					[Results.ResultSummaryList.RESULT_SHORTSECONDARYAGENT,
						#Results.ResultSummaryList.RESULT_SECONDARYAGENT
						],
					] if not extra_query else [])
	try:
		if query.next() == False:
			present_details = []
	except StopIteration:
		pass;

	#print title, headers, preconditions, queries, present_details  
	
	present_details = dict([[x if isinstance(x, str) else x[0],x] for x in present_details])

	details_presentations = []

	presentation_title = [title, [None] + headers]
	rows = []
	result_titles = dict(Results.ResultCondition.RESULTC_VALUES)
	waiters = []
	if isinstance(queries, list):
		if len(headers) == 1:
			#Single column, multiple rows
			precond = preconditions[0]
			for line in queries:
				row = []
				desc = None
				if isinstance(line, tuple):
					desc = line[0]
					conditions = line[1]
				else:
					conditions = line
				if isinstance(conditions, str):
					conditions = [conditions]
				if not desc:
					desc = result_titles.get(conditions[0], str(conditions))
				
				summaries = {"data":[]}
				summaries.update(present_details)
				
				row.append(None)
				if present_details:
					details_presentations.append(None)
				
				wait_item = threading.Event()
				wait_item.clear()
				waiters.append(wait_item)
				count += 1
					
				query_queue. put(((num, count), summary_base, 
								(row, len(row)-1),
								((details_presentations, len(details_presentations)-1) if present_details else None),
								title,
								desc, 
								{
								"filter" : {Results.ResultSummaryList.QUERY_CONDITION: precond + conditions},
								"summaries" : summaries
								},
								wait_item
								)
							)
				row.append(None)
				
				rows.append((desc, row))
		elif queries and not any([isinstance(x, tuple) for x in queries]):
			row = []
			conditions = [[x] if isinstance(x, str) else x for x in queries]
			desc = None

			for precond, cond, hdr  in map(None, preconditions[:len(conditions)],conditions, headers[:len(conditions)]):
				if isinstance(cond, str):
					cond = [cond]
				if not cond:
					cond = []
				if isinstance(precond, str):
					precond = [precond]
				if not precond:
					precond = []
				summaries = {"data":[]}
				summaries.update(present_details)

				row.append(None)
				if present_details:
					details_presentations.append(None)
				
				wait_item = threading.Event()
				wait_item.clear()
				waiters.append(wait_item)
				count += 1
					
				query_queue. put(((num, count),summary_base, 
								(row, len(row)-1),
								((details_presentations, len(details_presentations)-1) if present_details else None),
								title,  
								result_titles.get(cond[0], str(cond))+ (" (" + hdr + ")" if hdr else ""), 
								{
								"filter" : {Results.ResultSummaryList.QUERY_CONDITION: precond + cond},
								"summaries" : summaries
								},
								wait_item
								)
							)
			rows.append((desc, row))
		else:
			for line in queries:
				row = []
				desc = None
				if isinstance(line, tuple):
					desc = line[0]
					conditions = line[1]
				else:
					conditions = line
				if isinstance(conditions, str):
					conditions = [conditions]
				if not desc:
					desc = result_titles.get(conditions[0], str(conditions))

				for precond, cond, hdr  in map(None, preconditions[:len(conditions)],conditions, headers[:len(conditions)]):
					if isinstance(cond, str):
						cond = [cond]
					if not cond:
						cond = []
					if isinstance(precond, str):
						precond = [precond]
					if not precond:
						precond = []
					summaries = {"data":[]}
					summaries.update(present_details)

					row.append(None)
					if present_details:
						details_presentations.append(None)
					
					wait_item = threading.Event()
					wait_item.clear()
					wait_item.clear()
					count += 1
					
					waiters.append(wait_item)
						
					query_queue. put(((num, count),summary_base, 
									(row, len(row)-1),
									((details_presentations, len(details_presentations)-1) if present_details else None),
									title, 
									desc + " (" + hdr + ")", 
									{
									"filter" : {Results.ResultSummaryList.QUERY_CONDITION: precond + cond},
									"summaries" : summaries
									},
									wait_item
									)
								)
				rows.append((desc, row))
	elif isinstance(queries, Manager) or isinstance(queries, QuerySet):
		for x in queries.all().iterator():
			row = []
			for precond, hdr  in map(None, preconditions, headers):
				if isinstance(precond, str):
					precond = [precond]
				if not precond:
					precond = []
				summaries = {"data":[]}
				summaries.update(present_details)

				row.append(None)
				if present_details:
					details_presentations.append(None)
				
				wait_item = threading.Event()
				wait_item.clear()
				waiters.append(wait_item)
				count += 1
					
				query_queue. put(((num, count),summary_base, 
								(row, len(row)-1),
								((details_presentations, len(details_presentations)-1) if present_details else None),
								x.GetName(),
								hdr, 
								{
								"filter" : {
								Results.ResultSummaryList.QUERY_CONDITION: precond,
								Results.ResultSummaryList.QUERY_AUTO: [x]
								},
								"summaries": summaries
								}, 
								wait_item
								)
							)
				
			rows.append((x.GetName(), row))

	while any([not x.isSet() for x in waiters]):
		global debug
		if debug:
			print "item"
			do_analysis_step(query_queue,0)
		else:
			time.sleep(15)

	multiple_pages_writer.write_page(render(CreateContext(summary_base, (presentation_title, rows), None, extra_query)))
	for item in details_presentations:
		if item:
			multiple_pages_writer.write_page(render(CreateContext(summary_base, item, None, extra_query)))
		
	multiple_pages_writer.inc_file()

def CreateContext(summary_base, summary, alexa_link, extra_query=None):
	
	(title, top) =summary[0]
	new_summary = [(top, summary[1])]
	return {
							"run_id":summary_base.part_of_run.id,
							"run_description":summary_base.part_of_run.description,
							"run_date":summary_base.part_of_run.date,
							"alexa_link":alexa_link,
							"probed":summary_base.summaries.filter(part_of_run= summary_base.part_of_run, *([extra_query] if extra_query else []) ).count(),
							"document_title": title,
							#"debug_output":debug_list,
							"summary_tables": new_summary 
							}

def generate_results(queue, query_queue,run_item, run_result_id=None, multiple_pages_writer=False, extra_query=None):
	
	summary_base = Results.ResultSummaryList.objects.get(part_of_run = run_item);
	
	summary_base.init_cache([Results.ResultSummaryList.RESULT_HOSTS,
					Results.ResultSummaryList.RESULT_DOMAIN,
					Results.ResultSummaryList.RESULT_IP,
					]+
					([Results.ResultSummaryList.RESULT_PRIMARYAGENT, 
					Results.ResultSummaryList.RESULT_SHORTPRIMARYAGENT,
					Results.ResultSummaryList.RESULT_SECONDARYAGENT,
					Results.ResultSummaryList.RESULT_SHORTSECONDARYAGENT,
					] if not extra_query else []),
					extra_query
			)
	
	num = 0
	
	for query_conf in [ #collected groups
				("TLS versions", "Support TLS version",
					[	Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_SSLV2, 
						Results.ResultCondition.RESULTC_SUPPORT_SSLV2, 
						Results.ResultCondition.RESULTC_SUPPORT_SSLV2_NO_CIPHER,
						Results.ResultCondition.RESULTC_SUPPORT_HIGHEST_SSLV3, 
						Results.ResultCondition.RESULTC_SUPPORT_TLS_1_0, 
						Results.ResultCondition.RESULTC_SUPPORT_TLS_1_1, 
						Results.ResultCondition.RESULTC_SUPPORT_TLS_1_2
						],
					),
				("Problems with version negotiation", "Problematic servers",
					[
					Results.ResultCondition.RESULTC_VERSIONMIRROR,
					Results.ResultCondition.RESULTC_CLVERSIONSWAP,
					Results.ResultCondition.RESULTC_CLVERSIONRECMATCH,
					]
					),
				("Renego Patching",["Patched servers", "Non-compliant of these", "Unstable", "Does not accept combined Ext/SCSV"],
					[
					Results.ResultCondition.RESULTC_RENEGO,
					Results.ResultCondition.RESULTC_RENEGONONCOMPLIANT,
					Results.ResultCondition.RESULTC_RENEGOUNSTABLE,
					Results.ResultCondition.RESULTC_RENEGOEXTSCSV_INTOL,
					]
					),
				("Session resume",["Number of servers"],
					[
					Results.ResultCondition.RESULTC_RESUMABLE_SESSIONS,
					Results.ResultCondition.RESULTC_NONRESUMABLE_SESSIONS,
					Results.ResultCondition.RESULTC_RESUME_SESSION,
					Results.ResultCondition.RESULTC_NORESUME_SESSION,
					Results.ResultCondition.RESULTC_RESUME_SESSION_OVER,
					Results.ResultCondition.RESULTC_NEW_SESSION_OVER,
					Results.ResultCondition.RESULTC_FAIL_RESUME_SESSION_OVER,
					Results.ResultCondition.RESULTC_SENT_SESSION_TICKETS,
					Results.ResultCondition.RESULTC_RESUMED_SESSION_TICKETS,
					]
				),
				("Client certificates",["Number of servers"],
					[
					Results.ResultCondition.RESULTC_CLIENT_CERT_REQUEST,
					Results.ResultCondition.RESULTC_CLIENT_CERT_REQUIRED,
					Results.ResultCondition.RESULTC_NOCLIENT_CERT_ALERT
					]
				),
				("Renegotiation",["Patched servers", "Unpatched", "total"],
					[(Results.ResultCondition.RESULTC_VALUES_dict[x],[[x,Results.ResultCondition.RESULTC_RENEGO],[x, Results.ResultCondition.RESULTC_NONRENEGO],x]) for x in [
					Results.ResultCondition.RESULTC_PERFORM_RENEGO,
					Results.ResultCondition.RESULTC_ASKED_RENEGO,
					Results.ResultCondition.RESULTC_ACCEPT_RENEGO,
					Results.ResultCondition.RESULTC_ACCEPT_FAKE_RENEGO,
					Results.ResultCondition.RESULTC_ACCEPT_FAKE_START_RENEGO,
					Results.ResultCondition.RESULTC_ACCEPT_HIGH_PREM,
					Results.ResultCondition.RESULTC_ACCEPT_EHIGH_PREM,
					]]
					),
				("ServerName Indication", [ "Sent SNI extension", "Sent SNI warning", "Sent both"],
					[
					Results.ResultCondition.RESULTC_SENT_SNI_EXT,
					Results.ResultCondition.RESULTC_SENT_SNI_WARN,
					[Results.ResultCondition.RESULTC_SENT_SNI_EXT,
						Results.ResultCondition.RESULTC_SENT_SNI_WARN],
					]
					),
				("Certificate Status Extension", "Support Certstatus",
					[
					Results.ResultCondition.RESULTC_SENT_CERT_STATUS,
					]
					),
				("Encryption", "#of servers",
					[
					Results.ResultCondition.RESULTC_SUPPORT_WEAK_CIPHER,
					Results.ResultCondition.RESULTC_SUPPORT_DEPRECATED_CIPHER,
					Results.ResultCondition.RESULTC_SUPPORT_TOONEW_CIPHER,
					Results.ResultCondition.RESULTC_TOLERATE_SSLV2HAND,
					Results.ResultCondition.RESULTC_SSLV2_WEAK_CIPHER,
					Results.ResultCondition.RESULTC_PROBLEM_EXTRAPADDING,
					]
					),
				("DHE keysize","#of servers",
					summary_base.dhe_keysizes.filter(dhe_keysize__gt = 0).order_by("dhe_keysize")
					),
				("Compliance Problems", [ "Have problem in 1.x", "Have problem in 1.x or 2.x"],
					[
					("Version intolerant",
						[Results.ResultCondition.RESULTC_VERSION_INTOLERANT3,
						Results.ResultCondition.RESULTC_VERSION_INTOLERANT]),
					("Version intolerant TLS 1.0-TLS 1.2",
						[Results.ResultCondition.RESULTC_VERSION_INTOLERANT_CURRENT3]),
					("Version intolerant future version",
						[Results.ResultCondition.RESULTC_VERSION_INTOLERANT_FUTURE3,
						Results.ResultCondition.RESULTC_VERSION_INTOLERANT4]),
					("Extension intolerant",
						[Results.ResultCondition.RESULTC_EXTENSION_INTOLERANTX,
						Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT]),
					("Extension intolerant 3.0",
						[Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT30]),
					("Extension intolerant TLS 1.0-TLS 1.2",
						[Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT_C3]),
					("Extension intolerance reversed TLS 1.0-TLS 1.2",
						[Results.ResultCondition.RESULTC_REVERSED_EXTENSION_INTOLERANT]),
					("Version or extension intolerant",
						[Results.ResultCondition.RESULTC_VEROREXT_INTOLERANT]),
					("Version and extension intolerant",
						[Results.ResultCondition.RESULTC_VERANDEXT_INTOLERANT]),
					("Require bad version",
						[Results.ResultCondition.RESULTC_BADVERSION]),
					("No version check",
						[Results.ResultCondition.RESULTC_NOVERSION]),
					("Failed TLS False Start",
						[Results.ResultCondition.RESULTC_FALSE_START_FAILED]),
					("Tested partial record",
						Results.ResultCondition.RESULTC_PARTREC_TESTED),
					("Failed all partial record tests",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_ALL),
					("Failed some partial record tests",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_SOME),
					("Failed partial record zero byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_0),
					("Failed partial record one byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_1),
					("Failed partial record two byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_2),
					("Failed partial record block less one byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_L1),
					("Failed partial record block less two bytes",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_L2),
					("Failed Long Client Hello test", 
						Results.RESULTC_CH_MINLEN_FAILED_256),
					("Failed Long Client Hello test SSL v3", 
						Results.RESULTC_CH_MINLEN_FAILED_256_30),
					("Failed Long Client Hello test TLS 1.0", 
						Results.RESULTC_CH_MINLEN_FAILED_256_31),
					("Failed Long Client Hello test TLS 1.2", 
						Results.RESULTC_CH_MINLEN_FAILED_256_33),
					]
					),
				("Compliance Problems (Renego patched)", [ "Have problem in 1.x", "Have problem in 1.x or 2.x"],
					(Results.ResultCondition.RESULTC_RENEGO,),
					[
					("Version intolerant",
						[Results.ResultCondition.RESULTC_VERSION_INTOLERANT3,
						Results.ResultCondition.RESULTC_VERSION_INTOLERANT]),
					("Version intolerant TLS 1.0-TLS 1.2",
						[Results.ResultCondition.RESULTC_VERSION_INTOLERANT_CURRENT3]),
					("Version intolerant future version",
						[Results.ResultCondition.RESULTC_VERSION_INTOLERANT_FUTURE3,
						Results.ResultCondition.RESULTC_VERSION_INTOLERANT4]),
					("Extension intolerant",
						[Results.ResultCondition.RESULTC_EXTENSION_INTOLERANTX,
						Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT]),
					("Extension intolerant 3.0",
						[Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT30]),
					("Extension intolerant TLS 1.0-TLS 1.2",
						[Results.ResultCondition.RESULTC_EXTENSION_INTOLERANT_C3]),
					("Version or extension intolerant",
						[Results.ResultCondition.RESULTC_VEROREXT_INTOLERANT]),
					("Version and extension intolerant",
						[Results.ResultCondition.RESULTC_VERANDEXT_INTOLERANT]),
					("Require bad version",
						[Results.ResultCondition.RESULTC_BADVERSION]),
					("No version check",
						[Results.ResultCondition.RESULTC_NOVERSION]),
					("Tested partial record",
						Results.ResultCondition.RESULTC_PARTREC_TESTED),
					("Failed all partial record tests",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_ALL),
					("Failed some partial record tests",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_SOME),
					("Failed partial record zero byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_0),
					("Failed partial record one byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_1),
					("Failed partial record two byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_2),
					("Failed partial record block less one byte",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_L1),
					("Failed partial record block less two bytes",
						Results.ResultCondition.RESULTC_PARTREC_FAILED_L2),
					("Failed Long Client Hello test", 
						Results.RESULTC_CH_MINLEN_FAILED_256),
					("Failed Long Client Hello test SSL v3", 
						Results.RESULTC_CH_MINLEN_FAILED_256_30),
					("Failed Long Client Hello test TLS 1.0", 
						Results.RESULTC_CH_MINLEN_FAILED_256_31),
					("Failed Long Client Hello test TLS 1.2", 
						Results.RESULTC_CH_MINLEN_FAILED_256_33),
					("Failed one of the TLS 1.1 or TLS 1.2 Record Protocol version test",
						Results.RESULTC_RECV_ANY_FAILED),
					("Failed the TLS 1.1 Record Protocol version test",
						Results.RESULTC_RECV_32_FAILED),
					("Failed the TLS 1.2 Record Protocol version test",
						Results.RESULTC_RECV_33_FAILED),
					],
					),
				("Specific Extension Intolerance", ["All","Renego patched"],
					([Results.ResultCondition.RESULTC_INTOLERANT_SPECIFIC_EXTENSION],[Results.ResultCondition.RESULTC_RENEGO,Results.ResultCondition.RESULTC_INTOLERANT_SPECIFIC_EXTENSION]),
					Probe.CommonSpecificExtensionIntolerance.objects.distinct().filter(probecommonresult__proberesult__part_of_run=run_item).order_by("intolerant_for_extension")
					),
				("Supported ciphers", "Supported by",
					Probe.CipherName.objects.distinct().filter(id__in = summary_base.CipherSuiteEntries.all()).order_by("ciphername")
					),
				("Supported cipher groups", "Supported by",
					summary_base.CipherSuiteGroupEntries.annotate(suite_count= Count("cipher_suites__cipher_suites__id")).order_by("suite_count", "cipher_suites__cipher_suites_string"),
					False, #Do not show details
					),
			]:
		num += 1
		global debug
		if debug:
			execute_query(query_queue, 0, multiple_pages_writer.GetPageWriter(), summary_base, query_conf, extra_query)
		else:	 
			queue.put([num, multiple_pages_writer.GetPageWriter(), summary_base, query_conf, extra_query])

def do_queries(queue, query_queue, n):
	while True:
		pars = queue.get()
		
		try:
			execute_query(query_queue, *pars)
		except BaseException,error:
			print "Exception for ",n, ":", error

		queue.task_done()					

def do_analysis(queue, n):
	global debug
	
	while True and not debug:
		try:
			do_analysis_step(queue,n)
		except BaseException,error:
			print "Exception for ",n, ":", error
			
		
def do_analysis_step(queue,n):
	(item, summary_base, target_first, target_details, title, hdr, query, waiter) = queue.get()

	global debug
	if debug:	
		print "item2"
	results = summary_base.GetAnalyze(id=n, use_cache=True, **query)
	
	(target, index) = target_first
	target[index] = get_percentage(results["_matching"],results["_total"])
	
	if target_details:
		(target, index) = target_details
		if len(target)<= index:
			pass;
		target[index] = perform_detailed_presentation(title, title + " (" + hdr + ")", results)
	
	
	queue.task_done()					
	waiter.set()

	
def main():

	options_config = OptionParser()
	
	options_config.add_option("--debug", action="store_true", dest="debug")
	options_config.add_option("--verbose", action="store_true", dest="verbose")
	options_config.add_option("--id", action="store", type="int", dest="record_index", default=0)
	options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
	options_config.add_option("--threads", action="store", type="int", dest="threads", default=1)
	
	(options, args) = options_config.parse_args()

	probe_results = Queue.Queue()
	query_queue = Queue.PriorityQueue()
	
	num_probers = options.threads if options else 1
	threads = []
	for i in range(num_probers):
		new_thread = threading.Thread(target=do_queries, args=(probe_results, query_queue,i))
		new_thread.daemon = True
		new_thread.start()
		threads.append(new_thread)
	
	for i in range(num_probers):
		new_thread = threading.Thread(target=do_analysis, args=(query_queue,i))
		new_thread.daemon = True
		new_thread.start()
		threads.append(new_thread)
	
	if options.record_index:
		try:
			run_item = Probe.ProbeRun.objects.get(id=options.record_index);
		except:
			run_item = None

	if options.verbose:
		print "Generating"
	if run_item:
		
		protocols = Probe.ProbeResult.objects.filter(part_of_run = run_item).values_list("servername__protocol", flat=True).distinct()
		
		protocol_list = [x[0] for x in Probe.Server.PROTOCOL_LIST if x[0] in protocols]
		if len(protocol_list) <2:
			protocol_list = []
		mail_protocol_list = [x for x in protocol_list if x != Probe.Server.PROTOCOL_HTTPS]

		for protocol in ([("all",None)]+ protocol_list+ 
						([("mail", mail_protocol_list)] if mail_protocol_list else [])
						):
			fQ=None
			fldr = protocol
			if protocol:
				fQ1 = None
				if isinstance(protocol, tuple):
					fldr = protocol[0]
					if protocol[1]:
						fQ1 = Q(servername__protocol__in = (protocol[1] if isinstance(protocol[1], list) else [protocol[1]]))
				else:
					fQ1 = Q(servername__protocol = protocol)
				if fQ1:
					fQ = fQ | fQ1 if fQ else fQ1
			writer = WritePage(folder=fldr)
			generate_results(probe_results, query_queue, run_item, multiple_pages_writer = writer, extra_query=fQ)

	probe_results.join()
	if options.verbose:
		print "Completed"

	#print result
	#print "=============="
	#print "\n".join([str(x) for x in connection.queries]) 

#debug = True
if debug:
	import cProfile
	
	cProfile.run("main()")
else:
	main()	

	
