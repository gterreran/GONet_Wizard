from __future__ import annotations
from tifffile import tifffile
import os, PIL
from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np
import operator, inspect

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

    def __init__(self, original_file: str, red: np.ndarray, green: np.ndarray, blue: np.ndarray, meta: dict) -> None:
        self._original_file = original_file
        self._red = red
        self._green = green
        self._blue = blue
        self._meta = meta

    def __getitem__(self, item):
         return GONetFile(self.original_file, self._red[item], self._green[item], self._blue[item], self.meta)

    # def __add__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self._red + other._red, self._green + other._green, self._blue + other._blue, None)
    #     else:
    #         return GONetFile(self.original_file, self._red + other, self._green + other, self._blue + other, self.meta)
    
    # __radd__ = __add__

    # def __mul__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self._red * other._red, self._green * other._green, self._blue * other._blue, None)
    #     else:
    #         return GONetFile(self.original_file, self._red * other, self._green * other, self._blue * other, self.meta)
    
    # __rmul__ = __mul__

    # def __sub__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self._red - other._red, self._green - other._green, self._blue - other._blue, None)
    #     else:
    #         return GONetFile(self.original_file, self._red - other, self._green - other, self._blue - other, self.meta)
    
    # def __truediv__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self._red / other._red, self._green / other._green, self._blue / other._blue, None)
    #     else:
    #         return GONetFile(self.original_file, self._red / other, self._green / other, self._blue / other, self.meta)

    # def __lt__(self, other):
    #     if isinstance(other, GONetFile):
    #         return GONetFile(None, self._red < other._red, self._green < other._green, self._blue < other._blue, None)
    #     else:
    #         return GONetFile(self.original_file, self._red < other, self._green < other, self._blue < other, self.meta)
        
    # def mean(self, *args, **kwargs):
    #     return np.array([np.mean(self.red, *args, **kwargs), np.mean(self.green, *args, **kwargs), np.mean(self.blue, *args, **kwargs)])
                

    @property
    def original_file(self) -> np.ndarray:
        return self._original_file

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
        jpeg = Image.open(self.original_file)
        jpeg.convert("RGB")
        jpeg.save(outname, 'JPEG', exif=jpeg.getexif())

    def write_to_tiff(self, outname:str) -> None:
        tifffile.imwrite(outname, [self.red, self.greem, self.blue], photometric='rgb', metadata=self.meta)

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
            original_file = filepath,
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
        This script extracts this componet from the original .jpg file.

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


def apply_binary_op(func):
    def inner(self, other):
        if isinstance(other, GONetFile):
            return GONetFile(None, func(self._red, other._red), func(self._green, other._green), func(self._blue, other._blue), None)
        else:
            return GONetFile(self.original_file, func(self._red, other), func(self._green, other), func(self._blue, other), self.original_file)
    return inner

def apply_unary_op(func):
    def inner(self):
        return GONetFile(self.original_file, func(self._red), func(self._green), func(self._blue), self.original_file)
    return inner


for op_name in operator.__all__:
    # Getting the operator method
    op = getattr(operator, op_name)
    # I need to differentiate between operators that works between 2 parameters
    # And those that modify the operator directly. So I need to inspect
    # how many parameters does that method have
    p = len(inspect.signature(op).parameters)

    # Unary operators:
    if p == 1:
        # Testing the operator on a numpy array
        try:
            op(np.array([1,2,3]))
        except:
            continue
        setattr(GONetFile, op_name, apply_unary_op(getattr(operator, op_name)))
    
    # Binary operators:
    if p == 2:
        # Testing the operator 2 numpy array
        try:
            op(np.array([1,2,3]), np.array([1,2,3]))
        except:
            continue
        setattr(GONetFile, op_name, apply_binary_op(getattr(operator, op_name)))