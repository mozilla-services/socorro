/*
    This is loaded on any page that renders HTML errors for 500, 4xx errors.
    Remember, there's no jQuery available in this context.
 */

// If the page as a bugzilla link, because we can't rely on the server
// to figure out the current full URL, we have to use JavaScript to
// append the current full URL to the bug_file_loc parameter link.
window.onload = function () {
  var link = document.querySelector('a.bugzilla-link');
  if (link) {
    link.href += '&bug_file_loc=' + encodeURIComponent(document.location.href);
  }
};
