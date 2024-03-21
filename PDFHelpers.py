import os


from pypdf import PdfReader, PdfWriter

from HelpersPackage import ExtensionMatches
from Log import Log


# =============================================================================
def AddMissingMetadata(file: str, newmetadata: dict[str, str]):
    if file.lower().endswith(".pdf"):

        file_in=open(file, 'rb')
        reader=PdfReader(file_in)

        writer=PdfWriter()

        writer.append_pages_from_reader(reader)
        writer.add_metadata(newmetadata)
        try:
            writer.add_metadata(reader.metadata)
        except:
            Log(f"AddMissingMetadata().writer.add_metadata(reader.metadata) with file {file} threw an exception: Ignored")
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
