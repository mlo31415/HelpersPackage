from typing import Optional
import os

from PyPDF2 import PdfFileReader, PdfFileWriter

from HelpersPackage import ExtensionMatches
from Log import Log


# =============================================================================
def AddMissingMetadata(file: str, newmetadata: dict[str, str]):
    if file.lower().endswith(".pdf"):

        file_in=open(file, 'rb')
        reader=PdfFileReader(file_in)
        info=reader.getDocumentInfo()
        if "/Title" in info.keys() and info["/Title"]:
            return  # There's *something* there already

        writer=PdfFileWriter()

        writer.appendPagesFromReader(reader)
        writer.addMetadata(reader.getDocumentInfo())    # For unclear reasons, we have to add the existing metadata back as well as adding the new
        writer.addMetadata(newmetadata)
        # os.remove(file)
        path, ext=os.path.splitext(file)
        newfile=path+" added"+ext
        file_out=open(newfile, 'wb')
        writer.write(file_out)
        file_in.close()
        file_out.close()
        os.remove(file)
        os.rename(newfile, file)


# =============================================================================
# Get the file's page count if it's a pdf
# Bonus: Return 1 if it's a .jpd, png, or gif.
def GetPdfPageCount(pathname: str) -> Optional[int]:
    if ExtensionMatches(pathname, ".jog" or ExtensionMatches(pathname, ".png") or ExtensionMatches(pathname, ".gif")):
        return 1

    if not ExtensionMatches(pathname, ".pdf"):
        return None

    # So it claims to be a PDF.  Try to get its page count.
    try:
        with open(pathname, 'rb') as fl:
            reader=PdfFileReader(fl)
            return reader.getNumPages()
    except Exception as e:
        Log(f"GetPdfPageCount: Exception {e} raised while getting page count for '{pathname}'")
        Log(f"GetPdfPageCount: {os.getcwd()=}")
    return None
