
from django import template

register = template.Library()

def get_count_value(context, fieldname):
	""" {% get_count_value fieldname %}
		"""
	return {"value":fieldname}

