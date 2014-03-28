#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
# Time-stamp: <2014-03-28 18:57:28 (kthoden)>

__author__="Klaus Thoden"
__date__="2014-03-13"
__doc__ = """Getting a page out of the Confluence system and convert it to
something the Eclipse Marketplace understands."""

# Atlassian namespaces
# http://www.amnet.net.au/~ghannington/confluence/docs/confluence/g-ri_confluence.ri.html
# ri: http://www.atlassian.com/schema/confluence/4/ri/
# ac: http://www.atlassian.com/schema/confluence/4/ac/

def getConfluencePluginData(state="offline"):
    """
    Use python's lxml to get the Plugin pages from Confluence.
    REST documentation on https://docs.atlassian.com/atlassian-confluence/REST/latest/
    """
    import urllib
    import sys
    from lxml import etree

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

def parseConfluenceBody():
    """Body needs to be transformed a bit."""
## def parseConfluenceBody ends here

# main bit
bitterLemon = getConfluencePluginData()

pluginTitle = bitterLemon.xpath('/content/title')[0].text
print("""Title of the page is %s""" % pluginTitle)

print("seems to work")
