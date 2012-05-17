# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

node default {
    include socorro-db
    include socorro-monitor
    include socorro-php
    include socorro-processor
    include socorro-collector
    include socorro-api
#    include socorro-hbase
    include socorro-elasticsearch
}
