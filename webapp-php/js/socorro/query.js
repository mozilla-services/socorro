$(document).ready(function() {
      var dateFormat = 'mm/dd/yyyy';
      var showAdvFilter = $.cookies.get('advfilter');
      var showAdvFilterCookieOpts = {};

      if (showAdvFilter === null) {
	  showAdvFilter = false;
          $.cookies.set('advfilter', showAdvFilter, showAdvFilterCookieOpts);
      }
      
      if (showAdvFilter) {
          $('#advfilter').show();
      } else {
	  $('#advfilter').hide();      
      }

      $('#advfiltertoggle').click(function() {
          $('#advfilter').toggle("fast");
	  var showAdvFilter = ! $.cookies.get('advfilter');
  	  $.cookies.set('advfilter', showAdvFilter, showAdvFilterCookieOpts);
          if (showAdvFilter){
              $('#advfilter').show();
          } else {
	       $('#advfilter').hide();      
          }
      });

      //Process/Plugin area
      $('[name=process_type]').cookieBind();
      $('[name=plugin_field]').cookieBind();
      $('[name=plugin_query_type]').cookieBind();

      $('[name=hangtype]').bind('change', function(){
          // Hangs
          if ($('input[name=hangtype][value=hang]').attr('checked') == true) {
              $('[name=process_type]').attr('disabled', null).trigger('change');
          
          // All, Crash
          } else {
              $('[name=process_type]').attr('disabled', true);
	      $('#plugin-inputs').addClass('disabled');
	      $('#plugin-inputs *').attr('disabled', 'disabled');
          }
      });

      $('[name=process_type]').bind('change', function(){
          if ($('[name=process_type]:checked').val() == "plugin") {
	      $('#plugin-inputs').removeClass('disabled');
	      $('#plugin-inputs *').attr('disabled', null);
          } else {
	      $('#plugin-inputs').addClass('disabled');
	      $('#plugin-inputs *').attr('disabled', 'disabled');
          }
      }).trigger('change');

      $('[name=hangtype]').trigger('change');

      $(function() {
          Date.format='yyyy-mm-dd';
          $('.date-pick').datePicker();
          $('.date-pick').dpSetStartDate('2007-01-01');
          $('#signatureList').tablesorter({
              headers: { 
                  0: { sorter: 'digit' }, 
                  2: { sorter: 'digit' }, 
                  3: { sorter: 'digit' }, 
                  4: { sorter: 'digit' }, 
                  5: { sorter: 'digit' }, 
                  6: { sorter: 'digit' } 
              }
          }); 
      });

    $('#searchform').bind('submit', function(){
	if($('input[name=date]').val() == dateFormat){
	  $('input[name=date]').val('');
	}
      });
    if($.trim($('input[name=date]').val()) == ""){
      $('input[name=date]').val(dateFormat);
    }
    function productUpdater() {
        var selected =  $('select[name=product]').val();
        if(selected.length > 0){
	    if (selected == "ALL") {
	       updateVersionWithAllVersions();
  	    } else {
	       updateVersion(selected);
	    }
        }
    }
  $('select[name=product]').bind('change', productUpdater);

  function updateVersionWithAllVersions() {
      var prods = [];
      for (var key in prodVersMap) { prods.push(key); }
      updateVersion(prods, [])
  }
  function updateVersion(products, selected){
    var sel = selected || [];
    var s = "<option value='ALL:ALL'>All</option>";
    for(var j=0; j < products.length; j++){
      var product = products[j];
      for(var i=0; i < prodVersMap[product].length; i++){
        var v = [prodVersMap[product][i]['product'],
                 prodVersMap[product][i]['version']];
        var att = "";
        if($.inArray(v.join(':'), sel) >= 0){
	  att = " selected='true'";
	}
        s += "<option value='" + v.join(':') + "'" + att + ">" + v.join(' ') + "</option>";
      }
    }
    $('select[name=version]').html(s);
    //If nothing was already selected, pick the first item
    if( $('select[name=version]').val() == null ){
      $('select[name=version] option:first').attr('selected', true);
    }
  }

  updateVersion(socSearchFormModel.product, socSearchFormModel.version);

   $('#gofilter').bind('click', function(){
      $('#searchform').submit();
    });
    window.updateVersion = updateVersion;  
});


