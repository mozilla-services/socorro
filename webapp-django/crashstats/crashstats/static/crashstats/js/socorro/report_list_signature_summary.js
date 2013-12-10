/* jshint jquery:true, strict: true */
/* global Mustache, SIGNATURE_SUMMARY_URL */

var Templates = {};
Templates.percentageByOs = "{{#percentageByOs}} <tr><td> {{os}} </td><td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/percentageByOs}}";
Templates.uptimeRange = "{{#uptimeRange}} <tr><td> {{range}} </td><td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/uptimeRange}}";
Templates.productVersions = "{{#productVersions}} <tr><td> {{product}} </td> <td> {{version}} </td> <td> {{percentage}} %</td><td> {{numberOfCrashes}} </td></tr> {{/productVersions}}";
Templates.architecture = "{{#architectures}} <tr><td> {{architecture}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/architectures}}";
Templates.processType = "{{#processTypes}} <tr><td> {{processType}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/processTypes}}";
Templates.flashVersion = "{{#flashVersions}} <tr><td> {{flashVersion}} </td> <td> {{percentage}} %</td> <td> {{numberOfCrashes}} </td> </tr> {{/flashVersions}}";
Templates.distinctInstall = "{{#distinctInstall}} <tr><td> {{product}} </td> <td> {{version}} </td> <td> {{crashes}}</td><td> {{installations}} </td></tr> {{/distinctInstall}}";
Templates.deviceTmpl = "{{#devices}} <tr><td> {{manufacturer}} </td> <td> {{model}}</td><td> {{version}} </td><td> {{cpu_abi}} </td><td> {{report_count}} </td><td> {{percentage}} %</td></tr> {{/devices}}";
Templates.graphicsTmpl = "{{#graphics}} <tr><td> {{vendor}} </td> <td> {{adapter}}</td><td> {{report_count}} </td><td> {{percentage}} %</td></tr> {{/graphics}}";
Templates.exploitabilityScore = "{{#exploitabilityScore}} <tr><td> {{report_date}} </td> <td> {{null_count}} </td> <td> {{low_count}}</td><td> {{medium_count}} </td> <td> {{high_count}}</td></tr> {{/exploitabilityScore}}";


var SignatureSummary = (function() {
    var loaded = null;

    return {
       activate: function() {
           if (loaded) return;
           var deferred = $.Deferred();
           var $panel = $('#sigsummary');
           var url = $panel.data('url');
           var req = $.ajax({url: url});
           req.done(function(data) {
               $('.loading-placeholder', $panel).hide();
               var empty_signature_summary = true;
               var percentageByOsHtml = "";
               var uptimeRangeHtml = "";
               var productVersionsHtml = "";
               var architectureHtml = "";
               var processTypeHtml = "";
               var flashVersionHtml = "";
               var distinctInstallHtml = "";
               var devicesHtml = "";
               var graphicsHtml = "";
               var exploitabilityScoreHtml = "";
               var report_type = "";

               // Check whether any of the report types has data. If
               // at least one has data, set empty_signature_summary
               // to false.
               for (report_type in data) {
                   if (data[report_type].length) {
                       empty_signature_summary = false;
                   }
               }

               var $wrapper = $('.signature-summary', $panel);

               if (!empty_signature_summary) {

                   percentageByOsHtml = Mustache.to_html(Templates.percentageByOs, data);
                   uptimeRangeHtml = Mustache.to_html(Templates.uptimeRange, data);
                   productVersionsHtml = Mustache.to_html(Templates.productVersions, data);
                   architectureHtml = Mustache.to_html(Templates.architecture, data);
                   processTypeHtml = Mustache.to_html(Templates.processType, data);
                   flashVersionHtml = Mustache.to_html(Templates.flashVersion, data);
                   distinctInstallHtml = Mustache.to_html(Templates.distinctInstall, data);
                   devicesHtml = Mustache.to_html(Templates.deviceTmpl, data);
                   graphicsHtml = Mustache.to_html(Templates.graphicsTmpl, data);

                   /*
                    * The exploitability one is a bit special.
                    * Basically, if you don't have permission to see any exploitability
                    * ratings, the section should not only be empty, it should never even
                    * be visible.
                    */
                   if (data.canViewExploitability) {
                       exploitabilityScoreHtml = Mustache.to_html(Templates.exploitabilityScore, data);
                   } else {
                       $("#exploitabilityScore").remove();
                   }

                   $(percentageByOsHtml).appendTo("#percentageByOsBody");
                   $(uptimeRangeHtml).appendTo("#uptimeRangeBody");
                   $(productVersionsHtml).appendTo("#productVersionsBody");
                   $(architectureHtml).appendTo("#architectureBody");
                   $(processTypeHtml).appendTo("#processTypeBody");
                   $(flashVersionHtml).appendTo("#flashVersionBody");
                   $(distinctInstallHtml).appendTo("#distinctInstallBody");
                   $(devicesHtml).appendTo("#devices");
                   $(graphicsHtml).appendTo("#graphics");
                   if (data.canViewExploitability) {
                       $(exploitabilityScoreHtml).appendTo("#exploitabilityScore tbody");
                   }

                   $(".sig-dashboard-tbl", $wrapper).show();

                   $("caption", $wrapper).on("click", function(event) {
                       event.preventDefault();
                       $(this).parent("table").toggleClass("initially-hidden");
                   });

               } else {
                   $wrapper.append("<p>No summary data found for period.</p>");
               }
               deferred.resolve();
           });
           req.fail(function(data, textStatus, errorThrown) {
               $('.loading-placeholder', $panel).hide();
               $('.loading-failed', $panel).show();
               deferred.reject(data, textStatus, errorThrown);
           });
           loaded = true;
           return deferred.promise();
       }
    };
})();


Panels.register('sigsummary', function() {
    return SignatureSummary.activate();
});
