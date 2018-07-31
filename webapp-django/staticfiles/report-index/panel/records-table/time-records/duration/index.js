/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class Duration extends React.Component {
  static propTypes = {
    durationData: PropTypes.object.isRequired,
    text: PropTypes.string,
  };

  render() {
    const { durationData, text } = this.props;
    return (
      <React.Fragment>
        {durationData.formatted} seconds {text}
        {durationData.seconds > 60 ? (
          <span className="humanized" title={`${durationData.formatted} seconds`}>
            {' '}
            ({durationData.humanfriendly})
          </span>
        ) : null}
      </React.Fragment>
    );
  }
}
