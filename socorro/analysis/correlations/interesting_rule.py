# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This module represents the refactoring of an original dbaron correlation
script into a Socorro TransformRule.  This rule will be applied to a stream
of crashes flowing through a Fetch Transform Save app such as a Processor."""

import re
import os.path
import json

from collections import defaultdict

from configman import Namespace

from socorrolib.lib.converters import (
    change_default,
)
from socorrolib.lib.util import DotDict as SocorroDotDict
from socorro.analysis.correlations.correlations_rule_base import (
    CorrelationRule,
    CorrelationsStorageBase,
)

import macdebugids
import addonids


#==============================================================================
class CorrelationInterestingModulesRule(CorrelationRule):
    """this class attempts to be a faithful reproduction of the function of
    the original dbaron the "per-crash-interesting-modules.py" application
    embodied as a Socorro TransformRule.

    Individual crashes will be offered to this rule by a Fetch Transform Save
    app through the "_action_" method.  This class will examine the crash and
    to counters build on an instance of a ProductVersionMapping.  The counter
    add structure it builds looks like this:

    pv_counters[os_name*]
        .count
        .signatures[a_signature*]
           .count
           .modules[a_module*]
               .count
               .versions[a_version*] int
        .modules[a_module*]
            .count
            .versions[a_version*] int


    """
    required_config = Namespace()
    required_config.add_option(
        "show_versions",
        doc="Show data on module versions",
        default=False
    )
    required_config.add_option(
        "addons",
        doc="Tabulate addons (rather than modules)",
        default=False
    )
    required_config.add_option(
        "min_baseline_diff",
        doc="a floating point number",
        default=0.05
    )
    required_config.namespace('output')
    required_config.output.output_class = change_default(
        CorrelationRule,
        'output.output_class',
        'socorro.analysis.correlations.interesting_rule'
        '.FileOutputForInterestingModules',
        new_reference_value='global.correlations.interesting'
    )

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def __init__(self, config=None, quit_check_callback=None):
        super(CorrelationInterestingModulesRule, self).__init__(
            config,
            quit_check_callback
        )
        for an_accumulator in self.counters_for_all_producs_and_versions.values():
            an_accumulator.osyses = {}
        self.date_suffix = defaultdict(int)
        self.summary_names = {
            #(show_versions, addons)
            (False, False): 'interesting-modules',
            (True, False): 'interesting-modules-with-versions',
            (False, True): 'interesting-addons',
            (True, True): 'interesting-addons-with-versions',
        }

    #--------------------------------------------------------------------------
    def summary_name(self):
        return self.summary_names[(
            self.config.show_versions,
            self.config.addons,
        )]

    #--------------------------------------------------------------------------
    @staticmethod
    def contains_bare_address(a_signature):
        return re.search(r"\S+@0x[0-9a-fA-F]+$", a_signature) is not None

    #--------------------------------------------------------------------------
    @staticmethod
    def remove_bare_address_from_signature(a_signature):
        return re.sub(r"@0x[0-9a-fA-F]+$", "", a_signature)

    #--------------------------------------------------------------------------
    def _action(self, raw, dumps, crash, processor_meta):
        self.date_suffix[crash['crash_id'][-6:]] += 1
        if not "os_name" in crash:
            # We have some bad crash reports.
            return False

        # give the names of the old algorithm's critical variables to their
        # variables in the new system
        try:
            osyses = self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].osyses
            self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].counter += 1
        except (AttributeError, KeyError):
            # why both types? crashes can be represented by either the Socorro
            # or configman DotDict types which raise different exception on
            # not finding a key.
            osyses = {}
            self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].osyses = osyses
            self.counters_for_all_producs_and_versions[
                (crash["product"], crash["version"])
            ].counter = 1

        options = self.config

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # begin - refactored code section
        # unlike the "core count correlation report", this code from the
        # was refactored to help understand the structure of the counters
        # so that a generic summary structure could be made.  This allows
        # for output of the summary information to somewhere other than
        # stdout.
        #
        # the structure has been broken down into levels of regular dicts
        # and SocorroDotDicts.  The DotDicts have keys that are constant
        # and no more are added when new crashes come in.  The regular dicts
        # are key with variable things that come in with crashes.  In the
        # structure below, keys of DotDicts are shown as constants like
        # ".count" and ".modules". The keys of the dicts are shown as the
        # name of a field with a * (to designate zero or more) inside square
        # brackets.
        #
        # the counters structure looks like this:
        #     pv_counters[os_name*]
        #         .count
        #         .signatures[a_signature*]
        #             .count
        #             .modules[a_module*]
        #                 .count
        #                 .versions[a_version*] int
        #         .modules[a_module*]
        #              .count
        #              .versions[a_version*] int

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        os_name = crash["os_name"]
        # The os_version field is way too specific on Linux, and we don't
        # have much Linux data anyway.
        if options.by_os_version and os_name != "Linux":
            os_name = os_name + " " + crash["os_version"]
        counters_for_an_os = osyses.setdefault(
            os_name,
            SocorroDotDict({
                "count": 0,
                "signatures": {},
                "modules": {},
            })
        )
        a_signature = crash["signature"]
        if self.contains_bare_address(a_signature):
            if options.condense:
                # Condense all signatures in a given DLL.
                a_signature = self.remove_bare_address_from_signature(
                    a_signature
                )
        if "reason" in crash and crash["reason"] is not None:
            a_signature = a_signature + "__reason__" + crash["reason"]
        counters_for_a_signature = counters_for_an_os.signatures.setdefault(
            a_signature,
            SocorroDotDict({
                "count": 0,
                "modules": {}
            }),
        )
        list_of_counters = [counters_for_an_os, counters_for_a_signature]
        # increment both the os & signature counters
        for a_counter in list_of_counters:
            a_counter.count += 1

        for libname, version in self.generate_modules_or_addons(crash):
            # Increment the global count on osys and the per-signature count.
            for a_counter in list_of_counters:
                counters_for_modules = a_counter.modules.setdefault(
                    libname,
                    SocorroDotDict({
                        "count": 0,
                        "versions": defaultdict(int),
                    })
                )
                counters_for_modules.count += 1
                # Count versions of each module as well.
                counters_for_modules.versions[version] += 1
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # end - refactored code section
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        return True

    #--------------------------------------------------------------------------
    def _summary_for_a_product_version_pair(self, a_pv_accumulator):
        """in the original code, the counter structures were walked and
        manipulated to form the statistics.  Once a stat was determined,
        it was printed to stdout.  Since we want to have various means of
        outputting the data, instead of printing to stdout, this method
        save the statistic in a "summary_structure"  This structure will
        later be walked for printing or output to some future storage scheme

        The summary structure looks like this:
        pv_summary
            .date_key  # a list of the last six UUID characters present
            .notes  # any notes added by the algorithm to tell of problems
            .os_counters[os_name*]
                 .count
                 .signatures[a_signature*]
                     .count
                     .in_sig_ratio
                     .in_os_ratio
                     .in_os_count
                     .osys_count
                     .modules[a_module*]  # may be addons
                         .in_sig_ratio
                         .in_os_ratio
                         .in_os_count
                         .osys_count
                         .verisons[a_version*]  # may be addon versions
                             .sig_ver_ratio
                             .sig_ver_count
                             .sig_count
                             .os_ver_ratio
                             .os_ver_count
                             .osys_count
                             .version
        """

        options = self.config
        pv_summary = SocorroDotDict({
            'notes': [],
        })
        if (len(self.date_suffix) > 1):
            message = (
                "crashes from more than one day %s" %
                str(tuple(self.date_suffix.keys()))
            )
##            self.config.logger.debug(message)
            pv_summary.notes.append(message)
        pv_summary.date_key = self.date_suffix.keys()[0]
        pv_summary.os_counters = {}

        MIN_CRASHES = self.config.min_crashes
        counters_for_multiple_os = a_pv_accumulator.osyses

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # begin - refactored code section
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        infostr_re = re.compile("^(.*) with (\d+) cores$")  # unused?

        for os_name in counters_for_multiple_os.keys():
            counters_for_an_os = counters_for_multiple_os[os_name]

            pv_summary.os_counters[os_name] = SocorroDotDict()
            pv_summary.os_counters[os_name].count = counters_for_multiple_os[os_name].count
            pv_summary.os_counters[os_name].signatures = {}
            filtered_signatures = [
                (signature, signature_counter)
                for (signature, signature_counter)
                    in counters_for_an_os["signatures"].items()
                if signature_counter.count >= MIN_CRASHES
            ]
            for a_signature, a_signtaure_counter in filtered_signatures:
                pv_summary.os_counters[os_name].signatures[a_signature] = SocorroDotDict()
                pv_summary.os_counters[os_name].signatures[a_signature].count = a_signtaure_counter.count
                pv_summary.os_counters[os_name].signatures[a_signature].modules = {}
                modules_list = [
                    SocorroDotDict({
                        "libname": module_name,
                        "in_sig_count": a_module_counter.count,
                        "in_sig_ratio": float(a_module_counter.count) / a_signtaure_counter.count,
                        "in_sig_versions": a_module_counter.versions,
                        "in_os_count": counters_for_an_os.modules[module_name].count,
                        "in_os_ratio": (
                            float(counters_for_an_os.modules[module_name].count) /
                            counters_for_an_os.count
                        ),
                        "in_os_versions":
                            counters_for_an_os.modules[module_name].versions
                    })
                    for module_name, a_module_counter in a_signtaure_counter.modules.iteritems()
                ]

                modules_list = [
                    module for module in modules_list
                    if module.in_sig_ratio - module.in_os_ratio >= self.config.min_baseline_diff
                ]

                modules_list.sort(
                    key=lambda module: module.in_sig_ratio - module.in_os_ratio,
                    reverse=True
                )

                for module in modules_list:
                    module_name = module.libname
                    if options.addons:
                        info = addonids.info_for_id(module_name)
                        if info is not None:
                            module_name = (
                                module_name + u" ({0}, {1})".format(
                                    info.name,
                                    info.url
                                )
                            )
                    if options.show_versions and len(module["in_os_versions"]) == 1:
                        onlyver = module.in_os_versions.keys()[0]
                        if os_name.startswith("Mac OS X"):
                            info = macdebugids.info_for_id(module_name, onlyver)
                            if info is not None:
                                onlyver = onlyver + "; " + info
                        if (onlyver != ""):
                            module_name = module_name + " (" + onlyver + ")"
                    pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name] = SocorroDotDict()
                    pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].in_sig_count = (
                        module.in_sig_count
                    )
                    pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].in_sig_ratio = (
                        int(round(module["in_sig_ratio"] * 100))
                    )
                    pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].in_os_ratio = (
                        int(round(module.in_os_ratio * 100))
                    )
                    pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].in_os_count = (
                        module.in_os_count
                    )
                    pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].osys_count = (
                        counters_for_an_os.count
                    )

                    if options.show_versions and len(module.in_os_versions) != 1:
                        versions = module.in_os_versions.keys()
                        versions.sort()
                        pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions = {}
                        for version in versions:
                            sig_ver_count = module.in_sig_versions.get(version, 0)
                            os_ver_count = module.in_os_versions[version]
                            if os_name.startswith("Mac OS X"):
                                info = macdebugids.info_for_id(module_name, version)
                                if info is not None:
                                    version = version + " (" + info + ")"
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version] = SocorroDotDict()
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version].sig_ver_ratio = (
                                int(round(float(sig_ver_count) / a_signtaure_counter.count * 100))
                            )
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version].sig_ver_count = sig_ver_count
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version].sig_count = a_signtaure_counter.count
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version].os_ver_ratio = (
                                int(round(float(os_ver_count) / counters_for_an_os.count * 100))
                            )
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version].os_ver_count = os_ver_count
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version].osys_count = counters_for_an_os.count
                            pv_summary.os_counters[os_name].signatures[a_signature].modules[module_name].versions[version].version = version
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # end - refactored code section
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        return pv_summary

    #--------------------------------------------------------------------------
    def generate_modules_or_addons(self, crash):
        options = self.config
        if (options.addons):
            for addon in crash["addons"]:
                yield addon[0], addon[1]
        else:
            if "json_dump" in crash and "modules" in crash["json_dump"]:
                for module in crash["json_dump"]["modules"]:
                    libname = module["filename"]
                    version = module["version"]
                    pdb = module["debug_file"]  # never used?
                    checksum = module["debug_id"]
                    addrstart = module["base_addr"]  # vener used?
                    addrend = module["end_addr"]  # never used?
                    if crash["os_name"].startswith("Win"):
                        # We only have good version data on Windows.
                        yield libname, version
                    else:
                        yield libname, checksum

    #--------------------------------------------------------------------------
    def summarize(self):
        # for each product version pair in the accumulators
        summary = {}
        for pv, an_accumulator in self.counters_for_all_producs_and_versions.iteritems():
            summary['_'.join(pv)] = self._summary_for_a_product_version_pair(
                an_accumulator
            )
        return summary


#==============================================================================
class CorrelationInterestingModulesVersionsRule(CorrelationInterestingModulesRule):
    required_config = Namespace()
    required_config.show_versions = change_default(
        CorrelationInterestingModulesRule,
        'show_versions',
        True
    )


#==============================================================================
class CorrelationInterestingAddonsRule(CorrelationInterestingModulesRule):
    required_config = Namespace()
    required_config.addons = change_default(
        CorrelationInterestingModulesRule,
        'addons',
        True
    )


#==============================================================================
class CorrelationInterestingAddonsVersionsRule(CorrelationInterestingModulesRule):
    required_config = Namespace()
    required_config.addons = change_default(
        CorrelationInterestingModulesRule,
        'addons',
        True
    )
    required_config.show_versions = change_default(
        CorrelationInterestingModulesRule,
        'show_versions',
        True
    )


#==============================================================================
class StdOutOutputForInterestingModulesRule(CorrelationsStorageBase):
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def store(self, key, summary_structure, name):
        print "# --------------------------------------------------------------"
        print "# output divider for 20%s-%s-interesting-%s.txt" % (
            summary_structure["date_key"],
            key,
            name
        )
        print "#==============================================================="

    #--------------------------------------------------------------------------
    def output_correlations_to_stream(self, summary_structure, stream):
        for os_name in sorted(summary_structure.os_counters.keys()):
            print >>stream, os_name.encode("UTF-8")
            for a_signature, signatures in sorted(
                summary_structure.os_counters[os_name].signatures.iteritems()
            ):
                print >>stream, (
                    u"  %s (%d crashes)" % (a_signature, signatures.count)
                ).encode("UTF-8")
                for a_module, modules in sorted(signatures.modules.iteritems()):
                    print >>stream, (
                        u"    {0:3d}% ({1:d}/{2:d}) vs. {3:3d}% ({4:d}/{5:d}) {6}"
                        .format(
                            int(round(modules.in_sig_ratio)),
                            modules.in_sig_count,
                            signatures.count,
                            int(round(modules.in_os_ratio)),
                            modules.in_os_count,
                            summary_structure.os_counters[os_name].count,
                            a_module
                        ).encode("UTF-8")
                    )
                    if 'versions' in modules:
                        for a_version, versions in sorted(modules.versions.iteritems()):
                            print >>stream, (
                                u"        {0:3d}% ({1:d}/{2:d}) vs. {3:3d}% ({4:d}/{5:d}) {6}"
                                .format(
                                    int(round(float(versions.sig_ver_count) / signatures.count)),
                                    versions.sig_ver_count,
                                    signatures.count,
                                    int(round(float(versions.os_ver_count) / summary_structure.os_counters[os_name].count)),
                                    versions.os_ver_count,
                                    summary_structure.os_counters[os_name].count,
                                    a_version
                                ).encode("UTF-8")
                            )
                print >>stream, ''  # blank line between each signature
            print >>stream, ''  # blank line between each OS


#==============================================================================
class FileOutputForInterestingModules(StdOutOutputForInterestingModulesRule):
    required_config = Namespace()
    required_config.add_option(
        'path',
        doc="a file system path into which to store correlations",
        default='/mnt/crashanalysis/crash_analysis',
        reference_value_from='global.correlations'
    )
    required_config.add_option(
        'path_template',
        doc="a template from which to make a pathname",
        default='{path}/{prefix}/{prefix}_{key}-{name}.txt',
        reference_value_from='global.correlations.interesting'
    )

    #--------------------------------------------------------------------------
    def store(
        self,
        payload,
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
            self.output_correlations_to_stream(payload, f)


#==============================================================================
class JsonFileOutputForInterestingModules(FileOutputForInterestingModules):
    required_config = Namespace()
    required_config.path_template = change_default(
        FileOutputForInterestingModules,
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
