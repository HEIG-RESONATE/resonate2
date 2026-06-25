#!/usr/bin/env python3
"""Render PlantUML diagrams to SVG files."""

from pathlib import Path
from plantuml import PlantUML

DIAGRAMS_DIR = Path(__file__).parent
SERVER = "http://www.plantuml.com/plantuml/svg/"


def render_all():
    plantuml = PlantUML(url=SERVER)

    for puml_file in sorted(DIAGRAMS_DIR.glob("*.puml")):
        svg_file = DIAGRAMS_DIR / puml_file.with_suffix(".svg").name
        print(f"Rendering {puml_file.name} -> {svg_file.name}")

        try:
            plantuml.processes_file(str(puml_file), outfile=str(svg_file))
            print(f"  OK ({svg_file.stat().st_size} bytes)")
        except Exception as e:
            print(f"  FAILED: {e}")


if __name__ == "__main__":
    render_all()
