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
Update the Alexa numbers of server names, always uses the 
file top-1m.csv as the source
"""


import probedb.standalone
import probedb.probedata2.models as Probe

import alexa


import threading
import Queue, time

num_probers = 20
alexa_queue = Queue.Queue()
progress_queue = Queue.Queue()
active = True
alexa_list = alexa.Alexa("top-1m.csv")


def __ProgressCounter(queue):
	i=0
	while True:
		queue.get()

		i += 1
		if i%100 == 0:
			print "Updated ", i, "domains so far"


def do_save(tid,alexa_queue, progress_queue):

	while True :
		(domain, rating) = alexa_queue.get()
		
		Probe.Server.objects.filter(servername = domain).update(alexa_rating=rating)
		
		for x in Probe.ServerDomain.objects.filter(full_domain_name= domain):
			x.server_set.all().update(alexa_rating=rating)
		
		progress_queue.put(True)
		alexa_queue.task_done()


threads = [] 
for i in range(num_probers):
	new_thread = threading.Thread(target=do_save, args=(i,alexa_queue, progress_queue))
	new_thread.daemon = True
	threads.append(new_thread)
	new_thread.start()

progress_thread = threading.Thread(target=__ProgressCounter, args=(progress_queue,))
progress_thread.daemon = True
progress_thread.start()

Probe.Server.objects.exclude(alexa_rating=0).update(alexa_rating=0)

for x,v in alexa_list.alexa.iteritems():
	alexa_queue.put((x,v), block=True)

alexa_queue.join()
progress_queue.join()
