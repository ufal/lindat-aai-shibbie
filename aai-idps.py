#!/usr/bin/env python
# coding=utf-8
#
# by LINDAT/CLARIN dev team (http://lindat.cz, jm)
# @2013

"""
    You should have shm enabled if run in parallel:
    Add:
        none /dev/shm tmpfs rw,nosuid,nodev,noexec 0 0
    to /etc/fstab and run
        sudo mount /dev/shm
"""

import os
import sys
#
#
this_dir = os.path.dirname(os.path.abspath(__file__))

settings = {
    "json_url": "https://lindat.mff.cuni.cz/repository/xmlui/discojuice/feeds?callback=dj_md_1",
    "SP_URL": "https://lindat.mff.cuni.cz/Shibboleth.sso/Login?SAMLDS=1&target=https://lindat.mff.cuni.cz/repository/xmlui/shibboleth-login&entityID=",

    "file_error_json": os.path.join(this_dir, "aai-idps-data", "aai-idp-errors-lindat.json"),
    "parallel_max": 12,
    "timeout": 55.0,
    "ignore_error_countries": ( "BR", ),
    "wait": 0.5,
    "idps": [ 
        "/var/www/secure/aai-idps-data/edugain.xml",
        "/var/www/secure/aai-idps-data/spf.xml",
     ],
}


sys.path.insert(0, this_dir)
import aai_idps_core
aai_idps_core.settings.update( settings )

if "test" in sys.argv:
    aai_idps_core.test_idps( )
else:
    aai_idps_core.make_html( )
