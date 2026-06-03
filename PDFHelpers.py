import os
import re
from enum import IntEnum

from pypdf import PdfReader, PdfWriter

from HelpersPackage import ExtensionMatches
from Log import Log, LogError

try:
    from spellchecker import SpellChecker as _SpellChecker
    _spell = _SpellChecker()
except ImportError:
    _spell = None


# =============================================================================
class OcrQuality(IntEnum):
    NOT_OCRED = 1
    LOW       = 2
    HIGH      = 3


# =============================================================================
# Assess the OCR quality of an already-opened PdfReader.
#
# Parameters (all adjustable):
#   min_word_length        — words must be strictly longer than this to count
#   min_good_words_per_page — a page needs at least this many properly-spelled
#                             long words to be considered OCR'd at all
#   high_quality_ratio     — fraction of alphabetic characters that must belong
#                             to recognized words (in the busiest pages) for HIGH
#   top_page_count         — how many of the largest-text pages to examine for
#                             the HIGH quality test
#
# Returns:
#   OcrQuality.NOT_OCRED  — no page has >= min_good_words_per_page good words
#   OcrQuality.HIGH       — top pages pass the character-ratio test
#   OcrQuality.LOW        — OCR present but ratio too low
def LowQualityScan(reader: PdfReader,
                   label: str = "",
                   min_word_length: int = 5,
                   min_good_words_per_page: int = 20,
                   high_quality_ratio: float = 0.75,
                   top_page_count: int = 2) -> tuple[OcrQuality, dict]:
    """Return (quality, stats) where stats has keys: alpha, in_words, ratio, long_words."""

    prefix = f"LowQualityScan({label})" if label else "LowQualityScan"
    if _spell is None:
        Log(f"{prefix}: WARNING — pyspellchecker not available; ratio test will be skipped, quality capped at LOW")
    page_data = []   # (total_text_len, total_alpha_chars, good_long_word_count, recognized_chars)

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        words = re.findall(r'[a-zA-Z]+', text)

        if _spell is not None and words:
            lower_words = [w.lower() for w in words]
            unknown     = _spell.unknown(lower_words)
            good_long   = sum(1   for w in words if len(w) > min_word_length and w.lower() not in unknown)
            recog_chars = sum(len(w) for w in words if w.lower() not in unknown)
        else:
            # Without a spell-checker we can count long words but cannot assess recognition quality.
            good_long   = sum(1   for w in words if len(w) > min_word_length)
            recog_chars = 0   # unknown — do not inflate ratio

        total_alpha = sum(len(w) for w in words)
        page_data.append((len(text), total_alpha, good_long, recog_chars))
        if _spell is None:
            Log(f"{prefix} p{i+1}: alpha count={total_alpha}  # in words=n/a  ratio=n/a  # words>5 char={good_long}")
        else:
            ratio_str = f"{recog_chars/total_alpha:.2f}" if total_alpha > 0 else "n/a"
            Log(f"{prefix} p{i+1}: alpha count={total_alpha}  # in words={recog_chars}  ratio={ratio_str}  # words>5 char={good_long}")
        if total_alpha > 0:
            sample = ' '.join(text.split())[:120]
            Log(f"{prefix} p{i+1}: text sample: {sample!r}")

    # Aggregate stats across all pages (used for Processed.txt)
    total_alpha_all = sum(p[1] for p in page_data)
    total_recog_all = sum(p[3] for p in page_data)
    max_long_words  = max((p[2] for p in page_data), default=0)
    agg_ratio       = (total_recog_all / total_alpha_all
                       if _spell is not None and total_alpha_all > 0 else None)
    stats = {
        'alpha':      total_alpha_all,
        'in_words':   total_recog_all,
        'ratio':      agg_ratio,
        'long_words': max_long_words,
    }

    if not page_data:
        Log(f"{prefix}: no pages — NOT_OCRED")
        return OcrQuality.NOT_OCRED, stats

    # NOT_OCRED: too few alpha characters across all pages — likely a pure image scan.
    # Using total alpha chars rather than per-page recognized-long-word counts so that
    # low-quality OCR (many unrecognized words) is still classified as LOW, not NOT_OCRED.
    _not_ocred_threshold = min_good_words_per_page * (min_word_length + 1)
    if total_alpha_all < _not_ocred_threshold:
        Log(f"{prefix}: total_alpha={total_alpha_all} < {_not_ocred_threshold} — NOT_OCRED")
        return OcrQuality.NOT_OCRED, stats

    # HIGH: in the top N pages by raw text volume, enough chars are recognized.
    # Requires spell-checker; without it we can only confirm OCR is present, not that it is high quality.
    if _spell is None:
        Log(f"{prefix}: spell checker unavailable — LOW")
        return OcrQuality.LOW, stats

    top         = sorted(page_data, key=lambda p: p[0], reverse=True)[:top_page_count]
    total_alpha = sum(p[1] for p in top)
    total_recog = sum(p[3] for p in top)
    ratio       = total_recog / total_alpha if total_alpha > 0 else 0.0
    Log(f"{prefix}: top-{top_page_count} alpha count={total_alpha}  # in words={total_recog}  ratio={ratio:.2f}  threshold={high_quality_ratio}")

    if total_alpha > 0 and ratio >= high_quality_ratio:
        Log(f"{prefix}: HIGH")
        return OcrQuality.HIGH, stats

    Log(f"{prefix}: LOW")
    return OcrQuality.LOW, stats


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
    except Exception:
        LogError(f"AddMissingMetadata: writer.add_metadata() failed for {filename}: ignored")

    # Write out the new pdf using the existing pdf's name with " added" appended to it.
    path, ext=os.path.splitext(filename)
    newfile=path+" added"+ext
    try:
        with open(newfile, 'wb') as file_out:
            writer.write(file_out)
    except Exception as e:
        LogError(f"AddMissingMetadata: failed to write '{newfile}': {e}")
        return False

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
    try:
        with open(newfile, 'wb') as file_out:
            writer.write(file_out)
    except Exception as e:
        LogError(f"AddStdMetadata: failed to write '{newfile}': {e}")
        return False

    os.remove(filename)
    os.rename(newfile, filename)
    return True


# =============================================================================
# Get the file's page count if it's a pdf
# Bonus: Return 1 if it's a .jpd, png, or gif.
def GetPdfPageCount(pathname: str) -> int|None:
    if ExtensionMatches(pathname, [".jpg", ".jpeg", ".png", ".gif"]):
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
