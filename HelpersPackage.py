import os
import sys
import ctypes
import unicodedata
from tkinter import Tk, messagebox
import urllib.parse
from typing import Union, Tuple, Optional, List
from html import escape, unescape
from contextlib import suppress
import re

from Log import Log, LogClose


#=======================================================
# Locate all matches to the pattern and remove them
# Numgroups is the number of matching groups in the pattern
#   If numGroups=0, we just replace the matched text without returning it
#   If numGroups=1, the output list is a list of strings matched
#   If numGroups>1, the output list is a list of lists, with the sublist being whatever is matched by the groups -- we don't necessarily return everything that has been matched
# Return a list of matched strings and the remnant of the input string
def SearchAndReplace(pattern: str, inputstr: str, replacement: str, numGroups: int=1, caseinsensitive=False) -> Tuple[List[str], str]:
    found: Optional[List[str], List[List[str]]]=[]
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
            found.append(m.groups())
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
def SearchAndExtractBounded(source: str, startpattern: str, endpattern: str) -> Tuple[Optional[str], str]:
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


#==================================================================================
# Return a properly formatted link
# Depending on flags, the URL may get 'https://' or 'http://' prepended.
# If it is a PDF it will get view=Fit appended
# PDFs may have #page=nn attached
def FormatLink(url: str, text: str, ForceHTTP: bool=False, ForceHTTPS: bool=False) -> str:
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

#==================================================================================
# Take a string and strip out all hrefs, retaining all the text.
def UnformatLinks(s: str) -> str:
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

#-------------------------------------------------------------
def CanonicizeColumnHeaders(header: str) -> str:
    # 2nd item is the cannonical form
    translationTable={
                        "published" : "Date",
                        "editors" : "Editor",
                        "zine" : "Issue",
                        "fanzine" : "Issue",
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
    try:
        return translationTable[header.replace(" ", "").replace("/", "").lower()]
    except:
        return header[0].upper()+header[1:]

#=====================================================================================
# Scan for text bracketed by <bra>...</bra>
# Return True/False and remaining text after <bra> </bra> is removed
# Return the whole string if brackets not found
def ScanForBracketedText(s: str, bra: str) -> Tuple[bool, str]:
    m=re.match(f"\w*<{bra}>(.*)</{bra}>\w*$", s)
    if m is None:
        return False, s
    return True, m.groups()[0]

#=====================================================================================
# Find text bracketed by <b>...</b>
# Return the contents of the first pair of brackets found and the remainder of the input string
def FindBracketedText(s: str, b: str) -> Tuple[str, str]:

    pattern="<"+b+">(.*?)</"+b+">"
    m=re.search(pattern, s,  re.DOTALL)
    if m is None:
        return "", s
    match=RemoveAllHTMLTags(m.groups()[0])
    s2=re.sub(pattern, "", s, count=1)
    return match, s2


#=====================================================================================
# Remove a matched pair of <brackets> <containing anything> from a string, returning the inside
def StripExternalTags(s: str)-> Optional[str]:
    m=re.match("^<.*>(.*)</.*>$", s)
    if m is None:
        return None
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
def RemoveAccents(input: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', input)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


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
# Change"&nbsp;" to space
def ChangeNBSPToSpace(s: Optional[str]) -> Union[None, str, List[str]]:
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
# Function to generate the proper kind of path.  (This may change depending on the target location of the output.)
def RelPathToURL(relPath: str) -> Optional[str]:
    if relPath is None:
        return None
    if relPath.startswith("http"):  # We don't want to mess with foreign URLs
        return None
    return "https://www.fanac.org/"+os.path.normpath(os.path.join("fanzines", relPath)).replace("\\", "/")


#=====================================================================================
# Function to find the index of a string in a list of strings
def FindIndexOfStringInList(lst: List[str], s: str) -> Optional[int]:
    try:
        return lst.index(s)
    except:
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
def ExtensionMatches(file: str, ext: Union[str, List[str]]) -> bool:
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
# Read a list of lines in from a file
# Strip leading and trailing whitespace and ignore lines which begin with a '#'
def ReadList(filename: str, isFatal: bool=False) -> Optional[List[str]]:
    if not os.path.exists(filename):
        if isFatal:
            Log("***Fatal error: Can't find "+filename, isError=True)
            raise FileNotFoundError
        print("ReadList can't open "+filename)
        return None
    with open(filename, "r") as f:
        lst=f.readlines()

    lst=[l.strip() for l in lst]  # Strip leading and trailing whitespace
    lst=[l for l in lst if len(l)>0 and l[0]!= "#"]   # Drop empty lines and lines starting with "#"

    lst=[l for l in lst if l.find(" #") == -1] + [l[:l.find(" #")].strip() for l in lst if l.find(" #") > 0]    # (all members not containing " #") +(the rest with the trailing # stripped)

    return lst


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


# =============================================================================
# Nibble away at a line by applying the pattern with two capture groups to the line
# We return a tuple:
#       The line with the matched portion removed
#       Capture group 1
#       Capture group 2
def Match2AndRemove(inputstr: str, pattern: str) -> Tuple[str, Optional[str], Optional[str]]:
    m=re.match(pattern, inputstr)         # Do we match the pattern?
    if m is not None and len(m.groups()) > 0:
        g0=m.groups()[0]                    # There may be either 1 or two groups, but we need to return two matches
        g1=None
        if len(m.groups()) > 1:
            g1=m.groups()[1]
        return re.sub(pattern, "", inputstr), g0, g1  # And delete the matched text
    return inputstr, None, None


# =============================================================================
# Display a message box (needed only for the built/packaged version)
# User sparingly, since the messagebox must be closed by hand and can be annoying.
# It does nothing in the debug version
def MessageBox(s: str, ignoredebugger: bool=False) -> None:
 if sys.gettrace() is None or ignoredebugger:      # This is an incantation which detects the presence of a debugger
    root = Tk()
    root.withdraw()
    messagebox.showinfo(title=None, message=s)


# =============================================================================
# Title names the app
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
def WikidotCononicizeName(name: str) -> str:
    if len(name) == 0:
        return name
    elif len(name) == 1:
        return name.upper()
    name=name[0].upper()+name[1:].lower()
    name=re.sub("[^a-zA-Z0-9]+", "-", name)
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

    return out[0].upper()+out[1:]


#-----------------------------------------------------------------
# Break a Mediawiki link into its components
# [[link#anchor|display text]] --> (link, anchor, display text)
# Make sure that link[0] is upper case
# The brackets are optional. (Inputs of [[link#anchor|display text]] and link#anchor|display text give the same result)
def WikiLinkSplit(s: str) -> Tuple[str, str, str]:
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
    return (link, anchor, text)


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
    m=re.match("[^&]+(#)[^;]+$", s)        # First look for aaa#bbb where a does not contain an & and by does not contain a ;.  This is definitely a reference to an anchor
    if m is not None and len(m.regs) > 1:
        s=s[:m.regs[1][0]]       # Clip the reference at the #, leaving just the page name
        return s.replace("  ", " ")
    # Now we can deal with special characters
    return unescape(s).replace("  ", " ")

    # Note that this does not handle the case where we have an anchor jump *and* special characters
    # m=re.search("[^&]#[^\d]+[^;]", s)       # Search for a # that isn't in something of the form &#nnn; (a unicode character escape)
    # if m is not None:
    #     s=s[:m.start()+1]       # Clip the reference at the #, leaving just the page name

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
def SplitOnSpan(chars: str, s: str) -> List[str]:
    pattern=re.compile("["+chars+"]")
    # replace the matched span of <chars> with a single char from the span string
    return [x for x in re.sub(pattern, chars[0], s).split(chars[0]) if len(x) > 0]

#------------------------------------------------------------------
# Split a really long string of output for printing as text.
def SplitOutput(f, s: str):
    strs=s.split(",")
    while len(strs) > 0:
        out=""
        while (len(strs) > 0 and (len(out)+len(strs[0])) < 80 or (len(out) == 0 and len(strs[0]) >= 80)):
            out=out+strs[0].strip()+", "
            del strs[0]
        f.write(f"    {out}\n")