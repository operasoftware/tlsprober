
#from django.conf import global_settings as g_settings
from django.core.management import setup_environ
import settings
setup_environ(settings)
from django.conf.urls.defaults import *
