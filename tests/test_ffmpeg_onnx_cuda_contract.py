from __future__ import annotations

import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class FFmpegOnnxCudaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script=(ROOT/'tools/ffmpeg-ai/build_onnx_cuda_ffmpeg.sh').read_text()
        cls.acceptance=(ROOT/'tools/ffmpeg-ai/current_host_acceptance.py').read_text()

    def test_removed_libnpp_absent(self): self.assertNotIn('--enable-libnpp',self.script)
    def test_nonfree_explicit_opt_in(self):
        self.assertIn('FA3_ALLOW_NONFREE:-NO',self.script); self.assertIn('FA3_FFMPEG_LICENSE_PROFILE:-lgpl',self.script)
    def test_sources_immutably_pinned(self):
        self.assertIn('FFMPEG_REF="bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa"',self.script)
        self.assertIn('NV_CODEC_REF="1889e62e2d35ff7aa9baca2bceb14f053785e6f1"',self.script)
    def test_arch_not_hardcoded(self):
        self.assertIn('FA3_CUDA_ARCH_LIST',self.script); self.assertIn('--query-gpu=compute_cap',self.script)
        self.assertNotIn('compute_86',self.script); self.assertNotIn('compute_90',self.script)
    def test_build_does_not_claim_zero_copy(self):
        self.assertIn("'zero_copy_status':'NOT_CLAIMED'",self.script); self.assertIn("'onnx_cuda_runtime_status':'PENDING_CURRENT_HOST'",self.script)
    def test_runtime_requires_real_onnx_command(self):
        self.assertIn('dnn_processing',self.acceptance); self.assertIn('dnn_backend=onnx',self.acceptance); self.assertIn('CUDAExecutionProvider',self.acceptance)
    def test_zero_copy_requires_profiler_evidence(self):
        for text in ("'host_transfer_bytes':0","'io_binding':True","'cuda_frame_interop':True","'stream_synchronization_validated':True"):
            self.assertIn(text,self.acceptance)


if __name__=='__main__': unittest.main()
