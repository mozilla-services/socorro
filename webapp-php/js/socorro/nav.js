$(document).ready(function(){
    $('#subnav').hide();
    jQuery('#product-nav').superfish({autoArrows: false});
    $("#simple-search input[type=text]").focus(function(){
      $(this).attr('value', '');
    });
    $("#simple-search input[type=text]").blur(function(){
      $(this).attr('value', 'Report ID or Crash Signature');
    });
  });
