"""Run frontend handlerParamSchema + buildAddObjectAction smoke checks via Node."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_SCRIPT = r"""
import { formatHandlerSummaryFromCatalog, handlerParamsToCliParts } from './frontend/handlerParamSchema.js';
import { buildAddObjectAction } from './frontend/api.js';

const catalog = {
  skill_check: {
    summary_template: 'skill_check {stat} DC {dc}',
    param_fields: [
      { type: 'handler_ref', name: 'pass_handler', summary_key: 'pass' },
      { type: 'handler_ref', name: 'fail_handler', summary_key: 'fail' },
    ],
  },
};
const summary = formatHandlerSummaryFromCatalog({
  handler_id: 'skill_check',
  handler_params: { stat: 'DEX', dc: '12', pass_handler: 'inventory_pick_up' },
}, catalog);
if (!summary.includes('DEX') || !summary.includes('pass inventory_pick_up')) {
  console.error('bad summary', summary);
  process.exit(1);
}
const line = buildAddObjectAction('obj1', {
  name: 'check',
  range: 1,
  result: 'ok',
  passive: 'did',
  handler: 'skill_check',
  handlerParams: { stat: 'DEX', dc: '12', pass_handler: 'move_area', 'pass_dest-area': 'hall' },
});
if (!line.includes('handler skill_check') || !line.includes('stat') || !line.includes('pass_handler')) {
  console.error('bad cli', line);
  process.exit(1);
}
const parts = handlerParamsToCliParts({ dc: '10', skill: 'lockpicking' });
if (parts[0] !== 'dc' || parts[2] !== 'skill') process.exit(1);
console.log('ok');
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_handler_param_schema_cli_helpers_via_node():
    result = subprocess.run(
        ["node", "--input-type=module", "-e", _SCRIPT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
