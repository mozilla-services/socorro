/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

// Open the add product version form and fill the fields in with given input
function branchAddProductVersionFill(product, version) {
    $('#add_version').simplebox();
    $('#product').val(product);
    $('#version').val(version);
}

// Replace the submit button with a progress icon
function hideShow(hideId, showId) {
    $('#'+hideId).hide();
    $('#'+showId).show('fast');
}

$(document).ready(function(){

    var dataSourcesTabs = $('#data_sources'),
        optionalFieldToggle = $("h4.collapsed"),
        toggleAnchor = $("#optional-fields-toggle"),
        showHideOptionalFields = function() {
            optionalFieldToggle.toggleClass("expanded");
            optionalFieldToggle.next().toggleClass("optional-collapsed");
        },
        clearMessages = function() {
            //removing any previous success or error messages
            $(".success, .error").remove();
        };

    $("#add_release_tab").click(function() {
        clearMessages();
    });

    if(optionalFieldToggle) {
        toggleAnchor.click(function(event) {
            event.preventDefault();
            showHideOptionalFields();
        });
    }

    // When a optional field receives focus, for example when tabbed into,
    // show the optional fields.
    $("section.optional input").focus(function() {
        // but, only if it is currently hidden
        if(optionalFieldToggle.next().hasClass("optional-collapsed")) {
            showHideOptionalFields();
        }
    });

    $("#add_product").submit(function() {
        var params = $(this).serialize();

        clearMessages();

        //add loading animation
        socorro.ui.setLoader("body");

        $.getJSON("/admin/add_product?" + params, function(data) {
            // remove the loading animation
            $(".loading").remove();

            socorro.ui.setUserMsg("legend", data);
        });
        return false;
    });

    if($("#update_featured").length) {

        var updateFrm = $("#update_featured"),
        userMsgContainer = $(".user-msg"),
        successMsg = "",
        failedMsg = "",
        tbls = $("#update_featured").find("table"),
        errorMsg = "Each product should have a minimum of one, and a maximum of four featured products. The following products does not meet this criteria, ",
        params = "";

        updateFrm.submit(function(event) {
            event.preventDefault();

            var prodErrArray = [];

            // Remove any previously displayed error/success messages
            clearMessages();
            $(".failed-icon, .success-icon").remove();

            params = $(this).serialize();

            // Loop through all tables and ensure there are no more than four checked input elements,
            // as more than four featured versions per product is not allowed.
            tbls.each(function(i,d) {
                var featuredProdLength = $(this).find("input:checked").length;

                // If there are more than four, raise an error and prevent form submission.
                if(featuredProdLength < 1 || featuredProdLength > 4) {
                    prodErrArray.push($(this).attr("data-product"));
                }
            });

            if(prodErrArray.length > 0) {
                $("<p class='error'>" + errorMsg + prodErrArray.join(",") + "</p>").insertBefore(updateFrm);
                window.scroll(0, 0);
            } else {
                userMsgContainer.simplebox();
                //add loading animation
                socorro.ui.setLoader(".user-msg", "simplebox-loader");

                $.getJSON("/admin/update_featured_versions?" + params, function(data) {
                    successMsg = "<p class='success-icon'>" + data.message + "</p>";
                    failedMsg = "<p class='failed-icon'>" + data.message + "</p>";

                    // remove the loading animation
                    $(".simplebox-loader").remove();

                    if(data.status === "success") {
                        userMsgContainer.append(successMsg);
                    } else {
                        userMsgContainer.append(failedMsg);
                    }
                });
            }
        });
    }

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
