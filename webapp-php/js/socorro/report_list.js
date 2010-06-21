/*jslint browser:true */ 
/*global socSortCorrelation, SocReport, $*/

Date.prototype.format=function(format){var returnStr='';var replace=Date.replaceChars;for(var i=0;i<format.length;i++){var curChar=format.charAt(i);if(replace[curChar]){returnStr+=replace[curChar].call(this);}else{returnStr+=curChar;}}return returnStr;};Date.replaceChars={shortMonths:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],longMonths:['January','February','March','April','May','June','July','August','September','October','November','December'],shortDays:['Sun','Mon','Tue','Wed','Thu','Fri','Sat'],longDays:['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],d:function(){return(this.getDate()<10?'0':'')+this.getDate();},D:function(){return Date.replaceChars.shortDays[this.getDay()];},j:function(){return this.getDate();},l:function(){return Date.replaceChars.longDays[this.getDay()];},N:function(){return this.getDay()+1;},S:function(){return(this.getDate()%10==1&&this.getDate()!=11?'st':(this.getDate()%10==2&&this.getDate()!=12?'nd':(this.getDate()%10==3&&this.getDate()!=13?'rd':'th')));},w:function(){return this.getDay();},z:function(){return"Not Yet Supported";},W:function(){return"Not Yet Supported";},F:function(){return Date.replaceChars.longMonths[this.getMonth()];},m:function(){return(this.getMonth()<9?'0':'')+(this.getMonth()+1);},M:function(){return Date.replaceChars.shortMonths[this.getMonth()];},n:function(){return this.getMonth()+1;},t:function(){return"Not Yet Supported";},L:function(){return(((this.getFullYear()%4==0)&&(this.getFullYear()%100!=0))||(this.getFullYear()%400==0))?'1':'0';},o:function(){return"Not Supported";},Y:function(){return this.getFullYear();},y:function(){return(''+this.getFullYear()).substr(2);},a:function(){return this.getHours()<12?'am':'pm';},A:function(){return this.getHours()<12?'AM':'PM';},B:function(){return"Not Yet Supported";},g:function(){return this.getHours()%12||12;},G:function(){return this.getHours();},h:function(){return((this.getHours()%12||12)<10?'0':'')+(this.getHours()%12||12);},H:function(){return(this.getHours()<10?'0':'')+this.getHours();},i:function(){return(this.getMinutes()<10?'0':'')+this.getMinutes();},s:function(){return(this.getSeconds()<10?'0':'')+this.getSeconds();},e:function(){return"Not Yet Supported";},I:function(){return"Not Supported";},O:function(){return(-this.getTimezoneOffset()<0?'-':'+')+(Math.abs(this.getTimezoneOffset()/60)<10?'0':'')+(Math.abs(this.getTimezoneOffset()/60))+'00';},P:function(){return(-this.getTimezoneOffset()<0?'-':'+')+(Math.abs(this.getTimezoneOffset()/60)<10?'0':'')+(Math.abs(this.getTimezoneOffset()/60))+':'+(Math.abs(this.getTimezoneOffset()%60)<10?'0':'')+(Math.abs(this.getTimezoneOffset()%60));},T:function(){var m=this.getMonth();this.setMonth(0);var result=this.toTimeString().replace(/^.+ \(?([^\)]+)\)?$/,'$1');this.setMonth(m);return result;},Z:function(){return-this.getTimezoneOffset()*60;},c:function(){return this.format("Y-m-d")+"T"+this.format("H:i:sP");},r:function(){return this.toString();},U:function(){return this.getTime()/1000;}};

$(document).ready(function () {
    var shouldLoadCPU = true;
    $('#report-list-nav li a').click(function () {
        if (shouldLoadCPU) {
            shouldLoadCPU = false;
            $('#cpu_correlation').load(SocReport.base + 'cpu' + SocReport.path,       function () { 
                socSortCorrelation('#cpu_correlation');
            });
            $('#addon_correlation').load(SocReport.base + 'addon' + SocReport.path,   function () {
                socSortCorrelation('#addon_correlation'); 
            });
            $('#module_correlation').load(SocReport.base + 'module' + SocReport.path, function () { 
                socSortCorrelation('#module_correlation');
            });
        }
    });
    $('button.load-version-data').click(function () {
        var t = $(this).attr('name');
        $('#' + t + '-panel').html(SocReport.loading)
                                     .load(SocReport.base + t + SocReport.path);
    });

    $('#reportsList .hang-pair-btn').click(function() {
        var tr = $(this).parent().parent().parent();

        var url = $('input.ajax_endpoint', tr).val();

        $('.hang-pair', tr).html("<img src='../img/ajax-loader16x16.gif' alt='Loading data' />");
        $.getJSON(url, function(data) {
            if (data.length > 0 ) {
	        for (var i=0; data.length; i++) {
	            var hangType = data[i].processType && data[i].processType == 'plugin' ? 'Plugin' : 'Browser';
	            $('.hang-pair', tr).html(hangType + " Hang:<br /><a href='" + data[i].uuid + "'>" + data[i].display_date_processed  + "</a>");
                    $('img', tr).unbind('click');
	            break;
                }
            } else {
                $('.hang-pair', tr).html("Unable to locate other Hang Part.");
            }    
        });
        return false;
    });

    $('#buildid-table').tablesorter(); 
    
    $.tablesorter.addParser({  
        id: "hexToInt",  
        is: function(s) {  
            return false;  
        },  
        format: function(s) {  
            return parseInt(s, 16);
        },  
        type: "digit"  
    });
    
    $('#reportsList').tablesorter({ 
        textExtraction: "complex",
        headers: { 
            7: { sorter: "hexToInt" },  // Address
            9: { sorter: "digit" }      // Uptime
        }, 
        sortList : [[10,1]]
    });
    
    $('#report-list-nav').tabs({selected: 2}).show();
});
