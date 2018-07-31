/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Record from 'socorro/report-index/panel/records-table/record';

export default class OsRecords extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    rawCrash: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
  };

  render() {
    const { report, rawCrash, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record header="OS" description={descriptions.report.os}>
          {report.os}
        </Record>
        <Record header="OS Version" description={descriptions.report.osVersion}>
          {report.osVersion}
        </Record>
        <Record
          header="Android Version"
          description={descriptions.rawCrash.androidVersion}
          show={rawCrash.androidVersion}
        >
          {rawCrash.androidVersion}
        </Record>
        <Record header="B2G OS Version" description={descriptions.rawCrash.b2gOsVersion} show={rawCrash.b2gOsVersion}>
          {rawCrash.b2gOsVersion}
        </Record>
      </React.Fragment>
    );
  }
}
