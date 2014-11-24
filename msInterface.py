#!/usr/bin/env python3
# -*- coding: utf-8; mode: python -*-

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

"""

# what is the license??

__author__ = "Klaus Thoden"
__date__ = "2014-11-24"

###########
# Imports #
###########
from lxml import etree
import cgi

# had some big problems with getting the encoding right
# answer on https://stackoverflow.com/questions/9322410/set-encoding-in-python-3-cgi-scripts
# finally did the trick:
# Ensures that subsequent open()s are UTF-8 encoded.
# Mind you, this is dependant on the server it is running on!
import locale
locale.getpreferredencoding = lambda: 'UTF-8'
import sys
# Re-open standard files in UTF-8 mode.
sys.stdin = open('/dev/stdin', 'r')
sys.stdout = open('/dev/stdout', 'w')
sys.stderr = open('/dev/stderr', 'w')

# Atlassian namespaces, we don't really use them
# http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
NS = {'ri':'http://www.atlassian.com/schema/confluence/4/ri/',
      'ac':'http://www.atlassian.com/schema/confluence/4/ac/'}

# parse the XML config
CONFIG = etree.parse("msConf.xml")

# we somehow need to know here as well which category (external, beta,
# stable) this is in in the tuple first is ID, second the title, third
# the category. We should get this from Confluence
INST_UNITS = {}
for name, idno, longname, cat, conf_id, inst_unit in zip(CONFIG.xpath('//plugin/@name'), CONFIG.xpath('//plugin/id'), CONFIG.xpath('//plugin/longName'), CONFIG.xpath('//plugin/cat'), CONFIG.xpath('//plugin/pageID'), CONFIG.xpath('//plugin/installableUnit')):
    INST_UNITS.update({name:(idno.text, longname.text, cat.text, conf_id.text, inst_unit.text)})

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
    """With thanks to http://effbot.org/zone/re-sub.htm#unescape-html.
    Modified to work with Python3."""
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
def get_confluence_plugin_data(plugin_id):
    """Get info about the plugins from the Confluence pages. The plugId
    is found in the config file."""
    import urllib.request, urllib.parse, urllib.error

    base_url = "https://dev2.dariah.eu/wiki/rest/prototype/1/content/"
    fullpath = base_url + plugin_id

    usock = urllib.request.urlopen(fullpath)

    try:
        plugin_info = etree.parse(usock)
    except etree.XMLSyntaxError:
        sys.exit()
    usock.close()

    return plugin_info
## def get_confluence_plugin_data ends here

def parse_confluence_body(coded_body):
    """Parse the page returned by get_confluence_plugin_data, fix the code
    and read the relevant bits into XML again."""
    # some ugly modifications
    clean = reverse_tags(coded_body)
    clean = unescape(clean)

    body_info = etree.fromstring(clean)

    return body_info
## def parse_confluence_body ends here

def compile_info(plugin_data):
    """Return a dictionary of the things parsed out of the webpage. The
    table we are parsing needs to be in a strict order concerning the
    first four elements: title, description, logo, license
    """

    # these are the guts we need
    plugin_body = plugin_data.xpath('/content/body')[0].text
    plugin_table = parse_confluence_body(plugin_body)

    plugin_dict = dict({
        "pl_title" : plugin_table.xpath('/table/tbody/tr[1]/td')[0].text,
        "pl_desc" : plugin_table.xpath('/table/tbody/tr[2]/td')[0].text,
        "pl_icon" : plugin_table.xpath('/table/tbody/tr[3]/td/image/attachment/@filename')[0],
        # license needs not be a link
        "pl_license" : plugin_table.xpath('/table/tbody/tr[4]/td/a')[0].text
    })
    return plugin_dict
# def compile_info ends here

#############################################
# Here starts the building of the XML nodes #
#############################################
def build_mp_apip():
    """Return info about the whole marketplace. Which categories are in there?"""

    # parsing the config file
    ms_id = CONFIG.xpath('//general/id')[0].text
    ms_name = CONFIG.xpath('//general/name')[0].text
    ms_url = CONFIG.xpath('//general/url')[0].text

    # building the XML
    mplace = etree.Element("marketplace")
    market = etree.SubElement(mplace, "market", id=ms_id, name=ms_name, url=ms_url+"category/markets/"+ms_id)

    categ = CONFIG.xpath('//category')
    cat_id = CONFIG.xpath('//category/@id')

    # iterating through the categories
    cat_count = 1
    for cat_key, cat_val in zip(categ, cat_id):
        etree.SubElement(market, "category", count=str(cat_count), id=cat_val, name=cat_key.text, url=str(ms_url)+"taxonomy/term/"+ms_id+", "+cat_key.text)
        cat_count += 1
    return mplace
# def build_mp_apip ends here

def build_mp_cat_apip():
    """Return information on a catalog. According to server log, this is
    the first thing the Lab looks for. Requires only info from config
    file. After choosing that catalog, the root is called.
    """
    # read from config
    ms_id = CONFIG.xpath('//general/id')[0].text
    ms_url = CONFIG.xpath('//general/url')[0].text
    ms_title = CONFIG.xpath('//general/title')[0].text
    ms_icon = CONFIG.xpath('//general/icon')[0].text
    ms_desc = CONFIG.xpath('//general/description')[0].text

    # build the XML
    mplace = etree.Element("marketplace")
    catalogs = etree.SubElement(mplace, "catalogs")
    catalog = etree.SubElement(catalogs, "catalog", id=ms_id, title=ms_title, url=ms_url, selfContained="1", icon=ms_url+ms_icon)
    desc = etree.SubElement(catalog, "description").text = ms_desc
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

    ms_url = CONFIG.xpath('//general/url')[0].text

    # small dictionary for handling the category name and id
    cate_dict = {}
    for cat_key, cat_val in zip(CONFIG.xpath('//category'), CONFIG.xpath('//category/@id')):
        cate_dict.update({cat_val:cat_key.text})

    # a small detour, because we might get the name value of the category instead of the ID
    if cate_id in [v for k, v in list(cate_dict.items())]:
        cate_id = find_key(cate_dict, cate_id)

    # build the XML
    mplace = etree.Element("marketplace")
    category = etree.SubElement(mplace, "category", id=str(cate_id), name=(cate_dict[cate_id]), url=ms_url+"taxonomy/term/"+str(market_id)+", "+str(cate_id))
    # repeat for thoese belonging to the same group
    for i_unit in INST_UNITS.items():
        if int(i_unit[1][2]) == int(cate_id):
            node = etree.SubElement(category, "node", id=i_unit[1][0], name=i_unit[1][1], url=ms_url+"content/"+i_unit[1][0])
            fav = etree.SubElement(category, "favorited").text = "0"
    return mplace
# def build_mp_taxonomy ends here

def build_mp_node_apip(plug_name):
    """Return info on installable Unit (i.e. plugin)."""
    ms_url = CONFIG.xpath('//general/url')[0].text
    ms_id = CONFIG.xpath('//general/id')[0].text

    # here we get the info about the plugin! returns a dictionary full of stuff
    plugin_id = INST_UNITS[plug_name][3]
    raw_xml = get_confluence_plugin_data(plugin_id)
    plug = compile_info(raw_xml)

    node = etree.Element("node", id=INST_UNITS[plug_name][0], name=INST_UNITS[plug_name][1], url=ms_url+"content/"+INST_UNITS[plug_name][0])

    body_element = etree.SubElement(node, "body").text = etree.CDATA(plug["pl_desc"])
    # taken from Label of wikipage
    cate_element = etree.SubElement(node, "categories")
    # noch nicht ganz fertig!
    category = etree.SubElement(cate_element, "categories", id=INST_UNITS[plug_name][2], name=INST_UNITS[plug_name][1], url=ms_url+"taxonomy/term/"+ms_id+","+INST_UNITS[plug_name][2])
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

def build_mp_frfp_apip(list_type, mark_id=CONFIG.xpath('//general/id')[0].text):
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
    son = etree.tostring(node, pretty_print=True, encoding='utf-8', xml_declaration=True)
    # convert this to a string
    out_decode = son.decode('utf-8')
    # for debugging
    print(out_decode)
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
