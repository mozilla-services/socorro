/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import Filesize from 'socorro/report-index/panel/records-table/filesize';

describe('<Filesize />', () => {
  it('has the right content', () => {
    const container = shallow(
      <Filesize filesizeData={{ formatted: 'formattedText', bytes: 2000, humanfriendly: 'humanfriendlyText' }} />
    );
    expect(container.text()).toEqual('formattedText bytes (humanfriendlyText)');
  });
});
