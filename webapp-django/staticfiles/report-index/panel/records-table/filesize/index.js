/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class Filesize extends React.Component {
  static propTypes = { filesizeData: PropTypes.object.isRequired };

  render() {
    const filesizeData = this.props.filesizeData;
    return (
      <React.Fragment>
        {filesizeData.formatted} bytes
        {filesizeData.bytes > 1024 ? (
          <span className="humanized" title={`${filesizeData.formatted} bytes`}>
            {' '}
            ({filesizeData.humanfriendly})
          </span>
        ) : null}
      </React.Fragment>
    );
  }
}
