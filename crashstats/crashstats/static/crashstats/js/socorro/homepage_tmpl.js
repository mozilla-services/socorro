var crashReportsByVersionTmpl = "{{#product_versions}}<div class='release_channel'><h4>{{product}} {{version}}</h4><ul>" +
                                "<li><a href='/topcrasher/products/{{product}}/versions/{{version}}?days={{duration}}'>Top Crashers</a></li>" +
                                "<li><a href='/topchangers/products/{{product}}/versions/{{version}}?days={{duration}}'>Top Changers</a></li>" +
                                "<li><a href='/topcrasher/products/{{product}}/versions/{{version}}/crash_type/plugin?days={{duration}}'>Top Plugin Crashers</a></li>" +
                                "</div>{{/product_versions}}",
    crashReportsByBuildDateTmpl = "{{#product_versions}}<div class='release_channel'><h4>{{product}} {{version}}</h4><ul>" +
                                  "<li><a href='/topcrasher/products/{{product}}/versions/{{version}}?days={{duration}}'>Top Crashers</a></li>" +
                                  "<li><a href='/topchangers/products/{{product}}/versions/{{version}}?days={{duration}}'>Top Changers</a></li>" +
                                  "<li><a href='/topcrasher/products/{{product}}/versions/{{version}}/crash_type/plugin?days={{duration}}'>Top Plugin Crashers</a></li>" +
                                  "</div>{{/product_versions}}";
