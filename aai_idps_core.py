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
import json
import codecs
import urllib
import time
import re
import mechanize
import cgi
import cookielib
import socket
from datetime import datetime
import logging
_logger = None
#
#

settings = {
    #
    "common_header": "/opt/lindat-debug-services/header.htm",
    "common_footer": "/opt/lindat-common-b3/footer.htm",
    #
    "json_url": "CHANGE THIS",
    #
    "SP_URL": "CHANGE THIS",

    "external_tests": {
        "weblicht": {
            "SP_URL": "https://weblicht.sfs.uni-tuebingen.de/Shibboleth.sso/Login?SAMLDS=1&target=https://weblicht.sfs.uni-tuebingen.de/WebLicht-4/&entityID=",
            "json_url": "http://catalog.clarin.eu/mw1/sds/proxy",
        },
        "terena": {
            "SP_URL": "https://login.terena.org/wayf/module.php/discopower/disco.php",
            "json_url": "https://login.terena.org/wayf/module.php/core/authenticate.php?as=default-sp",
        },
    },
    #
    "file_error_json": "/var/www/secure/aai-idp-errors.json",
    #
    "parallel_max": 10,
    # 
    "error_responses": (
        "message did not meet security requirements",
        "could not find",
        "unhandledexc",
        "error processing request",
        "metadata not found",
    ),
    #
    "timeout": 35.0,

    #
    "show_errors": True,

    #
    "ignore_error_countries": [],

    #
    "log_stdout": True,

    # 10-minutes
    "execution_maxtime": 60*30,

    # idps list for technical contact
    "idps": [],

    "wait": 0.2,
}


#
#
def create_html(idps_str):
    """
        Main html page
    """
    common_header = u""
    if os.path.exists( settings["common_header"] ):
        with codecs.open(settings["common_header"], encoding="utf-8", mode="rb") as fin:
            common_header = fin.read()

    common_footer = u""
    if os.path.exists( settings["common_footer"] ):
        with codecs.open(settings["common_footer"], encoding="utf-8", mode="rb") as fin:
            common_footer = fin.read()

    return (u"""<html>
    <head>
        <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">
        <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap-theme.min.css">
        <link href="/common-theme-b3/public/css/lindat.css" rel="stylesheet">
        <script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
    </head>
    <body>
        %s
        <div class="well">
        %s
        </div>
        %s
    </body>
</html>""" % (common_header, idps_str, common_footer)).encode( "utf-8" )


def exc2html(e):
    import traceback
    e_str = traceback.format_exc()
    return u"""<div class="alert alert-danger">%s</div>""" % e_str.replace( "\n", "<br />" )


def log_stdout(msg):
    if settings["log_stdout"] is True:
        sys.stdout.write(msg)
        sys.stdout.flush()

#
#
#

def add_more_information(idps_arr):
    import xml.etree.ElementTree as ET
    idps = {}
    for f in settings["idps"]:
        if not os.path.exists(f):
            continue
        tree = ET.parse(f)
        root = tree.getroot() 
        for idp in root.findall("{urn:oasis:names:tc:SAML:2.0:metadata}EntityDescriptor"):
            eid = idp.attrib.get("entityID")
            if eid not in idps:
                idps[eid] = { "technical" : "<<unknown>>", "files": [] }
            idps[eid]["files"].append( f )
            for child in idp:
                if child.tag.endswith("ContactPerson"):
                    for cc in child:
                        if cc.tag.endswith("EmailAddress"):
                            idps[eid][child.attrib.get("contactType")] = cc.text
                            break
    for idp in idps_arr:
        eid = idp["entityID"]
        idp.update( idps.get( eid, {} ) )

    return idps_arr

def remove_duplicate_idps(idps_arr):
    done = set()
    new_arr = []
    for a in idps_arr:
        eid = a["entityID"]
        if eid in done:
            continue
        done.add(eid)
        new_arr.append( a )
    return new_arr


def login_url(entity_id):
    return settings["SP_URL"] + entity_id


def nav_from_idp(idp_json):
    return idp_json.get( "country", "???" )


def idp2html(idp_json, make_nav_link, pos):
    eid = idp_json["entityID"]
    title = idp_json.get( "title", eid )
    country = idp_json.get( "country", "unknown" )
    # hack for terena where we do not know EID
    login_url_str = idp_json.get("login_url", login_url( eid ))
    nav_link = "" if make_nav_link is False else u""" id="id-%s" """ % nav_from_idp( idp_json )
    return u"""<li class="list-group-item"{nav_link}>
    <a href="{login_url_str}" target="_blank">#{pos}.
    <span class="badge" style="margin-right:20px">{country}</span>
    {title}
    </a>
</li>""".format( **locals( ) )


def settings2html(d):
    return u"""<h3>Settings</h3>
<div><span class="badge">idp json:</span> <pre>%s</pre></div>
<div><Span class="badge">SP url:</span> <pre>%s</pre></div>
</div>""" % (d["json_url"], d["SP_URL"])


def json2nav(json_arr):
    s = set( )
    for i in json_arr:
        s.add( nav_from_idp( i ) )
    html = settings2html( settings )
    html += u"""<h1>List of all IdPs</h1><ul class="nav nav-pills" style="font-size:80%">"""
    for c in sorted( s ):
        ahref = "#id-" + c
        html += u"""<li><a href="%s">%s</a></li>""" % (ahref, c)
    html += "</ul>"
    return html


def idp_from_arr(eid, arr):
    for a in arr:
        if a["entityID"] == eid:
            return a
    return None


def errors2html(json_arr):
    errors = json.load( open( settings["file_error_json"], mode="rb" ) )
    errors_html = u"""
    <h2>Problematic IdPs checked at %s</h2>
    %s
    <ol class="list-panel">""" % (
        errors["checked"], settings2html( errors["settings"] ))
    for eid, msg in errors["errors"]:
        msg = cgi.escape( msg )
        idp = idp_from_arr( eid, json_arr )
        if idp is not None:
            country = idp.get( "country", "???" )
            if country in settings["ignore_error_countries"]:
                continue
            content = u"""
            <span class="badge">%s</span> <strong><a href="%s" class="btn btn-danger btn-xs">%s</a></strong>
            <br>
            %s""" % (country, login_url( eid ), idp.get( "title", eid ), msg)
        else:
            content = u"""<span class="btn btn-danger btn-xs">%s</span> - %s""" % (eid, msg)
        if "technical" in idp:
            content += u"""<br><div class="label label-info">%s</div>""" % (idp["technical"],)
        if "files" in idp:
            for f in idp["files"]:
                content += u"""<span class="label label-default">%s</spa>""" % os.path.basename(
                    f).replace(".xml", "")

        errors_html += u"""<li class="">%s</li>""" % (content)
    errors_html += u"</ol></div>"
    return errors_html


def json2html(json_arr):
    # add errors if found
    html = ""
    if settings["show_errors"] and os.path.exists( settings["file_error_json"] ):
        html += errors2html( json_arr )
    #
    json_arr.sort( key=lambda x: x.get( "country", "??" ) )
    html += json2nav( json_arr ) + u"""<ul class="list-group">\n"""
    last_nav = ""
    for i, idp in enumerate(json_arr):
        make_link = last_nav != nav_from_idp( idp )
        html += idp2html( idp, make_link, i + 1 )
        last_nav = nav_from_idp( idp )
    html += "\n</ul>"
    return html


#
#
#

def get_json(url):
    """
        Get list of IdPs with special handling of discojuice.
    """
    if url is None:
        return {}
    f = urllib.FancyURLopener().open( url )
    json_str = f.read()
    # discojuice to json
    if json_str.find( "(" ) < 15:
        json_str = json_str[json_str.find( "(" ) + 1: json_str.rfind( ")" )]
    return json.loads( json_str )


#
# make html page
#

# noinspection PyBroadException,PyUnresolvedReferences
def utf_friendly():
    reload( sys )
    try:
        sys.setdefaultencoding( 'utf-8' )
    except:
        pass
    sys.stdout = codecs.getwriter( 'utf-8' )( sys.stdout )


def handle_params():
    # any params?
    args = cgi.FieldStorage( )
    if "json_url" in args:
        settings["json_url"] = urllib.unquote( args["json_url"].value )
        settings["show_errors"] = False
    if "SP_URL" in args:
        settings["SP_URL"] = urllib.unquote( args["SP_URL"].value )
        settings["show_errors"] = False


def make_html():
    import cgitb
    utf_friendly()
    cgitb.enable( )
    print "Content-Type: text/html;charset=utf-8"
    print
    try:
        handle_params()
        json_obj = get_json( settings["json_url"] )
        json_obj = remove_duplicate_idps(json_obj)
        json_obj = add_more_information(json_obj)
        print create_html( json2html( json_obj ) )
    except Exception, e:
        print create_html( exc2html( e ) )


#
# make tests
#

# noinspection PyProtectedMember,PyUnresolvedReferences
def get_browser():
    """ Test browser e.g., through mechanize. """
    br = mechanize.Browser()
    br.set_handle_robots( False )
    br.set_handle_refresh( mechanize._http.HTTPRefreshProcessor( ), max_time=1 )
    br.set_handle_equiv( True )
    br.set_handle_redirect( True )
    br.set_handle_referer( True )
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar( cj )
    br.addheaders = [('User-agent',
        #'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1'
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36"
        )]
    return br


def test_idp((eid, url)):
    """
        Test idp through new / supplied browser instance.
    """
    exc = None
    absolute_url = url
    try:
        br = get_browser() if not isinstance(eid, mechanize.Browser) else eid
        if isinstance(url, mechanize.Link):
            f = br.follow_link(url)
            absolute_url = url.absolute_url
        else:
            f = br.open( url, timeout=settings["timeout"] )
        resp = f.read( ).lower( )

        # all went ok?
        if hasattr( f, "code" ):
            if f.code not in (401, 200):
                exc = u"http response code %d!" % f.code
        else:
            exc = br.error

        if exc is None:
            for k in settings["error_responses"]:
                if k in resp:
                    exc = "error keyword [%s] found in response" % k
                    break
    except Exception, e:
        not_error = False
        if hasattr( e, "hdrs" ):
            for h in e.hdrs.headers:
                # kerberos, see clarin-list
                if "www-authenticate: negotiate" in h.lower( ):
                    not_error = True
                    break
        if not not_error:
            exc = unicode( e )
    msg = u"[%s] %s requesting [%s]" % (eid, exc, absolute_url) if exc is not None else None
    log_stdout( "." if exc is None else "\nx - %s\n" % msg )
    time.sleep( settings["wait"] )
    return msg


# noinspection PyBroadException
def save_errors(error_d):
    _logger.warning( "We have found %d errors" % len(error_d["errors"]) )
    if len( error_d["errors"] ) > 0:
        json.dump( error_d, open( settings["file_error_json"], 'w+' ), indent=4 )
    else:
        try:
            os.remove( settings["file_error_json"] )
        except:
            pass


#
#
#

def test_terena(error_d):
    br = get_browser()
    br.open( settings["json_url"] )
    max_links = len(list(br.links(url_regex="idpentityid=.+")))
    want = 0
    done = set()
    while want < max_links:
        for i, link in enumerate(list(br.links(url_regex="idpentityid=.+"))):
            if i < want:
                continue
            title = link.text.strip()
            if title in done:
                # take the next one
                want += 1
                continue
            done.add(title)
            url = link.absolute_url
            _logger.info( "#%d: %s" % (i + 1, title) )
            msg = test_idp( (br, link) )
            _logger.info( "\t - %s\n" % ( "\n\t" + msg if msg is not None else "OK") )
            if msg is not None:
                idpentityid = re.compile("idpentityid=(.*)$").search(url)
                if idpentityid is not None:
                    idpentityid = urllib.unquote(idpentityid.group(1))
                error_d["errors"].append(
                    (title, u"%s - " % idpentityid + msg) )
            br.open( settings["json_url"] )
            break
        want += 1
    return []


def test_nagios(error_d, test_fnc):
    global settings
    settings["log_stdout"] = False
    took = time.time()
    json_obj = test_fnc(error_d) 
    took = time.time() - took

    def _exit( code, msg_str, time_d ):
        """
            OK = 0
            WARN = 1
            EXC = 2
        """
        #HTTP OK: HTTP/1.1 200 OK - 106963 bytes in 0.053 second response \
        #   time |time=0.052710s;10.000000;20.000000;0.000000 size=106963B;;;0
        msg_whole = "%s total time [%s.0s] with ret code [%s] |time=%ss;%s;%s;%s;%s\n" % (
            msg_str, time_d, code,
            int(time_d),
            len(json_obj) / 2,
            len(json_obj),
            0,
            len(json_obj) )
        print( msg_whole )
        sys.exit(code)

    msg = "OK: checked [%d] idps" % error_d["settings"]["idps_count"]
    if len(error_d["errors"]) == 0:
        _exit( 0, msg, took )
    else:
        # only info
        msg = "NOT " + msg
        ignore_errors = 0
        for eid, _1 in error_d["errors"]:
            idp = idp_from_arr( eid, json_obj )
            if idp is not None and "country" in idp:
                country = idp["country"]
                if country in settings["ignore_error_countries"]:
                    ignore_errors += 1
                    continue
            #msg += u"       \t  %s" % eid
        real_errors = len(error_d["errors"]) - ignore_errors
        msg += " from which [%d] are errors, [%d] total errors" % (
            real_errors, len(error_d["errors"]))
        _exit( 0, msg, real_errors )


# noinspection PyUnresolvedReferences,PyBroadException
def test_default(error_d):
    json_obj = get_json( settings["json_url"] )
    json_obj = remove_duplicate_idps(json_obj)
    error_d["settings"]["idps_count"] = len(json_obj)

    # limit time execution
    #
    try:
        import signal
        # noinspection PyProtectedMember
        def signal_handler(signum, frame):
            log_stdout( ".. taking too long (increase execution_maxtime setting), exitting..." )
            os._exit(1)
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(settings["execution_maxtime"])
    except:
        pass
    
    urls_to_check = [(x["entityID"], login_url( x["entityID"] )) for x in json_obj]
    # single threaded
    #
    if settings["parallel_max"] < 2:
        #if False:
        for i, (eid, u) in enumerate( urls_to_check ):
            log_stdout( "#%d: %s" % (i + 1, eid) )
            msg = test_idp( (eid, u) )
            log_stdout( " - %s\n" % ( "\n\t" + msg if msg is not None else "OK") )
            if msg is not None:
                error_d["errors"].append( (eid, msg) )
    # parallel
    #
    else:
        from multiprocessing import Pool
        slaves = Pool( settings["parallel_max"] )
        ret = [x for x in slaves.map( test_idp, urls_to_check )]
        slaves.close( )
        slaves.join( )
        for err in [x for x in ret if x is not None]:
            eid = err[1:err.find( "]" )]
            error_d["errors"].append( (eid, err) )
    return json_obj


def handle_external_test():
    del sys.argv[0]
    if len(sys.argv) > 0:
        del sys.argv[0]
    param = None if len(sys.argv) == 0 else sys.argv[-1]
    for name, t in settings["external_tests"].iteritems( ):
        if name in sys.argv:
            for k, v in t.iteritems( ):
                settings[k] = v
            return name, param
    return None, param


#
#
#

def test_idps():
    global _logger
    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)-15s %(message)s')
    _logger = logging.getLogger()
    socket.setdefaulttimeout( settings["timeout"] )
    # so we perform specific tests?
    test_name, test_param = handle_external_test()

    error_d = {
        "checked": str( datetime.now( ) ),
        "errors": [],
        "settings": settings
    }

    if test_param not in ("nagios", ):
        _logger.info( "Starting to test [%s] from [%s] using test [%s]" % (
            settings["SP_URL"], settings["json_url"], test_name) )

    # special browser handling
    test_fnc = test_default
    if test_name == "terena":
        test_fnc = test_terena
    # do nagios testing
    if test_param == "nagios":
        test_nagios(error_d, test_fnc)
    else:
        test_fnc(error_d)

    save_errors(error_d)

