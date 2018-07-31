/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Record from 'socorro/report-index/panel/records-table/record';

export default class MiscellaneousRecords extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    rawCrash: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
  };

  render() {
    const { report, rawCrash, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record
          header="Accessibility"
          description={descriptions.rawCrash.accessibility}
          show={rawCrash.accessibility !== undefined}
        >
          {rawCrash.accessibility}
        </Record>
        <Record header="EMCheckCompatibility" description={descriptions.report.addonsChecked}>
          <pre>{report.addonsChecked ? 'True' : 'False'}</pre>
        </Record>
      </React.Fragment>
    );
  }
}
