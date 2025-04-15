GONet Raw Data Format
=====================

Overview
--------

GONet cameras save raw image data in a special 12-bit packed format. Each frame is saved as a `.jpg` file, but the pixel data inside the file is encoded using a compact Bayer-mosaiced scheme with 12 bits per pixel. This allows storage of high dynamic range data with minimal space usage.

The sensor uses a BGGR Bayer pattern, as shown below:

.. figure:: _static/bayer_pattern.pdf
   :align: center
   :width: 50%
   :alt: BGGR Bayer Pattern

   BGGR Bayer mosaic used by the GONet image sensor.

Byte Parsing
------------

Each pixel is encoded with 12 bits, and every group of two pixels is packed into 3 consecutive bytes. The format is as follows:

- **Byte 0**: lower 8 bits of Pixel 0  
- **Byte 1**: lower 8 bits of Pixel 1  
- **Byte 2**: upper 4 bits of both Pixel 0 and Pixel 1, packed as two nibbles

This packaging is commonly known as a *12-bit packed little endian* format. The following diagram shows how 3 bytes form 2 pixel values:

.. figure:: _static/GONet_bytes_pixels.pdf
   :align: center
   :width: 90%
   :alt: Byte-wise packing of 12-bit pixels

   Packing of 12-bit pixel values into 8-bit bytes.

In :meth:`GONetFile._parse_jpg_file` raw files are read in binary mode. In order to reconstruct the original pixels values from the bytes, the following procedures are executed. Let's assume the bytes are listed in a ``bytes_array`` :mod:`numpy.array`

- To recreate the first pixel, the first element of every block of 3 elements of ``bytes_array`` is left shifted by 4 bits (using the operator ``<<``). The third element of every block of 3 elements is then cut to the first 4 less significant bits (done by using an ``&`` operator with the number 15, which is 1111). These 2 new numbers are then summed.

  .. code-block:: python

    byte0 = b'00010110'
    byte0_left_shifted = byte0 << 4 # -> 000101100000
    byte2 = b'10100111'
    byte2_cut = byte2 & 15 # -> 0111
    pixel0 = byte0_left_shifted + byte2_cut # -> 000101100111

- To recreate the second pixel, the second element of every block of 3 elements of ``bytes_array`` is left shifted by 4 bits. The third element of every block of 3 elements is then right shifted by 4 bits (using the operator ``>>``). These 2 new numbers are then summed.

  .. code-block:: python

    byte0 = b'11000110'
    byte0_left_shifted = byte0 << 4 # -> 110001100000
    byte2_right_shifted = byte2 >> 4 # -> 1010
    pixel0 = byte0_left_shifted + byte2_right_shifted # -> 110001101010

Each recreated pixel is then stored in each channel following the bayer pattern. 
