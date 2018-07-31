/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class SensitiveWarning extends React.Component {
  static propTypes = { isYourCrash: PropTypes.bool.isRequired };

  render() {
    if (this.props.isYourCrash) {
      return <React.Fragment>You can only see this because it is your crash!</React.Fragment>;
    }
    return <React.Fragment>This is super sensitive data! Be careful how you use it!</React.Fragment>;
  }
}
