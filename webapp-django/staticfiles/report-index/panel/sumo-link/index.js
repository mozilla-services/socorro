/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class SumoLink extends React.Component {
  static propTypes = {
    sumoLink: PropTypes.string.isRequired,
    mdnLink: PropTypes.string.isRequired,
  };

  render() {
    const { sumoLink, mdnLink } = this.props;
    return (
      <div id="sumo-link">
        <a href={sumoLink} title="Find more answers at support.mozilla.org!">
          Search Mozilla Support for this signature
        </a>
        <a href={mdnLink} title="MDN documentation about crash reports">
          How to read this crash report
        </a>
      </div>
    );
  }
}
