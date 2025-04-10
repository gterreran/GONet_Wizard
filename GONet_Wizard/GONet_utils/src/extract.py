from dataclasses import dataclass
import numpy as np

@dataclass
class extraction_output:
    total_counts: float
    mean_counts: float
    std: float
    npixels: int

def extract_circle(data: np.ndarray, x0: float, y0: float, radius: float) -> extraction_output:
    y = np.arange(0,data.shape[0])
    x = np.arange(0,data.shape[1])
    mask = (x[np.newaxis,:]-x0)**2 + (y[:,np.newaxis]-y0)**2 < radius**2
    return extraction_output(
        total_counts = np.sum(data[mask]),
        mean_counts = np.mean(data[mask]),
        std = np.std(data[mask]),
        npixels = len(data[mask])
    )