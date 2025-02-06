// # This Source Code Form is subject to the terms of the Mozilla Public
// # License, v. 2.0. If a copy of the MPL was not distributed with this
// # file, You can obtain one at https://mozilla.org/MPL/2.0/.

import esbuild from 'esbuild';

const entryPoints = ['crashstats/crashstats/static/crashstats/css/crashstats-base.css'];

await esbuild.build({
  bundle: true,
  entryNames: '[ext]/[name]',
  entryPoints,
  external: ['*.gif', '*.svg', '*.png', '*.eot', '*.woff', '*.ttf'],
  format: 'esm',
  logLevel: 'info',
  outdir: 'static',
  minify: true,
  sourcemap: true,
  splitting: false,
  treeShaking: true,
});
