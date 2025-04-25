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
import os, PIL, operator, re, ast, pprint
from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np
from enum import Enum, auto
from typing import Any, Optional, Union
from astropy.io import fits
from pathlib import Path


def scale_uint12_to_16bit_range(x):
    """
    Linearly scales unsigned 12-bit integer values to the full 16-bit range [0, 65535].

    This function maps values from the uint12 range [0, 4095] to the float range [0, 65535],
    preserving relative magnitudes without rounding or type conversion to integer.

    Parameters
    ----------
    x : array-like or int
        Input value(s) in the uint12 range [0, 4095]. Can be a scalar or NumPy array.

    Returns
    -------
    np.ndarray or float
        Scaled value(s) in the float range [0.0, 65535.0]. Output dtype is float64.

    Raises
    ------
    ValueError
        If any input values are outside the valid uint12 range.

    """
    x = np.asarray(x)

    max_uint12 = 2**12 - 1  # 4095
    max_uint16 = 2**16 - 1  # 65535

    if np.any((x < 0) | (x > max_uint12)):
        raise ValueError(f"Input values must be in the range [0, {max_uint12}] for uint12.")

    scaled = (x / max_uint12) * max_uint16
    return scaled

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

    def __init__(
        self,
        filename: str,
        red: np.ndarray,
        green: np.ndarray,
        blue: np.ndarray,
        meta: Optional[dict],
        filetype: FileType
    ) -> None:
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
        meta : :class:`dict` or :data:`None`
            Dictionary of extracted metadata, or None if no metadata is available.
        filetype : :class:`FileType`
            Type of GONet file (e.g., :attr:`FileType.SCIENCE`).

        Raises
        ------
        TypeError
            If input types are incorrect.
        ValueError
            If image arrays are not 2D.
        """
        # --- Runtime type checking ---
        if filename is not None and not isinstance(filename, str):
            raise TypeError("filename must be a string or None")

        for name, arr in zip(['red', 'green', 'blue'], [red, green, blue]):
            if not isinstance(arr, np.ndarray):
                raise TypeError(f"{name} must be a numpy.ndarray")
            if arr.ndim != 2:
                raise ValueError(f"{name} must be a 2D array")

        if meta is not None and not isinstance(meta, dict):
            raise TypeError("meta must be a dict or None")

        if filetype is not None and not isinstance(filetype, FileType):
            raise TypeError("filetype must be an instance of FileType or None")

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
    
    def write_to_jpeg(self, output_filename: str, white_balance: bool = True) -> None:
        """
        Write the RGB image data to a JPEG file.

        This method assumes that the red, green, and blue channels are in the
        uint16 range [0, 65535], and rescales them to the standard 8-bit range
        [0, 255] required for JPEG output. Values outside this range are clipped,
        and the data is converted to 8-bit for JPEG compatibility.

        If ``white_balance`` is True, the method applies red and blue channel gains
        from ``self.meta['WB']`` prior to conversion, in order to produce a 
        more natural-looking image. The white balance is expected to be a list 
        or tuple of two floats: [R_gain, B_gain].

        Parameters
        ----------
        output_filename : :class:`str`
            Path where the resulting JPEG file will be saved.

        white_balance : :class:`bool`, optional
            Whether to apply white balance using gains from metadata (default is False).

        Raises
        ------
        ValueError
            If ``white_balance`` is True but the WB metadata is missing or invalid.
        """
        def convert_to_uint8(arr):
            arr = np.clip(arr, 0, 2**16 - 1)
            return np.round(arr / (2**16 - 1) * 255).astype(np.uint8)

        red   = self.red.astype(np.float32)
        green = self.green.astype(np.float32)
        blue  = self.blue.astype(np.float32)

        # Apply white balance if requested
        if white_balance:
            try:
                r_gain, b_gain = self.meta["JPEG"]["WB"]
                red   *= r_gain
                blue  *= b_gain
                # green *= 1.0 (implicitly)
            except Exception as e:
                raise ValueError("White balance metadata 'WB' is missing or invalid.") from e

        # Convert to uint8 and stack
        rgb = np.stack([
            convert_to_uint8(red),
            convert_to_uint8(green),
            convert_to_uint8(blue)
        ], axis=-1)

        image = Image.fromarray(rgb, mode="RGB")
        image.save(output_filename, format="JPEG", quality=100)


    def write_to_tiff(self, output_filename: str, white_balance: bool = True) -> None:
        """
        Write the RGB image data to a TIFF file.

        This method assumes that the red, green, and blue channels are in the
        uint16 range [0, 65535]. Values outside this range are clipped, and
        the data is cast to uint16 for TIFF compatibility.

        If ``white_balance`` is True, the method applies red and blue channel gains
        from ``self.meta['JPEG']['WB']`` prior to writing, in order to produce a 
        more natural-looking image. The white balance is expected to be a list 
        or tuple of two floats: [R_gain, B_gain].

        Parameters
        ----------
        output_filename : :class:`str`
            Path where the resulting TIFF file will be saved.

        white_balance : :class:`bool`, optional
            Whether to apply white balance using gains from metadata (default is True).

        Raises
        ------
        ValueError
            If ``white_balance`` is True but the WB metadata is missing or invalid.
        """
        red   = self.red.astype(np.float32)
        green = self.green.astype(np.float32)
        blue  = self.blue.astype(np.float32)

        if white_balance:
            try:
                r_gain, b_gain = self.meta["JPEG"]["WB"]
                red *= r_gain
                blue *= b_gain
                # green remains unchanged
            except Exception as e:
                raise ValueError("White balance metadata 'WB' is missing or invalid.") from e

        rgb_stack = np.stack([
            np.clip(red, 0, 2**16 - 1).astype(np.uint16),
            np.clip(green, 0, 2**16 - 1).astype(np.uint16),
            np.clip(blue, 0, 2**16 - 1).astype(np.uint16)
        ], axis=0)

        tifffile.imwrite(output_filename, rgb_stack, photometric='rgb')

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

        def build_base_header():
            header = fits.Header()

            if self.meta is None:
                return header  # Return empty header if no metadata

            header['GONETCAM'] = (self.meta.get('hostname', 'Unknown'), 'GONet camera identifier')
            header['GONETVER'] = (self.meta.get('version', 'Unknown'), 'GONet software version')
            header['MAKE']     = (self.meta.get('Make', 'Unknown'), 'Camera manufacturer')
            header['MODEL']    = (self.meta.get('Model', 'Unknown'), 'Camera model')

            header['BAYWIDTH'] = (self.meta.get('bayer_width', -1), 'Raw Bayer array width')
            header['BAYHEIGH'] = (self.meta.get('bayer_height', -1), 'Raw Bayer array height')
            header['IMGWIDTH'] = (self.meta.get('image_width', -1), 'Demosaiced image width')
            header['IMGHEIGH'] = (self.meta.get('image_height', -1), 'Demosaiced image height')

            header['ISOSET']   = (self.meta.get('ISOSpeedRatings', -1), 'ISO sensitivity rating (log2-scaled index)')
            header['WBAUTO']   = (self.meta.get('WhiteBalance', -1), 'White balance mode (0=Auto)')

            header['DATE-OBS'] = (self.meta.get('DateTime', 'Unknown'), 'File creation date/time')
            header['EXPTIME']  = (float(self.meta.get('exposure_time', -1)), 'Exposure time in seconds')
            header['SHUTSPD']  = (float(self.meta.get('shutter_speed', -1)), 'Shutter speed value (log2 scale)')

            header['RESUNIT']  = (self.meta.get('ResolutionUnit', -1), 'Resolution unit')
            header['LAT']      = (self.meta.get('latitude', 0.0), 'Latitude in decimal degrees')
            header['LON']      = (self.meta.get('longitude', 0.0), 'Longitude in decimal degrees')
            header['ALT']      = (self.meta.get('altitude', 0.0), 'Altitude in meters')

            header['LENSCAP']  = (self.meta.get('lenscap', 'Unknown'), 'Lenscap status')
            header['ANAGAIN']  = (self.meta.get('analog_gain', -1.0), 'Analog gain used during capture')

            return header

        # Base metadata header
        base_header = build_base_header()

        # Create each image HDU with proper extensions
        def make_channel_hdu(data: np.ndarray, channel: str) -> fits.ImageHDU:
            hdr = base_header.copy()
            hdr['CHANNEL'] = (channel.upper(), 'Image channel')
            hdr['EXTNAME'] = (channel.upper(), 'Extension name')
            return fits.ImageHDU(data=data, header=hdr)

        red_hdu = make_channel_hdu(self.red, 'red')
        green_hdu = make_channel_hdu(self.green, 'green')
        blue_hdu = make_channel_hdu(self.blue, 'blue')

        # Create primary HDU (no data)
        primary_hdu = fits.PrimaryHDU()

        # Assemble HDUList
        hdul = fits.HDUList([primary_hdu, red_hdu, green_hdu, blue_hdu])
        hdul.writeto(output_filename, overwrite=True)


    @classmethod
    def from_file(cls, filepath: Union[str, Path], filetype: FileType = FileType.SCIENCE, meta: bool = True) -> 'GONetFile':
        """
        Create a :class:`GONetFile` instance from a TIFF or JPEG file.

        This class method reads a GONet image file, extracts the red, green, and blue
        channel data, and optionally parses the associated metadata. It returns a fully
        initialized :class:`GONetFile` object.

        Parameters
        ----------
        filepath : :class:`str` or :class:`pathlib.Path`
            Full path to the image file. The file must be in `.tif`, `.tiff`, or `.jpg` format.
        
        filetype : :class:`FileType`, optional
            Type of the file, chosen from the :class:`FileType` enumeration.
            Defaults to ``FileType.SCIENCE``.
        
        meta : :class:`bool`, optional
            If True (default), metadata will be extracted and included. If False, metadata will be skipped.

        Returns
        -------
        :class:`GONetFile`
            A new instance initialized with the file's pixel data and metadata.

        Raises
        ------
        FileNotFoundError
            If the specified file does not exist.
        
        ValueError
            If the file extension is unsupported (must be `.tif`, `.tiff`, `.jpg`).

        Notes
        -----
        Metadata extraction is supported only for `.jpg` files. TIFF files are read for image data only.
        """
        # Normalize filepath
        filepath = Path(filepath)

        if not filepath.is_file():
            raise FileNotFoundError(f'Could not find file {filepath}.')

        suffix = filepath.suffix.lower()
        if suffix in ['.tif', '.tiff']:
            parsed_data = cls._parse_tiff_file(str(filepath))
            parsed_meta = None  # No metadata for TIFFs
        elif suffix == '.jpg':
            parsed_data = cls._parse_raw_file(str(filepath))
            parsed_meta = None
            if meta:
                jpeg = Image.open(filepath)
                raw_exif = jpeg._getexif()
                parsed_meta = cls._parse_exif_metadata(raw_exif)
        else:
            raise ValueError("Extension must be '.tiff', '.tif', or original '.jpg' from a GONet camera.")

        return cls(
            filename=str(filepath.name),  # Only the filename part, no directory
            red=parsed_data[0],
            green=parsed_data[1],
            blue=parsed_data[2],
            meta=parsed_meta,
            filetype=filetype
        )

    @staticmethod
    def _parse_tiff_file(filepath: str) -> tuple[np.ndarray, dict]:
        """
        Parse a TIFF file and extract RGB channel data and optional metadata.

        This static method reads a TIFF file and separates the image into red, green, 
        and blue channels.

        Parameters
        ----------
        filepath : :class:`str`
            Path to the TIFF file to be parsed.
 
        Returns
        -------
        :class:``numpy.ndarray``
            A NumPy array of shape ``(3, H, W)`` representing the red, green, and blue channels.

        Raises
        ------
        FileNotFoundError
            If the file does not exist or is not accessible.
        ValueError
            If the TIFF file does not contain 3 channels.
        """

        with tifffile.TiffFile(filepath) as tif:
            tiff_data = tif.asarray()
            return tiff_data

    @staticmethod
    def _parse_raw_file(filepath: str) -> tuple[np.ndarray, dict]:
        """
        Parse a raw GONet file and extract RGB channel data and optional metadata.

        This static method reads a GONet raw file—typically with a `.jpg` extension 
        but not in standard JPEG format—and extracts the red, green, and blue image 
        channels.

        Parameters
        ----------
        filepath : :class:`str`
            Path to the raw file to be parsed.
        
        Returns
        -------
        :class:``numpy.ndarray``
            A NumPy array of shape ``(3, H, W)`` representing the red, green, and blue channels.

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
                s[0::2, i] = (gg[0::3].astype(np.uint16) << 4) + (gg[2::3].astype(np.uint16) & 15)
                s[1::2, i] = (gg[1::3].astype(np.uint16) << 4) + (gg[2::3].astype(np.uint16) >> 4)

        # form superpixel array
        sp=np.empty((int(GONetFile.PIXEL_PER_LINE/2),int(GONetFile.PIXEL_PER_COLUMN/2),3))
        sp[:,:,0]=s[1::2,1::2]                      # red
        sp[:,:,1]=(s[0::2,1::2]+s[1::2,0::2])/2     # green
        sp[:,:,2]=s[0::2,0::2]                      # blue

        array=scale_uint12_to_16bit_range(sp.transpose())

        return array
    
    @staticmethod
    def _parse_exif_metadata(exif: dict) -> dict:
        """
        Extract and restructure EXIF metadata from a JPEG file into a structured dictionary.

        Parameters
        ----------
        exif : dict
            A dictionary containing raw EXIF metadata extracted from the JPEG file.

        Returns
        -------
        dict
            A structured metadata dictionary, with JPEG-related keys under 'JPEG'.
        """
    
        structured = {}
        jpeg_meta = {}
        gps_meta = {}

        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, str(tag_id))

            if tag == "Artist":
                # Use a regex to match key-value pairs, including tuples inside parentheses
                # This avoids splitting on commas inside values
                matches = re.finditer(r'(\w+):\s*(\([^)]+\)|[^,]+)', value)
                for match in matches:
                    k, v = match.groups()
                    k = k.strip().lower()
                    v = v.strip()

                    if k == "wb":
                        try:
                            jpeg_meta["WB"] = [float(x.strip()) for x in v.strip("()").split(',')]
                        except Exception:
                            continue  # skip malformed white balance
                    # We get the latitude, longitude and altitude from the GPS field so we skip them here
                    elif k in {"lat", "long", "alt"}:
                        continue
                        # try:
                        #     structured["latitude" if k == "lat" else "longitude" if k == "long" else "altitude"] = float(v)
                        # except ValueError:
                        #     continue
                    else:
                        structured[k] = v
                continue

            # It looks like Software repeats stuff in the artist fiels, so I'll ignore it
            # I will leave the logic in here in case it is useful
            elif tag == "Software":
                continue
                # Parse: 'GONetDolus X.X WB: (3.35, 1.59)'
                # wb_match = re.search(r'WB:\s*\(([^)]+)\)', value)
                # if wb_match:
                #     structured["WB"] = [float(x) for x in wb_match.group(1).split(',')]

                # # Also extract software version if useful
                # parts = value.split()
                # if parts:
                #     structured["software"] = parts[0]
                #     if len(parts) > 1 and parts[1] != "WB:":
                #         structured["version"] = parts[1]
                # continue

            elif tag == "GPSInfo":
                gps = value

                # Normalize keys to integers (if they're strings)
                gps_normalized = {}
                for k, v in gps.items():
                    try:
                        gps_normalized[int(k)] = v
                    except (ValueError, TypeError):
                        gps_normalized[k] = v  # fallback for non-integer keys

                def dms_to_deg(dms):
                    return dms[0] + dms[1] / 60.0 + dms[2] / 3600.0

                if 1 in gps_normalized and 2 in gps_normalized:
                    lat = dms_to_deg(gps_normalized[2])
                    if gps_normalized[1] in ("S", b"S"):
                        lat = -lat
                    gps_meta["latitude"] = float(lat)

                if 3 in gps_normalized and 4 in gps_normalized:
                    lon = dms_to_deg(gps_normalized[4])
                    if gps_normalized[3] in ("W", b"W"):
                        lon = -lon
                    gps_meta["longitude"] = float(lon)

                if 6 in gps_normalized:
                    gps_meta["altitude"] = float(gps_normalized[6])
                continue

            elif tag == "MakerNote":
                # Parse values like 'gain_r=1.000 gain_b=1.000'
                if isinstance(value, bytes):
                    value = value.decode("latin1")

                for match in re.finditer(r'(\w+)=([-\d.]+)', value):
                    k, v = match.groups()
                    if k.lower() == 'ag':
                        structured['analog_gain'] = float(v)
                    else:
                        continue
                    #structured[k.lower()] = float(v)
                continue

            elif tag == "ComponentsConfiguration":
                decoded = {
                    1: "Y", 2: "Cb", 3: "Cr", 4: "R", 5: "G", 6: "B", 0: ""
                }
                component_str = "".join(decoded.get(b, "?") for b in value)
                jpeg_meta["ComponentsConfiguration"] = component_str
                continue

            elif tag == "YCbCrPositioning":
                YCBCR_POSITIONING_MAP = {
                    1: "Centered",
                    2: "Co-sited"
                }
                jpeg_meta["YCbCrPositioning"] = YCBCR_POSITIONING_MAP.get(value, f"Unknown ({value})")
                continue


            elif tag == "ColorSpace":
                COLORSPACE_MAP = {
                    1: "sRGB",
                    65535: "Uncalibrated"
                }
                jpeg_meta["ColorSpace"] = COLORSPACE_MAP.get(value, f"Reserved ({value})")
                continue

            elif tag == "ExifImageWidth":
                structured["bayer_width"] = int(value)
                continue
            elif tag == "ExifImageHeight":
                structured["bayer_height"] = int(value)
                continue
            elif tag == "ExposureTime":
                structured["exposure_time"] = float(value)
                continue
            elif tag == "ShutterSpeedValue":
                structured["shutter_speed"] = float(value)
                continue

            elif tag in ["ImageLength", "ImageWidth", "MeteringMode", "ExposureMode", "ExposureProgram", "Flash"]:
                continue

            else:
                if isinstance(value, (int, float, str)) and len(str(value)) < 100:
                    structured[tag] = value

        # Derive real image dimensions from Bayer size
        if "bayer_width" in structured and "bayer_height" in structured:
            structured["image_width"] = structured["bayer_width"] // 2
            structured["image_height"] = structured["bayer_height"] // 2

        structured["GPS"] = gps_meta
        structured["JPEG"] = jpeg_meta
        return structured

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
    
    def __getitem__(self, key) -> 'GONetFile':
        """
        Slice the GONetFile spatially.

        This allows spatial slicing of the pixel data (red, green, blue channels) using
        standard NumPy-style indexing. The result is a new :class:`GONetFile` instance.

        Parameters
        ----------
        key : slice, int, or tuple
            Slice or index to apply, e.g., [:, 10:20].

        Returns
        -------
        :class:`GONetFile`
            A new instance with sliced red, green, and blue arrays.

        Raises
        ------
        TypeError
            If the key is invalid or cannot be applied.
        """
        return self._operate(key, lambda arr, k=key: arr[k])
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
