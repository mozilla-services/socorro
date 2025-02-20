// # This Source Code Form is subject to the terms of the Mozilla Public
// # License, v. 2.0. If a copy of the MPL was not distributed with this
// # file, You can obtain one at https://mozilla.org/MPL/2.0/.

import esbuild from 'esbuild';

const entryPoints = [
  {
    in: 'crashstats/crashstats/static/crashstats/css/crashstats-base.css',
    out: 'crashstats/css/crashstats-base.min',
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
    out: 'tokens/css/home.min',
  },
  {
    in: 'crashstats/topcrashers/static/topcrashers/css/topcrashers.css',
    out: 'topcrashers/css/topcrashers.min',
  },
];

const options = {
  bundle: true,
  entryPoints,
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
