(function ($) {
  $.tablesorter.addParser({
    id: 'hexdigit',
    is: function () {
      return false;
    },
    format: function (str) {
      var newstr;

      if (str === null || str === '') {
        return 0;
      }

      // if it starts with 0x, peel that off and if all digits, convert the
      // rest from base 16 to base 10
      if (str.substring(0, 2) === '0x') {
        newstr = str.substring(2);
        if (!newstr.match(/^[0-9A-Fa-f]+$/)) {
          return 0;
        }
        newstr = parseInt(newstr, 16);
        return newstr;
      }

      // if it's all digits, convert to int
      if (!str.match(/^[0-9]+$/)) {
        return 0;
      }
      newstr = parseInt(str);
      return newstr;
    },
    // the parser converts to an int, so use numeric sort after that
    type: 'numeric',
  });
})(jQuery);
