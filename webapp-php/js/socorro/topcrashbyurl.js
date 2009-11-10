$(document).ready(function(){
    //$('#raw_mtbf_data').tablesorter();

    var product = $('#tcburl-product').text();
    var version = $('#tcburl-version').text();
    var caches = {};
    var urlToggler = function(e){
      function loadSignatureForUrl(urlId, domain, page, indent){
        page = page || 1;
	indent = indent || 1;
        $.getJSON("../../signaturesforurl/" + product + "/" + version + "?url=" + url + "&page=" + page,
  	  	    function(data){
                      var upd = "";
                      /* TODO rewrite this for clarity...
                         urlToggler on byurl page simply toggles signatures under this url. 
                         urlToggler on bydomain page is adding rows in the context of an "outter"
                         domain row, which when toggled should also hide these signatures. so we 
                         add a tcburl-urls0 to have all these signature hide when domain row 0 is hidden.
                      */
                      var outterClass = " nomatch";
                      var domainRowId = id.match(/(\d+)_\d+/);
                      if( domainRowId ){
                        outterClass = " tcburl-urls" + domainRowId[1];
		      }
                      for(var i=0; i < data.length; i++){
                        var signatureLink = "../../../report/list?product=" + product + "&version=" + product + "%3A" + version +
	                                    "&date=&range_value=1&range_unit=weeks&query_search=signature&query=" + 
				            data[i].signature + "&query_type=exact&do_query=1&signature=" + data[i].signature;

  		        upd += "<tr class='tcburl-signatures" + urlId + outterClass + "'><td class='in" + indent + "'><a href='" + signatureLink+ "'>" + data[i].signature + "</a></td><td>" + data[i].count + "</td></tr>";
                        if(data[i]['comments']){
                          upd += "<tr class='tcburl-signatures" + urlId + outterClass + "'><td class='in" + indent + "' colspan='2'><ul>";
                          for( var j=0; j < data[i]['comments'].length; j++){

  			    var crash = data[i]['comments'][j];
                            upd += "<li class='commented'><a href='../../../report/index/" + crash['report-id'] + "'>" + crash.comments + "</a></li>";
 			  }
                          upd += "</ul></td></tr>";
		        }
		        //aok$('#tcburl-domainToggle-row' + urlId + ' td:first img').hide();

			caches[index] = true;
		      }//end for
	              
                      if( data.length >= 50){
		        $('#tcburl-urlToggle-row' + urlId + ' td:first').append("<a id='tcburl-moresig" + 
									   urlId + "' class='page" + (page + 1)+ "' href='#'>Load 50 more (page " + (page + 1) + ")</a>");
                        $('#tcburl-moresig' + urlId).click(function(){
                            $('#tcburl-moresig' + urlId).remove();
  			    loadSignatureForUrl(urlId, url, (page + 1));
                            return false;
			  });
		      }
                      $('#tcburl-urlToggle-row' + urlId).after(upd);
                      $('#tcburl-urlToggle-row' + urlId).remove();
	      });
        return false;
      }//function loadSignatureForUrl
      var index = $(this).attr("id");
      //As we get further nested we add _. We can see how many levels
      //url signatures - 'tcburl-url0' - 1 indentation
      //domain url signatures - 'tcburl-url0_0' - 2 indentation
      var indent = function(index){ return index.split('_').length };
      var label = "+";
      if(e.target){
          var theId = $(e.target).parent().attr('id');
  	  var offset;
	  var id;
	  var url;
          //Either + widget or link with url text can trigger this event
          if( /^url-to-sig.*/.test(theId) ){
  	    offset = "url-to-sig".length;
	  }else{
  	    offset = "tcburl-url".length;
	  }
          id = theId.substring(offset);
	  url = escape( $('#tcburl-url' + id + " .url").text() );

	  if(caches[index]){
	    if(window.console) console.info("Using cached crashData");
	  }else{
            loadSignatureForUrl(id, url, null, indent(index));
          }

	  if( $('#url-to-sig' + id).text() == "+"){
	    $('#url-to-sig' + id).text("-");
	    label = "-";
  	  }else{
	    $('#url-to-sig' + id).text("+");
	    label = "+";
  	  }
	  
          $('#tcburl-urlToggle-row' + id).toggle();
	  $('.tcburl-signatures' + id).toggle();
        }
      return false;
      };

    var domainToggler = function(e){
      function loadUrlsForDomain(domainId, domain, page){
        page = page || 1;
        $('#tcburl-domainToggle-row' + id).show();
        $.getJSON("../../urlsfordomain/" + product + "/" + version + "?domain=" + domain + "&page=" + page,
  	  	    function(data){
                      var upd = "";
                      for(var i=0; i < data.length; i++){
                        upd += "<tr class='tcburl-urls" + domainId + "'><td class='in1'><div id='url-to-sig" + domainId + "_" + i;
                        upd += "' class='tcburl-toggler tcburl-urlToggler'>+</div>";
                        upd += "<a id='tcburl-url" + domainId + "_" + i + "' class='tcburl-urlToggler' href='#'>Expand ";

		        upd += "<span class='url'>" + data[i].url + "</span></a> <a href='" +  data[i].url + "'>Open This URL</a></td><td class='url-crash-count'>";
                        upd += data[i].count + "</td></tr>";

                        upd += "<tr id='tcburl-urlToggle-row" + domainId + "_" + i + "' style='display: none'><td colspan='2'></td></tr>";
		        //aok $('#tcburl-domainToggle-row' + domainId + ' td:first img').hide();
                        
			//TODO caches here ahave to be doman+urlindex
			caches[index] = true;

		      }//end for

                      if( data.length >= 50){

		        $('#tcburl-domainToggle-row' + domainId + ' td:first').append("<a id='tcburl-moreurls" + 
									   domainId + "' class='page" + (page + 1)+ "' href='#'>Load 50 more (page " + (page + 1) + ")</a>");
                        $('#tcburl-moreurls' + domainId).click(function(){
                            $('#tcburl-moreurls' + domainId).remove();
  			    loadUrlsForDomain(domainId, domain, (page + 1));
                            return false;
			  });
		      }
                      $('#tcburl-domainToggle-row' + domainId).after(upd);
                      $('#tcburl-domainToggle-row' + domainId).remove();
                      $('.tcburl-urlToggler').click(urlToggler, {"in": 2});
                      $('#tcburl-domainToggle-row' + id).show();
	      });
        return false;
      }
      var index = $(this).attr("id");
      var label = "+";
      if(e.target){
          var theId = $(e.target).parent().attr('id');
  	  var offset;
          var id;
          var url
	  if( /^domain-to-url.*/.test(theId) ){
            offset = "domain-to-url".length;
	  }else{
            offset = "tcburl-url".length;
	  }
          id = theId.substring(offset);
          url = escape( $('#tcburl-url' + id + " .url").text() );

	  if(caches[index]){
	    if(window.console) console.info("Using cached crashData");
	  }else{
            loadUrlsForDomain(id, url);
          }
	  if( $('#domain-to-url' + id).text() == "+"){
	    $('#domain-to-url' + id).text("-");
	    label = "-";
  	  }else{
	    $('#domain-to-url' + id).text("+");
	    label = "+";
  	  }

          $('#tcburl-urlToggle-row' + id).toggle();          

          var el = $('#domain-to-url' + id);

          if(el.hasClass('viz')){
            $('.tcburl-urls' + id + ':visible').hide();
            el.removeClass('viz')
	  }else{
            $('.tcburl-urls' + id + ':hidden').show();
            el.addClass('viz')
	  }
          
        }
        return false;
      };
   $('.tcburl-urlToggler').click(urlToggler);
   $('.tcburl-domainToggler').click(domainToggler);
   //TODO remove handlers
 });
