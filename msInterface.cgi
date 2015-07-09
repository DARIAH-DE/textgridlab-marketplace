#!/usr/bin/env python3
# -*- coding: utf-8; mode: python -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Tips von Thorsten
# ans Monitoring anschließen: wenn die Anfrage OK zurückkommt, dann läufts ok

"""A Python CGI webservice to provide marketplace functionality for
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

The system also expects an image file to be used as a logo.

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
__author__ = "Klaus Thoden, kthoden@mpiwg-berlin.mpg.de"
__date__ = "2015-04-24"

###########
# Imports #
###########
from lxml import etree
from datetime import datetime
import configparser
import logging
import cgi
import os

# had some big problems with getting the encoding right
# answer on https://stackoverflow.com/questions/9322410/set-encoding-in-python-3-cgi-scripts
# finally did the trick:
# Ensures that subsequent open()s are UTF-8 encoded.
# Mind you, this is dependant on the server it is running on!
import locale
import sys
import socket
# list of servers we are working on
servers = ("ocropus", "textgrid-esx2", "textgrid-esx1")
if socket.gethostname() in servers:
    locale.getpreferredencoding = lambda: 'UTF-8'
    # Re-open standard files in UTF-8 mode.
    sys.stdin = open('/dev/stdin', 'r')
    sys.stdout = open('/dev/stdout', 'w')
    sys.stderr = open('/dev/stderr', 'w')

# setting up things
# both config and cache directory are in the same place as this script
CONFIG = configparser.ConfigParser()
CONFIG.read("ms.conf")

LOGFILE = CONFIG['General']['logfile']
LOGLEVEL = CONFIG['General']['loglevel']

numeric_level = getattr(logging, LOGLEVEL.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)
logging.basicConfig(filename=LOGFILE, level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')

CACHE_DIR = CONFIG['General']['cache_dir']
if not os.path.exists(CACHE_DIR):
    os.mkdir(os.path.expanduser(CACHE_DIR))

WIKI_VIEW = CONFIG['General']['wiki_view']

###########
# Objects #
###########
class TGLab():
    """Class for storing information about the Lab that sent the query.
    # We should maybe catch and retain all those things the client tells us:
    # product=info.textgrid.lab.core.application.base_product
    # os=macosx
    # runtime.version=3.7.0.v20110110
    # client=org.eclipse.epp.mpc.core
    # java.version=1.6.0_65
    # product.version=0.0.2.201310011243
    # ws=cocoa
    # nl=de_DE
"""
    pass
# class TGLab ends here

class PlugIn():
    """Class for Plugins, just to collect their properties. Has one
    required positional argument, the confluence pageId."""
    def __init__(self,
                 pageId,
                 name = "",
                 human_title = "",
                 description = "",
                 featured = "",
                 logo = "",
                 license = "",
                 plugId = "",
                 category = "",
                 installableUnit = "",
                 screenshot = "",
                 owner = CONFIG['General']['company'],
                 company = CONFIG['General']['company'],
                 company_url = CONFIG['General']['company_url'],
                 update_url = CONFIG['General']['update_url']):
        self.human_title = human_title
        self.description = description
        self.logo = logo
        self.license = license
        self.plugId = plugId
        self.featured = featured
        self.name = name
        self.category = category
        self.pageId = pageId
        self.screenshot = screenshot
        self.installableUnit = installableUnit
        self.owner = owner
        self.company = company
        self.company_url = company_url
        self.update_url = update_url
# class PlugIn ends here

class MarketPlace():
    """Why not have that, too"""
    def __init__(self, human_title, desc, mpid, name, url, icon, company, company_url, update_url, main_wiki_page):
        self.human_title = human_title
        self.desc = desc
        self.mpid = mpid
        self.name = name
        self.url = url
        self.icon = icon
        self.company = company
        self.company_url = company_url
        self.update_url = update_url
        self.main_wiki_page = main_wiki_page
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
    CONFIG['General']['company_url'],
    CONFIG['General']['update_url'],
    CONFIG['General']['main_wiki_page'])

#################
# Small helpers #
#################
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
def get_confluence_config():
    """Read the developer's configuration of the plugins. This is also
    kept on Confluence so that it can be modified more easily.
    Currently it resides on
    https://dev2.dariah.eu/wiki/rest/prototype/1/content/36342854.
    Return a neatly formatted XML file containing a table.
    """
    info_site = CONFIG['General']['plugin_info']

    plugin_info = get_confluence_page(info_site)
    table = parse_confluence_body(plugin_info)

    return table
# def get_confluence_config ends here

def get_list_of_plugins():
    """Query the confluence wiki and return a list of plugin objects."""
    # Get the XML of the infopage and store it in memory
    infopage_xml = get_confluence_config()

    # create immutable tuple of the page_ids, because we need to deal
    # with positional stuff in that list lateron
    lopi = tuple(infopage_xml.xpath('/pluginInfo/table/tbody/tr[*]/td[4]/text()'))

    # with that tuple in place, we can call the build function
    # individually, however recurring to the tuple in order to get
    # info from the correct line in the table from infopage_xml
    return lopi, infopage_xml
# def get_list_of_plugins

def get_confluence_page(confluence_page_id):
    """Retrieve a page from Confluence's REST api. The confluence_page_id
    is found in the config file. Return an XML document which needs to
    be refined using parse_confluence_body.
    """
    import urllib.request, urllib.parse, urllib.error

    base_url = CONFIG['General']['wiki_api']
    fullpath = base_url + str(confluence_page_id)
    logging.debug("Trying to fetch %s" % fullpath)
    usock = urllib.request.urlopen(fullpath)

    try:
        logging.info("Querying %s for data" % fullpath)
        logging.info("This corrensponds to %s%s" % (WIKI_VIEW, str(confluence_page_id)))
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
    XML. Return that XML element, wrapped in a new root tag "pluginInfo".
    """

    # Atlassian namespaces, we don't really use them
    # http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
    NS = {'ri':'http://www.atlassian.com/schema/confluence/4/ri/',
          'ac':'http://www.atlassian.com/schema/confluence/4/ac/'}

    plugin_body = returned_xml.xpath('/content/body')[0].text

    # some ugly modifications
    clean = reverse_tags(plugin_body)
    clean = unescape(clean)

    body_xml = etree.fromstring(clean)

    # for sanity's sake we wrap this again in an XML element
    parsed_body = etree.Element("pluginInfo")
    parsed_body.append(body_xml)

    return parsed_body
## def parse_confluence_body ends here

def confluence_page_xml(page_id):
    """Get a page from the confluence wiki, have it parsed and
    timestamped. This is the XML to work with"""
    # get additional info from the plugin info pages
    raw_xml = get_confluence_page(page_id)
    parsed_body = parse_confluence_body(raw_xml)

    # control things, i. e. caching
    # put in here also name and links to the page!
    last_modified = etree.Element("lastModified")
    last_modified.text = raw_xml.xpath('/content/lastModifiedDate/@date')[0]
    parsed_body.insert(0, last_modified)

    parsed_body.insert(0, etree.Comment("""File generated on %s.
    Corresponds to %s%s """ % (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), WIKI_VIEW, page_id)))

    return parsed_body
# def confluence_page_xml ends here

def build_plugin_info(page_id, infopage_xml, l):
    """Construct the plugin object by using the confluence page id. Take
    the page_id to query first the infopage and then the individual
    plugin pages. l is the index of the page in the lopi tuple which
    we need to address the correct line in infopage table.
    """

    # # in what position is that page_id in lopi?
    # l = lopi.index(page_id)

    # make an object
    temp_plugin_object = PlugIn(page_id)

    for i in range(1,11):
        # this loop goes through the columns of a table line and
        # assigns the appropriate value to each plugin using double
        # slashes before the text() node to cater for the occasional p
        # tag
        tmp_xpath = '/pluginInfo/table/tbody/tr[%s]/td[%s]//text()' % (l + 2, i)
        if i == 1:
            temp_plugin_object.plugId = infopage_xml.xpath(tmp_xpath)[0]
        if i == 2:
            temp_plugin_object.name = infopage_xml.xpath(tmp_xpath)[0]
        if i == 3:
            temp_plugin_object.category = infopage_xml.xpath(tmp_xpath)[0]
        if i == 4:
            temp_plugin_object.pageId = infopage_xml.xpath(tmp_xpath)[0]
        if i == 5:
            temp_plugin_object.featured = infopage_xml.xpath(tmp_xpath)[0]
        if i == 6:
            temp_plugin_object.installableUnit = infopage_xml.xpath(tmp_xpath)[0]
        if i == 7:
            if infopage_xml.xpath(tmp_xpath)[0] != "\xa0":
                temp_plugin_object.owner = infopage_xml.xpath(tmp_xpath)[0]
        if i == 8:
            if infopage_xml.xpath(tmp_xpath)[0] != "\xa0":
                temp_plugin_object.company = infopage_xml.xpath(tmp_xpath)[0]
        if i == 9:
            if infopage_xml.xpath(tmp_xpath)[0] != "\xa0":
                tmp_xpath_href = '/pluginInfo/table/tbody/tr[%s]/td[%s]/a/@href' % (l + 2, i)
                temp_plugin_object.company_url = infopage_xml.xpath(tmp_xpath_href)[0]
        if i == 10:
            if infopage_xml.xpath(tmp_xpath)[0] != "\xa0":
                tmp_xpath_href = '/pluginInfo/table/tbody/tr[%s]/td[%s]/a/@href' % (l + 2, i)
                temp_plugin_object.update_url = infopage_xml.xpath(tmp_xpath_href)[0]

    # for speed issues, we store the wiki pages as XML files.
    cached_page = CACHE_DIR + "/" + page_id + ".xml"
    if not os.path.exists(cached_page):
        logging.info("Downloading %s." % page_id)
        make_cache(page_id)
    else:
        logging.info("Using cached version of plugin info for %s." % page_id)

    cached_page = CACHE_DIR + "/" + page_id + ".xml"
    parsed_body = etree.parse(cached_page)

    # double slashes before the text() node to cater for the
    # occasional p tag
    temp_plugin_object.human_title = parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Titel"]/../td//text()')[0]
    temp_plugin_object.description = parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Beschreibung"]/../td//text()')[0]
    if len(parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Lizenz"]/../td/a/@href')) != 0:
        temp_plugin_object.license = parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Lizenz"]/../td/a/@href')[0]

    if len(parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Logo"]/../td/image/attachment/@filename')) != 0:
        temp_plugin_object.logo = parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Logo"]/../td/image/attachment/@filename')[0]
    if len(parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Screenshots"]/../td/image/attachment/@filename')) != 0:
        temp_plugin_object.screenshot = parsed_body.xpath('/pluginInfo/table/tbody/tr/th[text()="Screenshots"]/../td/image/attachment/@filename')[0]

    return temp_plugin_object
# def build_plugin_info ends here

###########
# Caching #
###########
def get_modified_time(confluence_page_id):
    """Parse the last modified date from plugin info page. Return parsed
    datetime object"""

    raw_xml = get_confluence_page(str(confluence_page_id))
    # <lastModifiedDate date="2014-11-24T12:26:01+0100" friendly="Nov 24, 2014"/>
    last_modified = raw_xml.xpath('/content/lastModifiedDate/@date')[0]
    return datetime.strptime(last_modified, "%Y-%m-%dT%H:%M:%S%z")
# def get_modified_time ends here

def get_cached_time(page_id):
    """Return date of last modification from cached item so that we can
    compare it with the date from the wiki."""

    query_cache = CACHE_DIR + "/" + page_id + ".xml"
    XML = etree.parse(query_cache)

    cached_time_string = XML.xpath('/pluginInfo/lastModified/text()')[0]
    cached_time = datetime.strptime(cached_time_string, "%Y-%m-%dT%H:%M:%S%z")
    return cached_time
# def get_cached_time ends here

def get_updates(page_id):
    """Get new plugin information from Confluence. This is a function that
    should be run by a cron job or something"""
    wiki_date = get_modified_time(page_id)
    cached_date = get_cached_time(page_id)

    logging.info(wiki_date)
    logging.info(cached_date)

    if wiki_date == cached_date:
        logging.info("Nothing new on the server." % page_id)

    if wiki_date > cached_date:
        # renew cache for that page
        logging.info("Online version of %s is newer that cached version. Refreshing." % page_id)
        make_cache(page_id)
    else:
        logging.info("Nothing new on the server." % page_id)
# def get_updates ends here

def update_all(lopi):
    print('Content type: text/html; charset=utf-8\n')
    print('<html>\n<p>Updating %s files:</p>\n' % len(lopi))
    for page in lopi:
        print('<p>%s</p>' % page)
        logging.debug("Do I need to update %s?" % pi)
        get_updates(pi)

    print('</html>\n')
# def update_all ends here

def cache_reload(lopi):
    """Function for refreshing the cache."""
    print('Content type: text/html; charset=utf-8\n')
    print('<html><p>Refreshing cache.</p></html>\n')
    logging.info("Refreshing the cache.")

    for pi in lopi:
        make_cache(pi)
    logging.info("Refresh finished.")
# cache_reload ends here

def make_cache(page_id):
    """In order to gain additional speed, cache the data and store them on
    the server as XML files. This function downloads the page, has it
    modified and timestamped and writes it to a file.
    """
    parsed_page = confluence_page_xml(page_id)

    writeDest = CACHE_DIR + "/" + page_id + ".xml"
    logging.info("Writing plugin info to %s." % writeDest)
    tree = etree.ElementTree(parsed_page)
    tree.write(writeDest, pretty_print=True, xml_declaration=True,encoding="utf-8")
# make_cache ends here
    
#############
# Searching #
#############
def search_files(search_string, lopi):
    """Search the text nodes of all plugins using the unquoted form of the
    search string that came in by URL. If search string is found, add
    to a list and return the list of plugin_ids that contain the
    search term.


GET /~kthoden/m3/api/p/search/apachesolr_search/k%C3%B6nnen?filters=tid:tg0120%20tid:5&product=info.textgrid.lab.core.application.base_product&platform.version=4.4.2.v20150204-1700&os=macosx&java.version=1.8.0_31&client=org.eclipse.epp.mpc.core&product.version=0.0.3.201503251333&runtime.version=3.10.0.v20140318-2214&ws=cocoa&nl=de_DE HTTP/1.1" 302 666 "-" "Apache-HttpClient/4.3.6 (java 1.5)"
 
    Filters need to be done!

   """

    import urllib.parse

    # list of successful hits
    hits = []

    # sanitize search string
    sanitized_search_string = urllib.parse.unquote_plus(search_string)
    # get all cached files
    for plugin_id in lopi:
        cached_page = CACHE_DIR + "/" + plugin_id + ".xml"
        # collect text nodes
        textnodes = collect_text_nodes(cached_page)
        # search string
        if sanitized_search_string.lower() in textnodes.lower():
            hits.append(plugin_id)

    return hits
# search_files ends here

def collect_text_nodes(cached_file):
    """Collect the text nodes and put them in one string."""
    from lxml import etree
    import re
    
    result = ""

    XML = etree.parse(cached_file)
    textnodes = XML.findall(".//td")

    for node in textnodes:
        # search only strings (not NoneType)
        if type(node.text) != str:
            continue
        # also, just go on if you find empty nodes
        if re.match(r'\n +', node.text):
            continue
        result += node.text
        # add space between text strings
        result += " "
    return result
# collect_text_nodes ends here

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
                              url=MPLACE.url + "category/markets/" + MPLACE.mpid)

    categ = list(CONFIG['Categories'].values())
    cat_id = list(CONFIG['Categories'].keys())

    # Iterating through the categories
    cat_count = 1
    for cat_key, cat_val in zip(categ, cat_id):
        # is the space after mpid+","+cat_key) obligatory???
        etree.SubElement(market, "category", 
                         count=str(cat_count), 
                         id=cat_val, 
                         name=cat_key, 
                         url=str(MPLACE.url) + "taxonomy/term/" + MPLACE.mpid + "," + cat_key)
                         # url=str(MPLACE.url) + "taxonomy/term/" + MPLACE.mpid + ", " + cat_key)
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
                               icon=MPLACE.url + MPLACE.icon)
    desc = etree.SubElement(catalog, "description").text = MPLACE.desc
    dep_rep = etree.SubElement(catalog, "dependenciesRepository")
    wizard = etree.SubElement(catalog, "wizard", title="")
    icon = etree.SubElement(wizard, "icon")

    if CONFIG['General']['search'] != "0":
        search_tab = etree.SubElement(wizard, "searchtab", enabled="1").text = "Suche"
    else:
        search_tab = etree.SubElement(wizard, "searchtab", enabled="0").text = "Suche"
    if CONFIG['General']['popular'] != "0":
        pop_tab = etree.SubElement(wizard, "populartab", enabled="1").text = "Beliebt"
    else:
        pop_tab = etree.SubElement(wizard, "populartab", enabled="0").text = "Beliebt"
    if CONFIG['General']['recent'] != "0":
        rec_tab = etree.SubElement(wizard, "recenttab", enabled="1").text = "Neu"
    else:
        rec_tab = etree.SubElement(wizard, "recenttab", enabled="0").text = "Neu"

    return mplace
# def build_mp_cat_apip ends here

def build_mp_taxonomy(market_id, cate_id, PLUGINS):
    """Construct the taxonomy. List all plugins of one category. The
    category a plugin belongs to is taken from the config."""

    # small dictionary for handling the category name and id
    cate_dict = {}
    for cat_key, cat_val in zip(list(CONFIG['Categories'].values()), list(CONFIG['Categories'].keys())):
        cate_dict.update({cat_val:cat_key})

    # a small detour, because we might get the name value of the category instead of the Id
    if cate_id in [v for k, v in list(cate_dict.items())]:
        cate_id = [k for k, v in list(cate_dict.items()) if v == cate_id][0]

    # build the XML
    mplace = etree.Element("marketplace")
    category = etree.SubElement(mplace, "category", 
                                id=str(cate_id), 
                                name=(cate_dict[cate_id]), 
                                # space obligatory?
                                url=MPLACE.url + "taxonomy/term/" + str(market_id) + "," + str(cate_id))
                                # url=MPLACE.url + "taxonomy/term/" + str(market_id) + ", " + str(cate_id))

    # repeat for those belonging to the same group
    for iu in PLUGINS:
        if int(iu.category) == int(cate_id):
            node = etree.SubElement(category, "node",
                                    id = iu.plugId,
                                    name = iu.human_title,
                                    url = MPLACE.url + "content/" + iu.plugId)
            # do something about this!!
            fav = etree.SubElement(category, "favorited").text = "0"

    return mplace
# def build_mp_taxonomy ends here

def build_mp_node_apip(plug_id, PLUGINS):
    """Return info on installable Unit (i.e. plugin). Get info from the
    CONFIG and from Confluence info page. Input is plug_id, identifier
    of the plugin
    """

    # find out which Plugin we need
    for candidate in PLUGINS:
        if candidate.plugId == plug_id:
            current_plugin = candidate

    node = etree.Element("node", 
                         id = current_plugin.plugId,
                         name = current_plugin.human_title,
                         url = MPLACE.url + "content/" + current_plugin.plugId)

    body_element = etree.SubElement(node, "body").text = etree.CDATA(current_plugin.description)
    # taken from Label of wikipage
    cate_element = etree.SubElement(node, "categories")
    # noch nicht ganz fertig!
    category = etree.SubElement(cate_element, "categories",
                                id = current_plugin.category,
                                name = current_plugin.human_title,
                                url = MPLACE.url + "taxonomy/term/" + MPLACE.mpid + "," + current_plugin.category)
    # how to do that?
    change_element = etree.SubElement(node, "changed").text = "0"
    # constantly TextGrid? can be superseded by plugin-specific entry
    company_element = etree.SubElement(node, "companyname").text = etree.CDATA(current_plugin.company)
    # upload of plugin?, use old values here?
    created_element = etree.SubElement(node, "created").text = "0"
    # what here?
    eclipse_element = etree.SubElement(node, "eclipseversion").text = etree.CDATA("0")
    # would that be ticked on the wiki page?
    fav_element = etree.SubElement(node, "favorited").text = "0"
    # 1 is original value here
    foundation_element = etree.SubElement(node, "foundationmember").text = "1"
    url_element = etree.SubElement(node, "homepageurl").text = etree.CDATA(current_plugin.company_url)
    # icon of plugin
    image_element = etree.SubElement(node, "image").text = etree.CDATA("https://dev2.dariah.eu/wiki/download/attachments/" + current_plugin.pageId + "/" + current_plugin.logo)
    # just a container
    ius_element = etree.SubElement(node, "ius")
    iu_element = etree.SubElement(ius_element, "iu").text = current_plugin.installableUnit
    license_element = etree.SubElement(node, "license").text = current_plugin.license
    # who is the owner? same as company!
    owner_element = etree.SubElement(node, "owner").text = etree.CDATA(current_plugin.owner)
    # what is this about?
    resource_element = etree.SubElement(node, "resource")
    # see logo
    # screenshot would be displayed if we click on more info in marketplace
    if len(current_plugin.screenshot) != 0:
        scrshotEle = etree.SubElement(node, "screenshot").text = etree.CDATA("https://dev2.dariah.eu/wiki/download/attachments/" + current_plugin.pageId + "/" + current_plugin.screenshot)
    # also hidden field?
    update_element = etree.SubElement(node, "updateurl").text = etree.CDATA(current_plugin.update_url)
    return node
# def build_mp_node_apip ends here

def build_mp_frfp_apip(list_type, PLUGINS, mark_id=CONFIG['General']['id']):
    """Take those nodes (my theory here) that have a value of non-nil in
    'featured' (should be on the wiki page) and wraps them into some
    XML. Works also for recent, favorite and popular, they are
    similar. Hence the name of this function.

    This one needs to be fleshed out!
    """

    # the heart of everything. This list contains the plugins to be displayed!
    # controlled by the configuration page in the wiki.
    featured_list = []

    # find out which Plugin we need
    # for now, just display all
    for candidate in PLUGINS:
        featured_list.append(candidate.plugId)
        # if candidate.featured != "N":
        #     # featured_list.append(candidate.plugId)


    mplace = etree.Element("marketplace")
    plugin_list = etree.SubElement(mplace, list_type, count=str(len(featured_list)))
    # make the nodes here as a subElement of the list
    for item in featured_list:
        new_node = build_mp_node_apip(item, PLUGINS)
        plugin_list.insert(1, new_node)

    return mplace
# def build_mp_frfp_apip ends here

def build_mp_content_apip(plug_id, PLUGINS):
    """Return info on a single node. The node_id is """

    mplace = etree.Element("marketplace")
    new_node = build_mp_node_apip(plug_id, PLUGINS)
    mplace.insert(1, new_node)

    return mplace
# def build_mp_content_apip ends here

def build_mp_search_apip(search_string, lopi, PLUGINS):
    """Return nodes matching a search string."""
    # this is a list
    found_plugins = search_files(search_string, lopi)

    mplace = etree.Element("marketplace")
    # part of the specification is also an attribute URL (as in url = "http://what.is.th.is")
    # not sure what that is used for. But works also without.
    search = etree.SubElement(mplace, "search", term = search_string, count = str(len(found_plugins)))

    # make the nodes here as a subElement of the list
    for item in found_plugins:
        # ugly here:
        for plugin in PLUGINS:
            if item == plugin.pageId:
                plugin_id = plugin.plugId
        new_node = build_mp_node_apip(plugin_id, PLUGINS)
        search.insert(1, new_node)

    return mplace
# def build_mp_search_apip ends here

##########
# Output #
##########
def goto_confluence(plug_id, PLUGINS):
    """Redirect the browser to the Confluence page."""

    for candidate in PLUGINS:
        if candidate.plugId == plug_id:
            goto_page = candidate.pageId

    goto_url = WIKI_VIEW + goto_page

    print('Status: 303 See Other')
    # newline is important here
    print('Location: ' + goto_url + '\n')
# def goto_confluence ends here

def goto_main_page(main_page):
    """Redirect the browser to the Confluence page. Doubling code is not good!"""

    goto_url = WIKI_VIEW + main_page

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

    # get the list of plugins
    # lopi: tuple of the page_ids
    lopi, infopage_xml = get_list_of_plugins()

    # arguments need to be read into something that the CGI can deal with
    form = cgi.FieldStorage()

    if form.getvalue('action') == 'cache_reload':
        cache_reload(lopi)
    if form.getvalue('action') == 'knopf':
        cache_reload(lopi)
    if form.getvalue('action') == 'get_updates':
        update_all(lopi)

    else:
        # yay! Plugins!
        PLUGINS = []

        for pgid in lopi:
            PLUGINS.append(build_plugin_info(pgid, infopage_xml, lopi.index(pgid)))

        if form.getvalue('action') == 'main':
            node = build_mp_apip()
            output_xml(node)
        if form.getvalue('action') == 'catalogs':
            node = build_mp_cat_apip()
            output_xml(node)
        if form.getvalue('action') == 'taxonomy':
            node = build_mp_taxonomy(form.getvalue('marketId'), form.getvalue('categoryId'), PLUGINS)
            output_xml(node)
        # list covers all of recent, favorites, popular and featured
        if form.getvalue('action') == 'list':
            if form.getvalue('marketId') != None:
                node = build_mp_frfp_apip(form.getvalue('type'), PLUGINS, form.getvalue('marketId'))
            else:
                node = build_mp_frfp_apip(form.getvalue('type'), PLUGINS)
            output_xml(node)
        if form.getvalue('action') == 'content':
            node = build_mp_content_apip(form.getvalue('plugId'), PLUGINS)
            output_xml(node)
        if form.getvalue('action') == 'search':
            node = build_mp_search_apip(form.getvalue('query'), lopi, PLUGINS)
            output_xml(node)

        if form.getvalue('action') == 'redirect':
            goto_confluence(form.getvalue('plugId'), PLUGINS)
        if form.getvalue('action') == 'goto_wiki':
            goto_main_page(MPLACE.main_wiki_page)

    # really bad error handling, but search functionality has been disabled:
    # search_tab = etree.SubElement(wizard,"searchtab",enabled="0").text = "Search"

if __name__ == "__main__":
    main()

#########
# FINIS #
#########
