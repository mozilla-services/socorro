/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class ThreadName extends React.Component {
  static propTypes = {
    name: PropTypes.string,
    number: PropTypes.number.isRequired,
    isCrashingThread: PropTypes.bool.isRequired,
  };

  render() {
    const { name, number, isCrashingThread } = this.props;
    return (
      <h2>
        {isCrashingThread ? `Crashing Thread (${number})` : `Thread ${number}`}
        {name ? `, Name: ${name}` : ''}
      </h2>
    );
  }
}
