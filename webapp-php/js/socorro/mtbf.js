
(function(){
  var byOS = [];
  var shouldExpand = true;
  var origionalText = "";
  function handleOS(){
      if(shouldExpand){
        expandOS();
      }else{
        collapseOS();
      }
      return false;
  }
  function expandOS(){
    function display(){
      $.each(byOS, function(i,item){
          SocMtbfSeries.push(item);
        }); //function(data)
        replot();
        origionalText = $('#mtbf-os-drilldown').text();
        $('#mtbf-os-drilldown').text('Hide OS data');
    }
    if( byOS.length == 0 ){
      $('.ajax-loading').show();
      $.getJSON("../../ajax/" + $('#mtbf-product').text() + "/" + $('#mtbf-release-level').text() + "/Each",
        function(data){
          $('.ajax-loading').hide();
          if(data['error']){
            alert('Error loading your request. Sorry: ' + data['error']);
	  }else{
            byOS = data;  
            display();
            shouldExpand = false;
	  }
        });// getJSON()
    }else{
      display();
      shouldExpand = false;
    }
  }
  /**
   * TODO BUGS: collapse / expand causes scale of graph to change form 60 to 7???
   */
  function collapseOS(){
    shouldExpand = true;

    for(var i=0; i < byOS.length; i++){
      SocMtbfSeries.pop();
    }
    
    replot();
    $('#mtbf-os-drilldown').text(origionalText);
  }  
 
  function replot() {
      $('#mtbf-data-details').html("");
      $.each(SocMtbfSeries, function(i, item){
	  li = "<li>" + item['label'] + "- MTBF " + 
                item['mtbf-avg'] + " seconds based on " + 
                item['mtbf-report_count'] + "  crash reports of " +
	        item['mtbf-unique_users'] + " users (blackboxen) from period ";
	  if( item['mtbf-end-dt']){
	    li += "between " + item['mtbf-start-dt'] + " and " + 
	      item['mtbf-end-dt'] + "</li>";
          }else{ 
	    li += "starting at " + item['mtbf-start-dt'] + " </li>";
	  }

	  $('#mtbf-data-details').append(li);
	});
    $.plot($("#mtbf-graph"),
          //series
  	SocMtbfSeries,
        { //options	 
  	  lines: { show: true},
          points: {show:true},
          //legend: { position: 'ne', show: true }
          legend: { show: true, container: $("#overviewLegend") }
	  /*	    xaxis: {ticks: 30, tickSize: 2} */

        }
    );
  }
  $(document).ready(function(){      
      replot();
      $('#mtbf-os-drilldown').click(handleOS);

    });  
})();
