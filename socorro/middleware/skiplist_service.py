# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import web

from socorro.middleware.service import DataAPIService
from socorro.external import (
    MissingArgumentError,
    BadArgumentError
)

logger = logging.getLogger("webapi")


class SkipList(DataAPIService):
    """Return the skip list. """

    service_name = "skiplist"
    uri = "/skiplist/(.*)"

    def __init__(self, config):
        super(SkipList, self).__init__(config)
        logger.debug('SkipList service __init__')

    def get(self, *args):
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.SkipList(config=self.context)
        return impl.get(**params)

    def post(self, *args):
        params = self.parse_query_string(args[0])
        params.update(web.input())

        module = self.get_module(params)
        impl = module.SkipList(config=self.context)

        try:
            impl.post(**params)
        except (MissingArgumentError, BadArgumentError), e:
            raise web.webapi.InternalError(message=str(e))
        except Exception:
            raise

        return True

    def delete(self, *args):
        params = self.parse_query_string(args[0])
        params.update(web.input())

        module = self.get_module(params)
        impl = module.SkipList(config=self.context)

        try:
            return impl.delete(**params)
        except (MissingArgumentError, BadArgumentError), e:
            raise web.webapi.InternalError(message=str(e))
        except Exception:
            raise
