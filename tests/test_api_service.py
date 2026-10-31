"""
Tests unitaires pour l'orchestrateur FastAPI (Sprint 4).
"""
import unittest
from fastapi.testclient import TestClient
from api_service.main import app


class APIServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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

    def test_speak_smart_generation(self):
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
