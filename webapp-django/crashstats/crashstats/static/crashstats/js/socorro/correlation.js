/*jslint browser:true, regexp:false */
/*global window, $*/

window.correlations = (function(){
    function hex(buffer) {
        var hexCodes = [];
        var view = new DataView(buffer);

        for (var i = 0; i < view.byteLength; i += 4) {
            // Using getUint32 reduces the number of iterations needed (we process 4 bytes each time).
            var value = view.getUint32(i);
            // toString(16) will give the hex representation of the number without padding.
            var stringValue = value.toString(16);
            // We use concatenation and slice for padding.
            var padding = '00000000';
            var paddedValue = (padding + stringValue).slice(-padding.length);
            hexCodes.push(paddedValue);
        }

        // Join all the hex strings into one
        return hexCodes.join('');
    }

    function sha1(str) {
        return crypto.subtle.digest('SHA-1', new TextEncoder('utf-8').encode(str))
        .then(function(hash) {
            return hex(hash)
        });
    }

    var correlationData = {};

    function getDataURL(product) {
        if (product === 'Firefox') {
            return 'https://analysis-output.telemetry.mozilla.org/top-signatures-correlations/data/';
        } else if (product === 'FennecAndroid') {
            return 'https://analysis-output.telemetry.mozilla.org/top-fennec-signatures-correlations/data/';
        } else {
            throw new Error('Unknown product: ' + product);
        }
    }

    function loadChannelsData(product) {
        if (correlationData[product]) {
            return Promise.resolve();
        }

        return fetch(getDataURL(product) + 'all.json.gz')
        .then(function(response) {
            return response.json();
        })
        .then(function(totals) {
            correlationData[product] = {
                'date': totals['date'],
            };

            ['release', 'beta', 'aurora', 'nightly'].forEach(function(ch) {
                correlationData[product][ch] = {
                    'total': totals[ch],
                    'signatures': {},
                };
            });
        });
    }

    function loadCorrelationData(signature, channel, product) {
        return loadChannelsData(product)
        .then(function() {
            if (signature in correlationData[product][channel]['signatures']) {
                return;
            }

            return sha1(signature)
            .then(function(sha1signature) {
                return fetch(getDataURL(product) + channel + '/' + sha1signature + '.json.gz');
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                correlationData[product][channel]['signatures'][signature] = data;
            });
        })
        .catch(console.log.bind(console))
        .then(function() {
            return correlationData;
        });
    }

    function itemToLabel(item) {
        return Object.getOwnPropertyNames(item)
        .map(function(key) {
            return key + ' = ' + item[key];
        })
        .join(' ∧ ');
    }

    // Convert the number to a user-readable percentage with four digits.
    // We use the same number of digits for any number (e.g. 100.0%, 03.45%) so
    // that the results are aligned, also when copied and pasted.
    function toPercentage(num) {
        var result = (num * 100).toFixed(2);

        if (result === '100.00') {
          return '100.0';
        }

        if (num < 0.1) {
          return '0' + result;
        }

        return result;
    }

  function confidenceInterval(count1, total1, count2, total2) {
    var prop1 = count1 / total1;
    var prop2 = count2 / total2;
    var diff = prop1 - prop2;

    // Wald 95% confidence interval for the difference between the proportions.
    var standard_error = Math.sqrt(prop1 * (1 - prop1) / total1 + prop2 * (1 - prop2) / total2);
    var ci = [diff - 1.96 * standard_error, diff + 1.96 * standard_error];

    // Yates continuity correction for the confidence interval.
    var correction = 0.5 * (1.0 / total1 + 1.0 / total2);

    return [ci[0] - correction, ci[1] + correction];
  }

  function sortCorrelationData(correlationData, total_reference, total_group) {
    return correlationData
    .sort(function(a, b) {
      // Sort by the number of attributes first (results with a smaller number of attributes
      // are easier to read and are often the most interesting ones).
      var rule_a_len = Object.keys(a.item).length;
      var rule_b_len = Object.keys(b.item).length;

      if (rule_a_len < rule_b_len) {
        return -1;
      }

      if (rule_a_len > rule_b_len) {
        return 1;
      }

      // Then, sort by percentage difference between signature and overall (using the lower endpoint
      // of the confidence interval of the difference).
      var ciA = confidenceInterval(a.count_group, total_group, a.count_reference, total_reference);
      var ciB = confidenceInterval(b.count_group, total_group, b.count_reference, total_reference);

      return Math.min(Math.abs(ciB[0]), Math.abs(ciB[1])) - Math.min(Math.abs(ciA[0]), Math.abs(ciA[1]));
    });
  }

  function text(textElem, signature, channel, product) {
    loadCorrelationData(signature, channel, product)
    .then(function(data) {
      textElem.text('');

      if (!(product in data)) {
        textElem.text('No correlation data was generated for the \'' + product + '\' product.');
        return;
      }

      if (!(signature in data[product][channel]['signatures']) || !data[product][channel]['signatures'][signature]['results']) {
        textElem.text('No correlation data was generated for the signature "' + signature + '" on the ' + channel + ' channel, for the \'' + product + '\' product.');
        return;
      }

      var correlationData = data[product][channel]['signatures'][signature]['results'];

      var total_reference = data[product][channel].total;
      var total_group = data[product][channel]['signatures'][signature].total;

      textElem.text(sortCorrelationData(correlationData, total_reference, total_group)
      .reduce(function(prev, cur) {
        return prev + '(' + toPercentage(cur.count_group / total_group) + '% in signature vs ' + toPercentage(cur.count_reference / total_reference) + '% overall) ' + itemToLabel(cur.item) + '\n';
      }, ''));
    })
    .catch(console.log.bind(console));
  }

  return {
      loadCorrelationData: loadCorrelationData,
      writeResults: text,
  };
})();
