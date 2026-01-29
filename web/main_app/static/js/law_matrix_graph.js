var useGroupInABox = false,
    drawTemplate = false,
    template = "none";

d3.select("#selectTemplate").property("value", template);
d3.select("#checkShowTemplate").property("checked", drawTemplate);

var margin = { top: 8, right: 0, bottom: 0, left: 100 },
    width = 800,
    height = 800;

var force = d3
    .forceSimulation()
    .force("charge", d3.forceManyBody())
    .force("x", d3.forceX(width / 2))
    .force("y", d3.forceY(height / 2));

var svg01 = d3
    .select("#chart01")
    .append("svg")
    .attr("id", "svg01")
    .attr("width", width)
    .attr("height", height)
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var legend01 = d3
    .select("#chart01")
    .append("svg")
    .attr("id", "legend01")
    .attr("width", 270)
    .attr("height", height)
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var margin = { top: 150, right: 0, bottom: 0, left: 150 },
    width = 510,
    height = 510;

var x = d3.scaleBand().rangeRound([0, width]),
    z = d3.scaleLinear().domain([0, 2]).clamp(true),
    c = d3.scaleOrdinal(d3.schemeCategory10).domain(d3.range(10));

var svg02 = d3
    .select("#chart02")
    .append("svg")
    .attr("id", "svg02")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var legend02 = d3
    .select("#chart02")
    .append("svg")
    .attr("id", "legend02")
    .attr("width", 290)
    .attr("height", height + margin.top + margin.bottom);

function createGraphs() {
    var nodes;
    var links;
    var groups;

    d3.csv("/api/nodes", function (error, data) {
        if (error) throw error;
        nodes = data;

        groups = d3
            .nest()
            .key(function (d) {
                return d.group;
            })
            .entries(nodes);

        groups.forEach(function (d, i) {
            var str = "";
            var tmpX;
            var tmpY;

            legend01
                .append("rect")
                .attr("x", 35)
                .attr("y", (parseFloat(d3.select("#legend01").style("height")) - groups.length * 22) / 2 + i * 22)
                .attr("width", 18)
                .attr("height", 18)
                .style("fill", function () {
                    return c(d.key);
                })
                .style("fill-opacity", 0.7)
                .style("stroke", function () {
                    return c(d.key);
                });

            legend01
                .append("text")
                .attr("x", 60)
                .attr("y", (parseFloat(d3.select("#legend01").style("height")) - groups.length * 22) / 2 + 14 + i * 22)
                .attr("class", "legend")
                .text(d.key);

            legend02
                .append("rect")
                .attr("x", 60)
                .attr("y", (parseFloat(d3.select("#legend02").style("height")) - groups.length * 22) / 2 + i * 22)
                .attr("width", 18)
                .attr("height", 18)
                .style("fill", function () {
                    return c(d.key);
                })
                .style("fill-opacity", 0.7)
                .style("stroke", function () {
                    return c(d.key);
                });

            legend02
                .append("text")
                .attr("x", 85)
                .attr("y", (parseFloat(d3.select("#legend02").style("height")) - groups.length * 22) / 2 + 14 + i * 22)
                .attr("class", "legend")
                .text(d.key);
        });

        d3.csv("/api/links", function (error, data) {
            if (error) throw error;
            links = data;

            var groupingForce = forceInABox()
                .strength(0.999)
                .template(template)
                .groupBy("group")
                .links(links)
                .enableGrouping(useGroupInABox)
                .nodeSize(5)
                .linkStrengthIntraCluster(0.001)
                .size([width / 2, height / 2]);
            force.nodes(nodes).force("group", groupingForce).force("charge", d3.forceManyBody()).force("link", d3.forceLink(links).distance(5).strength(groupingForce.getLinkStrength));

            var link = svg01
                .selectAll(".link")
                .data(links)
                .enter()
                .append("line")
                .attr("class", "link")
                .style("stroke-width", function (d) {
                    return Math.sqrt(d.value);
                });

            var node = svg01
                .selectAll(".node")
                .data(nodes)
                .enter()
                .append("circle")
                .attr("class", "node")
                .attr("r", 5)
                .style("fill", function (d) {
                    return c(d.group);
                })
                .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

            node.append("title").text(function (d) {
                return d.name;
            });

            force.on("tick", function () {
                link.attr("x1", function (d) {
                    return d.source.x;
                })
                    .attr("y1", function (d) {
                        return d.source.y;
                    })
                    .attr("x2", function (d) {
                        return d.target.x;
                    })
                    .attr("y2", function (d) {
                        return d.target.y;
                    });

                node.attr("cx", function (d) {
                    return d.x;
                }).attr("cy", function (d) {
                    return d.y;
                });
            });

            d3.select("#selectTemplate").on("change", function () {
                template = d3.select("#selectTemplate").property("value");
                d3.select("#checkShowTemplate").property("checked", false);

                force.force("group").deleteTemplate(svg01);

                if (template == "none") {
                    force.stop();
                    force.force("group").enableGrouping(false);
                    force.alphaTarget(0.5).restart();
                } else {
                    force.stop();
                    force.force("group").enableGrouping(true);
                    force.force("group").template(template);
                    force.alphaTarget(0.5).restart();
                }
            });

            d3.select("#checkShowTemplate").on("change", function () {
                template = d3.select("#selectTemplate").property("value");

                if (template != "none") {
                    drawTemplate = d3.select("#checkShowTemplate").property("checked");
                    if (drawTemplate) {
                        force.force("group").drawTemplate(svg01);
                    } else {
                        force.force("group").deleteTemplate(svg01);
                    }
                }
            });

            var matrix = [];
            var n = nodes.length;

            nodes.forEach(function (node, i) {
                node.index = i;
                node.count = 0;
                matrix[i] = d3.range(n).map(function (j) {
                    return { x: j, y: i, z: 0 };
                });
            });

            links.forEach(function (link) {
                matrix[link.source.index][link.target.index].z += Number(link.value);
                matrix[link.target.index][link.source.index].z += Number(link.value);
                matrix[link.source.index][link.source.index].z += Number(link.value);
                matrix[link.target.index][link.target.index].z += Number(link.value);
                nodes[link.source.index].count += Number(link.value);
                nodes[link.target.index].count += Number(link.value);
            });

            var orders = {
                name: d3.range(n).sort(function (a, b) {
                    return d3.ascending(nodes[a].name, nodes[b].name);
                }),
                count: d3.range(n).sort(function (a, b) {
                    return nodes[b].count - nodes[a].count;
                }),
                group: d3.range(n).sort(function (a, b) {
                    return nodes[b].group - nodes[a].group;
                }),
            };

            x.domain(orders.name);

            svg02.append("rect").attr("class", "background").attr("width", width).attr("height", height);

            var row = svg02
                .selectAll(".row")
                .data(matrix)
                .enter()
                .append("g")
                .attr("class", "row")
                .attr("transform", function (d, i) {
                    return "translate(0," + x(i) + ")";
                })
                .each(row);

            row.append("line").attr("x2", width);

            row.append("text")
                .attr("x", -6)
                .attr("y", x.bandwidth() / 2)
                .attr("dy", ".32em")
                .attr("text-anchor", "end")
                .text(function (d, i) {
                    return nodes[i].name;
                });

            var column = svg02
                .selectAll(".column")
                .data(matrix)
                .enter()
                .append("g")
                .attr("class", "column")
                .attr("transform", function (d, i) {
                    return "translate(" + x(i) + ")rotate(-90)";
                });

            column.append("line").attr("x1", -width);

            column
                .append("text")
                .attr("x", 6)
                .attr("y", x.bandwidth() / 2)
                .attr("dy", ".32em")
                .attr("text-anchor", "start")
                .text(function (d, i) {
                    return nodes[i].name;
                });

            function row(row) {
                var cell = d3
                    .select(this)
                    .selectAll(".cellAM")
                    .data(
                        row.filter(function (d) {
                            return d.z;
                        })
                    )
                    .enter()
                    .append("rect")
                    .attr("class", "cellAM")
                    .attr("x", function (d) {
                        return x(d.x);
                    })
                    .attr("width", x.bandwidth())
                    .attr("height", x.bandwidth())
                    .style("fill-opacity", function (d) {
                        return z(d.z);
                    })
                    .style("fill", function (d) {
                        return nodes[d.x].group == nodes[d.y].group ? c(nodes[d.x].group) : null;
                    })
                    .on("mouseover", mouseover)
                    .on("mouseout", mouseout);
            }

            function mouseover(p) {
                d3.selectAll(".row text").classed("active", function (d, i) {
                    return i == p.y;
                });
                d3.selectAll(".column text").classed("active", function (d, i) {
                    return i == p.x;
                });
            }

            function mouseout() {
                d3.selectAll("text").classed("active", false);
            }

            d3.select("#order").on("change", function () {
                clearTimeout(timeout);
                order(this.value);
            });

            function order(value) {
                x.domain(orders[value]);

                var t = svg02.transition().duration(2500);

                t.selectAll(".row")
                    .delay(function (d, i) {
                        return x(i) * 4;
                    })
                    .attr("transform", function (d, i) {
                        return "translate(0," + x(i) + ")";
                    })
                    .selectAll(".cellAM")
                    .delay(function (d) {
                        return x(d.x) * 4;
                    })
                    .attr("x", function (d) {
                        return x(d.x);
                    });

                t.selectAll(".column")
                    .delay(function (d, i) {
                        return x(i) * 4;
                    })
                    .attr("transform", function (d, i) {
                        return "translate(" + x(i) + ")rotate(-90)";
                    });
            }

            var timeout = setTimeout(function () { }, 5000);
        });
    });
}

function dragstarted(d) {
    if (!d3.event.active) force.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(d) {
    d.fx = d3.event.x;
    d.fy = d3.event.y;
}

function dragended(d) {
    if (!d3.event.active) force.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

createGraphs();
