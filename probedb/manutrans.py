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


from django.db import transaction
from functools import wraps

def commit_manually_if_unmanaged(func):
	"""
	A decorator for database actions, which allows the caller to
	specify that if the current transaction is not managed, then 
	the called function will commit manually 
	""" 
	def _commit_manually_if_unmanaged(*args, **kw):
		is_managed = transaction.is_managed()
		if not is_managed:
			try:
				transaction.enter_transaction_management()
				transaction.managed(False)
				return func(*args, **kw)
			finally:
				transaction.leave_transaction_management()
		else:
			return func(*args, **kw)

	return wraps(func)(_commit_manually_if_unmanaged)
