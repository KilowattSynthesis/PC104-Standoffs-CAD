from dataclasses import dataclass
from pathlib import Path

import build123d as bd
from build123d_ease import show
from loguru import logger


@dataclass
class PC104Spec:
    """Specification for PC104.

    Assume the stack header is on the left side, with pins pointing down/into
    the page.

    Note the general lack of symmetry in the hole locations.

    H2 header is on the left.
    """

    # top_left_pin is H2-52
    top_left_pin_coord: tuple[float, float] = (0, 0)

    pin_count_x: int = 4
    pin_count_y: int = 26
    pin_pitch: float = 2.54

    box_width_x: float = 94.54
    box_height_y: float = 88.1
    box_top_left_coord: tuple[float, float] = (-4.4, 11.63)

    @property
    def hole_coord_list(self) -> dict[str, tuple[float, float]]:
        """Return a dictionary of hole coordinates."""
        return {
            "NW": (0, 5.08),  # Top-Left (NW).
            "NE": (85.73, 7.62),  # Top-Right (NE).
            "SW": (0, -68.58),  # Bottom-Left (SW).
            "SE": (85.73, -72.39),  # Bottom-Right (SE).
        }

    @property
    def stack_headers_center_coord(self) -> tuple[float, float]:
        """Return the center coordinate of the stack headers."""
        return (
            # X:
            self.top_left_pin_coord[0]
            + ((self.pin_count_x - 1) * self.pin_pitch / 2),
            # Y:
            self.top_left_pin_coord[1]
            - ((self.pin_count_y - 1) * self.pin_pitch / 2),
        )

    def __post_init__(self) -> None:
        """Post initialization checks."""


@dataclass
class StandSpec:
    """Specification for standoff part."""

    base_plate_thickness: float = 2.0
    plate_plate_corner_radius: float = 3.0

    standoff_total_height: float = 9.5

    standoff_id: float = 3.5

    standoff_od_east: float = 6.5
    standoff_od_west: float = 5.8

    def __post_init__(self) -> None:
        """Post initialization checks."""


def make_pc104_standoff(
    pc104: PC104Spec, part_spec: StandSpec
) -> bd.Part | bd.Compound:
    """Create a CAD model of the PC104 standoff board."""
    p = bd.Part(None)

    # Draw the outside edge of the board.
    _base_plate = bd.Part(None) + bd.Box(
        pc104.box_width_x,
        pc104.box_height_y,
        part_spec.base_plate_thickness,
        align=(bd.Align.MIN, bd.Align.MAX, bd.Align.MIN),
    ).translate(
        (
            *pc104.box_top_left_coord,
            0,
        )
    )
    p += _base_plate.fillet(
        radius=part_spec.plate_plate_corner_radius,
        edge_list=_base_plate.edges().filter_by(bd.Axis.Z),
    )

    # Draw the standoffs.
    for hole_name, hole_coord in pc104.hole_coord_list.items():
        p += bd.Cylinder(
            height=part_spec.standoff_total_height,
            radius=(
                part_spec.standoff_od_east
                if hole_name in ("NE", "SE")
                else part_spec.standoff_od_west
            )
            / 2,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).translate(
            (
                hole_coord[0],
                hole_coord[1],
                0,
            )
        )

        # Remove the hole.
        p -= bd.Cylinder(
            height=20,
            radius=part_spec.standoff_id / 2,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).translate(
            (
                hole_coord[0],
                hole_coord[1],
                (part_spec.base_plate_thickness if hole_name != "NW" else -10),
            )
        )

    # Remove where the stack header goes.
    p -= bd.Box(
        pc104.pin_count_x * pc104.pin_pitch + 8,
        pc104.pin_count_y * pc104.pin_pitch + 3,
        20,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    ).translate(
        (
            *pc104.stack_headers_center_coord,
            0,
        )
    )

    return p


if __name__ == "__main__":
    parts = {
        "pc104_standoff": show(
            make_pc104_standoff(
                pc104=PC104Spec(),
                part_spec=StandSpec(),
            )
        ),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(
        exist_ok=True
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid | bd.Compound), (
            f"{name} is not an expected type ({type(part)})"
        )
        if not part.is_manifold:
            logger.warning(f"Part '{name}' is not manifold")

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
