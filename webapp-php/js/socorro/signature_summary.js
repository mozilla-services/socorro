/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var percentageByOsTmpl = "{{#percentageByOs}} <tr><td> {{os}} </td><td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/percentageByOs}}";
var uptimeRangeTmpl = "{{#uptimeRange}} <tr><td> {{range}} </td><td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/uptimeRange}}";
var productVersionsTmpl = "{{#productVersions}} <tr><td> {{product}} </td> <td> {{version}} </td> <td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/productVersions}}";
var architectureTmpl = "{{#architectures}} <tr><td> {{architecture}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/architectures}}";
var processTypeTmpl = "{{#processTypes}} <tr><td> {{processType}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/processTypes}}";
var flashVersionTmpl = "{{#flashVersions}} <tr><td> {{flashVersion}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/flashVersions}}";
