var margin = {top: 1, right: 1, bottom: 6, left: 1},
    width = 960 - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom;

var format = d3.format(",.0f"),
    color = function(node) {
        if (node.error_count > 0 || node.errors > 0) {
            return "#E41A1C"; // red
        }
        if (node.skips > 0) {
            return "#fafa78"; // yellow
        }
        return "#4DAF4A"; // green
    },
    title = function(d) {
        var name = d.name,
            errors = d.errors,
            skips = d.skips;

        if (name === undefined) {
            name = d.source.name;
        }
        if(errors > 0) {
            return name + " has failed " + format(errors) + " times";
        }
        if (skips > 0) {
            return name + " has been skipped " + format(skips) + " times.";
        }
        return name + " is working normally.";
    };

var svg = d3.select('#crontabber-chart').append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
  .append('g')
    .attr('transform',
          'translate(' + margin.left + ',' + margin.top + ')');

var sankey = d3.sankey()
    .nodeWidth(15)
    .nodePadding(10)
    .size([width, height]);

var path = sankey.link();

d3.json("data.json", function(data) {

    /**
     * Reshape the data
     * Sankey wants the following:
     *   nodes: [ { name: 'something' }, { name: 'otherthing' } ]
     *   links: [ { source: 0, target: 1, value: 9001 } ]
     */
    var nodes = _.map(data.state, function(v, k, l) {
        v.name = k;
        return v;
    });

    // cache array positions
    _.each(nodes, function(e, i, l) {
        e.pos = i;
    });

    // infer skip counts by recursively walking up the tree
    // cache results in the node state
    _.each(nodes, function count_skips(node) {
        if (node.skips) {
            return node.skips;
        }
        var parents = _.map(node.depends_on, function(name) {
                return data.state[name];
            }),
            skips = _.map(parents, count_skips),
            errors = _.pluck(parents, "error_count");
        skips = _.max([_.max(errors) + _.max(skips), 0]);
        node.skips = skips;
        return skips;
    });

    // reverse linked lists
    var links = [];
    _.each(nodes, function(element, index, list) {
        _.each(element.depends_on, function (d) {
            var dep = data.state[d];
            links.push({
                source: dep.pos,
                target: index,
                value: 1,
                errors: dep.error_count,
                skips: dep.skips
            });
        });
    });

    sankey
        .nodes(nodes)
        .links(links)
        .layout(32);

    var link = svg.append("g").selectAll(".link")
        .data(links)
      .enter().append("path")
        .attr("class", "link")
        .attr("d", path)
        .style("stroke-width", function(d) {
            return Math.max(1, d.dy);
        })
        .style("stroke", function(d) {
            return d.color = color(d);
        })
        .sort(function(a, b) { return b.dy - a.dy; });

    link.append("title")
        .text(title);

    var node = svg.append('g').selectAll(".node")
        .data(nodes)
      .enter().append('g')
        .attr('class', 'node')
        .attr('transform', function(d) {
            return "translate(" + d.x + "," + d.y + ")";
        })
      .call(d3.behavior.drag()
        .origin(function(d) { return d; })
        .on('dragstart', function() {
            this.parentNode.appendChild(this);
        })
        .on("drag", dragmove));

    node.append("rect")
        .attr("height", function(d) { return d.dy; })
        .attr("width", sankey.nodeWidth())
        .style("fill", function(d) {
            return d.color = color(d);
        })
        .style("stroke", function(d) {
            return d3.rgb(d.color).darker(2);
        })
      .append("title")
        .text(title);

    node.append('text')
        .attr('x', -6)
        .attr('y', function(d) { return d.dy / 2; })
        .attr('dy', ".35em")
        .attr('text-anchor', 'end')
        .attr('transform', null)
        .text(function(d) { return d.name; })
      .filter(function(d) { return d.x < width / 2;})
        .attr('x', 6 + sankey.nodeWidth())
        .attr('text-anchor', 'start');

    function dragmove(d) {
        d.y = Math.max(0, Math.min(height - d.dy, d3.event.y));
        d3.select(this).attr(
            "transform",
            "translate(" + d.x + "," + d.y + ")");
        sankey.relayout();
        link.attr("d", path);
    }

    // misconfigured, no jobs
    // potential hook for a heads up
    if (_.size(data.state) < 2) {
        return;
    }

    var table = d3.select('#crontabber-table').append('table'),
        thead = table.append('thead'),
        tbody = table.append('tbody'),
        tableFields = [
            'name',
            'error_count',
            'next_run',
            'last_success',
            'depends_on'
        ];

    table.classed('tablesorter', true)

    thead.append("tr").selectAll("td")
        .data(tableFields)
      .enter().append("td")
        .text(function capitalize(s) {
            return s[0].toUpperCase() + s.slice(1);
        })
        .classed("header", true);

    var tr = tbody.selectAll("tr")
        .data(nodes)
      .enter().append("tr")
        .selectAll("td")
        .data(function(d) {
            // get only the tableFields
            var scrubbed = _.map(tableFields, function(field) {
                return d[field];
            });
            return scrubbed;
        })
      .enter().append("td")
        .text(function(d, i) {
            field = tableFields[i];
            isTime = (field === "last_success" || field === "next_run");
            if (isTime) {
                return moment(d).fromNow();
            }
            if (typeof(d) === "object") {
                joined = _.reduce(d, function(m, i) {
                    return m + i + ', ';
                }, '');
                return joined.substring(0, joined.length - 2);
            }
            return d;
        });

    $('crontabber-table tablesorter').tablesorter();
});
