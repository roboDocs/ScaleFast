#coding=utf-8
from __future__ import division
from math import atan2, tan, hypot, cos, degrees, radians

from fontParts.fontshell import RGlyph

import fontTools
import fontTools.misc.bezierTools as bezierTools
import fontTools.misc.arrayTools as arrayTools
import fontTools.misc.transform as transform
from fontTools.pens.boundsPen import BoundsPen

try:
    import mutatorScale
except:
    import os
    import sys
    libFolder = os.path.dirname(os.path.dirname(os.getcwd()))
    if not libFolder in sys.path:
        sys.path.append(libFolder)

from mutatorScale.pens.utilityPens import CollectSegmentsPen

def makeListFontName(font):
    """
    Return a font name in the form: 'Family name — style name'.
    The separator allows to easily split this full name later on with name.split(' — ').
    """
    familyName = font.info.familyName
    styleName = font.info.styleName
    if familyName is None:
        familyName = font.info.familyName = 'Unnamed'
    if styleName is None:
        styleName = font.info.styleName = 'Unnamed'
    return joinFontName(familyName, styleName)


def joinFontName(familyName, styleName):
    separator = '-'
    return '{familyName} {separator} {styleName}'.format(familyName=familyName, separator=separator, styleName=styleName)


def getRefStems(font, slantedSection=False):
    """
    Looks for stem values to serve as reference for a font in an interpolation scheme,
    only one typical value is returned for both horizontal and vertical stems.
    The method intersets the thick stem of a capital I and thin stem of a capital H.
    """
    stems = []
    angle = getSlantAngle(font, True)

    for i, glyphName in enumerate(['I','H']):

        if glyphName in font:

            baseGlyph = font[glyphName]

            # removing overlap
            glyph = freezeGlyph(baseGlyph)
            width = glyph.width

            glyph.skewBy((-angle, 0))

            xMin, yMin, xMax, yMax = getGlyphBox(glyph)
            xCenter = width / 2
            yCenter = (yMax - yMin) / 2

            # glyph I, cut thick stem
            if i == 0:
                intersections = intersect(glyph, yCenter, True)

            # glyph H, cut thin stem
            elif i == 1:
                intersections = intersect(glyph, xCenter, False)

            if len(intersections) > 1:
                (x1,y1), (x2,y2) = (intersections[0], intersections[-1])

                stemWidth = hypot(x2-x1, y2-y1)
                stems.append(round(stemWidth))
            else:
                stems.append(None)

        elif glyphName not in font:
            stems.append(None)

    if slantedSection == True and stems[0] is not None:
        stems[0] *= cos(radians(angle))

    return stems


def getSlantAngle(font, returnDegrees=False):
    """Returns the probable slant/italic angle of a font measuring the slant of a capital I."""

    if 'I' in font:
        testGlyph = font['I']
        xMin, yMin, xMax, yMax = getGlyphBox(testGlyph)
        hCenter = (yMax - yMin) / 2
        delta = 10
        intersections = []
        glyph = freezeGlyph(testGlyph)

        for i in range(2):
            horizontal = hCenter + (i * delta)
            intersections.append(intersect(glyph, horizontal, True))

        if len(intersections) > 1:
            if len(intersections[0]) > 1 and len(intersections[1]) > 1:
                (x1,y1), (x2,y2) = (intersections[0][0], intersections[1][0])
                angle = atan2(x2-x1, y2-y1)
                if returnDegrees == False:
                    return angle
                elif returnDegrees == True:
                    return round(degrees(angle), 2)
    return 0


def freezeGlyph(glyph):
    """Return a copy of a glyph, with components decomposed and all overlap removed."""

    toRFGlyph = RGlyph()
    toRFpen = toRFGlyph.getPen()
    # draw only the contours, decomposed components will be added later on
    for contour in glyph:
        contour.draw(toRFpen)

    if len(glyph.components):
        decomposedComponents = extractComposites(glyph)
        decomposedComponents.draw(toRFpen)

    singleContourGlyph = RGlyph()
    singleContourGlyph.width = glyph.width
    singleContourGlyph.name = glyph.name
    pointPen = singleContourGlyph.getPointPen()

    if len(toRFGlyph.contours) > 1:

        try:
            booleanGlyphs = []

            for c in toRFGlyph.contours:
                if len(c) > 1:
                    b = BooleanGlyph()
                    pen = b.getPen()
                    c.draw(pen)
                    booleanGlyphs.append(b)

            finalBooleanGlyph = reduce(lambda g1, g2: g1 | g2, booleanGlyphs)
            finalBooleanGlyph.drawPoints(pointPen)

        except:
            toRFGlyph.drawPoints(pointPen)
    else:
        toRFGlyph.drawPoints(pointPen)

    return singleContourGlyph


def extractComposites(glyph):
    """Return a new glyph with outline copies of each composite from the source glyph."""

    decomposedComposites = RGlyph()

    if len(glyph.components):
        font = glyph.layer

        for comp in reversed(glyph.components):

            # obtain source data
            baseGlyphName = comp.baseGlyph
            baseGlyph = font[baseGlyphName]
            t = transform.Transform(*comp.transformation)

            # create a temporary glyph on which to draw the decomposed composite
            single_decomposedComposite = RGlyph()
            decompPen = single_decomposedComposite.getPen()
            baseGlyph.draw(decompPen)
            single_decomposedComposite.transformBy(tuple(t))

            # add single composite to the returned glyph
            decomposedComposites.appendGlyph(single_decomposedComposite)

    return decomposedComposites


def intersect(glyph, where, isHorizontal):
    """
    Intersect a glyph with a horizontal or vertical line.
    Intersect each segment of a glyph using fontTools bezierTools.splitCubic and splitLine methods.
    """
    pen = CollectSegmentsPen(glyph.layer)
    glyph.draw(pen)
    nakedGlyph = pen.getSegments()
    glyphIntersections = []

    for i, contour in enumerate(nakedGlyph):

        for segment in contour:

            length = len(segment)

            if length == 2:
                pt1, pt2 = segment
                returnedSegments = splitLine(pt1, pt2, where, int(isHorizontal))
            elif length == 4:
                pt1, pt2, pt3, pt4 = segment
                returnedSegments = bezierTools.splitCubic(pt1, pt2, pt3, pt4, where, int(isHorizontal))

            if len(returnedSegments) > 1:
                intersectionPoints = findDuplicatePoints(returnedSegments)
                if len(intersectionPoints):
                    box = calcBounds(segment)
                    intersectionPoints = [point for point in intersectionPoints if arrayTools.pointInRect(point, box)]
                    glyphIntersections.extend(intersectionPoints)

    return glyphIntersections


def calcBounds(points):
    """
    Return rectangular bounds of a list of points.
    Similar to fontTools’ calcBounds only with rounding added,
    rounding is required for the test in intersect() to work.
    """
    xMin, xMax, yMin, yMax = None, None, None, None
    for (x, y) in points:
        for xRef in [xMin, xMax]:
            if xRef is None: xMin, xMax = x, x
        for yRef in [yMin, yMax]:
            if yRef is None: yMin, yMax = y, y
        if x > xMax: xMax = x
        if x < xMin: xMin = x
        if y > yMax: yMax = y
        if y < yMin: yMin = y
    box = [round(value, 4) for value in [xMin, yMin, xMax, yMax]]
    return tuple(box)


def findDuplicatePoints(segments):
    counter = {}
    for seg in segments:
        for (x, y) in seg:
            p = round(x, 4), round(y, 4)
            if p in counter:
                counter[p] += 1
            elif not p in counter:
                counter[p] = 1
    return [key for key in counter if counter[key] > 1]


def getGlyphBox(glyph):
    pen = BoundsPen(glyph.layer)
    glyph.draw(pen)
    return pen.bounds


# had to fetch that splitLine method from Robofont’s version of fontTools
# fontTools 2.4’s version was buggy.

def splitLine(pt1, pt2, where, isHorizontal):
    """Split the line between pt1 and pt2 at position 'where', which
    is an x coordinate if isHorizontal is False, a y coordinate if
    isHorizontal is True. Return a list of two line segments if the
    line was successfully split, or a list containing the original
    line.

        >>> printSegments(splitLine((0, 0), (100, 100), 50, True))
        ((0, 0), (50.0, 50.0))
        ((50.0, 50.0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 100, True))
        ((0, 0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 0, True))
        ((0, 0), (0.0, 0.0))
        ((0.0, 0.0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 0, False))
        ((0, 0), (0.0, 0.0))
        ((0.0, 0.0), (100, 100))
    """
    pt1x, pt1y = pt1
    pt2x, pt2y = pt2

    ax = (pt2x - pt1x)
    ay = (pt2y - pt1y)

    bx = pt1x
    by = pt1y

    a = (ax, ay)[isHorizontal]

    if a == 0:
        return [(pt1, pt2)]

    t = float(where - (bx, by)[isHorizontal]) / a
    if 0 <= t < 1:
        midPt = ax * t + bx, ay * t + by
        return [(pt1, midPt), (midPt, pt2)]
    else:
        return [(pt1, pt2)]




if __name__ == '__main__':

    import os
    import unittest
    from defcon import Font

    class FontUtilsTests(unittest.TestCase):

        def setUp(self):
            libFolder = os.path.dirname(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))
            singleFontPath = u'testFonts/isotropic-anisotropic/regular-mid-contrast.ufo'
            fontPath = os.path.join(libFolder, singleFontPath)
            self.font = Font(fontPath)

        def test_intersect_horizontal(self):
            glyph = self.font['I']
            yCenter = self.font.info.capHeight / 2
            intersections = intersect(glyph, yCenter, True)
            self.assertEqual(intersections, [(234.0, 375.0), (134.0, 375.0)])

        def test_intersect_vertical(self):
            glyph = self.font['H']
            xCenter = glyph.width / 2
            intersections = intersect(glyph, xCenter, False)
            self.assertEqual(intersections, [(426.5, 356.0), (426.5, 396.0)])

        def test_intersect_vertical_with_overlap_removed(self):
            glyph = freezeGlyph(self.font['H'])
            xCenter = glyph.width / 2
            intersections = intersect(glyph, xCenter, False)
            self.assertEqual(intersections, [(426.5, 356.0), (426.5, 396.0)])

        def test_getRefStems(self):
            stems = getRefStems(self.font)

    unittest.main()
