# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Spits out crash ids for all crash reports in Elasticsearch that have a
TelemetryClientId field.

Usage:

    python 1610520/es_tcid.py > crashids.txt

It prints some lines with a "#" to make it easier to see what it did. To
remove those, do:

    python 1610520/es_tcid.py | grep -v "#" > crashids.txt

"""

import json

from configman import ConfigurationManager
from configman.environment import environment
from elasticsearch_dsl import Search

from socorro.external.es.connection_context import ConnectionContext


def get_es_conn():
    # Create a configuration manager that will only check the environment for
    # configuration and not command line parameters

    cm = ConfigurationManager(
        ConnectionContext.get_required_config(), values_source_list=[environment]
    )
    config = cm.get_config()
    return ConnectionContext(config)


def cmd_list_crashids():
    es_conn = get_es_conn()
    indices = es_conn.get_indices()

    print("# %s indexes." % len(indices))
    print("# %r" % indices)
    total = 0
    for index in indices:
        print("# working on %s..." % index)
        with es_conn() as conn:
            search = Search(using=conn, index=index, doc_type=es_conn.get_doctype())
            search = search.filter("exists", field="TelemetryClientId")
            search = search.fields(["processed_crash.uuid"])
            results = search.scan()
            for hit in results:
                print(json.dumps(
                    {"crashid": hit["processed_crash.uuid"][0], "index": index}
                ))
                total += 1

    print("# total found %d" % total)


def main():
    cmd_list_crashids()


if __name__ == "__main__":
    main()
