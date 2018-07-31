/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import Panel from 'socorro/report-index/panel';

describe('<ReportIndex />', () => {
  it('has the right content', () => {
    const container = shallow(
      <Panel>
        <h1>Hello</h1>
      </Panel>
    );
    const panel = container.find('div .panel');
    expect(panel.exists()).toEqual(true);

    const body = container.find('div .body');
    expect(body.exists()).toEqual(true);

    const childHeader = container.find('h1');
    expect(childHeader.text()).toEqual('Hello');
  });
});
