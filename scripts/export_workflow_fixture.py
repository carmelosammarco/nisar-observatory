"""Refresh the test fixture from the actual backend contract; never a hand-edited UI rule copy."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.workflows import operator_registry,checked_recipe
from backend.workflow_templates import example_recipe
from backend.examples import CASES
registry=operator_registry()
fixture={'operators':registry['operators'],'outputs':registry['scientific_outputs'],'rules':registry['workflow_rules'],'recipes':{ident:checked_recipe(example_recipe(ident)).model_dump(mode='json') for ident in CASES}}
(ROOT/'tests/frontend/fixtures/scientific-blocks.json').write_text(json.dumps(fixture,indent=2)+'\n')
print('Exported backend rules, schemas and all seven example recipes.')
