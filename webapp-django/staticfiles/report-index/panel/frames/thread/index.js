/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Frame from 'socorro/report-index/panel/frames/thread/frame';
import ThreadName from 'socorro/report-index/panel/frames/thread/thread-name';
import ThreadTable from 'socorro/report-index/panel/frames/thread/thread-table';

export default class Thread extends React.Component {
  static propTypes = {
    thread: PropTypes.object.isRequired,
    isCrashingThread: PropTypes.bool.isRequired,
  };

  render() {
    const thread = this.props.thread;
    return (
      <React.Fragment>
        <ThreadName number={thread.thread} name={thread.name} isCrashingThread={this.props.isCrashingThread} />
        <ThreadTable>{thread.frames.map(frame => <Frame key={frame.frame} frame={frame} />)}</ThreadTable>
      </React.Fragment>
    );
  }
}
