#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2014-06-13 16:37:11 (kthoden)>

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
"""

# imports
from lxml import etree
import configparser

# Atlassian namespaces
# http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
NS={'ri':'http://www.atlassian.com/schema/confluence/4/ri/', 
    'ac':'http://www.atlassian.com/schema/confluence/4/ac/' }

config = configparser.ConfigParser()
config.read("ms.conf")
conGen = config['General']

# schreibt Thorsten
# p2-Update-Site enthält (in diesem Falle
# http://www.textgridlab.org/updates/beta). Dazu kommen dann noch
# die zugehörigen IDs der Installable Units, d.i. in der Regel
# die ID des entsprechenden Features mit angehängtem
# ».feature.group«.
# info.textgrid.lab.noteeditor.feature.feature.group
p2UpdateSite = "http://www.textgridlab.org/updates/beta"

# we somehow need to know here as well which category (external, beta, stable) this is in
# first tuple is ID, second the title, third the category
instUnits = dict(
    {"linguistics" : ("7","Linguistic Tools"), 
     "ttle" : ("8","Text Text Linkeditor"), 
     "collatex": ("4","CollateX"), 
     "noteeditor" : ("2","MEISE Noteneditor","4"), 
     "sadepublish" : ("1","SADE Publish Tool"), 
     "digilib" : ("3","DigiLib"), 
     "oxygen" : ("5","Oxygen XML Editor")
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
        baseURL = "file:///Users/kthoden/TextGrid/Marketsplace/dev/"
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

def buildMPapiP(config):
    """Construct of one answer. Requires only info from config file."""
    conGen=config['General']
    mplace = etree.Element("marketplace")
    market = etree.SubElement(mplace,"market", id=conGen['id'], name=conGen['name'], url=conGen["URL"]+"category/markets/"+conGen["id"])

    catCount=1
    conCat = config["Categories"]
    for key in conCat:
        etree.SubElement(market,"category",count=str(catCount), id=conCat[key],name=key, url=str(conGen["URL"])+"taxonomy/term/"+conGen["id"]+","+conCat[key])
        catCount += 1
    return mplace
# def buildMPapiP ends here

def buildMPcatApiP(config):
    """The info on catalog. According to server log, this is the first
    thing the Lab looks for. Requires only info from config file.
    After choosing that catalog, the root is called.
    """
    conGen=config['General']

    mplace = etree.Element("marketplace")
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

def buildMPnodeApiP(unit,plug):
    """info on installable Unit"""
    mplace = etree.Element("marketplace")
    node = etree.SubElement(mplace,"node", id=instUnits[unit[0]], name=instUnits[unit[1]], url=msDict["msURL"]+instUnits[unit[0]])
    bodyEle = etree.SubElement(node,"body").text = etree.CDATA([plug["plDesc"]])
    # taken from Label of wikipage
    catEle = etree.SubElement(node,"categories")
    # noch nicht ganz fertig!
    category = etree.SubElement(catEle,"categories",id=unit[2],name=unit[1],url=msDict["msURL"]+"taxonomy/term/"+msDict["id"]+","+cat[1])
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
    iuEle = etree.SubElement(iusEle,"iu").text = "info.textgrid.lab.noteeditor.feature.feature.group"
    licenseEle = etree.SubElement(node,"license").text = "URL!"
    # who is the owner?
    ownerEle = etree.SubElement(node,"owner").text = TextGrid
    # what is this about?
    resourceEle = etree.SubElement(node,"resource") # this?
    # see logo
    scrshotEle = etree.SubElement(node,"screenshot").text = "https://develop.sub.uni-goettingen.de/repos/textgrid/trunk/lab/noteeditor/info.textgrid.lab.noteeditor.feature/Screenshot_MEISE_2012-04-20.png"
    # also hidden field?
    updateEle = etree.SubElement(node,"updateurl").text = etree.CDATA("http://download.digital-humanities.de/updates/textgridlab/noteeditor")
# def buildMPnodeApiP ends here

def buildMPfeaturedApiP():
    """this takes those nodes (my theory here) that have a value of
    non-nil in 'featured' (should be on the wiki page) and wraps them
    into some XML
    """
    mplace = etree.Element("marketplace")
    featured = etree.SubElement(mplace,"featured",count=numFeat)
    # make the nodes here as a subElement of featured
    # for i in …
# def buildMPfeaturedApiP ends here

def buildMPtaxonomy():
    mplace = etree.Element("marketplace")
    category = etree.SubElement(mplace,"category",id=msDict["categories"][XXX_VAR_XXX][1],name=msDict["categories"][XXX_VAR_XXX][0],url=msDict["msURL"]+"taxonomy/term/"+msDict["id"]+","+cat[1])
    # wiederhole die zwei nächsten für alle, die in der entsprechenden Gruppe sind
    node = etree.SubElement(category,"node",id=unit[0],name=unit[1],url=msDict["msURL"]+"content/"+unit[0])
    fav = etree.SubElement(category,"favorited").text = "0"
# def buildMPtaxonomy ends here

def main():
    bitterLemon = getConfluencePluginData("offline")

    pluginTitle = bitterLemon.xpath('/content/title')[0].text
    print("""Title of the page is %s""" % pluginTitle)

    pluginBody = bitterLemon.xpath('/content/body')[0].text

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
    print("""Description is %s""" % pluginDict["plDesc"])

    msContent = msDict["msURL"] + "content/"
    iuID = "2"

    # needs a unit from installable units and the pluginDict
    node = buildMPnodeApiP()

    print(etree.tostring(node,pretty_print=True,encoding='unicode'))

if __name__ == "__main__":
    main()
