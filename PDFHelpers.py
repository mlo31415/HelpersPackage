import os
import re
import time
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
        LogError(f"AddMissingMetadata: Unable to open file {filename}")
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

    # Open with a short retry: a just-written temp file can be transiently locked on Windows
    # (e.g. antivirus scanning %TEMP%), which surfaces as PermissionError on open.
    writer = None
    for attempt in range(6):
        try:
            writer = PdfWriter(clone_from=filename)
            break
        except FileNotFoundError:
            LogError(f"AddStdMetadata: Unable to open file {filename}")
            return False
        except PermissionError:
            time.sleep(0.25)
    if writer is None:
        LogError(f"AddStdMetadata: '{filename}' stayed locked (PermissionError) after retries")
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

    # Replace the original with the updated copy. The remove can hit the same transient lock, so retry.
    for attempt in range(6):
        try:
            os.remove(filename)
            break
        except FileNotFoundError:
            break
        except PermissionError:
            if attempt == 5:
                LogError(f"AddStdMetadata: '{filename}' stayed locked (PermissionError); could not replace it")
                try:
                    os.remove(newfile)
                except Exception:
                    pass
                return False
            time.sleep(0.25)
    os.rename(newfile, filename)

    # Remove any stale XMP metadata (e.g. a scanner-written dc:title) so the DocInfo values we just
    # set are what viewers actually display -- many viewers prefer the XMP packet over the /Info dict.
    try:
        import fitz
        doc=fitz.open(filename)
        doc.del_xml_metadata()
        doc.saveIncr()
        doc.close()
    except Exception as e:
        LogError(f"AddStdMetadata: could not remove XMP metadata from '{filename}': {e}")

    return True


# =============================================================================
# Get the file's page count if it's a pdf
# Bonus: Return 1 if it's a .jpj, jpeg, png or gif.
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


# =============================================================================
# PDF page-header support (requires PyMuPDF / fitz)
#
# AddPdfPageHeader(pdf_path, format_string, items)
#
#   Adds (or replaces) a centered, single-line header at the top of the first
#   page of a PDF, expanding the page height on first use.
#
#   format_string  -- template with {} placeholders, e.g.
#                     "{} #1, May 1952, by {} and {}  ——  from {}"
#   items          -- list of strings consumed left-to-right into the {}s.
#                     If an item looks like a URL (starts with http/https/ftp)
#                     it silently consumes the next item too as the display
#                     text, and that text is rendered in blue as a hyperlink.
#                     Non-URL items are rendered as plain black text.
#
#   The page is expanded by _EXTRA points on the first call.  Subsequent calls
#   detect the existing header (by the presence of a URI link in the top band),
#   clear it, and write the new one without re-expanding the page.

# ── layout constants (PDF points; PyMuPDF coords: top-left origin, y-down) ──
# Prefer Calibri (full Unicode, correct advance widths) over the base-14 Helvetica,
# which lacks em-dashes and other non-ASCII characters and causes mis-centering.
_FONT_FILE = r"C:\Windows\Fonts\calibri.ttf"
_FONT_FILE = _FONT_FILE if os.path.exists(_FONT_FILE) else None   # graceful fallback
_FONT_FALLBACK = "helv"   # used only when Calibri is not found
_FONT_NAME = "cali"       # internal id under which Calibri is embedded
# kwargs passed to insert_textbox so it uses the same font the wrap/layout code measures with
_FONT_KW = {"fontname": _FONT_NAME, "fontfile": _FONT_FILE} if _FONT_FILE else {"fontname": _FONT_FALLBACK}

_FONT_SIZE = 11            # header text point size
_BAND_Y0   = 8              # top of label band
_LINE_H    = 16             # height of label band
_PAD       = 6              # extra textbox length so a tight segment is never clipped
_SIDE      = 6              # left/right margin kept clear when wrapping the header
_GAP       = 4              # whitespace below label before page content
_EXTRA     = _BAND_Y0 + _LINE_H + _GAP   # points added to page height = 28

_COLOR_TEXT = (0, 0, 0)     # black
_COLOR_LINK = (0, 0, 0.8)   # blue

_EXTENT_KEY = "FanacHdrPts" # page-dict key recording how many points a previously-added header added


def _make_font(fitz):
    """Return a fitz.Font using Calibri if available, otherwise Helvetica."""
    if _FONT_FILE:
        return fitz.Font(fontfile=_FONT_FILE)
    return fitz.Font(_FONT_FALLBACK)


# ── parsing ──────────────────────────────────────────────────────────────────

def _is_url(s):
    return isinstance(s, str) and s.startswith(("http://", "https://", "ftp://"))


def _parse(format_string, items):
    """
    Return a list of (display_text, url_or_None) segments built by
    substituting items into the {} placeholders of format_string.
    """
    parts    = format_string.split("{}")
    n_slots  = len(parts) - 1
    it       = iter(items)
    segments = []

    for i, literal in enumerate(parts):
        if literal:
            segments.append((literal, None))

        if i == n_slots:          # no {} follows the last literal
            break

        try:
            item = next(it)
        except StopIteration:
            raise ValueError(
                f"format_string has {n_slots} placeholder(s) but items ran out at slot {i + 1}"
            )

        if _is_url(item):
            try:
                display = next(it)
            except StopIteration:
                raise ValueError(f"URL {item!r} at slot {i + 1} has no following display text")
            segments.append((display, item))
        else:
            segments.append((item, None))

    return segments


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _band(page, fitz, nlines=1):
    # Display-coords band covering nlines header lines; spans the full width even when x0 != 0.
    return fitz.Rect(page.rect.x0, _BAND_Y0, page.rect.x1, _BAND_Y0 + nlines * _LINE_H)


def _tokenize(segments):
    # Flatten segments into (text, url) tokens, each a maximal run of spaces or non-spaces.
    # Preserving exact spacing keeps a non-wrapped header identical to before.
    tokens = []
    for text, url in segments:
        for m in re.finditer(r"\s+|\S+", text):
            tokens.append((m.group(), url))
    return tokens


def _wrap(segments, font, max_width):
    """Greedily wrap the header into lines that fit within max_width (display points).
    Returns a list of lines, each a list of (text, url) tokens with end whitespace trimmed.
    A single token wider than max_width is left on its own line (it may overflow)."""
    def w(tok):
        return font.text_length(tok[0], fontsize=_FONT_SIZE)
    lines, cur, cur_w = [], [], 0.0
    for tok in _tokenize(segments):
        space = tok[0].isspace()
        if cur and not space and cur_w + w(tok) > max_width:
            while cur and cur[-1][0].isspace():      # trim trailing space before wrapping
                cur_w -= w(cur.pop())
            lines.append(cur)
            cur, cur_w = [], 0.0
        if not cur and space:
            continue                                 # drop leading space on a new line
        cur.append(tok)
        cur_w += w(tok)
    while cur and cur[-1][0].isspace():
        cur_w -= w(cur.pop())
    if cur:
        lines.append(cur)
    return lines or [[]]


def _already_labeled(page, fitz):
    band = _band(page, fitz)
    return any(
        fitz.Rect(lnk["from"]).intersects(band)
        for lnk in page.get_links()
        if lnk.get("kind") == fitz.LINK_URI
    )


def _grow(box, rot, amount, fitz):
    """Return box grown by `amount` points on the edge (in PyMuPDF MediaBox coords) that maps to the
    VISUAL top for the given page rotation (0/90/180/270, clockwise). Edges verified empirically --
    note that both 90 and 270 grow the x1 edge (the displayed top of a side-rotated page)."""
    x0, y0, x1, y1 = box.x0, box.y0, box.x1, box.y1
    if   rot == 0:   y1 += amount
    elif rot == 90:  x1 += amount
    elif rot == 180: y0 -= amount
    elif rot == 270: x1 += amount
    return fitz.Rect(x0, y0, x1, y1)


def _expand_top(page, fitz, nlines=1):
    """Expand the page at the VISUAL top by enough for `nlines` header lines (MediaBox + CropBox),
    accounting for page rotation so the band always lands above the displayed top."""
    amount = _EXTRA + (nlines - 1) * _LINE_H
    rot = page.rotation
    mb  = fitz.Rect(page.mediabox)
    cb  = fitz.Rect(page.cropbox)
    page.set_mediabox(_grow(mb, rot, amount, fitz))
    # Grow the cropbox on the same edge so the new band is visible, then clamp it to the
    # new mediabox to avoid a 'CropBox not in MediaBox' error. (Comparing cb==mb exactly is
    # unreliable: scans often have sub-point differences between the two boxes.)
    nc  = _grow(cb, rot, amount, fitz)
    nmb = fitz.Rect(page.mediabox)
    nc  = fitz.Rect(max(nc.x0, nmb.x0), max(nc.y0, nmb.y0),
                    min(nc.x1, nmb.x1), min(nc.y1, nmb.y1))
    try:
        page.set_cropbox(nc)
    except Exception:
        pass   # set_mediabox already auto-adjusted the cropbox to cover the new extent


def _read_extent(doc, page):
    """Return the point-height a previously-added header added to this page, or None."""
    try:
        typ, val = doc.xref_get_key(page.xref, _EXTENT_KEY)
        if typ in ("int", "real", "float"):
            return float(val)
    except Exception:
        pass
    return None


def _write_extent(doc, page, amount):
    """Record on the page how many points the header just added (so a later update can undo it)."""
    try:
        doc.xref_set_key(page.xref, _EXTENT_KEY, str(int(round(amount))))
    except Exception:
        pass


def _remove_header(page, amount, fitz):
    """Undo a previously-added header: erase its band (graphics + links) and shrink the page back
    to its pre-header size by `amount` points on the visual-top edge. After this the page is in the
    same state as if the header had never been added, so a fresh header can be applied de novo."""
    rot = page.rotation
    # The header occupies the top `amount` points (display coords); paint it out and drop its links.
    band = fitz.Rect(page.rect.x0, 0, page.rect.x1, amount)
    un   = band * page.derotation_matrix
    un.normalize()
    page.draw_rect(un, color=(1, 1, 1), fill=(1, 1, 1))
    for a in [a for a in page.annots() if a.rect.intersects(band)]:
        page.delete_annot(a)
    for lnk in [lnk for lnk in page.get_links() if fitz.Rect(lnk["from"]).intersects(band)]:
        page.delete_link(lnk)
    # Shrink MediaBox/CropBox back by `amount` on the same (visual-top) edge. Capture the cropbox
    # before set_mediabox, which itself auto-shrinks the cropbox (reading it after would double up).
    mb  = fitz.Rect(page.mediabox)
    cb  = fitz.Rect(page.cropbox)
    page.set_mediabox(_grow(mb, rot, -amount, fitz))
    nc  = _grow(cb, rot, -amount, fitz)
    nmb = fitz.Rect(page.mediabox)
    nc  = fitz.Rect(max(nc.x0, nmb.x0), max(nc.y0, nmb.y0),
                    min(nc.x1, nmb.x1), min(nc.y1, nmb.y1))
    try:
        page.set_cropbox(nc)
    except Exception:
        pass   # set_mediabox already auto-adjusted the cropbox to cover the new extent


def _add_label(page, lines, fitz):
    font = _make_font(fitz)
    dm   = page.derotation_matrix
    rot  = page.rotation
    for i, line in enumerate(lines):
        y0      = _BAND_Y0 + i * _LINE_H
        total_w = sum(font.text_length(t, fontsize=_FONT_SIZE) for t, _ in line)
        x       = page.rect.x0 + (page.rect.width - total_w) / 2.0
        links   = []   # consecutive same-url runs on this line: [url, x0, x1]
        for text, url in line:
            w = font.text_length(text, fontsize=_FONT_SIZE)
            # Lay each token out in display coords, then map to the unrotated page space that
            # PyMuPDF's write methods use; rotate=rot keeps text upright on rotated pages.
            box = fitz.Rect(x, y0, x + w + _PAD, y0 + _LINE_H) * dm
            box.normalize()
            page.insert_textbox(box, text, fontsize=_FONT_SIZE,
                                color=_COLOR_LINK if url else _COLOR_TEXT, rotate=rot, **_FONT_KW)
            if url:
                if links and links[-1][0] == url and abs(links[-1][2] - x) < 0.5:
                    links[-1][2] = x + w               # extend the current run
                else:
                    links.append([url, x, x + w])
            x += w
        for url, lx0, lx1 in links:
            link = fitz.Rect(lx0, y0, lx1, y0 + _LINE_H) * dm
            link.normalize()
            page.insert_link({"kind": fitz.LINK_URI, "from": link, "uri": url})


# ── public API ────────────────────────────────────────────────────────────────

def AddPdfPageHeader(pdf_path: str, format_string: str, items: list) -> None:
    """
    Add or replace a header on the first page of pdf_path.
    See module docstring for format_string / items conventions.
    Requires PyMuPDF: install with  pip install pymupdf
    """
    try:
        import fitz
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for AddPdfPageHeader but is not installed.\n"
            "Install it with:  pip install pymupdf"
        )

    segments = _parse(format_string, items)

    # Retry the open: a just-written temp file can be transiently locked on Windows (antivirus
    # scanning %TEMP%), surfacing as PermissionError.
    doc = None
    for attempt in range(6):
        try:
            doc = fitz.open(pdf_path)
            break
        except Exception:
            if attempt == 5:
                raise
            time.sleep(0.25)
    page = doc[0]

    # Updating a header must yield the same result as removing the old header entirely and then
    # adding the new one. So first restore the page to its pre-header state, then add de novo.
    old_amount = _read_extent(doc, page)
    if old_amount is None and _already_labeled(page, fitz):
        old_amount = _EXTRA          # legacy header (pre-multi-line) was always a single line
    if old_amount:
        _remove_header(page, old_amount, fitz)

    # Wrap the header to as many lines as needed to fit the page width (page rotation does not
    # change the displayed width, so this is valid before expanding the page).
    lines  = _wrap(segments, _make_font(fitz), page.rect.width - 2 * _SIDE)
    amount = _EXTRA + (len(lines) - 1) * _LINE_H
    _expand_top(page, fitz, len(lines))
    _add_label(page, lines, fitz)
    _write_extent(doc, page, amount)

    # Subset the just-embedded header font and rewrite the file compactly. Embedding the full Calibri
    # TTF (~1.6 MB) otherwise bloats even tiny PDFs. A full, garbage-collected save is required to drop
    # the original full-font stream (an incremental save can only append). If the compact path isn't
    # available, fall back to an incremental save -- correct, just larger.
    try:
        doc.subset_fonts()
    except Exception as e:
        LogError(f"AddPdfPageHeader: subset_fonts() failed (continuing without subsetting): {e}")
    tmp_out = pdf_path + ".min.pdf"
    try:
        doc.save(tmp_out, garbage=4, deflate=True)
    except Exception as e:
        LogError(f"AddPdfPageHeader: compact save failed ({e}); using incremental save instead")
        try:
            doc.saveIncr()
        finally:
            doc.close()
        try:
            if os.path.exists(tmp_out):
                os.remove(tmp_out)
        except Exception:
            pass
        return
    doc.close()
    # Replace the original with the compact version, retrying past transient Windows file locks.
    for attempt in range(6):
        try:
            os.replace(tmp_out, pdf_path)
            return
        except PermissionError:
            if attempt == 5:
                LogError(f"AddPdfPageHeader: could not replace '{pdf_path}' with the compact version (locked)")
                try:
                    os.remove(tmp_out)
                except Exception:
                    pass
                return
            time.sleep(0.25)
