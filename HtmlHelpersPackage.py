import bs4
from bs4 import dammit

#=====================================================================================
def HtmlEscapesToUnicode(s: str, isURL=False) -> str:
    if isURL:
        s=s.replace("%23", "#").replace( "%26", "&").replace( "%20", " ")
    s=str(bs4.BeautifulSoup(s, features="html.parser")).strip()
    if isURL:
        s=s.replace("%23", "#").replace( "%26", "&").replace( "%20", " ")
    return s

def UnicodeToHtmlEscapes(s: str, isURL=False) -> str:
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
