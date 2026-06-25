"""
A flexible, extensible framework for extracting structured information from
raw observational inputs (e.g., GONet camera files). The package organizes
domain-specific *extractors* into a dependency-aware pipeline and returns a
clean list of per-observation dictionaries ready for CSV/Parquet/JSON.

Overview
--------
- **Dependency-aware execution:** Each extractor declares the context it *USES*
  and *PROVIDES*. The runner executes them in a valid topological order.
- **Per-file alignment by filepath:** Extractors that operate on files return a
  ``files`` list alongside their per-file columns. Results are merged via an
  inner join on the intersection of filepaths, guaranteeing that all per-file
  arrays remain aligned—even if some extractors skip (drop) problematic files.
- **Parallel extraction where it matters:** Heavy pixel-level work (e.g.,
  aperture statistics) runs in parallel while lightweight extractors (time,
  astronomy, weather) run sequentially.
- **Serializable outputs:** Numpy types are converted to standard Python types,
  producing a list of JSON-serializable dicts (one per observation).

Public API
----------
.. autofunction:: extract_all

"""
from GONet_Wizard.GONet_utils.src.extractors.runner import extract_all
