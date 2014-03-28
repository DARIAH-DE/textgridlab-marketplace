#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
# Time-stamp: <2014-03-28 20:09:25 (kthoden)>

__author__="Klaus Thoden"
__date__="2014-03-13"
__doc__ = """Getting a page out of the Confluence system and convert it to
something the Eclipse Marketplace understands."""

# imports
from lxml import etree

# Atlassian namespaces
# http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
NS={'ri':'http://www.atlassian.com/schema/confluence/4/ri/', 
    'ac':'http://www.atlassian.com/schema/confluence/4/ac/' }

def getConfluencePluginData(state="offline"):
    """
    Use python's lxml to get the Plugin pages from Confluence.
    REST documentation on https://docs.atlassian.com/atlassian-confluence/REST/latest/
    """
    import urllib
    import sys


    if state=="offline":
        baseURL = "file:///Users/kthoden/TextGrid/Marketsplace/dev/"
        ID = "27329537"
    else:
        baseURL = "https://dev2.dariah.eu/wiki/rest/prototype/1/content/"
        # ID = "27329537" # digilib, not yet accessible through script, as I am not logged in
        ID = "9012111"

    fullpath = baseURL + ID

    try:
        usock=urllib.urlopen(fullpath)
        print("Getting info from %s"% fullpath)
    except IOError as (errno, strerror):
        print("I/O error ({0}): {1}".format(errno,strerror))
        sys.exit()

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
    replacements = {
        u'&amp;' : u'&',
        u'&lt;' : u'<',
        u'&gt;' : u'>',
        u'&quot;' : u'"',
        u'&apos;' : u"'",
        u'&uuml;' : u'ü',
        u'&auml;' : u'ä',
        u'&ouml;' : u'ö',
        u'&nbsp;' : u' ',
        u'ac:' : u'',
        u'ri:' : u''
    }

    for thing in replacements.keys():
        text = text.replace(thing, replacements[thing])
    return text
# def reverseTags ends here

def parseConfluenceBody(codedBody):
    """Body needs to be transformed a bit."""
    # some ugly modifications
    clean = reverseTags(codedBody)
    bodyInfo = etree.fromstring(clean)

    return bodyInfo
## def parseConfluenceBody ends here

# main bit
bitterLemon = getConfluencePluginData()

pluginTitle = bitterLemon.xpath('/content/title')[0].text
print("""Title of the page is %s""" % pluginTitle)

pluginBody = bitterLemon.xpath('/content/body')[0].text

gingerAle = parseConfluenceBody(pluginBody)

plTitle = gingerAle.xpath('/table/tbody/tr[1]/td')[0].text
print("""Title taken from the body: %s""" % plTitle)
plDesc = gingerAle.xpath('/table/tbody/tr[2]/td')[0].text
plIcon = gingerAle.xpath('/table/tbody/tr[3]/td/image/attachment/@filename')[0]
plMaturity = gingerAle.xpath('/table/tbody/tr[4]/td/structured-macro/parameter[@name="colour"]')[0].text
plReq = gingerAle.xpath('/table/tbody/tr[5]/td')[0].text
# OBS, license needs not be a link
plLicense = gingerAle.xpath('/table/tbody/tr[6]/td/a')[0].text
plSource = gingerAle.xpath('/table/tbody/tr[7]/td/a')[0].text
plProjects = gingerAle.xpath('/table/tbody/tr[8]/td')[0].text
plFiles = gingerAle.xpath('/table/tbody/tr[9]/td')[0].text

print("""License is %s""" % plLicense)

