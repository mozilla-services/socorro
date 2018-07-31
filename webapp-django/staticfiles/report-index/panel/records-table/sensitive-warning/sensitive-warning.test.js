/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import SensitiveWarning from 'socorro/report-index/panel/records-table/sensitive-warning';

describe('<SensitiveWarning />', () => {
  it('has the right content when isYourCrash is true', () => {
    const container = shallow(<SensitiveWarning isYourCrash={true} />);
    expect(container.text()).toEqual('You can only see this because it is your crash!');
  });

  it('has the right content when isYourCrash is false', () => {
    const container = shallow(<SensitiveWarning isYourCrash={false} />);
    expect(container.text()).toEqual('This is super sensitive data! Be careful how you use it!');
  });
});
