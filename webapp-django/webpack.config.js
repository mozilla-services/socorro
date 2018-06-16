/* eslint-env node */
const path = require('path');
const BundleTracker = require('webpack-bundle-tracker');

// FIXME(osmose): This file is optimized for development; it will not produce
// minimal code suitable for a production environment.
module.exports = {
  mode: 'development',
  devtool: 'cheap-module-source-map',
  entry: {
    new_report_index: './staticfiles/index.js',
  },
  output: {
    path: path.resolve(__dirname, 'webpack_bundles'),
    filename: '[name].bundle.js',
  },
  module: {
    rules: [{ test: /\.js$/, exclude: /node_modules/, loader: 'babel-loader' }],
  },
  plugins: [
    new BundleTracker({
      path: __dirname,
      filename: './webpack-stats.json',
    }),
  ],
};
