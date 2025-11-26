"""
Dark signal correction utilities for GONet images.

The :mod:`gonet.dark_correction` module provides routines to mitigate fixed
electronic offsets in GONet data prior to scientific analysis and visualization.
Functions are written to work with both :class:`~GONetFile` (single green) and
:class:`~GONetFileRaw` (separate ``green1``/``green2``) via duck typing, preserving
metadata and file type, and optionally operating in-place.

**Functions**

- :func:`.remove_overscan`
    Subtract the mean of a predefined overscan stripe from one or more channels,
    in-place or returning a corrected copy.

"""
import numpy as np
from typing import Optional

def remove_overscan(self, inplace: bool = True, channels: Optional[list[str]] = None):
    """
    Remove overscan regions from the image data.

    This method subtracts the mean value of a predefined overscan region
    from the specified channels (blue, green, red). By default, the operation
    is performed on all channels and modifies the current instance in-place.
    Optionally, a new instance with the overscan-subtracted data can be returned.

    Parameters
    ----------
    inplace : bool, optional
        If True (default), modifies the current instance in-place.
        If False, returns a new instance with the overscan-subtracted data.

    channels : list of str, optional
        A list of channel names to operate on. Must be a subset of ``self.CHANNELS``.
        Defaults to all channels (``self.CHANNELS``).

    Returns
    -------
    GONetFile or None
        If `inplace` is False, returns a new instance with the overscan-subtracted data.
        Otherwise, returns None.

    Notes
    -----
    - The overscan region is defined as the slice of rows from 10 to 20 (exclusive).
    - If `inplace` is False, the metadata and file type are preserved in the returned instance.
    """
    if channels is None:
        channels = self.CHANNELS  # Default to all channels

    # Validate channels
    invalid_channels = [ch for ch in channels if ch not in self.CHANNELS]
    if invalid_channels:
        raise ValueError(f"Invalid channel(s): {invalid_channels}. Allowed channels: {self.CHANNELS}")

    overscan_region = slice(10, 20)  # Define the overscan region
    subtracted_data = {}

    # Loop over the specified channels and calculate the overscan-subtracted data
    for channel in channels:
        channel_data = self.get_channel(channel)
        overscan_mean = np.mean(channel_data[overscan_region])
        subtracted_data[channel] = channel_data - overscan_mean

    if inplace:
        # Modify the current instance in-place using set_channel
        for channel in channels:
            self.set_channel(channel, subtracted_data[channel])
        return None

    kwargs = {
        "filename": self.filename,
        "meta": self.meta,
        "filetype": self.filetype,
    }

    # duck typing to handle both GONetFile and GONetFileRaw
    if hasattr(self, "is_bayer_planes"):
        kwargs["is_bayer_planes"] = bool(getattr(self, "is_bayer_planes"))
    
    # Populate channel kwargs by iterating the class-declared CHANNELS
    for ch in self.CHANNELS:
        kwargs[ch] = subtracted_data.get(ch, self.get_channel(ch))
    
    # Construct a new instance of the same class with the appropriate signature
    return self.__class__(**kwargs)