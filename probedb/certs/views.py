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

import probedb.certs.models as Certs

def cert_summary(request):
	"""Prints a summary of certificates found in the database"""

	import probedb.certs.certhandler as certhandler

	
	q = Certs.CertAttributes.objects.all()
	
	results = {
			"summary_tables":[
				(["Item", "Count"], 
					[
					("Uses Netscape HostName extension", [q.filter(IsNetscapeName=True).count()]),
					("Netscape extention in Common",[q.filter(IsNetscapeName=True,NetscapeInCommon=True).count()]),
					]
					),
				(["NetscapeNames", "In common", "Name","Subject","Issuer","Selfsigned","Match"],
					[((x.NetscapeName.hostname if x.NetscapeName else x.id), [
												x.NetscapeInCommon, 
												certhandler.Certificate(x.cert.certificate_b64).ExtractHostnames().get("Netscape ServerName",None), 
												certhandler.Certificate(x.cert.certificate_b64).SubjectNameLine(), 
												certhandler.Certificate(x.cert.certificate_b64).IssuerNameLine(), 
												certhandler.Certificate(x.cert.certificate_b64).IsSelfSigned(), 
												(certhandler.Certificate(x.cert.certificate_b64).SubjectNameLine()== 
												certhandler.Certificate(x.cert.certificate_b64).IssuerNameLine())
												]) for x in q.filter(IsNetscapeName=True) ]),
						]
			
			
			}
	
	return render_to_response("certsummary.html", results)
 
