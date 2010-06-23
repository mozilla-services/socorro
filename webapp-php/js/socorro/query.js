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

      $('[name=process_type]').bind('change', function(){
          if ($('[name=process_type]:checked').val() == "plugin") {
	      $('#plugin-inputs').removeClass('disabled');
	      $('#plugin-inputs *').attr('disabled', null);
          } else {
	      $('#plugin-inputs').addClass('disabled');
	      $('#plugin-inputs *').attr('disabled', 'disabled');
          }
      }).trigger('change');

    $(function() {
        $('#dateHelp *').tooltip();
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

    // Upon submitting the form, hide the submit button and disable refresh options.
    $('#searchform').bind('submit', function () {
        if ($('input[name=date]').val() == dateFormat) {
            $('input[name=date]').val('');
        }
        
        $('input[type=submit]', this).attr('disabled', 'disabled');
        $('#query_submit').hide();
        $('#query_waiting').show();
    
        $(document).bind("keypress", function(e) {
            if (e.keyCode == 13 || e.keyCode == 116) {
                return false;
            }            
        });
    });
    
    if($.trim($('input[name=date]').val()) == ""){
      $('input[name=date]').val(dateFormat);
    }
    function productUpdater() {
        var selected =  $('select[name=product]').val();
        if(selected.length > 0){
	       updateVersion(selected);
        }
    }
  $('select[name=product]').bind('change', productUpdater);

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
