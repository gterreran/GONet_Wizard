from __future__ import annotations

import numpy as np
import pytest

from GONet_Wizard.GONet_utils import DATA_SPEC
from GONet_Wizard.GONet_utils.src.extract_app.shapes.annulus import Annulus
from GONet_Wizard.GONet_utils.src.extract_app.shapes.base import (
    IncompleteShapeError,
    Shape,
    build_arc_path,
)
from GONet_Wizard.GONet_utils.src.extract_app.shapes.circle import Circle
from GONet_Wizard.GONet_utils.src.extract_app.shapes.path import Path


def test_build_arc_path_contains_expected_number_of_line_commands():
    path = build_arc_path(x0=10, y0=20, r=5, start_angle=0, end_angle=90, n_segments=4)

    assert path.count("L ") == 5
    assert path.startswith("L 15.0,20.0")


def test_circle_accepts_numeric_strings_and_serializes_extractor_fields():
    circle = Circle(x0="10", y0="20", radius="5", start_angle="0", end_angle="90")

    assert circle.x0 == 10.0
    assert circle.y0 == 20.0
    assert circle.radius == 5.0
    assert circle.get_extractor_field() == {
        DATA_SPEC["shape"].key: "circle",
        DATA_SPEC["x0"].key: 10.0,
        DATA_SPEC["y0"].key: 20.0,
        DATA_SPEC["radius"].key: 5.0,
        DATA_SPEC["start_angle"].key: 0.0,
        DATA_SPEC["end_angle"].key: 90.0,
    }


@pytest.mark.parametrize(
    "kwargs, exc_type",
    [
        ({"x0": None, "y0": 0, "radius": 1}, IncompleteShapeError),
        ({"x0": 0, "y0": object(), "radius": 1}, TypeError),
        ({"x0": 0, "y0": 0, "radius": 0}, ValueError),
        ({"x0": 0, "y0": 0, "radius": float("inf")}, ValueError),
    ],
)
def test_circle_validation_rejects_invalid_parameters(kwargs, exc_type):
    with pytest.raises(exc_type):
        Circle(**kwargs)


def test_circle_draw_returns_circle_for_full_region_and_path_for_sector():
    full = Circle(x0=5, y0=6, radius=2).draw()
    sector = Circle(x0=5, y0=6, radius=2, start_angle=0, end_angle=90).draw(n_segments=3)

    assert full[0]["type"] == "circle"
    assert full[0]["x0"] == 3
    assert full[0]["x1"] == 7
    assert full[0]["y0"] == 4
    assert full[0]["y1"] == 8

    assert sector[0]["type"] == "path"
    assert sector[0]["path"].startswith("M 5.0,6.0 L")
    assert sector[0]["path"].endswith("Z")


def test_circle_from_dict_uses_param1_as_radius():
    circle = Circle.from_dict({
        "x0": 1,
        "y0": 2,
        "param1": 3,
        "start_angle": 0,
        "end_angle": 180,
    })

    assert isinstance(circle, Circle)
    assert circle.radius == 3


def test_annulus_accepts_numeric_strings_and_serializes_extractor_fields():
    annulus = Annulus(
        x0="10",
        y0="20",
        inner_radius="3",
        outer_radius="6",
        start_angle="0",
        end_angle="90",
    )

    assert annulus.inner_radius == 3.0
    assert annulus.outer_radius == 6.0
    assert annulus.get_extractor_field() == {
        DATA_SPEC["shape"].key: "annulus",
        DATA_SPEC["x0"].key: 10.0,
        DATA_SPEC["y0"].key: 20.0,
        DATA_SPEC["inner_radius"].key: 3.0,
        DATA_SPEC["outer_radius"].key: 6.0,
        DATA_SPEC["start_angle"].key: 0.0,
        DATA_SPEC["end_angle"].key: 90.0,
    }


@pytest.mark.parametrize(
    "kwargs, exc_type",
    [
        ({"x0": None, "y0": 0, "inner_radius": 1, "outer_radius": 2}, IncompleteShapeError),
        ({"x0": 0, "y0": 0, "inner_radius": "bad", "outer_radius": 2}, TypeError),
        ({"x0": 0, "y0": 0, "inner_radius": -1, "outer_radius": 2}, ValueError),
        ({"x0": 0, "y0": 0, "inner_radius": 2, "outer_radius": 2}, ValueError),
    ],
)
def test_annulus_validation_rejects_invalid_parameters(kwargs, exc_type):
    with pytest.raises(exc_type):
        Annulus(**kwargs)


def test_annulus_sector_mask_respects_wrapped_angles():
    data = np.zeros((11, 11))
    mask = Annulus(
        x0=5,
        y0=5,
        inner_radius=1,
        outer_radius=5,
        start_angle=170,
        end_angle=-170,
    ).mask(data)

    assert mask[5, 1]      # angle 180 / -180, inside annular band
    assert not mask[5, 5]  # center excluded by inner radius
    assert not mask[5, 9]  # angle 0 outside wrapped sector


def test_annulus_draw_returns_two_circles_for_full_annulus_and_path_for_sector():
    full = Annulus(x0=5, y0=6, inner_radius=2, outer_radius=4).draw()
    sector = Annulus(
        x0=5,
        y0=6,
        inner_radius=2,
        outer_radius=4,
        start_angle=0,
        end_angle=90,
    ).draw(n_segments=3)

    assert [shape["type"] for shape in full] == ["circle", "circle"]
    assert full[0]["x0"] == 3
    assert full[1]["x0"] == 1

    assert sector[0]["type"] == "path"
    assert sector[0]["path"].startswith("M 9.0,6.0 L")
    assert sector[0]["path"].endswith("Z")


def test_annulus_from_dict_uses_param1_and_param2_as_radii():
    annulus = Annulus.from_dict({
        "x0": 1,
        "y0": 2,
        "param1": 3,
        "param2": 5,
        "start_angle": 0,
        "end_angle": 180,
    })

    assert isinstance(annulus, Annulus)
    assert annulus.inner_radius == 3
    assert annulus.outer_radius == 5


def test_path_rejects_missing_non_string_and_malformed_paths():
    with pytest.raises(IncompleteShapeError):
        Path("path", None)

    with pytest.raises(TypeError):
        Path("path", 123)

    with pytest.raises(ValueError):
        Path("path", "1,1 2,2")


def test_path_draw_and_extractor_field_preserve_path_string():
    path_str = "M 1,1 L 3,1 L 3,3 L 1,3 Z"
    shape = Path("path", path_str)

    assert shape.draw() == [{"line": {"color": "red"}, "opacity": 1, "type": "path", "path": path_str}]
    assert shape.get_extractor_field() == {
        DATA_SPEC["shape"].key: "path",
        DATA_SPEC["path"].key: path_str,
    }


def test_path_from_rectangle_creates_full_rectangle_with_metadata():
    shape = Path.from_rectangle(x0=5, y0=6, side1=4, side2=2)
    fields = shape.get_extractor_field()

    assert shape.shape_name == "rectangle"
    assert shape.path_str.startswith("M 3.0,5.0 L 7.0,5.0")
    assert fields[DATA_SPEC["shape"].key] == "rectangle"
    assert fields[DATA_SPEC["x0"].key] == 5
    assert fields[DATA_SPEC["side1"].key] == 4


def test_path_from_rectangle_can_make_sector_and_mask_it():
    shape = Path.from_rectangle(x0=5, y0=5, side1=6, side2=6, start_angle=-45, end_angle=45)
    mask = shape.mask(np.zeros((11, 11)))

    assert shape.path_str.startswith("M 5,5 L")
    assert mask[5, 7]
    assert not mask[5, 3]


def test_path_from_dict_supports_path_and_rectangle():
    path = Path.from_dict({"shape": "path", "path": "M 1,1 L 3,1 L 3,3 L 1,3 Z"})
    rectangle = Path.from_dict({
        "shape": "rectangle",
        "x0": 5,
        "y0": 5,
        "param1": 4,
        "param2": 2,
        "start_angle": -180,
        "end_angle": 180,
    })

    assert path.shape_name == "path"
    assert rectangle.shape_name == "rectangle"


def test_shape_from_dict_instantiates_rectangle_alias():
    shape = Shape.from_dict({
        "shape": "rectangle",
        "x0": 5,
        "y0": 5,
        "param1": 4,
        "param2": 2,
        "start_angle": -180,
        "end_angle": 180,
    })

    assert isinstance(shape, Path)
    assert shape.shape_name == "rectangle"
