# GONet_Wizard/GONet_utils/src/gonet/gonet_file.py

"""
This module defines the :class:`GONetFile` class, which provides functionality for 
handling and processing GONet files. The class encapsulates the properties 
and methods required for manipulating the image data (including blue, green, 
and red channels) and metadata associated with GONet files.

The module supports various operations on GONet files, including:

- Loading image data from original raw (`.jpg`) or TIFF formats.
- Performing arithmetic operations between GONet files and scalar values.
- Writing image data to common formats like JPEG, TIFF, and FITS.
- Parsing and handling metadata for different file types.

The :class:`GONetFile` class also includes support for operator overloading, allowing 
users to easily perform element-wise operations between GONet files or between 
a GONet file and scalar values.

In order to ensure that all arithmetic operations on the image channels are safe and
reliable, we cast the blue, green, and red channel arrays to float64 upon initialization.
The original pixel data is typically stored as uint12 or uint16, which are prone to
overflow or precision loss during common operations like addition, subtraction, or
division. By promoting the arrays to float64, we avoid these issues and enable robust
numerical processing — particularly important for calibration, normalization, or stacked
image analysis. This casting ensures consistency and protects users from subtle bugs that
can arise from working with fixed-width integer types.

From the :class:`GONetFile`, :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw` class is derived, which keeps the
2 green channels separate and has basic functionality to work in the raw Bayer-plane format.

**Classes**

- :class:`GONetFile`: A class representing a GONet file.


Example usage
--------------
.. code-block:: python

   gonet_file = GONetFile.from_file('example_image.tiff')
   plt.imshow(gonet_file.green)

"""

import operator
from PIL import Image
import numpy as np
from typing import Any, Optional, Union
from pathlib import Path
import warnings
from GONet_Wizard.GONet_utils.src.gonet.filetypes import FileType
from GONet_Wizard.GONet_utils.src.gonet import parsers
from GONet_Wizard.GONet_utils.src.gonet import analysis_utils
from GONet_Wizard.GONet_utils.src.gonet import writers
from GONet_Wizard.GONet_utils.src.gonet import config

class GONetFile:
    """
    In-memory representation of a processed three-channel GONet image.

    A :class:`GONetFile` stores blue, green, and red image channels together
    with parsed metadata and a :class:`~GONet_Wizard.GONet_utils.src.gonet.filetypes.FileType`.
    The constructor accepts already-loaded arrays; most users should create
    instances with :meth:`from_file`, which dispatches to the appropriate parser
    for supported GONet file formats.

    Channel arrays are converted to ``float64`` during initialization so that
    arithmetic, dark/overscan correction, normalization, and stacking operations
    do not silently overflow fixed-width integer image data.

    Attributes
    ----------
    CHANNELS : :class:`list` of :class:`str`
        Canonical processed-channel names: ``["blue", "green", "red"]``.
    COLORS : :class:`dict`
        Default plotting colors keyed by channel name.

    Notes
    -----
    Arithmetic operators act channel-by-channel and return new image objects.
    Operations between two :class:`GONetFile` instances require matching channel
    shapes.
    """

    CHANNELS = config.CHANNEL_NAMES_PROCESSED
    COLORS = {'blue': 'b', 'green': 'g', 'red': 'r'}

    def __init__(
        self,
        filename: str,
        blue: np.ndarray,
        green: np.ndarray,
        red: np.ndarray,
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
        blue : :class:`numpy.ndarray`
            Pixel data for the blue channel. Will be cast to float64.
        green : :class:`numpy.ndarray`
            Pixel data for the green channel. Will be cast to float64.
        red : :class:`numpy.ndarray`
            Pixel data for the red channel. Will be cast to float64.
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
        channel_names = list(zip(self.CHANNELS, [blue, green, red]))

        if filename is not None and not isinstance(filename, str):
            raise TypeError("filename must be a string or None")

        for name, arr in channel_names:
            if not isinstance(arr, np.ndarray):
                raise TypeError(f"{name} must be a numpy.ndarray")
            if arr.ndim != 2:
                raise ValueError(f"{name} must be a 2D array")

        # All planes must share the same shape
        ref_shape = red.shape
        for name, arr in channel_names:
            if arr.shape != ref_shape:
                raise ValueError(f"{name} shape {arr.shape} must match red shape {ref_shape}")

        if meta is not None and not isinstance(meta, dict):
            raise TypeError("meta must be a dict or None")

        if filetype is not None and not isinstance(filetype, FileType):
            raise TypeError("filetype must be an instance of FileType or None")

        # --- Safe assignment ---
        self._filename = filename
        self._blue = blue.astype(np.float64)
        self._green = green.astype(np.float64)
        self._red = red.astype(np.float64)
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

    def get_channel(self, channel_name: config.ChannelName) -> np.ndarray:
        """
        Retrieve the pixel data for a specified color channel.

        This method returns the image data associated with the specified
        color channel as a :class:`numpy.ndarray`.

        Parameters
        ----------
        channel_name : :class:`~config.ChannelName`
            The name of the channel to retrieve. Must be one of
            ``'blue'``, ``'green'``, or ``'red'``.

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

    def set_channel(self, channel_name: config.ChannelName, data: np.ndarray, check_shape: bool = True) -> None:
        """
        Set the pixel data for a specified color channel.

        This method updates the image data associated with the specified
        color channel.

        Parameters
        ----------
        channel_name : :class:`~config.ChannelName`
            The name of the channel to update. Must be one of
            ``'blue'``, ``'green'``, or ``'red'``.

        data : :class:`numpy.ndarray`
            A 2D array of pixel values to assign to the specified channel.
            The shape of the array must match the current channel dimensions.
        
        check_shape : :class:`bool`, optional
            If True (default), the method checks that the shape of `data` matches
            the existing channel shape before assignment. If False, no shape check
            is performed.

        Raises
        ------
        :class:`ValueError`
            If an invalid channel name is provided or if the shape of the
            input data does not match the current channel dimensions.
        """
        if channel_name not in self.CHANNELS:
            raise ValueError(f"Invalid channel name: {channel_name}. Allowed channels: {self.CHANNELS}")
        
        current_channel = getattr(self, channel_name)
        if check_shape and data.shape != current_channel.shape:
            raise ValueError(f"Shape mismatch: Expected shape {current_channel.shape}, but got {data.shape}.")
        
        setattr(self, f"_{channel_name}", data)


    def remove_overscan(self, *args, **kwargs):
        """
        Remove overscan regions from the image data.

        See :func:`~GONet_Wizard.GONet_utils.src.gonet.analysis_utils.dark_correction.remove_overscan`
        for full documentation.
        """
        return analysis_utils.remove_overscan(self, *args, **kwargs)


    def write_to_jpeg(self, *args, **kwargs):
        """
        Write the RGB image data to a JPEG file.

        See :func:`~GONet_Wizard.GONet_utils.src.gonet.writers.jpeg.write_to_jpeg`
        for full documentation.
        """
        writers.write_to_jpeg(self, *args, **kwargs)


    def write_to_tiff(self, *args, **kwargs):
        """
        Write the image data to a multi-page TIFF file.

        See :func:`~GONet_Wizard.GONet_utils.src.gonet.writers.tiff.write_to_tiff`
        for full documentation.
        """
        writers.write_to_tiff(self, *args, **kwargs)


    def write_to_fits(self, *args, **kwargs):
        """
        Write the image data to a FITS file.

        See :func:`~GONet_Wizard.GONet_utils.src.gonet.writers.fits.write_to_fits`
        for full documentation.
        """
        writers.write_to_fits(self, *args, **kwargs)

    @classmethod
    def from_file(cls, filepath: Union[str, Path], filetype: FileType = FileType.SCIENCE, meta: bool = True) -> 'GONetFile':
        """
        Create a :class:`.GONetFile` instance from a TIFF or JPEG file.

        This class method reads a GONet image file, extracts the blue, green, and red
        channel data, and optionally parses the associated metadata. It returns a fully
        initialized :class:`.GONetFile` object.

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
        :class:`.GONetFile`
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
            blue, green, red = parsers.parse_tiff_file(str(filepath))
            parsed_meta = None  # No metadata for TIFFs
        elif suffix == '.jpg':
            blue, green1, green2, red = parsers.parse_raw_file(str(filepath))
            green = (green1 + green2) / 2.0
            parsed_meta = None
            if meta:
                jpeg = Image.open(filepath)
                raw_exif = jpeg._getexif()
                parsed_meta = parsers.parse_exif_metadata(raw_exif)
        else:
            raise ValueError("Extension must be '.tiff', '.tif', or original '.jpg' from a GONet camera.")

        return cls(
            filename=str(filepath.name),  # Only the filename part, no directory
            blue=blue,
            green=green,
            red=red,
            meta=parsed_meta,
            filetype=filetype
        )
    

    '''
    ---------------------
    Operators overloading.
    ---------------------
    
    The GONetFile class has attributes that are numpy arrays.
    Therefore it could be useful to allow operations applied to
    the blue, green and red channels all at the same time,
    instead of executing the operation 3 times in the code.
    For instance, summing 2 GONetFile instances (go1, go2) as

    go1 + go2

    instead of having to do

    go1.blue + go2.blue
    go1.green + go2.green
    go1.red + go2.red

    So operators are overloaded to allow this.

    '''

    def _operate(self, other, op) -> 'GONetFile':
        """
        Perform an element-wise operation on the current :class:`GONetFile` instance.

        This internal method supports element-wise operations between the current 
        GONetFile instance and either another GONetFile instance or a scalar value.
        Support for operations with :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw` is also included, where the green
        channels are averaged before applying the operation.
        The operation is applied independently to each color channel 
        (blue, green, and red) using the provided binary operator.

        Parameters
        ----------
        other : :class:`GONetFile` or :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw` or scalar
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
        # To prevent circular imports we use duck typing here
        # to check if other is a GONetFileRaw
        if hasattr(other, "green1") and hasattr(other, "green2"):
            raw = other
            if getattr(raw, "is_bayer_planes", False):
                warnings.warn(
                    "Auto-converting RAW from Bayer-plane (2H,2W) to compact (H,W) "
                    "before averaging greens for operation with GONetFile.",
                    RuntimeWarning,
                )
                raw = raw.as_compact_quads()

            warnings.warn(
                "Averaging RAW green1/green2 to 'green' to operate with GONetFile; "
                "returning a GONetFile result.",
                RuntimeWarning,
            )
            g_avg = 0.5 * (raw.green1 + raw.green2)

            return GONetFile(
                filename=None,
                blue=op(self.blue,  raw.blue),
                green=op(self.green, g_avg),
                red=op(self.red,    raw.red),
                meta=None,
                filetype=None,
            )

        if isinstance(other, GONetFile):
            return GONetFile(
                filename = None, 
                blue = op(self.blue, other.blue),
                green = op(self.green, other.green),
                red = op(self.red, other.red),
                meta = None,
                filetype = None
            )
        else:
            return GONetFile(
                filename = self.filename, 
                blue = op(self.blue, other),
                green = op(self.green, other),
                red = op(self.red, other),
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
        independently on the blue, green, and red channels using :func:`numpy.add`.

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
        :class:`float`). Addition is performed independently on the blue, green, and 
        red channels using :func:`numpy.add`.

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

        This method multiplies the blue, green, and red channels of the current 
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
        instance. The operation is applied independently to the blue, green, and red 
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

        This method divides the blue, green, and red channels of the current 
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

        This allows spatial slicing of the pixel data (blue, green, red channels) using
        standard NumPy-style indexing. The result is a new :class:`GONetFile` instance.

        Parameters
        ----------
        key : slice, int, or tuple
            Slice or index to apply, e.g., [:, 10:20].

        Returns
        -------
        :class:`GONetFile`
            A new instance with sliced blue, green, and red arrays.

        Raises
        ------
        TypeError
            If the key is invalid or cannot be applied.
        """
        return self._operate(key, lambda arr, k=key: arr[k])
