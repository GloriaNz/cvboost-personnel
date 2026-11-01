import unittest
from unittest.mock import patch, Mock
import json

from app.llm_router import (
    call_llm_with_fallback,
    LLMQuotaExceededError,
    LLMProviderError,
    _call_gemini,
    _call_groq,
    _call_mistral,
)


class LLMFallbackTests(unittest.TestCase):
    def setUp(self):
        self.messages = [
            {"role": "system", "content": "Tu es un recruteur."},
            {"role": "user", "content": "Question."},
        ]

    @patch("app.llm_router._call_gemini")
    def test_gemini_success_is_used_first(self, mock_gemini):
        mock_gemini.return_value = '{"status": "ok_gemini"}'

        content, provider = call_llm_with_fallback(
            messages=self.messages,
            gemini_key="gemini-key-123",
            groq_key="groq-key-123",
            mistral_key="mistral-key-123",
        )

        self.assertEqual(provider, "gemini")
        self.assertEqual(content, '{"status": "ok_gemini"}')
        mock_gemini.assert_called_once()

    @patch("app.llm_router._call_groq")
    @patch("app.llm_router._call_gemini")
    def test_gemini_quota_exceeded_falls_back_to_groq(self, mock_gemini, mock_groq):
        mock_gemini.side_effect = LLMQuotaExceededError("Gemini quota 429 atteint")
        mock_groq.return_value = '{"status": "ok_groq"}'

        content, provider = call_llm_with_fallback(
            messages=self.messages,
            gemini_key="gemini-key-123",
            groq_key="groq-key-123",
            mistral_key="mistral-key-123",
        )

        self.assertEqual(provider, "groq")
        self.assertEqual(content, '{"status": "ok_groq"}')
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()

    @patch("app.llm_router._call_mistral")
    @patch("app.llm_router._call_groq")
    @patch("app.llm_router._call_gemini")
    def test_gemini_and_groq_quota_exceeded_falls_back_to_mistral(
        self, mock_gemini, mock_groq, mock_mistral
    ):
        mock_gemini.side_effect = LLMQuotaExceededError("Gemini quota 429")
        mock_groq.side_effect = LLMQuotaExceededError("Groq TPM limit 429")
        mock_mistral.return_value = '{"status": "ok_mistral"}'

        content, provider = call_llm_with_fallback(
            messages=self.messages,
            gemini_key="gemini-key-123",
            groq_key="groq-key-123",
            mistral_key="mistral-key-123",
        )

        self.assertEqual(provider, "mistral")
        self.assertEqual(content, '{"status": "ok_mistral"}')
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()
        mock_mistral.assert_called_once()

    @patch("app.llm_router._call_mistral")
    @patch("app.llm_router._call_groq")
    @patch("app.llm_router._call_gemini")
    def test_all_providers_failed_raises_error(
        self, mock_gemini, mock_groq, mock_mistral
    ):
        mock_gemini.side_effect = LLMQuotaExceededError("Gemini quota 429")
        mock_groq.side_effect = LLMQuotaExceededError("Groq 429")
        mock_mistral.side_effect = LLMProviderError("Mistral 500 error")

        with self.assertRaises(LLMProviderError) as ctx:
            call_llm_with_fallback(
                messages=self.messages,
                gemini_key="gemini-key-123",
                groq_key="groq-key-123",
                mistral_key="mistral-key-123",
            )

        self.assertIn("Tous les fournisseurs d'IA configurés ont échoué", str(ctx.exception))
        self.assertIn("Gemini", str(ctx.exception))
        self.assertIn("Groq", str(ctx.exception))
        self.assertIn("Mistral", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
