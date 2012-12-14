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

# Django settings for probedb project.
#from django.conf.global_settings import * 
import os
import sys

if "--testbase2" in sys.argv:
	testbase2 = True
else:
	testbase2 = False

computername =  os.environ.get('COMPUTERNAME',"any").lower()

DEBUG = False
	
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'somebody_fill_me_in'),
)

MANAGERS = ADMINS

#define your database here (may have to change it for Django 1.2+)
DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'somebody_fill_me_in'             # Or path to database file if using sqlite3.
DATABASE_USER = 'somebody_fill_me_in'             # Not used with sqlite3.
DATABASE_PASSWORD = 'somebody_fill_me_in'         # Not used with sqlite3.
DATABASE_HOST = 'somebody_fill_me_in'             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = '5432' if not testbase2 else '15432'   # Set to empty string for default. Not used with sqlite3.
DATABASE_OPTIONS = {}
	
	

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'CET'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'Zo^lo+ph5!ie1#ieX%iXe*e\r6ioh-a8OhW$Eim@agh9+Aex7Ei{s'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'probedb.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #"C:/Python26/Lib/site-packages/django/contrib/admin/templates/admin",
)

INSTALLED_APPS = (
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.sites',
	'django.contrib.admin',
	'probedb.probedata2',
	'probedb.resultdb2',
	'probedb.cluster',
	'probedb.certs',
	'probedb.scanner',
	'probedb.batch',
)
