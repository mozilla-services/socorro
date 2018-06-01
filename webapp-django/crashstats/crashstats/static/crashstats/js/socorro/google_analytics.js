/* global ga */

window.ga =
  window.ga ||
  function() {
    (ga.q = ga.q || []).push(arguments);
  };
ga.l = +new Date();
ga('create', document.documentElement.dataset.googleAnalyticsId, 'auto');
ga('send', 'pageview');
