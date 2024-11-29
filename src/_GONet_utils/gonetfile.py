from __future__ import annotations
from tifffile import tifffile
import os, PIL, operator
from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np

def cast(v):
    '''
    This is necessary in order the get rid of weird Tiff formats
    which are not json serializable.
    
    '''
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

class GONetFile:

    RAW_FILE_OFFSET = 18711040
    RAW_HEADER_SIZE = 32768
    RAW_DATA_OFFSET = RAW_FILE_OFFSET - RAW_HEADER_SIZE
    RELATIVETOEND = 2

    PIXEL_PER_LINE=4056
    PIXEL_PER_COLUMN=3040
    USED_LINE_BYTES=int(PIXEL_PER_LINE*12/8)

    def __init__(self, filename: str, red: np.ndarray, green: np.ndarray, blue: np.ndarray, meta: dict) -> None:
        self._filename = filename
        self._red = red
        self._green = green
        self._blue = blue
        self._meta = meta

    @property
    def filename(self) -> np.ndarray:
        return self._filename

    @property
    def red(self) -> np.ndarray:
        return self._red

    @property
    def green(self) -> np.ndarray:
        return self._green

    @property
    def blue(self) -> np.ndarray:
        return self._blue

    @property
    def meta(self) -> np.ndarray:
        return self._meta

    def write_to_jpeg(self, outname:str) -> None:
        jpeg = Image.open(self.filename)
        jpeg.convert("RGB")
        jpeg.save(outname, 'JPEG', exif=jpeg.getexif())

    def write_to_tiff(self, outname:str) -> None:
        tifffile.imwrite(outname, [self.red, self.green, self.blue], photometric='rgb', metadata=self.meta)

    def write_to_fits(self, outname:str) -> None:
        raise NotImplementedError()

    @classmethod
    def from_file(cls, filepath: str) -> GONetFile:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f'Could not find file {filepath}.')
        if filepath.split('.')[-1] in ['tiff','TIFF','tif','TIF']:
            parsed_data, parsed_meta = cls._parse_tiff_file(filepath)
        elif filepath.split('.')[-1] in ['jpg']:
            parsed_data, parsed_meta = cls._parse_jpg_file(filepath)
        else:
            raise ValueError("Extension must be '.tiff', '.TIFF', '.tif', '.TIF' or the original '.jpg' from a GONet camera.")
        #computed_data = cls._precompute_stuff(parsed_data)
        return cls(
            filename = filepath,
            red = parsed_data[0],
            green = parsed_data[1],
            blue = parsed_data[2],
            meta = parsed_meta
        )

    @staticmethod
    def _parse_tiff_file(filepath: str) -> tuple[np.ndarray, dict]:
        with tifffile.TiffFile(filepath) as tif:
            return tif.asarray(), tif.shaped_metadata[0]

    @staticmethod
    def _parse_jpg_file(filepath: str) -> tuple[np.ndarray, dict]:
        '''
        An image taken by a GoNET camera has a full RAW image saved underneath.
        This script extracts this component from the original .jpg file.

        '''

        with open(filepath, "rb") as file:
            file.seek(-GONetFile.RAW_DATA_OFFSET,GONetFile.RELATIVETOEND) #### Negative value for first argument gives 'invalid argument' error, but removing the negative sign here causes downstream ValueError {"could not broadcast input array from shape (0,) into shape (2028,)"}.
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
        jpeg = Image.open(filepath)
        meta_data = jpeg._getexif()
        tiff_meta = {}
        for k,v in meta_data.items():
            v = cast(v)
            tiff_meta[TAGS[k]] = v


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

    So overload the basic operators to allow that.
    
    An operation between 2 GONetFile instances will return another
    GONetFile instance, but it loses the `filename` and the `meta`
    attributes.
    
    An operation between a GONetFile instance and a number, will
    keep the original `filename` and the `meta` attributes.

    '''

    # Addition
    def __add__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red + other.red, self.green + other.green, self.blue + other.blue, None)
        else:
            return GONetFile(self.filename, self.red + other, self.green + other, self.blue + other, self.meta)
    
    __radd__ = __add__

    # In place addition (+=)
    def __iadd__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, operator.iadd(self.red, other.red), operator.iadd(self.green, other.green), operator.iadd(self.blue, other.blue), None)
        else:
            return GONetFile(self.filename, operator.iadd(self.red, other), operator.iadd(self.green, other), operator.iadd(self.blue, other), self.meta)

    # Multiplication
    def __mul__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red * other.red, self.green * other.green, self.blue * other.blue, None)
        else:
            return GONetFile(self.filename, self.red * other, self.green * other, self.blue * other, self.meta)
    
    __rmul__ = __mul__

    # Subtraction
    def __sub__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red - other.red, self.green - other.green, self.blue - other.blue, None)
        else:
            return GONetFile(self.filename, self.red - other, self.green - other, self.blue - other, self.meta)
    
    # Division
    def __truediv__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red / other.red, self.green / other.green, self.blue / other.blue, None)
        else:
            return GONetFile(self.filename, self.red / other, self.green / other, self.blue / other, self.meta)

    # Comparison functions
    def __lt__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red < other.red, self.green < other.green, self.blue < other.blue, None)
        else:
            return GONetFile(self.filename, self.red < other, self.green < other, self.blue < other, self.meta)
        
    def __le__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red <= other.red, self.green <= other.green, self.blue <= other.blue, None)
        else:
            return GONetFile(self.filename, self.red <= other, self.green <= other, self.blue <= other, self.meta)
        
    def __eq__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red == other.red, self.green == other.green, self.blue == other.blue, None)
        else:
            return GONetFile(self.filename, self.red == other, self.green == other, self.blue == other, self.meta)
        
    def __ne__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red != other.red, self.green != other.green, self.blue != other.blue, None)
        else:
            return GONetFile(self.filename, self.red != other, self.green != other, self.blue != other, self.meta)
        
    def __ge__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red > other.red, self.green > other.green, self.blue > other.blue, None)
        else:
            return GONetFile(self.filename, self.red > other, self.green > other, self.blue > other, self.meta)
        
    def __gt__(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, self.red >= other.red, self.green >= other.green, self.blue >= other.blue, None)
        else:
            return GONetFile(self.filename, self.red >= other, self.green >= other, self.blue >= other, self.meta)
        
    # Making sure we are using numpy mean and median
    def mean(self, *args, **kwargs):
        return np.array([np.mean(self.red, *args, **kwargs), np.mean(self.green, *args, **kwargs), np.mean(self.blue, *args, **kwargs)])
    
    def median(self, *args, **kwargs):
        return np.array([np.median(self.red, *args, **kwargs), np.median(self.green, *args, **kwargs), np.median(self.blue, *args, **kwargs)])
                