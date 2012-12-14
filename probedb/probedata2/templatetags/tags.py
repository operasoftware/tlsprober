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


from django import template

register = template.Library()


@register.inclusion_tag("rg_number.html")
def redgreen(collection):
	""" {% redgreen collection %}
		render collection.value with a red or green text, 
		depending on parameters, optionally with a link.
		
		collection.value value to be rendered 
		collection.treshold : highest level for which one color apply, default 0. 
				if callable threshold(value, collection) return True if the level is above threshold
		collection.red_is_low: Default False. If True red is used for values below 
				or at the threshold, green for the rest, and vice versa if False
		collection.color: True if colors are to be displayed
		collection.link: If present contain a URL to be linked to
		"""
	if not collection:
		return {"valid":False}
	
	if not isinstance(collection,dict):
		return {"valid":True, "text":collection, "show_red":False, "debug":collection, "color":False}
	
	if not collection or "value" not in collection:
		return {"valid":False}
	
	value = collection["value"]
	treshold = collection.get("treshold", 0)
	low_is_red = collection.get("red_is_low", False)
	color = collection.get("color", True)
	
	if callable(treshold):
		above_treshold = treshold(value, collection)
	else:
		above_treshold = value > treshold
	
	if above_treshold:
		show_red = not low_is_red
	else:
		show_red = low_is_red
		
	args = {
			"valid":True,
			"text":value, 
			"show_red":show_red,
			"color":color, 
			"debug":(value, low_is_red, above_treshold, collection.get("values",None))
			}
	if "link" in collection:
		args["link"] = collection["link"];
	
	return args


@register.inclusion_tag("color_value.html")
def color_value(collection):
	""" {% color_value collection %}
		render collection.value with the assigned color 
		depending on parameters, optionally with a link.
		
		collection.value value to be rendered 
		collection.textcolor :  The color to be used
				if callable textcolor_fun(value, collection) return the text and color based on the value as (text, color)
		collection.link: If present contain a URL to be linked to
		"""
		
	if not collection:
		return {"valid":False}
	
	if not isinstance(collection,dict):
		return {"valid":True, "text":collection, "color":None, "debug":collection}
	
	if not collection or "value" not in collection:
		return {"valid":False}
	
	value = collection["value"]
	color = collection.get("textcolor", None)
	
	if callable(color):
		(value, color) = color(value, collection)
	
	args = {
			"valid":True,
			"text":value, 
			"color":color,
			"debug":(value, color, collection.get("color", None), collection.get("values",None))
			}
	if "link" in collection:
		args["link"] = collection["link"];
	
	return args

