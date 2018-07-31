/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import ReportHeaderDetails from 'socorro/report-index/panel/report-header-details';

describe('<ReportHeaderDetails />', () => {
  it('has the right content', () => {
    const container = shallow(<ReportHeaderDetails uuid={'reportId'} signature={'signatureName'} />);
    const body = container.find('div');
    expect(body.exists()).toEqual(true);

    const codes = container.find('code');
    expect(codes.at(0).text()).toEqual('reportId');
    expect(codes.at(1).text()).toEqual('signatureName');
  });
});
