$(document).ready(function() {
      var dateFormat = 'mm/dd/yyyy hh:mm:ss';
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
	
	/* Advanced search RSS feeds by product and platform */
	var selectedProduct = jQ("#product").val(),
	selectedVersion = jQ("#version").val().toString(),
	selectedPlatform = jQ("#platform").val(),
	protocol = "http://",
	baseURL = "crash-stats.mozilla.com/feed/",
	byProduct = "crashes_by_product/",
	byPlatform = "crashes_by_platform/",
	feedLinkContainer = jQ(".adv-search-rss");
	
	var buildProductFeed = function() {
		var productFeed = {},
		productFeedURL = protocol + baseURL + byProduct + selectedProduct,
		productFeedMsg = "Most recent 500 crashes for " + selectedProduct
		extractedVersionNr = 0;
		
		// If the first index in the version select field is selected we do not want to add 
		// a version number to the feed nor the message
		if(jQ("#version option").filter(":selected").index()) {
			extractedVersionNr = selectedVersion.substring(selectedVersion.indexOf(":") + 1);
		
			productFeedURL = productFeedURL + "/" + extractedVersionNr;
			productFeedMsg = productFeedMsg + " " + extractedVersionNr;
		}
		
		// If no OS is selected, do not add it to the URL nor the message
		if(selectedPlatform !== null) {
			productFeedURL = productFeedURL + "/" + selectedPlatform;
			productFeedMsg = productFeedMsg + " on " + selectedPlatform;
		}
		
		productFeed.url = productFeedURL;
		productFeed.msg = productFeedMsg;
		
		return productFeed;
	},
	buildPlatformFeed = function() {
		var platformFeed = {};
		
		platformFeed.url = protocol + baseURL + byPlatform + selectedPlatform;
		platformFeed.msg = "Most recent 500 crashes for " + selectedPlatform;

		return platformFeed;
	},
	buildListItem = function(linkData) {
		var listItem = document.createElement("li"),
		link = document.createElement("a");
		
		link.setAttribute("href", linkData.url);
		link.appendChild(document.createTextNode(linkData.msg));
		
		listItem.appendChild(link);
		
		return listItem;
	}
	buildHTML = function() {
		var byProduct = buildProductFeed(),
		byPlatform = {};	
		
		feedLinkContainer.append(buildListItem(byProduct));
		if(selectedPlatform !== null) {
			byPlatform = buildPlatformFeed();
			feedLinkContainer.append(buildListItem(byPlatform));
		}
	};
	
	buildHTML();
});
