import React from 'react';
import PropTypes from 'prop-types';

export default class PageHeading extends React.Component {
  render() {
    return (
      <div className="page-heading">
        <h2>
          {this.props.product} {this.props.version} Crash Report [@ {this.props.signature} ]
        </h2>
      </div>
    );
  }
}

PageHeading.propTypes = {
  product: PropTypes.string,
  version: PropTypes.string,
  signature: PropTypes.string,
};
