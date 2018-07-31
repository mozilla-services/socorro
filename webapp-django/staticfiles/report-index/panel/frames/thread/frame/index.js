/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

export default class Frame extends React.Component {
  static propTypes = { frame: PropTypes.object.isRequired };

  getMissingSymbolsIndicator(isMissingSymbols) {
    if (isMissingSymbols) {
      return (
        <span className="row-notice" title="missing symbol">
          &Oslash;
        </span>
      );
    }
    return null;
  }

  getSource(frame) {
    if (frame.sourceLink) {
      return (
        <a href={frame.sourceLink}>
          {frame.file}:{frame.line}
        </a>
      );
    }
    if (frame.line) {
      return `${frame.file}:${frame.line}`;
    }
    return frame.file;
  }

  render() {
    const frame = this.props.frame;
    return (
      <tr className={frame.isMissingSymbols ? 'missingsymbols' : ''}>
        <td>
          {this.getMissingSymbolsIndicator(frame.isMissingSymbols)}
          {frame.frame}
        </td>
        <td>{frame.module}</td>
        <td title={frame.signature}>{frame.signature}</td>
        <td>{this.getSource(frame)}</td>
      </tr>
    );
  }
}
