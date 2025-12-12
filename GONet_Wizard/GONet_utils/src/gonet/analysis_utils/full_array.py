"""
Build the Full-Array of a GONet Image
==============================================

Build a full-array GONet image by histogram matching and combining Bayer channels.

Overview
--------
GONet RAW images store data in a Bayer mosaic. This script:

1. Loads a GONet RAW :class:`.jpg` file via :class:`GONetFileRaw`.
2. Removes the overscan region.
3. Splits the image into Bayer planes (e.g. ``red``, ``green1``, ``green2``, ``blue``).
4. Histogram-matches all non-reference channels to the reference channel
   (by default ``green1``), so that their pixel distributions become comparable.
5. Combines the matched channels into a single full-array image using either
   equal weights (default) or user-specified per-channel weights.
6. Optionally displays diagnostic histograms and the combined image.
7. Saves the resulting full-array image as a compressed ``.npz`` file.

Notes
-----
- Since we need the full bayer array, only GONet RAW ``.jpg`` files can be used as input.
- Channel weights do not need to be normalized; they are applied and then
  normalized by the sum of weights at each pixel (taking into account NaNs).

Functions
---------
- :func:`build_full_array` : Build the full-array GONet image from a RAW file.
- :func:`hist_match_to_ref` : Histogram-match a source array to a reference array.
- :func:`kde_peak` : Compute a 1-D KDE and return the peak location.
- :func:`_combine_channels_weighted` : Combine matched channels using optional weights.

"""

from __future__ import annotations

import logging
import os
from typing import Dict, Iterable, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

from GONet_Wizard.GONet_utils import GONetFileRaw
from pathlib import Path

logger = logging.getLogger(__name__)


def hist_match_to_ref(
    src: np.ndarray,
    ref: np.ndarray,
    n_bins: int = 2048,
    clip: Optional[Tuple[float, float]] = None,
) -> np.ndarray:
    """
    Map ``src`` values so that its histogram matches ``ref``'s histogram.

    Parameters
    ----------
    src : :class:`numpy.ndarray`
        Source channel image (1-D or 2-D).
    ref : :class:`numpy.ndarray`
        Reference channel image (1-D or 2-D).
    n_bins : :class:`int`, optional
        Number of histogram bins to use for computing the CDFs.
    clip : :class:`tuple` of :class:`float`, optional
        If given as ``(low, high)``, both ``src`` and ``ref`` values are clipped
        to this range before building the histograms.

    Returns
    -------
    matched : :class:`numpy.ndarray`
        Array with the same shape as ``src``, where the pixel values have been
        remapped so that the overall histogram matches that of ``ref``.

    Raises
    ------
    ValueError
        If there are no finite values in ``src`` or ``ref`` after clipping.
    """
    src_flat = np.ravel(src).astype(float)
    ref_flat = np.ravel(ref).astype(float)

    # keep only finite values
    src_valid = np.isfinite(src_flat)
    ref_valid = np.isfinite(ref_flat)
    src_vals = src_flat[src_valid]
    ref_vals = ref_flat[ref_valid]

    if clip is not None:
        lo, hi = clip
        src_vals = src_vals[(src_vals >= lo) & (src_vals <= hi)]
        ref_vals = ref_vals[(ref_vals >= lo) & (ref_vals <= hi)]

    if src_vals.size == 0 or ref_vals.size == 0:
        raise ValueError("No finite values in src or ref after clipping.")

    # common bin range
    all_min = min(src_vals.min(), ref_vals.min())
    all_max = max(src_vals.max(), ref_vals.max())
    bins = np.linspace(all_min, all_max, n_bins)

    # histograms → CDFs
    src_hist, _ = np.histogram(src_vals, bins=bins, density=True)
    ref_hist, _ = np.histogram(ref_vals, bins=bins, density=True)

    src_cdf = np.cumsum(src_hist)
    src_cdf /= src_cdf[-1]

    ref_cdf = np.cumsum(ref_hist)
    ref_cdf /= ref_cdf[-1]

    bin_centers = 0.5 * (bins[:-1] + bins[1:])

    # Build inverse CDF for ref: given quantile q, get value x such that F_ref(x) = q
    ref_inv = np.interp(src_cdf, ref_cdf, bin_centers)

    # Now map each src pixel:
    # 1) value -> quantile under src (via interpolation)
    # 2) quantile -> value under ref_inv
    src_quantiles = np.interp(
        src_flat,
        bin_centers,
        src_cdf,
        left=0.0,
        right=1.0,
    )
    mapped_flat = np.interp(src_quantiles, src_cdf, ref_inv)

    matched = mapped_flat.reshape(src.shape)
    return matched


def kde_peak(
    values: Iterable[float],
    n_points: int = 500,
    clip: Optional[Tuple[float, float]] = None,
    bw_factor: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Compute a 1-D KDE and return the grid, KDE values, and peak location.

    Parameters
    ----------
    values : iterable of :class:`float`
        Input data. NaNs and non-finite values are ignored.
    n_points : :class:`int`, optional
        Number of grid points for KDE evaluation.
    clip : :class:`tuple` of :class:`float`, optional
        If given as ``(low, high)``, values outside this range are discarded.
    bw_factor : :class:`float`, optional
        Bandwidth multiplier passed to the Gaussian KDE. Values below 1.0
        sharpen the KDE, while values above 1.0 smooth it.

    Returns
    -------
    xgrid : :class:`numpy.ndarray`
        Grid of x values at which the KDE is evaluated.
    kde_vals : :class:`numpy.ndarray`
        KDE values corresponding to ``xgrid``.
    peak_x : :class:`float`
        Location of the maximum of the KDE (mode estimate).

    Raises
    ------
    ValueError
        If there are fewer than two finite values after clipping.
    """
    vals = np.asarray(list(values), dtype=float)
    vals = vals[np.isfinite(vals)]

    if clip is not None:
        lo, hi = clip
        vals = vals[(vals >= lo) & (vals <= hi)]

    if vals.size < 2:
        raise ValueError("Not enough finite values to compute KDE.")

    kde = gaussian_kde(vals)
    if bw_factor is not None:
        kde.set_bandwidth(kde.factor * bw_factor)

    xgrid = np.linspace(vals.min(), vals.max(), n_points)
    kde_vals = kde(xgrid)
    peak_x = xgrid[np.argmax(kde_vals)]
    return xgrid, kde_vals, peak_x


def _combine_channels_weighted(
    matched: Dict[str, np.ndarray],
    channel_order: Iterable[str],
    channel_weights: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    """
    Combine matched channels into a single image using optional weights.

    Parameters
    ----------
    matched : :class:`dict`
        Mapping from channel name to matched image array.
    channel_order : iterable of :class:`str`
        Order in which channels should be combined.
    channel_weights : :class:`dict`, optional
        Mapping ``channel_name -> weight``. If ``None``, all channels are
        assigned weight 1.0. Missing channels default to 1.0.

    Returns
    -------
    combined_image : :class:`numpy.ndarray`
        Full-array combined image (float).
    """
    # Default weights: all 1.0
    if channel_weights is None:
        channel_weights = {}

    # Initialize accumulation arrays
    first_channel = next(iter(channel_order))
    shape = matched[first_channel].shape
    weighted_sum = np.zeros(shape, dtype=float)
    weight_sum = np.zeros(shape, dtype=float)

    for c in channel_order:
        ch = matched[c].astype(float)
        w = float(channel_weights.get(c, 1.0))

        valid = np.isfinite(ch)
        ch_safe = np.nan_to_num(ch, nan=0.0)

        weighted_sum += w * ch_safe
        weight_sum += w * valid

        logger.debug("Applied weight %.3f to channel '%s'.", w, c)

    combined_image = weighted_sum / np.maximum(weight_sum, 1e-9)
    return combined_image


def build_full_array(
    gonet_file: Path,
    show: bool = False,
    outfile: Optional[Path] = None,
    verbose: bool = False,
    channel_weights: Optional[Dict[str, float]] = None,
) -> None:
    """
    Build a full-array GONet image by histogram matching and averaging channels.

    Parameters
    ----------
    gonet_file : :class:`Path`
        Path to the input GONet RAW ``.jpg`` file.
    show : :class:`bool`, optional
        If ``True``, show diagnostic histograms and the combined image.
    outfile : :class:`Path`, optional
        Output file name for the compressed ``.npz`` file. If ``None``,
        a default name based on ``gonet_file`` is used.
    verbose : :class:`bool`, optional
        If ``True``, enable more verbose logging.
    channel_weights : :class:`dict`, optional
        Mapping ``channel_name -> weight``. If given, these weights are
        used when combining the matched channels. Missing channels default
        to 1.0; extra keys are ignored.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the input file is not a GONet RAW ``.jpg`` file.
    """
    if gonet_file.suffix.lower() != ".jpg":
        raise ValueError("Input file must be a GONet RAW .jpg file.")

    # If logger has no handlers, configure it minimally
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Set default level only if not already set externally
    if verbose:
        logger.setLevel(logging.INFO)
    else:
        # only set WARNING if logger is still at NOTSET
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.WARNING)

    logger.info("Loading %s.", os.path.basename(gonet_file))
    go = GONetFileRaw.from_file(gonet_file, meta=False)

    logger.info("Processing image: removing overscan.")
    go.remove_overscan()

    logger.info("Converting to Bayer planes.")
    go.as_bayer_planes()

    # Optional diagnostic: per-channel histograms and KDE peaks
    if show:
        peaks = {}
        for c in go.CHANNELS:
            ch = go.get_channel(c)

            plt.hist(
                ch.ravel(),
                bins=100,
                alpha=0.3,
                color=go.COLORS[c],
                density=True,
                label=c,
            )

            try:
                xg, kde_vals, peak = kde_peak(ch.ravel())
                plt.plot(xg, kde_vals, color=go.COLORS[c], lw=2)
                plt.axvline(peak, color=go.COLORS[c], linestyle="--")
                peaks[c] = peak
            except ValueError as exc:
                logger.warning("Skipping KDE for channel '%s': %s", c, exc)

        plt.legend()
        plt.title("Original channel histograms with KDE peaks")
        plt.xlabel("Pixel value")
        plt.ylabel("Density")
        plt.tight_layout()
        plt.show()

    # Histogram-match all channels to green1
    ref_channel_name = "green1"
    ref = go.get_channel(ref_channel_name)
    matched: Dict[str, np.ndarray] = {}

    logger.info("Histogram matching channels to reference '%s'.", ref_channel_name)
    for c in go.CHANNELS:
        ch = go.get_channel(c)
        if c == ref_channel_name:
            matched[c] = ch
            logger.debug("Channel '%s' is the reference; no matching applied.", c)
        else:
            matched[c] = hist_match_to_ref(ch, ref)
            logger.debug("Histogram matched channel '%s' to '%s'.", c, ref_channel_name)

        if show:
            plt.hist(
                matched[c].ravel(),
                bins=100,
                alpha=0.3,
                color=go.COLORS[c],
                density=True,
                label=c,
            )

    if show:
        plt.legend()
        plt.title(f"Matched histogram for channel '{c}'")
        plt.xlabel("Pixel value")
        plt.ylabel("Density")
        plt.tight_layout()
        plt.show()

    logger.info("Combining matched channels into a full-array image.")
    combined_image = _combine_channels_weighted(
        matched=matched,
        channel_order=go.CHANNELS,
        channel_weights=channel_weights,
    )

    if show:
        plt.figure()
        plt.imshow(combined_image, origin="upper")
        plt.colorbar(label="Value")
        plt.title("Combined full-array GONet image")
        plt.tight_layout()
        plt.show()

    if outfile is None:
        outfile = Path(f"{gonet_file.stem}_full_array.npz")

    np.savez_compressed(outfile, image=combined_image)
    logger.info("Saved full-array GONet image to %s.", outfile)