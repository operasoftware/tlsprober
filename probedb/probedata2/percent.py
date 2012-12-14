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

"""Present percentages in various formats, including for a red or green format""" 

def calc_percent(count, groupsize):
	if groupsize == 0:
		return 0.0
	return float(count)/float(groupsize)*100.0
def calc_percent_tuple(count, groupsize, non_zero_is_fail=True):
	return (count, calc_percent(count, groupsize),non_zero_is_fail)

def check_threshold_percent_tuple(value, context):
	if "values" not in context:
		return False
	val = context["values"]
	if len(val) <3:
		return False
	if val[2]:
		return val[0] >0
	else:
		return val[0] <= 0

def setup_redgreen_percent(count, groupsize, non_zero_is_fail=True, link=None, no_color=False):
	val = calc_percent_tuple(count, groupsize, non_zero_is_fail)
	args = {
		"values":val,
		"value":"%.1f%% (%d)" % (val[1], val[0]),
		"treshold":check_threshold_percent_tuple,
		"red_is_low": not non_zero_is_fail,
		"color": not no_color,
		}
	if link:
		args["link"]=link
		
	return args
