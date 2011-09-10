/*jslint browser:true, regexp:false, plusplus:false */
/*global window, $, socSortCorrelation, SocReport */
$(document).ready(function () {
    $("#signatureList").tablesorter();

    $('td a.signature').girdle({previewClass: 'signature-preview', fullviewClass: 'signature-popup'});

});
