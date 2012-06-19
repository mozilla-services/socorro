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
    
    var dataSourcesTabs = $('#data_sources');
    
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
    
    if(dataSourcesTabs.length) {
        dataSourcesTabs.tabs({
            cookie: {
                expires: 1
            }
        }).show();
    }
    
    //hide the loader
    $("#loading-bds").hide();
});
