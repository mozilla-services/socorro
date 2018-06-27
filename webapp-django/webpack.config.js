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

  // Depedencies are installed in the /webapp-frontend-deps folder in the
  // container. resolve handles imports in compiled bundles, while resolveLoader
  // handles importing loaders used by webpack for bundling.
  resolve: {
    modules: [path.join('/webapp-frontend-deps', 'node_modules')],
  },
  resolveLoader: {
    modules: [path.join('/webapp-frontend-deps', 'node_modules')],
  },
};
