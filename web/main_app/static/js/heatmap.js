//fetch dictionary data

var merge_lt_dict = [];
fetch("/api/get-lt-dict")
    .then((response) => response.json())
    .then((data) => {
        merge_lt_dict = data;
    })
    .catch((error) => console.log(error));

var doc_dict = [];
fetch("/api/get-doc-dict")
    .then((response) => response.json())
    .then((data) => {
        doc_dict = data;
    })
    .catch((error) => console.log(error));
// var heatmap_tot_lens = {};
// fetch("/api/get-heatmap-data-len")
//     .then((res) => {
//         heatmap_tot_lens = res;
//     })
//     .catch((err) => {
//         console.error(err);
//     });

// set the dimensions and margins of the graph
var margin = { top: 120, right: 0, bottom: 60, left: 60 },
    width = 950 - margin.left - margin.right,
    height = 640 - margin.top - margin.bottom;

// append the svg object to the body of the page
var svg = d3
    .select("#d3-data-visual")
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

//Read the data
d3.csv("/api/heatmap-data", function (error, data) {
    if (error) throw error;

    var ls = document.getElementById("loader-spinning");
    ls ? (ls.className += " hidden") : "";

    // Labels of row and columns -> unique identifier of the column called 'group' and 'variable'
    var groups = d3
        .map(data, function (d) {
            return d.group;
        })
        .keys();
    var vars = d3
        .map(data, function (d) {
            return d.variable;
        })
        .keys();

    // Build X scales and axis:
    var x = d3.scaleBand().range([0, width]).domain(groups).padding(0.05);
    var mouseover_x = function (d) {
        tooltip.style("opacity", 1);
        d3.select(this).style("font-weight", "bold");
    };
    var mousemove_x = function (d) {
        let text_val = "";
        let dd = doc_dict.find((lt) => lt["doc_id"] === d);
        if (dd) {
            text_val = dd["doc_title"].charAt(0).toUpperCase() + dd["doc_title"].slice(1);
        }
        tooltip
            .html(text_val)
            .style("left", d3.mouse(this)[0] + 10 + "px")
            .style("top", d3.mouse(this)[1] + "px");
    };
    var mouseleave_x = function (d) {
        tooltip.style("opacity", 0);
        d3.select(this).style("font-weight", "400");
    };
    svg.append("g")
        .style("font-size", 9)
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x).tickSize(0))
        .selectAll("text")
        .style("fill", "rgb(4, 19, 120)")
        .style("text-anchor", "end")
        .style("cursor", "pointer")
        .on("mouseover", mouseover_x)
        .on("mousemove", mousemove_x)
        .on("mouseleave", mouseleave_x)
        .attr("dx", "-.8em")
        .attr("dy", ".15em")
        .attr("transform", "rotate(-65)")
        .select(".domain")
        .remove();

    // Build Y scales and axis:
    var y = d3.scaleBand().range([height, 0]).domain(vars).padding(0.05);
    var mouseover_y = function (d) {
        tooltip.style("opacity", 1);
        d3.select(this).style("font-weight", "bold");
    };
    var mousemove_y = function (d) {
        let text_val = "";
        let lt_dict = merge_lt_dict.find((lt) => lt["id"] * 1 === d * 1);
        if (lt_dict) {
            text_val = lt_dict["leg_term"].charAt(0).toUpperCase() + lt_dict["leg_term"].slice(1);
        }
        tooltip
            .html(text_val)
            .style("left", d3.mouse(this)[0] + 10 + "px")
            .style("top", d3.mouse(this)[1] + "px");
    };
    var mouseleave_y = function (d) {
        tooltip.style("opacity", 0);
        d3.select(this).style("font-weight", "400");
    };
    svg.append("g")
        .style("font-size", 9)
        .call(d3.axisLeft(y).tickSize(0))
        .selectAll("text")
        .style("fill", "rgb(4, 19, 120)")
        .style("cursor", "pointer")
        .on("mouseover", mouseover_y)
        .on("mousemove", mousemove_y)
        .on("mouseleave", mouseleave_y)
        .select(".domain")
        .remove();

    // Build color scale
    var color = d3.scaleSequential().interpolator(d3.interpolateInferno).domain([0, 1]);

    // create a tooltip
    var tooltip = d3
        .select("#d3-data-visual")
        .append("div")
        .style("width", 120)
        .style("opacity", 0)
        .attr("class", "tooltip")
        .style("background-color", "white")
        .style("color", "rgb(13, 57, 156)")
        .style("border", "solid")
        .style("stroke", "rgb(13, 57, 156)")
        .style("border-width", "2px")
        .style("border-radius", "5px")
        .style("padding", "5px")
        .style("font-size", "12px");

    // Three function that change the tooltip when user hover / move / leave a cell
    var mouseover = function (d) {
        tooltip.style("opacity", 1);
        d3.select(this).style("stroke", "black").style("opacity", 1);
    };
    var mousemove = function (d) {
        tooltip
            .html(d.value * 1 === 0 ? "Ороогүй" : "Орсон")
            .style("left", d3.mouse(this)[0] + 10 + "px")
            .style("top", d3.mouse(this)[1] + "px");
    };
    var mouseleave = function (d) {
        tooltip.style("opacity", 0);
        d3.select(this).style("stroke", "none").style("opacity", 0.8);
    };

    // add the squares
    svg.selectAll()
        .data(data, function (d) {
            return d.group + ":" + d.variable;
        })
        .enter()
        .append("rect")
        .attr("x", function (d) {
            return x(d.group);
        })
        .attr("y", function (d) {
            return y(d.variable);
        })
        .attr("rx", 4)
        .attr("ry", 4)
        .attr("width", x.bandwidth())
        .attr("height", y.bandwidth())
        .style("fill", function (d) {
            return color(d.value);
        })
        .style("stroke-width", 4)
        .style("stroke", "none")
        .style("opacity", 0.8)
        .on("mouseover", mouseover)
        .on("mousemove", mousemove)
        .on("mouseleave", mouseleave);
});

// Add title to graph
svg.append("text").attr("x", 0).attr("y", -50).attr("text-anchor", "left").style("font-size", "24px").style("fill", "rgb(13, 57, 156)").text("Heatmap диаграмм");

// Add subtitle to graph
svg.append("text")
    .attr("x", 0)
    .attr("y", -20)
    .attr("text-anchor", "left")
    .style("font-size", "16px")
    .style("fill", "rgb(13, 57, 156, 0.5)")
    .style("max-width", 400)
    .text("Дараах диаграмм нь хуулийн баримт бичиг дээрх нэр томьёоны холбоосыг харуулж байна.");
