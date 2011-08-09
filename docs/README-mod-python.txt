mod_python
--------------------------------------

You will need to configure mod_python to use the collector:

From httpd.conf:
 
  Alias /breakpad/ "/mywebdir/"
  <Directory "/mywebdir/">
      AddHandler mod_python .py
      PythonHandler collector
  </Directory>

From .htaccess:

  AddHandler mod_python .py
  PythonHandler collector
