/* This Source Code Form is subject to the terms of the Mozilla Public
* License, v. 2.0. If a copy of the MPL was not distributed with this
* file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { shallow } from 'enzyme';
import React from 'react';

import SumoLink from 'socorro/report-index/panel/sumo-link';

describe('<SumoLink />', () => {
  it('has the right content', () => {
    const container = shallow(<SumoLink sumoLink={'sumoLink'} mdnLink={'mdnLink'} />);
    const links = container.find('a');
    const sumoLink = links.at(0);
    const mdnLink = links.at(1);
    expect(sumoLink.prop('href')).toEqual('sumoLink');
    expect(sumoLink.prop('title')).toEqual('Find more answers at support.mozilla.org!');
    expect(sumoLink.text()).toEqual('Search Mozilla Support for this signature');
    expect(mdnLink.prop('href')).toEqual('mdnLink');
    expect(mdnLink.prop('title')).toEqual('MDN documentation about crash reports');
    expect(mdnLink.text()).toEqual('How to read this crash report');
  });
});
