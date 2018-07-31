/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import React from 'react';
import PropTypes from 'prop-types';

import Record from 'socorro/report-index/panel/records-table/record';

export default class CrashCircumstanceRecords extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    rawCrash: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
    sensitive: PropTypes.object.isRequired,
  };

  render() {
    const { report, rawCrash, descriptions, sensitive } = this.props;
    return (
      <React.Fragment>
        <Record
          header="Startup Crash"
          description={descriptions.rawCrash.isStartupCrash}
          show={rawCrash.isStartupCrash !== null}
        >
          {rawCrash.isStartupCrash}
        </Record>
        <Record
          header="Flash Process Dump"
          description={descriptions.rawCrash.flashProcessDump}
          show={rawCrash.flashProcessDump !== null}
        >
          {rawCrash.flashProcessDump}
        </Record>
        <Record
          header="MOZ_CRASH Reason"
          description={descriptions.rawCrash.mozCrashReason}
          show={rawCrash.mozCrashReason !== null}
        >
          {rawCrash.mozCrashReason}
        </Record>
        <Record header="Crash Reason" description={descriptions.report.crashReason} show={report.crashReason !== null}>
          {report.crashReason}
        </Record>
        <Record
          header="Crash Address"
          description={descriptions.report.crashAddress}
          show={report.crashAddress !== null}
        >
          {report.crashAddress}
        </Record>
        <Record
          header="Java Stack Trace"
          description={descriptions.rawCrash.javaStackTrace}
          show={rawCrash.javaStackTrace !== null}
        >
          {rawCrash.javaStackTrace}
        </Record>
        <Record
          header="Exploitability"
          description={descriptions.report.exploitability}
          show={sensitive.exploitability !== null}
        >
          {sensitive.exploitability}
        </Record>
      </React.Fragment>
    );
  }
}
