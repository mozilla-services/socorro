$(function () {
  var Checker = (function () {
    var intervalTime = 5 * 1000;
    var checkInterval;

    return {
      startChecking: function (crashID) {
        checkInterval = setInterval(function () {
          $.get('/api/ProcessedCrash/', { crash_id: crashID })
            .then(function () {
              clearInterval(checkInterval);
              // If it exists, we can reload the page we're on.
              $('.pending .searching').hide();
              $('.pending .found').fadeIn(300, function () {
                document.location.reload();
              });
            })
            .fail(function (err) {
              // Perfectly expected.
              // We kind of expect the processed crash to not
              // exist for a while. Once it's been processed,
              // it should exist and yield a 200 error.
              if (err.status !== 404) {
                // But it's not a 404 error it's something unexpected.
                clearInterval(checkInterval);
                throw new Error(err);
              }
            });
        }, intervalTime);
      },
    };
  })();

  var pathname = document.location.pathname.split('/');
  var crashID = pathname[pathname.length - 1];
  Checker.startChecking(crashID);
});
