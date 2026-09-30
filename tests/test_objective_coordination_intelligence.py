import unittest
from src.fa3_objective_coordination_intelligence import Objective,Dependency,CoordinationError,ready,blockers,downstream_impact,movable_forward,dependency_batches

class CoordinationIntelligenceTests(unittest.TestCase):
 def test_readiness_and_blocker(self):
  o=Objective({"a":"PENDING","b":"PENDING"},[Dependency("a","b")])
  self.assertEqual(ready(o),["a"]); self.assertIn("b",blockers(o))
 def test_cycle_fail_closed(self):
  o=Objective({"a":"PENDING","b":"PENDING"},[Dependency("a","b"),Dependency("b","a")])
  with self.assertRaises(CoordinationError): ready(o)
 def test_impact(self):
  o=Objective({"a":"FAILED","b":"PENDING","c":"PENDING"},[Dependency("a","b"),Dependency("b","c")])
  self.assertEqual(downstream_impact(o,"a"),["b","c"])
 def test_movable_forward(self):
  o=Objective({"a":"FAILED","b":"PENDING","x":"PENDING"},[Dependency("a","b")])
  self.assertEqual(movable_forward(o,"a"),["x"])
 def test_batches(self):
  o=Objective({"a":"PENDING","b":"PENDING","c":"PENDING"},[Dependency("a","c"),Dependency("b","c")])
  self.assertEqual(dependency_batches(o),[["a","b"],["c"]])

if __name__=="__main__": unittest.main()
