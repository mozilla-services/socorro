# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.lib.transform_rules import Rule


# Kinds of memory reporters.
KIND_NONHEAP = 0
KIND_HEAP = 1
# Type of units used by memory reporters.
UNITS_BYTES = 0
# For more information on those values, see:
# https://dxr.mozilla.org/mozilla-central/source/xpcom/base/nsIMemoryReporter.idl#27-125


class MemoryReportExtraction(Rule):
    """Extract key measurements from the memory_report object into a more
    comprehensible and usable dictionary. """

    def version(self):
        return '1.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            # Verify that...
            return (
                # ... we have a pid...
                'pid' in processed_crash['json_dump'] and
                # ... we have a memory report...
                bool(processed_crash['memory_report']) and
                # ... and that memory report is recognisable.
                'version' in processed_crash['memory_report'] and
                'reports' in processed_crash['memory_report'] and
                'hasMozMallocUsableSize' in processed_crash['memory_report']
            )
        except KeyError:
            return False

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        pid = processed_crash['json_dump']['pid']
        memory_report = processed_crash['memory_report']

        try:
            measures = self._get_memory_measures(memory_report, pid)
        except ValueError as e:
            self.config.logger.info(
                'Unable to extract measurements from memory report: {}'
                .format(e)
            )
            return False
        except KeyError as e:
            self.config.logger.info(
                'Unable to extract measurements from memory report: '
                'key {} is missing from a report'.format(e)
            )
            return False

        processed_crash['memory_measures'] = measures
        return True

    def _get_memory_measures(self, memory_report, pid):
        explicit_heap = 0
        explicit_nonheap = 0
        pid_found = False
        pid_str = '(pid {})'.format(pid)

        # These ones are in the memory report.
        metrics_measured = {
            'ghost-windows': 0,
            'heap-allocated': 0,
            'private': 0,
            'resident': 0,
            'resident-unique': 0,
            'system-heap-allocated': 0,
            'vsize-max-contiguous': 0,
            'vsize': 0,
        }

        # These ones are derived from the memory report.
        metrics_derived = {
            'heap-unclassified': 0,
            'explicit': 0,
            'top-non-detached': 0,
        }

        all_metrics = {}
        all_metrics.update(metrics_measured)
        all_metrics.update(metrics_derived)

        # Process reports
        for report in memory_report['reports']:
            process = report['process']

            if pid_str not in process:
                continue

            pid_found = True

            path = report['path']
            kind = report['kind']
            units = report['units']
            amount = report['amount']

            if path.startswith('explicit/'):
                if units != UNITS_BYTES:
                    raise ValueError(
                        'bad units for an explicit/ report: {}, {}'.format(
                            path, str(units)
                        )
                    )

                if kind == KIND_NONHEAP:
                    explicit_nonheap += amount
                elif kind == KIND_HEAP:
                    explicit_heap += amount
                else:
                    raise ValueError(
                        'bad kind for an explicit/ report: {}, {}'.format(
                            path, str(kind)
                        )
                    )

                if 'top(none)/detached' in path:
                    all_metrics['top-non-detached'] += amount

            elif path in metrics_measured:
                all_metrics[path] += amount

        if not pid_found:
            raise ValueError('no measurements found for pid {}'.format(pid))

        # Nb: sometimes heap-unclassified is negative due to bogus measurements
        # of some kind. We just show the negative value anyway.
        all_metrics['heap-unclassified'] = (
            all_metrics['heap-allocated'] - explicit_heap
        )
        all_metrics['explicit'] = (
            all_metrics['heap-allocated'] + explicit_nonheap
        )

        return all_metrics
