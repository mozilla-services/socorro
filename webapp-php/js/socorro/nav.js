$(document).ready(function(){
    $('#subnav').hide();
    $('#product-nav').superfish({autoArrows: false});

    $('#simple-search-submit').hide();

    $("#simple-search input[type=text]").focus(function(){
      $(this).attr('value', '');
    });
    $("#simple-search input[type=text]").blur(function(){
      $(this).attr('value', 'Report ID or Crash Signature');
    });

  });
