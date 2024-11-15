import bs4
from bs4 import dammit

#=====================================================================================
def HtmlEscapesToUnicode(s: str, isURL=False) -> str:
    if isURL:
        s=s.replace("%23", "#").replace( "%26", "&").replace( "%20", " ")
    return str(bs4.BeautifulSoup(s, features="html.parser")).strip()


def UnicodeToHtmlEscapes(s: str, isURL=False) -> str:
    if isURL:
        s=s.replace("#", "%23").replace("&", "%26").replace( " ", "%20")
    return bs4.dammit.EntitySubstitution.substitute_html(s)
