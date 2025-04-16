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
    Casts various types to JSON serializable types.

    This is necessary in order to get rid of weird TIFF formats
    which are not JSON serializable.

    Parameters
    ----------
    v : various types
        The value to be cast.

    Returns
    -------
    various types
        The cast value.
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
    """Enumeration for GONet file types."""
    
    SCIENCE = auto()  # Represents science data
    FLAT = auto()     # Represents flat field data
    BIAS = auto()     # Represents bias data
    DARK = auto()     # Represents dark frame data

class GONetFile:
    """
    A class to represent a GONet file.

    This class encapsulates the properties and methods for manipulating
    GONet files, including the ability to load image data, handle metadata,
    and process pixel data for different file types.

    Attributes
    ----------
    RAW_FILE_OFFSET : int
        The offset for the raw file. Defaults to `18711040`.
    RAW_HEADER_SIZE : int
        The size of the raw header. Defaults to `32768`.
    RAW_DATA_OFFSET : int
        The offset for the raw data. Defaults to `RAW_FILE_OFFSET - RAW_HEADER_SIZE`.
    RELATIVETOEND : int
        Relative to end constant. Defaults to `2`.
    PIXEL_PER_LINE : int
        Number of pixels per line. Defaults to `4056`.
    PIXEL_PER_COLUMN : int
        Number of pixels per column. Defaults to `3040`.
    USED_LINE_BYTES : int
        Number of bytes used per line. Defaults to `int(PIXEL_PER_LINE * 12 / 8)`.
    CHANNELS: list
        List of string description of the RGB channels. Defaults to `['red', 'green', 'blue']`.
    """

    RAW_FILE_OFFSET = 18711040
    RAW_HEADER_SIZE = 32768
    RAW_DATA_OFFSET = RAW_FILE_OFFSET - RAW_HEADER_SIZE
    RELATIVETOEND = 2

    PIXEL_PER_LINE = 4056
    PIXEL_PER_COLUMN = 3040
    USED_LINE_BYTES = int(PIXEL_PER_LINE * 12 / 8)

    CHANNELS = ['red', 'green', 'blue']

    def __init__(self, filename: str, red: np.ndarray, green: np.ndarray, blue: np.ndarray, meta: dict, filetype: FileType) -> None:
        """
        Initializes a GONetFile instance.

        Parameters
        ----------
        filename : str
            The name of the file.
        red : numpy.ndarray
            The red channel pixel data.
        green : numpy.ndarray
            The green channel pixel data.
        blue : numpy.ndarray
            The blue channel pixel data.
        meta : dict
            A dictionary containing metadata.
        filetype : FileType
            The type of the file (e.g., SCIENCE, FLAT, etc.). Defaults to `FileType.SCIENCE`.
        """
        self._filename = filename
        self._red = red
        self._green = green
        self._blue = blue
        self._meta = meta
        self._filetype = filetype

    @property
    def filename(self) -> str:
        """
        Gets the filename of the GONet file.

        Returns
        -------
        str
            The filename.
        """
        return self._filename

    @property
    def red(self) -> np.ndarray:
        """
        Gets the red channel data.

        Returns
        -------
        numpy.ndarray
            The red channel data.
        """
        return self._red

    @property
    def green(self) -> np.ndarray:
        """
        Gets the green channel data.

        Returns
        -------
        numpy.ndarray
            The green channel data.
        """
        return self._green

    @property
    def blue(self) -> np.ndarray:
        """
        Gets the blue channel data.

        Returns
        -------
        numpy.ndarray
            The blue channel data.
        """
        return self._blue

    @property
    def meta(self) -> dict:
        """
        Gets the metadata associated with the GONet file.

        Returns
        -------
        dict
            The metadata.
        """
        return self._meta
    
    @property
    def filetype(self) -> FileType:
        """
        Gets the type of the GONet file.

        Returns
        -------
        FileType
            The file type.
        """
        return self._filetype

    def channel(self, channel_name: str) -> np.ndarray:
        """
        Retrieves the pixel data for a specified color channel.

        This function returns the pixel data for the given color channel 
        (e.g., 'red', 'green', 'blue') as a numpy array.

        Parameters
        ----------
        channel_name : str
            The name of the channel to retrieve ('red', 'green', 'blue').

        Returns
        -------
        numpy.ndarray
            The pixel data for the specified channel as a numpy array.

        Raises
        ------
        ValueError
            If an invalid channel name is provided.
        """
        if channel_name not in self.CHANNELS:
            raise ValueError(f"Invalid channel name: {channel_name}. Allowed channels: {self.CHANNELS}")
        return getattr(self, channel_name)
    
    def write_to_jpeg(self, output_filename: str) -> None:
        """
        Writes the image data from the GONetFile instance to a JPEG file.

        This function combines the red, green, and blue channel data into a 
        single image and saves it as a JPEG file to the specified output 
        location using the :mod:`PIL.Image` library.

        Parameters
        ----------
        output_filename : str
            The path and filename where the JPEG file will be saved.

        Returns
        -------
        None
            This function does not return a value.

        Notes
        -----
        - The function uses the :mod:`PIL.Image` library to handle the file saving.
        - If an invalid file path or unsupported format is provided, 
          :mod:`PIL.Image` will raise an appropriate exception.
        
        """
        jpeg = Image.open(self.filename)
        jpeg.convert("RGB")
        jpeg.save(output_filename, 'JPEG', exif=jpeg.getexif())

    def write_to_tiff(self, output_filename: str) -> None:
        """
        Writes the image data from the GONetFile instance to a TIFF file.

        This function combines the red, green, and blue channel data into a 
        single image and saves it as a TIFF file to the specified output 
        location using the :mod:`PIL.Image` library or `tifffile`.

        Parameters
        ----------
        output_filename : str
            The path and filename where the TIFF file will be saved.

        Returns
        -------
        None
            This function does not return a value.

        Notes
        -----
        - The function uses the :mod:`PIL.Image` or `tifffile` library to handle the file saving.
        - If the output file extension is not `.tiff` or `.tif`, the behavior is dependent on the implementation.
        - Unsupported formats or invalid file paths will raise an appropriate exception from :mod:`PIL.Image` or `tifffile`.

        """
        tifffile.imwrite(output_filename, [self.red, self.green, self.blue], photometric='rgb', metadata=self.meta)

    def write_to_fits(self, output_filename: str) -> None:
        """
        Writes the image data from the GONetFile instance to a multi-extension FITS file.

        This function combines the red, green, and blue channel data into separate extensions
        within a single FITS file, using metadata from the 'meta' attribute to create the headers.

        Parameters
        ----------
        output_filename : str
            The path and filename where the FITS file will be saved.

        Returns
        -------
        None
            This function does not return a value.

        Notes
        -----
        - The function uses the :mod:`astropy.io.fits` library to handle the file saving.
        - FITS header labels are constrained to 8 characters, uppercase letters, and must follow FITS standards.

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
        Creates a GONetFile instance from a file.

        This class method reads the specified file (either TIFF or JPEG format), 
        extracts the image data (red, green, blue channels), and metadata. It then 
        creates and returns an instance of the GONetFile class with the parsed data.

        Parameters
        ----------
        filepath : str
            The path to the file that will be used to initialize the GONetFile instance. 
            The file should be in either TIFF or JPEG format.
        
        filetype : FileType, optional
            The type of the file, which can be one of the `FileType` enum values 
            (e.g., SCIENCE, FLAT, BIAS, or DARK). Defaults to FileType.SCIENCE.
        
        meta : bool, optional
            Whether to parse metadata from the file. Defaults to True. 
            If set to False, metadata will not be included in the resulting GONetFile instance.

        Returns
        -------
        GONetFile
            A new instance of the GONetFile class, initialized with the data and 
            metadata extracted from the specified file.

        Raises
        ------
        FileNotFoundError
            If the specified file does not exist or cannot be found.
        
        ValueError
            If the file extension is not `.tiff`, `.TIFF`, `.tif`, `.TIF`, or `.jpg`.
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
        Parses a TIFF file and extracts image data and metadata.

        This method reads the TIFF file specified by `filepath` and extracts the 
        red, green, and blue channel data, as well as metadata if `meta` is True.

        Parameters
        ----------
        filepath : str
            The path to the TIFF file.
        meta : bool, optional
            Whether to extract metadata from the file. Defaults to `True`.

        Returns
        -------
        tuple
            A tuple containing the parsed image data (red, green, blue channels)
            and metadata (if `meta` is True).
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
        Parses a raw GONet file and extracts image data and metadata.

        This method reads the raw file specified by `filepath` and extracts the 
        red, green, and blue channel data, as well as metadata if `meta` is True.
        Note that the raw files usually have `.jpg` extensions, but they are not
        standard JPEG images.

        Parameters
        ----------
        filepath : str
            The path to the raw file.
        meta : bool, optional
            Whether to extract metadata from the file. Defaults to `True`.

        Returns
        -------
        tuple
            A tuple containing the parsed image data (red, green, blue channels)
            and metadata (if `meta` is True).
        """

        with open(filepath, "rb") as file:
            file.seek(-GONetFile.RAW_DATA_OFFSET,GONetFile.RELATIVETOEND)
            s=np.zeros((GONetFile.PIXEL_PER_LINE,GONetFile.PIXEL_PER_COLUMN),dtype='uint16')   
            # do this at least 3040 times though the precise number of lines is a bit unclear
            for i in range(GONetFile.PIXEL_PER_COLUMN):

                # read in 6112 bytes, but only 6084 will be used
                bdLine = file.read(6112)
                gg=np.array(list(bdLine[0:GONetFile.USED_LINE_BYTES]),dtype='uint16')
                s[0::2,i] = (gg[0::3]<<4) + (gg[2::3]&15)
                s[1::2,i] = (gg[1::3]<<4) + (gg[2::3]>>4)

        # form superpixel array
        sp=np.zeros((int(GONetFile.PIXEL_PER_LINE/2),int(GONetFile.PIXEL_PER_COLUMN/2),3),dtype='uint16')
        sp[:,:,0]=s[1::2,1::2]                      # red
        sp[:,:,1]=(s[0::2,1::2]+s[1::2,0::2])/2     # green
        sp[:,:,2]=s[0::2,0::2]                      # blue
        sp = np.multiply(sp,16) ## adjusting the image to be saturated correctly(it was imported from 12bit into a 16bit) so it is a factor of 16 dimmer than should be, i.e this conversion

        sp=sp.transpose()

        # now we need to write it to a tiff file
        array = ((sp+0.5).astype('uint16'))

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
        Performs an operation between the current GONetFile instance and another object.

        This method facilitates operations between two GONetFile instances or 
        between a GONetFile instance and a scalar value. If the operation is between
        two GONetFile instances, the operation is applied to each color channel (red, 
        green, blue) independently. If the operation is between a GONetFile instance 
        and a scalar, the operation is applied element-wise to the pixel data using 
        numpy's operators.

        Parameters
        ----------
        other : GONetFile or scalar
            The other object to perform the operation with. It can either be another 
            GONetFile instance or a scalar value (e.g., an integer or float).
        op : function
            The operation to perform. This is expected to be a function 
            (e.g., `numpy.add`, `numpy.subtract`, etc.) that takes two 
            arguments and returns the result of the operation.

        Returns
        -------
        GONetFile
            A new GONetFile instance with the result of the operation. 
            If the operation is between two GONetFile instances, the new 
            GONetFile will have no metadata and file type.

        Notes
        -----
        - If the operation is between two GONetFile instances, the metadata and 
          file type of the resulting GONetFile will be set to `None`.
        - If the operation is between a GONetFile instance and a scalar, the metadata 
          and file type from the original instance are preserved.
        - If the operation between the channels and the other object is not supported 
          by numpy (e.g., incompatible shapes or types), a numpy error will be raised.
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
        Overloads the `+` operator to add two GONetFile instances.

        This method adds the red, green, and blue channels of two GONetFile 
        instances together independently. If the operation is between a GONetFile 
        instance and a scalar, the operation is applied element-wise to the pixel 
        data using numpy's addition.

        Parameters
        ----------
        other : Any
            Another GONetFile instance or a scalar value (int, float) to add to 
            the current GONetFile instance.

        Returns
        -------
        GONetFile
            A new GONetFile instance with the result of the addition.

        Notes
        -----
        - The resulting GONetFile instance will not have metadata or file type 
          if the operation is between two GONetFile instances.
        - Any errors during the operation are raised by numpy.
        """
        return self._operate(other, operator.add)

    __radd__ = __add__

    # In-place addition (+=)
    def __iadd__(self, other: Any) -> 'GONetFile':
        """
        Overloads the `+=` operator to perform in-place addition on a GONetFile instance.

        This method adds the red, green, and blue channels of another GONetFile 
        instance or a scalar value to the current GONetFile instance in-place.

        Parameters
        ----------
        other : Any
            Another GONetFile instance or a scalar value (int, float) to add 
            to the current GONetFile instance.

        Returns
        -------
        GONetFile
            The updated GONetFile instance with the result of the in-place addition.

        Notes
        -----
        - This operation modifies the current instance and returns the updated 
          GONetFile.
        - Any errors during the operation are raised by numpy.
        """
        return self._operate(other, operator.iadd)

    # Multiplication
    def __mul__(self, other: Any) -> 'GONetFile':
        """
        Overloads the `*` operator to multiply the current GONetFile instance 
        with another GONetFile instance or a scalar.

        This method multiplies the red, green, and blue channels of two GONetFile 
        instances or applies element-wise multiplication between a GONetFile instance 
        and a scalar using numpy's multiplication.

        Parameters
        ----------
        other : Any
            Another GONetFile instance or a scalar value (int, float) to multiply 
            with the current GONetFile instance.

        Returns
        -------
        GONetFile
            A new GONetFile instance with the result of the multiplication.

        Notes
        -----
        - If the operation is between two GONetFile instances, the resulting 
          GONetFile instance will not have metadata or file type.
        - Any errors during the operation are raised by numpy.
        """
        return self._operate(other, operator.mul)

    __rmul__ = __mul__

    # Subtraction
    def __sub__(self, other: Any) -> 'GONetFile':
        """
        Overloads the `-` operator to subtract another GONetFile instance 
        or a scalar from the current GONetFile instance.

        This method subtracts the red, green, and blue channels of two GONetFile 
        instances or applies element-wise subtraction between a GONetFile instance 
        and a scalar using numpy's subtraction.

        Parameters
        ----------
        other : Any
            Another GONetFile instance or a scalar value (int, float) to subtract 
            from the current GONetFile instance.

        Returns
        -------
        GONetFile
            A new GONetFile instance with the result of the subtraction.

        Notes
        -----
        - If the operation is between two GONetFile instances, the resulting 
          GONetFile instance will not have metadata or file type.
        - Any errors during the operation are raised by numpy.
        """
        return self._operate(other, operator.sub)

    # Division
    def __truediv__(self, other: Any) -> 'GONetFile':
        """
        Overloads the `/` operator to divide the current GONetFile instance 
        by another GONetFile instance or a scalar.

        This method divides the red, green, and blue channels of two GONetFile 
        instances or applies element-wise division between a GONetFile instance 
        and a scalar using numpy's true division.

        Parameters
        ----------
        other : Any
            Another GONetFile instance or a scalar value (int, float) to divide 
            the current GONetFile instance.

        Returns
        -------
        GONetFile
            A new GONetFile instance with the result of the division.

        Notes
        -----
        - If the operation is between two GONetFile instances, the resulting 
          GONetFile instance will not have metadata or file type.
        - Any errors during the operation are raised by numpy.
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
