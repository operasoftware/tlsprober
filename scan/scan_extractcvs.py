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

'''
Created on 2. okt. 2010

@author: Yngve
'''

"""
Extract a scan result as a CSV list of servernames
"""

import sys,os,subprocess,time,os.path

sys.path.insert(1, os.path.join(".."))
sys.path.insert(1, os.path.join("..","tlslite"))

import libinit

from optparse import OptionParser
import probedb.standalone
import probedb.probedata2.models as ProbeData
import probedb.scanner.models as Scanner
import threading
import socket
from tlslite import TLSConnection, HandshakeSettings
options_config = OptionParser()

options_config.add_option("--run-id", action="store", type="int", dest="run_id", default=0)
options_config.add_option("--testbase2", action="store_true", dest="use_testbase2")
options_config.add_option("--output", action="store", type="string", dest="output_filename", default="output.csv")

(options, args) = options_config.parse_args()

run = Scanner.ScannerRun.objects.get(id=options.run_id)

import csv
file = csv.writer(open(options.output_filename,"wb"))

i=0
for item in run.scannerresults_set.all().iterator():
	i += 1
	file.writerow([i,item.server, item.port, item.protocol])
	if i%100 == 0:
		print i 


