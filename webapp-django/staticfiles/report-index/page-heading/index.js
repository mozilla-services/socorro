/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import React from 'react';
import PropTypes from 'prop-types';

export default class PageHeading extends React.Component {
  static propTypes = {
    product: PropTypes.string,
    version: PropTypes.string,
    signature: PropTypes.string,
  };

  render() {
    return (
      <div className="page-heading">
        <h2>
          {this.props.product} {this.props.version} Crash Report [@ {this.props.signature} ]
        </h2>
      </div>
    );
  }
}
