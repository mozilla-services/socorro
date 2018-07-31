/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import PageHeading from 'socorro/report-index/page-heading';
import Panel from 'socorro/report-index/panel';
import Frames from 'socorro/report-index/panel/frames';
import RecordsTable from 'socorro/report-index/panel/records-table';
import ReportHeaderDetails from 'socorro/report-index/panel/report-header-details';
import SumoLink from 'socorro/report-index/panel/sumo-link';

export default class ReportIndex extends React.Component {
  static propTypes = { crashId: PropTypes.string.isRequired };

  componentDidMount() {
    fetch(`/api/ReportDetails?crash_id=${this.props.crashId}`)
      .then(response => response.json())
      .then(details => this.setState({ details }));
  }

  render() {
    if (this.state === null) {
      return <React.Fragment>Fetching data...</React.Fragment>;
    }
    const details = this.state.details;
    if (details.error === 'Invalid crash ID') {
      return <React.Fragment>Invalid crash ID.</React.Fragment>;
    }
    return (
      <React.Fragment>
        <PageHeading
          product={details.report.product}
          version={details.report.version}
          signature={details.report.signature}
        />
        <Panel>
          <SumoLink sumoLink={details.sumoLink} mdnLink={details.mdnLink} />
          <ReportHeaderDetails uuid={details.report.uuid} signature={details.report.signature} />
          <RecordsTable
            report={details.report}
            rawCrash={details.rawCrash}
            descriptions={details.descriptions}
            sensitive={details.sensitive}
          />
          <Frames crashingThread={details.crashingThread} threads={details.threads} />
        </Panel>
      </React.Fragment>
    );
  }
}
