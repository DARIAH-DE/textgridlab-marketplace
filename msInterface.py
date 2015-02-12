#!/usr/bin/env python3
# -*- coding: utf-8; mode: python -*-

# Tips von Thorsten
# ans Monitoring anschließen: wenn die Anfrage OK zurückkommt, dann läufts ok
# Konfigurationsdatei auch ins Confluence tun
# caching einsetzen, wäre vielleicht ganz cool
# Gute Fehlermeldungen produzieren
#
# Konfiguration wieder ohne XML, weil kürzer
# 

"""A tiny CGI webservice to provide marketplace functionality for
TextGridLab/Eclipse.

Provides the necessary XML files for showing content in the
Marketplace Menu. Content itself comes from two sources: an XML
configuration file next to this script and another system which gives
information about the plugin to the users and to this webservice.

In this specific case, this is the Atlassian Confluence Wiki system
which also provides their content via REST API:
https://dev2.dariah.eu/wiki/rest/prototype/1/content/27329537

A fourth component is a .htaccess file which deals with the rewriting
of URLs to cater for all the needs. Using htaccess means of course
that we need an Apache webserver.

The system also expects a directory called "files" on the server which
contains an image file to be used as a logo.

To try out the functionality, the ini file of the Lab has to be tweaked:
-Dorg.eclipse.epp.internal.mpc.core.service.DefaultCatalogService.url=http://ocropus.rz-berlin.mpg.de/~kthoden/m/
Or point the URL to your own private instance.

Query by Eclipse looks like this:
http://ocropus.rz-berlin.mpg.de/~kthoden/m/featured/6/api/p?product=info.textgrid.lab.core.application.base_product&os=macosx&runtime.version=3.7.0.v20110110&client=org.eclipse.epp.mpc.core&java.version=1.6.0_65&product.version=0.0.2.201310011243&ws=cocoa&nl=de_DE

The reference of the Eclipse interface is at http://wiki.eclipse.org/Marketplace/REST

Some new stuff:
- first step: a plugin has to be registered at page 36342854
- we get the list from there

"""

# what is the license??

__author__ = "Klaus Thoden, kthoden@mpiwg-berlin.mpg.de"
__date__ = "2015-01-07"

###########
# Imports #
###########
from lxml import etree
import configparser
import logging
logging.basicConfig(filename='msInterface.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
import cgi

import os
CACHE_DIR = "./cache"

if not os.path.exists(CACHE_DIR):
    os.mkdir(os.path.expanduser(CACHE_DIR))

# had some big problems with getting the encoding right
# answer on https://stackoverflow.com/questions/9322410/set-encoding-in-python-3-cgi-scripts
# finally did the trick:
# Ensures that subsequent open()s are UTF-8 encoded.
# Mind you, this is dependant on the server it is running on!
import locale
import sys
import socket
if socket.gethostname() == "ocropus":
    locale.getpreferredencoding = lambda: 'UTF-8'
    # Re-open standard files in UTF-8 mode.
    sys.stdin = open('/dev/stdin', 'r')
    sys.stdout = open('/dev/stdout', 'w')
    sys.stderr = open('/dev/stderr', 'w')

# Atlassian namespaces, we don't really use them
# http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
NS = {'ri':'http://www.atlassian.com/schema/confluence/4/ri/',
      'ac':'http://www.atlassian.com/schema/confluence/4/ac/'}

CONFIG = configparser.ConfigParser()
CONFIG.read("ms.conf")

# we somehow need to know here as well which category (external, beta,
# stable) this is in in the tuple first is ID, second the title, third
# the category. We should get this from Confluence
INST_UNITS = {}
#for name, idno, longname, cat, conf_id, inst_unit in zip(CONFIG.xpath('//plugin/@name'), CONFIG.xpath('//plugin/id'), CONFIG.xpath('//plugin/longName'), CONFIG.xpath('//plugin/cat'), CONFIG.xpath('//plugin/pageID'), CONFIG.xpath('//plugin/installableUnit')):
#    INST_UNITS.update({name:(idno.text, longname.text, cat.text, conf_id.text, inst_unit.text)})

###########
# Objects #
###########
# whole new thing
class PlugIn():
    """Useful comment here"""
    def __init__(self, 
                 name="", 
                 human_title="",
                 description="",
                 logo="", 
                 license="",
                 plugID="",
                 category="", 
                 pageID="", 
                 installableUnit="", 
                 owner=CONFIG['General']['company'], 
                 company=CONFIG['General']['company'], 
                 updateURL=CONFIG['General']['updateUrl']):
        self.human_title = human_title
        self.description = description
        self.logo = logo
        self.license = license
        self.plugID = plugID
        self.name = name
        self.category = category
        self.pageID = pageID
        self.installableUnit = installableUnit
        self.owner = owner
        self.company = company
        self.updateURL = updateURL
# class PlugIn ends here

class MarketPlace():
    """Why not have that, too"""
    def __init__(self, human_title, desc, mpid, name, url, icon, company, company_url, update_url):
        self.human_title = human_title
        self.desc = desc
        self.mpid = mpid
        self.name = name
        self.url = url
        self.icon = icon
        self.company = company
        self.company_url = company_url
        self.update_url = update_url

    # what about
    # <p2UpdateSite>http://www.textgridlab.org/updates/beta</p2UpdateSite>

    # should be configurable, too!
    # search_tab = etree.SubElement(wizard, "searchtab", enabled="0").text = "Search"
    # pop_tab = etree.SubElement(wizard, "populartab", enabled="1").text = "Popular"
    # rec_tab = etree.SubElement(wizard, "recenttab", enabled="0").text = "Recent"

# class MarketPlace ends here

# create Marketplace object
MPLACE = MarketPlace(
    CONFIG['General']['human_title'],
    CONFIG['General']['description'],
    CONFIG['General']['id'],
    CONFIG['General']['name'],
    CONFIG['General']['url'],
    CONFIG['General']['icon'],
    CONFIG['General']['company'],
    CONFIG['General']['companyUrl'],
    CONFIG['General']['updateUrl'])

#################
# Small helpers #
#################
def find_key(dic, val):
    """A dictionary should be searchable both ways. Thanks to the
    internet for that solution
    """
    return [k for k, v in list(dic.items()) if v == val][0]
# def find_key ends here

def reverse_tags(text):
    """Deals with the escaped html markup in the page that is returned
    from confluence. Re-establishes the XML tags and deletes the
    namespaces.
    """
    import re

    replacements = {
        '&amp;' : '&',
        '&lt;' : '<',
        '&gt;' : '>',
        '&quot;' : '"',
        '&apos;' : "'",
        'ac:' : '',
        'ri:' : ''
    }

    for thing in list(replacements.keys()):
        text = text.replace(thing, replacements[thing])
    text = re.sub(r'&(?=\s)', '&amp;', text)
    return text
# def reverse_tags ends here

def unescape(text):
    """Remove HTML or XML character references and entities from a text
    string. Return a Unicode string.

    With thanks to http://effbot.org/zone/re-sub.htm#unescape-html.
    Modified to work with Python3.
    """
    import re, html.entities

    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(html.entities.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub(r"&#?\w+;", fixup, text)
# def unescape ends here

####################
# Confluence stuff #
####################
def get_confluence_page(confluence_page_id):
    """Retrieve a page from Confluence's REST api. The confluence_page_id
    is found in the config file. Return an XML document which needs to
    be refined using parse_confluence_body.
    """
    import urllib.request, urllib.parse, urllib.error

    base_url = CONFIG['General']['wikiSite']
    fullpath = base_url + str(confluence_page_id)
    logging.debug("Trying to fetch %s" % fullpath)
    usock = urllib.request.urlopen(fullpath)

    try:
        logging.info("Querying %s for data" % fullpath)
        plugin_info = etree.parse(usock)
    except etree.XMLSyntaxError:
        logging.error("Retrieved XML syntax error.")
        sys.exit()
    usock.close()

    return plugin_info
## def get_confluence_page ends here

def parse_confluence_body(returned_xml):
    """Parse the page returned by get_confluence_page, fix the code and
    read the content of /content/body, which is escaped XML code, into
    XML. Return that XML element, wrapped in a new root tag "pagebody".
    """

    plugin_body = returned_xml.xpath('/content/body')[0].text

    # some ugly modifications
    clean = reverse_tags(plugin_body)
    clean = unescape(clean)

    body_xml = etree.fromstring(clean)

    # for sanity's sake we wrap this again in an XML element
    parsed_body = etree.Element("pagebody")
    parsed_body.append(body_xml)

    return parsed_body
## def parse_confluence_body ends here

def compile_info(parsed_confluence_body):
    """Return a dictionary of the things parsed out of the webpage. The
    table we are parsing needs to be in a strict order concerning the
    first four elements: title, description, logo, license
    """

    # this should work differently: use XPath to parse the title based on the th-Element "Titel"
    # here: //tr/th[text()="Titel"]/../td/text()
    # these are the guts we need
    plugin_dict = dict({
        "pl_title" : parsed_confluence_body.xpath('/pagebody/table/tbody/tr/th[text()="Titel"]/../td/text()'),
        "pl_desc" : parsed_confluence_body.xpath('/pagebody/table/tbody/tr/th[text()="Beschreibung"]/../td/text()'),
        "pl_icon" : parsed_confluence_body.xpath('/pagebody/table/tbody/tr/th[text()="Logo"]/../td/image/attachment/@filename')[0],
        # Careful! If we do it like this, then license needs not be a link!
        "pl_license" : parsed_confluence_body.xpath('/pagebody/table/tbody/tr/th[text()="Lizenz"]/../td/a'),
    })
    return plugin_dict
# def compile_info ends here

# meise = PlugIn(parsed_confluence_body.xpath('/pagebody/table/tbody/tr[1]/td')[0].text,
#                parsed_confluence_body.xpath('/pagebody/table/tbody/tr[2]/td')[0].text,
#                parsed_confluence_body.xpath('/pagebody/table/tbody/tr[3]/td/image/attachment/@filename')[0],
#                parsed_confluence_body.xpath('/pagebody/table/tbody/tr[4]/td/a')[0].text)
# for testing, create PlugIn object
#plugin_digilib = 

def get_modified_time(confluence_page_id):
    """Parse the last modified date from plugin info page. Return parsed
    datetime object"""

    import datetime

    raw_xml = get_confluence_page(str(confluence_page_id))
    # <lastModifiedDate date="2014-11-24T12:26:01+0100" friendly="Nov 24, 2014"/>
    last_modified = raw_xml.xpath('/content/lastModifiedDate/@date')[0]
    return datetime.datetime.strptime(last_modified, "%Y-%m-%dT%H:%M:%S%z")
# def get_modified_time ends here

def get_updates():
    """Get new plugin information from Confluence. This is a function that
    should be run by a cron job or something"""
    wiki_date = get_modified_time(confluence_page_id)
    if wiki_date > cached_date:
    # renew cache
        get_data()
# def get_updates ends here

def get_confluence_config():
    """Read the developer's configuration of the plugins. This is also
    kept on Confluence so that it can be modified more easily.
    Currently it resides on
    https://dev2.dariah.eu/wiki/rest/prototype/1/content/36342854
    """
    info_site = CONFIG['General']['pluginInfo']

    plugin_info = get_confluence_page(info_site)
    table = parse_confluence_body(plugin_info)

    return table
# def get_confluence_config ends here

###########
# Caching #
###########
def make_cache():
    """In order to gain additional speed, cache the data and store them on
    the server as pickled objects
    """
    pass
# make_cache ends here
    
def get_cached_time():
    """Return date of last modification from cached item so that we can
    compare it with the date from the wiki"""

# newdate = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z")
# if newdate>olddate: get_data
# store them as pickles?
#
# at the same time, there should be a function, accessible also via the cgi, to refresh the cache
# instantaneously

# def get_cached_time ends here

#################
# The Beginning #
#################

def some_infos():
    """Playing around with things"""
    # Get the config and start building objects
    infopage_xml=get_confluence_config()

    # this is the list of all plugin names
    list_of_plugins = infopage_xml.xpath('/pagebody/table/tbody/tr[*]/td[2]/text()')

    # Playing around with classes, according to
    # http://inventwithpython.com/blog/2014/12/02/why-is-object-oriented-programming-useful-with-an-role-playing-game-example/
    # how do I get a sensible name for the plugin? or are they ok kept in a dictionary?
    # keeping all the objects in a dictionary seems like a typical way?
    plugins = []

    # iterate through the table and get info about plugin
    for l in range(len(list_of_plugins)):
        # construct an object for each plugin, put the name in
        plugins.append(PlugIn(list_of_plugins[l]))
        for i in range(1,9):
            # this loop goes through each line of the table and
            # assigns the appropriate value to each plugin using
            # double slashes before the text() node to cater for the
            # occasional p tag
            tmpx = '/pagebody/table/tbody/tr[%s]/td[%s]//text()' % (l+2,i)
            if i == 1:
                plugins[l].plugID = infopage_xml.xpath(tmpx)[0]
            # name is already in
            # if i == 2:
            #     plugins[l].name = infopage_xml.xpath(tmpx)[0]
            if i == 3:
                plugins[l].category = infopage_xml.xpath(tmpx)[0]
            if i == 4:
                plugins[l].pageID = infopage_xml.xpath(tmpx)[0]
            if i == 5:
                plugins[l].installableUnit = infopage_xml.xpath(tmpx)[0]
            if i == 6:
                if infopage_xml.xpath(tmpx)[0] != "\xa0":
                    plugins[l].owner = infopage_xml.xpath(tmpx)[0]
            if i == 7:
                if infopage_xml.xpath(tmpx)[0] != "\xa0":
                    plugins[l].company = infopage_xml.xpath(tmpx)[0]
            if i == 8:
                if len(infopage_xml.xpath(tmpx)) == 0:
                    tmpxhref = '/pagebody/table/tbody/tr[%s]/td[%s]/a/@href' % (l+2,i)
                    if infopage_xml.xpath(tmpxhref)[0] != "\xa0":
                        plugins[l].updateURL = infopage_xml.xpath(tmpxhref)[0]

        # get additional info from the plugin info pages
        for plugin in plugins:
            raw_xml = get_confluence_page(plugin.pageID)
            parsed_body = parse_confluence_body(raw_xml)

            # double slashes before the text() node to cater for the
            # occasional p tag
            plugin.human_title = parsed_body.xpath('/pagebody/table/tbody/tr/th[text()="Titel"]/../td//text()')[0]
            plugin.description = parsed_body.xpath('/pagebody/table/tbody/tr/th[text()="Beschreibung"]/../td//text()')[0]
            plugin.icon = parsed_body.xpath('/pagebody/table/tbody/tr/th[text()="Logo"]/../td/image/attachment/@filename')
            plugin.license = parsed_body.xpath('/pagebody/table/tbody/tr/th[text()="Lizenz"]/../td/a/@href')

    return plugins
# def some_infos ends here

#############################################
# Here starts the building of the XML nodes #
#############################################
def build_mp_apip():
    """Return info about the whole marketplace. Which categories are in there?"""

    # building the XML
    mplace = etree.Element("marketplace")
    market = etree.SubElement(mplace, "market", 
                              id=MPLACE.mpid, 
                              name=MPLACE.name, 
                              url=MPLACE.url+"category/markets/"+MPLACE.mpid)

    categ = list(CONFIG['Categories'].values())
    cat_id = list(CONFIG['Categories'].keys())

    # Iterating through the categories
    cat_count = 1
    for cat_key, cat_val in zip(categ, cat_id):
        # is the space after mpid+","+cat_key) obliatory???
        etree.SubElement(market, "category", 
                         count=str(cat_count), 
                         id=cat_val, 
                         name=cat_key, 
                         url=str(MPLACE.url)+"taxonomy/term/"+MPLACE.mpid+","+cat_key)
        cat_count += 1
    return mplace
# def build_mp_apip ends here

def build_mp_cat_apip():
    """Return information on a catalog. According to server log, this is
    the first thing the Lab looks for. Requires only info from config
    file. After choosing that catalog, the root is called.
    """
    # build the XML
    mplace = etree.Element("marketplace")
    catalogs = etree.SubElement(mplace, "catalogs")
    catalog = etree.SubElement(catalogs, "catalog", 
                               id=MPLACE.mpid, 
                               title=MPLACE.human_title, 
                               url=MPLACE.url, 
                               selfContained="1", 
                               icon=MPLACE.url+MPLACE.icon)
    desc = etree.SubElement(catalog, "description").text = MPLACE.desc
    dep_rep = etree.SubElement(catalog, "dependenciesRepository")
    wizard = etree.SubElement(catalog, "wizard", title="")
    icon = etree.SubElement(wizard, "icon")
    search_tab = etree.SubElement(wizard, "searchtab", enabled="0").text = "Search"
    pop_tab = etree.SubElement(wizard, "populartab", enabled="1").text = "Popular"
    rec_tab = etree.SubElement(wizard, "recenttab", enabled="0").text = "Recent"
    return mplace
# def build_mp_cat_apip ends here

def build_mp_taxonomy(market_id, cate_id):
    """Construct the taxonomy. List all plugins of one category. The
    category a plugin belongs to is taken from the config."""

    # small dictionary for handling the category name and id
    cate_dict = {}
    for cat_key, cat_val in zip(list(CONFIG['Categories'].values()), list(CONFIG['Categories'].keys())):
        cate_dict.update({cat_val:cat_key})

    # a small detour, because we might get the name value of the category instead of the ID
    if cate_id in [v for k, v in list(cate_dict.items())]:
        cate_id = [k for k, v in list(cate_dict.items()) if v == cate_id][0]
        # using the function
        # cate_id = find_key(cate_dict, cate_id)

    # build the XML
    mplace = etree.Element("marketplace")
    category = etree.SubElement(mplace, "category", 
                                id=str(cate_id), 
                                name=(cate_dict[cate_id]), 
                                url=MPLACE.url+"taxonomy/term/"+str(market_id)+", "+str(cate_id))
    # repeat for those belonging to the same group
    for i_unit in INST_UNITS.items():
        if int(i_unit[1][2]) == int(cate_id):
            node = etree.SubElement(category, "node", 
                                    id=i_unit[1][0], 
                                    name=i_unit[1][1], 
                                    url=MPLACE.url+"content/"+i_unit[1][0])
            fav = etree.SubElement(category, "favorited").text = "0"
    return mplace
# def build_mp_taxonomy ends here

def build_mp_node_apip(plug_name):
    """Return info on installable Unit (i.e. plugin). Get info from the
    CONFIG and from Confluence info page. Input is plug_name"""

    import os

    # here we get the info about the plugin! returns a dictionary full of stuff
    # should be an object
    plugin_id = INST_UNITS[plug_name][3]
    if os.path.exists("%s/%s.p" % (CACHE_DIR,plug_name)):
        plug = get_from_cache(plug_name)
    else:
        raw_xml = get_confluence_page(plugin_id)
        parsed_body = parse_confluence_body(raw_xml)
        plug = compile_info(parsed_body)

    node = etree.Element("node", 
                         id=INST_UNITS[plug_name][0], 
                         name=INST_UNITS[plug_name][1], 
                         url=MPLACE.url+"content/"+INST_UNITS[plug_name][0])

    body_element = etree.SubElement(node, "body").text = etree.CDATA(plug["pl_desc"])
    # taken from Label of wikipage
    cate_element = etree.SubElement(node, "categories")
    # noch nicht ganz fertig!
    category = etree.SubElement(cate_element, "categories", 
                                id=INST_UNITS[plug_name][2], 
                                name=INST_UNITS[plug_name][1], 
                                url=MPLACE.url+"taxonomy/term/"+MPLACE.mpid+","+INST_UNITS[plug_name][2])
    # how to do that?
    change_element = etree.SubElement(node, "changed").text = "0"
    # constantly TextGrid? can be superseded by plugin-specific entry
    tmp = '//plugin[@name="%s"]/company' % plug_name
    if len(CONFIG.xpath(tmp)) != 0:
        company_element = etree.SubElement(node, "companyname").text = etree.CDATA(CONFIG.xpath(tmp)[0].text)
    else:
        company_element = etree.SubElement(node, "companyname").text = etree.CDATA(CONFIG.xpath('//general/company')[0].text)
    # upload of plugin?, use old values here?
    created_element = etree.SubElement(node, "created").text = "0"
    # what here?
    eclipse_element = etree.SubElement(node, "eclipseversion").text = etree.CDATA("0")
    # would that be ticked on the wiki page?
    fav_element = etree.SubElement(node, "favorited").text = "0"
    # 1 is original value here
    foundation_element = etree.SubElement(node, "foundationmember").text = "1"
    url_element = etree.SubElement(node, "homepageurl").text = etree.CDATA(CONFIG.xpath('//general/companyUrl')[0].text)
    # icon of plugin
    image_element = etree.SubElement(node, "image").text = etree.CDATA("https://dev2.dariah.eu/wiki/download/attachments/" + plugin_id + "/" + plug["pl_icon"])
    # just a container
    ius_element = etree.SubElement(node, "ius")
    iu_element = etree.SubElement(ius_element, "iu").text = INST_UNITS[plug_name][4]
    license_element = etree.SubElement(node, "license").text = plug["pl_license"]
    # who is the owner? same as company!
    tmp = '//plugin[@name="%s"]/owner' % plug_name
    if len(CONFIG.xpath(tmp)) != 0:
        owner_element = etree.SubElement(node, "owner").text = etree.CDATA(CONFIG.xpath(tmp)[0].text)
    else:
        owner_element = etree.SubElement(node, "owner").text = etree.CDATA(CONFIG.xpath('//general/company')[0].text)
    # what is this about?
    resource_element = etree.SubElement(node, "resource") # this?
    # see logo
    # screenshot would be displayed if we click on more info in marketplace
    scrshotEle = etree.SubElement(node,"screenshot").text = "https://i.imgur.com/z8hViF9.jpg"
    #scrshotEle = etree.SubElement(node,"screenshot").text = "https://develop.sub.uni-goettingen.de/repos/textgrid/trunk/lab/noteeditor/info.textgrid.lab.noteeditor.feature/Screenshot_MEISE_2012-04-20.png"
    # also hidden field?
    tmp = '//plugin[@name="%s"]/updateUrl' % plug_name
    if len(CONFIG.xpath(tmp)) != 0:
        update_element = etree.SubElement(node, "updateurl").text = etree.CDATA(CONFIG.xpath(tmp)[0].text)
    else:
        update_element = etree.SubElement(node, "updateurl").text = etree.CDATA(CONFIG.xpath('//general/updateUrl')[0].text + plug_name)

    return node
# def build_mp_node_apip ends here

def build_mp_frfp_apip(list_type, mark_id=CONFIG['General']['id']):
    """Take those nodes (my theory here) that have a value of non-nil in
    'featured' (should be on the wiki page) and wraps them into some
    XML. Works also for recent, favorite and popular, they are
    similar. Hence the name of this function.
    """
    # this list needs to be somewhat dynamic
    featured_list = ["oxygen","noteeditor","digilib","collatex","sadepublish","ttle"]
    mplace = etree.Element("marketplace")
    plugin_list = etree.SubElement(mplace, list_type, count=str(len(featured_list)))
    # make the nodes here as a subElement of the list
    for item in featured_list:
        new_node = build_mp_node_apip(item)
        plugin_list.insert(1, new_node)

    return mplace
# def build_mp_frfp_apip ends here

def build_mp_content_apip(node_id):
    """Return info on a single node."""

    auxdic = dict()
    for i_unit in INST_UNITS.items():
        auxdic.update({i_unit[1][0] : i_unit[0]})

    mplace = etree.Element("marketplace")
    new_node = build_mp_node_apip(auxdic[node_id])
    mplace.insert(1, new_node)

    return mplace
# def build_mp_content_apip ends here

##########
# Output #
##########
def goto_confluence(node_id):
    """Redirect the browser to the Confluence page."""

    auxdic = dict()
    for i_unit in INST_UNITS.items():
        auxdic.update({i_unit[1][0] : i_unit[1][3]})

    goto_url = "https://dev2.dariah.eu/wiki/pages/viewpage.action?pageId=" + auxdic[node_id]

    print('Status: 303 See Other')
    # newline is important here
    print('Location: ' + goto_url + '\n')
# def goto_confluence ends here

def output_xml(node):
    """Serve the XML for the Marketplace. Here you go."""
    # output
    print('Content type: text/xml; charset=utf-8\n')
    # this is of a bytes type
    xml_bytes = etree.tostring(node, pretty_print=True, encoding='utf-8', xml_declaration=True)
    # convert this to a string
    ship_out = xml_bytes.decode('utf-8')
    # for debugging
    print(ship_out)
# def output_xml ends here

################
# The main bit #
################
def main():
    """Parse what is received by the URL and ship it out to the relevant channel."""
    # We should maybe catch and retain all those things the client tells us:
    # product=info.textgrid.lab.core.application.base_product
    # os=macosx
    # runtime.version=3.7.0.v20110110
    # client=org.eclipse.epp.mpc.core
    # java.version=1.6.0_65
    # product.version=0.0.2.201310011243
    # ws=cocoa
    # nl=de_DE

    # arguments need to be read into something that the CGI can deal with
    form = cgi.FieldStorage()
    if form.getvalue('action') == 'main':
        node = build_mp_apip()
        output_xml(node)
    if form.getvalue('action') == 'catalogs':
        node = build_mp_cat_apip()
        output_xml(node)
    if form.getvalue('action') == 'taxonomy':
        node = build_mp_taxonomy(form.getvalue('marketId'), form.getvalue('categoryId'))
        output_xml(node)
    # list covers all of recent, favorites, popular and featured
    if form.getvalue('action') == 'list':
        if form.getvalue('marketId') != None:
            node = build_mp_frfp_apip(form.getvalue('type'), form.getvalue('marketId'))
        else:
            node = build_mp_frfp_apip(form.getvalue('type'))
        output_xml(node)
    if form.getvalue('action') == 'content':
        node = build_mp_content_apip(form.getvalue('nodeId'))
        output_xml(node)
    if form.getvalue('action') == 'redirect':
        goto_confluence(form.getvalue('nodeId'))

    # I think, node can be redirected to content. Did so in htaccess file.
    # if form.getvalue('action') == 'node':
    #     node = "not yet implemented"

    # really bad error handling, but search functionality has been disabled:
    # search_tab = etree.SubElement(wizard,"searchtab",enabled="0").text = "Search"
    if form.getvalue('action') == 'search':
        node = "not yet implemented"

if __name__ == "__main__":
    main()

#########
# FINIS #
#########
