from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
import matplotlib.pyplot as plt
import math, os
import numpy as np

def create_efficient_subplots(N, figsize=(10, 6)):
    """
    Creates a nearly square grid of subplots for N plots,
    and removes any unused axes.

    Parameters:
        N (int): Number of subplots needed.
        figsize (tuple): Size of the overall figure (width, height).

    Returns:
        fig (Figure): The matplotlib figure object.
        axes (list): List of Axes objects (length N).
    """
    if N <= 0:
        raise ValueError("N must be at least 1 to create subplots.")

    rows = int(math.sqrt(N))
    cols = math.ceil(N / rows)

    fig, axes = plt.subplots(rows, cols, figsize=figsize)

    # Normalize axes to always be a 1D list
    if N == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    # Remove unused axes if any
    for i in range(N, len(axes)):
        fig.delaxes(axes[i])

    return fig, axes[:N]

def save_figure(fig, save_path):
    """
    Saves the matplotlib figure to a file.
    If the file already exists, appends a number to avoid overwriting.
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


def auto_vmin_vmax(data, lower_percentile=0.5, upper_percentile=99.5):
    vmin = np.percentile(data, lower_percentile)
    vmax = np.percentile(data, upper_percentile)
    return vmin, vmax

def show(files, save: bool = False, red: bool = False, green: bool = False, blue: bool = False) -> None:
    '''
    Plot GONet files, with the 
    
    '''

    print(red, green, blue)
    # If all extensions are false, we will plot all them
    if not any(extensions := [red, green, blue]):
        extensions =  [not el for el in extensions]
    print(extensions)
    n_of_extensions = np.sum(extensions)
    print(n_of_extensions)

    Tot = len(files) * n_of_extensions#number_of_subplots
    fig, ax = create_efficient_subplots(Tot)

    i_plot = 0

    for gof in files:
        go = GONetFile.from_file(gof)

        if 'Software' in go.meta:
            camera = go.meta['Software'].split()[0]
        else:
            camera = ''
        if 'DateTime' in go.meta:
            date = go.meta['DateTime']
        else:
            date = ''
        
        for c,val in zip(GONetFile.CHANNELS, extensions):
            if val:
                print(c)
                ax[i_plot].set_title(f'{camera} - {c}\n{date}')
                z1,z2 = auto_vmin_vmax(go.channel(c))
                ax[i_plot].imshow(go.channel(c), vmin=z1, vmax=z2)
                i_plot+=1

    plt.tight_layout()

    if save:
        save_figure(fig, save)


    plt.show()



    