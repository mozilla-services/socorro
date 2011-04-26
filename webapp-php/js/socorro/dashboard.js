$("#adu-chart").ready(function(){
  var colors = chartOpts['colors'] || [ '#058DC7', '#ED561B', '#50B432', '#990099'];
  $('h4').each(function(){
    $(this).css('color',colors.shift())
  })   
});

