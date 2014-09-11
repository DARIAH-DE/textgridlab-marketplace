#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2014-07-30 11:47:30 (kthoden)>

__author__="Klaus Thoden"
__date__="2014-03-13"
__doc__ = """Getting a page out of the Confluence system and convert it to
something the Eclipse Marketplace understands.
https://dev2.dariah.eu/wiki/rest/prototype/1/content/27329537

Do we need content negotiation?
If the Lab calls, redirect it to /api/p and deliver the XML
A browser might want to go to $MS/content/3 and expects the plugin info there

For the pages to be served by the service then, we need several inputs:
- the data parsed out of the corresponding wiki pages
- a config file
- some other stuff?

The Lab sends a request. In my theory, it will first end in $MS/api/p where it gets information about:
- msID
- msName
- the categories with id and name and a generated url pointing to the taxonomies

we can browse that url. taxonomy knows about
- who is in that group
- their internal id
- human readable name
- link to that node

that link (content) knows everything and more.

what about the catalogs?
This simply has to be there, I think

Things to put on the server
- directory with image files

Query by Eclipse looks like this:
http://ocropus.rz-berlin.mpg.de/~kthoden/marketplace/featured/6/api/p?product=info.textgrid.lab.core.application.base_product&os=macosx&runtime.version=3.7.0.v20110110&client=org.eclipse.epp.mpc.core&java.version=1.6.0_65&product.version=0.0.2.201310011243&ws=cocoa&nl=de_DE

We should maybe catch and retain all those arguments:
product=info.textgrid.lab.core.application.base_product
os=macosx
runtime.version=3.7.0.v20110110
client=org.eclipse.epp.mpc.core
java.version=1.6.0_65
product.version=0.0.2.201310011243
ws=cocoa
nl=de_DE

Reference: http://wiki.eclipse.org/Marketplace/REST

        - [X] $baseURL/api/p :: listing of markets and categories: http://textgridlab.org/marketplace/api/p
        - [ ] $baseURL/catalogs/api/p :: obtain all available catalogs: http://textgridlab.org/marketplace/catalogs/api/p
        - [ ] $baseURL/taxonomy/term/[category id],[market id]/api/p :: listing
             of a specific market and category: http://textgridlab.org/marketplace/taxonomy/term/8a207eea3542f8b9013542f8f0d40001,6/api/p
        - [ ] $baseURL/content/[title]/api/p :: return a specific listing: http://textgridlab.org/marketplace/
        - [ ] $baseURL/node/[node id]/api/p :: return a specific listing: http://textgridlab.org/marketplace/
        - [ ] $baseURL/api/p/search/apachesolr_search/[query]?page=[page num]&filters=[filters] :: Return
             search results: http://textgridlab.org/marketplace/
        - [X] $baseURL/featured/api/p :: List of Featured listings: http://textgridlab.org/marketplace/featured/api/p
        - [X] $baseURL/recent/api/p :: Recently updated or added listings: http://textgridlab.org/marketplace/recent/api/p
        - [X] $baseURL/favorites/top/api/p :: most favourite things: http://textgridlab.org/marketplace/favorites/top/api/p
        - [X] $baseURL/popular/top/api/p :: most popular by activity: http://textgridlab.org/marketplace/popular/top/api/p

put info on installable Units also in config
config should be kept in XML.
"""

# imports
from lxml import etree
import configparser
import argparse
from datetime import datetime

# Atlassian namespaces
# http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
NS={'ri':'http://www.atlassian.com/schema/confluence/4/ri/', 
    'ac':'http://www.atlassian.com/schema/confluence/4/ac/' }

config = configparser.ConfigParser()
config.read("ms.conf")

# we somehow need to know here as well which category (external, beta, stable) this is in
# in the tuple first is ID, second the title, third the category. We should get this from Confluence
# put this into config XML file
instUnits = dict(
    {"linguistics" : ("7","Linguistic Tools","4"), 
     "ttle" : ("8","Text Text Linkeditor","2"), 
     "collatex": ("4","CollateX","2"), 
     "noteeditor" : ("2","MEISE Noteneditor","4"), 
     "sadepublish" : ("1","SADE Publish Tool","2"), 
     "digilib" : ("3","DigiLib","4"), 
     "oxygen" : ("5","Oxygen XML Editor","6")
     # missing?
     # "glosses" : (), 
     # "base-extras",
})

def getConfluencePluginData(state="offline"):
    """
    Use python's lxml to get the Plugin pages from Confluence.
    REST documentation on https://docs.atlassian.com/atlassian-confluence/REST/latest/

    using curl, I can access restricted pages via command line:

    curl -u KlausThoden -X GET https://dev2.dariah.eu/wiki/rest/prototype/1/content/27329537

    """
    import urllib.request, urllib.parse, urllib.error
    import sys

    if state=="offline":
        baseURL = "file:///home/klaus/tmp/FUCKYOU/Marketsplace/dev/"
        # baseURL = "file:///Users/kthoden/TextGrid/Marketsplace/dev/"
        ID = "27329537"
    else:
        baseURL = "https://dev2.dariah.eu/wiki/rest/prototype/1/content/"
        ID = "27329537" # digilib, not yet accessible through script, as I am not logged in
        # ID = "9012111"

    fullpath = baseURL + ID

    sys.stdout.write("Getting info from %s.\n"% fullpath)
    usock=urllib.request.urlopen(fullpath)
    # try:
    #     usock=urllib.request.urlopen(fullpath)
    # except:
    #     sys.stderr.write("not working, mate\n")
    #     sys.exit()

    try:
        pluginInfo = etree.parse(usock)
    except etree.XMLSyntaxError:
        print("Online resource %s not found." % fullpath)
        sys.exit()
    usock.close()

    return pluginInfo
## def getConfluencePluginData ends here

def reverseTags(text):
    """Escape html entities, just in case."""
    import re

    replacements = {
        '&amp;' : '&',
        '&lt;' : '<',
        '&gt;' : '>',
        '&quot;' : '"',
        '&apos;' : "'",
        '&uuml;' : 'ü',
        '&auml;' : 'ä',
        '&ouml;' : 'ö',
        '&nbsp;' : ' ',
        '&ndash;' : '–',
        '&larr;' : "←",
        'ac:' : '',
        'ri:' : ''
    }

    for thing in list(replacements.keys()):
        text = text.replace(thing, replacements[thing])
    text = re.sub(r'&(?=\s)','&amp;',text)
    return text
# def reverseTags ends here

def parseConfluenceBody(codedBody):
    """Body needs to be transformed a bit."""
    # some ugly modifications
    clean = reverseTags(codedBody)
    bodyInfo = etree.fromstring(clean)

    return bodyInfo
## def parseConfluenceBody ends here

def compileInfo(pluginData):
    """Return a dictionary of the things we parsed out of the webpage"""
    pluginTitle = pluginData.xpath('/content/title')[0].text
    print("""Title of the page is %s""" % pluginTitle)

    pluginBody = pluginData.xpath('/content/body')[0].text

    # tonic = etree.XML(pluginBody,nsmap=NS)
    # print(tonic)

    gingerAle = parseConfluenceBody(pluginBody)
    # print(gingerAle.xpath('//h1')[0].text)
    # print("""Title taken from the body: %s""" % plTitle)
    pluginDict = dict({
        "plTitle" : gingerAle.xpath('/table/tbody/tr[1]/td')[0].text,
        "plDesc" : gingerAle.xpath('/table/tbody/tr[2]/td')[0].text,
        "plIcon" : gingerAle.xpath('/table/tbody/tr[3]/td/image/attachment/@filename')[0],
        "plMaturity" : gingerAle.xpath('/table/tbody/tr[4]/td/structured-macro/parameter[@name="colour"]')[0].text,
        "plReq" : gingerAle.xpath('/table/tbody/tr[5]/td')[0].text,
        # OBS, license needs not be a link
        "plLicense" : gingerAle.xpath('/table/tbody/tr[6]/td/a')[0].text,
        "plSource" : gingerAle.xpath('/table/tbody/tr[7]/td/a')[0].text,
        "plProjects" : gingerAle.xpath('/table/tbody/tr[8]/td')[0].text,
        "plFiles" : gingerAle.xpath('/table/tbody/tr[9]/td')[0].text
    })
    # print("""Description is %s""" % pluginDict["plDesc"])
    return pluginDict
# def compileInfo ends here

def buildMPapiP():
    """Construct of one answer. Requires only info from config file."""
    conGen=config['General']
    mplace = etree.Element("marketplace")
    market = etree.SubElement(mplace,"market", id=conGen['id'], name=conGen['name'], url=conGen["URL"]+"category/markets/"+conGen["id"])

    catCount=1
    conCat = config["Categories"]
    for key in conCat:
        etree.SubElement(market,"category",count=str(catCount), id=key,name=conCat[key], url=str(conGen["URL"])+"taxonomy/term/"+conGen["id"]+","+key)
        catCount += 1
    return mplace
# def buildMPapiP ends here

def buildMPcatApiP():
    """The info on catalog. According to server log, this is the first
    thing the Lab looks for. Requires only info from config file.
    After choosing that catalog, the root is called.
    """
    conGen=config['General']

    mplace = etree.Element("marketplace")
    mplace.append(etree.Comment("File generated on %s" % datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
    catalogs = etree.SubElement(mplace,"catalogs")
    catalog = etree.SubElement(catalogs,"catalog", id=conGen["id"], title=conGen["title"], url=conGen["URL"], selfContained="0",icon=conGen["URL"]+conGen["icon"])
    desc = etree.SubElement(catalog,"description").text = "The features of TextGrid"
    depRep = etree.SubElement(catalog,"dependenciesRepository")
    wizard = etree.SubElement(catalog,"wizard", title="")
    icon = etree.SubElement(wizard,"icon")
    sTab = etree.SubElement(wizard,"searchtab",enabled="1").text = "Search"
    popTab = etree.SubElement(wizard,"populartab",enabled="1").text = "Popular"
    recTab = etree.SubElement(wizard,"recenttab",enabled="1").text = "Recent"
    return mplace
# def buildMPcatApiP ends here

def buildMPtaxonomy(marID,catID,instUnits):
    """
    """

    mplace = etree.Element("marketplace")
    conCat = config["Categories"]
    print(conCat[catID])
    category = etree.SubElement(mplace,"category",id=catID,name=conCat[catID],url=config["General"]["URL"]+"taxonomy/term/"+marID+","+catID)
    # wiederhole die zwei nächsten für alle, die in der entsprechenden Gruppe sind
    for iu in instUnits.items():
        if iu[1][2] == catID:
            node = etree.SubElement(category,"node",id=iu[1][0],name=iu[1][1],url=config["General"]["URL"]+"content/"+iu[1][0])
            fav = etree.SubElement(category,"favorited").text = "0"
    return mplace
# def buildMPtaxonomy ends here

def buildMPnodeApiP(instUnits,plugName):
    """info on installable Unit"""
    node = etree.Element("node",id=instUnits[plugName][0], name=instUnits[plugName][1], url=config["General"]["URL"]+instUnits[plugName][0])
    bodyEle = etree.SubElement(node,"body").text = etree.CDATA([plug["plDesc"]])
    # taken from Label of wikipage
    catEle = etree.SubElement(node,"categories")
    # noch nicht ganz fertig!
    category = etree.SubElement(catEle,"categories",id=instUnits[plugName][2],name=instUnits[plugName][1],url=config["General"]["URL"]+"taxonomy/term/"+config["General"]["id"]+","+instUnits[plugName][2])
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
    imageEle = etree.SubElement(node,"image").text = etree.CDATA("https://develop.sub.uni-goettingen.de/repos/textgrid/trunk/lab/noteeditor/info.textgrid.lab.noteeditor/icons/meise_64.png")
    # just a container
    iusEle = etree.SubElement(node,"ius")
    # where to store that information?
    iuEle = etree.SubElement(iusEle,"iu").text = "info.textgrid.lab.%s.feature.feature.group" % plugName
    licenseEle = etree.SubElement(node,"license").text = "URL!"
    # who is the owner?
    ownerEle = etree.SubElement(node,"owner").text = TextGrid
    # what is this about?
    resourceEle = etree.SubElement(node,"resource") # this?
    # see logo
    scrshotEle = etree.SubElement(node,"screenshot").text = "https://develop.sub.uni-goettingen.de/repos/textgrid/trunk/lab/noteeditor/info.textgrid.lab.noteeditor.feature/Screenshot_MEISE_2012-04-20.png"
    # also hidden field?
    updateEle = etree.SubElement(node,"updateurl").text = etree.CDATA("http://download.digital-humanities.de/updates/textgridlab/noteeditor")

    return node
# def buildMPnodeApiP ends here

def buildMPfeaturedApiP():
    """this takes those nodes (my theory here) that have a value of
    non-nil in 'featured' (should be on the wiki page) and wraps them
    into some XML
    """
    mplace = etree.Element("marketplace")
    featured = etree.SubElement(mplace,"featured",count=numFeat)
    # make the nodes here as a subElement of featured
    for i in featuredList:
        
        i = buildMPnodeApiP(config,instUnits,plugName,plDict)
        i = etree.SubElement(featured)

    return mplace
# def buildMPfeaturedApiP ends here

def prepareConf():
    # returns pluginInfo (XML Data)
    sho = getConfluencePluginData
    body = parseConfluenceBody(sho)
    # returns a dictionary
    return compileInfo(body)
# def prepareConf ends here

def main():
    parser = argparse.ArgumentParser()
    msActions = parser.add_mutually_exclusive_group()
    msActions.add_argument("-m","--main",help="listing of markets and categories",action="store_true")
    msActions.add_argument("-c","--catalogs",help="obtain all available catalogs",action="store_true")
    msActions.add_argument("-t","--taxonomy",help="listing of specific market or category",action="store_true")
    msActions.add_argument("-co","--content",help="return a specific listing",action="store_true")
    msActions.add_argument("-n","--node",help="return a specific listing",action="store_true")
    msActions.add_argument("-s","--search",help="return search results",action="store_true")
    msActions.add_argument("-f","--featured",help="list of Featured listings",action="store_true")
    msActions.add_argument("-r","--recent",help="recently updated or added listings",action="store_true")
    msActions.add_argument("-fa","--favorites",help="most favourite things",action="store_true")
    msActions.add_argument("-p","--popular",help="most popular by activity",action="store_true")

    parser.add_argument("-cId","--categoryId",help="ID of category")
    parser.add_argument("-mId","--marketId",help="ID of market")
    parser.add_argument("-ti","--title",help="title of a plugin?")
    parser.add_argument("-no","--nodeTitle",help="title of a node?")
    parser.add_argument("-q","--query",help="query string")
    # things the client tells us:
    parser.add_argument("--product")
    parser.add_argument("--os")
    parser.add_argument("--runtime.version")
    parser.add_argument("--client")
    parser.add_argument("--java.version")
    parser.add_argument("--product.version")
    parser.add_argument("--ws",help="returns cocoa in case of apple")
    parser.add_argument("--nl",help="Language")

    args=parser.parse_args()

    if args.main:
        node = buildMPapiP()
    if args.catalogs:
        node = buildMPcatApiP()
    if args.taxonomy:
        node = buildMPtaxonomy(args.marketId,args.categoryId,instUnits)
    if args.featured:
        node = fdd
    # if args.recent:
    #     node = fdd
    # if args.favorites:
    #     node = fdd
    # if args.popular:
    #     node = fdd
        
    # output
    print('Content type: text/xml\n')
    son = etree.tostring(node,pretty_print=True,encoding='utf-8',xml_declaration=True)
    outDecode = son.decode(encoding='utf-8')
    print(outDecode)

if __name__ == "__main__":
    main()
