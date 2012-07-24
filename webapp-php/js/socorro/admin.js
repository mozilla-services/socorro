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

    var missingDataInField = "This field is required and cannot be empty. ",
        incorrectLength = "The number of numerical characters in this field must be neither less, nor more than 14.",
        dataSourcesTabs = $('#data_sources'),
        addReleaseForm = $("#add_release"),
        optionalFieldToggle = $("h4.collapsed"),
        toggleAnchor = $("#optional-fields-toggle");

    var showHideOptionalFields = function() {
            optionalFieldToggle.toggleClass("expanded");
            optionalFieldToggle.next().toggleClass("optional-collapsed");
        },
        clearAllMessages = function() {
            if($("#add_release").length) {
                //removing any previous success or error messages
                $(".success, .error, .usr-error-msg").remove();

                // remove any info or error related classes from
                // element containers.
                $(".field").removeClass("error-field info");
            }
        },
        clearMsgFromContainer = function(container, msgLevel) {
            container.removeClass(msgLevel);
            //ensure and message text that was appended is removed.
            container.find("span").remove();
        }
        notifyUser = function(inputContainer, msgLevel, usrMsg, updateMsg) {
            var msgContainer = document.createElement("span");

            if(!inputContainer.hasClass(msgLevel)) {
                msgContainer.setAttribute("class", "usr-error-msg");
                msgContainer.appendChild(document.createTextNode(usrMsg));
                inputContainer.append(msgContainer).addClass(msgLevel);
            } else if(updateMsg) {
                inputContainer.find(".usr-error-msg").empty().append(usrMsg);
            }
        },
        validateAddRelease = function(form_elem) {
            var hasErrors = false;

            form_elem.find("input").each(function() {
                var usrMsg = "",
                    inputContainer = $(this).parents(".field"),
                    currentInputVal = $.trim($(this).val());

                if($(this)[0].hasAttribute("data-required") && currentInputVal === "") {
                    usrMsg = missingDataInField;
                    hasErrors = true;
                }

                if($(this)[0].hasAttribute("data-requiredlength") &&
                    currentInputVal.length !== parseInt($(this).attr("data-requiredlength"))) {
                        usrMsg += incorrectLength;
                        hasErrors = true;
                }

                // If the usrMsg variables has a length greater than 0 we need to notify the user of errors
                // on this field.
                if(usrMsg.length) {
                    notifyUser(inputContainer, "error-field", usrMsg);
                }
            });
            // Once we have looped over all input elements, we need to check the hasError boolean in order
            // to know whether the form passes validation or not.
            if(hasErrors) {
                return false;
            }
            return true;
        };

    $("#addrelease_tab").click(function() {
        clearAllMessages();
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

    // When the user moves to another field after entering the buildid,
    // ensure that the buildid is not more than 30 days ago from today.
    // If the date is, show a notification to the user to inform them
    // what the implications will be.
    $("#build_id").blur(function(event) {
        var buildID = $.trim($(this).val());

        if(buildID !== "") {
            var enteredTimeInMilis = socorro.date.convertToDateObj(buildID, "ISO8601").getTime(),
                thirtyDaysAgoInMilis = socorro.date.now() - (socorro.date.ONE_DAY * 30),
                inputContainer = $(this).parents(".field");

            // Ensure that the buildid is of the correct length before proceeding
            if(buildID.length === 14) {
                var msgContainer = document.createElement("span"),
                    usrInfoMsg = "The buildid is older than 30 days. You can still add the release but, it will not be viewable from the UI.";

                // Ensure any error message on this field has been removed.
                clearMsgFromContainer(inputContainer, "error-field");

                if(enteredTimeInMilis < thirtyDaysAgoInMilis) {
                    notifyUser(inputContainer, "info", usrInfoMsg);
                } else {
                    clearMsgFromContainer(inputContainer, "info");
                }
            } else {
                notifyUser(inputContainer, "error-field", incorrectLength, true);
            }
        }
    });

    $("#add_release").submit(function(event) {
        event.preventDefault();
        clearAllMessages();

        if(validateAddRelease(addReleaseForm)) {
            var params = addReleaseForm.serialize();

            //add loading animation
            socorro.ui.setLoader("body");

            $.getJSON("/admin/add_product?" + params, function(data) {
                // remove the loading animation
                $(".loading").remove();

                socorro.ui.setUserMsg("legend", data);
            });
        }
    });

    if($("#update_featured").length) {

        var updateFrm = $("#update_featured"),
        userMsgContainer = $(".user-msg"),
        successMsg = "",
        failedMsg = "",
        tbls = $("#update_featured").find("table"),
        errorMsg = "Each product should have a minimum of one and a maximum of four featured products. The following product(s) does not meet this criteria, ",
        params = "";

        updateFrm.submit(function(event) {
            event.preventDefault();

            var prodErrArray = [];

            // Remove any previously displayed error/success messages
            clearAllMessages();
            $(".failed-icon, .success-icon").remove();

            params = $(this).serialize();

            // Loop through all tables and ensure there are no more than four checked input elements,
            // as more than four featured versions per product is not allowed.
            tbls.each(function(i,d) {
                //First ensure that the product has at least one release
                if($(this).find("input[type='checkbox']").length !== 0) {
                    var featuredProdLength = $(this).find("input:checked").length;
                    // If there are more than four, raise an error and prevent form submission.
                    if(featuredProdLength < 1 || featuredProdLength > 4) {
                        prodErrArray.push($(this).attr("data-product"));
                    }
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
