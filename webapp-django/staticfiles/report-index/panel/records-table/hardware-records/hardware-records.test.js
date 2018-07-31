/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import HardwareRecords from 'socorro/report-index/panel/records-table/hardware-records';
import Record from 'socorro/report-index/panel/records-table/record';

describe('<HardwareRecords />', () => {
  it('has the right content', () => {
    const container = shallow(
      <HardwareRecords
        report={{
          cpuName: 'cpuNameText',
          cpuInfo: 'cpuInfoText',
        }}
        rawCrash={{
          androidManufacturer: 'androidManufacturerText',
          androidModel: 'androidModelText',
          androidCpuAbi: 'androidCpuAbiText',
          adapterVendorId: 'adapterVendorIdText',
          adapterDeviceId: 'adapterDeviceIdText',
        }}
        descriptions={{
          report: {
            cpuName: 'cpuNameDescription',
            cpuInfo: 'cpuInfoDescription',
          },
          rawCrash: {
            androidManufacturer: 'androidManufacturerDescription',
            androidModel: 'androidModelDescription',
            androidCpuAbi: 'androidCpuAbiDescription',
            adapterVendorId: 'adapterVendorIdDescription',
            adapterDeviceId: 'adapterDeviceIdDescription',
          },
        }}
      />
    );
    const records = container.find(Record);
    expect(records.length).toEqual(7);

    const buildArchitectureRecord = records.at(0);
    expect(buildArchitectureRecord.props()).toEqual({
      children: 'cpuNameText',
      header: 'Build Architecture',
      description: 'cpuNameDescription',
      show: true,
    });

    const buildArchitectureInfoRecord = records.at(1);
    expect(buildArchitectureInfoRecord.props()).toEqual({
      children: 'cpuInfoText',
      header: 'Build Architecture Info',
      description: 'cpuInfoDescription',
      show: true,
    });

    const androidManufacturerRecord = records.at(2);
    expect(androidManufacturerRecord.props()).toEqual({
      children: 'androidManufacturerText',
      header: 'Android Manufacturer',
      description: 'androidManufacturerDescription',
      show: true,
    });

    const androidModelRecord = records.at(3);
    expect(androidModelRecord.props()).toEqual({
      children: 'androidModelText',
      header: 'Android Model',
      description: 'androidModelDescription',
      show: true,
    });

    const androidCpuAbiRecord = records.at(4);
    expect(androidCpuAbiRecord.props()).toEqual({
      children: 'androidCpuAbiText',
      header: 'Android CPU ABI',
      description: 'androidCpuAbiDescription',
      show: true,
    });

    const adapterVendorIdRecord = records.at(5);
    expect(adapterVendorIdRecord.props()).toEqual({
      children: 'adapterVendorIdText',
      header: 'Adapter Vendor ID',
      description: 'adapterVendorIdDescription',
      show: true,
    });

    const adapterDeviceIdRecord = records.at(6);
    expect(adapterDeviceIdRecord.props()).toEqual({
      children: 'adapterDeviceIdText',
      header: 'Adapter Device ID',
      description: 'adapterDeviceIdDescription',
      show: true,
    });
  });
});
