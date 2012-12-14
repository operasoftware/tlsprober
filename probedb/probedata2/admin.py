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

from django.contrib import admin
from probedata2.models import *
from proberun import ProbeRunSort

#admin.site.register(Server)
#admin.site.register(ProbeResultEntry)
admin.site.register(CipherName)
#admin.site.register(ProbeResult)
admin.site.register(ProbeRunSort)
admin.site.register(ProbeRun)
#admin.site.register(ProbeQueue)
#admin.site.register(PrimaryServerAgent)
#admin.site.register(SecondaryServerAgent)
#admin.site.register(Certificate)
admin.site.register(PreparedQueueList)
#admin.site.register(PreparedQueueItem)


class IP_adress_admin(admin.ModelAdmin):
	search_fields = ["ip_address"]
	 
admin.site.register(IP_Address, IP_adress_admin)


class ServerIP_probed_admin(admin.ModelAdmin):
	search_fields = ["ip_address__ip_address"]

#admin.site.register(ServerIPProbed, ServerIP_probed_admin)


class ServerDomain_admin(admin.ModelAdmin):
	search_fields = ["domain_name"]
	list_display = ("full_domain_name", "domain_name", "level", "domain_parent")

#admin.site.register(ServerDomain, ServerDomain_admin)

class Server_admin(admin.ModelAdmin):
	list_display = ("servername", "port", "alexa_rating")
	search_fields=("servername",)

admin.site.register(Server, Server_admin)
