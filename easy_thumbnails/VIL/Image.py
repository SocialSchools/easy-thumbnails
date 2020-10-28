import builtins
import io
from pathlib import Path

from reportlab.graphics import renderSVG
from reportlab.lib.colors import Color

from svglib.svglib import svg2rlg


class Image:
    """
    Attempting to be compatible with PIL's Image, but suitable for reportlab's SVGCanvas.
    """
    def __init__(self, size=(300, 300)):
        assert isinstance(size, (list, tuple)) and len(size) == 2 \
            and isinstance(size[0], (int, float)) and isinstance(size[1], (int, float)), \
            "Expected `size` as tuple with two elements"
        self.canvas = renderSVG.SVGCanvas(size=size, useClip=True)
        self.size = tuple(size)
        self.mode = None

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

    def getbbox(self):
        """
        Calculates the bounding box of the non-zero regions in the image.

        :returns: The bounding box is returned as a 4-tuple defining the
           left, upper, right, and lower pixel coordinate.
        """
        return tuple(float(b) for b in self.canvas.svg.getAttribute('viewBox').split())

    def resize(self, size, **kwargs):
        """
        :param size: The requested size in pixels, as a 2-tuple: (width, height).
        :returns: An :py:class:`easy_thumbnails.VIL.Image.Image` object.
        """
        copy = Image(size=size)
        copy.canvas.svg = self.canvas.svg.cloneNode(True)
        return copy

    def convert(self, *args):
        """
        Does nothing, just for compatibility with PIL.
        :returns: An :py:class:`easy_thumbnails.VIL.Image.Image` object.
        """
        return self

    def crop(self, box=None):
        """
        Returns a rectangular region from this image. The box is a
        4-tuple defining the left, upper, right, and lower pixel
        coordinate. See :ref:`coordinate-system`.

        :param box: The crop rectangle, as a (left, upper, right, lower)-tuple.
        :returns: An :py:class:`easy_thumbnails.VIL.Image.Image` object.
        """
        copy = Image(size=self.size)
        copy.canvas.svg = self.canvas.svg.cloneNode(True)
        if box:
            bbox = list(self.getbbox())
            current_aspect_ratio = (bbox[2] - bbox[0]) / (bbox[3] - bbox[1])
            wanted_aspect_ratio = (box[2] - box[0]) / (box[3] - box[1])
            if current_aspect_ratio > wanted_aspect_ratio:
                new_width = wanted_aspect_ratio * bbox[3]
                bbox[0] += (bbox[2] - new_width) / 2
                bbox[2] = new_width
            else:
                new_height = bbox[2] / wanted_aspect_ratio
                bbox[1] += (bbox[3] - new_height) / 2
                bbox[3] = new_height
            copy.size = box[2] - box[0], box[3] - box[1]
            copy.canvas.svg.setAttribute('viewBox', '{0} {1} {2} {3}'.format(*bbox))
            copy.canvas.svg.setAttribute('width', '{0}'.format(*copy.size))
            copy.canvas.svg.setAttribute('height', '{1}'.format(*copy.size))
        return copy

    def filter(self, *args):
        """
        Does nothing, just for compatibility with PIL.
        :returns: An :py:class:`easy_thumbnails.VIL.Image.Image` object.
        """
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if hasattr(self, "fp") and getattr(self, "_exclusive_fp", False):
            if hasattr(self, "_close__fp"):
                self._close__fp()
            if self.fp:
                self.fp.close()
        self.fp = None

    def close(self):
        """
        Closes the file pointer, if possible.

        This operation will destroy the image core and release its memory.
        The image data will be unusable afterward.

        This function is only required to close images that have not
        had their file read and closed by the
        :py:meth:`~PIL.Image.Image.load` method. See
        :ref:`file-handling` for more information.
        """
        try:
            if hasattr(self, "_close__fp"):
                self._close__fp()
            self.fp.close()
            self.fp = None
        except Exception as msg:
            pass

        self.map = None
        self.im = None

    def save(self, fp, format=None, **params):
        """
        Saves this image under the given filename.  If no format is
        specified, the format to use is determined from the filename
        extension, if possible.

        You can use a file object instead of a filename. In this case,
        you must always specify the format. The file object must
        implement the ``seek``, ``tell``, and ``write``
        methods, and be opened in binary mode.

        :param fp: A filename (string), pathlib.Path object or file object.
        :param format: Must be None or 'SVG'.
        :param params: Unused extra parameters.
        :returns: None
        :exception ValueError: If the output format could not be determined
           from the file name.  Use the format option to solve this.
        :exception OSError: If the file could not be written.  The file
           may have been created, and may contain partial data.
        """

        filename = ""
        open_fp = False
        if isinstance(fp, (bytes, str)):
            filename = fp
            open_fp = True
        elif isinstance(fp, Path):
            filename = str(fp)
            open_fp = True
        if not filename and hasattr(fp, "name") and isinstance(fp.name, (bytes, str)):
            # only set the name for metadata purposes
            filename = fp.name

        suffix = Path(filename).suffix.lower()
        if format != 'SVG' and suffix != '.svg':
            raise ValueError("Image format is expected to be 'SVG' and file suffix to be '.svg'")

        if open_fp:
            fp = builtins.open(filename, "w+b")

        self.canvas.svg.writexml(fp)


def new(self, size, color=None):
    im = Image(size)
    if color:
        im.canvas.setFillColor(Color(*color))
    return im


def load(fp, mode='r'):
    """
    Opens and identifies the given SVG image file.

    :param fp: A filename (string), pathlib.Path object or a file object.
       The file object must implement :py:meth:`~file.read`,
       :py:meth:`~file.seek`, and :py:meth:`~file.tell` methods,
       and be opened in binary mode.
    :param mode: The mode.  If given, this argument must be "r".
    :returns: An :py:class:`easy_thumbnails.VIL.Image.Image` object.
    :exception FileNotFoundError: If the file cannot be found.
    :exception ValueError: If the ``mode`` is not "r", or if a ``StringIO``
       instance is used for ``fp``.
    """

    if mode != 'r':
        raise ValueError("bad mode %r" % mode)
    elif isinstance(fp, io.StringIO):
        raise ValueError(
            "StringIO cannot be used to open an image. "
            "Binary data must be used instead."
        )
    if isinstance(fp, Path):
        filename = str(fp.resolve())
    elif isinstance(fp, str):
        filename = fp
    else:
        raise RuntimeError("Can not open file.")
    drawing = svg2rlg(filename)
    if drawing is None:
        return
        # raise ValueError("cannot decode SVG image")
    im = Image(size=(drawing.width, drawing.height))
    renderSVG.draw(drawing, im.canvas)
    return im