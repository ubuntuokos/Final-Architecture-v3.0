import unittest
from src.fa3_embedding_fabric_gate import embedding_space_identity,direct_similarity_allowed,migration_cutover_allowed

class EmbeddingFabricTests(unittest.TestCase):
    def descriptor(self):
        return {"model_family":"bge-m3","immutable_model_revision":"r1","tokenizer_revision":"t1","pooling":"cls","normalization":"l2","query_template":"q:{text}","document_template":"d:{text}","dimension":1024,"semantic_role":"retrieval","modality":"text"}
    def test_space_identity_is_deterministic(self):
        self.assertEqual(embedding_space_identity(self.descriptor()),embedding_space_identity(self.descriptor()))
    def test_space_identity_changes_on_semantic_field(self):
        a=self.descriptor(); b={**a,"normalization":"none"}
        self.assertNotEqual(embedding_space_identity(a),embedding_space_identity(b))
    def test_cross_space_direct_similarity_fails_closed(self):
        sid=embedding_space_identity(self.descriptor())
        self.assertTrue(direct_similarity_allowed(sid,sid))
        self.assertFalse(direct_similarity_allowed(sid,"sha256:other"))
    def test_migration_requires_quality_and_performance(self):
        good={"shadow_reembed":True,"new_index":True,"dual_query_comparison":True,"quality_result":"PASS","performance_result":"PASS","controlled_cutover":True,"old_index_retirement":True}
        self.assertTrue(migration_cutover_allowed(good))
        self.assertFalse(migration_cutover_allowed({**good,"performance_result":"FAIL"}))

if __name__=="__main__": unittest.main()
