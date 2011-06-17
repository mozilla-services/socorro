import logging
logger = logging.getLogger("webapi")

import socorro.webapi.webapiService as webapi

class Search(webapi.JsonServiceBase):
	"""
	Search API interface

	Handles the /search API entry point, parses the parameters, and
	calls the API implementation to execute the query.
	"""

	def __init__(self, configContext):
		"""
		Constructor
		"""
		super(Search, self).__init__(configContext)
		self.apiImpl = configContext.searchImplClass(configContext)
		logger.debug('Search __init__')


	uri = '/201105/search/([^/.]*)/(.*)'

	def get(self, *args):
		"""
		Called when a get HTTP request is executed to /search
		"""
		params = self._parseQueryString(args[1])
		types = args[0]
		return self.apiImpl.search(types, **params)


	def _parseQueryString(self, queryString):
		termsSeparator = "+"
		paramsSeparator = "/"

		args = queryString.split(paramsSeparator)

		params = {}
		for i in xrange(0, len(args), 2):
			if args[i] and args[i+1]:
				params[ args[i] ] = args[i+1]

		for i in params:
			if params[i].find(termsSeparator) > -1:
				params[i] = params[i].split(termsSeparator)

		return params
