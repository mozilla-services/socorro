/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Record from 'socorro/report-index/panel/records-table/record';
import Duration from 'socorro/report-index/panel/records-table/time-records/duration';
import Time from 'socorro/report-index/panel/records-table/time-records/time';

export default class TimeRecords extends React.Component {
  static propTypes = {
    report: PropTypes.object,
    rawCrash: PropTypes.object,
    descriptions: PropTypes.object,
  };

  render() {
    const { report, rawCrash, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record header="Uptime" description={descriptions.report.uptime}>
          <Duration durationData={report.uptime} />
        </Record>
        <Record
          header="Last Crash"
          description={descriptions.report.lastCrash}
          show={report.lastCrash.seconds !== null}
        >
          <Duration durationData={report.lastCrash} />
        </Record>
        <Record header="Install Age" description={descriptions.report.installAge}>
          <Duration durationData={report.installAge} text="since version was first installed" />
        </Record>
        <Record header="Install Time" description={descriptions.rawCrash.installTime}>
          <Time time={rawCrash.installTime} />
        </Record>
      </React.Fragment>
    );
  }
}
