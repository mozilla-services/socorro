var percentageByOsTmpl = "{{#percentageByOs}} <tr><td> {{os}} </td><td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/percentageByOs}}";
var uptimeRangeTmpl = "{{#uptimeRange}} <tr><td> {{range}} </td><td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/uptimeRange}}";
var productVersionsTmpl = "{{#productVersions}} <tr><td> {{product}} </td> <td> {{version}} </td> <td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/productVersions}}";
var architectureTmpl = "{{#architectures}} <tr><td> {{architecture}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/architectures}}";
var processTypeTmpl = "{{#processTypes}} <tr><td> {{processType}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/processTypes}}";
var flashVersionTmpl = "{{#flashVersions}} <tr><td> {{flashVersion}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/flashVersions}}";
var distinctInstallTmpl = "{{#distinctInstall}} <tr><td> {{product}} </td> <td> {{version}} </td> <td> {{crashes}} %</td><td> {{installations}} </td></tr> {{/distinctInstall}}";
