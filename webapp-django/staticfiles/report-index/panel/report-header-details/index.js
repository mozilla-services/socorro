/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class ReportHeaderDetails extends React.Component {
  static propTypes = {
    uuid: PropTypes.string.isRequired,
    signature: PropTypes.string.isRequired,
  };

  render() {
    const { uuid, signature } = this.props;
    return (
      <div>
        ID: <code>{uuid}</code>
        <br />
        Signature: <code>{signature}</code>
      </div>
    );
  }
}
