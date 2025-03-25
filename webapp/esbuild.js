// # This Source Code Form is subject to the terms of the Mozilla Public
// # License, v. 2.0. If a copy of the MPL was not distributed with this
// # file, You can obtain one at https://mozilla.org/MPL/2.0/.

import esbuild from 'esbuild';

const entryPointsJS = [
  {
    in: 'crashstats/crashstats/static/crashstats/js/socorro/crashstats-base.js',
    out: 'crashstats/js/crashstats.min',
  },
  {
    in: 'crashstats/crashstats/static/crashstats/js/socorro/report.js',
    out: 'crashstats/js/socorro/report_index.min',
  },
  {
    in: 'crashstats/crashstats/static/crashstats/js/socorro/pending.js',
    out: 'crashstats/js/socorro/report_pending.min',
  },
  {
    in: 'crashstats/supersearch/static/supersearch/js/socorro/search.js',
    out: 'supersearch/js/search.min',
  },
  {
    in: 'crashstats/supersearch/static/supersearch/js/socorro/search_custom.js',
    out: 'supersearch/js/search_custom.min',
  },
  {
    in: 'crashstats/documentation/static/documentation/js/documentation.js',
    out: 'documentation/js/documentation.min',
  },
  {
    in: 'crashstats/api/static/api/js/testdrive.js',
    out: 'api/js/api_documentation.min',
  },
  {
    in: 'crashstats/signature/static/signature/js/signature_report.js',
    out: 'signature/js/signature_report.min',
  },
  {
    in: 'crashstats/topcrashers/static/topcrashers/js/topcrashers.js',
    out: 'topcrashers/js/topcrashers.min',
  },
  {
    in: 'crashstats/tokens/static/tokens/js/home.js',
    out: 'tokens/js/tokens.min',
  },
  {
    in: 'crashstats/crashstats/static/js/error.js',
    out: 'crashstats/js/error.min',
  },
];

const entryPointsCSS = [
  {
    in: 'crashstats/crashstats/static/crashstats/css/crashstats-base.css',
    out: 'crashstats/css/crashstats.min',
  },
  {
    in: 'crashstats/crashstats/static/crashstats/css/pages/product_home.css',
    out: 'crashstats/css/pages/product_home.min',
  },
  {
    in: 'crashstats/crashstats/static/crashstats/css/pages/report_index.css',
    out: 'crashstats/css/pages/report_index.min',
  },
  {
    in: 'crashstats/crashstats/static/crashstats/css/pages/report_pending.css',
    out: 'crashstats/css/pages/report_pending.min',
  },
  {
    in: 'crashstats/api/static/api/css/documentation.css',
    out: 'api/css/documentation.min',
  },
  {
    in: 'crashstats/documentation/static/documentation/css/documentation.css',
    out: 'documentation/css/documentation.min',
  },
  {
    in: 'crashstats/profile/static/profile/css/profile.css',
    out: 'profile/css/profile.min',
  },
  {
    in: 'crashstats/signature/static/signature/css/signature_report.css',
    out: 'signature/css/signature_report.min',
  },
  {
    in: 'crashstats/status/static/status/css/status.css',
    out: 'status/css/status.min',
  },
  {
    in: 'crashstats/supersearch/static/supersearch/css/search.css',
    out: 'supersearch/css/search.min',
  },
  {
    in: 'crashstats/tokens/static/tokens/css/home.css',
    out: 'tokens/css/tokens.min',
  },
  {
    in: 'crashstats/topcrashers/static/topcrashers/css/topcrashers.css',
    out: 'topcrashers/css/topcrashers.min',
  },
];

const options = {
  bundle: true,
  entryPoints: [...entryPointsJS, ...entryPointsCSS],
  format: 'esm',
  loader: {
    '.gif': 'copy',
    '.svg': 'copy',
    '.png': 'copy',
    '.eot': 'copy',
    '.woff': 'copy',
    '.ttf': 'copy',
  },
  assetNames: 'img/[name]',
  logLevel: 'info',
  outdir: 'static',
  minify: true,
  sourcemap: true,
  splitting: false,
  treeShaking: true,
};

if (process.argv.includes('--watch')) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
  console.info('ESBuild watch-mode enabled');
} else {
  esbuild.build(options);
}
