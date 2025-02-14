// # This Source Code Form is subject to the terms of the Mozilla Public
// # License, v. 2.0. If a copy of the MPL was not distributed with this
// # file, You can obtain one at https://mozilla.org/MPL/2.0/.

import esbuild from 'esbuild';

const entryPoints = [
  {
    out: 'crashstats/css/crashstats-base.min',
    in: 'crashstats/crashstats/static/crashstats/css/crashstats-base.css',
  },
  {
    out: 'api/css/documentation.min',
    in: 'crashstats/api/static/api/css/documentation.css',
  },
  {
    out: 'documentation/css/documentation.min',
    in: 'crashstats/documentation/static/documentation/css/documentation.css',
  },
  {
    out: 'profile/css/profile.min',
    in: 'crashstats/profile/static/profile/css/profile.css',
  },
  {
    out: 'signature/css/signature_report.min',
    in: 'crashstats/signature/static/signature/css/signature_report.css',
  },
  {
    out: 'status/css/status.min',
    in: 'crashstats/status/static/status/css/status.css',
  },
  {
    out: 'supersearch/css/search.min',
    in: 'crashstats/supersearch/static/supersearch/css/search.css',
  },
  {
    out: 'tokens/css/home.min',
    in: 'crashstats/tokens/static/tokens/css/home.css',
  },
  {
    out: 'topcrashers/css/topcrashers.min',
    in: 'crashstats/topcrashers/static/topcrashers/css/topcrashers.css',
  },
];

await esbuild.build({
  bundle: true,
  entryPoints,
  format: 'esm',
  loader: {
    '.gif': 'file',
    '.svg': 'file',
    '.png': 'file',
    '.eot': 'file',
    '.woff': 'file',
    '.ttf': 'file',
  },
  assetNames: 'img/[name]',
  logLevel: 'info',
  outdir: 'static',
  minify: true,
  sourcemap: true,
  splitting: false,
  treeShaking: true,
});
