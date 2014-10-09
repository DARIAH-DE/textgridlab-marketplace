#!/usr/bin/env python3
# -*- coding: utf-8; mode: python -*-
# Time-stamp: <2014-10-09 15:24:44 (kthoden)>

__author__="Klaus Thoden"
__date__="2014-10-09"
__doc__ = """
A tiny CGI webservice to provide marketplace functionality for
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

###########
# Imports #
###########
import argparse
from lxml import etree
import cgi

# had some big problems with getting the encoding right
# answer on https://stackoverflow.com/questions/9322410/set-encoding-in-python-3-cgi-scripts
# finally did the trick:
# Ensures that subsequent open()s are UTF-8 encoded.
import locale
locale.getpreferredencoding = lambda: 'UTF-8'
import sys                                     
# Re-open standard files in UTF-8 mode.
sys.stdin = open('/dev/stdin', 'r')       
sys.stdout = open('/dev/stdout', 'w')
sys.stderr = open('/dev/stderr', 'w')

# Atlassian namespaces, we don't really use them
# http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
NS={'ri':'http://www.atlassian.com/schema/confluence/4/ri/', 
    'ac':'http://www.atlassian.com/schema/confluence/4/ac/' }

# parse the XML config
config = etree.parse("msConf.xml")

# we somehow need to know here as well which category (external, beta,
# stable) this is in in the tuple first is ID, second the title, third
# the category. We should get this from Confluence
instUnits = {}
for name, idno, longname, cat, confId in zip(config.xpath('//plugin/@name'),config.xpath('//plugin/id'),config.xpath('//plugin/longName'),config.xpath('//plugin/cat'),config.xpath('//plugin/confluenceID')):
    instUnits.update({name:(idno.text,longname.text,cat.text,confId.text)})

#################
# Small helpers #
#################
def findKey(dic,val):
        """A dictionary should be searchable both ways. Thanks to the
        internet for that solution
        """
        return [k for k, v in list(dic.items()) if v == val][0]
# def findKey ends here

def reverseTags(text):
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
    text = re.sub(r'&(?=\s)','&amp;',text)
    return text
# def reverseTags ends here

def unescape(text):
    """With thanks to http://effbot.org/zone/re-sub.htm#unescape-html.
    Modified to work with Python3."""
    import re,html.entities

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
    return re.sub("&#?\w+;", fixup, text)
# def unescape ends here

####################
# Confluence stuff #
####################
def getConfluencePluginData(plugId):
    """Get info about the plugins from the Confluence pages. The plugId
    is found in the config file."""
    import urllib.request, urllib.parse, urllib.error
    import sys

    baseURL = "https://dev2.dariah.eu/wiki/rest/prototype/1/content/"
    fullpath = baseURL + plugId

    usock=urllib.request.urlopen(fullpath)

    try:
        pluginInfo = etree.parse(usock)
    except etree.XMLSyntaxError:
        sys.exit()
    usock.close()

    return pluginInfo
## def getConfluencePluginData ends here

def parseConfluenceBody(codedBody):
    """Parse the page returned by getConfluencePluginData, fix the code
    and read the relevant bits into XML again."""
    # some ugly modifications
    clean = reverseTags(codedBody)
    clean = unescape(clean)

    bodyInfo = etree.fromstring(clean)

    return bodyInfo
## def parseConfluenceBody ends here

def compileInfo(pluginData):
    """Return a dictionary of the things parsed out of the webpage"""

    # these are the guts we need
    pluginBody = pluginData.xpath('/content/body')[0].text
    pluginTable = parseConfluenceBody(pluginBody)

    pluginDict = dict({
        "plTitle" : pluginTable.xpath('/table/tbody/tr[1]/td')[0].text,
        "plDesc" : pluginTable.xpath('/table/tbody/tr[2]/td')[0].text,
        "plIcon" : pluginTable.xpath('/table/tbody/tr[3]/td/image/attachment/@filename')[0],
        "plMaturity" : pluginTable.xpath('/table/tbody/tr[4]/td/structured-macro/parameter[@name="colour"]')[0].text,
        "plReq" : pluginTable.xpath('/table/tbody/tr[5]/td')[0].text,
        # OBS, license needs not be a link
        "plLicense" : pluginTable.xpath('/table/tbody/tr[6]/td/a')[0].text,
        "plSource" : pluginTable.xpath('/table/tbody/tr[7]/td/a')[0].text,
        "plProjects" : pluginTable.xpath('/table/tbody/tr[8]/td')[0].text,
        "plFiles" : pluginTable.xpath('/table/tbody/tr[9]/td')[0].text
    })
    return pluginDict
# def compileInfo ends here

#############################################
# Here starts the building of the XML nodes #
#############################################

def buildMPapiP():
    """Return info about the whole marketplace. Which categories are in there?"""

    # parsing the config file
    msId = config.xpath('//general/id')[0].text
    msName = config.xpath('//general/name')[0].text
    msUrl = config.xpath('//general/url')[0].text

    # building the XML
    mplace = etree.Element("marketplace")
    market = etree.SubElement(mplace,"market", id=msId, name=msName, url=msUrl+"category/markets/"+msId)

    catCount=1

    cat = config.xpath('//category')
    catId = config.xpath('//category/@id')

    # iterating through the categories
    for catKey,catVal in zip(cat,catId):
        etree.SubElement(market,"category",count=str(catCount), id=catVal,name=catKey.text, url=str(msUrl)+"taxonomy/term/"+msId+","+catKey.text)
        catCount += 1
    return mplace
# def buildMPapiP ends here

def buildMPcatApiP():
    """Return information on a catalog. According to server log, this is
    the first thing the Lab looks for. Requires only info from config
    file. After choosing that catalog, the root is called.
    """
    # read from config
    msId = config.xpath('//general/id')[0].text
    msName = config.xpath('//general/name')[0].text
    msUrl = config.xpath('//general/url')[0].text
    msTitle = config.xpath('//general/title')[0].text
    msIcon = config.xpath('//general/icon')[0].text

    # build the XML
    mplace = etree.Element("marketplace")
    catalogs = etree.SubElement(mplace,"catalogs")
    catalog = etree.SubElement(catalogs,"catalog", id=msId, title=msTitle, url=msUrl, selfContained="1",icon=msUrl+msIcon)
    desc = etree.SubElement(catalog,"description").text = "The features of TextGrid"
    depRep = etree.SubElement(catalog,"dependenciesRepository")
    wizard = etree.SubElement(catalog,"wizard", title="")
    icon = etree.SubElement(wizard,"icon")
    sTab = etree.SubElement(wizard,"searchtab",enabled="0").text = "Search"
    popTab = etree.SubElement(wizard,"populartab",enabled="1").text = "Popular"
    recTab = etree.SubElement(wizard,"recenttab",enabled="0").text = "Recent"
    return mplace
# def buildMPcatApiP ends here

def buildMPtaxonomy(marID,catID,instUnits):
    """Construct the taxonomy. List all plugins of one category. The
    category a plugin belongs to is taken from the config."""

    msUrl = config.xpath('//general/url')[0].text

    # small dictionary for handling the category name and id
    catDict = {}
    for catKey,catVal in zip(config.xpath('//category'),config.xpath('//category/@id')):
        catDict.update({catVal:catKey.text})

    # a small detour, because we might get the name value of the category instead of the ID
    if catID in [v for k, v in list(catDict.items())]:
        catID = findKey(catDict,catID)

    # build the XML
    mplace = etree.Element("marketplace")
    category = etree.SubElement(mplace,"category",id=str(catID),name=(catDict[catID]),url=msUrl+"taxonomy/term/"+str(marID)+","+str(catID))
    # repeat for thoese belonging to the same group
    for iu in instUnits.items():
        if int(iu[1][2]) == int(catID):
            node = etree.SubElement(category,"node",id=iu[1][0],name=iu[1][1],url=msUrl+"content/"+iu[1][0])
            fav = etree.SubElement(category,"favorited").text = "0"
    return mplace
# def buildMPtaxonomy ends here

def buildMPnodeApiP(instUnits,plugName):
    """Return info on installable Unit (i.e. plugin). Totally un-finished"""
    msUrl = config.xpath('//general/url')[0].text
    msId = config.xpath('//general/id')[0].text

    # here we get the info about the plugin! returns a dictionary full of stuff
    plugId = instUnits[plugName][3]
    rawXML = getConfluencePluginData(plugId)
    plug = compileInfo(rawXML)

    node = etree.Element("node",id=instUnits[plugName][0], name=instUnits[plugName][1], url=msUrl+"content/"+instUnits[plugName][0])

    bodyEle = etree.SubElement(node,"body").text = etree.CDATA(plug["plDesc"])
    # taken from Label of wikipage
    catEle = etree.SubElement(node,"categories")
    # noch nicht ganz fertig!
    category = etree.SubElement(catEle,"categories",id=instUnits[plugName][2],name=instUnits[plugName][1],url=msUrl+"taxonomy/term/"+msId+","+instUnits[plugName][2])
    # how to do that?
    changeEle = etree.SubElement(node,"changed").text = "0"
    # constantly TextGrid?
    companyEle = etree.SubElement(node,"companyname").text = etree.CDATA("TextGrid")
    # upload of plugin?, use old values here?
    creatEle = etree.SubElement(node,"created").text = "0"
    # what here?
    eclipseEle = etree.SubElement(node,"eclipseversion").text = etree.CDATA("0")
    # would that be ticked on the wiki page?
    favEle = etree.SubElement(node,"favorited").text = "0"
    # 1 is original value here
    foundationEle = etree.SubElement(node,"foundationmember").text = "1"
    urlEle = etree.SubElement(node,"homepageurl").text = etree.CDATA("http://www.textgrid.de")
    imageEle = etree.SubElement(node,"image").text = etree.CDATA("https://dev2.dariah.eu/wiki/download/attachments/" + plugId + "/" + plug["plIcon"])
    # just a container
    iusEle = etree.SubElement(node,"ius")
    # where to store that information?
    # iuEle = etree.SubElement(iusEle,"iu").text = "info.textgrid.lab.%s.feature.feature.group" % plugName
    iuEle = etree.SubElement(iusEle,"iu").text = "de.mpg.mpiwg.itgroup.textgrid.%s.feature.feature.group" % plugName
    licenseEle = etree.SubElement(node,"license").text = plug["plLicense"]
    # who is the owner?
    ownerEle = etree.SubElement(node,"owner").text = "TextGrid"
    # what is this about?
    resourceEle = etree.SubElement(node,"resource") # this?
    # see logo
    #scrshotEle = etree.SubElement(node,"screenshot").text = "https://develop.sub.uni-goettingen.de/repos/textgrid/trunk/lab/noteeditor/info.textgrid.lab.noteeditor.feature/Screenshot_MEISE_2012-04-20.png"
    # also hidden field?
    updateEle = etree.SubElement(node,"updateurl").text = etree.CDATA("http://download.digital-humanities.de/updates/textgridlab/" + plugName)

    return node
# def buildMPnodeApiP ends here

def buildMPfrfpApiP(listType,mId=config.xpath('//general/id')[0].text):
    """Take those nodes (my theory here) that have a value of non-nil in
    'featured' (should be on the wiki page) and wraps them into some
    XML. Works also for recent, favorite and popular, they are
    similar. Hence the name of this function.
    """
    # this list needs to be somewhat dynamic
    featuredList = ["digilib"]

    mplace = etree.Element("marketplace")
    plugList = etree.SubElement(mplace,listType,count=str(len(featuredList)))
    # make the nodes here as a subElement of the list
    for i in featuredList:
        xxx = buildMPnodeApiP(instUnits,i)
        plugList.insert(1,xxx)

    return mplace
# def buildMPfrfpApiP ends here

def buildMPcontentApiP(nodeId,instUnits):
    """Return info on a single node."""

    auxdic = dict()
    for iu in instUnits.items():
        auxdic.update({iu[1][0] : iu[0]})

    mplace = etree.Element("marketplace")
    xxx = buildMPnodeApiP(instUnits,auxdic[nodeId])
    mplace.insert(1,xxx)

    return mplace
# def buildMPcontentApiP ends here


##########
# Output #
##########
def goToConfluence(nodeId,instUnits):
    """Redirect the browser to the Confluence page."""

    auxdic = dict()
    for iu in instUnits.items():
        auxdic.update({iu[1][0] : iu[1][3]})

    gotoURL = "https://dev2.dariah.eu/wiki/pages/viewpage.action?pageId=" + auxdic[nodeId]    

    print('Status: 303 See Other')
    # newline is important here
    print('Location: ' + gotoURL + '\n')
# def goToConfluence ends here

def outputXML(node):
    """Serve the XML for the Marketplace. Here you go."""
    # output
    print('Content type: text/xml; charset=utf-8\n')
    # this is of a bytes type
    son = etree.tostring(node,pretty_print=True,encoding='utf-8',xml_declaration=True)
    # convert this to a string
    outDecode = son.decode('utf-8')
    # for debugging
    print(outDecode)
# def outputXML ends here

################
# The main bit #
################
def main():
    parser = argparse.ArgumentParser()
    msActions = parser.add_mutually_exclusive_group()
    msActions.add_argument("-a","--action",help="call the function",action="store_true")

    # other arguments that we might somewhat use but so far don't
    parser.add_argument("-ty","--type",help="type of list to be generated")
    parser.add_argument("-cid","--categoryId",help="ID of category")
    parser.add_argument("-mid","--marketId",help="ID of market")
    parser.add_argument("-ti","--title",help="title of a plugin?")
    parser.add_argument("-no","--nodeTitle",help="title of a node?")
    parser.add_argument("-q","--query",help="query string")

    # We should maybe catch and retain all those things the client tells us:
    # product=info.textgrid.lab.core.application.base_product
    # os=macosx
    # runtime.version=3.7.0.v20110110
    # client=org.eclipse.epp.mpc.core
    # java.version=1.6.0_65
    # product.version=0.0.2.201310011243
    # ws=cocoa
    # nl=de_DE

    parser.add_argument("--product")
    parser.add_argument("--os")
    parser.add_argument("--runtime.version")
    parser.add_argument("--client")
    parser.add_argument("--java.version")
    parser.add_argument("--product.version")
    parser.add_argument("--ws",help="returns cocoa in case of apple")
    parser.add_argument("--nl",help="Language")

    args=parser.parse_args()

    # arguments need to be read into something that the CGI can deal with
    form = cgi.FieldStorage()
    if form.getvalue('action') == 'main':
        node = buildMPapiP()
        outputXML(node)
    if form.getvalue('action') == 'catalogs':
        node = buildMPcatApiP()
        outputXML(node)
    if form.getvalue('action') == 'taxonomy':
        node = buildMPtaxonomy(form.getvalue('marketId'),form.getvalue('categoryId'),instUnits)
        outputXML(node)
    # list covers all of recent, favorites, popular and featured
    if form.getvalue('action') == 'list':
        if form.getvalue('marketId') != None:
            node = buildMPfrfpApiP(form.getvalue('type'),form.getvalue('marketId'))
        else:
            node = buildMPfrfpApiP(form.getvalue('type'))
        outputXML(node)
    if form.getvalue('action') == 'content':
        node = buildMPcontentApiP(form.getvalue('nodeId'),instUnits)
        outputXML(node)
    if form.getvalue('action') == 'redirect':
        goToConfluence(form.getvalue('nodeId'),instUnits)

    # I think, node can be redirected to content. Did so in htaccess file.
    # if form.getvalue('action') == 'node':
    #     node = "not yet implemented"

    # really bad error handling, but search functionality has been disabled:
    # sTab = etree.SubElement(wizard,"searchtab",enabled="0").text = "Search"
    if form.getvalue('action') == 'search':
        node = "not yet implemented"

if __name__ == "__main__":
    main()

#########
# FINIS #
#########
