"""
Tests unitaires pour l'orchestrateur FastAPI (Sprint 4).
"""
import unittest
import tempfile
import wave
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch
from api_service.main import app


class APIServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.audio_directory = tempfile.TemporaryDirectory()
        self.audio_dir_patch = patch(
            'api_service.main.TEMP_AUDIO_DIR',
            Path(self.audio_directory.name),
        )
        self.audio_dir_patch.start()
        self.addCleanup(self.audio_dir_patch.stop)
        self.addCleanup(self.audio_directory.cleanup)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("service", data)
        self.assertIn("POST /speak-smart", data["endpoints"])

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    @patch('api_service.main.reformulate_pitch_with_llm', return_value='Pitch professionnel de test.')
    @patch('api_service.main.synthesize_audio_wav')
    def test_speak_smart_generation(self, synthesize_audio, _reformulate):
        def write_test_audio(_text, output_path):
            with wave.open(str(output_path), 'wb') as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(16000)
                audio_file.writeframes(b'\x00\x00' * 100)

        synthesize_audio.side_effect = write_test_audio
        payload = {
            "cv_text": "Gloria NZ - Développeuse IA et Full Stack avec 3 ans d'expérience en Python, FastAPI et LLM.",
            "job_target": "Ingénieure IA Générative",
            "duration_seconds": 30
        }
        response = self.client.post("/speak-smart", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["pitch_text"]) > 10)
        self.assertTrue(data["audio_url"].startswith("/audio/"))
        self.assertIn("MOS_estimated", data["audio_metrics"])

        # Vérifier que le fichier audio est téléchargeable
        audio_res = self.client.get(data["audio_url"])
        self.assertEqual(audio_res.status_code, 200)
        self.assertEqual(audio_res.headers["content-type"], "audio/wav")
        self.assertGreater(len(audio_res.content), 100)


if __name__ == "__main__":
    unittest.main()
