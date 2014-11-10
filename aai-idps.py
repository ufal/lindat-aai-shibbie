#!/usr/bin/env python
 
# -*- coding: UTF-8 -*-
"""
    Had to add
    none /dev/shm tmpfs rw,nosuid,nodev,noexec 0 0 to /etc/fstab
    and run
    sudo mount /dev/shm
    in ubuntu

"""

import os
import sys
#
#
this_dir = os.path.dirname(os.path.abspath(__file__))

settings = {
    "json_url": "https://lindat.mff.cuni.cz/repository/xmlui/discojuice/feeds?callback=dj_md_1",
    "SP_URL": "https://lindat.mff.cuni.cz/Shibboleth.sso/Login?SAMLDS=1&target=https://lindat.mff.cuni.cz/repository/xmlui/shibboleth-login&entityID=",

    "file_error_json": os.path.join(this_dir, "aai-idps-data", "aai-idp-errors.json"),
    "ignore_error_countries": ( "BR", ),
}


sys.path.insert(0, this_dir)
import aai_idps_core
aai_idps_core.settings.update( settings )

if "test" in sys.argv:
    aai_idps_core.test_idps( )
else:
    aai_idps_core.make_html( )

