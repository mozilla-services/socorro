# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from contextlib import contextmanager
from collections import (
    MutableMapping,
    Sequence,
    defaultdict
)

from configman import (
    Namespace,
    RequiredConfig
)
from configman.converters import (
    to_str,
    class_converter
)

from socorro.lib.transform_rules import Rule
from socorro.lib.util import DotDict as SocorroDotDict


#------------------------------------------------------------------------------
def minimum_count_for_summary_threhold_fn(
    global_config,
    local_config,
    unused_extra_args
):
    """a configman aggregation method - set a config-like value to
    determine how many crashes of a type to be included in the correlation
    summary report.  See the 'min_crashes' configman aggregation definition
    in the class CorrelationRule
    """
    if global_config.number_of_submissions == "all":
        return local_config.min_count_for_inclusion
    return 1


#==============================================================================
class CorrelationRule(Rule):
    required_config = Namespace()
    required_config.add_option(
        "min_count_for_inclusion",
        doc='the minimum number of crashes need to be included '
            'in summary report, used only if --number_of_submissions is '
            'not set to "all"',
        default=10,
        reference_value_from='global.correlation',
    )
    required_config.add_aggregation(
        'min_crashes',
        # the minimum number of crashes to consider for a P/V to participtate
        # in the summary report.  it is set to the value of
        # "min_count_for_inclusion" if -number_of_submissions is set to "all",
        # otherwise it is 1 - this is mainly used for sampled runs or testing
        minimum_count_for_summary_threhold_fn
    )
    required_config.add_option(
        "by_os_version",
        doc="Group reports by *version* of operating system",
        default=False
    )
    required_config.add_option(
        "condense",
        doc="Condense signatures in modules we don't have symbols for",
        default=False
    )
    required_config.namespace('output')
    required_config.output.add_option(
        'output_class',
        doc="fully qualified Python path for the output",
        default='',
        likely_to_be_changed=True,
        from_string_converter=class_converter,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config=None, quit_check_callback=None):
        super(CorrelationRule, self).__init__(config, quit_check_callback)
        self.counters_for_all_producs_and_versions = ProductVersionMapping(
            (),
            SocorroDotDict
        )

    #--------------------------------------------------------------------------
    def summary_name(self):
        return to_str(self.__class__)

    #--------------------------------------------------------------------------
    def close(self):
        self.config.logger.debug(
            'compiling summary for %s',
            self.summary_name()
        )
        summary = self.summarize()

        with self.config.output.output_class(
            self.config.output
        )() as storage:
            for product_and_version, summary_counts in summary.iteritems():
                storage.store(
                    summary_counts,
                    key=product_and_version,
                    prefix="20" + summary_counts["date_key"],
                    name=self.summary_name()
                )


#==============================================================================
class ProductVersionMapping(MutableMapping):
    """this class is used to as a Mapping to hold multiple copies of the
    working counter structures in the correlations reports.  It is keyed by
    a product/version pair. Hierarchical in nature, 'product' is the lowest
    level key, followed by 'version'.  The Correlation rules will build a
    nested mapping many level deeps with this structure at its root.  Many
    levels of the nested mapping will contain counters used to tally the
    occurance of values or states within the stream of crashes flowing through
    the Correlation App.

    For an example of the counter structures build on this collection, see
    the docs in the individual correlation rule definitions.
    """
    #--------------------------------------------------------------------------
    def __init__(self, pv_tuple_initializer=None, value_type=None):
        self.pv_tuples = pv_tuple_initializer
        if value_type:
            self.products = defaultdict(lambda: defaultdict(value_type))
        else:
            self.products = defaultdict(dict)
        for product, version in pv_tuple_initializer:
            self.products[product][version] = \
                value_type() if value_type is not None else None

    #--------------------------------------------------------------------------
    def __str__(self):
        return json.dumps(self.products)

    #--------------------------------------------------------------------------
    def __getitem__(self, key):
        if isinstance(key, basestring):
            return self.products[key]
        elif isinstance(key, Sequence):
            product, version = key
            return self.products[product][version]
        else:
            raise KeyError(key)

    #--------------------------------------------------------------------------
    def __setitem__(self, key, value):
        if isinstance(key, basestring):
            raise KeyError(key)
        elif isinstance(key, Sequence):
            product, version = key
            self.products[product][version] = value
        else:
            raise KeyError(key)

    #--------------------------------------------------------------------------
    def __delitem__(self, key, value):
        if isinstance(key, basestring):
            raise KeyError(key)
        elif isinstance(key, Sequence):
            product, version = key
            del self.products[product][version]
            if not len(self.products[product]):
                del self.products[product]
        else:
            raise KeyError(key)

    #--------------------------------------------------------------------------
    def __len__(self):
        length = 0
        for version in self.products.values():
            length += len(version)
        return length

    #--------------------------------------------------------------------------
    def __iter__(self):
        for product, verisons in self.products.iteritems():
            for version in self.products[product].keys():
                yield (product, version)

    #--------------------------------------------------------------------------
    def __contains__(self, key):
        if isinstance(key, basestring):
            return key in self.products
        elif isinstance(key, Sequence):
            product, version = key
            return version in self.products[product]
        else:
            raise KeyError(key)

    #--------------------------------------------------------------------------
    def __keys__(self):
        return tuple(x for x in self)

    #--------------------------------------------------------------------------
    def __items__(self):
        return tuple((x, self[x]) for x in self)

    #--------------------------------------------------------------------------
    def __values__(self):
        return tuple(self[x] for x in self)

    #--------------------------------------------------------------------------
    def get(self, key, default=None):
        if key in self:
            return self.__getitem__(key)
        return default

    #--------------------------------------------------------------------------
    def __eq__(self, other):
        return self.__items__() == other.__items__()

    #--------------------------------------------------------------------------
    def __ne__(self, other):
        return self.__items__() != other.__items__()


#==============================================================================
class CorrelationsStorageBase(RequiredConfig):
    """this is the base class for the correlation storage system. It defines the
    base API for storing correlation summary information.  Derived classes
    must override the 'store' method to save the correlation summary structure
    for a given correlation report.

    To see the structure of the correlation summary, see the documenation within
    the individual CorrelationRule classes themselves."""
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config

    #--------------------------------------------------------------------------
    def store(self, product_version, correlation_summary, name):
        raise NotImplementedError

    #--------------------------------------------------------------------------
    def close(self):
        # assume nothing needs to be done to close
        pass

    #--------------------------------------------------------------------------
    @contextmanager
    def __call__(self):
        yield self
        self.close()
