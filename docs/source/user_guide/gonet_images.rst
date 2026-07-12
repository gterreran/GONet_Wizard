.. _user-guide-gonet-images:

GONet Images
============

A GONet image is usually stored as a JPEG file, but it should not be thought of
as a simple photograph. In the GONet acquisition configuration, the file can
contain both an ordinary JPEG image and an appended raw Bayer data block. It
also carries metadata that describes the observation and camera state.

A useful mental model is:

.. code-block:: text

   GONet image file
   ├── JPEG image data
   ├── raw Bayer sensor data
   ├── EXIF metadata
   └── GONet-specific observational metadata

GONet Wizard exists largely to make these components accessible through a common
interface.

JPEG component
--------------

The JPEG component is the image that ordinary viewers open. It is useful for:

- quick visual inspection;
- previews in the GUI;
- display-oriented plots;
- checking framing, clouds, gross image quality, or obvious acquisition issues.

Because the JPEG is processed and compressed, it should not be treated as the
most reliable source for quantitative sensor-level measurements. When a
standard display-oriented JPEG product is needed outside the original GONet RAW
container, use the :doc:`split RAW images tool <../tools/split_raw_images>` to
write a converted ``.jpeg`` file.

Raw Bayer component
-------------------

The raw Bayer component stores the sensor measurements in a packed 12-bit
format. Every pixel belongs to one position in the Bayer mosaic, so the raw
array must be interpreted in terms of color-filter positions before it can be
split into channels.

GONet Wizard parses this raw block and exposes the resulting data through
channel arrays. Those arrays are the basis for channel display, full-array
construction, extraction workflows, and conversion to standard TIFF/JPEG
products through the :doc:`split RAW images tool <../tools/split_raw_images>`.

Metadata
--------

GONet images also contain metadata. Depending on the file and acquisition
context, this can include information such as:

- camera and acquisition settings;
- exposure information;
- timestamp information;
- location or observing context;
- weather or environment-related fields, when available.

The exact available fields may vary between files. GONet Wizard therefore uses a
structured metadata model rather than assuming every file contains every field.

Converted TIFF and JPEG products
--------------------------------

Original GONet RAW files normally use the ``.jpg`` extension because the file
contains a JPEG component. Converted products should be treated differently:

``.tiff``
    A standard TIFF image written from the parsed RAW data. GONet Wizard keeps
    TIFF white balance disabled by default in the split RAW workflow so the
    output remains better suited to quantitative follow-up.

``.jpeg``
    A standard JPEG image written for display. GONet Wizard uses the ``.jpeg``
    extension for converted JPEGs to distinguish them from the original RAW
    ``.jpg`` containers. JPEG white balance is enabled by default because these
    products are usually intended for visual inspection.

For conversion instructions, see :doc:`split RAW images tool guide <../tools/split_raw_images>`.

How GONet Wizard reads image files
----------------------------------

When GONet Wizard opens a supported image file, it builds an internal object
that combines the image arrays and metadata. This object is usually a
:class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile` or, when the
separate Bayer-plane representation is needed, a
:class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file_raw.GONetFileRaw`.

Those objects are described conceptually in :ref:`user-guide-gonetfile` and in
more detail in the :doc:`API Reference <../api_reference/index>`.

Where to Go Next
----------------

* :doc:`GONetFile user guide <gonetfile>`
* :doc:`channels user guide <channels>`
* :doc:`metadata inspection tool guide <../tools/inspect_metadata>`
* :doc:`split RAW images tool guide <../tools/split_raw_images>`
* :doc:`GONetFile API reference <../api_reference/gonet>`

