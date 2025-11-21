from __future__ import annotations
from typing import Any, DefaultDict
import os
import sys
import ctypes
import unicodedata
import re
import stat
import json
import html

from unidecode import unidecode
from datetime import datetime
import tkinter
from tkinter import Tk, messagebox
from tkinter.simpledialog import askstring
import urllib.parse
from html import escape, unescape
from contextlib import suppress
from collections import defaultdict


from Log import Log, LogClose, LogError


#=======================================================
# Locate all matches to the pattern and remove them
# Numgroups is the number of matching groups in the pattern
#   If numGroups=0, we just replace the matched text without returning it
#   If numGroups=1, the output list is a list of strings matched
#   If numGroups>1, the output list is a list of lists, with the sublist being whatever is matched by the groups -- we don't necessarily return everything that has been matched
# Return a list of matched strings and the remnant of the input string

# NOTE: Text to be removed *must* be part of a group!
def SearchAndReplace(pattern: str, inputstr: str, replacement: str, numGroups: int=1, caseinsensitive: bool=False, ignorenewlines: bool=False) -> tuple[list[str], str]:

    flags=0
    if caseinsensitive:     # This nonsense is due to an old error
        flags=re.IGNORECASE
    if ignorenewlines:
        flags=flags | re.DOTALL

    # Keep looping and removing matched material until the match fails
    found: list[str] | list[list[str]]=[]
    while True:
        # Look for a match
        m=re.search(pattern, inputstr, flags=flags)

        # If none is found, return the results
        if m is None:
            return found, inputstr
        # We found something. Append it to the list of found snippets
        # When numGroups is zero we just replace the text without saving it.
        if numGroups == 1:
            found.append(m.groups()[0])
        elif numGroups > 1:
            found.extend([x for x in m.groups()])
        # Replace the found text
        inputstr=re.sub(pattern, replacement, inputstr, 1, flags=flags)


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
def SearchAndExtractBounded(source: str, startpattern: str, endpattern: str, Flags=0) -> tuple[str|None, str]:
    m=re.search(startpattern, source)
    if m is None:
        return None, source
    loc=m.span()[1]
    m=re.search(endpattern, source[loc:], flags=Flags)
    if m is None:
        return None, source
    return source[loc:loc+m.span()[0]], source[loc+m.span()[1]+1:]


#=======================================================
# Locate and return a chunk of text matched by a pattern.  The patten has three capturing groups: (start)(middle)(end)
# Remove the starting and ending patterns and all they contain.
# Return a tuple consisting of (middle),  all of the input before (start)+after (end)
# The default is to search *everying, ignoring line boundaries and case.
# When there is no match, (middle) is returned as None
def SearchExtractAndRemoveBounded(source: str, pattern: str, Flags=re.IGNORECASE | re.DOTALL) -> tuple[str|None, str]:
    m=re.search(pattern, source, flags=Flags)
    if m is None:
        return None, source
    middle=m.groups()[1]
    source=re.sub(pattern, "", source, count=1)
    return middle, source


# Remove *all* the matches
def SearchExtractAndRemoveBoundedAll(source: str, pattern: str, Flags=re.IGNORECASE | re.DOTALL) -> tuple[list[str], str]:
    matches=[]
    while True:
        middle, source=SearchExtractAndRemoveBounded(source, pattern, Flags=Flags)
        if middle is None:
            return matches, source
        matches.append(f"<td{middle}")


#=======================================================
# Take a list of strings and turn it into an english list.  E.g. ["A", "B", "C"] --> "A, B, and C"
def TurnPythonListIntoWordList(plist: list[str]) -> str:
    return MakeNiceCommaSeparatedList(plist)
    # if len(plist) == 0:
    #     return ""
    # if len(plist) == 1:
    #     return plist[0]
    #
    # out=""
    # for pl in plist[:-1]:
    #     if len(out) > 0:
    #         out+=", "
    #     out+=pl
    # out+=" and"+plist[-1]
    # return out


# Turn a list of str into a comm-separated list
# Skip empty strings and spaces-only strings
def MakeNiceCommaSeparatedList(input: list[str], AppendPeriod=False, UseAnd=False, Delimiter=", ") -> str:
    lastitem=""
    if UseAnd:
        if len(input) > 1:
            lastitem=input[-1]
            input=input[:-1]

    stuff=[x.strip() for x in input if x is not None and x.strip() != ""]
    stuff=Delimiter.join(stuff)

    if UseAnd and len(lastitem) > 0:
        stuff+= " and "+lastitem.strip()

    if AppendPeriod:
        if len(stuff) > 0:
            stuff+="."
    return stuff

#=======================================================
# Try to make the input numeric
# Note that if it fails, it returns what came in.
def ToNumeric(val: None | int | float | str) -> None | int | float:
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


# # Take a string and find the first hyperlink.
# # Return a tuple of: <material before>, <link>, <display text>, <material after>
# def FindLinkInString(s: str) -> tuple[str, str, str, str]:
#     # Get rid of any class=stuff crud
#     #s=re.sub(r'class=".+?"', "", s, count=10, flags=re.IGNORECASE)
#     pat="^(.*?)<a\s+href=['\"]https?(.*?)>(.*?)</a>(.*)$"
#     m=re.match(pat, s, flags=re.RegexFlag.IGNORECASE)
#     if m is None:
#         return s, "", "", ""
#     return m.groups()[0], m.groups()[1], m.groups()[2], m.groups()[3]


# Take a string and find the first hyperlink.
# Return a tuple of: <material before>, <link>, <display text>, <material after>
# This version does not require
def FindLinkInString(s: str) -> tuple[str, str, str, str]:
    # Get rid of any class=stuff crud
    s=re.sub(r'class=".+?"', "", s, count=10, flags=re.IGNORECASE)
    pat=r"^(.*?)<a\s+href=['\"](https?:)?(.*?)['\"]>(.*?)</a>(.*)$"
    m=re.match(pat, s, flags=re.IGNORECASE|re.DOTALL)
    if m is None:
        return s, "", "", ""
    return m.groups()[0], m.groups()[2], m.groups()[3], m.groups()[4]


# Take a string and find the first href.
# Return a tuple of: <material before>, <link>, <display text>, <material after>
# This version does not require
def FindHrefInString(s: str) -> tuple[str, str, str, str]:
    # Get rid of any class=stuff crud
    s=re.sub(r'class=".+?"', "", s, count=10, flags=re.IGNORECASE)
    m=re.match(r"^(.*?)<a +href=['\"](https?:)?(.*?)['\"]>(.*)</a>.*$", s, flags=re.IGNORECASE|re.DOTALL)
    if m is None:
        m=re.match(r"^(.*?)<a +href=['\"](https?:)?(.*?)['\"]>(.*)$", s, flags=re.IGNORECASE|re.DOTALL)     # Some rows lack the trailing "</A>" !
        if m is None:
            return s, "", "", ""
    if len(m.groups()) == 5:
        return m.groups()[0], m.groups()[2], m.groups()[3], m.groups()[4]
    elif len(m.groups()) == 4:
        return m.groups()[0], m.groups()[2], m.groups()[3], ""

    assert False



# ==================================================================================
# Scan the input string looking for a pair of HTML comments of the form '<!-- fanac-<tag> start> ... <fanac-<tag> end>'
# separate the string into three p[ices: Before the start tag, between the tags, after the end tag.
# Return None if the tags are not found.
def FindFanacTagsInHTML(s: str, opentag: str, closetag) -> tuple[str | None, str, str]:

    # Scan for the tags
    locopen=s.find(opentag)
    if locopen < 0:
        return None, "", ""
    locclose=s.find(closetag, locopen+len(opentag))
    if locclose < locopen:
        return None, "", ""

    start=s[:locopen]
    middle=s[locopen+len(opentag): locclose]
    end=s[locclose+len(closetag):]
    return start, middle, end


# ==================================================================================
# Scan the input string looking for a pair of HTML comments of the form '<!-- fanac-<tag> start--> ... <!--fanac-<tag> end-->'
# separate the string into three pieces: Before the start tag, between the tags, after the end tag.
# Replace the middle part with insert
# Return the empty string if the tags are not found.
def InsertHTMLUsingFanacStartEndCommentPair(s: str, tag: str, insert: str) -> str:
    opentag=f"<!-- fanac-{tag} start-->"
    closetag=f"<!-- fanac-{tag} end-->"
    start, mid, end=FindFanacTagsInHTML(s, opentag, closetag)
    if start is None:
        LogError(f"Unable to locate tag pair {opentag}....{closetag}")
        return ""
    return start+opentag+insert+closetag+end

#--------------
# Scan for a pair of fanac comments and return the contents (but not the tags themselves)
def ExtractHTMLUsingFanacStartEndCommentPair(s: str, tag: str) -> str:
    opentag=f"<!-- fanac-{tag} start-->"
    closetag=f"<!-- fanac-{tag} end-->"
    _, mid, _=FindFanacTagsInHTML(s, opentag, closetag)
    return mid


# ==================================================================================
# Scan the input string looking for a pair of HTML comments of the form '<!--<tag>--> ... <!--<tag>-->'
# separate the string into three pieces: Before the start tag, between the tags, after the end tag.
# Replace the middle part with insert
# Return the empty string if the tags are not found.
def InsertHTMLUsingFanacTagCommentPair(s: str, tag: str, insert: str) -> str:
    boundingComment=f"<!--{tag}-->"
    start, mid, end=FindFanacTagsInHTML(s, boundingComment, boundingComment)
    if start is None:
        LogError(f"Unable to locate tag pair {boundingComment}....{boundingComment}")
        return ""
    return start+boundingComment+insert+boundingComment+end

#--------------
# Scan for a pair of fanac comments and return the contents (but not the tags themselves)
# REturn the empty string if the tag is not found
def ExtractHTMLUsingFanacTagCommentPair(s: str, tag: str) -> str:
    boundingComment=f"<!--{tag}-->"
    _, mid, _=FindFanacTagsInHTML(s, boundingComment, boundingComment)
    return mid

#
# def InsertInvisibleTextUsingFanacStartEndCommentPair(s: str, tag: str, insert: str) -> str:
#     opentag=f"<!-- fanac-{tag} start-->"
#     closetag=f"<!-- fanac-{tag} end-->"
#     start, mid, end=FindFanacTagsInHTML(s, opentag, closetag)
#     if start is None:
#         LogError(f"Unable to locate tag pair <fanac-{tag} start-->end>")
#         return ""
#     return start+opentag+"<!-- "+insert+" -->"+closetag+end


# def ExtractInvisibleTextUsingFanacComments(s: str, tag: str) -> str:
#     mid=ExtractHTMLUsingFanacStartEndCommentPair(s, tag)
#     return mid.removeprefix("<!--").removesuffix("-->").strip()


# The comment is <!--fanac-<tag><stuff>-->, where tag is the ID and stuff is the payload
def InsertInvisibleTextInsideFanacComment(s: str, tag: str, insert: str) -> str:
    return re.sub(fr"<!--\s*fanac-{tag}\s*(.*?)\s*-->", f"<!-- fanac-{tag} {insert} -->", s, count=1,flags=re.IGNORECASE|re.DOTALL)

def ExtractInvisibleTextInsideFanacComment(s: str, tag: str) -> str:
    m=re.search(fr"<!--\s*fanac-{tag}\s*(.*?)\s*-->", s, flags=re.IGNORECASE|re.DOTALL)
    if m is None:
        return ""
    return m.groups()[0].strip()


# Insert text between HTML comments:  <!tag-->stuff<!tag-->
def InsertBetweenHTMLComments(s: str, tag: str, val: str) -> str:
    # Look for a section of the input string surrounded by  "<!--- tag -->" and replace it all by val
    return re.sub(rf"<!--\s*{tag}\s*-->(.*?)<!--\s*{tag}\s*-->", f"<!--{tag}-->{val}<!--{tag}-->", s, flags=re.IGNORECASE|re.DOTALL|re.MULTILINE)

def ExtractBetweenHTMLComments(s: str, tag: str) -> str:
    m=re.search(rf"<!--\s*{tag}\s*-->(.*?)<!--\s*{tag}\s*-->", s, flags=re.IGNORECASE|re.DOTALL)
    if m is None:
        return ""
    return m.groups()[0].strip()


# =============================================================================
# Converting between page names and poge file names (urlname) in MediaWiki
# Name -> filename
#   Turn spaces to underscores
#   Capitalize the first letter
#   Map certain forbidden characters to %escape sequences
# Note that Mediawiki canonicalization is not reversable.
# We reserve the right to improve on the accuracy of the translation as issues are discovered
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

def WikiUrlnameToWikiPagename(s: str) -> str:
    for key, val in subst.items():
        s=s.replace(val, key)
    return s.replace("_", " ")




#==================================================================================
# Make a properly formatted link to a Fancy 3 page
# If the second argument is present, use the first as the LinkTargetsURL and the second as the display text.
# If only one is present, use it for both
def MakeFancyLink(fancyName: str, displayName: str=None) -> str:
    if displayName is None:
        displayName=fancyName

    return f'<a href="https://fancyclopedia.org/{WikiPagenameToWikiUrlname(fancyName)}">{displayName}</a>'


# Take a string containing a fancy link and convert the link's url back to ordinary text, returning:
# link|display text (if they are different
# display text (if they are the same
def UnmakeFancyLink(link: str) -> list[str]:
    m=re.match(r"^(.*?)<a href=\"?https?://fancyclopedia.org/(.*?)\"?>(.*?)</a>(.*)$", link)
    if m is None:
        return [WikiUrlnameToWikiPagename(link)]

    link=m.groups()[1]
    text=m.groups()[2]

    return WikiUrlnameToWikiPagename(link)+"|"+text


# Take a string containing a fancy link and remove the link, leaving the link text
def RemoveFancyLink(link: str) -> str:
    m=re.match(r"^(.*?)<a href=\"?http[s]?://fancyclopedia.org/.*?\"?>(.*?)</a>(.*)$", link)
    if m is None:
        return link

    return " ".join(m.groups())


#==================================================================================
# Return a properly formatted link
# Depending on flags, the LinkTargetsURL may get 'https://' or 'http://' prepended.
# If it is a PDF it will get view=Fit appended
# PDFs may have #page=nn attached
def FormatLink(url: str, text: str, ForceHTTP: bool=False, ForceHTTPS: bool=False, QuoteChars=False) -> str:
    # TODO: Do we need to deal with turning blanks into %20 whatsits?

    # If a null LinkTargetsURL is provided, don't return a hyperlink
    if url is None or url == "":
        return text

    # '#' can't be part of an href as it is misinterpreted
    # But it *can* be part of a link to an anchor on a page or a part of a pdf reference.
    # Look for #s in a LinkTargetsURL *before* a .pdf extension and convert them to %23s
    if '#' in url:
        m=re.match(r"(.*)(\.pdf.*)", url, re.IGNORECASE)
        if m is not None:
            url=m.groups()[0].replace("#", "%23")+m.groups()[1]
    url=UnicodeToHtml(url)

    if QuoteChars:
        url=urllib.parse.quote(url)

    # If the url points to a pdf, add '#view=Fit' to the end to force the PDF to scale to the page
    if ".pdf" in url and not "view=Fit" in url:
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
def UnformatLinks(s: str) -> str|None:
    if s is None or s == "":
        return s

    try:
        # Convert substrings of the form '<a href="'(stuff1)'>'(stuff2)'</a>'  to (stuff2)
        s=re.sub(r'(<a\s+href=".+?">)(.+?)(</a>)', "\\2", s)

        # And then there are Mediawiki redirects
        s=re.sub(r'(<a\s+class=".+?">)(.+?)(</a>)', "\\2", s)
    except:
        pass
    return s


#-------------------------------------------------------------
# Change the 1st character to uppercase and leave the rest alone
def CapitalizeFirstChar(s: str) -> str:
    return s[0].upper()+s[1:]


# ==================================================================================
# Format an integer for typical Fanac.org numbering:  nnnn. but nn,nnn for longer
def FormatCount(i: int) -> str:
    if i < 10000:
        return f"{i}"
    return f"{i:,}"

# -------------------------------------------------------------------------
# Take a string and a value and add appropriate pluralization to string -- used in calls to WriteTable
def Pluralize(val: int, s: str, Spacechar: str=" ") -> str:
    return f"{FormatCount(val)}{Spacechar}{s}{'s' if val != 1 else ''}"

#-------------------------------------------------------------
# We have a list of preferred column headers.  This routine converts common variations to the preferred form.
# If the input is not opne of these cpmmon variations, it is simple retured with the 1st character capitalized.
# All matching is case-insensitive.
def CanonicizeColumnHeaders(header: str) -> str:
    # 2nd item is the canonical form for fanac.org and fancyclopedia series tables
    translationTable={
                        "published" : "Date",
                        "(date)" : "Date",
                        "author" : "Editor",
                        "editors" : "Editor",
                        "editor/s" : "Editor",
                        "fanzine" : "IssueName",
                        "title" : "IssueName",
                        "zine" : "IssueName",
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
                        "pdf" : "PDF",
                        "pp," : "Pages",
                        "pp." : "Pages",
                        "pub" : "Publisher",
                        "scanned by": "Scanned",
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
    m=re.match(fr"\w*<{bra}>(.*)</{bra}>\w*$", s)
    if m is None:
        return False, s
    return True, m.groups()[0]


#=====================================================================================
# Find the first <bracket>bracketed text</bracket> located.  Return:  leading, enclosed, and trailing text
def ParseFirstStringBracketedText(s: str, bracket: str, IgnoreCase=False) -> tuple[str, str, str]:
    # We need to escape certain characters before substituting them into a RegEx pattern
    bracket=bracket.replace("[", r"\[").replace("(", r"\(").replace("{", r"\{")

    pattern=rf"^(.*?)<{bracket}[^>]*>(.*?)</{bracket}>(.*)$"
    flags=re.DOTALL
    if IgnoreCase:
        flags=flags|re.IGNORECASE
    m=re.match(pattern, s,  flags)
    if m is None:
        return s, "", ""

    return m.group(1), m.group(2), m.group(3)

#=====================================================================================
# Find text bracketed by <b>...</b> and replace it with new text
# The bracketing text must enclose everything else in the string -- this, essentially, removes the first layer of the onion.
# Return the (possibly) modified text and a bool to indicate if anything was found
def RemoveTopBracketedText(s: str, bracket: str, stripHtml: bool=True) -> tuple[str, bool]:

    pattern=fr"^\s*<{bracket}>(.*?)</{bracket}>\s*$"
    m=re.search(pattern, s,  flags=re.DOTALL)     # Do it multiline
    if m is None:
        return s, False

    return m.groups()[0], True


#=====================================================================================
# Find text bracketed by <b>...</b> and replace it with new text
# Return the (possibly) modified text and a bool to indicate if anything was found
def FindAndReplaceBracketedText(s: str, bracket: str, replacement: str, stripHtml: bool=True, caseInsensitive=False) -> tuple[str, bool]:

    pattern=f"<{bracket}>(.*?)</{bracket}>"
    flags=re.DOTALL
    if caseInsensitive:
        flags=flags | re.IGNORECASE
    m=re.search(pattern, s,  flags=flags)     # Do it multiline
    if m is None:
        return s, False
    # match=m.groups()[0]
    # if stripHtml:
    #     match=RemoveAllHTMLTags(match)      #TODO: Why is this here!??
    s2=re.sub(pattern, replacement, s, flags=flags, count=1)
    return s2, True


#=====================================================================================
# Find first text bracketed by pre<anything>...</anything>post
# Return a tuple consisting of:
#   Any leading material (pre)
#   The name ("anything") of the first pair of brackets found
#   The contents ("...") of the first pair of brackets found
#   The remainder (post) of the input string
# Note that this is a *non-greedy* scanner
# Note also that it is not very tolerant of errors in the bracketing, just dropping things on the floor
# (Was: FindNextBracketedText() )
def FindNextBracketedText(s: str) -> tuple[str, str, str, str]:

    pattern="^(.*?)<(?P<tag>[a-z0-9][^>]*?)>(.*?)</(?P=tag)>(.*)$"
    m=re.search(pattern, s,  flags=re.DOTALL|re.IGNORECASE)
    if m is None:
        return s, "", "", ""

    x=m.group(1), m.group(2), m.group(3), m.group(4)
    return x


#=====================================================================================
# Find text bracketed by <b>...</b>
# Return the contents of the first pair of the specified brackets found and the remainder of the input string
def FindBracketedText2(s: str, tag: str, caseInsensitive=False, includeBrackets=False) -> tuple[str, str]:
    # We want to remove any leading or trailing whitespace
    m=re.match(r"^\s*(.*?)\s*$", s, re.DOTALL)
    if m is not None:
        s=m.group(1)
    return FindBracketedText(s, tag, stripHtml=False, caseInsensitive=caseInsensitive, includeBrackets=includeBrackets)


def FindBracketedText(s: str, tag: str, stripHtml: bool=True, stripWhitespace: bool=False, caseInsensitive=False, includeBrackets=False) -> tuple[str, str]:

    if includeBrackets:
        pattern=f"(<{tag}.*?>.*?</{tag}>)"
    else:
        pattern=f"<{tag}.*?>(.*?)</{tag}>"

    if stripWhitespace:
        pattern=fr"\s*{pattern}\s*"
    flags=re.DOTALL
    if caseInsensitive:
        flags=flags | re.IGNORECASE
    m=re.search(pattern, s,  flags)
    if m is None:
        return "", s
    pre=s[:m.regs[0][0]]
    match=s[m.regs[1][0]:m.regs[1][1]]  # The matched part -- the only group of the pattern
    post=s[m.regs[0][1]:]
    if stripHtml:
        match=RemoveAllHTMLTags(match)
    return match, pre+post


#---------------------------------------------------
# Find a bracket of the form <xxxx ....> and replace it
# Find a bracket beginning with tag xxxx. Replace the whole thing, brackets, content and all.
def FindAndReplaceSingleBracketedText(input: str, tag: str, replacement: str, caseInsensitive=True) -> str:
    flags=re.DOTALL
    if caseInsensitive:
        flags=flags|re.IGNORECASE

    m=re.search(f"(<{tag}.*?>)", input,  flags)
    if m is None:
        return input
    pre=input[:m.regs[0][1]]
    post=input[m.regs[0][1]:]
    return pre+replacement+post


#---------------------------------------------------
# Does the input string contain a balanced set of brackets with text inside?
# The brackets overall do not need to be balanced as long as there is a substring with balanced brackets.
def ContainsBracketedText(s: str) -> bool:

    m=re.search("<[^<>]+>", s)
    if m is None:
        return False
    return True


#=====================================================================================
# Find the first bracket located.  Return the leading, enclosed, and trailing text
def ParseFirstBracketedText(s: str, b1: str, b2: str) -> tuple[str, str, str]:
    # We need to escape certain characters before substituting them into a RegEx pattern
    b1=b1.replace("[", r"\[").replace("(", r"\(").replace("{", r"\{")

    pattern=r"^(.*?)"+b1+"(.+?)"+b2+"(.*)$"
    m=re.search(pattern, s,  re.DOTALL)
    if m is None:
        return s, "", ""

    return m.group(1), m.group(2), m.group(3)


#=====================================================================================
# Remove hyperlinks leaving the link text behind
# E.g., <a http:xxx.com>abc</a>  ==> abc
def RemoveHyperlink(s: str, repeat: bool=False) -> str:
    return RemoveHyperlinkContainingPattern(s, "[^<>]*?", repeat, flags=re.IGNORECASE)



#=====================================================================================
# Remove hyperlinks leaving the link text behind
# E.g., <a http:xxx.com>abc</a>  ==> abc
def RemoveHyperlinkContainingPattern(s: str, pattern: str, repeat: bool=False, flags: re.RegexFlag | None=None) -> str:
    while True:
        m=re.match(f"(.*?)<a.*?>({pattern})</a>(.*)$", s, flags)
        if m:
            s=m.groups()[0]+m.groups()[1]+m.groups()[2]
            if repeat:
                continue
        break
    return s


#=====================================================================================
# Find text bracketed by [[]]
# Return the contents of the first pair of brackets found
def FindWikiBracketedText(s: str) -> str:

    m=re.search(r"\[\[(:?.+)]]", s)
    if m is None:
        return ""
    return m.groups()[0]


#=====================================================================================
# Remove an outside matched pair of <tag> </tag> from a string, returning the inside
def StripSpecificTag(s: str, tag: str, CaseSensitive=False, Number=1)-> str:
    while Number > 0:
        pattern=fr"^<{tag}>(.*)</{tag}>$"
        if CaseSensitive:
            m=re.match(pattern, s)
        else:
            m=re.match(pattern, s, re.IGNORECASE)
        if m is None:
            break
        Number-=1
        s=m.groups()[0]

    return s

#=====================================================================================
# Remove a matched pair of external <brackets> <containing anything> from a string, returning the inside
def StripExternalTags(s: str)-> str|None:
    m=re.match("^<.*>(.*)</.*>$", s)
    if m is None:
        return None
    return m.groups()[0]


#=====================================================================================
# Remove a matched pair of <brackets> <containing anything> from a string, returning the inside
def StripWikiBrackets(s: str)-> str:
    m=re.match(r"^\[\[(.*)]]$", s)
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
    return RemoveAccents("".join(re.sub(r"[?*&%$#@'><:;,.{}\][=+)(^!\s]+", "_", name)))


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
# Turn all strings of whitespace (including HTMLish whitespace) to a single space
def CompressWhitespace(s: str) -> str:
    return re.sub(r"\s+", " ", RemoveFunnyWhitespace(s))


#=====================================================================================
def CompressAllWhitespaceAndRemovePunctuation(s: str) -> str:
    s=re.sub(r"[.,\-?!_*\'\";:]+", " ", s)
    return CompressAllWhitespace(s)

#=====================================================================================
# There are HTML codes which display characters which we'd prefer to see as ASCII. So change them.
def ConvertHTMLishCharacters(s: str) -> str:
    return s.replace("&#8209;", "-").replace("&nbsp;", " ")


#=====================================================================================
# Turn some whitespace escape characters into spaces
def RemoveFunnyWhitespace(s: str) -> str:
    return RemoveHTMLishWhitespace(s.replace("\xc2\xa0", " ").replace(u"\u00A0", " "))


#=====================================================================================
# Replace certain strings which amount to whitespace in html with whitespace
def RemoveHTMLishWhitespace(s: str, replacement: str=" ") -> str:
    return re.sub(r"<br>|</br>|<br/>|&nbsp;", replacement, s, flags=re.IGNORECASE)

def RemoveLinebreaks(s: str, replacement: str="") -> str:
    return re.sub(r"<br>|</br>|<br/>|\n", replacement, s, flags=re.IGNORECASE | re.DOTALL)


#=====================================================================================
# Remove <Hx>-type brackets from a string.
def RemoveHxTags(s: str) -> str:
    return re.sub(r"</?h\d>", "", s, flags=re.IGNORECASE)

#=====================================================================================
def CompressAllWhitespace(s: str) -> str:
    return CompressWhitespace(RemoveHTMLishWhitespace(RemoveFunnyWhitespace(s)))


#=====================================================================================
# An older version of this
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
# Remove the top level of html tags.  I.e., <a>xx<>/a>yy<b><c>zzz</c></b>  -->  yy<c>zzz</c>
def RemoveTopLevelHTMLTags(s: str, LeaveLinks: bool=False) -> str:
    if not LeaveLinks:
        return re.sub(r'<([a-zA-Z0-9]+)[^>]*>(.+?)</\1>', r"\2", s)
    return re.sub(r'<([b-z0-9][a-z0-9]*)[^>]*?>(.*?)</\1>', r"\2", s)

#=====================================================================================
# Remove all HTML-like tags (No need for them to be balanced!)
def RemoveAllHTMLLikeTags(s: str) -> str:
    vv=re.sub(r"(</?.*?/?>)", "", s)
    return vv


#=====================================================================================
# Change all occurances of </br> and <br/> to <br> (case insensitive)
def RegularizeBRTags(s: str) -> str:
    return re.sub(r"<(/br|br/)>", "<br>", s, flags=re.IGNORECASE)


#=====================================================================================
# Change"&nbsp;" to space
def ChangeNBSPToSpace(s: None | str) -> None | str | list[str]:
    if s is None:
        return None
    if len(s) == 0:
        return s

    if isinstance(s, str):
        return s.replace("&nbsp;", " ").replace("&NBSP;", " ")      #TODO: Maybe this should be done by regex?

    return [c.replace("&nbsp;", " ").replace("&NBSP;", " ") for c in s]


#=====================================================================================
# Convert the unicode of a str to a string which can be used in an HTML file
def UnicodeToHtml(s: str) -> str:
    # Convert the text to ascii and then used decode to turn it back into a str
    s=escape(s).encode('ascii', 'xmlcharrefreplace').decode()
    # But this overachieves and converts <, > and & to html.  Reverse this.
    return s.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")


#=====================================================================================
# Convert the unicode of a str to a string which can be used in an HTML file
def UnicodeToHtml2(s: str) -> str:
    # Convert the text to ascii and then use decode to turn it back into a str
    return s.encode(encoding='ascii', errors="xmlcharrefreplace").decode()

def HtmlToUnicode2(s: str) -> str:
    return html.unescape(s)
    #return s.encode(encoding='ascii', errors="xmlcharrefreplace").decode()



#=====================================================================================
# Function to generate the proper kind of path.  (This may change depending on the target location of the output.)
def RelPathToURL(relPath: str) -> str|None:
    if relPath is None:
        return None
    if relPath.startswith("http"):  # We don't want to mess with foreign URLs
        return None
    return "https://www.fanac.org/"+os.path.normpath(os.path.join("fanzines", relPath)).replace("\\", "/")


#=====================================================================================
# Given the URL of a directory in which we have an HTML filee with a reference and given the reference (which may or may not be local) generate a proper URL
def MergeURLs(dirURL: str, pageFilename: str) -> str:
    parsedFilename=urllib.parse.urlparse(pageFilename)

    if len(parsedFilename.scheme) > 0 or len(parsedFilename.netloc) > 0:  # If the PageFilename begins with http: or a network location, we just return it
        return urllib.parse.urlunparse(("https", parsedFilename.netloc, parsedFilename.path, parsedFilename.params, parsedFilename.query, parsedFilename.fragment))

    # OK, apparently we have a filename which is not a full URL
    # WE'll intelligently prepend the directory URL to flesh it out
    parsedDirURL=urllib.parse.urlparse(dirURL)
    pp=parsedDirURL.path+"/"+parsedFilename.path
    pn=parsedDirURL.netloc
    ps=parsedDirURL.scheme
    if len(ps) == 0:
        ps="https"

    # # Is it just a pagename alone, without any path info?
    # # Then we add it to the directory's URL to form the new URL
    # if "/" not in pp and "\\" not in pp:
    #     pp=parsedDirURL.path+"/"+pp
    #     ps=parsedDirURL.scheme

    parsedFilename=ps, pn, pp, parsedFilename.params, parsedFilename.query, parsedFilename.fragment
    return urllib.parse.urlunparse(parsedFilename)


# =====================================================================================
# Function to find the index of one or more strings in a list of strings.  Stop with the first one found.
#  E.g., find the first occurance of "Mailing" or "Mailings" or "APA Mailing" in a list of possible column headers
def FindIndexOfStringInList(lst: list[str], s: str|list[str], IgnoreCase=False) -> int|None:
    if isinstance(s, str):  # If it's a single string, just go with it!
        return FindIndexOfStringInList2(lst, s)

    for item in s:
        val=FindIndexOfStringInList2(lst, item, IgnoreCase=IgnoreCase)
        if val is not None:
            return val
    return None


#=====================================================================================
# Function to find the index of a specific string in a list of strings
def FindIndexOfStringInList2(lst: list[str], s: str, IgnoreCase=False) -> int|None:
    if not IgnoreCase:
        try:
            return lst.index(s)
        except:
            return None

    # Do it the hard way
    for i, item in enumerate(lst):
        if item.casefold() == s.casefold():
            return i
    return None



#==================================================================================
def CreateFanacOrgAbsolutePath(fanacDir: str, s: str) -> str:
    return "https://www.fanac.org/fanzines/"+fanacDir+"/"+s


#==================================================================================
# Is at least one item in inputlist also in checklist?  Return the index of the 1st match or None
def CrosscheckListElement(inputList: str |list[str], checkList: list[str]) -> int|None:
    if isinstance(inputList, str):
        inputlist=[inputList]
    ListofHits=[FindIndexOfStringInList(checkList, x) for x in inputList]
    n=next((item for item in ListofHits if item is not None), None)     #TODO: Could this be done by replacing next() with [0]?
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
# But "The" all by itself is kept.
# Also, "A" and "An"
def RemoveArticles(name: str) -> str:
    lname=name.lower()
    # If someone has been too clever (I'm talking about you, Harter!) and used "The" is the title, we need to handle this specially
    if lname.strip() == "the" or lname.strip() == "an" or lname.strip() == "a":
        return name
    if lname.strip() == ", the" or lname.strip() == ", an" or lname.strip() == ", a":
        return name

    # Normal cases
    if lname[:4] == "the ":
        return name[4:].strip()
    if lname[-5:] == ", the":
        return name[:-5].strip()
    if lname[:3] == "an ":
        return name[3:].strip()
    if lname[-4:] == ", an":
        return name[:-4].strip()
    if lname[:2] == "a ":
        return name[2:].strip()
    if lname[-3:] == ", a":
        return name[:-3].strip()
    return name.strip()


# Move a leading article to the end of a string
# E.g., "The Hobbit" --> "Hobbit, The"
def ArticleToEnd(s: str) -> str:
    articles=["the", "a", "an"]
    ls=s.lower()
    for a in articles:
        if ls.startswith(a+" "):
            return s[len(a)+1:]+", "+s[:len(a)]
    return s

# Move a trailing article to the front of a string
# Make sure it's capitalized.
# E.g., "Hobbit, the" --> "The Hobbit"
def ArticleToFront(s: str) -> str:
    s=s.strip()
    if s == "":
        return ""

    articles=["the", "a", "an"]
    ls=s.lower()
    mixedcase=s[0] == s[0].upper()
    for a in articles:
        if ls.endswith(" "+a):
            s=a[0].upper()+a[1:]+" "+s[:-(len(a)+2)]
            break
    # If the string is mixed case, be sure to capitalize any leading article
    if mixedcase:
        for a in articles:
            if s.startswith(a):
                s=s[0].upper()+s[1:]
                break
    return s

#=============================================================================
# Sometime we need to construct a directory name by changing all the funny characters to underscores.
def FanzineNameToDirName(s: str) -> str:       # MainWindow(MainFrame)
    return re.sub("[^a-zA-Z0-9\\-]+", "_", RemoveArticles(s))


#=============================================================================
# None counts as the empty string
def CaseInsensitiveCompare(s1: str, s2: str) -> bool:
    if s1 == s2:
        return True
    if (s1 is None and s2 == "") or (s2 is None and s1 == ""):
        return True
    if s1 is None or s2 is None:
        return False  # We already know that s1 and s2 are different
    return s1.casefold() == s2.casefold()  # Now that we know that neither is None, we can do the case-insensitive compare


# =============================================================================
#   Change the filename in a LinkTargetsURL
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
    return str(urllib.parse.urlunparse(u))


# =============================================================================
# Case insensitive check if a file's extension is in a list of extensions
# The extension can be either a string or a list of strings. Leading '.' optional
def ExtensionMatches(file: str, ext: str | list[str]) -> bool:
    file=os.path.splitext(file.lower())
    if isinstance(ext, str):
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
# Add a timestamp to a filename
def TimestampFilename(fname: str) -> str:
    head, tail=os.path.split(fname)
    if head != "":
        head+="/"
    filename, ext=os.path.splitext(tail)
    tstampedFilename=f"{filename} - {datetime.now():%Y-%m-%d %H-%M-%S}{ext}"
    return head+tstampedFilename


def JoinPathWithSimpleSingleSlashes(p1: str|list[str], p2: str|list[str]= "", p3: str|list[str]= "") -> str:
    if isinstance(p1, str):
        p=[p1]
    else:
        p=p1

    if p2 is not None and p2 != "":
        if isinstance(p2, str):
            p.append(p2)
        else:
            p.extend(p2)

    if p3 is not None and p3 != "":
        if isinstance(p3, str):
            p.append(p3)
        else:
            p.extend(p3)

    out="/".join(p)
    return out.replace("\\", "/").replace("//", "/").replace("//", "/")



class SplitPath:
    def __init__(self, path: str):
        hd, sp, tl=SplitFilepath(path)

        self.Tail: str=tl  # Trailing slashes

        self.Head: str=""  # Leading dots and slashes
        # First the drive, if any
        if len(hd) > 0 and len(sp[0]) > 0 and hd[0][-1] == ":":
            self.Drive=sp[0]
            hd=hd[1:]

        # Then whatever leading slashes and dots

        self.Head: str=""
        if len(hd) > 0 and len(sp[0]) > 0:
            out=""
            hd0=hd[0]
            if len(hd0) > 0 and hd0[0] == ".":
                hd0=hd0[1:]
                out+="."
                hd=hd[1:]
            if len(hd0) > 0 and hd0[0] == ".":
                hd0=hd0[1:]
                out+="."
            if hd0[0] == "/" or hd0[0] == r"\\":
                out+="/"
            self.Head=out

        self.Tail: str=""
        # self.Tail: str=""  # Trailing slashes
        # if len(sp) > 0 and len(sp[-1]) > 0 and (sp[-1][0] == "/" or sp[-1][0] == r"\\"):
        #     self.Tail=sp[-1]
        #     sp=sp[:-1]

        self.Filename: str=""   # The filename
        if len(sp) > 0 and len(sp[-1]) > 0 and "." in sp[-1]:
            self.Filename=sp[-1]
            sp=sp[:-1]

        # The path to the filename as a list of strings
        self.Path: list[str]=sp # A list of directories


    def __str__(self):
        return self.Head + "/".join(self.Path) + self.Tail + ("/"+ self.Filename) if self.Filename != "" else ""

    @property
    def FilePath(self) -> str:
        fp="/".join(self.Path)
        if self.Filename != "":
            fp+="/"+self.Filename
        return fp

    @property
    def IsEmpty(self) -> bool:
        return self.Head == "" and self.Tail == "" and self.Filename == "" and (self.Path == [] or self.Path == "")

    @property
    def IsFilename(self) -> bool:
        return self.Head == "" and self.Tail == "" and self.Filename != "" and self.Path == []

    @property
    def IsRelative(self) -> bool:
        return len(self.Head) > 0 and self.Head[0] == "."
    @IsRelative.setter
    def IsRelative(self, value: bool):
        self.Head=""


# =============================================================================
# Split a file path into a list of components
#       --> head [path] tail
# a/b/c  --> [a, b, c]      (str --> list [str])
# /a/b/c --> / [a, b, c]
# a --> [a]
# a/ --> [a] /
# a/b//c --> [a, b, c]
# r"a/b\\c" --> [a, b, c]
# r"//c/d" --> // [c, d]
# r"/c/d" --> / [c, d]
# r"/c/d/" --> / [c, d] /

def SplitFilepath(filepath: str) -> tuple[str, list[str], str]:
    head=filepath
    if len(head) == 0:
        return ("", [], "")

    # Replace all backslashes by forward slashes
    head=head.replace("\\", "/")

    drive, rest=os.path.splitdrive(head)

    # Look for leading slashes
    startswith=None
    if rest[0] == "/":
        startswith="/"
        rest=rest[1:]
    if len(rest) > 0 and rest[0:1] == "//":
        startswith="//"
        rest=rest[2:]
    if startswith is None:
        startswith=drive
    else:
        startswith=drive+startswith

    # Look for trailing slashes
    endswith=None
    if len(rest) > 0 and rest[-1] == "/":
        endswith="/"
        rest=rest[:-1]

    # Now parse what's left
    path=[]
    while True:
        rest, tail=os.path.split(rest)
        path.insert(0, tail)     # Prepend it
        if rest is None or rest == "" or rest == "/" or rest == "//" or rest == "":
            break

    return (startswith, path, endswith)


# =============================================================================
# Check to see if an argument (int, float or string) is a number
def IsInt(arg: Any) -> bool:
    if isinstance(arg, int):
        return True

    # It's not an integer type.  See if it can be converted into an integer.  E.g., it's a string representation of a number
    with suppress(Exception):
        int(arg)  # We throw away the result -- all we're interested in is if the conversation can be done without throwing an error
        return True

    return False


# =============================================================================
# Convert a string to Int or None w/o throwing exception
def Int(val: str) -> int|None:
    if IsInt(val):
        return int(val)
    return None

# Convert a string to integer, returning 0 when uninterpretable
def Int0(val: str|int) -> int:
    ret=Int(val)
    if ret is None:
        ret=0
    return ret

# =============================================================================
# Convert a string to float, returning 0 when uninterpretable
def Float0(arg: Any) -> float:
    if isinstance(arg, float) or isinstance(arg, int):
        return float(arg)

    # It's not a numeric type.  See if it can be converted into float.  E.g., it's a string representation of a number
    with suppress(Exception):
        return float(arg)

    return 0    # Apparently it can't be handled



def ZeroIfNone(x: int|None) -> int:
    return 0 if x is None else x


# =============================================================================
# Check to see if an argument (int, float or string) is a number
def IsNumeric(arg: Any) -> bool:
    if isinstance(arg, float) or isinstance(arg, int):
        return True

    # It's not a numeric type.  See if it can be converted into a float.  E.g., it's a string representation of a number
    with suppress(Exception):
        float(arg)    # We throw away the result -- all we're interested in is if the conversation can be done without throwing an error
        return True

    return False


# =============================================================================
# Move a block of elements within a list
# All element numbers are logical
# startingIndex is the 1st index of the start of the block to be moved
# Numcols is the number of elements to be moved
# Newcol is the target position to which oldrow is moved.
# Note: to Swap cols 5 and 6, the arguments would be 5, 1, 6: Take 1 column starting at col 5 and move it to where col 6 is.
# NOTE: Does not do a move in place
def ListBlockMove(lst: list[str], startingIndex: int, numElements: int, targetIndex: int) -> list[str]:
    numCols=len(lst)
    #print(f"{startingIndex=}  {numElements=}  {targetIndex=}  {numCols=}")
    if startingIndex < 0 or targetIndex < 0 or startingIndex+numElements > numCols or targetIndex+numElements > numCols:
        return lst

    end=startingIndex+numElements-1
    out=[""]*numCols
    #print(f"MoveCols: {startingIndex=}  {end=}  {numElements=}  {targetIndex=}")
    if targetIndex < startingIndex:
        # Move earlier
        i1=list(range(0, targetIndex))
        i2=list(range(targetIndex, startingIndex))
        i3=list(range(startingIndex, end+1))
        i4=list(range(end+1, numCols))
        #print(f"{i1=}  {i2=}  {i3=}  {i4=}")
    else:
        # Move Later
        i1=list(range(0, startingIndex))
        i2=list(range(startingIndex, end+1))
        i3=list(range(end+1, end+1+targetIndex-startingIndex))
        i4=list(range(end+1+targetIndex-startingIndex, numCols))
        #print(f"{i1=}  {i2=}  {i3=}  {i4=}")

    tpermuter: list[int]=i1+i3+i2+i4
    permuter: list[int]=[-1]*len(tpermuter)     # This next bit of code inverts tpermuter. (There ought to be a more elegant way to generate it!)
    for i, r in enumerate(tpermuter):
        permuter[r]=i

    if isinstance(lst, list) and len(lst) > 0:
        if isinstance(lst[0], tuple):
            # The input is a list of (cols, col) tuples (e.g., AllowCellEdits)
            for i, (row, col) in enumerate(lst):
                try:
                    lst[i]=(permuter[row], col)
                except:
                    pass
        else:
            # The inout is a list of cells (like a cols)
            # Just move the elements
            temp: list=[None]*numCols
            for i in range(numCols):
                out[permuter[i]]=lst[i]

    return out


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
def ReadList(filename: str, isFatal: bool=False) -> list[str]:
    if not os.path.exists(filename):
        if isFatal:
            MessageLog(f"***Fatal error: Can't find {os.getcwd()}/{filename}")
            raise FileNotFoundError
        Log(f"ReadList can't find {os.getcwd()}/{filename}")
        return []
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
        self._parms: dict[str, Any]={}
        self._CaseInsensitiveCompare=CaseInsensitiveCompare
        self._IgnoreSpacesCompare=IgnoreSpacesCompare
        self._sourcefilename=None

    def __str__(self) -> str:
        return ",   ".join([f"'{key}'='{val}'" for key, val in self.items()])

    # Get an item.  Returns None if key does not exist and no default value is specified.
    # Call as parms[key] or parms[key, defaultvalue]
    # parms[key] returns None if key is not found
    def __getitem__(self, key: str | tuple[str, str]):
        if isinstance(key, tuple):
            val=self.GetItem(key[0])
            if val is None:
                val=key[1]
            return val
        return self.GetItem(key)


    def GetItem(self, key: str):
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


    # Given a key and a default value, return the key's value.
    # If the key does not exist, create it and set its value to default and then return defaiult
    def SetIfMissingAndGet(self, key: str, default: str):
        if key in self:
            return self[key]
        self[key]=default
        return default


    def __setitem__(self, key: str, val: Any) -> None:
        if self._IgnoreSpacesCompare:
            key=key.replace(" ", "")

        if self._CaseInsensitiveCompare:
            for k, v in self._parms.items():
                if k.lower() == key.lower(): # If the key wasn't present, we eventually fall through to the case-sensitive branch.
                    self._parms[k]=val  # We use the old key (case doesn't matter!) so we don;t have to delete it and then add the new key
                    return

        self._parms[key.strip()]=val

    def __contains__(self, key):
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


    def __len__(self) -> int:
        return len(self._parms)


    @property
    def SourceFilename(self) -> str:
        return self._sourcefilename


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
# Get a parameter i present or log an error message and terminate if parameter missing and no default supplied
def GetParmFromParmDict(parameters: ParmDict, name: str, default: str=None) -> Any:
    val=parameters[name]
    if not val:
        if default is not None:
            val=default
        else:
            MessageLog(f"GetParmFromParmDict: Can't find a parameter '{name}' in {parameters.SourceFilename}\nProgram terminated.")
            exit(999)
    return val

# =============================================================================
# Read a file using ReadList and then parse lines from name=value pairs to a defaultdict
def ReadListAsParmDict(filename: str, isFatal: bool=False, CaseInsensitiveCompare: bool=False, IgnoreSpacesCompare: bool=False) -> ParmDict | None:
    dict=ParmDict(CaseInsensitiveCompare=CaseInsensitiveCompare, IgnoreSpacesCompare=IgnoreSpacesCompare)
    lines=ReadList(filename, isFatal=isFatal)
    if len(lines) == 0:
        return None
    for line in lines:
        # Remove everything beyond the first #
        if '#' in line:
            loc=line.find("#")
            line=line[:loc-1].strip()

        # There are two kinds of lines, "=" lines and "{}" lines
        # The former are simple: A=B assigns B and everything else following the =-sign to a dictionary entry "A"
        # The latter attempts to interpret the text following as json which will be appended to settings
        val=""
        if len(line) > 5 and line[0] == "{" and line[-1] == "}":
            d=json.loads(line)
            if d is None:
                LogError(f"settings.ReadListAsParmDict(): could not interpret '{line}'")
                continue
            dict.Append(d)
        else:
            ret=line.split("=", maxsplit=1)
            if len(ret) != 2:
                LogError(f"settings.ReadListAsParmDict(): could not interpret '{line}'")
                continue
            dict[ret[0]]=ret[1]

    dict._sourcefilename=filename  # Save filename of source of parameters for debugging use

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
        s1, val, s2=ParseFirstBracketedText(s, r"\[", "]")
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
def InterpretRoman(s: str) -> int|None:
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
def InterpretInteger(inputstring: str|None) -> int|None:
    num=InterpretNumber(inputstring)
    if num is None:
        return None
    return int(num)

def InterpretNumber(inputstring: str|None) -> None | int | float:
    if inputstring is None:
        return None

    inputstring=inputstring.strip()
    if IsInt(inputstring):  # Simple integer
        return int(inputstring)

    # nn-nn (Hyphenated integers which usually means a range of numbers)
    # nnn + dash + nnn
    m=re.match(r"^([0-9]+)\s*-\s*([0-9]+)$", inputstring)
    if m is not None and len(m.groups()) == 2:
        return int(m.groups()[0])        # We just sorta ignore n2...

    # nn.nn (Decimal number)
    m=re.match("^([0-9]+.[0-9]+)$", inputstring)
    if m is not None and len(m.groups()) == 1:
        return float(m.groups()[0])

    # .nn (Decimal number -- no leading digits)
    m=re.match("^(.[0-9]+)$", inputstring)
    if m is not None and len(m.groups()) == 1:
        return float(m.groups()[0])

    # n 1/2, 1/4 in general, n a/b where a and b are single digit integers
    m=re.match(r"^([0-9]+)\s+([0-9])/([0-9])$", inputstring)
    if m is not None:
        return int(m.groups()[0])+int(m.groups()[1])/int(m.groups()[2])

    # n 1/2, 1/4 in general, n a/b where a and b are single digit integers
    m=re.match(r"^([0-9]+)\s+([0-9]+)/([0-9]+)$", inputstring)
    if m is not None:
        return int(m.groups()[0])+int(m.groups()[1])/int(m.groups()[2])

    # nnaa (integer followed by letter)
    # nnn + optional space + nnn
    m=re.match(r"^([0-9]+)\s?([a-zA-Z]+)$", inputstring)
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
    m=re.match(r"^([0-9,.\-/ ]*)([a-zA-Z ]*)$", inputstring)
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
# Take an input string and check for "yes" or "no" (case insenstive, abbreviations allowed.
# Return "yes" or "no" or "unknown" depending on what's found
def YesNoMaybe(s: str) -> str:
    if s is None:
        return "unknown"
    s=s.strip().lower()
    if s == "yes" or s == "y" or s == "true":
        return "yes"
    if s == "no" or s == "n" or s == "false":
        return "no"
    return "unknown"


# ==========================================================
# Normalize a person's name
# Johnson, Lyndon Baines --> Lyndon Baines Johnson
def NormalizePersonsName(name: str) -> str:
    names=UnscrambleListOfNames(name)
    if len(names) == 1:
        return names[0]
    return name

# ==========================================================
# Normalize a person's name
# For now, all we do is flips the 'stuff lname' to 'lname, stuff'
# Lyndon Baines Johnson --> Johnson, Lyndon Baines
def SortPersonsName(name: str, IsLowerCaseOnly=False) -> str:
    if name is None or name == "":
        return " "

    name=HidePrefixsAndSuffixes(name, IsLowerCaseOnly=IsLowerCaseOnly)   # Need to hide things like Warner, Jr.

    if "," in name:     # If name has a comma, it's probably already in lname, fname  order
        return UnhidePrefixsAndSuffixes(name, IsLowerCaseOnly-IsLowerCaseOnly)

    if " " not in name:     # If it's all non-whitespace characters, there's not much to be done
        return UnhidePrefixsAndSuffixes(name, IsLowerCaseOnly=IsLowerCaseOnly)

    # Use <last token>, <other tokens>
    tokens=name.split()
    return UnhidePrefixsAndSuffixes(" ".join([tokens[-1]+","]+tokens[:-1]), IsLowerCaseOnly=IsLowerCaseOnly)


# Two routines to hide and unhide various name prefixes and suffixes
suffixesLC=[(", jr.", "qqqjr"), (" jr.", "qqq2jr"), (", jr", "qqq3jr"), (" jr", "qqq4jr"), # With comma & period, with period, with comma, with neither
          (", sr.", "qqqsr"), (" sr.", "qqq2sr"), (", sr", "qqq3sr"), (" sr", "qqq4sr"),
          (", iii", "qqqiii"), (" III", "qqq2iii"), (", II", "qqqii"), (" II", "qqq2ii"),
          (", et al", "qqqetal"), (" et al", "qqq2etal"), (" et. al.", "qqq3etal")]
suffixesUC=[(", Jr.", "qqqJr"), (" Jr.", "qqq2Jr"), (", Jr", "qqq3Jr"), (" Jr", "qqq4Jr"),  # With comma & period, with period, with comma, with neither
          (", Sr.", "qqqSr"), (" Sr.", "qqq2Sr"), (", Sr", "qqq3Sr"), (" Sr", "qqq4Sr"),
          (", III", "qqqIII"), (" III", "qqq2III"), (", II", "qqqII"), (" II", "qqq2II")]

prefixesLC=[(" van ", " van_"), (" von ", " von_"), (" del ", " del_"), (" de ", " de_"), (" le ", " le_")]
prefixesUC=[(" Van ", " Van_"), (" Von ", " Von_"), (" Del ", " Del_"),  (" De ", " De_"), (" Le ", " Le_")]

# Note that we can get a performance boost if we know that the input text is already all lower case.
def HidePrefixsAndSuffixes(input: str, IsLowerCaseOnly=False) -> str:
    # We will hide them as "qqq#" where # is the number, below.  This way, they will appear to be part of the name
    for key, val in suffixesLC:
        input=input.replace(key, val)
    if not IsLowerCaseOnly:
        for key, val in suffixesUC:
            input=input.replace(key, val)
    # The same for prefixes.  (Note that Del must precede Ge to prevent mis-matches.)
    for key, val in prefixesLC:
        input=input.replace(key, val)
    if not IsLowerCaseOnly:
        for key, val in prefixesUC:
            input=input.replace(key, val)
    return input

# Undo the above hiding
def UnhidePrefixsAndSuffixes(input: str, IsLowerCaseOnly=False) -> str:
    for key, val in suffixesLC:
        input=input.replace(val, key)
    if not IsLowerCaseOnly:
        for key, val in suffixesUC:
            input=input.replace(val, key)
    # The same for prefixes.  (Note that Del must precede Ge to prevent mis-matches.)
    for key, val in prefixesLC:
        input=input.replace(val, key)
    if not IsLowerCaseOnly:
        for key, val in prefixesUC:
            input=input.replace(val, key)
    return input


def FlattenPersonsNameForSorting(s: str) -> str:
    return RemoveNonAlphanumericChars(unidecode(SortPersonsName(s.casefold(), IsLowerCaseOnly=True)), LeaveSingleQuote=True)


def FlattenTextForSorting(s: str, RemoveLeadingArticles: bool=False) -> str:
    s=RemoveNonAlphanumericChars(unidecode(s.casefold()))     # Since we don't care about O'Neil, we don't need to fuss about single quotes
    if RemoveLeadingArticles:
        s=RemoveArticles(s)
    return s


def RemoveNonAlphanumericChars(s: str, LeaveSingleQuote: bool=False) -> str:

    out=""
    for c in s:
        if c.isalpha():
            out+=c
        elif c.isdigit():
            out+=c
        elif c == " ":
            out+=c
        elif c == "'" and LeaveSingleQuote:
            out+=c
        # Everything else is ignored

    return out

# ==========================================================
# Handle lists of names
def UnscrambleListOfNames(input: str) -> list[str]:
    # A list of names can be Fname [MI] Lname, Fname2 [MI2] Lname2...
    # Names cane be of the form Heinlein, Robert A.
    # Or Harry Warner, Jr.
    #
    # We want to return a list of names in the normal format: John W. Campbell, Jr.

    # We may need to deal with html that should not be treated as syntax o as part of the name
    # needsEncoding=False
    # encoded=HtmlToUnicode2(input)
    # if input != encoded:
    #     needsEncoding=True
    #     input=encoded

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
            # if needsEncoding:
            #     name=UnicodeToHtml2(name)
            return [name]   # Return a list of the one name

    # Now deal with a list of names
    names=re.split(", and |, |/| and|&", input)       # delimiters=[", ", "/", " and ", ", and",  "&"]
    names=[UnhidePrefixsAndSuffixes(x.strip()) for x in names]
    # if needsEncoding:
    #     names=[UnicodeToHtml2(x) for x in names]
    # In certain cases (e.g., "Del Coger") the first name is interpreted as a prefix and is left with a trailing '_'.  Turn it into a space
    return [x.replace("_", " ") for x in names]

    # For now, these are the only cases we'll try to deal with.
    # Return the input as a single name
    #return [input]


# Split on pattern, but ", Jr." and suchlike should not be detached
def SplitListOfNamesOnPattern(s: str, pattern: str) -> list[str]:

    # Commas are very confusing, so begin by hiding certain constructs which are part of some last names
    # Note that this uses the _ to stand for stuff we want to treat as a monolith, so we can't include _ in the patter of splitters
    s=HidePrefixsAndSuffixes(s)

    # We can now be pretty confident that any remaining commas are separators.
    # Use the pattern to split the string
    # an example of a pattern is:   r", and |,|/|;|and |&|\n|<br>"
    names=re.split(pattern, s)       # delimiters=[", ", "/", " and ", ", and",  "&"]
    names=[UnhidePrefixsAndSuffixes(x.strip()) for x in names]
    names=list(filter(None, names))     # Drop emtry strings from list
    # In certain cases (e.g., the name "Del Coger") the first name is interpreted as a prefix and is left with a trailing '_'.  Turn it into a space
    return [x.replace("_", " ") for x in names]


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
def Match2AndRemove(inputstr: str, pattern: str) -> tuple[str, str|None, str|None]:
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
def MessageBox(s: str, ignoredebugger: bool=False, Title=None) -> None:
    if not DebuggerIsRunning() or ignoredebugger:
        root = Tk()
        root.withdraw()
        messagebox.showinfo(title=Title, message=s)

# =============================================================================
# Display a message box (needed only for the built/packaged version)
# Use sparingly, since the messagebox must be closed by hand and can be annoying.
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
    if e is not None:
        LogError("exception: "+str(e))
    else:
        LogError("Failure")
    LogError("   title: "+title)
    LogError("   msg: "+msg)
    LogClose()
    ctypes.windll.user32.MessageBoxW(0, msg, title, 1)
    if e is None:
        sys.exit(666)
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

#-----------------------------------------------------------------
# Break a Mediawiki link into its components
# [[link#anchor|display text]] --> (link, anchor, display text)
# Make sure that link[0] is upper case
# The brackets are optional. (Inputs of [[link#anchor|display text]] and link#anchor|display text give the same result)
def WikiLinkSplit(s: str) -> tuple[str, str, str]:
    link=""
    anchor=""
    text=""
    m=re.match(r"(?:\[\[)?"
               r"([^|#\]]+)"
               r"(#[^|\]]*)*"
               r"(\|[^]]*)*"
               r"(?:]])?", s)
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
    pattern=re.compile(rf"[{chars}]")
    # replace the matched span of <chars> with a single char from the span string
    return [x for x in re.sub(pattern, chars[0], s).split(chars[0]) if len(x) > 0]


def SplitOnAnyChar(chars: str, s: str) -> list[str]:
    return re.split(rf"[{chars}]*", s)


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


# ------------------------------------------------------------------
# Split a string based on spans of <br>, </br>, <br/>, /n, \n
def SplitOnSpansOfLineBreaks(s: str) -> list[str]:
    # Turn spans of /n or \n into a single <br>
    s=re.sub(r"([\\/]n)+", "<br>", s)

    # Split on <br> in all its forms
    ss=re.split(r"</?br/?>", s, flags=re.IGNORECASE)

    # Trim leading and trailing spaces, drop empty members
    ss=[x.strip() for x in ss if len(x.strip()) > 0]
    return ss

# =============================================================================================
# Try to interpret a complex string as serial information
# If there's a trailing Vol+Num designation at the end of a string, interpret it.
#  leading=True means that we don't try to match the entire input, but just a greedy chunk at the beginning.
#  strict=True means that we will not match potentially ambiguous or ill-formed strings
# complete=True means that we will only match the *complete* input (other than leading and trailing whitespace).

# We accept:
#       ...Vnn[,][ ]#nnn[ ]
#       ...nnn nnn/nnn      a number followed by a fraction
#       ...nnn/nnn[  ]      vol/num
#       ...rrr/nnn          vol (in Roman numerals)/num
#       ...nn.mm
#       ...nn[ ]
#
#  Return value: Leading stuff (presumably a name), Vol#, Num, NumSuffix
#       If it is not Vol/num, it's a whole number witch is returned in Num with Vol=""
def ExtractTrailingSequenceNumber(s: str, complete: bool = False, IgnoreRomanNumerals=False) -> tuple[str, str, str, str]:
    s=s.strip()  # Remove leading and trailing whitespace
    #Log(f"ExtractTrailingSequenceNumber({s})")

    # First look for a Vol+Num designation: Vnnn #mmm
    # # Leading junk
    # Vnnn + optional whitespace
    # #nnn + optional single alphabetic character suffix
    m=re.match(r"^(.*?)V(\d+)\s*#(\d+)(\w?)$", s)
    if m is not None and len(m.groups()) in [3, 4]:
        ns=""
        if len(m.groups()) == 4:
            ns=m.groups()[3]
        return m.groups()[0].strip(), m.groups()[1], m.groups()[2], ns

    #
    #  Vol (or VOL) + optional space + nnn + optional comma + optional space
    # + #nnn + optional single alphabetic character suffix
    m=re.match(r"^(.*?)V[oO][lL]\s*(\d+)\s*#(\d+)(\w?)$", s)
    if m is not None and len(m.groups()) in [3, 4]:
        ns=None
        if len(m.groups()) == 4:
            ns=m.groups()[2]
        return m.groups()[0].strip(), m.groups()[1], m.groups()[2], ns

    # Now look for nnn nnn/nnn (fractions!)
    # nnn + mandatory whitespace + nnn + slash + nnn * optional whitespace
    m=re.match(r"^(.*?)(\d+)\s+(\d+)/(\d+)$", s)
    if m is not None and len(m.groups()) == 4:
        return m.groups()[0].strip(), "", m.groups()[1]+" "+m.groups()[2]+"/"+m.groups()[3], ""

    # Now look for nnn/nnn (which is understood as vol/num
    # Leading stuff + nnn + slash + nnn * optional whitespace
    m=re.match(r"^(.*?)(\d+)/(\d+)$", s)
    if m is not None and len(m.groups()) == 3:
        return m.groups()[0].strip(), m.groups()[1], m.groups()[2], ""

    # Now look for xxx, where xxx is in Roman numerals
    # Leading whitespace + roman numeral characters + whitespace
    if not IgnoreRomanNumerals:
        m=re.match(r"^(.*?)([IVXLC]+)$", s)  # TODO: the regex detects more than just Roman numerals.  We need to bail out of this branch if that happens and not return
        if m is not None and len(m.groups()) == 2:
            return m.groups()[0].strip(), "", str(InterpretRoman(m.groups()[1])), ""

    # Next look for nnn-nnn (which is a range of issue numbers; only the start is returned)
    # Leading stuff + nnn + dash + nnn
    m=re.match(r"^(.*?)(\d+)-(\d+)$", s)
    if m is not None and len(m.groups()) == 3:
        return m.groups()[0].strip(), "", m.groups()[1], ""

    # Next look for #nnn
    # Leading stuff + nnn
    m=re.match(r"^(.*?)#(\d+)$", s)
    if m is not None and len(m.groups()) == 2:
        return m.groups()[0].strip(), "", m.groups()[1], ""

    # Now look for a trailing decimal number
    # Leading characters + single non-digit + nnn + dot + nnn + whitespace
    # the ? makes * a non-greedy quantifier
    m=re.match(r"^(.*?)(\d+\.\d+)$", s)
    if m is not None and len(m.groups()) == 2:
        return m.groups()[0].strip(), "", m.groups()[1], ""

    if not complete:
        # Now look for a single trailing number
        # Leading stuff + nnn + optional single alphabetic character suffix + whitespace
        m=re.match(r"^(.*?)([0-9]+)([a-zA-Z]?)\s*$", s)
        if m is not None and len(m.groups()) in [2, 3]:
            ws=None
            if len(m.groups()) == 3:
                ws=m.groups()[1].strip()
            return m.groups()[0].strip(), "", m.groups()[1], ws

        # Now look for trailing Roman numerals
        # Leading stuff + mandatory whitespace + roman numeral characters + optional trailing whitespace
        if not IgnoreRomanNumerals:
            m=re.match(r"^(.*?)\s+([IVXLC]+)\s*$", s)
            if m is not None and len(m.groups()) == 2:
                return m.groups()[0].strip(), "", str(InterpretRoman(m.groups()[1])), ""

    # No good, return failure
    return s, "", "", ""


def DropTrailingSequenceNumber(s: str) -> str:
    val=ExtractTrailingSequenceNumber(s, complete=True, IgnoreRomanNumerals=True)

    # If we find anything, return it
    if val[0] == "" and len(val[1]) > 0 and len(val[2]) > 0 and val[3] == "":
        return val[1]

    # Now look for a single trailing decimal number, possibly preceded by a #
    m=re.match(r"^\s*(.*?)( #)?(\d+)\s*$", s)
    if m is not None and len(m.groups()) >= 2:
        return m.groups()[0].strip()

    # No go. Just return the input, stripped.
    return s.strip()