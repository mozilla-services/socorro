/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import Frame from 'socorro/report-index/panel/frames/thread/frame';

describe('<Frame />', () => {
  it('has the right content when isMissingSymbols is true', () => {
    const container = shallow(
      <Frame
        frame={{
          isMissingSymbols: true,
          frame: 0,
          module: 'moduleText',
          signature: 'signatureText',
          sourceLink: 'sourceLinkText',
          file: 'fileText',
          line: 'lineText',
        }}
      />
    );
    const row = container.find('tr');
    expect(row.hasClass('missingsymbols')).toEqual(true);

    const cells = row.find('td');
    expect(cells.length).toEqual(4);

    const frameCell = cells.at(0);
    const missingSymbolsNotice = frameCell.find('span');
    expect(missingSymbolsNotice.props()).toEqual({ children: 'Ø', className: 'row-notice', title: 'missing symbol' });
    expect(missingSymbolsNotice.text()).toEqual('Ø');

    expect(frameCell.text()).toEqual('Ø0');

    expect(cells.at(1).text()).toEqual('moduleText');

    const signatureCell = cells.at(2);
    expect(signatureCell.props().title).toEqual('signatureText');
    expect(signatureCell.text()).toEqual('signatureText');

    const sourceCell = cells.at(3);
    const sourceLink = sourceCell.find('a');
    expect(sourceLink.props().href).toEqual('sourceLinkText');
    expect(sourceLink.text()).toEqual('fileText:lineText');
  });
});
