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



import csv

class Alexa:
	"""List of Alexa top million domains""" 
	def __init__(self,file_name):
		self.alexa = {}
		for line in csv.reader(open(file_name)):
			if len(line) >1:
				host = line[1]
				index = line[0]
				self.alexa[host] = index
	
	def IsAlexaSite(self,hostname):
		"""return Alexa ranking for a hostname"""
		labels = hostname.split(".")
		for i in range(len(labels)-1):
			index = self.alexa.get(".".join(labels[i:]),-1)
			if index > 0:
				return index
		
		return 0 


if __name__ == '__main__': 
	
	alexa_list = Alexa("top-1m.csv")

	assert(alexa_list)
	assert(alexa_list.IsAlexaSite("google.com")>0)
	assert(alexa_list.IsAlexaSite("www.google.com")>0)
	
	print "PASS"
