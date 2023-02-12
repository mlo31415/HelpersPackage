from __future__ import annotations
import os
import sys
import ctypes
import unicodedata
from tkinter import Tk, messagebox
from tkinter.simpledialog import askstring
import tkinter
import urllib.parse
from typing import Union, Optional, DefaultDict
from html import escape, unescape
from contextlib import suppress
from collections import defaultdict
import re
import stat

from Log import Log, LogClose


#=======================================================
# Locate all matches to the pattern and remove them
# Numgroups is the number of matching groups in the pattern
#   If numGroups=0, we just replace the matched text without returning it
#   If numGroups=1, the output list is a list of strings matched
#   If numGroups>1, the output list is a list of lists, with the sublist being whatever is matched by the groups -- we don't necessarily return everything that has been matched
# Return a list of matched strings and the remnant of the input string

# NOTE: Text to be removed *must* be part of a group!
def SearchAndReplace(pattern: str, inputstr: str, replacement: str, numGroups: int=1, caseinsensitive: bool=False) -> tuple[list[str], str]:
    found: list[str] | list[list[str]]=[]
    # Keep looping and removing matched material until the match fails
    while True:
        # Look for a match
        if caseinsensitive:
            m=re.search(pattern, inputstr, re.IGNORECASE)
        else:
            m=re.search(pattern, inputstr)
        # If none is found, return the results
        if m is None:
            return found, inputstr
        # We found something. Append it to the list of found snippets
        # When numGroups is zero we just replace the text without saving it.
        if numGroups == 1:
            found.append(m.groups()[0])
        elif numGroups > 1:
            found.append([x for x in m.groups()])
        # Replace the found text
        inputstr=re.sub(pattern, replacement, inputstr, 1, flags=re.IGNORECASE)

#=======================================================
# When a python program has been frozen using Pyinstaller, some of its resource files may be frozen with it
# PyiResourcePath takes a path *relative to the python source files* and turns it into the resource path if we're running frozen.
def PyiResourcePath(relative_path):
    frozen=getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    # If we're not frozen, just use the local path
    if not frozen:
        return os.path.join(sys.path[0], relative_path)

    # Get absolute path to resource, works for dev and for PyInstaller
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path=getattr(sys, '_MEIPASS', False)
    except Exception:
        base_path=os.environ.get("_MEIPASS2", os.path.abspath("."))

    return os.path.join(base_path, relative_path)

#=======================================================
# Locate and return a chunk of text bounded by two patterns
def SearchAndExtractBounded(source: str, startpattern: str, endpattern: str) -> tuple[Optional[str], str]:
    m=re.search(startpattern, source)
    if m is None:
        return None, source
    loc=m.span()[1]
    m=re.search(endpattern, source[loc:])
    if m is None:
        return None, source
    return source[loc:loc+m.span()[0]], source[loc+m.span()[1]+1:]


#=======================================================
# Try to make the input numeric
# Note that if it fails, it returns what came in.
def ToNumeric(val: Union[None, int, float, str]) -> Union[None, int, float]:
    if val is None:
        return None

    if isinstance(val, str) and len(val.strip()) == 0:  # Empty strings become None
        return None

    if isinstance(val, int) or isinstance(val, float):  # Numbers are numbers and just get returned
        return val

    # Last chance is to try to convert val into an int or float.
    try:
        return int(val)
    except:
        with suppress(Exception):
            return float(val)

    # If nothing works, return None
    return None


# Take a string and find the first hyperlink.
# Return a tuple of: <material before>, <link>, <display text>, <material after>
def FindLinkInString(s: str) -> tuple[str, str, str, str]:
    pat="^(.*?)<a\s+href=['\"]http[s]?(.*?)>(.*?)</a>(.*)$"
    m=re.match(pat, s, flags=re.RegexFlag.IGNORECASE)
    if m is None:
        return s, "", "", ""
    return m.groups()[0], m.groups()[1], m.groups()[2], m.groups()[3]



#==================================================================================
# Return a properly formatted link
# Depending on flags, the URL may get 'https://' or 'http://' prepended.
# If it is a PDF it will get view=Fit appended
# PDFs may have #page=nn attached
def FormatLink(url: str, text: str, ForceHTTP: bool=False, ForceHTTPS: bool=False, QuoteChars=False) -> str:
    # TODO: Do we need to deal with turning blanks into %20 whatsits?

    # If a null URL is provided, don't return a hyperlink
    if url is None or url == "":
        return text

    # '#' can't be part of an href as it is misinterpreted
    # But it *can* be part of a link to an anchor on a page or a part of a pdf reference.
    # Look for #s in a URL *before* a .pdf extension and convert them to %23s
    if '#' in url:
        m=re.match("(.*)(\.pdf.*)", url, re.IGNORECASE)
        if m is not None:
            url=m.groups()[0].replace("#", "%23")+m.groups()[1]
    url=UnicodeToHtml(url)

    if QuoteChars:
        url=urllib.parse.quote(url)

    # If the url points to a pdf, add '#view=Fit' to the end to force the PDF to scale to the page
    if ".pdf" in url:
        # Note that if there's already a #whatzit at the end, this gets added as &view=Fit and not as #view=Fit
        if ".pdf#" in url:
            url+="&view=Fit"
        else:
            url+="#view=Fit"

    if ForceHTTP:
        if not url.lower().startswith("http"):
            url="http://"+url
    elif ForceHTTPS:
        if not url.lower().startswith("https"):
            url="https://"+url

    return '<a href="'+url+'">'+text+'</a>'


def FormatLink2(url: str, text: str, ForceHTTP: bool=False) -> str:
    return FormatLink(url, text, ForceHTTP=ForceHTTP, ForceHTTPS=not ForceHTTP, QuoteChars=True)


#==================================================================================
# Take a string and strip out all hrefs, retaining all the text.
def UnformatLinks(s: str) -> Optional[str]:
    if s is None or s == "":
        return s

    try:
        # Convert substrings of the form '<a href="'(stuff1)'>'(stuff2)'</a>'  to (stuff2)
        s=re.sub('(<a\s+href=".+?">)(.+?)(</a>)', "\\2", s)

        # And then there are Mediawiki redirects
        s=re.sub('(<a\s+class=".+?">)(.+?)(</a>)', "\\2", s)
    except:
        pass
    return s


#-------------------------------------------------------------
# Change the 1st character to uppercase and leave the rest alonw
def CapitalizeFirstChar(s: str) -> str:
    return s[0].upper()+s[1:]


# -------------------------------------------------------------------------
# Take a string and a value and add appropriate pluralization to string -- used in calls to WriteTable
def Pluralize(val: int, s: str) -> str:
    return f"{val} {s}{'s' if val != 1 else ''}"

#-------------------------------------------------------------
def CanonicizeColumnHeaders(header: str) -> str:
    # 2nd item is the canonical form for fanac.org and fancyclopedia series tables
    translationTable={
                        "published" : "Date",
                        "editors" : "Editor",
                        "zine" : "Issue",
                        "fanzine" : "Issue",
                        "apa mailing" : "Mailing",
                        "mo." : "Month",
                        "mon" : "Month",
                        "quartermonth" : "Month",
                        "quarter" : "Month",
                        "season" : "Month",
                        "notes" : "Notes",
                        "no." : "Number",
                        "no,": "Number",
                        "num" : "Number",
                        "#" : "Number",
                        "page" : "Pages",
                        "pages" : "Pages",
                        "pp," : "Pages",
                        "pp." : "Pages",
                        "pub" : "Publisher",
                        "vol" : "Volume",
                        "volume" : "Volume",
                        "volumenumber" : "Vol+Num",
                        "vol#" : "Vol+Num",
                        "vol.#" : "Vol+Num",
                        "wholenum" : "Whole",
                        "year" : "Year",
                      }
    if len(header) == 0:
        return ""
    try:
        return translationTable[header.replace(" ", "").replace("/", "").lower()]
    except:
        return header[0].upper()+header[1:]


#=====================================================================================
# Scan for text bracketed by <bra>...</bra>
# Return True/False and remaining text after <bra> </bra> is removed
# Return the whole string if brackets not found
def ScanForBracketedText(s: str, bra: str) -> tuple[bool, str]:
    m=re.match(f"\w*<{bra}>(.*)</{bra}>\w*$", s)
    if m is None:
        return False, s
    return True, m.groups()[0]

#=====================================================================================
# Find the first <bracket>bracketed text</bracket> located.  Return the leading, enclosed, and trailing text
def ParseFirstStringBracketedText(s: str, bracket: str) -> tuple[str, str, str]:
    # We need to escape certain characters before substituting them into a RegEx pattern
    bracket=bracket.replace("[", r"\[").replace("(", r"\(").replace("{", r"\{")

    pattern=rf"^(.*?)<{bracket}>(.*?)</{bracket}>(.*)$"
    m=re.search(pattern, s,  re.DOTALL)
    if m is None:
        return s, "", ""

    return m.group(1), m.group(2), m.group(3)


#=====================================================================================
# Find text bracketed by <b>...</b> and replace it with new text
# Return the (possibly) modified text and a bool to indicate if anything was found
def FindAndReplaceBracketedText(s: str, bracket: str, replacement: str, stripHtml: bool=True) -> tuple[str, bool]:

    pattern=f"<{bracket}>(.*?)</{bracket}>"
    m=re.search(pattern, s,  flags=re.DOTALL)     # Do it multiline
    if m is None:
        return s, False
    match=m.groups()[0]
    if stripHtml:
        match=RemoveAllHTMLTags(match)
    s2=re.sub(pattern, replacement, s, flags=re.DOTALL, count=1)
    return s2, True


#=====================================================================================
# Find first text bracketed by <anything>...</anything>
# Return a tuple consisting of:
#   Any leading material
#   The name of the first pair of brackets found
#   The contents of the first pair of brackets found
#   The remainder of the input string
# Note that this is a *non-greedy* scanner
# Note also that it is not very tolerant of errors in the bracketing, just dropping things on the floor
def FindAnyBracketedText(s: str) -> tuple[str, str, str, str]:

    pattern=r"^(.*?)<([a-zA-Z0-9]+)[^>]*?>(.*?)<\/\2>"
    m=re.search(pattern, s,  re.DOTALL)
    if m is None:
        return s, "", "", ""

    x=m.group(1), m.group(2), m.group(3), s[m.regs[0][1]:]
    return x


#=====================================================================================
# Find text bracketed by <b>...</b>
# Return the contents of the first pair of brackets found and the remainder of the input string
def FindBracktedText2(s: str, b: str) -> tuple[str, str]:
    return FindBracketedText(s, b, stripHtml=False, stripWhitespace=True)

def FindBracketedText(s: str, b: str, stripHtml: bool=True, stripWhitespace: bool=False) -> tuple[str, str]:

    pattern="<"+b+">(.*?)</"+b+">"
    if stripWhitespace:
        pattern=fr"\s*{pattern}\s*"
    m=re.search(pattern, s,  re.DOTALL)
    if m is None:
        return "", s
    #match=m.groups()[0]
    match=s[m.regs[1][0]:m.regs[1][1]]  # The matched part -- the only group of the pattern
    s2=s[:m.regs[0][0]]+s[m.regs[0][1]:]
    if stripHtml:
        match=RemoveAllHTMLTags(match)
    #s2=re.sub(pattern, "", s, count=1)
    return match, s2


#=====================================================================================
# Find the cfirst bracket located.  Return the leading, enclosed, and trailing text
def ParseFirstBracketedText(s: str, b1: str, b2: str) -> tuple[str, str, str]:
    # We need to escape certain characters before substituting them into a RegEx pattern
    b1=b1.replace("[", r"\[").replace("(", r"\(").replace("{", r"\{")

    pattern=r"^(.*?)"+b1+"(.+?)"+b2+"(.*)$"
    m=re.search(pattern, s,  re.DOTALL)
    if m is None:
        return s, "", ""

    return m.group(1), m.group(2), m.group(3)


#=====================================================================================
# Find text bracketed by [[]]
# Return the contents of the first pair of brackets found
def FindWikiBracketedText(s: str) -> str:

    m=re.search("\[\[(:?.+)]]", s)
    if m is None:
        return ""
    return m.groups()[0]


#=====================================================================================
# Remove an outside matched pair of <tag> </tag> from a string, returning the inside
def StripSpecificTag(s: str, tag: str, CaseSensitive=False)-> str:
    pattern=f"^<{tag}>(.*)</{tag}>$"
    if CaseSensitive:
        m=re.match(pattern, s, re.IGNORECASE)
    else:
        m=re.match(pattern, s, re.IGNORECASE)

    if m is None:
        return s
    return m.groups()[0]

#=====================================================================================
# Remove a matched pair of <brackets> <containing anything> from a string, returning the inside
def StripExternalTags(s: str)-> Optional[str]:
    m=re.match("^<.*>(.*)</.*>$", s)
    if m is None:
        return None
    return m.groups()[0]


#=====================================================================================
# Remove a matched pair of <brackets> <containing anything> from a string, returning the inside
def StripWikiBrackets(s: str)-> str:
    m=re.match("^\[\[(.*)]]$", s)
    if m is None:
        return s
    return m.groups()[0]


#=====================================================================================
# Take the input, find the text surrounded by <tag> and </tag> and substitute the replacement
def SubstituteHTML(input: str, tag: str, replacement: str) -> str:
    t="<"+tag+">"
    loc=input.find(t)
    if loc == -1:
        return input
    t2="</"+tag+">"
    loc2=input.find(t2, loc+2)
    if loc2 == -1:
        return input
    return input[:loc]+t+replacement+t2+input[loc2+len(t2):]

#=====================================================================================
# If needed, prepend http://
def PrependHTTP(input: str) -> str:
    if input.lower().startswith("http://") or input.lower().startswith("https://"):
        return input
    return "http://"+input

#=====================================================================================
# If needed, prepend https://
def PrependHTTPS(input: str) -> str:
    if input.lower().startswith("http://") or input.lower().startswith("https://"):
        return input
    return "https://"+input


# =====================================================================================
# If needed, remove http://
def RemoveHTTP(input: str) -> str:
    return input.replace("http://", "", 1).replace("HTTP://", "", 1).replace("https://", "", 1).replace("HTTPS://", "", 1)


#=====================================================================================
# Remove the accents, unlats, etc from characters
def RemoveAccents(s: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', s)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


#=====================================================================================
# Most non-alphanumeric characters can't be used in filenames with Jack's software on fanac.org. Turn runs of those characters into a single underscore
def RemoveScaryCharacters(name: str) -> str:
    return RemoveAccents("".join(re.sub("[?*&%$#@'><:;,.{}\][=+)(^!\s]+", "_", name)))


#=====================================================================================
# Do a case-insensitive replace, replacing old with new
def CaseInsensitiveReplace(s: str, old: str, new: str) -> str:
    loc=s.lower().find(old.lower())
    if loc == -1:
        return s
    if loc == 0:
        return new+s[loc+len(old):]
    return s[:loc]+new+s[loc++len(old)]


#=====================================================================================
# Remove certain strings which amount to whitespace in html
def RemoveHTMLDebris(s: str) -> str:
    return s.replace("<br>", "").replace("<BR>", "")


#=====================================================================================
# Remove all html tags (or at least those which have been an issue
def RemoveAllHTMLTags(s: str) -> str:
    vv=re.sub('(</?[a-zA-Z0-9]+>)', "", s)
    return vv


#=====================================================================================
# Remove all html tags (or at least those which have been an issue
# This one is more aggressive
def RemoveAllHTMLTags2(s: str) -> str:
    vv=re.sub('(</?[a-zA-Z0-9]+>)', "", s)
    return vv


#=====================================================================================
# Turn some whitespace escape characters into spaces
def RemoveFunnyWhitespace(s: str) -> str:
    return s.replace("\xc2\xa0", " ").replace(u"\u00A0", " ")

#=====================================================================================
# Change"&nbsp;" to space
def ChangeNBSPToSpace(s: Optional[str]) -> Union[None, str, list[str]]:
    if s is None:
        return None
    if len(s) == 0:
        return s

    if isinstance(s, str):
        return s.replace("&nbsp;", " ")

    return [c.replace("&nbsp;", " ") for c in s]


#=====================================================================================
# Convert the unicode of a str to a string which can be used in an HTML file
def UnicodeToHtml(s: str) -> str:
    # Convert the text to ascii and then used decode to turn it back into a str
    return escape(s).encode('ascii', 'xmlcharrefreplace').decode()


#=====================================================================================
# Convert the unicode of a str to a string which can be used in an HTML file
def UnicodeToHtml2(s: str) -> str:
    # Convert the text to ascii and then used decode to turn it back into a str
    return s.encode(encoding='ascii', errors="xmlcharrefreplace").decode()


#=====================================================================================
# Function to generate the proper kind of path.  (This may change depending on the target location of the output.)
def RelPathToURL(relPath: str) -> Optional[str]:
    if relPath is None:
        return None
    if relPath.startswith("http"):  # We don't want to mess with foreign URLs
        return None
    return "https://www.fanac.org/"+os.path.normpath(os.path.join("fanzines", relPath)).replace("\\", "/")


# =====================================================================================
# Function to find the index of one or more strings in a list of strings
def FindIndexOfStringInList(lst: list[str], s: [str, list[str]], IgnoreCase=False) -> Optional[int]:
    if type(s) is str:  # If it's a single string, just go with it!
        return FindIndexOfStringInList2(lst, s)

    for item in s:
        val=FindIndexOfStringInList2(lst, item)
        if val is not None:
            return val

    return None


#=====================================================================================
# Function to find the index of a string in a list of strings
def FindIndexOfStringInList2(lst: list[str], s: str, IgnoreCase=False) -> Optional[int]:
    if not IgnoreCase:
        try:
            return lst.index(s)
        except:
            return None

    # Do it the hard way
    for i, item in enumerate(lst):
        if item.lower() == s.lower():
            return i
    return None








#==================================================================================
def CreateFanacOrgAbsolutePath(fanacDir: str, s: str) -> str:
    return "https://www.fanac.org/fanzines/"+fanacDir+"/"+s

#==================================================================================
# Is at least one item in inputlist also in checklist?  Return the index of the 1st match or None
def CrosscheckListElement(inputList, checkList) -> Optional[int]:
    ListofHits=[FindIndexOfStringInList(checkList, x) for x in inputList]
    n=next((item for item in ListofHits if item is not None), None)
    return n


#==================================================================================
# Create a name for comparison purposes which is lower case and without whitespace or punctuation
# We make it all lower case
# We move leading "The ", "A " and "An " to the rear
# We remove spaces and certain punctuation
def CompressName(name: str) -> str:
    name=name.lower()
    if name.startswith("the "):
        name=name[:4]+"the"
    if name.startswith("a "):
        name=name[:2]+"a"
    if name.startswith("an "):
        name=name[:3]+"an"
    return name.replace(" ", "").replace(",", "").replace("-", "").replace("'", "").replace(".", "").replace("’", "")


#==================================================================================
def CompareCompressedName(n1: str, n2: str) -> bool:
    return CompressName(n1) == CompressName(n2)

#==================================================================================
# Compare two directory paths.  Convery them to canonical form (lc, all "/")
def ComparePathsCanonical(p1: str, p2: str) -> bool:
    p1=os.path.abspath(p1).lower().replace("\\", "/")
    p2=os.path.abspath(p2).lower().replace("\\", "/")

    return p1 == p2


#==================================================================================
# Compare two titles: Ignore case and ignore start or end position of [a, an, the]
def CompareTitles(name1: str, name2: str) -> bool:
    if name1 is None and name2 is None:
        return True
    if name1 is None or name2 is None:
        return False
    name1=name1.lower()
    if name1.startswith("the "):
        name1=name1[4:]+", the"
    name2=name2.lower()
    if name2.startswith("the "):
        name2=name2[4:]+", the"
    if name1 == name2:
        return True
    return False


#=============================================================================
# Remove leading and trailing articles
# "The Hobbit" --> "Hobbit"
# "Odyssey, The" --> "Odyssey"
# Also, "A" and "An"
def RemoveArticles(name: str) -> str:
    lname=name.lower()
    if lname[:4] == "the ":
        return name[4:]
    if lname[-5:] == ", the":
        return name[:-5]
    if lname[:3] == "an ":
        return name[3:]
    if lname[-4:] == ", an":
        return name[:-4]
    if lname[:2] == "a ":
        return name[2:]
    if lname[-3:] == ", a":
        return name[:-3]
    return name

#=============================================================================
# Sometime we need to construct a directory name by changing all the funny characters to underscores.
def FanzineNameToDirName(s: str) -> str:       # MainWindow(MainFrame)
    return re.sub("[^a-zA-Z0-9\-]+", "_", RemoveArticles(s))


#=============================================================================
def CaseInsensitiveCompare(s1: str, s2: str) -> bool:
    if s1 == s2:
        return True
    if (s1 is None and s2 == "") or (s2 is None and s1 == ""):
        return True
    if s1 is None or s2 is None:
        return False  # We already know that s1 and s2 are different
    return s1.lower() == s2.lower()  # Now that we know that neither is None, we can do the lower case compare


# =============================================================================
#   Change the filename in a URL
def ChangeFileInURL(url: str, newFileName: str) -> str:
    u=urllib.parse.urlparse(url)
    p=u[2].split("/")   # Split the path (which may include a filename) into components
    f=p[-1:][0].split(".")     # Split the last component of the path (which may be a filename) into stuff plus an extension
    if len(f) > 1:
        # If there is an extension, then the last component of the path is a filename to be replaced.
        p="/".join(p[:-1])+"/"+newFileName
    else:
        # Otherwise, we just tack on the new filename
        p="/".join(p)+"/"+newFileName

    u=(u[0], u[1], p, u[3], u[4], u[5])
    return urllib.parse.urlunparse(u)


# =============================================================================
# Case insensitive check if a file's extension is in a list of extensions
# The extension can be either a string or a list of strings. Leading '.' optional
def ExtensionMatches(file: str, ext: Union[str, list[str]]) -> bool:
    file=os.path.splitext(file.lower())
    if type(ext) is str:
        ext=[ext]
    for ex in ext:
        if ex[0] != ".":
            ex="."+ex   # Add a leading '.' if necessary
        if file[1] == ex.lower():
            return True
    return False


# =============================================================================
# Format numeric month+year as January 1944
# Note that Month is 1-12
def DateMonthYear(month: int, year: int) -> str:
    months=["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    if month > 0 and year > 0:
        return f"{months[month-1]} {year}"
    if year > 0:
        return str(year)
    if month > 0:
        return months[month]
    return "date?"


# =============================================================================
# Check to see if an argument (int, float or string) is a number
def IsInt(arg: any) -> bool:
    if type(arg) is int:
        return True

    # It's not an integer type.  See if it can be converted into an integer.  E.g., it's a string representation of a number
    with suppress(Exception):
        int(arg)  # We throw away the result -- all we're interested in is if the conversation can be done without throwing an error
        return True

    return False


# =============================================================================
# Convert a string to Int or None w/o throwing exception
def Int(val: str) -> Optional[int]:
    if IsInt(val):
        return int(val)
    return None

# Convert a string to integer, returning 0 when uninterpretable
def Int0(val: str) -> int:
    ret=Int(val)
    if ret is None:
        ret=0
    return ret

def ZeroIfNone(x: Optional[int]):
    return 0 if x is None else x


# =============================================================================
# Check to see if an argument (int, float or string) is a number
def IsNumeric(arg: any) -> bool:
    if type(arg) in [float, int]:
        return True

    # It's not a numeric type.  See if it can be converted into a float.  E.g., it's a string representation of a number
    with suppress(Exception):
        float(arg)    # We throw away the result -- all we're interested in is if the conversation can be done without throwing an error
        return True

    return False


# =============================================================================
# Return true iff a path points to a file which is writeable
def IsFileWriteable(pathname: str) -> bool:
    return os.path.exists(pathname) and os.path.isfile(pathname) and os.access(pathname, os.W_OK)


# =============================================================================
# Return true iff a path points to a file which exists, but is read-only
def IsFileReadonly(pathname: str) -> bool:
    return os.path.exists(pathname) and os.path.isfile(pathname) and not os.access(pathname, os.W_OK)


# =============================================================================
# Set or reset a file's read-only status
def SetReadOnlyFlag(pathname: str, flag: bool) -> None:
    if os.path.exists(pathname):
        if os.path.isfile(pathname):
            writeable=os.access(pathname, os.W_OK)
            if writeable and not flag or not writeable and flag:    # If it's already in the desired state, we're done
                return
            if flag:
                os.chmod(pathname, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)  # Set read-only
            else:
                os.chmod(pathname, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP |stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)  # Set Read/write



# =============================================================================
# Read a list of lines in from a file
# Strip leading and trailing whitespace and ignore lines which begin with a '#'
def ReadList(filename: str, isFatal: bool=False) -> Optional[list[str]]:
    if not os.path.exists(filename):
        if isFatal:
            MessageLog(f"***Fatal error: Can't find {os.getcwd()}/{filename}")
            raise FileNotFoundError
        Log(f"ReadList can't find {os.getcwd()}/{filename}")
        return None
    with open(filename, "r") as f:
        lst=f.readlines()

    lst=[l.strip() for l in lst]  # Strip leading and trailing whitespace
    lst=[l for l in lst if len(l)>0 and l[0]!= "#"]   # Drop empty lines and lines starting with "#"

    lst=[l for l in lst if l.find(" #") == -1] + [l[:l.find(" #")].strip() for l in lst if l.find(" #") > 0]    # (all members not containing " #") +(the rest with the trailing # stripped)

    return lst

# =============================================================================
# Read a file using ReadList and then parse lines from name=value pairs to a defaultdict
def ReadListAsDict(filename: str, isFatal: bool=False) -> DefaultDict[str, str]:
    dict=defaultdict(str)
    lines=ReadList(filename, isFatal=isFatal)
    for line in lines:
        ret=line.split("=", maxsplit=1)
        if len(ret) == 2:
            dict[ret[0]]=ret[1]
    return dict


# =============================================================================
# A wrapper for dict that returns None if item not present.
# With this class you can write parms[key, strdefault] and it will return strdefault if key is not a key
# If CaseInsensntive=True, then keys are stored with case, but are queried case-insensitively.  (E.f., "full name" == "Full Name")
# If IgnoreSpacesCompare=True, then spaces are squeexed out of keys before comaparison
class ParmDict():
    def __init__(self, CaseInsensitiveCompare=False, IgnoreSpacesCompare=False):
        self._parms: dict={}
        self._CaseInsensitiveCompare=CaseInsensitiveCompare
        self._IgnoreSpacesCompare=IgnoreSpacesCompare

    # Get an item.  Returns None if key does not exist and no default value is specified.
    # Call as parms[key] or parms[key, defaultvalue]
    # parms[key] returns None if key is not found
    def __getitem__(self, key: str | tuple[str, str]) -> Optional[str]:
        if type(key) is tuple:
            val=self.GetItem(key[0])
            if val is None:
                val=key[1]
            return val
        return self.GetItem(key)

    def GetItem(self, key: str) -> Optional[str]:
        if self._IgnoreSpacesCompare:
            key=key.replace(" ","")

        if self._CaseInsensitiveCompare:
            rslt=[v for k, v in self._parms.items() if k.lower() == key.lower()]
            if len(rslt) == 0:
                return None
            return rslt[0]

        if key not in self._parms.keys():
            return None
        return self._parms[key]

    def __setitem__(self, key: str, val: str) -> None:
        if self._IgnoreSpacesCompare:
            key=key.replace(" ", "")

        if self._CaseInsensitiveCompare:
            for k, v in self._parms.items():
                if k.lower() == key.lower(): # If the key wasn't present, we eventually fall through to the case sensitive branch.
                    self._parms[k]=val  # We use the old key (case doesn;t matter!) so we don;t have to delete it and then add the new key
                    return

        self._parms[key.strip()]=val

    def __len__(self) -> int:
        return len(self._parms)


    def __iterate_kv(self):
        for item in self._parms.items():
            yield item

    def __iter__(self):
        for key_var in self.__iterate_kv():
            yield key_var[0]

    def keys(self):
        return self.__iter__()

    def values(self):
        for key_var in self.__iterate_kv():
            yield key_var[1]

    def items(self):
        return self.__iterate_kv()

    def Exists(self, key: str) -> bool:
        if self._IgnoreSpacesCompare:
            key=key.replace(" ", "")

        if self._CaseInsensitiveCompare:
            key=key.lower()
            for k in self._parms.keys():
                if key == k.lower():
                    return True
            return False
        return key in self._parms.keys()

    # Take list of lines of the form xxx=yyy and add item yyy to key xxx
    def AppendLines(self, lines: list[str]) -> None:
        for line in lines:
            m=re.match("^([a-zA-Z0-9_ ]+)=(.*)$", line)
            if m:
                self[m.groups()[0].strip()]=m.groups()[1].strip()

    # Append one ParmDict to another
    def Append(self, new: ParmDict) -> None:
        for key, val in new.items():
            self[key]=val


    def Lines(self) -> list[str]:
        return [f"{key} = {val}\n" for key, val in self.items()]


# =============================================================================
# Read a file using ReadList and then parse lines from name=value pairs to a defaultdict
def ReadListAsParmDict(filename: str, isFatal: bool=False) -> ParmDict:
    dict=ParmDict()
    lines=ReadList(filename, isFatal=isFatal)
    for line in lines:
        # Remove everything beyond the first #
        if '#' in line:
            loc=line.find("#")
            line=line[:loc-1].strip()

        ret=line.split("=", maxsplit=1)
        if len(ret) == 2:
            dict[ret[0]]=ret[1]
    return dict


# =============================================================================
# Take a text file and a ParmDict as input.
# Search through the text file and for every instance of [yyy xxx] (where yyy is an arbitrary string with no whitespace and xxx is an arbitrary string, including the empty string).
#
# If yyy exists and no value, replace [yyy xxx] with xxx.
# This basically makes xxx visible iff yyy is in the ParmDict
#
# OTOH, if it is found and does have a value, replace [yyy xxx] with yyy's value.
# This lets you, for instance, replace [Convention Name] with "Confluence 2022"
def ApplyParmDictToString(s: str, parms: ParmDict) -> str:
    out: str=""

    while len(s) > 0:
        s1, val, s2=ParseFirstBracketedText(s, "\[", "]")
        if parms.Exists(val) and len(parms[val]) > 0:
            out+=s1+parms[val]
            s=s2
            continue
        # Look for the first token of val
        if " " in val:
            token1, token2=val.split(" ", 1)
            if parms.Exists(token1) and len(parms[token1]) > 0:
                out+=s1+token2
                s=s2
                continue
        out+=s1+"["+val+"]"
        s=s2

    return out


# =============================================================================
# Interpret a string of Roman numerals into an int
# Better to use roman.fromRoman() if you can, but roman is not supported by Pyinstaller
def InterpretRoman(s: str) -> Optional[int]:
    values={"m":1000, "d":500, "c":100, "l":50, "x":10, "v":5, "i":1}
    val=0
    lastv=0     # Holds the value of the last character processed -- needed for inversions like "XIX"
    s=s.lower().replace(" ", "")[::-1]  # The [::-1] is Python magic which reverses a string
    for c in s:
        if c not in values.keys():
            return None
        v=values[c]
        if v < lastv:
            val=val-v
            continue
        val=val+v
        lastv=v

    return val


# =============================================================================
# Try to interpret a fairly messy string such as those found in fanzine serial numbers as a number (decimal or integer)
#   nnn
#   nnn-nnn
#   nnn.nnn
#   nnnaaa
def InterpretInteger(inputstring: Optional[str]) -> Optional[int]:
    num=InterpretNumber(inputstring)
    if num is None:
        return None
    return int(num)

def InterpretNumber(inputstring: Optional[str]) -> Union[None, int, float]:
    if inputstring is None:
        return None

    inputstring=inputstring.strip()
    if IsInt(inputstring):  # Simple integer
        return int(inputstring)

    # nn-nn (Hyphenated integers which usually means a range of numbers)
    # nnn + dash + nnn
    m=re.match("^([0-9]+)\s*-\s*([0-9]+)$", inputstring)
    if m is not None and len(m.groups()) == 2:
        return int(m.groups()[0])        # We just sorta ignore n2...

    # nn.nn (Decimal number)
    m=re.match("^([0-9]+.[0-9]+)$", inputstring)
    if m is not None and len(m.groups()) == 1:
        return float(m.groups()[0])

    # n 1/2, 1/4 in general, n a/b where a and b are single digit integers
    m=re.match("^([0-9]+)\s+([0-9])/([0-9])$", inputstring)
    if m is not None:
        return int(m.groups()[0])+int(m.groups()[1])/int(m.groups()[2])

    # nnaa (integer followed by letter)
    # nnn + optional space + nnn
    m=re.match("^([0-9]+)\s?([a-zA-Z]+)$", inputstring)
    if m is not None and len(m.groups()) == 2:
        return int(m.groups()[0])
    
    # roman numeral characters
    m=re.match("^([IVXLC]+)$", inputstring)
    if m is not None and len(m.groups()) == 1:
        val=InterpretRoman(m.groups()[0])
        if val is not None:
            return val

    if inputstring is not None and len(inputstring) > 0:
        Log("*** Uninterpretable number: '"+str(inputstring)+"'", True)
    return None


# This is a lot like InterpretNumber(), but it focuses on yielding a number which represents the input for purposes of sorting, and nothing else.
# A pure numbers goes to itself (e.g., 1.5-> 1.5, etc)
# An integer followed by letters goes to a heuristic float (e.g., 32A -> 32.1, 32.b -> 32.3)
# A range goes to something a bit bigger than the first number, so that 29-35 sorts after 29
# The uninterpretable just goes to a Really BigNumber so it sorts last
def SortMessyNumber(inputstring: str) -> float:
    inputstring=inputstring.strip()

    # Empty strings sort first
    if inputstring == "":
        return -99999999

    # Locate any trailing alphabetic characters
    m=re.match("^([0-9,.\-/ ]*)([a-zA-Z ]*)$", inputstring)
    if m is None:
        # Confusing result. Sort last
        return 99999999

    number=m.groups()[0].strip()
    alpha=m.groups()[1].strip()
    if len(number) == 0:
        # We have no leading Arabic numerals, but just *maybe* the text part is Roman numerals
        val=InterpretRoman(alpha)
        if val is not None:
            return val
        # Apparently it's just letters.  These sort last
        return 99999999
    # OK, we have leading numerals.  Do we have trailing letters?
    if len(alpha) > 0:
        # This is a fast-and-loose heuristic.  We'll just look at the first two characters and come up with a number which sorts in the same order
        ordering=" abcdefghijklmnopqurstuvwxyzABCDEFGHIJKLMNOPQURSTUVWXYZ"
        if alpha[0] not in ordering:
            return 99999999
        o1=ordering.index(alpha[0])
        if len(alpha) == 1 or alpha[1] not in ordering:
            return InterpretNumber(number)+o1/100
        o2=ordering.index(alpha[1])
        return InterpretNumber(number)+o1/100+o2/10000
    # So it appears we have a more-or-less pure number
    return InterpretNumber(number)


# A sort function (to be passed in to sorted() or sort()) which sorts into a sensible alphabetic order
# A, An, or The is moved to the end of the name
# Case is ignored
# Leading spaces are ignored
def SortTitle(inputstring: str) -> str:
    inputstring=inputstring.strip().lower()

    # Empty strings sort first
    if inputstring == "":
        return ""

    if inputstring.startswith("a "):
        return inputstring.removeprefix("a ")+", a"
    if inputstring.startswith("an "):
        return inputstring.removeprefix("an ")+", an"
    if inputstring.startswith("the "):
        return inputstring.removeprefix("the ")+", the"

    return inputstring


# ==========================================================
# Normalize a person's name
# Johnson, Lyndon Baines --> Lyndon Baines Johnson
def NormalizePersonsName(name: str) -> str:
    names=UnscrambleNames(name)
    if len(names) == 1:
        return names[0]
    return name

# ==========================================================
# Normalize a person's name
# For now, all we do is flips the lname, stuff to stuff lname
# Lyndon Baines Johnson --> Johnson, Lyndon Baines
def SortPersonsName(name: str) -> str:
    if name is None or name == "":
        return " "

    name=HidePrefixsAndSuffixes(name)   # Need to hide things like Warner, Jr.

    if "," in name:     # If name has a comma, it's probably already in desired order
        return UnhidePrefixsAndSuffixes(name)

    if " " not in name:     # If it's all characters, there's not much to be done
        return UnhidePrefixsAndSuffixes(name)

    # Use <last token>, <other tokens>
    tokens=name.split()
    return UnhidePrefixsAndSuffixes(" ".join([tokens[-1]+","]+tokens[:-1]))


# Two routines to hide and unhide various name prefixes and suffixes
suffixes=[(", Jr.", "qqqJr"), (", jr.", "qqqjr"), (" Jr.", "qqq2Jr"), (" jr.", "qqq2jr"), (" Jr", "qqq3Jr"), (" jr", "qqq3jr"), # With comma & period, with period, with neither
          (", Sr.", "qqqSr"), (", sr.", "qqqsr"), (" Sr.", "qqq2Sr"), (" sr.", "qqq2sr"), (" Sr", "qqq3Sr"), (" sr", "qqq3sr"),
          (", III", "qqqIII"), (" III", "qqq2III"), (", II", "qqqII"), (" II", "qqq2II"),
          (", et al", "qqqetal"), (" et al", "qqq2etal")]
prefixes=[("Van ", "xxxVan"), ("van ", "xxxvan"), ("Von ", "xxxVon"), ("von ", "xxxvon"), ("Del ", "xxxDel"), ("del ", "xxxdel"),
          ("De ", "xxxDe"), ("de ", "xxxde"), ("Le ", "xxxLe"), ("le ", "xxxle")]

def HidePrefixsAndSuffixes(input: str) -> str:
    # We will hide them as "qqq#" where # is the number, below.  This way, they will appear to be part of the name
    for key, val in suffixes:
        input=input.replace(key, val)
    # The same for prefixes.  (Note that Del must precede Ge to prevent mis-matches.)
    for key, val in prefixes:
        input=input.replace(key, val)
    return input

def UnhidePrefixsAndSuffixes(input: str) -> str:
    for key, val in suffixes:
        input=input.replace(val, key)
    for key, val in prefixes:
        input=input.replace(val, key)
    return input


# ==========================================================
# Handle lists of names
def UnscrambleNames(input: str) -> list[str]:
    # A list of names can be Fname [MI] Lname, Fname2 [MI2] Lname2...
    # Names cane be of the form Heinlein, Robert A.
    # Or Harry Warner, Jr.
    #
    # We want to return a list of names in the normal format: John W. Campbell, Jr.

    # Commas are very confusing, so begin by hiding certain constructs which are part of the last name
    input=HidePrefixsAndSuffixes(input)

    # We can now be pretty confident that any commas are separators.  They could be a list: E. E. Smith, Poul Anderson
    # Or an inverted name: de Camp, L. Sprague.
    # We detect the first case because it is always token, token -- never more than one token before the comma.
    # (Note that we've already turned "de camp" into "xxxdecamp" so it's one token.)
    # We decline to handle the ugly case

    # First look for the Asimov, Isaac case
    if input.count(",") == 1:   # Look for a single comma
        tokens=input.split(",")
        if " " not in tokens[0].strip():   # With no interior spaces before the comma
            name=" ".join(tokens[1:])+" "+tokens[0]     # Create a name in normal order
            # Restore the prefixes & suffixes
            name=UnhidePrefixsAndSuffixes(name)
            return [name]   # Return a list of the one name

    # Now deal with a list of names
    names=re.split(", and |, |/| and|&", input)       # delimiters=[", ", "/", " and ", ", and",  "&"]
    return [UnhidePrefixsAndSuffixes(x.strip()) for x in names]

    # For now, these are the only cases we'll try to deal with.
    # Return the input as a single name
    return [input]


# =============================================================================
# Take a possibly ragged list of lists of strings and make all rows the length of the longest by padding with empty strings
def SquareUpMatrix(m: list[list[str]]) -> list[list[str]]:
    lmax=max([len(r) for r in m])
    for r in m:
        if len(r) < lmax:
            r.extend([""]*(lmax-len(r)))
    return m


# =============================================================================
# Take a possibly ragged list of lists of strings and remove any rows filled only with spaces
def RemoveEmptyRowsFromMatrix(m: list[list[str]]) -> list[list[str]]:
    out: list[list[str]]=[]
    for r in m:
        if len("".join(r).strip()) > 0:
            out.append(r)
    return out

# =============================================================================
# Nibble away at a line by applying the pattern with two capture groups to the line
# We return a tuple:
#       The line with the matched portion removed
#       Capture group 1
#       Capture group 2
def Match2AndRemove(inputstr: str, pattern: str) -> tuple[str, Optional[str], Optional[str]]:
    m=re.match(pattern, inputstr)         # Do we match the pattern?
    if m is not None and len(m.groups()) > 0:
        g0=m.groups()[0]                    # There may be either 1 or two groups, but we need to return two matches
        g1=None
        if len(m.groups()) > 1:
            g1=m.groups()[1]
        return re.sub(pattern, "", inputstr), g0, g1  # And delete the matched text
    return inputstr, None, None


# =============================================================================
# Call Log (with isError=True) and then call MessageBox with the error
# This should only be called if logging is in use!
def MessageLog(s: str) -> None:
    Log(s, isError=True)
    MessageBox(s)


# =============================================================================
# Display a message box (needed only for the built/packaged version)
# User sparingly, since the messagebox must be closed by hand and can be annoying.
# It does nothing in the debug version
def MessageBox(s: str, ignoredebugger: bool=False) -> None:
    if not DebuggerIsRunning() or ignoredebugger:
        root = Tk()
        root.withdraw()
        messagebox.showinfo(title=None, message=s)

# =============================================================================
# Display a message box (needed only for the built/packaged version)
# User sparingly, since the messagebox must be closed by hand and can be annoying.
# It does nothing in the debug version
def MessageBoxInput(s: str, ignoredebugger: bool=False) -> str:
    if not DebuggerIsRunning() or ignoredebugger:
        root = Tk()
        root.withdraw()
        return tkinter.simpledialog.askstring("xxx", s)
    return ""

# Same thing with more control
def MessageBoxInput2(title: str="", prompt: str="", ignoredebugger: bool=False, **kwds) -> str:
    if not DebuggerIsRunning() or ignoredebugger:
        root = Tk()
        root.withdraw()
        return tkinter.simpledialog.askstring(title, prompt, **kwds)
    return ""


# =============================================================================
# Are we running under a debugger?
def DebuggerIsRunning() -> bool:
    return sys.gettrace() is not None   # This is an incantation which detects the presence of a debugger


# =============================================================================
# Select a file based on debugger presence
# If debugger is present, use path/fname.  If running as exe, use just fname
# This allows program to be debugged in their own directories, but all run from the same directory
def SelectFileBasedOnDebugger(path: str, fname: str) -> str:
    if not DebuggerIsRunning():
        return fname
    return os.path.join(path, fname)


# =============================================================================
# Text names the app
# msg is the error message
def Bailout(e, msg: str, title: str) -> None:
    Log("exception: "+str(e), isError=True)
    Log("   title: "+title, isError=True)
    Log("   msg: "+msg, isError=True)
    LogClose()
    ctypes.windll.user32.MessageBoxW(0, msg, title, 1)
    raise e


#=============================================================================
# Convert a page name to the old Wikidot canonical format:
#   1st character is upper case, all others are lower case
#   All spans of non-alphanumeric characters are replaced by a single hyphen
def WikidotCanonicizeName(name: str) -> str:
    if len(name) == 0:
        return name
    elif len(name) == 1:
        return name.upper()
    name=name[0].upper()+name[1:].lower()
    name=re.sub("[^a-zA-Z0-9]+", "-", name)
    # Wikidot does not start or end URLs with hyphens
    if name[0] == "-" and len(name) > 1:
        name=name[1:]
    if name[-1] == "-" and len(name) > 1:
        name=name[:-1]
    return name

# =============================================================================
# Convert page names to legal Windows filename
# The characters illegal in Windows filenams will be replaced by ";xxx;" where xxx is a plausible name for the illegal character.
def WikiPagenameToWindowsFilename(pname: str) -> str:
    # "Con" is a special case because it's a reserved Windows (DOS, actually) filename
    if pname.lower() == "con":
        pname=";"+pname+";" # And now handle it normally

    # There's a complicated algorithm for handling uc/lc issues
    # Letters that are the wrong case are followed by a ^^
    # The right case is the 1st character uc and the first character after a space uc, all others lc.
    s=""
    i=0
    while i < len(pname):
        if i == 0:  # Leading char defaults to upper
            if pname[0].isupper() or not pname[0].isalpha():
                s=pname[0]
            else:
                s=pname[0].upper()+"^^"
            i+=1
        elif not pname[i].isalpha():    # Nonalpha characters pass through unchanged
            s+=pname[i]
            i+=1
        elif pname[i-1] == " ":      # First alpha char after a space defaults to upper
            # pname[i] is alpha
            if pname[i].isupper():
                s+=pname[i]         # Upper case in this position passes through
            else:
                s+=pname[i].upper()+"^^"    # Lower case gets a special flag
            i+=1
        else:    # All other chars defaults to lower
            # pname[i] is alpha
            if pname[i].islower():
                s+=pname[i]     # Lower passes through
            else:
                s+=pname[i].lower()+"^^"    # Upper gets converted to lower and flagged
            i+=1
    # Now handle special characters
    return s.replace("*", ";star;").replace("/", ";slash;").replace("?", ";ques;").replace('"', ";quot;").replace("<", ";lt;").replace(">", ";gt;").replace("\\", ";back;").replace("|", ";bar;").replace(":", ";colon;")


# =============================================================================
# Convert a local Windows site file name to a wiki page name
def WindowsFilenameToWikiPagename(fname: str) -> str:
    # First undo the handling of special characters
    fname=fname.replace(";star;", "*").replace(";slash;", "/").replace(";ques;", "?").replace(";quot;", '"').replace(";lt;", "<").replace(";gt;", ">").replace(";back;", "\\").replace(";bar;", "|").replace(";colon;", ":")

    s=""
    i=0
    while i < len(fname):
        if fname[i].isalpha() and len(fname) > i+2:     # Is it a letter which could be flagged?
            if fname[i+1] == "^" and fname[i+2] == "^": # Is it flagged?
                if i == 0:                              # 1st letter is flagged: 'X^^' --> 'x'
                    s+=fname[0].lower()
                    i+=3
                elif fname[i-1] == " ":                 # Flagged letter following space: ' x^^' --> ' x'
                    s+=fname[i].lower()
                    i+=3
                else:                                   # flagged letter not following space: 'ax^^' --> 'aX'
                    s+=fname[i].upper()
                    i+=3
            else:                                       # It is unflagged
                if fname[i-1] == " ":                   # Is it an unflagged letter following space? ' x' --> ' X'
                    s+=fname[i].upper()
                    i+=1
                else:
                    s+=fname[i]                         # stet
                    i+=1
        else:   # Non-letter or unflagged letter not following space: stet
            s+=fname[i]
            i+=1

        # "Con" is a special case because it's a reserved Windows (DOS, actually) filename
        if s.lower() == ";con;":
            return s[1:-1]

    return s

# =============================================================================
# Turn a page name to and from  Wiki canonical form
# Capitalize the first character and turn spaces to underscores
subst={
    "&": "%26",
    "?": "%3F"
    }

def WikiPagenameToWikiUrlname(s: str) -> str:
    if len(s) == 0:
        return s
    out=""
    for c in s:
        if c == " ":
            out+="_"
        elif c in subst.keys():
            out+=subst[c]
        else:
            out+=c

    return out[0].upper()+(out[1:] if len(out) > 1 else "")


#-----------------------------------------------------------------
# Break a Mediawiki link into its components
# [[link#anchor|display text]] --> (link, anchor, display text)
# Make sure that link[0] is upper case
# The brackets are optional. (Inputs of [[link#anchor|display text]] and link#anchor|display text give the same result)
def WikiLinkSplit(s: str) -> tuple[str, str, str]:
    link=""
    anchor=""
    text=""
    m=re.match("(?:\[\[)?"
               "([^|#\]]+)"
               "(#[^|\]]*)*"
               "(\|[^]]*)*"
               "(?:]])?", s)
    # Optional "[["
    # A string not containing "#", "|" or "]" (the link)
    # An optional string beginning with "#" and not containing "|" or "]" (the anchor)
    # An optional string beginning with "|" and not containing "]" (the display text)
    # Optional "]]"
    if m is not None:
        for val in m.groups():
            if val is None:
                continue
            elif val[0] == "#":
                anchor=val[1:]
            elif val[0] == "|":
                text=val[1:]
            else:
                link=val[0].upper()+val[1:]
    return link, anchor, text


#-----------------------------------------------------------------
# Turn underscores to spaces
# Note that Mediawiki canonicalization is not reversable.  We will turn underscores to spaces, but otherwise do nothing.
def WikiUrlnameToWikiPagename(s: str) -> str:
    for key, val in subst.items():
        s=s.replace(val, key)
    return s.replace("_", " ")


#-----------------------------------------------------------------
# Convert a Mediawiki redirect to a page name
def WikiRedirectToPagename(s: str) -> str:

    s=s[0].upper()+s[1:]
    s=unescape(s)
    l=s.find("#")
    if l > -1:
        s=s[:l]
    return s.replace("  ", " ")


#-----------------------------------------------------------------
# Extract the link from a bracketed name
# If there are brackets, ignore everything outside the brackets
# Take [[stuff] or [[stuff|display text]] or [[stuff#substuff]] and return stuff
# If there are no brackets, just return the input
def WikiExtractLink(s: str) -> str:
    b1=s.find("[[")
    b2=s.find("]]")
    if b2 > b1 > -1:
        s=s[b1+2:b2]
    return s.split("|")[0].split("#")[0].strip()

#-----------------------------------------------------------------
# Split a string into a list of string.  The split is done on *spans* of the input characters.
def SplitOnSpan(chars: str, s: str) -> list[str]:
    pattern=re.compile("["+chars+"]")
    # replace the matched span of <chars> with a single char from the span string
    return [x for x in re.sub(pattern, chars[0], s).split(chars[0]) if len(x) > 0]

#------------------------------------------------------------------
# Split a really long string of output for printing as text.
def SplitOutput(f, s: str):
    strs=s.split(",")
    while len(strs) > 0:
        out=""
        while len(strs) > 0 and (len(out)+len(strs[0])) < 80 or (len(out) == 0 and len(strs[0]) >= 80):
            out=out+strs[0].strip()+", "
            del strs[0]
        f.write(f"    {out}\n")