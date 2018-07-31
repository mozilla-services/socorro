/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import ThreadTable from 'socorro/report-index/panel/frames/thread/thread-table';

describe('<ThreadTable />', () => {
  it('has the right content', () => {
    const container = shallow(
      <ThreadTable>
        <tr>
          <td>firstCellText</td>
          <td>secondCellText</td>
        </tr>
      </ThreadTable>
    );
    const table = container.find('table');
    expect(table.props().className).toEqual('data-table');

    const tableHead = table.find('thead');
    const tableHeadRow = tableHead.find('tr');
    const headers = tableHeadRow.find('th');
    expect(headers.length).toEqual(4);
    headers.forEach(header => expect(header.props().scope).toEqual('col'));
    expect(headers.at(0).text()).toEqual('Frame');
    expect(headers.at(1).text()).toEqual('Module');
    expect(headers.at(2).text()).toEqual('Signature');
    expect(headers.at(3).text()).toEqual('Source');

    const tableBody = table.find('tbody');
    const tableBodyRow = tableBody.find('tr');
    const cells = tableBodyRow.find('td');
    expect(cells.at(0).text()).toEqual('firstCellText');
    expect(cells.at(1).text()).toEqual('secondCellText');
  });
});
