"""
Core extractor framework
=========================

This module defines the abstract base class and fundamental data structures
that underpin the GONet extraction framework. It provides the base
:class:`~GONet_Wizard.GONet_utils.src.extractors.core.Extractor` interface,
which all specialized extractors inherit from, as well as lightweight utilities
for dependency management and structured output.

Overview
--------
The extraction framework is designed to process raw GONet observations through
a sequence of modular *extractors*. Each extractor is responsible for computing
a specific subset of metadata or derived quantities (e.g., time, weather,
astronomical parameters, or pixel-level statistics).

Extractors communicate through a shared *context* dictionary. To ensure they run
in the correct order, each extractor declares two class attributes:

- **USES** – A list of context keys required by the extractor.
- **PROVIDES** – A list of context keys created or updated by the extractor.

The function :func:`.sort_extractors` uses these declarations to perform a
topological sort, producing a dependency-resolved execution order that guarantees
all prerequisites are available before an extractor runs.

The module also defines a small, strongly-typed dataclass,
:class:`.extraction_output`, which encapsulates the results of circular aperture
photometric extractions (total, mean, and standard deviation of pixel values,
and the number of contributing pixels).

Responsibilities
----------------
- Define the abstract :class:`.Extractor` interface shared by all modules in
  ``GONet_Wizard.GONet_utils.src.gonet.extractors``.
- Provide type-safe containers for pixel-level measurements.
- Enable dependency-aware orchestration of extractor pipelines via
  :func:`.sort_extractors`.

**Functions**

:func:`.sort_extractors`
    Topologically sort extractors based on their declared `USES` and `PROVIDES`
    dependencies, ensuring a valid and reproducible execution sequence.

**Classes**

:class:`.Extractor`
    Abstract base class for all extractors. Subclasses must implement
    :meth:`.Extractor.extract`, declaring which context keys they use and provide.

:class:`.extraction_output`
    Lightweight dataclass representing the result of a circular aperture or
    region-based pixel extraction, including basic summary statistics.

Notes
-----
- The base :class:`.Extractor` class does not perform any data processing itself.
  It exists solely to define a consistent interface and dependency contract.
- Extractors that operate on individual files should also include a ``files``
  field in their output to allow per-file alignment during merging.
- Dependency resolution is deterministic; cycles or unsatisfied dependencies
  raise a :class:`RuntimeError`.

"""


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Set

class Extractor(ABC):
    """
    Base class for all extractors.

    The `Extractor` class provides a framework for defining modular components
    that extract structured information from raw input data and shared context.
    Subclasses must implement the `extract` method and define the `USES` and
    `PROVIDES` attributes to declare dependencies and outputs.

    Attributes
    ----------
    USES : :class:`list` of :class:`str`
        A list of context keys required by the extractor. These keys must be
        available in the shared context before the extractor runs.
    PROVIDES : :class:`list` of :class:`str`
        A list of context keys created or updated by the extractor. These keys
        are added to the shared context after the extractor runs.

    Notes
    -----
    - The `USES` and `PROVIDES` attributes are used to determine the execution
      order of extractors in a pipeline. Extractors are executed in dependency
      order, ensuring that required context keys are available before an extractor runs.
    - Subclasses should focus on extracting specific types of information, such as
      metadata, time-based data, astronomical data, weather data, or pixel statistics.
    - The `extract` method must return a tuple containing:

      - A dictionary of extracted fields.
      - The updated shared context.


    """
    USES: List[str] = []
    PROVIDES: List[str] = []

    @abstractmethod
    def extract(self, raw: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Abstract method to extract structured information from raw input and shared context.

        Subclasses must implement this method to define the logic for extracting specific
        types of information. It processes the raw input and shared context, returning
        extracted fields and the updated context.

        Parameters
        ----------
        raw : :class:`dict`
            A dictionary containing raw input data. The structure of this dictionary
            depends on the specific extractor.
        context : :class:`dict`
            A shared dictionary for intermediate results. This dictionary is updated
            with the keys defined in the `PROVIDES` attribute.

        Returns
        -------
        :class:`tuple`
            A tuple containing:

            - A dictionary of extracted fields.
            - The updated shared context.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        raise NotImplementedError


@dataclass
class extraction_output:
    """
    Container for the results of a circular aperture extraction.

    Attributes
    ----------
    total_counts : :class:`float`
        Sum of pixel values within the circular region.

    mean_counts : :class:`float`
        Average of the pixel values within the circle.

    std : :class:`float`
        Standard deviation of the pixel values.

    npixels : :class:`int`
        Number of pixels within the circular region.

    """
    total_counts: int
    mean_counts: float
    std: float
    npixels: int


def sort_extractors(extractors: List[Extractor]) -> List[Extractor]:
    """
    Topologically sort extractors based on their USES/PROVIDES dependencies.

    Parameters
    ----------
    extractors : :class:`list` of :class:`Extractor`
        Extractor instances to order.

    Returns
    -------
    :class:`list` of :class:`Extractor`
        Ordered list that respects dependency requirements.

    Raises
    ------
    :class:`RuntimeError`
        If there is a circular or unsatisfiable dependency.

    """
    provided_context: Set[str] = set()
    ordered: List[Extractor] = []
    remaining: Set[Extractor] = set(extractors)

    while remaining:
        ready = [e for e in remaining if all(req in provided_context for req in e.USES)]
        if not ready:
            raise RuntimeError("Circular or unsatisfiable dependencies detected.")
        for e in ready:
            ordered.append(e)
            provided_context.update(e.PROVIDES)
            remaining.remove(e)

    return ordered