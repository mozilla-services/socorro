/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Filesize from 'socorro/report-index/panel/records-table/filesize';
import Record from 'socorro/report-index/panel/records-table/record';

export default class MemoryUsageRecords extends React.Component {
  static propTypes = {
    rawCrash: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
  };

  render() {
    const { rawCrash, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record header="Total Virtual Memory" description={descriptions.rawCrash.totalVirtualMemory}>
          <Filesize filesizeData={rawCrash.totalVirtualMemory} />
        </Record>
        <Record header="Available Virtual Memory" description={descriptions.rawCrash.availableVirtualMemory}>
          <Filesize filesizeData={rawCrash.availableVirtualMemory} />
        </Record>
        <Record header="Available Page File" description={descriptions.rawCrash.availablePageFile}>
          <Filesize filesizeData={rawCrash.availablePageFile} />
        </Record>
        <Record header="Available Physical Memory" description={descriptions.rawCrash.availablePhysicalMemory}>
          <Filesize filesizeData={rawCrash.availablePhysicalMemory} />
        </Record>
        <Record header="System Memory Use Percentage" description={descriptions.rawCrash.systemMemoryUsePercentage}>
          {rawCrash.systemMemoryUsePercentage}
        </Record>
        <Record
          header="OOM Allocation Size"
          description={descriptions.rawCrash.oomAllocationSize}
          show={rawCrash.oomAllocationSize.bytes !== undefined}
        >
          <Filesize filesizeData={rawCrash.oomAllocationSize} />
        </Record>
      </React.Fragment>
    );
  }
}
