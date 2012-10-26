/*jslint browser:true, regexp:false, plusplus:false */
/*global window, $, socSortCorrelation, SocReport */
$(document).ready(function () {
    $("#signatureList").tablesorter({
        headers: {
            0: { sorter: 'text'  },
            1: { sorter: 'text'  },
            2: { sorter: 'digit' },
            3: { sorter: 'text'  },
            4: { sorter: 'date'  }
        }
    });

    $('td a.signature').girdle({previewClass: 'signature-preview', fullviewClass: 'signature-popup'});

});
