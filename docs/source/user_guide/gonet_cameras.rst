.. _user-guide-gonet-cameras:

GONet Cameras
=============

A GONet camera is an imaging unit built around a Raspberry Pi camera stack and
a Sony IMX477 image sensor. In the current configuration, GONet uses the
Raspberry Pi HQ Camera module and captures images through the legacy
``picamera``/MMAL pipeline.

For GONet Wizard, the most important practical point is that these cameras do
not only produce ordinary JPEG images. When acquisition is configured with raw
capture enabled, the JPEG file also contains raw Bayer sensor data. That raw
component preserves physically meaningful pixel values that are better suited to
quantitative work than the processed 8-bit JPEG preview.

Hardware overview
-----------------

The current GONet hardware configuration uses:

- Raspberry Pi HQ Camera module.
- Sony IMX477 back-illuminated CMOS image sensor.
- Native full-frame resolution of 4056 x 3040 pixels.
- 1.55 micrometer pixels.
- Rolling shutter readout.
- Native 12-bit ADC output.
- Raw Bayer acquisition when enabled by the capture pipeline.

The raw sensor values span the physical ADC range from approximately 0 to 4095.
For saturation analysis, this matters: a raw pixel value near 4095 corresponds
to the meaningful saturation limit of the acquisition, whereas the JPEG image is
an 8-bit, ISP-processed representation intended primarily for display.

Acquisition pipeline
--------------------

GONet images are captured with the legacy Raspberry Pi camera stack, using
``picamera`` with the camera configured in sensor mode 3. Conceptually, the
capture pipeline produces two related products inside the same image file:

- an ISP-processed JPEG image, convenient for quick viewing;
- a packed 12-bit raw Bayer block, useful for quantitative analysis.

GONet Wizard focuses on recovering and working with the scientifically useful
parts of that file while still making the convenient display image available for
inspection and visualization.

Current sensor mode
-------------------

The current GONet configuration uses ``sensor_mode = 3``. In the legacy IMX477
camera stack, this mode provides:

- full-resolution readout at 4056 x 3040 pixels;
- full sensor field of view;
- true 12-bit raw Bayer acquisition;
- no binning;
- maximum dynamic range for still-image acquisition.

This is the mode assumed by the GONet parsing utilities in the package. It is
also why the raw data path is central to GONet Wizard: the raw values preserve
the full 12-bit dynamic range of the sensor.

Why raw data matters
--------------------

The JPEG image is useful for visual inspection, but it has already passed
through the camera image signal processor. During that processing, the data are
converted to 8-bit channels and may be affected by color processing, tone
mapping, compression, and other display-oriented transformations.

The raw Bayer data are different. They retain the sensor measurements before
that display-oriented processing. For tasks such as saturation checks, channel
statistics, or repeatable photometric-style measurements, the raw data are the
preferred input.

GONet Wizard therefore treats a GONet image as more than a picture. It treats it
as an observational data product containing image arrays, channels, and metadata.

Where to Go Next
----------------

* :doc:`GONet images user guide <gonet_images>`
* :doc:`channels user guide <channels>`
* :doc:`image inspection tool guide <../tools/inspect_images>`
* :doc:`GONetFile API reference <../api_reference/gonet>`

