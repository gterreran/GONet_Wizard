# GONet_Wizard/GONet_utils/src/calibrators/distortion.py
"""
distortion.py
=============

Utilities to apply a polar-harmonic distortion calibration to GONet images.

This module provides tools to convert between:

    pixel coordinates  <->  angular coordinates (r, theta)

The distortion model is defined in the full Bayer-array coordinate system,
but can be applied seamlessly to single-channel (BGGR) images.

Typical usage
-------------

>>> cal = PolarHarmonicCalibrator.from_fit_npz("fit.npz")
>>> lookup = cal.build_lookup(image.shape)
>>> r, theta = lookup.sample(x, y)

You can also attach coordinate formatters for visualization:

>>> ax.format_coord = make_coordinate_formatter(lookup)

This enables WCS-like interaction (pixel + angular coordinates).

Notes
-----
- The fitted center (cx, cy) corresponds to the **distortion center**
  (≈ field-of-view center).
- Angular radius is in degrees.
- Theta is in degrees in [0, 360).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Tuple

import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.ndimage import map_coordinates

from GONet_Wizard.GONet_utils.src.gonet import config


# =============================================================================
# Data containers
# =============================================================================


@dataclass(frozen=True)
class CalibrationConfig:
    """
    Configuration of the fitted distortion model.

    Parameters
    ----------
    radial_degree : int
        Degree of the symmetric radial polynomial.
    harmonic_radial_degree : int
        Degree of radial dependence in harmonic terms.
    harmonic_order : int
        Maximum azimuthal harmonic order.
    fit_constant_terms : bool
        Whether constant (n=0) harmonic terms are included.
    r_nom_max_deg : float
        Maximum nominal angular radius used in the fit.
    """

    radial_degree: int
    harmonic_radial_degree: int
    harmonic_order: int
    fit_constant_terms: bool
    r_nom_max_deg: float


@dataclass
class PixelAngleLookup:
    """
    Lookup table mapping pixel coordinates to angular coordinates.

    Parameters
    ----------
    r_deg : np.ndarray
        Angular radius map (degrees).
    theta_deg : np.ndarray
        Angular azimuth map (degrees).
    channel : str
        Channel identifier ("full", "B", "G1", "G2", "R").
    """

    r_deg: np.ndarray
    theta_deg: np.ndarray
    channel: str = "full"

    def sample(self, x: np.ndarray, y: np.ndarray, order: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sample angular coordinates at arbitrary pixel positions.

        Parameters
        ----------
        x, y : np.ndarray
            Pixel coordinates.
        order : int
            Interpolation order.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            (r_deg, theta_deg)
        """
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        shape = np.broadcast_shapes(x.shape, y.shape)

        coords = np.vstack([
            np.broadcast_to(y, shape).ravel(),
            np.broadcast_to(x, shape).ravel(),
        ])

        r = map_coordinates(self.r_deg, coords, order=order, mode="constant", cval=np.nan)
        theta = map_coordinates(self.theta_deg, coords, order=order, mode="constant", cval=np.nan)

        return r.reshape(shape), theta.reshape(shape)


# =============================================================================
# Main calibrator
# =============================================================================


class PolarHarmonicCalibrator:
    """
    Apply a fitted polar-harmonic distortion calibration.

    The model maps:

        (r_deg, theta_deg) -> (pixel_x, pixel_y)

    and is inverted numerically via lookup tables.
    """

    def __init__(
        self,
        params: np.ndarray,
        param_names: list[str],
        config: CalibrationConfig,
    ) -> None:
        self.params = np.asarray(params, dtype=float)
        self.param_names = list(param_names)
        self.config = config

        self.cx = float(self.params[0])
        self.cy = float(self.params[1])
        self.theta0_deg = float(self.params[2])

        self.n_sym = 3 + config.radial_degree
        self.n_field_scalar = self._basis_size()

        expected = self.n_sym + 2 * self.n_field_scalar
        if self.params.size != expected:
            raise ValueError("Parameter vector size mismatch.")

    # -------------------------------------------------------------------------
    # Constructors
    # -------------------------------------------------------------------------

    @classmethod
    def from_fit_npz(cls, path: Path | str) -> "PolarHarmonicCalibrator":
        """Load a fitted calibration from NPZ."""
        loaded = np.load(Path(path), allow_pickle=True)

        params = loaded["params_full"]
        param_names = list(loaded["param_names"])

        radial_degree = sum(name.startswith("k") for name in param_names)

        dr_names = [n for n in param_names if n.startswith("dr_")]
        harmonic_radial_degree = max(int(n.split("_m")[1].split("_")[0]) for n in dr_names)
        harmonic_order = max(
            int(part[1:])
            for n in dr_names
            for part in n.split("_")
            if part.startswith(("c", "s"))
        )

        fit_constant_terms = any(n.endswith("_c0") for n in dr_names)
        r_nom_max_deg = float(np.nanmax(loaded["r_nominal_deg"]))

        config = CalibrationConfig(
            radial_degree=radial_degree,
            harmonic_radial_degree=harmonic_radial_degree,
            harmonic_order=harmonic_order,
            fit_constant_terms=fit_constant_terms,
            r_nom_max_deg=r_nom_max_deg,
        )

        return cls(params, param_names, config)

    # -------------------------------------------------------------------------
    # Model internals
    # -------------------------------------------------------------------------

    def _basis_size(self) -> int:
        start = 0 if self.config.fit_constant_terms else 1
        n_az = sum(1 if n == 0 else 2 for n in range(start, self.config.harmonic_order + 1))
        return (self.config.harmonic_radial_degree + 1) * n_az

    def _basis(self, s: np.ndarray, phi: np.ndarray) -> np.ndarray:
        cols = []
        start = 0 if self.config.fit_constant_terms else 1

        for m in range(self.config.harmonic_radial_degree + 1):
            sm = s**m
            for n in range(start, self.config.harmonic_order + 1):
                if n == 0:
                    cols.append(sm)
                else:
                    cols.append(sm * np.cos(n * phi))
                    cols.append(sm * np.sin(n * phi))

        return np.column_stack(cols) if cols else np.empty((s.size, 0))

    # -------------------------------------------------------------------------
    # Forward model
    # -------------------------------------------------------------------------

    def angular_to_pixel(self, r_deg: np.ndarray, theta_deg: np.ndarray):
        """Convert angular coordinates to full Bayer-array pixel coordinates."""
        r = np.asarray(r_deg, dtype=float)
        t = np.asarray(theta_deg, dtype=float)

        shape = np.broadcast_shapes(r.shape, t.shape)
        r_flat = np.broadcast_to(r, shape).ravel()
        t_flat = np.broadcast_to(t, shape).ravel()

        u = np.deg2rad(r_flat)
        s = r_flat / self.config.r_nom_max_deg
        phi = np.deg2rad(t_flat + self.theta0_deg)

        coeffs = self.params[3:self.n_sym]
        field = self.params[self.n_sym:]

        rho = np.zeros_like(u)
        for i, c in enumerate(coeffs, start=1):
            rho += c * u**i

        basis = self._basis(s, phi)

        if basis.size:
            n = basis.shape[1]
            dr = basis @ field[:n]
            dtan = basis @ field[n:n + n]
            rho = rho + dr
        else:
            dtan = np.zeros_like(rho)

        x = self.cx + rho * np.cos(phi) - dtan * np.sin(phi)
        y = self.cy + rho * np.sin(phi) + dtan * np.cos(phi)

        return x.reshape(shape), y.reshape(shape)

    # -------------------------------------------------------------------------
    # Lookup generation
    # -------------------------------------------------------------------------

    def build_lookup(
        self,
        image_shape: tuple[int, int],
        channel: config.ChannelName | Literal["full"] = "full",
        method: Literal["linear", "nearest"] = "linear",
    ) -> PixelAngleLookup:
        """
        Build pixel -> angular coordinate lookup.
        """
        if channel != "full":
            row_off, col_off = config.get_channel_bayer_offsets(channel)
            full_shape = (image_shape[0] * 2, image_shape[1] * 2)
        else:
            full_shape = image_shape

        r_axis = np.linspace(0, self.config.r_nom_max_deg, 600)
        t_axis = np.linspace(0, 360, 1800, endpoint=False)
        tt, rr = np.meshgrid(t_axis, r_axis)

        x, y = self.angular_to_pixel(rr, tt)
        pts = np.column_stack([x.ravel(), y.ravel()])

        theta_rad = np.deg2rad(tt.ravel())

        interp_cls = LinearNDInterpolator if method == "linear" else NearestNDInterpolator

        interp_r = interp_cls(pts, rr.ravel())
        interp_c = interp_cls(pts, np.cos(theta_rad))
        interp_s = interp_cls(pts, np.sin(theta_rad))

        yy, xx = np.indices(full_shape)
        q = np.column_stack([xx.ravel(), yy.ravel()])

        r_map = interp_r(q).reshape(full_shape)
        theta_map = np.degrees(np.arctan2(interp_s(q), interp_c(q))).reshape(full_shape) % 360

        if channel != "full":
            r_map = r_map[row_off::2, col_off::2]
            theta_map = theta_map[row_off::2, col_off::2]

        return PixelAngleLookup(r_map, theta_map, channel)
    
    def pixel_to_angle(
        self,
        x: np.ndarray | list[float] | float,
        y: np.ndarray | list[float] | float,
        *,
        channel: config.ChannelName | None = None,
        max_iter: int = 6,
        eps: float = 1e-3,
    ) -> tuple[float, float] | tuple[np.ndarray, np.ndarray]:
        """
        Convert pixel coordinates to angular coordinates.

        Uses a fast Newton-style numerical inversion of the forward model.

        Parameters
        ----------
        x, y : :class:`np.ndarray` | :class:`list` of :class:`float` | :class:`float`
            Pixel coordinates. If ``channel`` is provided, these are interpreted as
            channel-plane coordinates and converted to full Bayer-frame coordinates.
            Otherwise, they are interpreted as full Bayer-frame coordinates.

        channel : :class:`~config.ChannelName`, optional
            If specified, applies the appropriate Bayer offsets for the given channel.

        max_iter : :class:`int`
            Number of Newton iterations.

        eps : :class:`float`
            Step size for finite differences.

        Returns
        -------
        :class:`tuple`
            ``(r_deg, theta_deg)``. If scalar inputs are provided, both values are
            returned as :class:`float`. If array-like inputs are provided, both values
            are returned as 1D :class:`numpy.ndarray`.

        Raises
        ------
        ValueError
            If input shapes are invalid.
        """

        x_was_scalar = np.isscalar(x)
        y_was_scalar = np.isscalar(y)

        x = np.atleast_1d(np.asarray(x, dtype=float))
        y = np.atleast_1d(np.asarray(y, dtype=float))

        if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
            raise ValueError("x and y must be scalars or 1D arrays of the same shape.")

        scalar_output = x_was_scalar and y_was_scalar

        if channel is not None:
            row_off, col_off = config.get_channel_bayer_offsets(channel)
            x_full = x * 2.0 + col_off
            y_full = y * 2.0 + row_off
        else:
            x_full = x
            y_full = y

        dx = x_full - self.cx
        dy = y_full - self.cy

        theta = (np.degrees(np.arctan2(dy, dx)) - self.theta0_deg) % 360.0
        rho = np.hypot(dx, dy)

        # Initial radial guess from approximate equidistant projection.
        k1 = self.params[3]
        if k1 != 0:
            r = np.degrees(rho / k1)
        else:
            r = np.full_like(rho, self.config.r_nom_max_deg / 2.0)

        r = np.clip(r, 0.0, self.config.r_nom_max_deg)

        # --- Newton iterations ---
        for _ in range(max_iter):
            xp, yp = self.angular_to_pixel(r, theta)

            fx = xp - x_full
            fy = yp - y_full

            converged = (np.abs(fx) + np.abs(fy)) < 1e-3
            if np.all(converged):
                break

            # Finite-difference Jacobian.
            xp_r, yp_r = self.angular_to_pixel(r + eps, theta)
            xp_t, yp_t = self.angular_to_pixel(r, theta + eps)

            j11 = (xp_r - xp) / eps
            j21 = (yp_r - yp) / eps
            j12 = (xp_t - xp) / eps
            j22 = (yp_t - yp) / eps

            det = j11 * j22 - j12 * j21

            valid = (~converged) & np.isfinite(det) & (np.abs(det) > 1e-12)

            if not np.any(valid):
                break

            # Solve 2x2 systems analytically for each point:
            #
            # [j11 j12] [dr    ] = [fx]
            # [j21 j22] [dtheta]   [fy]
            dr = np.zeros_like(r)
            dtheta = np.zeros_like(theta)

            dr[valid] = (
                j22[valid] * fx[valid] - j12[valid] * fy[valid]
            ) / det[valid]

            dtheta[valid] = (
                -j21[valid] * fx[valid] + j11[valid] * fy[valid]
            ) / det[valid]

            r[valid] -= dr[valid]
            theta[valid] -= dtheta[valid]

            r = np.clip(r, 0.0, self.config.r_nom_max_deg)
            theta = theta % 360.0

        if scalar_output:
            return float(r[0]), float(theta[0])

        return r, theta

# =============================================================================
# Visualization helpers
# =============================================================================


def make_coordinate_formatter(lookup: PixelAngleLookup):
    """
    Create a Matplotlib coordinate formatter with angular info.
    """

    def fmt(x, y):
        r, t = lookup.sample(np.array([x]), np.array([y]))
        if not np.isfinite(r[0]):
            return f"x={x:.1f}, y={y:.1f}"
        return f"x={x:.1f}, y={y:.1f}, r={r[0]:.2f}°, θ={t[0]:.2f}°"

    return fmt


def make_plotly_hover_function(lookup: PixelAngleLookup):
    """
    Return a function usable inside Plotly callbacks to compute angular coords.

    Example usage:
        hover_fn = make_plotly_hover_function(lookup)
        r, theta = hover_fn(x, y)
    """

    def fn(x, y):
        r, t = lookup.sample(np.array([x]), np.array([y]))
        return float(r[0]), float(t[0])

    return fn