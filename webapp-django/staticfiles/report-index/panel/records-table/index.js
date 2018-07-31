/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import MetadataRecords from 'socorro/report-index/panel/records-table/metadata-records';
import TimeRecords from 'socorro/report-index/panel/records-table/time-records';
import ProductRecords from 'socorro/report-index/panel/records-table/product-records';
import OsRecords from 'socorro/report-index/panel/records-table/os-records';
import HardwareRecords from 'socorro/report-index/panel/records-table/hardware-records';
import CrashCircumstanceRecords from 'socorro/report-index/panel/records-table/crash-circumstance-records';
import PersonalUserInfoRecords from 'socorro/report-index/panel/records-table/personal-user-info-records';
import MemoryUsageRecords from 'socorro/report-index/panel/records-table/memory-usage-records';
import MiscellaneousRecords from 'socorro/report-index/panel/records-table/miscellaneous-records';
import NotesRecords from 'socorro/report-index/panel/records-table/notes-records';

export default class RecordsTable extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    rawCrash: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
    sensitive: PropTypes.object.isRequired,
  };

  render() {
    const { report, rawCrash, descriptions, sensitive } = this.props;
    return (
      <table className="record data-table vertical">
        <tbody>
          <MetadataRecords report={report} descriptions={descriptions} />
          <TimeRecords report={report} rawCrash={rawCrash} descriptions={descriptions} />
          <ProductRecords report={report} descriptions={descriptions} />
          <OsRecords report={report} rawCrash={rawCrash} descriptions={descriptions} />
          <HardwareRecords report={report} rawCrash={rawCrash} descriptions={descriptions} />
          <CrashCircumstanceRecords
            report={report}
            rawCrash={rawCrash}
            descriptions={descriptions}
            sensitive={sensitive}
          />
          <PersonalUserInfoRecords sensitive={sensitive} descriptions={descriptions} />
          <MemoryUsageRecords rawCrash={rawCrash} descriptions={descriptions} />
          <MiscellaneousRecords report={report} rawCrash={rawCrash} descriptions={descriptions} />
          <NotesRecords report={report} descriptions={descriptions} />
        </tbody>
      </table>
    );
  }
}
