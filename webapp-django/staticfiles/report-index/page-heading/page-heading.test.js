/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import PageHeading from 'socorro/report-index/page-heading';

describe('<PageHeading />', () => {
  it('has the right content', () => {
    const container = shallow(<PageHeading product="product" version="version" signature="signature" />);
    expect(container.prop('className')).toEqual('page-heading');

    const heading = container.find('h2');
    expect(heading.text()).toEqual('product version Crash Report [@ signature ]');
  });
});
