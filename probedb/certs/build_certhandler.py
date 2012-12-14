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
Created on 4. aug. 2010

@author: Yngve
'''

"""
Builds the C++ based certhandler module
"""

from distutils.core import setup, Extension
import os

print os.name

module1 = Extension('certhandler',
                    define_macros = [('MAJOR_VERSION', '1'),
                                     ('MINOR_VERSION', '0')],
                    libraries = ['crypto'] + (["WS2_32", "ADVAPI32", "GDI32","USER32"] if os.name == "nt" else []),
                     sources = ['certhandler.cpp'])

setup (name = 'certhandler',
       version = '1.0',
       description = 'This is the certificate handler APIs',
       author = 'Yngve N. Pettersen, Opera Software ASA',
       author_email = 'yngve@opera.com',
       url = 'http://www.opera.com',
       long_description = 'This is the certificate handler APIs',
       ext_modules = [module1])
