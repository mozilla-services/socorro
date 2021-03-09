/* global BugLinks */

$(document).ready(function () {
  /* Idempotent function to display the TelemetryEnvironment with
   * jQuery JSONView */
  var displayTelemetryEnvironment = (function () {
    var once = false;
    return function inner() {
      if (once) {
        // idempotent function
        return;
      }
      once = true;
      var container = $('#telemetryenvironment-json');
      if (container.length) {
        var jsonData = container.data('telemetryenvironment');
        try {
          $('#telemetryenvironment-json').JSONView(jsonData);
        } catch (ex) {
          console.warn('The data in the #telemetryenvironment-json dataset is not valid JSON');
          container.append($('<p>Error when parsing JSON. Showing raw value:</p>'));
          container.append(document.createTextNode(jsonData));
        }
      }
    };
  })();

  /* Idempotent function to display the json dump with jQuery JSONView */
  var displayMinidumpStackwalkJson = (function () {
    var once = false;
    return function inner() {
      if (once) {
        // idempotent function
        return;
      }
      once = true;
      var container = $('#minidump-stackwalk-json');
      if (container.length) {
        var jsonData = container.data('minidumpstackwalk');
        try {
          $('#minidump-stackwalk-json').JSONView(jsonData);
        } catch (ex) {
          console.warn('The data in the #minidump-stackwalk-json dataset is not valid JSON');
          container.append($('<p>Error when parsing JSON. Showing raw value:</p>'));
          container.append(document.createTextNode(jsonData));
        }
      }
    };
  })();

  // If the page is loaded with a location.hash like '#tab-...'
  // then find out which index that is so when we set up $.tabs()
  // we can set the right active one.
  var activeTab = 0;
  if (location.hash.search(/#tab-/) > -1) {
    var tabId = location.hash.split('#tab-')[1];
    var tab = $('#' + tabId);
    // only bother if this tab exists
    if (tab.length) {
      if (tabId === 'telemetryenvironment') {
        displayTelemetryEnvironment();
      } else if (tabId === 'rawdump') {
        displayMinidumpStackwalkJson();
      }
      $('.ui-tabs li a').each(function (i, tab) {
        if (tab.href.search('#' + tabId) > -1) {
          activeTab = i;
        }
      });
    }
  }
  $('#report-index').tabs({
    active: activeTab,
    activate: function (event, ui) {
      var tabId = ui.newPanel.attr('id');
      if (tabId === 'telemetryenvironment') {
        displayTelemetryEnvironment();
      } else if (tabId === 'rawdump') {
        displayMinidumpStackwalkJson();
      }
      document.location.hash = 'tab-' + tabId;
    },
  });

  $('a[href="#allthreads"]').on('click', function () {
    var element = $(this);
    $('#allthreads').toggle(400);
    if (element.text() === element.data('show')) {
      element.text(element.data('hide'));
      return true;
    } else {
      element.text(element.data('show'));
      location.hash = 'frames';
      return false;
    }
  });

  var tbls = $('#frames').find('table');
  var addExpand = function (sigColumn) {
    $(sigColumn).append(' <a class="expand" href="#">[Expand]</a>');
    $('.expand').click(function (event) {
      event.preventDefault();
      // swap cell title into cell text for each cell in this column
      $('td:nth-child(3)', $(this).parents('tbody')).each(function () {
        $(this).text($(this).attr('title')).removeAttr('title');
      });
      $(this).remove();
    });
  };

  // collect all tables inside the div with id frames
  tbls.each(function () {
    var isExpandAdded = false;
    var cells = $(this).find('tbody tr td:nth-child(3)');

    // Loop through each 3rd cell of each row in the current table and if
    // any cell's title atribute is not of the same length as the text
    // content, we need to add the expand link to the table.
    // There is a second check to ensure that the expand link has not been added already.
    // This avoids adding multiple calls to addExpand which will add multiple links to the
    // same header.
    cells.each(function () {
      if ($(this).attr('title').length !== $(this).text().length && !isExpandAdded) {
        addExpand($(this).parents('tbody').find('th.signature-column'));
        isExpandAdded = true;
      }
    });
  });

  $('#modules-list').tablesorter({ sortList: [[1, 0]], headers: { 1: { sorter: 'digit' } } });

  // Decide whether to show the Correlations tab if this product,
  // channel and signature has correlations.
  var container = $('#mainbody');
  var signature = container.data('signature');
  var channel = container.data('channel');
  var product = container.data('product');

  window.correlations.getCorrelations(signature, channel, product).then(function (results) {
    $('#correlation h3').text('Correlations for ' + product + ' ' + channel[0].toUpperCase() + channel.substr(1));

    if (!Array.isArray(results)) {
      $('#correlation pre').text('No correlation data available.');
      return;
    }

    var content = results.join('\n');

    $('#correlation pre').empty().text(content);
  });

  // Enhance bug links.
  BugLinks.enhance();
});
