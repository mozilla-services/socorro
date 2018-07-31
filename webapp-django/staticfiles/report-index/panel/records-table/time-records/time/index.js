/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class Time extends React.Component {
  static propTypes = {
    time: PropTypes.string.isRequired,
  };

  render() {
    return <time dateTime={this.props.time}>{this.props.time}</time>;
  }
}
