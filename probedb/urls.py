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

from django.conf.urls.defaults import *
from django.views.generic import list_detail		
from probedata2.views import * 
from resultdb2.views import * 
from certs.views import *
import sys
import os.path

sys.path.insert(1, os.path.join(".."))
sys.path.insert(1, os.path.join("..","tlslite"))

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
	# Example:
	# (r'^probedb/', include('probedb.foo.urls')),

	# Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
	# to INSTALLED_APPS to enable admin documentation:
	# (r'^admin/doc/', include('django.contrib.admindocs.urls')),

	# Uncomment the next line to enable the admin:
	(r'^admin/', include(admin.site.urls)),
	 
	#(r'^runs/$', list_detail.object_list, run_list_info),
		
	#(r'^runs/details/([0-9]+)$', run_details_info),
	#(r'^runs/details/([0-9]+)/(\w+)(/alexa)?$', run_details_field_list),
	
	#(r'^results/$', list_detail.object_list, result_list_info),
	#(r'^results/details/(?P<object_id>[0-9]+)$', result_details_info),

	#(r'^results/summaries/$', list_detail.object_list, result_summaries_info),
	#(r'^results/summary/(?P<object_id>[0-9]+)$',result_summary_info),

	#(r'^security/$', list_detail.object_list, run_list_info),
	
	#(r'^certs/summary$', cert_summary),
	(r'^$', SearchResults),
	url(r'^get$', SearchResults, kwargs={"method":"GET"}),
	(r'^search$', SearchResults_doSearch),
	(r'^showprofile/(?P<object_id>[0-9]+)$', PresentProfile),
	
)
