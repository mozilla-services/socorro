# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This module represents the refactoring of an original dbaron correlation
script into a Socorro TransformRule.  This rule will be applied to a stream
of crashes flowing through a Fetch Transform Save app such as a Processor."""

import re
import os.path
import sys
import json

from contextlib import contextmanager
from collections import defaultdict


from configman import Namespace, RequiredConfig

from socorro.analysis.correlations.correlations_rule_base import (
    CorrelationRule,
    CorrelationsStorageBase,
)
from socorrolib.lib.util import DotDict as SocorroDotDict
from socorrolib.lib.converters import change_default


#==============================================================================
class CorrelationCoreCountRule(CorrelationRule):
    """this class attempts to be a faithful reproduction of the function of
    the original dbaron the "per-crash-core-count.py" application embodied as
    a Socorro TransformRule.

    Individual crashes will be offered to this rule by a Fetch Transform Save
    app through the "_action_" method.  This class will examine the crash and
    to counters build on an instance of a ProductVersionMapping.  The counter
    add structure it builds looks like this:

    a_product_version_mapping[product_version*]
        .osyses[operating_system_name*]
            .count
            .signature[a_signature*]
                .count
                .core_counts[number_of_cores*]
            .core_counts[number_of_cores*]


    """
    required_config = Namespace()
    required_config.namespace('output')
    required_config.output.output_class = change_default(
        CorrelationRule,
        'output.output_class',
        'socorro.analysis.correlations.core_count_rule'
            '.FileOutputForCoreCounts',
        new_reference_value='global.correlations.core'
    )

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def __init__(self, config=None, quit_check_callback=None):
        super(CorrelationCoreCountRule, self).__init__(
            config,
            quit_check_callback
        )
        for an_accumulator in self.counters_for_all_producs_and_versions.values():
            an_accumulator.osyses = {}
        self.date_suffix = defaultdict(int)

    #--------------------------------------------------------------------------
    def summary_name(self):
        return 'core-counts'

    #--------------------------------------------------------------------------
    def _action(self, raw, dumps, crash, processor_meta):
        self.date_suffix[crash['crash_id'][-6:]] += 1
        if not "os_name" in crash:
            # We have some bad crash reports.
            return False

        # give the names of the old algorithm's critical variables to their
        # variables in the new system
        # what does "osyses" mean?  this is the original variable name from
        # the dbaron correlation scripts for a mapping of each os name to the
        # counters for the signatures & crashes for that os.
        try:
            osyses = self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].osyses
            self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].counter += 1
        except (AttributeError, KeyError):
            osyses = {}
            self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].osyses = osyses
            self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].counter = 1
        options = self.config

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # begin - original unaltered code section
        # to not introduce errors, this code was not refactored to produce more
        # comprehensible variable names or adopt current style guides.
        # glossary of names:
        #     osyses - a mapping keyed by the name of an OS
        #     osys - the counter structure for an individual OS
        #     signame - a signature
        #     signature - the counter structure for a signature
        #     accumulate_objs = a list of counter structures
        #     obj = a counter as a loop variable
        #     crash = a socorro processed crash
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        osname = crash["os_name"]
        # The os_version field is way too specific on Linux, and we don't
        # have much Linux data anyway.
        if options.by_os_version and osname != "Linux":
            osname = osname + " " + crash["os_version"]
        osys = osyses.setdefault(osname,
                                 { "count": 0,
                                   "signatures": {},
                                   "core_counts": {} })
        signame = crash["signature"]
        if re.search(r"\S+@0x[0-9a-fA-F]+$", signame) is not None:
            if options.condense:
                # Condense all signatures in a given DLL.
                signame = re.sub(r"@0x[0-9a-fA-F]+$", "", signame)
        if "reason" in crash and crash["reason"] is not None:
            signame = signame + "__reason__" + crash["reason"]
        signature = osys["signatures"].setdefault(signame,
                                                  { "count": 0,
                                                    "core_counts": {} })
        accumulate_objs = [osys, signature]

        for obj in accumulate_objs:
            obj["count"] = obj["count"] + 1

        if "json_dump" in crash and "system_info" in crash["json_dump"]:
            family = crash["json_dump"]["system_info"]["cpu_arch"]
            details = crash["json_dump"]["system_info"]["cpu_info"]  # unused?
            cores = crash["json_dump"]["system_info"]["cpu_count"]
            infostr = family + " with " + str(cores) + " cores"
            # Increment the global count on osys and the per-signature count.
            for obj in accumulate_objs:
                obj["core_counts"][infostr] = \
                    obj["core_counts"].get(infostr, 0) + 1
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # end - original unaltered code section
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        return True

    #--------------------------------------------------------------------------
    def _summary_for_a_product_version_pair(self, an_accumulator):
        """in the original code, the counter structures were walked and
        manipulated to form the statistics.  Once a stat was determined,
        it was printed to stdout.  Since we want to have various means of
        outputting the data, instead of printing to stdout, this method
        save the statistic in a "summary_structure"  This structure will
        later be walked for printing or output to some future storage scheme

        The summary structure looks like this:

        summary[product_version*]
            .note - a list of comments by the algorithm
            [os_name]
                .count
                .signatures[signame*]
                    .name
                    .count
                    .cores[number_of_cores]
                        .in_sig_count
                        .in_sig_ratio
                        .rounded_in_sig_ratio
                        .in_os_count
                        .in_os_ratio
                        .rounded_in_os_ratio

        """
        pv_summary = {
            'notes': [],
        }
        if (len(self.date_suffix) > 1):
            message = (
                "crashes from more than one day %s" %
                str(tuple(self.date_suffix.keys()))
            )
            pv_summary['notes'].append(message)
        pv_summary['date_key'] = self.date_suffix.keys()[0]

        MIN_CRASHES = self.config.min_crashes
        osyses = an_accumulator.osyses

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # begin - minimally altered section from original code
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        infostr_re = re.compile("^(.*) with (\d+) cores$")

        #----------------------------------------------------------------------
        def cmp_infostr(x, y):
            (familyx, coresx) = infostr_re.match(x).groups()
            (familyy, coresy) = infostr_re.match(y).groups()
            if familyx != familyy:
                return cmp(familyx, familyy)
            return cmp(int(coresx), int(coresy))

        #----------------------------------------------------------------------
        sorted_osyses = osyses.keys()
        sorted_osyses.sort()

        for osname in sorted_osyses:
            osys = osyses[osname]

            pv_summary[osname] = SocorroDotDict()
            pv_summary[osname].count = osys['count']
            pv_summary[osname].signatures = {}

            sorted_signatures = [sig for sig in osys["signatures"].items()
                                 if sig[1]["count"] >= MIN_CRASHES]
            sorted_signatures.sort(
                key=lambda tuple: tuple[1]["count"],
                reverse=True
            )
            sorted_cores = osys["core_counts"].keys()
            # strongly suspect that sorting is useless here
            sorted_cores.sort(cmp=cmp_infostr)
            for signame, sig in sorted_signatures:
                pv_summary[osname].signatures[signame] = SocorroDotDict({
                    'name': signame,
                    'count': sig['count'],
                    'cores': {},
                })
                by_number_of_cores = \
                    pv_summary[osname].signatures[signame].cores
                for cores in sorted_cores:
                    by_number_of_cores[cores] = SocorroDotDict()
                    in_sig_count = sig["core_counts"].get(cores, 0)
                    in_sig_ratio = float(in_sig_count) / sig["count"]
                    in_os_count = osys["core_counts"][cores]
                    in_os_ratio = float(in_os_count) / osys["count"]

                    rounded_in_sig_ratio = int(round(in_sig_ratio * 100))
                    rounded_in_os_ratio = int(round(in_os_ratio * 100))
                    by_number_of_cores[cores].in_sig_count = in_sig_count
                    by_number_of_cores[cores].in_sig_ratio = in_sig_ratio
                    by_number_of_cores[cores].rounded_in_sig_ratio = \
                        rounded_in_sig_ratio
                    by_number_of_cores[cores].in_os_count = in_os_count
                    by_number_of_cores[cores].in_os_ratio = in_os_ratio
                    by_number_of_cores[cores].rounded_in_os_ratio = \
                        rounded_in_os_ratio
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # end - minimally altered code section
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        return pv_summary

    #--------------------------------------------------------------------------
    def summarize(self):
        # for each product version pair in the accumulators
        summary = {}
        for pv, counters_for_pv in self.counters_for_all_producs_and_versions.iteritems():
            summary['_'.join(pv)] = self._summary_for_a_product_version_pair(
                counters_for_pv
            )
        return summary


#==============================================================================
class StdOutOutputForCoreCounts(CorrelationsStorageBase):
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def store(
        self,
        key,
        payload,
        prefix=None,
        name=None,
        suffix=None,
        template=None
    ):
        print "# --------------------------------------------------------------"
        print "# output divider for 20%s-%s-core-counts.txt" % (
            payload["date_key"],
            key
        )
        print "# --------------------------------------------------------------"
        self.output_correlations_to_stream(payload, sys.stdout)

    #--------------------------------------------------------------------------
    def output_correlations_to_stream(self, payload, stream):
        for an_os, os_counts in sorted(payload.iteritems()):
            if an_os == 'date_key' or an_os == 'notes':
                continue

            print >>stream, an_os.encode("UTF-8")
            counts_by_signature = os_counts.signatures
            for a_signature, signature_counts in sorted(
                counts_by_signature.iteritems()
            ):
                print >>stream, (
                    u"  %s (%d crashes)"
                    % (a_signature, signature_counts.count)
                ).encode("UTF-8")
                for cores, core_counts in sorted(signature_counts.cores.iteritems()):
                    print >>stream, u"    {0:3d}% ({1:d}/{2:d}) vs. {3:3d}% ({4:d}/{5:d}) {6}" \
                        .format(
                            core_counts.rounded_in_sig_ratio,
                            core_counts.in_sig_count,
                            signature_counts.count,  # orignally sig
                            core_counts.rounded_in_os_ratio,
                            core_counts.in_os_count,
                            os_counts.count,  # originally osys
                            cores
                        ).encode("UTF-8")
                print >>stream, ''  # blank line between signatures
            print >>stream, ''  # blank line between OS


#==============================================================================
class FileOutputForCoreCounts(StdOutOutputForCoreCounts):
    required_config = Namespace()
    required_config.add_option(
        'path',
        doc="a files system path into which to store correlations",
        default='/mnt/crashanalysis/crash_analysis',
        reference_value_from='global.correlations'
    )
    required_config.add_option(
        'path_template',
        doc="a template from which to make a pathname",
        default='{path}/{prefix}/{prefix}_{key}-{name}.txt',
        reference_value_from='global.correlations.core'
    )

    #--------------------------------------------------------------------------
    def store(
        self,
        counts_summary_structure,
        **kwargs
    ):
        template_args = {
            'path': self.config.path,
        }
        template_args.update(kwargs)
        pathname = self.config.path_template.format(**template_args)
        pathname = pathname.replace('//', '/')
        path, filename = tuple(os.path.split(pathname))
        try:
            os.makedirs(path)
        except OSError:
            # path already exists, we can ignore and move on
            pass
        with open(pathname, 'w') as f:
            self.output_correlations_to_stream(counts_summary_structure, f)


#==============================================================================
class JsonFileOutputForCoreCounts(FileOutputForCoreCounts):
    required_config = Namespace()
    required_config.path_template = change_default(
        FileOutputForCoreCounts,
        'path_template',
       '{path}/{prefix}/{prefix}_{key}-{name}.json',
    )

    #--------------------------------------------------------------------------
    def output_correlations_to_stream(self, counts_summary_structure, stream):
        json.dump(
            counts_summary_structure,
            stream,
            indent=4,
            sort_keys=True
        )
