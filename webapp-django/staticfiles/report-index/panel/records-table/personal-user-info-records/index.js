/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Record from 'socorro/report-index/panel/records-table/record';
import SensitiveWarning from 'socorro/report-index/panel/records-table/sensitive-warning';

export default class PersonalUserInfoRecords extends React.Component {
  static propTypes = {
    descriptions: PropTypes.object.isRequired,
    sensitive: PropTypes.object.isRequired,
  };

  render() {
    const { descriptions, sensitive } = this.props;
    return (
      <React.Fragment>
        <Record header="URL" description={descriptions.report.url} show={sensitive.url !== undefined}>
          <a href={sensitive.url} title={sensitive.url}>
            {sensitive.url}
          </a>
          - <SensitiveWarning isYourCrash={sensitive.isYourCrash} />
        </Record>
        <Record header="Email Address" description={descriptions.report.url} show={sensitive.email !== undefined}>
          <a href={`mailto:${sensitive.email}`} title={sensitive.email}>
            {sensitive.email}
          </a>
          - <SensitiveWarning isYourCrash={sensitive.isYourCrash} />
        </Record>
        <Record header="User Comments" description={descriptions.report.userComments}>
          {sensitive.userComments}
        </Record>
      </React.Fragment>
    );
  }
}
