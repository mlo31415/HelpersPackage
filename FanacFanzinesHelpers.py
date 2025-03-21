import re
from Log import Log

def ReadClassicFanzinesTable(html: str) -> list[str]|None:
    # Parse the HTML looking for the classic fanzines table
    # (Note that this used to be done using BeautifulSoup, but it was very slow.)
    m=re.search(r"<table[^>]*sortable\">(.*)$", html, flags=re.DOTALL|re.IGNORECASE)
    if m is None:
        Log("ReadClassicFanzinesTable: Could not find sortable table.")
        return None
    table=m.groups()[0]
    
    # Go through the table finding, extracting and then deleting the rows one-by-one
    rows=[]
    while True:
        m=re.search(r"<tr.*?>(.*?)</tr>", table, flags=re.DOTALL|re.IGNORECASE|re.MULTILINE)
        if m is None:
            break
        rows.append(m.groups()[0])
        table=re.sub(r"<tr.*?>(.*?)</tr>", "?", table, count=1, flags=re.DOTALL|re.IGNORECASE)

    return rows