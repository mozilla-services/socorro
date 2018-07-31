/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import ReportIndex from 'socorro/report-index';

describe('<ReportIndex />', () => {
  it('has the right content for no crashId', () => {
    const container = shallow(<ReportIndex crashId={'crashId'} />);
    expect(container.text()).toEqual('Fetching data...');
  });

  it('has the right content for no crashId', () => {
    const container = shallow(<ReportIndex crashId={'crashId'} />);
    expect(container.text()).toEqual('Fetching data...');
  });
});
