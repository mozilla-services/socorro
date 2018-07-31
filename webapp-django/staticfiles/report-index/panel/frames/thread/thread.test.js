/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import Thread from 'socorro/report-index/panel/frames/thread';

describe('<Thread />', () => {
  it('has the right content', () => {
    const container = shallow(
      <Thread
        thread={{ thread: 0, name: 'threadName', frames: [{ frame: 0 }, { frame: 1 }] }}
        isCrashingThread={true}
      />
    );
    const threadName = container.find('ThreadName');
    expect(threadName.props()).toEqual({ number: 0, name: 'threadName', isCrashingThread: true });

    const threadTable = container.find('ThreadTable');
    expect(threadTable.exists()).toEqual(true);

    const frames = threadTable.find('Frame');
    expect(frames.length).toEqual(2);

    const firstFrame = frames.at(0);
    expect(firstFrame.props()).toEqual({ frame: { frame: 0 } });
  });
});
