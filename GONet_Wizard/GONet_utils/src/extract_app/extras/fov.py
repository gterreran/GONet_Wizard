import matplotlib.pyplot as plt

import numpy as np
from numpy.linalg import lstsq
from scipy import ndimage as ndi
from scipy.special import erf, erfinv
from GONet_Wizard.logging_utils import get_logger

logger = get_logger(__name__)

# ------------------------- Stats helpers -------------------------

def _plot_mask_overlay(image: np.ndarray, mask: np.ndarray, pts: np.ndarray, title: str = "Cleaned + LCC mask") -> None:
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].imshow(image, origin="lower")
    y, x = zip(*pts)
    ax[0].plot(x,y, 'r.', markersize=1)
    ax[0].set_title(title + " (over image)")
    ax[1].imshow(mask, origin="lower", cmap="gray")
    ax[1].set_title(title + " (binary)")
    plt.tight_layout()

def _p_to_intensity_gauss(p_star: float, mu: float, sigma: float, tail: str = "high"):
    """
    Map an FDR p* to an intensity cutoff x_cut under N(mu, sigma^2).
    Returns (x_cut, z), where z = (x_cut - mu)/sigma.
    """
    sigma = max(float(sigma), 1e-12)
    if tail == "high":
        # p = 1 - Phi(z) => z = Phi^{-1}(1 - p) = sqrt(2)*erfinv(1 - 2p)
        z = np.sqrt(2.0) * erfinv(1.0 - 2.0 * p_star)
    else:
        # p = Phi(z) => z = Phi^{-1}(p) = sqrt(2)*erfinv(2p - 1)
        z = np.sqrt(2.0) * erfinv(2.0 * p_star - 1.0)
    x_cut = mu + sigma * z
    return float(x_cut), float(z)

def _median_z(x_cut: float, vals_bg: np.ndarray):
    """
    z-score relative to median using MAD-scaled sigma (robust).
    Returns (z_med, med, sigma_mad).
    """
    vb = np.asarray(vals_bg, float).ravel()
    med = float(np.median(vb))
    mad = float(np.median(np.abs(vb - med)))
    sigma_mad = 1.4826 * mad if mad > 0 else float(np.std(vb, ddof=1) or 1.0)
    z_med = (x_cut - med) / max(sigma_mad, 1e-12)
    return float(z_med), med, sigma_mad

def _count_threshold(image: np.ndarray, x_cut: float, tail: str = "high", mask: np.ndarray | None = None):
    """
    Count pixels beyond the cutoff in the whole image and (optionally) in a mask.
    Returns (n_img, frac_img, n_mask, frac_mask).
    """
    img = np.asarray(image, float)
    finite = np.isfinite(img)
    if tail == "high":
        sel_img = finite & (img >= x_cut)
    else:
        sel_img = finite & (img <= x_cut)
    n_img = int(sel_img.sum())
    frac_img = n_img / float(finite.sum() or 1)

    if mask is not None:
        mfin = finite & mask
        if tail == "high":
            sel_m = mfin & (img >= x_cut)
        else:
            sel_m = mfin & (img <= x_cut)
        n_m = int(sel_m.sum())
        frac_m = n_m / float(mfin.sum() or 1)
    else:
        n_m, frac_m = 0, 0.0

    return n_img, frac_img, n_m, frac_m

def _pvals_from_noise(image: np.ndarray, noise_cdf, tail: str = "high") -> np.ndarray:
    """
    One-sided p-values under H0 = noise. If illumination is brighter than noise,
    use tail='high' (default). If darker, use tail='low'.
    """
    F = noise_cdf(image)
    if tail == "high":
        p = 1.0 - F
    else:
        p = F
    # Avoid exact zeros to keep logs stable
    return np.clip(p, 1e-16, 1.0)

def _bh_threshold(pvals: np.ndarray, q: float) -> float:
    """
    Benjamini–Hochberg FDR threshold for an array of p-values.
    Returns the p-value cutoff; anything <= cutoff is "discovery".
    """
    pv = np.sort(pvals.ravel())
    m = pv.size
    ranks = np.arange(1, m + 1)
    crit = ranks * q / m
    mask = pv <= crit
    if not np.any(mask):
        # No discoveries at this q; fall back to min p to allow a seed
        return pv[0] * 0.99
    k = np.max(np.where(mask)[0])
    return pv[k]

def _fit_gaussian_sigma_clipped(
    vals: np.ndarray,
    clip_sigma: float = 3.0,
    max_iter: int = 8,
    tol: float = 1e-3
) -> tuple[float, float, int]:
    """
    Iterative sigma clipping under a Gaussian assumption.
    Returns (mu, sigma, n_kept).

    Notes
    -----
    - Starts with robust (median/MAD) then iterates mean/std on clipped set.
    - Falls back gracefully if sigma collapses.
    """
    v = np.asarray(vals, float).ravel()
    if v.size == 0:
        raise ValueError("No samples provided for sigma clipping.")

    med = np.median(v)
    mad = np.median(np.abs(v - med))
    sigma0 = 1.4826 * mad if mad > 0 else np.std(v)
    mu = float(med)
    sigma = float(sigma0 if sigma0 > 0 else (np.std(v) or 1.0))

    kept = np.ones_like(v, dtype=bool)

    for _ in range(max_iter):
        prev_mu, prev_sigma = mu, sigma
        kept = np.abs(v - mu) <= clip_sigma * max(sigma, 1e-12)
        if kept.sum() < 5:
            break
        mu = float(v[kept].mean())
        sigma = float(v[kept].std(ddof=1))
        if sigma <= 1e-12:
            sigma = float(np.std(v) or 1.0)
        # relative change small? stop
        dmu = abs(mu - prev_mu)
        dsig = abs(sigma - prev_sigma) / max(prev_sigma, 1e-12)
        if dmu < tol and dsig < tol:
            break

    return mu, sigma, int(kept.sum())


def _gaussian_cdf_factory(mu: float, sigma: float):
    """
    Make a vectorized Gaussian CDF with given parameters.
    """
    sigma = max(float(sigma), 1e-12)
    inv = 1.0 / (sigma * np.sqrt(2.0))
    def cdf(v: np.ndarray) -> np.ndarray:
        return 0.5 * (1.0 + erf((v - mu) * inv))
    return cdf


# ------------------------- Morphology / connectivity -------------------------

def _clean_and_lcc(mask: np.ndarray, min_hole: int = 64, min_object: int = 64) -> np.ndarray:
    """
    Binary clean-up + Largest Connected Component extraction.
    """
    # Fill small holes then open/close a bit for coherence
    mask = ndi.binary_fill_holes(mask)
    mask = ndi.binary_opening(mask, structure=np.ones((3,3)))
    mask = ndi.binary_closing(mask, structure=np.ones((3,3)))
    # Remove tiny specks by labeling
    lbl, n = ndi.label(mask)
    if n == 0:
        return np.zeros_like(mask, bool)
    sizes = np.bincount(lbl.ravel())
    sizes[0] = 0
    keep = np.argmax(sizes)
    return lbl == keep

# ------------------------- Circle fitting -------------------------

def _circle_fit_least_squares(yx: np.ndarray):
    """
    Algebraic center from linear LS (no extra /2); robust geometric radius.
    Points are [N,2] in (y,x). Returns (yc, xc, r).
    """
    if yx.shape[0] < 3:
        raise ValueError("Need at least 3 points for circle fit")

    y = yx[:, 0].astype(float)
    x = yx[:, 1].astype(float)

    # Model: x^2 + y^2 = 2*a*x + 2*b*y + c  ->  A@[a,b,c] = bvec
    A = np.c_[2.0 * x, 2.0 * y, np.ones_like(x)]
    bvec = x**2 + y**2

    a, b, c0 = lstsq(A, bvec, rcond=None)[0]  # <-- a=xc, b=yc directly
    xc = float(a)
    yc = float(b)

    # Geometric radius from mean distance (robust & nonnegative)
    d = np.hypot(x - xc, y - yc)
    r_geom = float(np.mean(d))

    if np.isfinite(r_geom) and r_geom > 0:
        r = r_geom
    else:
        r2 = float(c0 + xc**2 + yc**2)
        r = float(np.sqrt(max(r2, 0.0)))

    return yc, xc, r


def _circle_from_3pts(p1, p2, p3):
    """
    Circle through 3 points (y,x). Returns (yc, xc, r). Raises on degeneracy.
    """
    (y1, x1), (y2, x2), (y3, x3) = map(lambda p: (float(p[0]), float(p[1])), (p1, p2, p3))
    A = np.array([[x2 - x1, y2 - y1],
                  [x3 - x1, y3 - y1]], float)
    B = 0.5 * np.array([x2**2 - x1**2 + y2**2 - y1**2,
                        x3**2 - x1**2 + y3**2 - y1**2], float)
    det = np.linalg.det(A)
    if abs(det) < 1e-12:
        raise ValueError("Nearly collinear points")
    xc, yc = np.linalg.solve(A, B)
    r = np.hypot(x1 - xc, y1 - yc)
    return yc, xc, r

def _ransac_circle(yx: np.ndarray, n_iter: int = 300, inlier_tol: float = 2.5, min_inliers: int = 100):
    """
    RANSAC circle fit for robustness. Returns (yc, xc, r, inlier_mask).
    """
    rng = np.random.default_rng(42)
    N = yx.shape[0]
    best = (None, -1, None)  # (params, inliers_count, mask)
    if N < 3:
        raise ValueError("Not enough points for RANSAC circle")
    for _ in range(n_iter):
        idx = rng.choice(N, size=3, replace=False)
        try:
            yc, xc, r = _circle_from_3pts(yx[idx[0]], yx[idx[1]], yx[idx[2]])
        except Exception:
            continue
        dy = yx[:, 0] - yc
        dx = yx[:, 1] - xc
        dist = np.abs(np.hypot(dy, dx) - r)
        inliers = dist <= inlier_tol
        n_in = int(inliers.sum())
        if n_in > best[1] and n_in >= min_inliers:
            best = ((yc, xc, r), n_in, inliers)
    if best[0] is None:
        # Fall back to plain least squares on all points
        yc, xc, r = _circle_fit_least_squares(yx)
        dy = yx[:, 0] - yc
        dx = yx[:, 1] - xc
        dist = np.abs(np.hypot(dy, dx) - r)
        inliers = dist <= inlier_tol
        return yc, xc, r, inliers
    # Refine on inliers
    # Refine on inliers
    yc, xc, r = _circle_fit_least_squares(yx[best[2]])
    if not (np.isfinite(yc) and np.isfinite(xc) and np.isfinite(r) and r > 0):
        # Fallback: estimate radius from median distance to center on inliers
        d_in = np.hypot(yx[best[2],0] - yc, yx[best[2],1] - xc)
        r = float(np.median(d_in))
    dy = yx[:, 0] - yc
    dx = yx[:, 1] - xc
    dist = np.abs(np.hypot(dy, dx) - r)
    inliers = dist <= inlier_tol
    return yc, xc, r, inliers


def _plot_background_overlay(image: np.ndarray, bg_mask: np.ndarray) -> None:
    """
    Show the image with the provided background (non-illuminated) mask overlaid.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(image, origin="lower")
    # Red translucent overlay where bg_mask is True
    overlay = np.ma.masked_where(~bg_mask, bg_mask)
    ax.imshow(overlay, origin="lower", alpha=0.35, cmap="Reds")
    ax.set_title("Sanity check: image + background (non-illuminated) region")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()


def _plot_noise_stats(
    image: np.ndarray,
    bg_mask: np.ndarray,
    p_star: float | None = None,
    tail: str = "high",
    mu: float | None = None,
    sigma: float | None = None
) -> None:
    """
    Plot noise histogram + ECDF from the background region, with optional
    Gaussian fit overlay (mu, sigma). If p_star is given, mark the implied
    intensity cutoff under that Gaussian model.
    """
    vals = image[bg_mask].astype(float).ravel()
    vals_sorted = np.sort(vals)
    n = vals_sorted.size
    ecdf = np.arange(1, n + 1) / n

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Histogram (+ Gaussian PDF overlay if available)
    ax = axes[0]
    counts, bins, _ = ax.hist(vals, bins=100, histtype="stepfilled", alpha=0.8)
    ax.set_title("Noise histogram (background ROI)")
    ax.set_xlabel("Intensity")
    ax.set_ylabel("Count")

    mu_emp = float(np.mean(vals))
    sig_emp = float(np.std(vals))
    med = float(np.median(vals))
    ax.text(0.02, 0.98, f"empirical:\nmean={mu_emp:.2f}\nmedian={med:.2f}\nstd={sig_emp:.2f}",
            transform=ax.transAxes, va="top", ha="left", fontsize=9,
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))

    if (mu is not None) and (sigma is not None) and sigma > 0:
        # Overlay Gaussian PDF scaled to histogram area
        binw = np.diff(bins).mean()
        xpdf = np.linspace(bins[0], bins[-1], 512)
        # Gaussian PDF
        pdf = np.exp(-0.5 * ((xpdf - mu)/sigma)**2) / (sigma * np.sqrt(2*np.pi))
        pdf_scaled = pdf * (vals.size * binw)
        ax.plot(xpdf, pdf_scaled, lw=2, label=f"Gaussian fit μ={mu:.2f}, σ={sigma:.2f}")
        ax.legend(loc="best")

    # ECDF (+ Gaussian CDF overlay if available)
    ax = axes[1]
    ax.plot(vals_sorted, ecdf, lw=2, label="Empirical ECDF")
    ax.set_title("Noise ECDF (background ROI)")
    ax.set_xlabel("Intensity")
    ax.set_ylabel("F(noise ≤ x)")

    if (mu is not None) and (sigma is not None) and sigma > 0:
        xcdf = np.linspace(vals_sorted[0], vals_sorted[-1], 512)
        cdf_g = 0.5 * (1.0 + erf((xcdf - mu)/(sigma*np.sqrt(2))))
        ax.plot(xcdf, cdf_g, lw=2, linestyle="--", label="Gaussian CDF (fit)")
        ax.legend(loc="best")

    # If we know the FDR p*, show implied intensity cutoff under the Gaussian
    if (p_star is not None) and (mu is not None) and (sigma is not None) and sigma > 0:
        qtile = (1.0 - p_star) if tail == "high" else p_star
        qtile = float(np.clip(qtile, 0.0, 1.0))
        # Inverse Gaussian CDF via erfinv
        x_cut = mu + sigma * np.sqrt(2.0) * erfinv(2.0 * qtile - 1.0)
        ax.axvline(x_cut, ls="--")
        ax.text(0.02, 0.05, f"p*={p_star:.2e} ⇒ intensity≈{x_cut:.2f}",
                transform=ax.transAxes, va="bottom", ha="left", fontsize=9,
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))

    plt.tight_layout()



def _plot_probability_map(
    image: np.ndarray,
    score: np.ndarray,
    mask: np.ndarray,
    center: tuple,
    radius: float
) -> None:
    """
    Show the -log10 p map, with the FDR mask contour and the fitted circle.
    """
    yc, xc = center
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))

    # Left: image with fitted circle
    ax0 = ax[0]
    im0 = ax0.imshow(image, origin="lower")
    circ = plt.Circle((xc, yc), radius, fill=False, linewidth=2)
    ax0.add_patch(circ)
    ax0.set_title("Image + fitted circle")
    fig.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04)

    # Right: probability/score map
    ax1 = ax[1]
    # Clip extreme values for display
    vmax = np.nanpercentile(score, 99.5)
    im1 = ax1.imshow(np.nan_to_num(score), origin="lower", vmax=vmax)
    ax1.contour(mask, levels=[0.5], linewidths=1.5)
    circ2 = plt.Circle((xc, yc), radius, fill=False, linewidth=2)
    ax1.add_patch(circ2)
    ax1.set_title(r"Score map  $-\log_{10} p_{\rm noise}$  + FDR mask")
    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

    plt.tight_layout()


# ------------------------- Main pipeline -------------------------

def detect_fov(
    image: np.ndarray,
    bg_mask: np.ndarray,
    q: float = 1e-3,
    tail: str = "high",
    max_iter: int = 5,
    tol: float = 1e-3,
    min_object: int = 64,
    verbose: bool = False,
    return_debug: bool = True,
    clip_sigma: float = 3.0,
) -> dict:
    """
    Segment a roughly circular illuminated region using noise statistics,
    spatial coherence, and a circle prior. Iteratively refines the result,
    starting from a user-provided background (non-illuminated) mask.

    Parameters
    ----------
    image : np.ndarray
        2D array of intensities.
    bg_mask : np.ndarray
        Boolean mask selecting pixels that are *definitely* non-illuminated.
    q : float
        Target FDR rate (Benjamini–Hochberg).
    tail : str
        'high' if illuminated pixels are brighter than noise, 'low' if darker.
    max_iter : int
        Max refinement iterations.
    tol : float
        Convergence tolerance on relative radius change.
    min_object : int
        Minimum object size (pixels) to keep during cleaning.
    verbose : bool
        If True, prints step-by-step logs (thresholds, circle params, etc.).
    return_debug : bool
        If True, includes a 'debug' key with intermediate artifacts.

    Returns
    -------
    dict
        {
          'mask': np.ndarray (bool),
          'score': np.ndarray (float),      # -log10(p_noise) from final iteration
          'center': (float, float),         # (yc, xc)
          'radius': float,
          'converged': bool,
          'iterations': int,
          'debug': dict  # present if return_debug=True
        }
    """
    if image.ndim != 2:
        raise ValueError("image must be 2D")
    if not np.any(bg_mask):
        raise ValueError("bg_mask must contain at least one True pixel")

    H, W = image.shape
    yy, xx = np.indices((H, W))

    dbg = {
        "bg_count": int(bg_mask.sum()),
        "q": float(q),
        "tail": tail,
        "init": {},
        "iters": []
    }

    if verbose:
        logger.info("[init] bg pixels=%s, q=%g, tail=%r", dbg["bg_count"], q, tail)

    # --- Initial noise model from provided background (sigma-clipped Gaussian)
    vals0 = image[bg_mask]
    mu0, sig0, n0 = _fit_gaussian_sigma_clipped(vals0, clip_sigma=clip_sigma)
    noise_cdf = _gaussian_cdf_factory(mu0, sig0)
    if verbose:
        logger.info("[init] noise μ=%.3f, σ=%.3f (kept %s/%s)", mu0, sig0, n0, vals0.size)

    # --- Per-pixel p-values and scores
    p = _pvals_from_noise(image, noise_cdf, tail=tail)
    score = -np.log10(p)

    # --- Initial FDR and mask
    thr = _bh_threshold(p, q=q)
    mask = p <= thr
    # Map p* -> intensity & z, and print counts
    x_cut0, z0 = _p_to_intensity_gauss(thr, mu0, sig0, tail=tail)
    n_all0, f_all0, n_bg0, f_bg0 = _count_threshold(image, x_cut0, tail=tail, mask=bg_mask)
    z_med0, med0, sigmad0 = _median_z(x_cut0, image[bg_mask])

    if verbose:
        logger.info("[init] FDR p*=%.3e discoveries=%s (%.2f%%)", thr, int(mask.sum()), 100 * mask.mean())
        logger.info(
            "[init] p*→ intensity≈%.3f z_mu=%.2fσ z_med=%.2fσ (μ=%.2f, σ=%.2f, med=%.2f, σ_MAD=%.2f)",
            x_cut0, z0, z_med0, mu0, sig0, med0, sigmad0,
        )
        logger.info(
            "[init] counts: image %s/%s (%.2f%%) bgROI %s/%s (%.2f%%)",
            n_all0, image.size, 100 * f_all0, n_bg0, int(bg_mask.sum()), 100 * f_bg0,
        )

    # --- Spatial coherence & LCC
    mask = _clean_and_lcc(mask)

    # --- Initial circle fit from boundary
    er = ndi.binary_erosion(mask, structure=np.ones((3,3)))
    boundary = mask ^ er
    pts = np.column_stack(np.nonzero(boundary))

    if pts.shape[0] < 20:
        pts = np.column_stack(np.nonzero(mask))
    yc, xc, r, inliers = _ransac_circle(pts, n_iter=400, inlier_tol=2.5, min_inliers=50)

    if verbose:
        logger.info("[init] circle: yc=%.2f, xc=%.2f, r=%.2f (boundary pts=%s)", yc, xc, r, pts.shape[0])

    dbg["init"] = {
        "thr": float(thr),
        "mask_sum": int(mask.sum()),
        "circle": (float(yc), float(xc), float(r)),
        "mask_clean": mask,
        "pts": pts
    }

    prev_r = r
    converged = False
    last_thr = float(thr)

    for it in range(1, max_iter + 1):
        # Update background from OUTSIDE current circle
        dist = np.hypot(yy - yc, xx - xc)
        new_bg = dist > (r + 2.0)

        if not np.any(new_bg):
            if verbose:
                logger.info("[iter %s] No outside-of-circle background left; stopping.", it)
            break

        vals_bg = image[new_bg]
        mu_i, sig_i, n_i = _fit_gaussian_sigma_clipped(vals_bg, clip_sigma=clip_sigma)
        noise_cdf = _gaussian_cdf_factory(mu_i, sig_i)
        p = _pvals_from_noise(image, noise_cdf, tail=tail)
        score = -np.log10(p)

        thr = _bh_threshold(p, q=q)
        x_cuti, zi = _p_to_intensity_gauss(thr, mu_i, sig_i, tail=tail)
        n_alli, f_alli, n_bgi, f_bgi = _count_threshold(image, x_cuti, tail=tail, mask=bg_mask)
        z_medi, medi, sigmadi = _median_z(x_cuti, image[bg_mask])

        if verbose:
            logger.info(
                "[iter %s] p*→ intensity≈%.3f z_mu=%.2fσ z_med=%.2fσ (μ=%.2f, σ=%.2f, med=%.2f, σ_MAD=%.2f)",
                it, x_cuti, zi, z_medi, mu_i, sig_i, medi, sigmadi,
            )
            logger.info(
                "[iter %s] counts: image %s/%s (%.2f%%) bgROI %s/%s (%.2f%%)",
                it, n_alli, image.size, 100 * f_alli, n_bgi, int(bg_mask.sum()), 100 * f_bgi,
            )
        last_thr = float(thr)
        mask = p <= thr
        mask = _clean_and_lcc(mask)
        if return_debug:
            # ensure the current iteration dict exists; append later details after fit
            dbg["iters"].append({"mask_clean": mask.copy()})

        # Refit circle
        er = ndi.binary_erosion(mask, structure=np.ones((3,3)))
        boundary = mask ^ er
        pts = np.column_stack(np.nonzero(boundary))
        if pts.shape[0] < 20:
            pts = np.column_stack(np.nonzero(mask))
        yc, xc, r, inliers = _ransac_circle(pts, n_iter=400, inlier_tol=2.5, min_inliers=50)

        rel = abs(r - prev_r) / max(prev_r, 1e-12)
        if verbose:
            logger.info(
                "[iter %s] FDR p*=%.3e mask=%s px circle: yc=%.2f, xc=%.2f, r=%.2f Δr=%.2e",
                it, thr, int(mask.sum()), yc, xc, r, rel,
            )

        dbg["iters"].append({
            "thr": float(thr),
            "mask_sum": int(mask.sum()),
            "circle": (float(yc), float(xc), float(r)),
            "rel_dr": float(rel)
        })

        if rel < tol:
            converged = True
            if verbose:
                logger.info("[iter %s] Converged (Δr<%s).", it, tol)
            break
        prev_r = r

    # Final: inside circle → mask (clean to remove jaggies)
    final_inside = (np.hypot(yy - yc, xx - xc) <= r)
    final_mask = _clean_and_lcc(final_inside)

    out = {
        "mask": final_mask,
        "score": score,
        "x0": float(xc),
        "y0": float(yc),
        "radius": float(r),
        "converged": bool(converged),
        "iterations": it if 'it' in locals() else 0,
    }
    if return_debug:
        out["debug"] = {
            **dbg,
            "last_thr": last_thr
        }
    return out

def _ring_mask(yc: float, xc: float, r: float, shape, band: int = 3) -> np.ndarray:
    """
    Annulus mask (r - band <= d <= r + band) centered at (yc, xc).
    """
    H, W = shape
    yy, xx = np.indices((H, W))
    d = np.hypot(yy - yc, xx - xc)
    return (d >= (r - band)) & (d <= (r + band))

def channel_ring_weight(score: np.ndarray, center: tuple, radius: float, band: int = 3) -> float:
    """
    Robust channel 'quality' weight: median score on a thin ring around the fitted circle.
    Higher is better. Returns 0 if ring has no pixels.
    """
    yc, xc = center
    m = _ring_mask(yc, xc, radius, score.shape, band=band)
    if not np.any(m):
        return 0.0
    vals = np.asarray(score[m], float)
    if vals.size == 0 or not np.isfinite(vals).any():
        return 0.0
    return float(np.nanmedian(vals))

def fuse_circles_weighted(results: dict, max_center_sep: float = 50.0) -> dict:
    """
    Weighted fusion of (yc, xc, r) from multiple channels.
    
    Parameters
    ----------
    results : dict
        Mapping like {'r': res_r, 'g': res_g, 'b': res_b}, where each res_* is the
        dict returned by `segment_illuminated_circle`, and includes keys:
        - 'center' -> (yc, xc)
        - 'radius' -> float
        - 'score'  -> 2D array (-log10 p)
    max_center_sep : float
        If a channel's center is farther than this (pixels) from the median center,
        drop it as an outlier.

    Returns
    -------
    dict
        {'center': (yc, xc), 'radius': r, 'weights': {ch: w}, 'used_channels': [..]}
    """
    # 1) compute weights per channel from ring scores
    stats = []
    for ch, res in results.items():
        yc     = res["y0"]
        xc     = res["x0"]
        r      = res["radius"]
        w      = channel_ring_weight(res["score"], (yc, xc), r, band=3)
        stats.append((ch, yc, xc, r, w))

    # 2) reject outliers by center distance
    ycs = np.array([s[1] for s in stats], float)
    xcs = np.array([s[2] for s in stats], float)
    med_center = (float(np.median(ycs)), float(np.median(xcs)))
    keep = []
    for s in stats:
        _, yc, xc, r, w = s
        d = float(np.hypot(yc - med_center[0], xc - med_center[1]))
        if d <= max_center_sep and np.isfinite(w) and w > 0:
            keep.append(s)

    if not keep:
        # Fallback: use the channel with the highest weight overall
        keep = [max(stats, key=lambda s: s[4])]

    # 3) normalize weights and compute weighted averages
    ws   = np.array([s[4] for s in keep], float)
    wsum = float(ws.sum()) if np.isfinite(ws).all() and ws.sum() > 0 else 1.0
    ws   = ws / wsum

    ycs  = np.array([s[1] for s in keep], float)
    xcs  = np.array([s[2] for s in keep], float)
    rs   = np.array([s[3] for s in keep], float)

    yc_f = float(np.dot(ws, ycs))
    xc_f = float(np.dot(ws, xcs))
    r_f  = float(np.dot(ws, rs))

    return {
        "x0": xc_f,
        "y0": yc_f,
        "radius": r_f,
        "weights": {s[0]: float(wi) for s, wi in zip(keep, ws)},
        "used_channels": [s[0] for s in keep],
        "median_center": med_center,
    }


