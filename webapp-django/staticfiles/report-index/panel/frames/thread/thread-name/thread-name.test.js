/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import ThreadName from 'socorro/report-index/panel/frames/thread/thread-name';

describe('<ThreadName />', () => {
  it('has the right content', () => {
    const container = shallow(<ThreadName name="nameText" number={0} isCrashingThread={true} />);
    const header = container.find('h2');
    expect(header.text()).toEqual('Crashing Thread (0), Name: nameText');
  });
});
