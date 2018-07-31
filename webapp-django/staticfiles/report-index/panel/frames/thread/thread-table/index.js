/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class ThreadTable extends React.Component {
  static propTypes = { children: PropTypes.oneOfType([PropTypes.object, PropTypes.array]) };

  render() {
    return (
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Frame</th>
            <th scope="col">Module</th>
            <th className="signature-column" scope="col">
              Signature
            </th>
            <th scope="col">Source</th>
          </tr>
        </thead>
        <tbody>{this.props.children}</tbody>
      </table>
    );
  }
}
