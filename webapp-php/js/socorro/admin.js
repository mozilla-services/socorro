// Open the add product version form and fill the fields in with given input
function branchAddProductVersionFill(product, version) {
	$('#add_version').simplebox();
	$('#product').val(product);
	$('#version').val(version);
}

// Open the update product version form and fill the fields in with given input
function branchUpdateProductVersionFill(product, version, branch, start_date, end_date, featured, throttle) {
	$('#update_product_version').simplebox();
	$('#update_product').val(product);
	$('#update_product_display').html(product);
	$('#update_version').val(version);
	$('#update_version_display').html(version);
	$('#update_branch').val(branch);
	$('#update_start_date').val(start_date);
	$('#update_end_date').val(end_date);
	if (featured == 't') {
	    $('#update_featured').attr('checked','checked');
	} else {
	    $('#update_featured').removeAttr('checked');
	}
	$('#update_throttle').val(throttle);
	$('#update_branch').focus();
}

// Open the delete product version form and fill the fields in with given input
function branchDeleteProductVersionFill(product, version) {
	$('#delete_product_version').simplebox();
	$('#delete_product').val(product);
	$('#delete_product_display').html(product);
	$('#delete_version').val(version);
	$('#delete_version_display').html(version);
	$('#delete_product').focus();
}

// Replace the submit button with a progress icon
function hideShow(hideId, showId) {
	$('#'+hideId).hide();
	$('#'+showId).show('fast');
}

$(document).ready(function(){
	/* Emails */
    $('input[name=email_start_date][type=text], input[name=email_end_date][type=text]').datepicker({
		dateFormat: "dd/mm/yy"
	});
	
	/* Add new */
	$("#start_date, #end_date").datepicker({
		dateFormat: "yy/mm/dd"
	});
	
	/* Update */
	$("#update_start_date, #update_end_date").datepicker({
		dateFormat: "yy/mm/dd"
	});
	
    $('input[name=submit][type=submit][value="OK, Send Emails"]').click(function(){
      postData = {token: $('input[name=token]').val(),
                  campaign_id: $('input[name=campaign_id]').val(),
                  submit: 'start'}
      $.post('/admin/send_email', postData);
    });
    $('input[name=submit][type=submit][value="STOP Sending Emails"]').click(function(){
      postData = {token: $('input[name=token]').val(),
                  campaign_id: $('input[name=campaign_id]').val(),
                  submit: 'stop'}
      $.post('/admin/send_email', postData);
    });

    $('.admin tbody tr:odd').css('background-color', '#efefef');
    
    $('#data_sources').tabs({
        cookie: {
            expires: 1
        }
    }).show();
    
    //hide the loader
    $("#loading-bds").hide();
    
    // data containers for branch data sources
    var missingEntriesContainer = $("#missingentries"),
    incompleteEntriesContainer = $("#incompleteentries"),
    productsContainer = $("#products"),
    nceContainer = $("#noncurrententries");
    
    if(productsContainer.length && nceContainer.length) {
        // we need to know the current state of the table and therefore adding the expanded class
        // to the first table in each of the relevant containers.
        var missingEntriesTbl = missingEntriesContainer.find("table:eq(0)").addClass("expanded"),
        incompleteEntriesTbl = incompleteEntriesContainer.find("table:eq(0)").addClass("expanded"),
        firstProdTbl = productsContainer.find("table:eq(0)").addClass("expanded"),
        firstNceTbl = nceContainer.find("table:eq(0)").addClass("expanded");
        
        // set the icon for the first tbl to the collapse icon as these will be
        // expanded by default
        missingEntriesTbl.find("th:last-child span").addClass("collapse");
        incompleteEntriesTbl.find("th:last-child span").addClass("collapse");
        firstProdTbl.find("th:last-child span").addClass("collapse");
        firstNceTbl.find("th:last-child span").addClass("collapse");
        
        //collapse all but the first table inside the product and non current entries containers
        productsContainer.find("table:gt(0)").addClass("collapsed").find("tbody").addClass("hide_body");
        nceContainer.find("table:gt(0)").addClass("collapsed").find("tbody").addClass("hide_body");
        
        $("table thead").click(function(event) {
            var currentTbl = $(this).parents("table");
            if(currentTbl.hasClass("expanded")) {
                currentTbl.removeClass("expanded").addClass("collapsed")
                currentTbl.find("tbody").addClass("hide_body");
                //change icon to expand
                currentTbl.find("th:last-child span").removeClass("collapse");
            } else {
                currentTbl.removeClass("collapsed").addClass("expanded")
                currentTbl.find("tbody").removeClass("hide_body");
                //change icon to collapse
                currentTbl.find("th:last-child span").addClass("collapse");
            }
        });
    }
});
