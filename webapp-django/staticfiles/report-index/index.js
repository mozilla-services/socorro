/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import React from 'react';
import PageHeading from 'socorro/report-index/page-heading';

export default class ReportIndex extends React.Component {
  render() {
    return <PageHeading product="product" version="version" signature="signature" />;
  }
}
