"""
This module defines the :class:`GONetFile` class, which provides functionality for 
handling and processing GONet files. The class encapsulates the properties 
and methods required for manipulating the image data (including red, green, 
and blue channels) and metadata associated with GONet files.

The module supports various operations on GONet files, including:

- Loading image data from original raw (`.jpg`) or TIFF formats.
- Performing arithmetic operations between GONet files and scalar values.
- Writing image data to common formats like JPEG, TIFF, and FITS.
- Parsing and handling metadata for different file types.

For more info regarding how the raw data is parsed, see :doc:`raw_data`.

The :class:`GONetFile` class also includes support for operator overloading, allowing 
users to easily perform element-wise operations between GONet files or between 
a GONet file and scalar values.

In order to ensure that all arithmetic operations on the image channels are safe and
reliable, we cast the red, green, and blue channel arrays to float64 upon initialization.
The original pixel data is typically stored as uint12 or uint16, which are prone to
overflow or precision loss during common operations like addition, subtraction, or
division. By promoting the arrays to float64, we avoid these issues and enable robust
numerical processing — particularly important for calibration, normalization, or stacked
image analysis. This casting ensures consistency and protects users from subtle bugs that
can arise from working with fixed-width integer types.

**Functions**

- :func:`cast`: Convert a value to a JSON-serializable type if necessary.

**Classes**

- :class:`FileType`: Enumeration of file types used in GONet observations.
- :class:`GONetFile`: A class representing a GONet file.


Example usage
--------------
.. code-block:: python

   gonet_file = GONetFile.from_file('example_image.tiff')
   plt.imshow(gonet_file.green)

"""

from tifffile import tifffile
import os, PIL, operator
from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np
from enum import Enum, auto
from typing import Any
from astropy.io import fits

def cast(v: 'Any') -> 'Any':
    """
    Convert a value to a JSON-serializable type if necessary.

    This is primarily used to sanitize data types such as unusual TIFF formats 
    that cannot be serialized to JSON (e.g., numpy scalars, certain image metadata types).

    Parameters
    ----------
    v : :class:`Any`
        The input value to be cast.

    Returns
    -------
    :class:`Any`
        A version of the input that is safe for JSON serialization.
    """
    if isinstance(v, PIL.TiffImagePlugin.IFDRational):
        return v._numerator / v.denominator
    elif isinstance(v, tuple):
        return tuple(cast(t) for t in v)
    elif isinstance(v, bytes):
        return v.decode(errors="replace")
    elif isinstance(v, dict):
        for kk, vv in v.items():
            v[kk] = cast(vv)
        return v
    else: return v

class FileType(Enum):
    """
    Enumeration of file types used in GONet observations.

    This enum defines the standard types of data that a GONet file may represent,
    used for categorizing the file during processing or analysis.

    Attributes
    ----------
    SCIENCE : :class:`FileType`
        Represents a science frame (standard observational data).
    FLAT : :class:`FileType`
        Represents a flat field frame (used for pixel response correction).
    BIAS : :class:`FileType`
        Represents a bias frame (used for sensor readout offset correction).
    DARK : :class:`FileType`
        Represents a dark frame (used to correct for dark current noise).
    """
    
    SCIENCE = auto()  # Represents science data
    FLAT = auto()     # Represents flat field data
    BIAS = auto()     # Represents bias data
    DARK = auto()     # Represents dark frame data

class GONetFile:
    """
    A class representing a GONet file.

    This class provides methods for loading, interpreting, and processing GONet image data 
    along with its associated metadata. It supports operations such as reading binary formats, 
    extracting image channels, and converting pixel data into structured arrays.

    Attributes
    ----------
    RAW_FILE_OFFSET : :class:`int`
        Offset in bytes to the beginning of the raw data in the file (default: 18711040).
    RAW_HEADER_SIZE : :class:`int`
        Size in bytes of the file header preceding the image data (default: 32768).
    RAW_DATA_OFFSET : :class:`int`
        Offset in bytes to the raw image data, computed as ``RAW_FILE_OFFSET`` - ``RAW_HEADER_SIZE``.
    RELATIVETOEND : :class:`int`
        Flag used to indicate seeking relative to the end of the file (default: 2).
    PIXEL_PER_LINE : :class:`int`
        Number of pixels per image row (default: 4056).
    PIXEL_PER_COLUMN : :class:`int`
        Number of pixels per image column (default: 3040).
    PADDED_LINE_BYTES : :class:`int`
        Number of bytes used to store a single image row, including padding (default: 6112).
    USED_LINE_BYTES : :class:`int`
        Number of bytes used to store a single image row, based on 12-bit pixel encoding 
        (default: int(``PIXEL_PER_LINE`` * 12 / 8)).
    CHANNELS : :class:`list` of :class:`str`
        Names of the RGB channels available in the GONet image (default: ['red', 'green', 'blue']).
    """

    RAW_FILE_OFFSET = 18711040
    RAW_HEADER_SIZE = 32768
    RAW_DATA_OFFSET = RAW_FILE_OFFSET - RAW_HEADER_SIZE
    RELATIVETOEND = 2

    PIXEL_PER_LINE = 4056
    PIXEL_PER_COLUMN = 3040
    PADDED_LINE_BYTES = 6112  # Including padding
    USED_LINE_BYTES = int(PIXEL_PER_LINE * 12 / 8)

    CHANNELS = ['red', 'green', 'blue']

    def __init__(self, filename: str, red: np.ndarray, green: np.ndarray, blue: np.ndarray, meta: dict, filetype: FileType) -> None:
        """
        Initialize a :class:`GONetFile` instance with image data and metadata.

        This constructor sets up the internal state of a GONet file, including its 
        RGB channel data, metadata, and file type classification.

        Parameters
        ----------
        filename : :class:`str`
            Path or name of the GONet file.
        red : :class:`numpy.ndarray`
            Pixel data for the red channel. Will be cast to float64.
        green : :class:`numpy.ndarray`
            Pixel data for the green channel. Will be cast to float64.
        blue : :class:`numpy.ndarray`
            Pixel data for the blue channel. Will be cast to float64.
        meta : :class:`dict`
            Dictionary of extracted metadata.
        filetype : :class:`FileType`
            Type of GONet file (e.g., :attr:`FileType.SCIENCE`).
        """
        # --- Runtime type checking ---
        if not isinstance(filename, str):
            raise TypeError("filename must be a string")

        for name, arr in zip(['red', 'green', 'blue'], [red, green, blue]):
            if not isinstance(arr, np.ndarray):
                raise TypeError(f"{name} must be a numpy.ndarray")
            if arr.ndim != 2:
                raise ValueError(f"{name} must be a 2D array")

        if not isinstance(meta, dict):
            raise TypeError("meta must be a dict")

        if not isinstance(filetype, FileType):
            raise TypeError("filetype must be an instance of FileType")

        # --- Safe assignment ---
        self._filename = filename
        self._red = red.astype(np.float64)
        self._green = green.astype(np.float64)
        self._blue = blue.astype(np.float64)
        self._meta = meta
        self._filetype = filetype

    @property
    def filename(self) -> str:
        """
        Get the filename of the GONet file.

        Returns
        -------
        :class:`str`
            The name or path of the file associated with this :class:`GONetFile` instance.
        """
        return self._filename

    @property
    def red(self) -> np.ndarray:
        """
        Get the red channel data from the GONet file.

        Returns
        -------
        :class:`numpy.ndarray`
            A 2D array of pixel values corresponding to the red channel.
        """
        return self._red

    @property
    def green(self) -> np.ndarray:
        """
        Get the green channel data from the GONet file.

        Returns
        -------
        :class:`numpy.ndarray`
            A 2D array of pixel values corresponding to the green channel.
        """
        return self._green

    @property
    def blue(self) -> np.ndarray:
        """
        Get the blue channel data from the GONet file.

        Returns
        -------
        :class:`numpy.ndarray`
            A 2D array of pixel values corresponding to the blue channel.
        """
        return self._blue

    @property
    def meta(self) -> dict:
        """
        Get the metadata associated with the GONet file.

        Returns
        -------
        :class:`dict`
            Dictionary containing metadata fields extracted from the file header or sidecar.
        """
        return self._meta
    
    @property
    def filetype(self) -> FileType:
        """
        Get the file type of the GONet file.

        Returns
        -------
        :class:`FileType`
            The type of the file, such as :attr:`~FileType.SCIENCE`, :attr:`~FileType.FLAT`, etc.
        """
        return self._filetype

    def channel(self, channel_name: str) -> np.ndarray:
        """
        Retrieve the pixel data for a specified color channel.

        This method returns the image data associated with the specified
        color channel as a :class:`numpy.ndarray`.

        Parameters
        ----------
        channel_name : :class:`str`
            The name of the channel to retrieve. Must be one of
            ``'red'``, ``'green'``, or ``'blue'``.

        Returns
        -------
        :class:`numpy.ndarray`
            The pixel data corresponding to the requested color channel.

        Raises
        ------
        :class:`ValueError`
            If an invalid channel name is provided.
        """
        if channel_name not in self.CHANNELS:
            raise ValueError(f"Invalid channel name: {channel_name}. Allowed channels: {self.CHANNELS}")
        return getattr(self, channel_name)
    
    def write_to_jpeg(self, output_filename: str) -> None:
        """
        Write the RGB image data to a JPEG file.

        This method assumes that the red, green, and blue channels are in the
        uint16 range [0, 65535], and rescales them to the standard 8-bit range
        [0, 255] required for JPEG output. Values outside this range are clipped.

        Parameters
        ----------
        output_filename : :class:`str`
            Path where the resulting JPEG file will be saved.
        """
        def convert_to_uint8(arr):
            arr = np.clip(arr, 0, 2**16 - 1)
            return np.round(arr / (2**16 - 1) * 255).astype(np.uint8)

        rgb = np.stack([
            convert_to_uint8(self.red),
            convert_to_uint8(self.green),
            convert_to_uint8(self.blue)
        ], axis=-1)

        image = Image.fromarray(rgb, mode="RGB")
        image.save(output_filename, format="JPEG")

    def write_to_tiff(self, output_filename: str) -> None:
        """
        Write the RGB image data to a TIFF file.

        This method assumes that the red, green, and blue channels are in the
        uint16 range [0, 65535]. Values outside this range are clipped, and
        the data is cast to uint16 for TIFF compatibility.

        Parameters
        ----------
        output_filename : :class:`str`
            Path where the resulting TIFF file will be saved.
        """
        rgb_stack = np.stack([
            np.clip(self.red, 0, 2**16 - 1).astype(np.uint16),
            np.clip(self.green, 0, 2**16 - 1).astype(np.uint16),
            np.clip(self.blue, 0, 2**16 - 1).astype(np.uint16)
        ], axis=0)

        tifffile.imwrite(output_filename, rgb_stack, photometric='rgb', metadata=self.meta)

    def write_to_fits(self, output_filename: str) -> None:
        """
        Write the image data to a multi-extension FITS file.

        This method saves the red, green, and blue channel data into separate
        HDUs (Header/Data Units) within a single FITS file. The metadata stored
        in the ``meta`` attribute is propagated into the FITS headers, adhering
        to the standard FITS format.

        Parameters
        ----------
        output_filename : :class:`str`
            The full path and filename where the FITS file will be written.

        Returns
        -------
        :class:`None`
            This method does not return a value.

        Notes
        -----

        - The FITS file is created using the :mod:`astropy.io.fits` library.
        - Each color channel (red, green, blue) is stored in a separate image extension.
        - Metadata keys longer than 8 characters or containing lowercase letters or symbols
          will be truncated or sanitized to conform to FITS header requirements.

        """
        
        # Create the header for each extension based on the meta attribute
        def create_header(channel_name: str):
            header = fits.Header()
            
            # Populate header with the meta dictionary's information
            for key, value in self.meta.items():
                # Convert labels to respect FITS standards (e.g., max 8 chars, uppercase)
                if len(key) > 8:
                    key = key[:8]
                header[key.upper()] = value
            
            # Add specific channel information to the header
            header['CHANNEL'] = channel_name.upper()  # Add channel info to header
            header['EXTNAME'] = channel_name.upper()  # Extension name

            return header

        # Create the data for each channel
        red_data = self.red
        green_data = self.green
        blue_data = self.blue

        # Create the FITS HDUs (Header/Data Units) for each channel
        hdu_list = []

        # Red channel extension
        red_header = create_header('red')
        red_hdu = fits.ImageHDU(data=red_data, header=red_header)
        hdu_list.append(red_hdu)

        # Green channel extension
        green_header = create_header('green')
        green_hdu = fits.ImageHDU(data=green_data, header=green_header)
        hdu_list.append(green_hdu)

        # Blue channel extension
        blue_header = create_header('blue')
        blue_hdu = fits.ImageHDU(data=blue_data, header=blue_header)
        hdu_list.append(blue_hdu)

        # Create the Primary HDU (needed for a valid FITS file)
        primary_hdu = fits.PrimaryHDU()
        hdu_list.insert(0, primary_hdu)

        # Create the HDU list (multi-extension FITS file)
        hdul = fits.HDUList(hdu_list)

        # Write the FITS file to disk
        hdul.writeto(output_filename, overwrite=True)

    @classmethod
    def from_file(cls, filepath: str, filetype: FileType = FileType.SCIENCE, meta: bool = True) -> 'GONetFile':
        """
        Create a :class:`GONetFile` instance from a TIFF or JPEG file.

        This class method reads a GONet image file, extracts the red, green, and blue
        channel data, and optionally parses the associated metadata. It returns a fully
        initialized :class:`GONetFile` object.

        Parameters
        ----------
        filepath : :class:`str`
            Full path to the image file. The file must be in `.tif`, `.tiff`, or `.jpg` format.
        
        filetype : :class:`FileType`, optional
            Type of the file, chosen from the :class:`FileType` enumeration 
            (e.g., ``SCIENCE``, ``FLAT``, ``BIAS``, ``DARK``). Defaults to ``FileType.SCIENCE``.
        
        meta : :class:`bool`, optional
            If True (default), metadata will be extracted and included in the resulting object.
            If False, metadata will be skipped.

        Returns
        -------
        :class:`GONetFile`
            A new instance of the :class:`GONetFile` class initialized with the file's pixel data
            and (optionally) metadata.

        Raises
        ------
        FileNotFoundError
            If the specified file does not exist or cannot be accessed.
        
        ValueError
            If the file extension is not supported (only `.tif`, `.tiff`, or `.jpg` are allowed).

    
        """

        if not os.path.isfile(filepath):
            raise FileNotFoundError(f'Could not find file {filepath}.')
        if filepath.split('.')[-1] in ['tiff','TIFF','tif','TIF']:
            parsed_data, parsed_meta = cls._parse_tiff_file(filepath, meta)
        elif filepath.split('.')[-1] in ['jpg']:
            parsed_data, parsed_meta = cls._parse_raw_file(filepath, meta)
        else:
            raise ValueError("Extension must be '.tiff', '.TIFF', '.tif', '.TIF' or the original '.jpg' from a GONet camera.")

        return cls(
            filename = filepath,
            red = parsed_data[0],
            green = parsed_data[1],
            blue = parsed_data[2],
            meta = parsed_meta,
            filetype = filetype
        )

    @staticmethod
    def _parse_tiff_file(filepath: str, meta: bool) -> tuple[np.ndarray, dict]:
        """
        Parse a TIFF file and extract RGB channel data and optional metadata.

        This static method reads a TIFF file and separates the image into red, green, 
        and blue channels. If ``meta`` is True, it also extracts metadata from the file 
        header and returns it alongside the image data.

        Parameters
        ----------
        filepath : :class:`str`
            Path to the TIFF file to be parsed.
        
        meta : :class:`bool`
            Whether to extract metadata from the file. If True, metadata will be 
            returned as a dictionary. If False, the metadata will be an empty dictionary.

        Returns
        -------
        :class:`tuple` [ :class:`numpy.ndarray`, :class:`dict` ]
            A tuple containing:
            
            - A NumPy array of shape ``(3, H, W)`` representing the red, green, and blue channels.
            - A dictionary of metadata (empty if ``meta`` is False).

        Raises
        ------
        FileNotFoundError
            If the file does not exist or is not accessible.
        ValueError
            If the TIFF file does not contain 3 channels.
        """

        with tifffile.TiffFile(filepath) as tif:
            tiff_data = tif.asarray()
            tiff_meta = tif.shaped_metadata[0]
            if meta:
                return tiff_data, tiff_meta
            else:
                return tiff_data, None

    @staticmethod
    def _parse_raw_file(filepath: str, meta: bool) -> tuple[np.ndarray, dict]:
        """
        Parse a raw GONet file and extract RGB channel data and optional metadata.

        This static method reads a GONet raw file—typically with a `.jpg` extension 
        but not in standard JPEG format—and extracts the red, green, and blue image 
        channels. If ``meta`` is True, it also extracts metadata from the embedded 
        header.

        Parameters
        ----------
        filepath : :class:`str`
            Path to the raw file to be parsed.
        
        meta : :class:`bool`
            Whether to extract metadata from the file. If True, metadata will be 
            returned as a dictionary. If False, the metadata will be an empty dictionary.

        Returns
        -------
        :class:`tuple` [ :class:`numpy.ndarray`, :class:`dict` ]
            A tuple containing:

            - A NumPy array of shape ``(3, H, W)`` representing the red, green, and blue channels.
            - A dictionary of metadata (empty if ``meta`` is False).

        Notes
        -----

        - The file is assumed to follow the GONet binary structure with embedded metadata 
          and interleaved RGB pixel data.

        Raises
        ------
        FileNotFoundError
            If the file does not exist or is not accessible.
        ValueError
            If the file format is incompatible or corrupted.
        """

        with open(filepath, "rb") as file:
            file.seek(-GONetFile.RAW_DATA_OFFSET,GONetFile.RELATIVETOEND)
            s=np.zeros((GONetFile.PIXEL_PER_LINE,GONetFile.PIXEL_PER_COLUMN),dtype='uint16')   
            # do this at least 3040 times though the precise number of lines is a bit unclear
            for i in range(GONetFile.PIXEL_PER_COLUMN):

                # read in 6112 bytes, but only 6084 will be used
                bdLine = file.read(GONetFile.PADDED_LINE_BYTES)
                gg = np.frombuffer(bdLine[0:GONetFile.USED_LINE_BYTES], dtype=np.uint8)
                s[0::2,i] = (gg[0::3]<<4) + (gg[2::3]&15)
                s[1::2,i] = (gg[1::3]<<4) + (gg[2::3]>>4)

        # form superpixel array
        sp=np.empty((int(GONetFile.PIXEL_PER_LINE/2),int(GONetFile.PIXEL_PER_COLUMN/2),3))
        sp[:,:,0]=s[1::2,1::2]                      # red
        sp[:,:,1]=(s[0::2,1::2]+s[1::2,0::2])/2     # green
        sp[:,:,2]=s[0::2,0::2]                      # blue

        array=sp.transpose()

        # Extracting the metadata
        if meta:
            jpeg = Image.open(filepath)
            meta_data = jpeg._getexif()
            tiff_meta = {}
            for k,v in meta_data.items():
                v = cast(v)
                tiff_meta[TAGS[k]] = v
        else:
            tiff_meta = None


        return array, tiff_meta

    '''
    ---------------------
    Operators overloading.
    ---------------------
    
    The GONetFile class has attributes that are numpy arrays.
    Therefore it could be useful to allow operations applied to
    the red, green and blue channels all at the same time,
    instead of executing the operation 3 times in the code.
    For instance, summing 2 GONetFile instances (go1, go2) as

    go1 + go2

    instead of having to do

    go1.red + go2.red
    go1.green + go2.green
    go1.blue + go2.blue

    So operators are overloaded to allow this.

    '''

    def _operate(self, other, op) -> 'GONetFile':
        """
        Perform an element-wise operation on the current :class:`GONetFile` instance.

        This internal method supports element-wise operations between the current 
        GONetFile instance and either another GONetFile instance or a scalar value.
        The operation is applied independently to each color channel 
        (red, green, and blue) using the provided binary operator.

        Parameters
        ----------
        other : :class:`GONetFile` or scalar
            The operand for the operation. This can be another :class:`GONetFile` 
            instance or a scalar (e.g., :class:`int` or :class:`float`).

        op : :class:`function`
            A binary operator function (e.g., :func:`numpy.add`, :func:`numpy.multiply`)
            that performs the desired operation between corresponding pixel arrays.

        Returns
        -------
        :class:`GONetFile`
            A new :class:`GONetFile` instance with the operation applied to each channel.
            If ``other`` is a GONetFile, the result has no metadata or file type.
            If ``other`` is a scalar, metadata and file type are preserved.

        Raises
        ------
        TypeError
            If ``other`` is neither a GONetFile nor a scalar.
        
        ValueError
            If the operation cannot be broadcast between the channels and ``other``.

        Notes
        -----

        - This method is primarily used internally to implement operators like 
          `__add__`, `__sub__`, etc.
        - Metadata is only retained when operating with scalars.

        """
        if isinstance(other, GONetFile):
            return GONetFile(
                filename = None, 
                red = op(self.red, other.red),
                green = op(self.green, other.green),
                blue = op(self.blue, other.blue),
                meta = None,
                filetype = None
            )
        else:
            return GONetFile(
                filename = self.filename, 
                red = op(self.red, other),
                green = op(self.green, other),
                blue = op(self.blue, other),
                meta = self.meta,
                filetype = self.filetype
            )

    # Addition
    def __add__(self, other: Any) -> 'GONetFile':
        """
        Add another object to this :class:`GONetFile` instance.

        This method overloads the ``+`` operator to support element-wise addition 
        between the current :class:`GONetFile` and either another :class:`GONetFile` 
        or a scalar value (e.g., :class:`int`, :class:`float`). Addition is performed 
        independently on the red, green, and blue channels using :func:`numpy.add`.

        Parameters
        ----------
        other : :class:`GONetFile` or scalar
            The operand to add. Can be another :class:`GONetFile` or a scalar value.

        Returns
        -------
        :class:`GONetFile`
            A new instance resulting from the addition. If `other` is a 
            :class:`GONetFile`, the returned object has no metadata or file type.

        Raises
        ------
        TypeError
            If the operation is not supported between the operands.
        
        ValueError
            If the image shapes are incompatible.


        """
        return self._operate(other, operator.add)

    __radd__ = __add__

    # In-place addition (+=)
    def __iadd__(self, other: Any) -> 'GONetFile':
        """
        Perform in-place addition on this :class:`GONetFile` instance.

        This method overloads the ``+=`` operator to support in-place element-wise 
        addition of another :class:`GONetFile` or a scalar value (e.g., :class:`int`, 
        :class:`float`). Addition is performed independently on the red, green, and 
        blue channels using :func:`numpy.add`.

        Parameters
        ----------
        other : :class:`GONetFile` or scalar
            The value to add in-place. Can be another :class:`GONetFile` or a scalar.

        Returns
        -------
        :class:`GONetFile`
            The modified instance after in-place addition.

        Raises
        ------
        TypeError
            If the operation is not supported between the operands.

        ValueError
            If the channel dimensions are incompatible for element-wise addition.


        """
        return self._operate(other, operator.iadd)

    # Multiplication
    def __mul__(self, other: Any) -> 'GONetFile':
        """
        Perform element-wise multiplication using the ``*`` operator.

        This method multiplies the red, green, and blue channels of the current 
        :class:`GONetFile` instance with either another :class:`GONetFile` instance 
        or a scalar (e.g., :class:`int`, :class:`float`). The multiplication is 
        performed element-wise using :func:`numpy.multiply`.

        Parameters
        ----------
        other : :class:`GONetFile` or scalar
            The object to multiply with. Can be another :class:`GONetFile` instance 
            or a scalar value.

        Returns
        -------
        :class:`GONetFile`
            A new :class:`GONetFile` instance containing the result of the multiplication.

        Raises
        ------
        TypeError
            If the operation is not supported between the operands.

        ValueError
            If the channel dimensions are incompatible for element-wise multiplication.


        """
        return self._operate(other, operator.mul)

    __rmul__ = __mul__

    # Subtraction
    def __sub__(self, other: Any) -> 'GONetFile':
        """
        Perform element-wise subtraction using the ``-`` operator.

        This method subtracts either another :class:`GONetFile` instance or a scalar 
        (e.g., :class:`int`, :class:`float`) from the current :class:`GONetFile` 
        instance. The operation is applied independently to the red, green, and blue 
        channels using :func:`numpy.subtract`.

        Parameters
        ----------
        other : :class:`GONetFile` or scalar
            The object to subtract. Can be another :class:`GONetFile` instance or a scalar value.

        Returns
        -------
        :class:`GONetFile`
            A new :class:`GONetFile` instance containing the result of the subtraction.

        Raises
        ------
        TypeError
            If the operation is not supported between the operands.

        ValueError
            If the channel dimensions are incompatible for element-wise subtraction.


        """
        return self._operate(other, operator.sub)

    # Division
    def __truediv__(self, other: Any) -> 'GONetFile':
        """
        Perform element-wise division using the ``/`` operator.

        This method divides the red, green, and blue channels of the current 
        :class:`GONetFile` instance by either another :class:`GONetFile` instance 
        or a scalar (e.g., :class:`int`, :class:`float`). The division is 
        applied using :func:`numpy.true_divide`.

        Parameters
        ----------
        other : :class:`GONetFile` or scalar
            The object to divide by. Can be another :class:`GONetFile` instance 
            or a scalar value.

        Returns
        -------
        :class:`GONetFile`
            A new :class:`GONetFile` instance containing the result of the division.

        Raises
        ------
        ZeroDivisionError
            If division by zero occurs (e.g., scalar is zero or zero elements in another GONetFile).
        
        TypeError
            If the operation is not supported between the operands.


        """
        return self._operate(other, operator.truediv)
    
    # I'd like to start writing some tests. But first I need to understand why in line 144 we add 0.5 (to avoid zeros?) and wether we can use uint32 

    

    # # Comparison functions
    # def __lt__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self.red < other.red, self.green < other.green, self.blue < other.blue, None)
    #     else:
    #         return GONetFile(self.filename, self.red < other, self.green < other, self.blue < other, self.meta)
        
    # def __le__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self.red <= other.red, self.green <= other.green, self.blue <= other.blue, None)
    #     else:
    #         return GONetFile(self.filename, self.red <= other, self.green <= other, self.blue <= other, self.meta)
        
    # def __eq__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self.red == other.red, self.green == other.green, self.blue == other.blue, None)
    #     else:
    #         return GONetFile(self.filename, self.red == other, self.green == other, self.blue == other, self.meta)
        
    # def __ne__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self.red != other.red, self.green != other.green, self.blue != other.blue, None)
    #     else:
    #         return GONetFile(self.filename, self.red != other, self.green != other, self.blue != other, self.meta)
        
    # def __ge__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self.red > other.red, self.green > other.green, self.blue > other.blue, None)
    #     else:
    #         return GONetFile(self.filename, self.red > other, self.green > other, self.blue > other, self.meta)
        
    # def __gt__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self.red >= other.red, self.green >= other.green, self.blue >= other.blue, None)
    #     else:
    #         return GONetFile(self.filename, self.red >= other, self.green >= other, self.blue >= other, self.meta)
        
    # # Making sure we are using numpy mean and median
    # def mean(self, *args, **kwargs):
    #     return np.array([np.mean(self.red, *args, **kwargs), np.mean(self.green, *args, **kwargs), np.mean(self.blue, *args, **kwargs)])
    
    # def median(self, *args, **kwargs):
    #     return np.array([np.median(self.red, *args, **kwargs), np.median(self.green, *args, **kwargs), np.median(self.blue, *args, **kwargs)])
