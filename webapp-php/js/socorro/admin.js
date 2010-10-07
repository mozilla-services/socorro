
// Open the add product version form
function branchAddProductVersion() {
	$('#add_version').show('fast'); 
	$('#product').focus();
}

// Open the add product version form and fill the fields in with given input
function branchAddProductVersionFill(product, version) {
	branchAddProductVersion();
	$('#product').val(product);
	$('#version').val(version);
}

// Open the update product version form and fill the fields in with given input
function branchUpdateProductVersionFill(product, version, branch, start_date, end_date, featured) {
	$('#update_product_version').show('fast'); 
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
	$('#update_branch').focus();
}

// Open the delete product version form and fill the fields in with given input
function branchDeleteProductVersionFill(product, version) {
	$('#delete_product_version').show('fast'); 
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
    $('input[name=email_start_date][type=text], input[name=email_end_date][type=text]').datePicker({
        startDate: '01/01/2008',
    });
});