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
__date__ = "2017-05-19"

###########
# Imports #
###########
import os
import logging
import yaml
import requests
from configparser import ConfigParser
from lxml import etree
from yaml.loader import BaseLoader

from fastapi import FastAPI, Path, Response, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# setting up things
# both config and cache directory are in the same place as this script
CONFIG = ConfigParser()
CONFIG.read('default.conf')

# override config from the general section from environment, for configuration inside docker.
# environment variables starting with MS_GENERAL_ are mapped, example:
#   MS_GENERAL_LOGFILE -> CONFIG['General']['logfile']
env_vars=os.environ
for key in env_vars:
  if(key.startswith("MS_GENERAL_")):
    confkey=key[11:].lower()
    confval=env_vars[key]
    CONFIG.set("General", confkey, confval)

LOGFILE = CONFIG['General']['logfile']
LOGLEVEL = CONFIG['General']['loglevel']

numeric_level = getattr(logging, LOGLEVEL.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)
logging.basicConfig(filename=LOGFILE, level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')

WIKI_VIEW = CONFIG['General']['wiki_view']

# adaptable XPath for info that is parsed out of the confluence page
# was /pluginInfo/table/
PLUGIN_INFO_TABLE_XPATH = "/pluginInfo//table[1]/"

HEADERLINE = 'Content-Type: text/%s; charset=utf-8\n'

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
                 featured = False,
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
        self.plugId = str(plugId)
        self.featured = featured
        self.name = name
        self.category = str(category)
        self.pageId = str(pageId)
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

################
# YAML parsing #
################
def plugin_constructor(loader, node):
    fields = loader.construct_mapping(node)
    return PlugIn(**fields)

yaml.add_constructor('!PlugIn', plugin_constructor)

def load_data():
    with open('data.yaml', 'r', encoding='utf-8') as stream:
        PLUGINS = yaml.load(stream, Loader=yaml.FullLoader)
    return PLUGINS
    
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

/apachesolr_search/k%C3%B6nnen?filters=tid:tg0120%20tid:5&product=
nur MS ausgewählt
/~kthoden/m3/api/p/search/apachesolr_search/musik?filters=tid:tg0120&product=info
nur Kategorie
/~kthoden/m3/api/p/search/apachesolr_search/musik?filters=tid:5&produc
beide
/~kthoden/m3/api/p/search/apachesolr_search/musik?filters=tid:tg0120%20tid:5&produ

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
                              url=MPLACE.url + "/category/markets/" + MPLACE.mpid)

    categ = list(CONFIG['Categories'].values())
    cat_id = list(CONFIG['Categories'].keys())

    # Iterating through the categories
    cat_count = 1
    for cat_key, cat_val in zip(categ, cat_id):
        etree.SubElement(market, "category", 
                         count=str(cat_count), 
                         id=cat_val, 
                         name=cat_key, 
                         url=str(MPLACE.url) + "/taxonomy/term/" + MPLACE.mpid + "," + cat_key)
                         # is the space after mpid+","+cat_key) obligatory???
                         # url=str(MPLACE.url) + "/taxonomy/term/" + MPLACE.mpid + ", " + cat_key)
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
                               icon=MPLACE.url + "/" + MPLACE.icon)
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
                                url=MPLACE.url + "/taxonomy/term/" + str(market_id) + "," + str(cate_id))
                                # is the space after mpid+","+cat_key) obligatory???
                                # url=MPLACE.url + "/taxonomy/term/" + str(market_id) + ", " + str(cate_id))

    # repeat for those belonging to the same group
    for iu in PLUGINS:
        if int(iu.category) == int(cate_id):
            node = etree.SubElement(category, "node",
                                    id = iu.plugId,
                                    name = iu.human_title,
                                    url = MPLACE.url + "/content/" + iu.plugId)
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
                         url = MPLACE.url + "/content/" + current_plugin.plugId)

    body_element = etree.SubElement(node, "body").text = etree.CDATA(current_plugin.description)
    # taken from Label of wikipage
    cate_element = etree.SubElement(node, "categories")
    # noch nicht ganz fertig!
    category = etree.SubElement(cate_element, "categories",
                                id = current_plugin.category,
                                name = current_plugin.human_title,
                                url = MPLACE.url + "/taxonomy/term/" + MPLACE.mpid + "," + current_plugin.category)
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
    if current_plugin.logo.startswith('http'):
        image_element = etree.SubElement(node, "image").text = etree.CDATA(current_plugin.logo)
    else:
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
def xmlresponse(node):
    xml = etree.tostring(node, pretty_print=True, encoding='utf-8', xml_declaration=True)
    return Response(content=xml, media_type='text/xml')


##########
# routes #
##########
app = FastAPI(
    title="TextGridLab Marketplace",
    description="This is the API for the TextGridLab Marketplace, an implementation of the [Eclipse Marketplace API](https://wiki.eclipse.org/Marketplace/REST)",
    version="2.0.0",
)

# define xml response content type for openapi
xmlresponsedef = {
  200: {
    "content": {
      "text/xml": {}
    }
  },
  422: {
    "description": "Validation Error",
    "content": {
      "text/plain": {}
    }
  }
}

@app.get(
  "/api/p", 
  summary="List Markets and Categories",
  description="""This will return a listing of Markets and Categories, it includes URLs for each category, as well number of listings in each category.
    See [Retrieving A listing of Markets and Categories](https://web.archive.org/web/20200220202907/https://wiki.eclipse.org/Marketplace/REST#Retrieving_A_listing_of_Markets_and_Categories)""",
  response_class=Response,
  responses=xmlresponsedef
)
def main_api_p():
    node = build_mp_apip()
    return xmlresponse(node)


@app.get("/catalogs/api/p",   
  summary="List all Catalogs",
  description="""This will return a listing of all catalogs that are browsable with the MPC. It also includes basic branding parameters, 
    like title and icon and strategies resolving dependencies.
    See [Retrieving a listing of all catalogs](https://web.archive.org/web/20200220202907/https://wiki.eclipse.org/Marketplace/REST#Retrieving_a_listing_of_all_catalogs)""",
  response_class=Response,
  responses=xmlresponsedef
)
def catalogs_api_p():
    node = build_mp_cat_apip()
    return xmlresponse(node)


@app.get("/taxonomy/term/{market_id},{category_id}/api/p",
  summary="Listings from a specific Market / Category",
  response_class=Response,
  responses=xmlresponsedef)
def taxonomy_term_api_p(
  market_id = Path(..., example="tg01"),
  category_id = Path(..., example="stable")):
    PLUGINS = load_data()
    node = build_mp_taxonomy(market_id, category_id, PLUGINS)
    return xmlresponse(node)


@app.get("/node/{plugin_id}/api/p", 
  summary="Specific Listing",
  response_class=Response,
  responses=xmlresponsedef)
def show_node_api_p(plugin_id = Path(..., example="1")):
    PLUGINS = load_data()
    node = build_mp_content_apip(plugin_id, PLUGINS)
    return xmlresponse(node)


@app.get("/content/{plugin_id}/api/p", 
  summary="Specific Listing",
  response_class=Response,
  responses=xmlresponsedef)
def show_content_api_p(plugin_id = Path(..., example="1")):
    PLUGINS = load_data()
    node = build_mp_content_apip(plugin_id, PLUGINS)
    return xmlresponse(node)


@app.get("/{ltype}/api/p",
  summary="Listing featured",
  response_class=Response,
  responses=xmlresponsedef)
def list_type_api_p(ltype = Path(..., example="featured")):
    PLUGINS = load_data()
    node = build_mp_frfp_apip(ltype, PLUGINS)
    return xmlresponse(node)


@app.get("/{ltype}/{market_id}/api/p", 
  summary="Listing featured for a specific market",
  response_class=Response,
  responses=xmlresponsedef)
def list_type_market_api_p(
  ltype = Path(..., example="featured"), 
  market_id = Path(..., example="tg01")):
    PLUGINS = load_data()
    node = build_mp_frfp_apip(ltype, PLUGINS, market_id)
    return xmlresponse(node)



@app.get("/check",
  summary="Check update site URLs",
  response_class=Response,
  responses={
    200: { "description": "All update site URLS ok" },
    500: { "description": "At least one update site URL failed" },
  })
def check_urls():
    """Check all update site URLs from data.yaml, return 500 in case of failures."""
    PLUGINS = load_data()
    urls = set() # a set, so we check every url only once
    broken = set()
    for plugin in PLUGINS:
        urls.add(plugin.update_url)
    for url in urls:
        r = requests.get(url)
        if r.status_code != 200:
            broken.add(url)
    if len(broken) > 0:
        #return Response(content="Failed update site URLs: " + ", ".join(broken), status=500)
        raise HTTPException(status_code=500, detail="Failed update site URLs: " + ", ".join(broken))
    else:
        return "All update site URLS ok"


######################
# exception handlers #
######################

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
  """Custom 404 page and plaintext response for exceptions."""
  if(exc.status_code == 404):
    #return 
    html_content = """
      <html>
          <head>
              <title>Not Found</title>
          </head>
          <body>
              <h1>Method not found, check the <a href="/docs">interactive</a> or the <a href="/redoc">redoc</a> API documentation.</h1>
          </body>
      </html>
      """
    return HTMLResponse(content=html_content, status_code=404)
  else:
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
  """Return plaintext for validation errors"""
  return PlainTextResponse(str(exc), status_code=422)

#########
# FINIS #
#########
