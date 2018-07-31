/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import Frames from 'socorro/report-index/panel/frames';

describe('<Frames />', () => {
  it('has the right content if crashing thread is null', () => {
    const container = shallow(<Frames threads={[]} crashingThread={null} />);
    expect(container.type()).toEqual(null);
  });

  it('has the right content', () => {
    const container = shallow(<Frames threads={[{ thread: 0 }, { thread: 1 }]} crashingThread={0} />);
    const threads = container.find('Thread');
    expect(threads.length).toEqual(2);

    const crashingThread = threads.at(0);
    expect(crashingThread.props()).toEqual({ thread: { thread: 0 }, isCrashingThread: true });

    let nonThrashingThreadsContainer = container.find('#allthreads');
    expect(nonThrashingThreadsContainer.hasClass('hidden')).toEqual(true);
    container.find('button').simulate('click');
    nonThrashingThreadsContainer = container.find('#allthreads');
    expect(nonThrashingThreadsContainer.hasClass('hidden')).toEqual(false);

    const nonCrashingThread = threads.at(1);
    expect(nonCrashingThread.props()).toEqual({ thread: { thread: 1 }, isCrashingThread: false });
  });
});
