"""
Build the Full-Array of a GONet Image
=====================================

Build a full-array GONet image by histogram matching and combining Bayer channels.

Overview
--------
GONet RAW images store data in a Bayer mosaic. This module:

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
- Since we need the full Bayer array, only GONet RAW ``.jpg`` files can be used as input.
- Output full-array is stored as float32 to reduce disk and memory footprint.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np

from GONet_Wizard.GONet_utils import GONetFileRaw
from GONet_Wizard.logging_utils import get_logger

logger = get_logger(__name__)


def hist_match_to_ref(
    src: np.ndarray,
    ref: np.ndarray,
    n_bins: int = 512,
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
        Float32 array with the same shape as ``src``, histogram-matched to ``ref``.
    """
    # Work in float32 to reduce memory and avoid float64 promotion.
    src_flat = np.asarray(src, dtype=np.float32).ravel()
    ref_flat = np.asarray(ref, dtype=np.float32).ravel()

    # finite values only
    src_vals = src_flat[np.isfinite(src_flat)]
    ref_vals = ref_flat[np.isfinite(ref_flat)]

    if clip is not None:
        lo, hi = clip
        src_vals = src_vals[(src_vals >= lo) & (src_vals <= hi)]
        ref_vals = ref_vals[(ref_vals >= lo) & (ref_vals <= hi)]

    if src_vals.size == 0 or ref_vals.size == 0:
        raise ValueError("No finite values in src or ref after clipping.")

    # common bin range
    all_min = float(min(src_vals.min(), ref_vals.min()))
    all_max = float(max(src_vals.max(), ref_vals.max()))
    if all_min == all_max:
        # pathological constant image; just return src as float32
        return src_flat.reshape(src.shape).astype(np.float32, copy=False)

    # bins in float32
    bins = np.linspace(all_min, all_max, int(n_bins), dtype=np.float32)

    # histograms -> CDFs (hist is float64 by default; that's fine; it's small)
    src_hist, _ = np.histogram(src_vals, bins=bins, density=True)
    ref_hist, _ = np.histogram(ref_vals, bins=bins, density=True)

    src_cdf = np.cumsum(src_hist)
    src_cdf /= src_cdf[-1]

    ref_cdf = np.cumsum(ref_hist)
    ref_cdf /= ref_cdf[-1]

    bin_centers = 0.5 * (bins[:-1] + bins[1:])  # float32

    # inverse CDF for ref (via interpolation)
    ref_inv = np.interp(src_cdf, ref_cdf, bin_centers)

    # map each src pixel: value -> quantile under src -> value under ref
    src_quantiles = np.interp(src_flat, bin_centers, src_cdf, left=0.0, right=1.0)
    mapped_flat = np.interp(src_quantiles, src_cdf, ref_inv).astype(np.float32, copy=False)

    return mapped_flat.reshape(src.shape)


def _combine_channels_weighted(
    matched: Dict[str, np.ndarray],
    channel_order: Iterable[str],
    channel_weights: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    """
    Combine matched channels into a single image using optional weights.

    Returns
    -------
    combined_image : :class:`numpy.ndarray`
        Float32 combined full-array image.
    """
    if channel_weights is None:
        channel_weights = {}

    first_channel = next(iter(channel_order))
    shape = matched[first_channel].shape

    # Accumulate in float32 (big arrays); keep weights as float32 too.
    weighted_sum = np.zeros(shape, dtype=np.float32)
    weight_sum = np.zeros(shape, dtype=np.float32)

    for c in channel_order:
        ch = np.asarray(matched[c], dtype=np.float32)
        w = np.float32(channel_weights.get(c, 1.0))

        valid = np.isfinite(ch)
        ch_safe = np.where(valid, ch, np.float32(0.0))

        weighted_sum += w * ch_safe
        weight_sum += w * valid.astype(np.float32)

        logger.debug("Applied weight %.3f to channel '%s'.", float(w), c)

    combined = weighted_sum / np.maximum(weight_sum, np.float32(1e-9))
    return combined.astype(np.float32, copy=False)


def _hist_payload(arr: np.ndarray, hist_bins: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (bin_centers, density) for finite values of arr, both float32.
    """
    vals = np.asarray(arr, dtype=np.float32).ravel()
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

    hist, edges = np.histogram(vals, bins=int(hist_bins), density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers.astype(np.float32, copy=False), hist.astype(np.float32, copy=False)


def build_full_array(
    gonet_file: Path,
    show: bool = False,
    outfile: Optional[Path] = None,
    verbose: bool = False,
    channel_weights: Optional[Dict[str, float]] = None,
    *,
    save_diagnostics: bool = True,
    hist_bins: int = 100,
    n_bins_match: int = 512,
    clip_match: Optional[Tuple[float, float]] = None,
) -> None:
    """
    Build a full-array GONet image by histogram matching and averaging channels.

    Parameters
    ----------
    gonet_file : :class:`Path`
        Path to the input GONet RAW ``.jpg`` file.
    show : :class:`bool`, optional
        If ``True``, show diagnostic histograms and the combined image using matplotlib.
    outfile : :class:`Path`, optional
        Output file name for the compressed ``.npz`` file. If ``None``,
        a default name based on ``gonet_file`` is used.
    verbose : :class:`bool`, optional
        If ``True``, enable more verbose logging.
    channel_weights : :class:`dict`, optional
        Mapping ``channel_name -> weight`` for combining channels.
    save_diagnostics : :class:`bool`, optional
        If ``True``, save per-channel histogram summaries (raw + matched) in the output .npz.
    hist_bins : :class:`int`, optional
        Number of bins used for diagnostic histograms.
    n_bins_match : :class:`int`, optional
        Number of bins used for histogram matching CDFs.
    clip_match : :class:`tuple` of :class:`float`, optional
        Optional clipping applied inside histogram matching.

    Returns
    -------
    None
    """
    if gonet_file.suffix.lower() != ".jpg":
        raise ValueError("Input file must be a GONet RAW .jpg file.")

    if verbose:
        logger.info("Verbose processing requested for full-array build.")

    logger.info("Loading %s.", os.path.basename(gonet_file))
    go = GONetFileRaw.from_file(gonet_file, meta=False)

    logger.info("Processing image: removing overscan.")
    go.remove_overscan()

    logger.info("Converting to Bayer planes.")
    go.as_bayer_planes()

    ref_channel_name = "green1"
    ref = np.asarray(go.get_channel(ref_channel_name), dtype=np.float32)

    diag: Dict[str, object] = {}

    # Optional matplotlib diagnostics (kept separate; no KDE)
    if show:
        import matplotlib.pyplot as plt  # local import

        plt.figure()
        for c in go.CHANNELS:
            ch = np.asarray(go.get_channel(c), dtype=np.float32)
            plt.hist(
                ch.ravel(),
                bins=int(hist_bins),
                alpha=0.3,
                color=go.COLORS.get(c, None),
                density=True,
                label=c,
            )
        plt.legend()
        plt.title("Original channel histograms")
        plt.xlabel("Pixel value")
        plt.ylabel("Density")
        plt.tight_layout()
        plt.show()

    # Save raw histogram diagnostics
    if save_diagnostics:
        for c in go.CHANNELS:
            centers, hist = _hist_payload(go.get_channel(c), hist_bins=int(hist_bins))
            diag[f"raw_hist_bins_{c}"] = centers
            diag[f"raw_hist_density_{c}"] = hist

    # Histogram-match all channels to green1
    matched: Dict[str, np.ndarray] = {}
    logger.info("Histogram matching channels to reference '%s'.", ref_channel_name)

    for c in go.CHANNELS:
        ch = np.asarray(go.get_channel(c), dtype=np.float32)

        if c == ref_channel_name:
            matched[c] = ch
            logger.debug("Channel '%s' is the reference; no matching applied.", c)
        else:
            matched[c] = hist_match_to_ref(
                ch,
                ref,
                n_bins=int(n_bins_match),
                clip=clip_match,
            )
            logger.debug("Histogram matched channel '%s' to '%s'.", c, ref_channel_name)

        if save_diagnostics:
            centers, hist = _hist_payload(matched[c], hist_bins=int(hist_bins))
            diag[f"matched_hist_bins_{c}"] = centers
            diag[f"matched_hist_density_{c}"] = hist

    if show:
        import matplotlib.pyplot as plt  # local import

        plt.figure()
        for c in go.CHANNELS:
            plt.hist(
                np.asarray(matched[c], dtype=np.float32).ravel(),
                bins=int(hist_bins),
                alpha=0.3,
                color=go.COLORS.get(c, None),
                density=True,
                label=c,
            )
        plt.legend()
        plt.title("Matched channel histograms")
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
        import matplotlib.pyplot as plt  # local import

        plt.figure()
        plt.imshow(combined_image, origin="upper")
        plt.colorbar(label="Value")
        plt.title("Combined full-array GONet image")
        plt.tight_layout()
        plt.show()

    if outfile is None:
        outfile = Path(f"{gonet_file.stem}_full_array.npz")

    # Save float32 image (biggest win)
    image_out = np.asarray(combined_image, dtype=np.float32)

    if save_diagnostics:
        np.savez_compressed(outfile, image=image_out, **diag)
    else:
        np.savez_compressed(outfile, image=image_out)

    logger.info("Saved full-array GONet image to %s.", outfile)
