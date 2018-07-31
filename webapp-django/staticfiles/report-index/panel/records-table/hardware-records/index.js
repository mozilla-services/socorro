/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import React from 'react';
import PropTypes from 'prop-types';

import Record from 'socorro/report-index/panel/records-table/record';

export default class HardwareRecords extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    rawCrash: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
  };

  render() {
    const { report, rawCrash, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record header="Build Architecture" description={descriptions.report.cpuName}>
          {report.cpuName}
        </Record>
        <Record header="Build Architecture Info" description={descriptions.report.cpuInfo}>
          {report.cpuInfo}
        </Record>
        <Record
          header="Android Manufacturer"
          description={descriptions.rawCrash.androidManufacturer}
          show={rawCrash.androidManufacturer !== null}
        >
          {rawCrash.androidManufacturer}
        </Record>
        <Record
          header="Android Model"
          description={descriptions.rawCrash.androidModel}
          show={rawCrash.androidModel !== null}
        >
          {rawCrash.androidModel}
        </Record>
        <Record
          header="Android CPU ABI"
          description={descriptions.rawCrash.androidCpuAbi}
          show={rawCrash.androidCpuAbi !== null}
        >
          {rawCrash.androidCpuAbi}
        </Record>
        <Record header="Adapter Vendor ID" description={descriptions.rawCrash.adapterVendorId}>
          {rawCrash.adapterVendorId}
        </Record>
        <Record header="Adapter Device ID" description={descriptions.rawCrash.adapterDeviceId}>
          {rawCrash.adapterDeviceId}
        </Record>
      </React.Fragment>
    );
  }
}
