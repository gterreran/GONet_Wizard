"""
Plotting Utilities for GONet File Visualization.

This module provides functions to visualize GONet image files,
optionally saving figures and selecting specific RGB channels to display.
The main function :func:`show` is meant to be used as a command-line tool.

**Functions**

- :func:`create_efficient_subplots` : Create optimized subplot grids for multiple channels.
- :func:`save_figure` : Save matplotlib figures to disk with auto-incremented filenames.
- :func:`auto_vmin_vmax` : Automatically scale image intensity using robust percentiles.
- :func:`show` : Main interface to plot GONet files and optionally save the output.

"""

from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
import matplotlib.pyplot as plt
import math, os
import numpy as np
from typing import Union, List


def create_efficient_subplots(N: int, figsize: tuple = (10, 6)) -> tuple:
    """
    Create a compact grid of subplots for displaying multiple images.

    Automatically chooses the number of rows and columns based on the number of
    plots required. Removes any unused axes to avoid blank spaces.

    Parameters
    ----------
    N : :class:`int`
        The number of subplots needed.
    figsize : :class:`tuple`, optional
        Size of the entire figure in inches (width, height).

    Returns
    -------
    :class:`tuple`
        A tuple of `(fig, axes)` where:
        - `fig` is the matplotlib Figure
        - `axes` is a list of Axes objects (length N)
    """
    if N <= 0:
        raise ValueError("N must be at least 1 to create subplots.")

    rows = int(math.sqrt(N))
    cols = math.ceil(N / rows)

    fig, axes = plt.subplots(rows, cols, figsize=figsize)

    if N == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for i in range(N, len(axes)):
        fig.delaxes(axes[i])

    return fig, axes[:N]


def save_figure(fig: plt.Figure, save_path: str) -> None:
    """
    Save a matplotlib figure to a PDF file, avoiding overwrites.

    If a file with the same name already exists, appends a counter to the filename.

    Parameters
    ----------
    fig : :class:`matplotlib.figure.Figure`
        The figure to be saved.
    save_path : :class:`str`
        The target filename (with or without `.pdf` extension).

    Returns
    -------
    None
    """
    if not save_path.lower().endswith('.pdf'):
        save_path += '.pdf'

    base, ext = os.path.splitext(save_path)
    counter = 1
    final_path = save_path

    while os.path.exists(final_path):
        final_path = f"{base}_{counter}{ext}"
        counter += 1

    fig.savefig(final_path, bbox_inches='tight')
    print(f"✅ Figure saved to {final_path}")


def auto_vmin_vmax(data: np.ndarray, lower_percentile: float = 0.5, upper_percentile: float = 99.5) -> tuple:
    """
    Compute intensity bounds for image display using percentiles.

    Parameters
    ----------
    data : :class:`numpy.ndarray`
        The image data array.
    lower_percentile : :class:`float`, optional
        The lower percentile for clipping (default is 0.5).
    upper_percentile : :class:`float`, optional
        The upper percentile for clipping (default is 99.5).

    Returns
    -------
    :class:`tuple`
        A tuple `(vmin, vmax)` suitable for image display scaling.
    """
    vmin = np.percentile(data, lower_percentile)
    vmax = np.percentile(data, upper_percentile)
    return vmin, vmax

def show_gonet_files(files: Union[str, List[str]], save: bool = False, red: bool = False, green: bool = False, blue: bool = False) -> None:
    """
    Display one or more GONet image files with optional channel filtering and saving.

    This function loads and visualizes GONet files using matplotlib. By default, 
    all RGB channels are displayed unless specific channels are enabled via flags. 
    Images are arranged in a compact grid. If `save` is specified, the resulting figure 
    is saved to a PDF file with automatic filename disambiguation.

    Parameters
    ----------
    files : :class:`str` or :class:`list` of :class:`str`
        A single file path or a list of paths to GONet files to display.
    save : :class:`bool`, optional
        If provided, saves the resulting figure to a `.pdf` file (default is False).
        The filename or path can be passed as the value of `save`.
    red : :class:`bool`, optional
        Whether to include the red channel for visualization.
    green : :class:`bool`, optional
        Whether to include the green channel for visualization.
    blue : :class:`bool`, optional
        Whether to include the blue channel for visualization.

    Returns
    -------
    None

    Notes
    -----
    - If none of the color channel flags (`red`, `green`, `blue`) are set, all channels will be shown.
    - Subplot titles include camera model and timestamp when available in metadata.
    - Output intensity is automatically scaled using robust percentiles (0.5–99.5%).
    - The saved figure will be named according to `save` with automatic suffixes to avoid overwrites.
    """

    # If all extensions are false, we will plot all them
    if not any(extensions := [red, green, blue]):
        extensions =  [not el for el in extensions]

    n_of_extensions = np.sum(extensions)

    Tot = len(files) * n_of_extensions#number_of_subplots
    fig, ax = create_efficient_subplots(Tot)

    i_plot = 0

    for gof in files:
        go = GONetFile.from_file(gof)

        if go.meta and 'hostname' in go.meta:
            camera = go.meta['hostname']
        else:
            camera = ''
        if go.meta and 'DateTime' in go.meta:
            date = go.meta['DateTime']
        else:
            date = ''
        
        for c,val in zip(GONetFile.CHANNELS, extensions):
            if val:
                ax[i_plot].set_title(f'{camera} - {c}\n{date}')
                z1,z2 = auto_vmin_vmax(go.channel(c))
                ax[i_plot].imshow(go.channel(c), vmin=z1, vmax=z2)
                i_plot+=1

    plt.tight_layout()

    if save:
        save_figure(fig, save)


    plt.show()
    plt.close('all')



    