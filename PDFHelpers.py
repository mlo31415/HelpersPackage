import os


from pypdf import PdfReader, PdfWriter

from HelpersPackage import ExtensionMatches
from Log import Log, LogError


# =============================================================================
def AddMissingMetadata(filename: str, newmetadata: dict[str, str], keywords: str="") -> bool:
    if not filename.lower().endswith(".pdf"):
        return False

    # Try to create a writer which is filled with a clone of the input pdf
    try:
        writer=PdfWriter(clone_from=filename)
    except FileNotFoundError:
        LogError(f"SetPDFMetadata: Unable to open file {filename}")
        return False

    # # Open the existing pdf file
    # file_in=open(filename, 'rb')
    # reader=PdfReader(file_in)

    # If keywords are supplied, add them to the new metadata
    if keywords != "":
        newmetadata["/Keywords"]=keywords

    # Add the new metadata to the cloned pdf.
    try:
        writer.add_metadata(newmetadata)
    except:
        LogError(f"SetPDFMetadata().writer.add_metadata(metadata) with file {filename} threw an exception: Ignored")

    # Write out the new pdf using the existing pdf's name with " added" appended to it.
    path, ext=os.path.splitext(filename)
    newfile=path+" added"+ext
    file_out=open(newfile, 'wb')

    writer.write(file_out)

    # Close both the old and new pdfs, delete the old and rename the new to the old's name
    #file_in.close()
    file_out.close()
    os.remove(filename)
    os.rename(newfile, filename)
    return True


# =============================================================================
# Add standard bibliographic metadata fields to a PDF.
# Only fields supplied with a non-empty value are written; omitted or empty fields are left unchanged.
def AddStdMetadata(filename: str, title: str="", author: str="", subject: str="", keywords: str="") -> bool:
    if not filename.lower().endswith(".pdf"):
        return False

    metadata: dict[str, str] = {}
    if title:
        metadata["/Title"] = title
    if author:
        metadata["/Author"] = author
    if subject:
        metadata["/Subject"] = subject
    if keywords:
        metadata["/Keywords"] = keywords

    if not metadata:
        return True  # Nothing to do

    try:
        writer = PdfWriter(clone_from=filename)
    except FileNotFoundError:
        LogError(f"AddStdMetadata: Unable to open file {filename}")
        return False

    try:
        writer.add_metadata(metadata)
    except Exception:
        LogError(f"AddStdMetadata: writer.add_metadata() failed for {filename}: ignored")

    path, ext = os.path.splitext(filename)
    newfile = path+" added"+ext
    file_out = open(newfile, 'wb')
    writer.write(file_out)
    file_out.close()
    os.remove(filename)
    os.rename(newfile, filename)
    return True


# =============================================================================
# Get the file's page count if it's a pdf
# Bonus: Return 1 if it's a .jpd, png, or gif.
def GetPdfPageCount(pathname: str) -> int|None:
    if ExtensionMatches(pathname, ".jog" or ExtensionMatches(pathname, ".png") or ExtensionMatches(pathname, ".gif")):
        return 1

    if not ExtensionMatches(pathname, ".pdf"):
        return None

    # So it claims to be a PDF.  Try to get its page count.
    try:
        with open(pathname, 'rb') as fl:
            reader=PdfReader(fl)
            return len(reader.pages)
    except Exception as e:
        Log(f"GetPdfPageCount: Exception {e} raised while getting page count for '{pathname}'")
        Log(f"GetPdfPageCount: {os.getcwd()=}")
    return None
