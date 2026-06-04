"""
Utility for exporting GONet image data to FITS format.

This module defines a function, :func:`.write_to_fits`, for saving the RGB image
data and associated metadata from a
:class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile`
or :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw`
instance into a standard multi-extension FITS file.

Each color channel is written to a separate FITS image extension (HDU),
and all relevant metadata from the GONet file is propagated into the FITS headers.
Metadata fields are automatically sanitized to comply with FITS format conventions.

**Functions**

- :func:`.write_to_fits`
    Write GONet RGB data and metadata to a multi-extension FITS file with separate HDUs for each color channel.
    
"""

import numpy as np
from astropy.io import fits

def write_to_fits(self, output_filename: str) -> None:
    """
    Write the image data to a multi-extension FITS file.

    This method saves the blue, green, and red channel data into separate
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
    - Each color channel (blue, green, red) is stored in a separate image extension.
    - Metadata keys longer than 8 characters or containing lowercase letters or symbols
        will be truncated or sanitized to conform to FITS header requirements.
    
    """

    def build_base_header() -> fits.Header:
        """
        Build the shared FITS header from the file metadata.

        Returns
        -------
        :class:`astropy.io.fits.Header`
            Header populated with GONet camera, image, exposure, and location
            metadata when available. If no metadata are present, an empty
            header is returned.
        """
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
        """
        Create an image extension for a single color channel.

        Parameters
        ----------
        data : :class:`numpy.ndarray`
            Pixel data to store in the FITS image extension.
        channel : :class:`str`
            Name of the channel represented by ``data``.

        Returns
        -------
        :class:`astropy.io.fits.ImageHDU`
            FITS image extension with channel-specific header keywords.
        """
        hdr = base_header.copy()
        hdr['CHANNEL'] = (channel.upper(), 'Image channel')
        hdr['EXTNAME'] = (channel.upper(), 'Extension name')
        return fits.ImageHDU(data=data, header=hdr)

    blue_hdu = make_channel_hdu(self.blue, 'blue')
    if hasattr(self, 'green1') and hasattr(self, 'green2'):
        green = ((self.green1 + self.green2) / 2)
    else:
        green = self.green
    green_hdu = make_channel_hdu(green, 'green')
    red_hdu = make_channel_hdu(self.red, 'red')

    # Create primary HDU (no data)
    primary_hdu = fits.PrimaryHDU()

    # Assemble HDUList
    hdul = fits.HDUList([primary_hdu, blue_hdu, green_hdu, red_hdu])
    hdul.writeto(output_filename, overwrite=True)