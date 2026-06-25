from __future__ import annotations

import numpy as np
import pytest

from GONet_Wizard.GONet_utils.src.extract_app.shapes.annulus import Annulus
from GONet_Wizard.GONet_utils.src.extract_app.shapes.base import Shape, normalize_angle_deg
from GONet_Wizard.GONet_utils.src.extract_app.shapes.circle import Circle
from GONet_Wizard.GONet_utils.src.extract_app.shapes.path import Path


def test_normalize_angle_deg_maps_to_expected_range():
    assert normalize_angle_deg(0) == 0
    assert normalize_angle_deg(180) == 180
    assert normalize_angle_deg(181) == -179
    assert normalize_angle_deg(-181) == 179
    assert normalize_angle_deg(540) == 180


def test_circle_full_mask_includes_boundary_pixels():
    data = np.zeros((5, 5))
    mask = Circle(x0=2, y0=2, radius=1, start_angle=-180, end_angle=180).mask(data)

    expected = np.zeros((5, 5), dtype=bool)
    expected[2, 2] = True
    expected[1, 2] = True
    expected[2, 1] = True
    expected[2, 3] = True
    expected[3, 2] = True

    np.testing.assert_array_equal(mask, expected)


def test_circle_sector_can_wrap_across_minus_180_boundary():
    data = np.zeros((11, 11))

    mask = Circle(
        x0=5,
        y0=5,
        radius=5,
        start_angle=170,
        end_angle=-170,
    ).mask(data)

    assert mask[5, 1]      # angle 180 / -180, safely inside radius
    assert not mask[5, 9]  # angle 0, safely inside radius but outside sector


def test_annulus_mask_selects_radial_band_only_for_full_annulus():
    data = np.zeros((7, 7))
    mask = Annulus(x0=3, y0=3, inner_radius=1, outer_radius=2).mask(data)

    assert not mask[3, 3]  # center excluded by inner radius
    assert mask[1, 3]      # exactly on outer radius included
    assert mask[3, 5]
    assert not mask[0, 3]  # outside outer radius


def test_annulus_validation_rejects_bad_radii():
    with pytest.raises(ValueError):
        Annulus(x0=0, y0=0, inner_radius=2, outer_radius=1)

    with pytest.raises(ValueError):
        Annulus(x0=0, y0=0, inner_radius=0, outer_radius=1)


def test_path_mask_selects_points_inside_closed_polygon():
    data = np.zeros((5, 5))
    shape = Path("path", "M 1,1 L 3,1 L 3,3 L 1,3 Z")
    mask = shape.mask(data)

    assert mask.shape == data.shape
    assert mask[2, 2]
    assert not mask[0, 0]


def test_shape_registry_instantiates_supported_shapes():
    circle = Shape.from_dict({
        "shape": "circle",
        "x0": 2,
        "y0": 2,
        "param1": 1,
        "start_angle": -180,
        "end_angle": 180,
    })
    annulus = Shape.from_dict({
        "shape": "annulus",
        "x0": 2,
        "y0": 2,
        "param1": 1,
        "param2": 2,
        "start_angle": -180,
        "end_angle": 180,
    })

    assert isinstance(circle, Circle)
    assert isinstance(annulus, Annulus)


def test_shape_registry_rejects_unknown_and_missing_shape():
    with pytest.raises(ValueError):
        Shape.from_dict({"shape": "triangle"})

    with pytest.raises(KeyError):
        Shape.from_dict({})
