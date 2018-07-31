/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import PropTypes from 'prop-types';
import React from 'react';

import Thread from 'socorro/report-index/panel/frames/thread';

export default class Frames extends React.Component {
  static propTypes = {
    threads: PropTypes.array.isRequired,
    crashingThread: PropTypes.number,
  };

  constructor(props) {
    super(props);
    this.state = { hideNonCrashingThreads: props.crashingThread !== null };
  }

  flipHideNonCrashingThreads = () => {
    this.setState({ hideNonCrashingThreads: !this.state.hideNonCrashingThreads });
  };

  render() {
    const { crashingThread, threads } = this.props;
    if (crashingThread === null) {
      return null;
    }
    return (
      <div>
        <Thread thread={threads[crashingThread]} isCrashingThread={true} />
        <button className="text-button" onClick={this.flipHideNonCrashingThreads}>
          {this.state.hideNonCrashingThreads ? 'Show other threads' : 'Hide other threads'}
        </button>
        <div id="allthreads" className={this.state.hideNonCrashingThreads ? 'hidden' : ''}>
          {threads
            .filter(thread => thread.thread != crashingThread)
            .map(thread => <Thread key={thread.thread} thread={thread} isCrashingThread={false} />)}
        </div>
      </div>
    );
  }
}
