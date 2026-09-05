"""The geometry SlideShow and PhotosEditor both use to show a detected face.

A face is *recorded* as a box -- [x, y, w, h] in the pixels of the original
photo, as OpenCV's YuNet detector returns it -- but it is *shown* as a circle:
the round pictures in SlideShow's Identify Photo list, the green ring drawn
over the photo, and the ring PhotosEditor draws while reviewing are all the
same circle.  The two programs have to agree about it exactly, or the same face
would be cropped one way and ringed another, so there is one copy of it here.

The circle is centred on the box and its radius is 0.65 of the box's diagonal,
which takes in the whole head rather than the detector's tighter box.

Which faces are worth showing at all is here too, so that every program that
extracts faces discards the same strays: see DropTinyFaces.
"""
from PIL import Image, ImageDraw

FACE_CIRCLE_RATIO=0.65          # of the box's diagonal

# A detector will find faces far back in a crowd that nobody could put a name
# to.  They are dropped by comparing each against the third-largest face in the
# same photo -- the third rather than the largest, so that one head close to the
# camera cannot set the bar for everybody behind it.
SMALL_FACE_RATIO=0.20           # of the third-largest face, measured across


# How big a face is, for comparing one against another in the same photo: the
# box's diagonal, the same measure the display circle is built on.  This is a
# length, not an area, so a face at SMALL_FACE_RATIO is a fifth as wide -- a
# speck -- rather than a person merely standing further back.
def FaceSize(box) -> float:
    _, _, w, h=(float(v) for v in box)
    return (w*w+h*h)**0.5


# The size a face in this photo has to reach to be worth identifying, or 0.0
# when none of them should be dropped.
#
# Fewer than three faces gives 0.0: there is no third-largest to measure
# against, nothing to declutter, and dropping one of two would be worse than
# leaving a small one in.  The third-largest face itself always reaches it.
#
# Programs that extract faces use DropTinyFaces below; this is here for a
# program that has to say which of the faces it was *given* are the small ones
# -- PhotosEditor, reading back reports written before the extractor filtered.
def SmallFaceCutoff(boxes, ratio: float=SMALL_FACE_RATIO) -> float:
    sizes=sorted((FaceSize(b) for b in boxes), reverse=True)
    if len(sizes) < 3:
        return 0.0
    return sizes[2]*ratio


# The faces worth offering for identification, smallest strays removed
def DropTinyFaces(boxes, ratio: float=SMALL_FACE_RATIO) -> list:
    boxes=list(boxes)
    cutoff=SmallFaceCutoff(boxes, ratio)
    return [b for b in boxes if FaceSize(b) >= cutoff]


# The circle a face box is shown as: (centre x, centre y, radius), in whatever
# pixels the box was given in
def FaceCircle(box) -> tuple[float, float, float]:
    x, y, w, h=(float(v) for v in box)
    return x+w/2, y+h/2, FACE_CIRCLE_RATIO*(w*w+h*h)**0.5


# The same circle as (left, top, right, bottom)
def FaceCircleBounds(box) -> tuple[float, float, float, float]:
    cx, cy, r=FaceCircle(box)
    return cx-r, cy-r, cx+r, cy+r


# Where to draw the circle when the photo is shown scaled into a rectangle:
#   box           [x, y, w, h] in the original photo's pixels
#   originalSize  (width, height) of that photo
#   displayRect   (x0, y0, x1, y1) the photo occupies on the screen or canvas
# Returns (x0, y0, x1, y1) for the circle, or None when the box cannot belong to
# this photo at all -- so a record left over from some other picture, or from
# before the photo was cropped, draws nothing rather than a ring in the wrong
# place.
def FaceCircleOnDisplay(box, originalSize, displayRect):
    try:
        x, y, w, h=(float(v) for v in box)
        width, height=(float(v) for v in originalSize)
        left, top, right, bottom=(float(v) for v in displayRect)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0 or w <= 0 or h <= 0:
        return None
    if x < 0 or y < 0 or x+w > width or y+h > height:
        return None
    displayWidth, displayHeight=right-left, bottom-top
    if displayWidth <= 0 or displayHeight <= 0:
        return None
    cx, cy, r=FaceCircle(box)
    return (left+(cx-r)*displayWidth/width, top+(cy-r)*displayHeight/height,
            left+(cx+r)*displayWidth/width, top+(cy+r)*displayHeight/height)


# A round picture of the face, PIL image in and PIL image out (each program
# wraps it for its own toolkit).  The crop is *not* clamped to the photo: a face
# at an edge is padded with the background instead, so it keeps its proportions
# rather than being stretched into the square.
def RoundFaceThumbnail(image: Image.Image, box, background="black", size: int=72) -> Image.Image:
    left, top, right, bottom=(int(round(v)) for v in FaceCircleBounds(box))
    width, height=right-left, bottom-top
    if width < 1 or height < 1:
        return Image.new("RGB", (size, size), background)

    # The square the circle sits in, filled with the background and then given
    # whatever part of it the photo actually holds.  Cutting the square down to the
    # photo instead would squeeze the face sideways when it was resized, and PIL's
    # own padding is black whatever background was asked for.
    square=Image.new("RGB", (width, height), background)
    cropLeft, cropTop=max(left, 0), max(top, 0)
    cropRight, cropBottom=min(right, image.width), min(bottom, image.height)
    if cropRight > cropLeft and cropBottom > cropTop:
        square.paste(image.crop((cropLeft, cropTop, cropRight, cropBottom)).convert("RGB"),
                     (cropLeft-left, cropTop-top))
    square=square.resize((size, size), Image.LANCZOS)

    mask=Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size-1, size-1), fill=255)
    thumbnail=Image.new("RGB", (size, size), background)
    thumbnail.paste(square, (0, 0), mask)
    return thumbnail
