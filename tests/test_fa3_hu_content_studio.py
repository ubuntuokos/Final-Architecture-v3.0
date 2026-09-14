from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fa3_marketing_studio import (ConsentError, ConsentRegistry, FA3HungarianMarketingStudio,
    LanguageValidationResult, LicenseAdmissionError, ProviderAdmissionGate, SecurityError, sha256_file)


def write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes((b'\x01\x00')*1600)


def sign(row: dict, key: bytes) -> dict:
    data=dict(row); raw=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    data['signature']=hmac.new(key,raw,hashlib.sha256).hexdigest(); return data


class Broker:
    def __init__(self,attested=False): self.released=[]; self.attested=attested
    def request_gpu_lease(self,**kwargs):
        return {'lease_id':'lease-1','gpu_uuid':'GPU-test','cuda_ordinal':2,'current_host_attested':self.attested}
    def release_gpu_lease(self,lease_id): self.released.append(lease_id)


class Validator:
    def __init__(self,locale='hu-HU',confidence=.99): self.locale=locale; self.confidence=confidence
    def validate(self,text,expected_locale): return LanguageValidationResult(self.locale,self.confidence,'test-validator')


class HuContentStudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.key=b'unit-test-secret'
        self.speaker=self.root/'speaker.wav'; write_wav(self.speaker)
        self.model=self.root/'hu_HU-anna-medium.onnx'; self.model.write_bytes(b'model')
        now=datetime.now(timezone.utc)
        self.receipt={'consent_id':'consent-1','voice_owner_id':'owner-1','audit_receipt_id':'audit-1',
            'valid_from':(now-timedelta(hours=1)).isoformat(),'expires_at':(now+timedelta(hours=1)).isoformat(),
            'revoked_at':None,'permitted_purposes':['VOICE_CLONE_MARKETING'],'allowed_providers':['idiap/coqui-ai-TTS'],
            'allowed_models':['tts_models/multilingual/multi-dataset/xtts_v2'],'speaker_sha256':sha256_file(self.speaker)}
        self.consent_path=self.root/'consents.json'; self._write_receipt(self.receipt)
        self.admission_path=self.root/'admissions.json'; self._write_admissions('APPROVED')
        self.evidence=self.root/'evidence'

    def tearDown(self): self.tmp.cleanup()

    def _write_receipt(self,row): self.consent_path.write_text(json.dumps({'receipts':[sign(row,self.key)]}))
    def _write_admissions(self,status):
        rows=[
          {'provider':'idiap/coqui-ai-TTS','model':'tts_models/multilingual/multi-dataset/xtts_v2','voice':None,
           'status':status,'allowed_purposes':['VOICE_CLONE_MARKETING'],'license_review_sha256':'a'*64},
          {'provider':'OHF-Voice/piper1-gpl','model':'hu_HU-anna-medium','voice':'hu_HU-anna-medium',
           'status':'APPROVED','allowed_purposes':['GENERIC_HU_TTS'],'license_review_sha256':'c'*64}]
        self.admission_path.write_text(json.dumps({'schema':'fa3.voice-provider-admission.v1','admissions':rows}))

    def studio(self,broker=None,runner=None,attestation=None,validator=None,suppression=None):
        return FA3HungarianMarketingStudio(
          consent_registry=ConsentRegistry(self.consent_path,self.key),provider_gate=ProviderAdmissionGate(self.admission_path),
          resource_broker=broker or Broker(),evidence_dir=self.evidence,language_validator=validator or Validator(),
          suppression=suppression or set(),xtts_runner=runner or (lambda text,speaker,out,ordinal: write_wav(Path(out))),
          current_host_attestation=attestation or {})

    def test_tampered_receipt_fails_closed(self):
        doc=json.loads(self.consent_path.read_text()); doc['receipts'][0]['voice_owner_id']='attacker'; self.consent_path.write_text(json.dumps(doc))
        with self.assertRaises(ConsentError): self.studio().execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))

    def test_revoked_consent_fails_closed(self):
        row=dict(self.receipt); row['revoked_at']=datetime.now(timezone.utc).isoformat(); self._write_receipt(row)
        with self.assertRaises(ConsentError): self.studio().execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))

    def test_purpose_scope_fails_closed(self):
        row=dict(self.receipt); row['permitted_purposes']=['OTHER']; self._write_receipt(row)
        with self.assertRaises(ConsentError): self.studio().execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))

    def test_changed_speaker_fails_closed(self):
        write_wav(self.speaker); self.speaker.write_bytes(self.speaker.read_bytes()+b'x')
        with self.assertRaises(ConsentError): self.studio().execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))

    def test_provider_admission_deny_by_default(self):
        self._write_admissions('PENDING_LEGAL_REVIEW')
        with self.assertRaises(LicenseAdmissionError): self.studio().execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))

    def test_gpu_lease_released_on_synthesis_failure(self):
        broker=Broker()
        def fail(*args): raise RuntimeError('synthetic failure')
        with self.assertRaises(RuntimeError): self.studio(broker=broker,runner=fail).execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))
        self.assertEqual(broker.released,['lease-1'])

    def test_success_without_host_attestation_stays_pending(self):
        output=self.studio().execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))
        self.assertTrue(Path(output).exists()); evidence=json.loads(next(self.evidence.glob('xtts-*.evidence.json')).read_text())
        self.assertEqual(evidence['pipeline_status'],'PENDING_CURRENT_HOST'); self.assertEqual(evidence['source_speaker_wav_sha256'],sha256_file(self.speaker))

    def test_current_host_pass_requires_attested_lease_and_digest(self):
        self.studio(broker=Broker(True),attestation={'qualified':True,'sha256':'b'*64}).execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))
        evidence=json.loads(next(self.evidence.glob('xtts-*.evidence.json')).read_text()); self.assertEqual(evidence['pipeline_status'],'CURRENT_HOST_E2E_PASS')

    def test_piper_uses_argv_and_stdin_without_shell(self):
        dangerous="teszt'; touch /tmp/FA3_INJECTION; echo '"
        def fake(args,**kwargs):
            self.assertIsInstance(args,list); self.assertNotIn('shell',kwargs); self.assertEqual(kwargs['input'],dangerous)
            write_wav(Path(args[args.index('--output_file')+1])); return subprocess.CompletedProcess(args,0)
        with patch('fa3_marketing_studio.subprocess.run',side_effect=fake):
            self.studio().execute_generic_hungarian_tts(text=dangerous,voice_model='hu_HU-anna-medium',model_path=self.model)
        self.assertFalse(Path('/tmp/FA3_INJECTION').exists())

    def test_voice_clone_never_silently_falls_back_to_piper(self):
        def fail(*args): raise RuntimeError('xtts unavailable')
        with patch('fa3_marketing_studio.subprocess.run') as run:
            with self.assertRaises(RuntimeError): self.studio(runner=fail).execute_voice_cloning_pipeline(target_text='teszt',consent_id='consent-1',speaker_wav_path=str(self.speaker))
            run.assert_not_called()

    def test_real_language_validation_and_suppression_gate(self):
        response=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Magyar szöveg.'))])
        engine=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
        with self.assertRaises(SecurityError): self.studio(validator=Validator('en',.99)).generate_native_hungarian_copy({'target_locale':'hu-HU','purpose':'teszt'},engine)
        with self.assertRaises(PermissionError): self.studio(suppression={'blocked@example.com'}).assert_recipient_allowed('Blocked@Example.com')


if __name__=='__main__': unittest.main()
