
/* Javascript for the Pending Reports page */

// Begin the timer and Ajax calls for reports
var original_seconds = 30;
var seconds = original_seconds; 
var number_calls = 1;

// Maintain the time in seconds, and make an ajax call every 30 seconds
function pendingReportTimer(url){ 
    if (seconds == 0){ 
        $('#next_attempt').hide();
        $('#processing').show();

        // Upon the third attempt, state that this failed 
        if (number_calls == 10) {
            $('#checking').hide();
            $('#fail').show();
        } else {
            pendingReportCheck(url);
            number_calls += 1;
            seconds = original_seconds;
            $('#counter').html(original_seconds);
            setTimeout("pendingReportTimer(\""+url+"\")",1000);
        }
    } 
    // Decrement the seconds count
    else { 
        $('#processing').hide();
        $('#next_attempt').show();
        seconds -= 1; 
        $('#counter').html(seconds);
        setTimeout("pendingReportTimer(\""+url+"\")",1000);
    }
}

// Perform the ajax call to check for this report
function pendingReportCheck (url)
{
    $.get(url, {},
        function(responseJSON){  
            if (responseJSON.status == 'ready') {
                top.location = responseJSON.url_redirect;
            }
        },"json"
    );
}
