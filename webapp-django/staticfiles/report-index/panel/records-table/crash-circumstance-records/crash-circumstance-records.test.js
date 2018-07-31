/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import CrashCircusmstanceRecords from 'socorro/report-index/panel/records-table/crash-circumstance-records';
import Record from 'socorro/report-index/panel/records-table/record';

describe('<CrashCircusmstanceRecords />', () => {
  it('has the right content', () => {
    const container = shallow(
      <CrashCircusmstanceRecords
        report={{
          crashReason: 'crashReasonText',
          crashAddress: 'crashAddressText',
        }}
        rawCrash={{
          isStartupCrash: true,
          flashProcessDump: 'flashProcessDumpText',
          mozCrashReason: 'mozCrashReasonText',
          javaStackTrace: 'javaStackTraceText',
        }}
        descriptions={{
          report: {
            crashReason: 'crashReasonDescription',
            crashAddress: 'crashAddressDescription',
            exploitability: 'exploitabilityDescription',
          },
          rawCrash: {
            isStartupCrash: 'isStartupCrashDescription',
            flashProcessDump: 'flashProcessDumpDescription',
            mozCrashReason: 'mozCrashReasonDescription',
            javaStackTrace: 'javaStackTraceDescription',
          },
        }}
        sensitive={{ exploitability: 'exploitabilityText' }}
      />
    );
    const records = container.find(Record);
    expect(records.length).toEqual(7);

    const startupCrashRecord = records.at(0);
    expect(startupCrashRecord.props()).toEqual({
      children: true,
      header: 'Startup Crash',
      description: 'isStartupCrashDescription',
      show: true,
    });

    const flashProcessDumpRecord = records.at(1);
    expect(flashProcessDumpRecord.props()).toEqual({
      children: 'flashProcessDumpText',
      header: 'Flash Process Dump',
      description: 'flashProcessDumpDescription',
      show: true,
    });

    const mozCrashReasonRecord = records.at(2);
    expect(mozCrashReasonRecord.props()).toEqual({
      children: 'mozCrashReasonText',
      header: 'MOZ_CRASH Reason',
      description: 'mozCrashReasonDescription',
      show: true,
    });

    const crashReasonRecord = records.at(3);
    expect(crashReasonRecord.props()).toEqual({
      children: 'crashReasonText',
      header: 'Crash Reason',
      description: 'crashReasonDescription',
      show: true,
    });

    const crashAddressRecord = records.at(4);
    expect(crashAddressRecord.props()).toEqual({
      children: 'crashAddressText',
      header: 'Crash Address',
      description: 'crashAddressDescription',
      show: true,
    });

    const javaStackTraceRecord = records.at(5);
    expect(javaStackTraceRecord.props()).toEqual({
      children: 'javaStackTraceText',
      header: 'Java Stack Trace',
      description: 'javaStackTraceDescription',
      show: true,
    });

    const exploitabilityRecord = records.at(6);
    expect(exploitabilityRecord.props()).toEqual({
      children: 'exploitabilityText',
      header: 'Exploitability',
      description: 'exploitabilityDescription',
      show: true,
    });
  });
});
