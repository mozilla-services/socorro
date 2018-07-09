import React from 'react';
import { shallow } from 'enzyme';

import PageHeading from './index';

describe('<PageHeading />', () => {
  it('has the right content', () => {
    const container = shallow(<PageHeading product="product" version="version" signature="signature" />);
    const title = container.find('h2');
    expect(container.prop('className')).toEqual('page-heading');
    expect(title.text()).toEqual('product version Crash Report [@ signature ]');
  });
});
