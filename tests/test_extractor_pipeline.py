from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from GONet_Wizard.GONet_utils.src.extractors.core import Extractor, sort_extractors
from GONet_Wizard.GONet_utils.src.extractors.extraction_values import extract_counts_from_region
from GONet_Wizard.GONet_utils.src.extractors.merge import merge_extractor_into_data
from GONet_Wizard.GONet_utils.src.extractors.runner import convert_to_serializable, extract_all


@dataclass(eq=False)
class DummyExtractor(Extractor):
    name: str
    uses: list[str]
    provides: list[str]
    results: dict

    @property
    def USES(self):
        return self.uses

    @property
    def PROVIDES(self):
        return self.provides

    def extract(self, raw, context):
        context = dict(context)
        for key in self.provides:
            context[key] = self.name
        return self.results, context


def test_sort_extractors_orders_by_declared_dependencies():
    c = DummyExtractor("c", ["b"], ["c"], {})
    a = DummyExtractor("a", [], ["a"], {})
    b = DummyExtractor("b", ["a"], ["b"], {})

    ordered = sort_extractors([c, b, a])

    assert ordered == [a, b, c]


def test_sort_extractors_raises_for_unsatisfied_dependency():
    extractor = DummyExtractor("needs_missing", ["missing"], [], {})

    with pytest.raises(RuntimeError):
        sort_extractors([extractor])


def test_merge_extractor_into_data_aligns_to_intersection_in_sorted_order():
    data = {}
    merge_extractor_into_data(
        data,
        {"files": ["b", "a", "c"], "first": [2, 1, 3], "scalar": "old"},
    )
    merge_extractor_into_data(
        data,
        {"files": ["c", "a"], "second": [30, 10], "scalar": "new"},
    )

    assert data == {
        "files": ["a", "c"],
        "first": [1, 3],
        "second": [10, 30],
        "scalar": "new",
    }


def test_extract_counts_from_region_computes_region_statistics():
    data = np.arange(9).reshape(3, 3)
    mask = np.array([
        [True, False, False],
        [False, True, False],
        [False, False, True],
    ])

    result = extract_counts_from_region(data, mask)

    assert result.total_counts == 12
    assert result.mean_counts == 4
    assert result.npixels == 3
    assert result.std == pytest.approx(np.std([0, 4, 8]))


def test_convert_to_serializable_handles_common_numpy_scalars_and_arrays():
    assert convert_to_serializable(np.array([1, 2])) == [1, 2]
    assert convert_to_serializable(np.float64(1.5)) == 1.5
    assert convert_to_serializable(np.int64(2)) == 2
    assert convert_to_serializable(np.str_("x")) == "x"


def test_run_extractors_merges_results_into_records():
    first = DummyExtractor(
        "first",
        [],
        ["first_done"],
        {"files": ["a", "b"], "filename": ["a", "b"], "x": np.array([1, 2])},
    )
    second = DummyExtractor(
        "second",
        ["first_done"],
        [],
        {"files": ["b"], "y": [20], "global": "same"},
    )

    records = extract_all(
        file_list=["a", "b"],
        channels=["red"],
        extraction_params={"shape": "circle"},
        extractors=[second, first],
    )

    assert records == [{"filename": "b", "x": 2, "y": 20, "global": "same"}]
