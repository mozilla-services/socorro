/* global Promise, jsSHA */

window.correlations = (function () {
  /**
   * Handle any errors by logging them.
   */
  function handleError(error) {
    console.error(error.message);
  }

  var correlationData = {};

  function getDataURL(product) {
    if (product === 'Firefox') {
      return 'https://analysis-output.telemetry.mozilla.org/top-signatures-correlations/data/';
    } else {
      return null;
    }
  }

  function loadChannelsData(product) {
    return Promise.resolve().then(function () {
      if (correlationData[product]) {
        return correlationData[product];
      }

      var dataURL = getDataURL(product);
      if (!dataURL) {
        console.warn('Correlation results unavailable for the "' + product + '" product.');
        return null;
      }

      return fetch(dataURL + 'all.json.gz')
        .then(function (response) {
          return response.json();
        })
        .then(function (totals) {
          correlationData[product] = {
            date: totals.date,
          };

          var channels = $('#mainbody').data('channels');
          if (!channels) {
            channels = [$('#mainbody').data('channel')];
          }
          if (!channels || !channels.length) {
            throw new Error('No channel or channels dataset attribute set');
          }

          channels.forEach(function (ch) {
            correlationData[product][ch] = {
              total: totals[ch],
              signatures: {},
            };
          });
          return correlationData[product];
        });
    });
  }

  function loadCorrelationData(signature, channel, product) {
    return loadChannelsData(product)
      .then(function (channelsData) {
        if (!channelsData || !channelsData[channel] || signature in channelsData[channel].signatures) {
          return;
        }

        var shaObj = new jsSHA('SHA-1', 'TEXT');
        shaObj.update(signature);
        var sha1signature = shaObj.getHash('HEX');

        return fetch(getDataURL(product) + channel + '/' + sha1signature + '.json.gz')
          .then(function (response) {
            return response.json();
          })
          .then(function (data) {
            correlationData[product][channel].signatures[signature] = data;
          });
      })
      .catch(handleError)
      .then(function () {
        return correlationData;
      });
  }

  function itemToLabel(item) {
    return Object.getOwnPropertyNames(item)
      .map(function (key) {
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

    if (result.length < 5) {
      return '0' + result;
    }

    return result;
  }

  function confidenceInterval(count1, total1, count2, total2) {
    var prop1 = count1 / total1;
    var prop2 = count2 / total2;
    var diff = prop1 - prop2;

    // Wald 95% confidence interval for the difference between the proportions.
    var standard_error = Math.sqrt((prop1 * (1 - prop1)) / total1 + (prop2 * (1 - prop2)) / total2);
    var ci = [diff - 1.96 * standard_error, diff + 1.96 * standard_error];

    // Yates continuity correction for the confidence interval.
    var correction = 0.5 * (1.0 / total1 + 1.0 / total2);

    return [ci[0] - correction, ci[1] + correction];
  }

  function sortCorrelationData(correlationData, total_reference, total_group) {
    return correlationData.sort(function (a, b) {
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

      // Then, sort by percentage difference between signature and
      // overall (using the lower endpoint of the confidence interval
      // of the difference).
      var ciA = null;
      if (a.prior) {
        // If one of the two elements has a prior that alters a rule's
        // distribution significantly, sort by the percentage of the rule
        // given the prior.
        ciA = confidenceInterval(
          a.prior.count_group,
          a.prior.total_group,
          a.prior.count_reference,
          a.prior.total_reference
        );
      } else {
        ciA = confidenceInterval(a.count_group, total_group, a.count_reference, total_reference);
      }

      var ciB = null;
      if (b.prior) {
        ciB = confidenceInterval(
          b.prior.count_group,
          b.prior.total_group,
          b.prior.count_reference,
          b.prior.total_reference
        );
      } else {
        ciB = confidenceInterval(b.count_group, total_group, b.count_reference, total_reference);
      }

      return Math.min(Math.abs(ciB[0]), Math.abs(ciB[1])) - Math.min(Math.abs(ciA[0]), Math.abs(ciA[1]));
    });
  }

  function getResults(signature, channel, product) {
    return loadCorrelationData(signature, channel, product)
      .then(function (data) {
        if (!data[product]) {
          return 'No correlation data was generated for the "' + product + '" product.';
        }

        if (!data[product][channel]) {
          return (
            'No correlation data was generated for the "' + channel + '" channel and the "' + product + '" product.'
          );
        }

        var signatureData = data[product][channel].signatures[signature];

        if (!signatureData || !signatureData.results) {
          return [
            'No correlation data was generated for the signature "' +
              signature +
              '" on the "' +
              channel +
              '" channel, for the "' +
              product +
              '" product.',
            'There may be correlation data available for other channels; please select another using the controls above.',
          ];
        }

        var correlationData = signatureData.results;
        if (correlationData.length === 0) {
          return (
            'No correlations found for the signature "' +
            signature +
            '" on the "' +
            channel +
            '" channel, for the "' +
            product +
            '" product.'
          );
        }

        var total_reference = data[product][channel].total;
        var total_group = signatureData.total;

        var results = sortCorrelationData(correlationData, total_reference, total_group).map(function (line) {
          var percentGroup = toPercentage(line.count_group / total_group);
          var percentRef = toPercentage(line.count_reference / total_reference);

          var result = '(' + percentGroup + '% in signature vs ' + percentRef + '% overall) ' + itemToLabel(line.item);

          // If the rule has a prior that alters its distribution significantly, print it after the rule.
          if (line.prior && line.prior.total_group && line.prior.total_reference) {
            var percentGroupGivenPrior = toPercentage(line.prior.count_group / line.prior.total_group);
            var percentRefGivenPrior = toPercentage(line.prior.count_reference / line.prior.total_reference);
            result +=
              ' [' +
              percentGroupGivenPrior +
              '% vs ' +
              percentRefGivenPrior +
              '% if ' +
              itemToLabel(line.prior.item) +
              ']';
          }

          return result;
        });

        if (signatureData.top_words) {
          results.push('');
          results.push('Top words: ' + signatureData.top_words.join(', '));
        }

        return results;
      })
      .catch(handleError);
  }

  return {
    getCorrelations: getResults,
  };
})();
