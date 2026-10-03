from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def test_controller(self):
  x=(ROOT/".github/workflows/fa3-current-host-closure-controller.yml").read_text()
  self.assertIn("cancel-in-progress: true",x); self.assertIn("git merge --no-ff --no-commit",x)
  self.assertIn("Projection stability barrier",x); self.assertIn("needs.plan.outputs.execute == 'true'",x)
  self.assertIn("fa3_current_host_requalification_plan.py",x)
 def test_projection_adopter_is_exact_parent_projection_only(self):
  x=(ROOT/".github/workflows/fa3-current-host-projection-adopt.yml").read_text()
  self.assertIn('test "$(git rev-parse "$rec^")" = "$SOURCE_SHA"',x)
  self.assertIn('test "${#changed[@]}" -eq 1',x)
  self.assertIn('test "${changed[0]}" = "$projection"',x)
  self.assertIn("./bin/fa3-enforce release-projection",x)
 def test_shared_physical_lock(self):
  token="fa3-current-host-physical-${{ github.event.pull_request.head.ref || github.ref_name }}"
  for p in [
   ".github/workflows/fa3-global-current-host-closure.yml",
   ".github/workflows/fa3-accelerator-guard-current-host.yml",
   ".github/workflows/fa3-decision-fabric-current-host.yml",
   ".github/workflows/fa3-khronos-current-host.yml",
   ".github/workflows/fa3-model-router-current-host.yml",
  ]:
   x=(ROOT/p).read_text(); self.assertIn(token,x,p); self.assertIn("cancel-in-progress: true",x,p)
if __name__=="__main__":unittest.main()
