import os
import re
import urllib.parse
from typing import Union, Tuple, Optional, List

import roman
from html import escape

from Log import Log

#-----------------------------
# Helper function
# Try to make the input numeric
# Note that if it fails, it returns what came in.
def ToNumeric(val: Union[None, int, float, str]) ->Union[None, int, float]:
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
        try:
            return float(val)
        except:
            pass

    # If nothing works, return None
    return None


#==================================================================================
# Return a properly formatted link
def FormatLink(url: str, text: str) -> str:
    # TODO: Do we need to deal with turning blanks into %20 whatsits?
    # If the url points to a pdf, add '#view=Fit' to the end to force the PDF to scale to the page
    if url.lower().endswith(".pdf"):
        url+="#view=Fit"
    return '<a href='+url+'>'+UnicodeToHtml(text)+'</a>'


#-------------------------------------------------------------
def CannonicizeColumnHeaders(header: str) -> str:
    # 2nd item is the cannonical form
    translationTable={
                        "published" : "date",
                        "editors" : "editor",
                        "zine" : "issue",
                        "fanzine" : "issue",
                        "mo." : "month",
                        "mon" : "month",
                        "quartermonth" : "month",
                        "quarter" : "month",
                        "season" : "month",
                        "notes" : "notes",
                        "no." : "number",
                        "no,": "number",
                        "num" : "number",
                        "#" : "number",
                        "page" : "pages",
                        "pages" : "pages",
                        "pp," : "pages",
                        "pub" : "publisher",
                        "vol" : "volume",
                        "volume" : "volume",
                        "volumenumber" : "volnum",
                        "vol#" : "volnum",
                        "vol.#" : "volnum",
                        "wholenum" : "whole",
                        "year" : "year",
                      }
    try:
        return translationTable[header.replace(" ", "").replace("/", "").lower()]
    except:
        return header.lower()


#-----------------------------------------
# Find text bracketed by <b>...</b>
# Return the contents of the first pair of brackets found and the remainder of the input string
def FindBracketedText(s: str, b: str) -> Tuple[str, str]:
    strlower=s.lower()
    l1=strlower.find("<"+b.lower())
    if l1 == -1:
        return "", ""
    l1=strlower.find(">", l1)
    if l1 == -1:
        Log("***Error: no terminating '>' found in "+strlower+"'", True)
        return "", ""
    l2=strlower.find("</"+b.lower()+">", l1+1)
    if l2 == -1:
        return "", ""
    return s[l1+1:l2], s[l2+3+len(b):]

#=====================================================================================
# Remove certain strings which amount to whitespace
def RemoveHTMLDebris(s: str) -> str:
    return s.replace("<br>", "").replace("<BR>", "")


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
    return "http://www.fanac.org/"+os.path.normpath(os.path.join("fanzines", relPath)).replace("\\", "/")


#=====================================================================================
# Function to find the index of a string in a list of strings
def FindIndexOfStringInList(lst: List[str], s: str) -> Optional[int]:
    try:
        return lst.index(s)
    except:
        return None


#==================================================================================
def CreateFanacOrgAbsolutePath(fanacDir: str, s: str) -> str:
    return "http://www.fanac.org/fanzines/"+fanacDir+"/"+s


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


#=============================================================================
def CaseInsensitiveCompare(s1: str, s2: str) -> bool:
    if s1 == s2:
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
# Check to see if an argument (int, float or string) is a number
def IsInt(arg) -> bool:
    if type(arg) is int:
        return True

    # It's not an integer type.  See if it can be converted into an integer.  E.g., it's a string representation of a number
    try:
        int(arg)  # We throw away the result -- all we're interested in is if the conversation can be done without throwing an error
        return True
    except:
        return False


# =============================================================================
# Check to see if an argument (int, float or string) is a number
def IsNumeric(arg) -> bool:
    if type(arg) in [float, int]:
        return True

    # It's not a numeric type.  See if it can be converted into a float.  E.g., it's a string representation of a number
    try:
        float(arg)    # We throw away the result -- all we're interested in is if the conversation can be done without throwing an error
        return True
    except:
        return False



# =============================================================================
# Read a list of lines in from a file
# Strip leading and trailing whitespace and ignore lines which begin with a '#'
def ReadList(filename: str, isFatal: bool=False) -> Optional[List[str]]:
    if not os.path.exists(filename):
        if isFatal:
            Log("Fatal error: Can't find "+filename, isError=True)
            raise FileNotFoundError
        print("ReadList can't open "+filename)
        return None
    f=open(filename, "r")
    lst=f.readlines()
    f.close()

    lst=[l.strip() for l in lst]  # Strip leading and trailing whitespace
    lst=[l for l in lst if len(l)>0 and l[0]!= "#"]   # Drop empty lines and lines starting with "#"

    lst=[l for l in lst if l.find(" #") == -1] + [l[:l.find(" #")].strip() for l in lst if l.find(" #") > 0]    # (all members not containing " #") +(the rest with the trailing # stripped)

    return lst


# =============================================================================
# Try to interpret a string as an integer
#   nnn
#   nnn-nnn
#   nnn.nnn
#   nnnaaa
def InterpretNumber(inputstring: Optional[str]) -> Optional[int]:
    value=None
    if inputstring is not None:
        inputstring=inputstring.strip()
        if IsInt(inputstring):  # Simple integer
            value=int(inputstring)
        if value is None:
            # nn-nn (Hyphenated integers which usually means a range of numbers)
            p=re.compile("^([0-9]+)-([0-9]+)$")  # nnn + dash + nnn
            m=p.match(inputstring)
            if m is not None and len(m.groups()) == 2:
                value=int(m.groups()[0])        # We just sorta ignore n2...
        if value is None:
            # nn.nn (Decimal number)
            p=re.compile("^([0-9]+.[0-9]+)$")   # nnn.nnn
            m=p.match(inputstring)
            if m is not None and len(m.groups()) == 1:
                value=float(m.groups()[0])      # Note that this returns a float
        if value is None:
            # nnaa (integer followed by letter)
            p=re.compile("^([0-9]+)\s?([a-zA-Z]+)$")  # nnn + optional space + nnn
            m=p.match(inputstring)
            if m is not None and len(m.groups()) == 2:
                value=int(m.groups()[0])
        if value is None:
            p=re.compile("^([IVXLC]+)$")        # roman numeral characters
            m=p.match(inputstring)
            if m is not None and len(m.groups()) == 1:
                value=roman.fromRoman(m.groups()[0])
        if value is None:
            if inputstring is not None and len(inputstring) > 0:
                Log("*** Uninterpretable number: '"+str(inputstring)+"'", True)
    return value