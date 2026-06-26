import warnings

import bs4
from bs4 import MarkupResemblesLocatorWarning

#=====================================================================================
def HtmlEscapesToUnicode(s: str, isURL: bool=False) -> str:
    if isURL:
        s=s.replace("%23", "#").replace( "%26", "&").replace( "%20", " ")
    # This helper is routinely called on short URL/filename strings, which BeautifulSoup mistakes for
    # filenames and warns about. The parse is fine; the warning is spurious, so suppress it for this call only.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=MarkupResemblesLocatorWarning)
        s=str(bs4.BeautifulSoup(s, features="html.parser")).strip()
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
