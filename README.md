Shibboleth IdP QA
=====


This tool loads a list of IdPs from a json file (or specific html parsing for terena) and uses
a specific SP (Service Provider) url to loop through them and get redirected to the login screen.

There is a list of known issues which can happen during this process and this tool tries to 
find problematic IdPs and lists them.

Run it from a command line using the `test` parameter:

```
python aai-idps.py test
```

Or use it to display the results in html (or set of IdPs if no results ara available):

```
python aai-idps.py
```

You can also use it as a [nagios](http://www.nagios.org/) probe by specifying

```
python aai-idps.py test nagios
```

If you have an academic account, try logging to https://lindat.mff.cuni.cz/secure/aai-idps-clarin .
   
Notes
-----------------

This tool runs in parallel so be careful not to overload the servers!

National Federations (NF) admins can be touchy if you scan a lot of IdPs regularly.

Run this tool (regularly) *only* on SPs which have been informed in advance (and agreed!).