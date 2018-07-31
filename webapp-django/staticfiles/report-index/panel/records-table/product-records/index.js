/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Record from 'socorro/report-index/panel/records-table/record';

export default class ProductRecords extends React.Component {
  static propTypes = {
    report: PropTypes.object.isRequired,
    descriptions: PropTypes.object.isRequired,
  };

  render() {
    const { report, descriptions } = this.props;
    return (
      <React.Fragment>
        <Record header="Product" description={descriptions.report.product}>
          {report.product}
        </Record>
        <Record header="Release Channel" description={descriptions.report.releaseChannel}>
          {report.releaseChannel}
        </Record>
        <Record header="Version" description={descriptions.report.version}>
          {report.version}
        </Record>
        <Record header="Build ID" description={descriptions.report.build}>
          <a href={`https://mozilla-services.github.io/buildhub/?q=${report.build}`}>{report.build}</a>
        </Record>
      </React.Fragment>
    );
  }
}
