/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var crashReportsByVersionTmpl = "{{#productVersions}}<div class='release_channel'><h4>{{product}} {{version}}</h4><ul>" +
                                "<li><a href='{{url_base}}topcrasher/byversion/{{product}}/{{version}}/{{duration}}'>Top Crashers</a></li>" +
                                "<li><a href='{{url_base}}products/{{product}}/versions/{{version}}/topchangers?duration={{duration}}'>Top Changers</a></li>" +
                                "<li><a href='{{url_base}}topcrasher/byversion/{{product}}/{{version}}/{{duration}}/plugin'>Top Plugin Crashers</a></li>" +
                                "</div>{{/productVersions}}",
    crashReportsByBuildDateTmpl = "{{#productVersions}}<div class='release_channel'><h4>{{product}} {{version}}</h4><ul>" +
                                  "<li><a href='{{url_base}}topcrasher/by_build_date/{{product}}/{{version}}/{{duration}}'>Top Crashers</a></li>" +
                                  "<li><a href='{{url_base}}products/{{product}}/versions/{{version}}/topchangers?duration={{duration}}'>Top Changers</a></li>" +
                                  "<li><a href='{{url_base}}topcrasher/by_build_date/{{product}}/{{version}}/{{duration}}/plugin'>Top Plugin Crashers</a></li>" +
                                  "</div>{{/productVersions}}";
