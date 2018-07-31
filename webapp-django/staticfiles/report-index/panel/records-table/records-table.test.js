/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import RecordsTable from 'socorro/report-index/panel/records-table';

describe('<RecordsTable />', () => {
  it('has the right content', () => {
    const container = shallow(<RecordsTable report={{}} rawCrash={{}} descriptions={{}} sensitive={{}} />);
    const table = container.find('table');
    expect(table.props().className).toEqual('record data-table vertical');

    const tableBody = table.find('tbody');
    expect(tableBody.exists()).toEqual(true);

    const records = tableBody.children();
    expect(records.length).toEqual(10);
  });
});
