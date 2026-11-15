"""Regression: even API modules collected without lifespan use a private root."""
from pathlib import Path
from backend.access import DATA

def test_collection_runtime_cannot_be_the_owner_data_folder():
 owner=Path(__file__).resolve().parents[1]/'data'
 assert DATA.resolve()!=owner.resolve()
 assert DATA.name.startswith('nisar-pytest-')
 assert DATA.is_dir()
