$(document).ready(function () {
  var getReportsURLs = function () {
    var urls = {};
    $('#report_select option').each(function (i, elem) {
      urls[elem.value] = {
        product: elem.dataset.urlProduct,
        version: elem.dataset.urlVersion,
      };
    });

    return urls;
  };

  var getURL = function () {
    var report = $('#report_select').val();
    var product = $('#products_select').val();
    var version = $('#product_version_select').val();

    var url;
    var reportsURLs = getReportsURLs();

    if (version === 'Current Versions') {
      // That means there is no version set, so we only set the product.
      url = reportsURLs[report].product.replace('__PRODUCT__', product);
    } else {
      // There is both a product and a version.
      url = reportsURLs[report].version.replace('__PRODUCT__', product).replace('__VERSION__', version);
    }

    return url;
  };

  $('.version-nav').on('change', 'select', function () {
    window.location = getURL();
  });

  $('.user-info-button').on('click', function () {
    $(this).siblings('.user-info-menu').toggle();
  });

  $(document).on('click', function (event) {
    var userInfo = $('.user-info');
    if (!userInfo.is(event.target) && !userInfo.has(event.target).length) {
      $('.user-info-menu').hide();
    }
  });
});
