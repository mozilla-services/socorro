/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Record from 'socorro/report-index/panel/records-table/record';

export default class Metadata extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
  };

  render() {
    const { report, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record header="Signature" description={descriptions.report.signature}>
          {report.signature}
          <a
            className="sig-overview"
            href={`/signature/?product=Firefox&signature=${report.signature}`}
            title="View more reports of this type"
          >
            More Reports
          </a>
          <a
            className="sig-search"
            href={`/search/?product=Firefox&signature=${report.signature}`}
            title="Search for more reports of this type"
          >
            Search
          </a>
        </Record>
        <Record header="UUID" description={descriptions.report.uuid}>
          {report.uuid}
        </Record>
        <Record header="Date Processed" description={descriptions.report.dateProcessed}>
          {report.dateProcessed}
        </Record>
      </React.Fragment>
    );
  }
}
