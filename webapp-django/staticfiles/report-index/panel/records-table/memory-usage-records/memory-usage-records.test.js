/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import Filesize from 'socorro/report-index/panel/records-table/filesize';
import MemoryUsageRecords from 'socorro/report-index/panel/records-table/memory-usage-records';
import Record from 'socorro/report-index/panel/records-table/record';

describe('<MemoryUsageRecords />', () => {
  it('has the right content', () => {
    const container = shallow(
      <MemoryUsageRecords
        rawCrash={{
          totalVirtualMemory: {},
          availableVirtualMemory: {},
          availablePageFile: {},
          availablePhysicalMemory: {},
          systemMemoryUsePercentage: 50,
          oomAllocationSize: { bytes: 50 },
        }}
        descriptions={{
          rawCrash: {
            totalVirtualMemory: 'totalVirtualMemoryDescription',
            availableVirtualMemory: 'availableVirtualMemoryDescription',
            availablePageFile: 'availablePageFileDescription',
            availablePhysicalMemory: 'availablePhysicalMemoryDescription',
            systemMemoryUsePercentage: 'systemMemoryUsePercentageDescription',
            oomAllocationSize: 'oomAllocationSizeDescription',
          },
        }}
      />
    );
    const records = container.find(Record);
    expect(records.length).toEqual(6);

    const totalVirtualMemoryRecord = records.at(0);
    expect(totalVirtualMemoryRecord.props()).toEqual({
      children: <Filesize filesizeData={{}} />,
      header: 'Total Virtual Memory',
      description: 'totalVirtualMemoryDescription',
      show: true,
    });

    const availableVirtualMemoryRecord = records.at(1);
    expect(availableVirtualMemoryRecord.props()).toEqual({
      children: <Filesize filesizeData={{}} />,
      header: 'Available Virtual Memory',
      description: 'availableVirtualMemoryDescription',
      show: true,
    });

    const availablePageFileRecord = records.at(2);
    expect(availablePageFileRecord.props()).toEqual({
      children: <Filesize filesizeData={{}} />,
      header: 'Available Page File',
      description: 'availablePageFileDescription',
      show: true,
    });

    const availablePhysicalMemoryRecord = records.at(3);
    expect(availablePhysicalMemoryRecord.props()).toEqual({
      children: <Filesize filesizeData={{}} />,
      header: 'Available Physical Memory',
      description: 'availablePhysicalMemoryDescription',
      show: true,
    });

    const systemMemoryUsePercentageRecord = records.at(4);
    expect(systemMemoryUsePercentageRecord.props()).toEqual({
      children: 50,
      header: 'System Memory Use Percentage',
      description: 'systemMemoryUsePercentageDescription',
      show: true,
    });

    const oomAllocationSizeRecord = records.at(5);
    expect(oomAllocationSizeRecord.props()).toEqual({
      children: <Filesize filesizeData={{ bytes: 50 }} />,
      header: 'OOM Allocation Size',
      description: 'oomAllocationSizeDescription',
      show: true,
    });
  });
});
