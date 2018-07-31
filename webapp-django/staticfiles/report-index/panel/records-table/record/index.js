/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class Records extends React.Component {
  static propTypes = {
    header: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    show: PropTypes.bool,
    children: PropTypes.oneOfType([PropTypes.bool, PropTypes.number, PropTypes.string, PropTypes.object]),
  };
  static defaultProps = { show: true };

  render() {
    if (!this.props.show) {
      return null;
    }
    return (
      <tr title={this.props.description}>
        <th scope="row">{this.props.header}</th>
        <td>{this.props.children} </td>
      </tr>
    );
  }
}
