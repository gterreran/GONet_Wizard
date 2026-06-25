# GONet_Wizard/GONet_utils/src/gonet/gonet_file_raw.py

"""
Specialized handling of RAW GONet `.jpg` images containing BGGR Bayer data.

This module defines the :class:`GONetFileRaw` class, a subclass of
:class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile` designed for
working with unprocessed RAW GONet camera files. Unlike the base class, which
stores a single averaged green channel, this subclass preserves both green
channels present in the BGGR Bayer mosaic (`green1` and `green2`).

The :class:`GONetFileRaw` class provides tools for reading RAW `.jpg` files,
handling per-channel arithmetic operations, converting between compact
(H, W) quads and full (2H, 2W) Bayer-plane representations, and maintaining
consistent metadata and file typing with the base :class:`GONetFile`.

**Classes**

- :class:`GONetFileRaw`: A class representing a RAW GONet file with separate green channels.

"""

from __future__ import annotations
from typing import Optional, Union
from pathlib import Path
import warnings
import numpy as np
from PIL import Image
from GONet_Wizard.GONet_utils.src.gonet.filetypes import FileType
from GONet_Wizard.GONet_utils import GONetFile
from GONet_Wizard.GONet_utils.src.gonet import parsers
from GONet_Wizard.GONet_utils.src.gonet import config


class GONetFileRaw(GONetFile):
    """
    In-memory representation of RAW GONet data with separate Bayer channels.

    RAW GONet images use a BGGR mosaic with two distinct green samples.  This
    subclass preserves those samples as ``green1`` and ``green2`` instead of
    immediately averaging them into the processed ``green`` channel used by
    :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile`.

    Instances may be stored in either compact quad representation ``(H, W)`` or
    expanded Bayer-plane representation ``(2H, 2W)``.  The
    :attr:`is_bayer_planes` flag records which representation is currently in
    use, and conversion helpers move between the two forms.

    Attributes
    ----------
    CHANNELS : :class:`list` of :class:`str`
        Raw channel names: ``["blue", "green1", "green2", "red"]``.
    COLORS : :class:`dict`
        Default plotting colors keyed by raw channel name.
    """

    CHANNELS = config.CHANNEL_NAMES_RAW
    COLORS = {'blue': 'b', 'green1':'forestgreen', 'green2':'lime', 'red': 'r'}

    def __init__(
        self,
        filename: str,
        blue: np.ndarray,
        green1: np.ndarray,
        green2: np.ndarray,
        red: np.ndarray,
        meta: Optional[dict],
        filetype: FileType,
        is_bayer_planes: bool = False,
    ) -> None:
        """
        Initialize a :class:`GONetFileRaw` instance.

        This constructor expands upon the base :class:`GONetFile` by accepting
        two additional green channel arrays, `green1` and `green2`.

        Parameters
        ----------
        filename : :class:`str`
            Name of the file (without path) (inherited from :class:`GONetFile`).
        blue : :class:`numpy.ndarray`
            2D array representing the blue channel (inherited from :class:`GONetFile`).
        green1 : :class:`numpy.ndarray`
            2D array representing the first green channel.
        green2 : :class:`numpy.ndarray`
            2D array representing the second green channel.
        red : :class:`numpy.ndarray`
            2D array representing the red channel (inherited from :class:`GONetFile`).
        meta : :class:`dict`, optional
            Metadata dictionary (default is None) (inherited from :class:`GONetFile`).
        filetype : :class:`FileType`
            Type of the file, chosen from the :class:`FileType` enumeration (inherited from :class:`GONetFile`).
        is_bayer_planes : :class:`bool`, optional
            Indicates if the provided channels are raw Bayer planes (default is False).
        """
        # --- Runtime type checking ---
        channel_names = list(zip(self.CHANNELS, [blue, green1, green2, red]))

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

        self._filename = filename
        self._blue = blue.astype(np.float64)
        self._green1 = green1.astype(np.float64)
        self._green2 = green2.astype(np.float64)
        self._red = red.astype(np.float64)
        self._meta = meta
        self._filetype = filetype
        self._is_bayer_planes = bool(is_bayer_planes)

    # --- Properties ---
    @property
    def green1(self) -> np.ndarray:
        """
        Get the first green channel.

        Returns
        -------
        :class:`numpy.ndarray`
            2D array representing the first green channel.
        """
        return self._green1

    @property
    def green2(self) -> np.ndarray:
        """
        Get the second green channel.

        Returns
        -------
        :class:`numpy.ndarray`
            2D array representing the second green channel.
        """
        return self._green2

    @property
    def green(self) -> np.ndarray:
        """
        Override the green property to prevent access.
        Accessing a single combined green channel is invalid for GONetFileRaw.

        Raises
        ------
        :class:`AttributeError`
            Always raised, because GONetFileRaw maintains separate green1 and green2
            channels and does not define a combined green channel.
        """
        raise AttributeError(
            "GONetFileRaw does not have a single combined 'green' channel. "
            "Use 'green1' or 'green2' instead."
        )

    @property
    def is_bayer_planes(self) -> bool:
        """
        True if channel arrays are expanded to (2H, 2W) Bayer-plane coordinates.
        
        Returns
        -------
        :class:`bool`
            Indicates if the channel arrays represent Bayer planes.
        """
        return self._is_bayer_planes
    
    # --- Operator propagation ---
    def _operate(self, other, op) -> 'GONetFileRaw':
        """
        Propagate operations to the underlying data arrays.

        Rules:

        - RAW ⨉ RAW:

            * If both in Bayer-planes -> operate in Bayer-planes, return Bayer-planes.
            * If mixed representations -> compact the Bayer one, warn, return compact quads.

        - RAW ⨉ scalar/array -> keep current representation.
        - RAW ⨉ base -> convert RAW->base (avg greens; compact first if needed), warn, return GONetFile.

        Parameters
        ----------
        other : Union[:class:`GONetFileRaw`, :class:`float`, :class:`int`]
            The other operand to operate with.
        op : Callable
            The operation to perform (e.g., np.add, np.subtract).

        Returns
        -------
        :class:`GONetFileRaw`
            A new GONetFileRaw instance with the result of the operation.
        """
        def ensure_compact(obj):
            if isinstance(obj, GONetFileRaw) and obj.is_bayer_planes:
                warnings.warn(
                    "Auto-converting from Bayer-plane (2H,2W) to compact (H,W) quads "
                    "to perform operation; result will be in compact quads.",
                    RuntimeWarning,
                )
                return obj.as_compact_quads()
            return obj

        # Case A: RAW ⨉ RAW
        if isinstance(other, GONetFileRaw):
            # Both Bayer-planes -> keep Bayer-planes
            if self.is_bayer_planes and other.is_bayer_planes:
                return GONetFileRaw(
                    filename=None,
                    blue=op(self.blue, other.blue),
                    green1=op(self.green1, other.green1),
                    green2=op(self.green2, other.green2),
                    red=op(self.red, other.red),
                    meta=None,
                    filetype=None,
                    is_bayer_planes=True,   # keep planes
                )

            # If representations differ, compact the Bayer one and return compact
            a = self if not self.is_bayer_planes else ensure_compact(self)
            b = other if not other.is_bayer_planes else ensure_compact(other)

            return GONetFileRaw(
                filename=None,
                blue=op(a.blue, b.blue),
                green1=op(a.green1, b.green1),
                green2=op(a.green2, b.green2),
                red=op(a.red, b.red),
                meta=None,
                filetype=None,
                is_bayer_planes=False,     # result is compact
            )

        # Case B: RAW ⨉ base
        if isinstance(other, GONetFile):
            a = self if not self.is_bayer_planes else ensure_compact(self)

            warnings.warn(
                "Operating GONetFileRaw with GONetFile: averaging green1/green2 into a single "
                "'green' and returning a GONetFile result.",
                RuntimeWarning,
            )
            a_green = 0.5 * (a.green1 + a.green2)

            return GONetFile(
                filename=None,
                blue=op(a.blue, other.blue),
                green=op(a_green, other.green),
                red=op(a.red, other.red),
                meta=None,
                filetype=None,
            )

        # Case C: RAW ⨉ scalar/array -> preserve current representation
        if self.is_bayer_planes:
            return GONetFileRaw(
                filename=self.filename,
                blue=op(self.blue, other),
                green1=op(self.green1, other),
                green2=op(self.green2, other),
                red=op(self.red, other),
                meta=self.meta,
                filetype=self.filetype,
                is_bayer_planes=True,
            )
        else:
            return GONetFileRaw(
                filename=self.filename,
                blue=op(self.blue, other),
                green1=op(self.green1, other),
                green2=op(self.green2, other),
                red=op(self.red, other),
                meta=self.meta,
                filetype=self.filetype,
                is_bayer_planes=False,
            )

    # --- File loader for RAW .jpgs ---
    @classmethod
    def from_file(
        cls,
        filepath: Union[str, Path],
        filetype: FileType = FileType.SCIENCE,
        meta: bool = True,
    ) -> 'GONetFileRaw':
        """
        Load a GONetFileRaw instance from a RAW .jpg file.

        Parameters
        ----------
        filepath : Union[:class:`str`, :class:`Path`]
            The path to the .jpg file.
        filetype : :class:`FileType`, optional
            The type of the file (default is FileType.SCIENCE).
        meta : :class:`bool`, optional
            Whether to parse metadata from the file (default is True).

        Returns
        -------
        :class:`GONetFileRaw`
            The loaded GONetFileRaw instance.
        """
        filepath = Path(filepath)
        if not filepath.is_file():
            raise FileNotFoundError(f"Could not find file {filepath}.")
        if filepath.suffix.lower() != '.jpg':
            raise ValueError("GONetFileRaw only supports RAW '.jpg' files.")

        blue, green1, green2, red = parsers.parse_raw_file(str(filepath))

        parsed_meta = None
        if meta:
            jpeg = Image.open(filepath)
            raw_exif = jpeg._getexif()
            parsed_meta = parsers.parse_exif_metadata(raw_exif)

        return cls(
            filename=str(filepath.name),
            blue=blue,
            green1=green1,
            green2=green2,
            red=red,
            meta=parsed_meta,
            filetype=filetype,
            is_bayer_planes=False,
        )
        

    def to_bayer_planes(
        self,
        fill_value: float | int = np.nan,
    ) -> dict[str, np.ndarray]:
        """
        Expand per-channel images to Bayer-sized planes with values only at the
        pixel locations of each channel in the CFA pattern; other pixels are filled.

        Parameters
        ----------
        fill_value : :class:`float` or :class:`int`, optional
            Value to place where a given channel does not live (default: NaN).

        Returns
        -------
        :class:`dict` of :class:`numpy.ndarray`
            Dictionary with keys 'red', 'green1', 'green2', 'blue', each of shape (2H, 2W).

        Raises
        ------
        ValueError
            If the CFA pattern is unsupported or channel shapes are inconsistent.
        """
        h, w = self.red.shape
        H, W = 2 * h, 2 * w
        out_dtype = self.red.dtype

        # Initialize filled planes
        out_array = {ch: np.full((H, W), fill_value, dtype=out_dtype) for ch in self.CHANNELS}

        for ch in self.CHANNELS:
            row_offset, col_offset = config.get_channel_bayer_offsets(ch)
            out_array[ch][row_offset::2, col_offset::2] = self.get_channel(ch)

        return out_array
    
    def as_bayer_planes(self, inplace: bool = True, fill_value: float | int = np.nan) -> 'GONetFileRaw':
        """
        Return a new GONetFileRaw whose channels are Bayer-sized (2H, 2W) planes.

        Parameters
        ----------
        inplace : :class:`bool`, optional
            If True, modifies the current instance in-place.
            If False, returns a new instance with Bayer-plane channels.
        fill_value : :class:`float` or :class:`int`, optional
            Value to place where a given channel does not live (default: NaN).
        
        Returns
        -------
        :class:`GONetFileRaw`
            A new instance with channels expanded to Bayer-plane coordinates.
        """
        if self.is_bayer_planes:
            warnings.warn("Instance is already in Bayer-plane coordinates.", RuntimeWarning)
            return self  # No change needed.
        
        planes = self.to_bayer_planes(fill_value=fill_value)
        if inplace:
            for channel in self.CHANNELS:
                self.set_channel(channel, planes[channel], check_shape=False)

            self._is_bayer_planes = True
            return self
        
        return GONetFileRaw(
            filename=self.filename,
            blue=planes["blue"],
            green1=planes["green1"],
            green2=planes["green2"],
            red=planes["red"],
            meta=self.meta,
            filetype=self.filetype,
            is_bayer_planes=True,
        )
    
    def as_compact_quads(self) -> 'GONetFileRaw':
        """
        Return a new GONetFileRaw whose channels are compact (H, W) quads,
        by sampling each channel at its CFA parity from Bayer planes.

        Returns
        -------
        :class:`GONetFileRaw`
            A new instance with channels in compact (H, W) per-channel form.
        """
        if not self.is_bayer_planes:
            warnings.warn("Instance is already in compact (H, W) per-channel form.", RuntimeWarning)
            return self  # No change needed.

        # Inverse of BGGR placement:
        out_arrays = {}
        for channel in self.CHANNELS:
            row_offset, col_offset = config.get_channel_bayer_offsets(channel)
            out_arrays[channel] = self.get_channel(channel)[row_offset::2, col_offset::2]
        
        return GONetFileRaw(
            filename=self.filename,
            red=out_arrays["red"],
            green1=out_arrays["green1"],
            green2=out_arrays["green2"],
            blue=out_arrays["blue"],
            meta=self.meta,
            filetype=self.filetype,
            is_bayer_planes=False,
        )