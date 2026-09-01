import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_model_manager_provider_adapter import regression_check,select_lmstudio_model,select_ollama_models,safe_child_env,valid_revision

class ModelManagerProviderAdapterTests(unittest.TestCase):
    def test_regression_passes(self):
        report=regression_check()
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual(report["passed"],report["total"])
    def test_lmstudio_smallest_local_llm(self):
        row=select_lmstudio_model([
            {"modelKey":"z-large","type":"llm","sizeBytes":100},
            {"modelKey":"a-small","type":"llm","sizeBytes":10},
            {"modelKey":"embed","type":"embedding","sizeBytes":1},
        ])
        self.assertEqual("a-small",row["modelKey"])
    def test_ollama_rejects_non_digest(self):
        rows=select_ollama_models({"models":[
            {"name":"floating","digest":"latest","size":1},
            {"name":"pinned","digest":"a"*64,"size":2},
        ]})
        self.assertEqual(["pinned"],[x["name"] for x in rows])
    def test_safe_env_removes_secrets_and_proxies(self):
        env=safe_child_env({"PATH":"/bin","HOME":"/tmp","HF_TOKEN":"x","API_KEY":"x","HTTPS_PROXY":"http://x","WAYLAND_DISPLAY":"wayland-0"})
        self.assertNotIn("HF_TOKEN",env); self.assertNotIn("API_KEY",env); self.assertNotIn("HTTPS_PROXY",env)
        self.assertEqual("wayland-0",env["WAYLAND_DISPLAY"])
    def test_revision_is_immutable_hash_only(self):
        self.assertTrue(valid_revision("b"*40)); self.assertFalse(valid_revision("main")); self.assertFalse(valid_revision("latest"))
if __name__=="__main__": unittest.main()
