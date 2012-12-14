
from django import template

register = template.Library()

def get_protocol_count_value(context, source, fieldname):
	""" {% get_protocol_count_value source fieldname %}
		"""
		
	return {"value":getattr(getattr(context["object"], source), fieldname).count()}

register.inclusion_tag("count_value.html",takes_context=True)(get_protocol_count_value)

def get_count_value(context, fieldname):
	""" {% get_count_value source fieldname %}
		"""
		
	return {"value":getattr(context["object"], fieldname).count()}

register.inclusion_tag("count_value.html",takes_context=True)(get_count_value)