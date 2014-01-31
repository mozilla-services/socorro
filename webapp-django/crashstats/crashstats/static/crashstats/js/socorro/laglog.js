/* global filesize */

function drawGraph(name, element, data, averages) {

    var graph = new Rickshaw.Graph( {
       element: element,
        width: 500,
        height: 200,
        renderer: 'line',
        series: [
                 {
                    color: "rgba(123,100,10, 0.3)",
                     data: data,
                     name: name
             },
                 {
                    color: "rgb(123,100,10)",
                       data: averages,
                       name: "Average"
                 },
                ]
    } );

    graph.render();

    var hoverDetail = new Rickshaw.Graph.HoverDetail( {
       graph: graph,
        formatter: function(series, x, y) {
            console.log(series, x, y);
            return filesize(y);
        }
    } );

}


function message_to_classname(message) {
    message = message || 'NORMAL';
    return 'message-' + message;
}

$(function() {

    $.get('/api/LagLog/')
      .then(function(result) {
          //console.dir(result);
          $.each(result.replicas, function(i, data) {
              console.log(data);
              var node = $('<div>')
                .data('name', data.name)
                .addClass(message_to_classname(data.message))
                .addClass('container')
                .append($('<div>')
                        .addClass('numbers')
                        .append($('<h2>')
                                .text(data.name))
                        .append($('<h5>')
                                .text('Latest Rolling Average'))
                        .append($('<h3>')
                                .addClass('number')
                                .text(filesize(data.last_average))))
                .append($('<div>')
                        .addClass('chart'))
                .appendTo($('#all_containers'));
              var chart_element = $('.chart', node);
              if (chart_element.length !== 1) throw "Not one element";
              drawGraph(data.name, chart_element[0], data.rows, data.averages);
          });
      }).fail(function() {
          $('#all_containers')
            .append($('<em>')
                    .text('Currently unable to download lag log data.'));
      });
});
