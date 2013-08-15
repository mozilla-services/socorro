/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(document).ready(function() {
  $('.explosive-item').each(function(i, element) {
    var element = $(element);
    var signature = element.attr('data-signature');
    var date = element.attr('data-date');
    var reportUrl = element.attr('data-url');

    var url = '/explosive-data/signature/' + signature + '/date/' + date;

    var req = $.ajax({
      url: url,
      type: 'GET',
      dataType: 'json'
    });

    req.done(function(data) {
      data = data.counts;
      var plotdata = [];
      var xticks = [];
      var vlinespot;
      for (var i=0; i<data.length; i++) {
        if (data[i][0] === date) {
          vlinespot = i;
        }
        plotdata.push([i, data[i][1]]);
        xticks.push([i, data[i][0]]);
      }

      plotdata = [{
        data: plotdata,
        lines: { show: true },
        points: { show: true },
      }];

      var options = {
        xaxis: {
          ticks: xticks
        },
        grid: {
          markings: [
            { color: "#e9e9e9", xaxis: { from: vlinespot - 0.5, to: vlinespot + 0.5 } }
          ],
          hoverable: true,
          clickable: true
        }
      };

      var plotarea = element.children('.explosive-plot');
      $.plot(plotarea, plotdata, options);

      var showTooltip = function(date, count, pos) {
        var div = $('<div id="tooltip"></div>');
        div.text(date + " Count: " + count);
        div.css({
          position: "absolute",
          top: pos.pageY + 5,
          left: pos.pageX + 5,
          border: "1px solid #fdd",
          padding: "5px",
          "background-color": "#fee",
          opacity: 0.80,
          "font-size": "15px"
        });
        div.appendTo("body");
      };

      $(plotarea).bind("plothover", function (event, pos, item) {
        $("#tooltip").remove();
        if (item) {
          var date = data[item.dataIndex][0];
          var count = data[item.dataIndex][1][0];
          showTooltip(date, count, pos)
        }
      });

      $(plotarea).bind("plotclick", function(event, pos, item) {
        if (item) {
          var date = data[item.dataIndex][0];
          window.location = reportUrl + '&date=' + date;
        }
      });
    });
  });
});