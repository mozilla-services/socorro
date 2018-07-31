/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Record from 'socorro/report-index/panel/records-table/record';

export default class NotesRecords extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
  };

  render() {
    const { report, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record header="App Notes" description={descriptions.report.appNotes}>
          {report.appNotes}
        </Record>
        <Record header="Processor Notes" description={descriptions.report.processorNotes}>
          {report.processorNotes}
        </Record>
      </React.Fragment>
    );
  }
}
