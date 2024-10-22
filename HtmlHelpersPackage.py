import bs4
from bs4 import dammit

#=====================================================================================
def HtmlEscapesToUnicode(s: str) -> str:
    return str(bs4.BeautifulSoup(s)).strip()


def UnicodeToHtmlEscapes(s: str) -> str:
    return bs4.dammit.EntitySubstitution.substitute_html(s)
