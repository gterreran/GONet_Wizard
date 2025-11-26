"""
Parser for EXIF metadata embedded in GONet JPEG files.

This module defines :func:`.parse_exif_metadata`, which extracts, normalizes,
and restructures EXIF metadata from the header of a GONet JPEG image into a
hierarchical Python dictionary.

The function decodes camera-embedded fields such as analog gain, exposure time,
and Bayer dimensions, organizes GPS coordinates into a dedicated sub-dictionary,
and groups JPEG-specific information (e.g., color space, white balance, component
configuration) under the ``'JPEG'`` key.

**Functions**

- :func:`.parse_exif_metadata`
    Parse and restructure EXIF metadata from a GONet JPEG file into a nested
    dictionary with standardized field names.

"""

from PIL.ExifTags import TAGS
import re

@staticmethod
def parse_exif_metadata(exif: dict) -> dict:
    """
    Extract and restructure EXIF metadata from a JPEG file into a structured dictionary.

    Parameters
    ----------
    exif : dict
        A dictionary containing raw EXIF metadata extracted from the JPEG file.

    Returns
    -------
    dict
        A structured metadata dictionary, with JPEG-related keys under 'JPEG'.
    """

    structured = {}
    jpeg_meta = {}
    gps_meta = {}

    for tag_id, value in exif.items():
        tag = TAGS.get(tag_id, str(tag_id))

        if tag == "Artist":
            # Use a regex to match key-value pairs, including tuples inside parentheses
            # This avoids splitting on commas inside values
            matches = re.finditer(r'(\w+):\s*(\([^)]+\)|[^,]+)', value)
            for match in matches:
                k, v = match.groups()
                k = k.strip().lower()
                v = v.strip()

                if k == "wb":
                    try:
                        jpeg_meta["WB"] = [float(x.strip()) for x in v.strip("()").split(',')]
                    except Exception:
                        continue  # skip malformed white balance
                # We get the latitude, longitude and altitude from the GPS field so we skip them here
                elif k in {"lat", "long", "alt"}:
                    continue
                    # try:
                    #     structured["latitude" if k == "lat" else "longitude" if k == "long" else "altitude"] = float(v)
                    # except ValueError:
                    #     continue
                else:
                    structured[k] = v
            continue

        # It looks like Software repeats stuff in the artist fiels, so I'll ignore it
        elif tag == "Software":
            continue

        elif tag == "GPSInfo":
            gps = value

            # Normalize keys to integers (if they're strings)
            gps_normalized = {}
            for k, v in gps.items():
                try:
                    gps_normalized[int(k)] = v
                except (ValueError, TypeError):
                    gps_normalized[k] = v  # fallback for non-integer keys

            def dms_to_deg(dms):
                return dms[0] + dms[1] / 60.0 + dms[2] / 3600.0

            if 1 in gps_normalized and 2 in gps_normalized:
                lat = dms_to_deg(gps_normalized[2])
                if gps_normalized[1] in ("S", b"S"):
                    lat = -lat
                gps_meta["latitude"] = float(lat)

            if 3 in gps_normalized and 4 in gps_normalized:
                lon = dms_to_deg(gps_normalized[4])
                if gps_normalized[3] in ("W", b"W"):
                    lon = -lon
                gps_meta["longitude"] = float(lon)

            if 6 in gps_normalized:
                gps_meta["altitude"] = float(gps_normalized[6])
            continue

        elif tag == "MakerNote":
            # Parse values like 'gain_r=1.000 gain_b=1.000'
            if isinstance(value, bytes):
                value = value.decode("latin1")

            for match in re.finditer(r'(\w+)=([-\d.]+)', value):
                k, v = match.groups()
                if k.lower() == 'ag':
                    structured['analog_gain'] = float(v)
                else:
                    continue
                #structured[k.lower()] = float(v)
            continue

        elif tag == "ComponentsConfiguration":
            decoded = {
                1: "Y", 2: "Cb", 3: "Cr", 4: "R", 5: "G", 6: "B", 0: ""
            }
            component_str = "".join(decoded.get(b, "?") for b in value)
            jpeg_meta["ComponentsConfiguration"] = component_str
            continue

        elif tag == "YCbCrPositioning":
            YCBCR_POSITIONING_MAP = {
                1: "Centered",
                2: "Co-sited"
            }
            jpeg_meta["YCbCrPositioning"] = YCBCR_POSITIONING_MAP.get(value, f"Unknown ({value})")
            continue


        elif tag == "ColorSpace":
            COLORSPACE_MAP = {
                1: "sRGB",
                65535: "Uncalibrated"
            }
            jpeg_meta["ColorSpace"] = COLORSPACE_MAP.get(value, f"Reserved ({value})")
            continue

        elif tag == "ExifImageWidth":
            structured["bayer_width"] = int(value)
            continue
        elif tag == "ExifImageHeight":
            structured["bayer_height"] = int(value)
            continue
        elif tag == "ExposureTime":
            structured["exposure_time"] = float(value)
            continue
        elif tag == "ShutterSpeedValue":
            structured["shutter_speed"] = float(value)
            continue

        elif tag in ["ImageLength", "ImageWidth", "MeteringMode", "ExposureMode", "ExposureProgram", "Flash"]:
            continue

        else:
            if isinstance(value, (int, float, str)) and len(str(value)) < 100:
                structured[tag] = value

    # Derive real image dimensions from Bayer size
    if "bayer_width" in structured and "bayer_height" in structured:
        structured["image_width"] = structured["bayer_width"] // 2
        structured["image_height"] = structured["bayer_height"] // 2

    structured["GPS"] = gps_meta
    structured["JPEG"] = jpeg_meta
    return structured