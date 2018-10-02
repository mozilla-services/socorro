/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import React from 'react';
import { shallow } from 'enzyme';
import PageHeading from 'socorro/report-index/page-heading';

describe('<PageHeading />', () => {
  it('has the right content', () => {
    const container = shallow(<PageHeading product="product" version="version" signature="signature" />);
    const title = container.find('h2');
    expect(container.prop('className')).toEqual('page-heading');
    expect(title.text()).toEqual('product version Crash Report [@ signature ]');
  });
});
