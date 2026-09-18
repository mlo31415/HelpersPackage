import html

import bs4

#=====================================================================================
# Turn HTML character escapes back into the characters they stand for.
# This must handle "&amp;", "&lt;" and "&gt;".  (The previous implementation round-tripped the string through
# BeautifulSoup, whose serializer re-escapes exactly those three, so they came back unchanged -- meaning an
# ampersand in, say, a fanzine name picked up another "amp;" on each download/upload cycle.)
# The decode is repeated to a fixpoint so values already escalated by that bug ("Sweetness &amp;amp; Light")
# are repaired when they are read.
def HtmlEscapesToUnicode(s: str, isURL: bool=False) -> str:
    if isURL:
        s=s.replace("%23", "#").replace( "%26", "&").replace( "%20", " ")
    for _ in range(4):
        t=html.unescape(s)
        if t == s:
            break
        s=t
    s=s.strip()
    if isURL:
        s=s.replace("%23", "#").replace( "%26", "&").replace( "%20", " ")
    return s

def UnicodeToHtmlEscapes(s: str, isURL: bool=False) -> str:
    if isURL:
        s=s.replace("#", "%23").replace("&", "%26").replace( " ", "%20")
    s=bs4.dammit.EntitySubstitution.substitute_html(s)
    if isURL:
        s=s.replace("#", "%23").replace("&", "%26").replace( " ", "%20")
    return s

#=====================================================================================
def ConvertHTMLEscapes(s: str) -> str:
    s=s.replace("&amp;", "&")
    s=s.replace("%23", "#").replace( "%26", "&").replace( "%20", " ")
    s=s.replace("&gt;", ">").replace( "&lt;", "<").replace("&nbsp;", " ")
    return s
