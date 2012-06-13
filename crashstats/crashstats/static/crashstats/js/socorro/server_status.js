$(function() {
  var graphOpts = {
    series: {
      lines: {show: true},
      points: {
        radius: 1,
        show: true,
      }
    },
    legend: {},
    xaxis: {
      ticks: x_ticks,
    },
    yaxis: {
      tickDecimals: 0,
      min: 0,
    },
    grid: {
      color: '#606060',
      borderColor: '#c0c0c0',
      borderWidth: 0,
      minBorderMargin: 9,
    },
    colors: ["#058DC7"],
    shadowSize: 0
  };

  $.plot(
    $("#server-status-graph-jobs-wait"),
    [{ data: waiting_job_count }],
    graphOpts
  );

  $.plot(
    $("#server-status-graph-proc-count"),
    [{ data: processors_count }],
    graphOpts
  );

  $.plot(
    $("#server-status-graph-avg-proc"),
    [{ data: avg_process_sec }],
    graphOpts
  );

  $.plot(
    $("#server-status-graph-avg-wait"),
    [{ data: avg_wait_sec }],
    graphOpts
  );
  $('#server-stats-table').tablesorter();
  $('time.timeago').timeago();
});
