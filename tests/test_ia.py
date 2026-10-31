import json
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from docx import Document
from pypdf import PdfWriter

from app.ia import (
    AIConfigurationError,
    AIServiceError,
    DocumentExtractionError,
    _groq_error_message,
    analyze_profile,
    extract_cv_text,
    generate_interview_question,
    transcribe_audio,
)


class IAServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_extracts_docx_paragraphs_and_tables(self):
        path = self.root / 'resume.docx'
        document = Document()
        document.add_paragraph('Gloria Nziengi - Analyste de données')
        table = document.add_table(rows=1, cols=1)
        table.cell(0, 0).text = 'Compétence : Python'
        document.save(path)

        text = extract_cv_text(path, 'docx')

        self.assertIn('Gloria Nziengi', text)
        self.assertIn('Compétence : Python', text)

    def test_rejects_image_only_or_empty_pdf(self):
        path = self.root / 'empty.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        with path.open('wb') as pdf_file:
            writer.write(pdf_file)

        with self.assertRaisesRegex(DocumentExtractionError, 'Aucun texte extractible'):
            extract_cv_text(path, 'pdf')

    def test_rejects_missing_api_key(self):
        with self.assertRaises(AIConfigurationError):
            analyze_profile('CV text', 'job text', '')

    def test_groq_errors_explain_invalid_key_quota_and_model_problems(self):
        self.assertIn('GROQ_API_KEY', _groq_error_message(SimpleNamespace(status_code=401)))
        self.assertIn('quota', _groq_error_message(SimpleNamespace(status_code=429)))
        self.assertIn('GROQ_MODEL', _groq_error_message(SimpleNamespace(status_code=404)))

    @patch('app.ia.Groq')
    def test_analyze_profile_validates_and_normalizes_structured_response(self, groq_class):
        groq_class.return_value.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content=json.dumps({
                'summary': 'Profil data.',
                'matching_percentage': 82,
                'strengths': [
                    {'skill': 'Python', 'evidence': 'Python'},
                    {'skill': 'SQL', 'evidence': 'SQL'},
                ],
                'gaps': ['Power BI'],
                'first_interview_question': 'Décrivez un projet data.',
            })))
        ]

        result = analyze_profile(
            'CV text: Python and SQL projects',
            'Job description',
            'test-key',
        )

        self.assertEqual(result['matching_percentage'], 82)
        self.assertEqual(result['summary'], 'Profil data.')
        self.assertEqual(
            result['strengths'],
            ['Python — preuve du CV : « Python »', 'SQL — preuve du CV : « SQL »'],
        )
        prompt_data = json.loads(
            groq_class.return_value.chat.completions.create.call_args.kwargs[
                'messages'
            ][1]['content']
        )
        self.assertEqual(prompt_data['job_description'], 'Job description')
        self.assertEqual(
            groq_class.return_value.chat.completions.create.call_args.kwargs['model'],
            'llama-3.3-70b-versatile',
        )

    @patch('app.ia.Groq')
    def test_rejects_invalid_model_score(self, groq_class):
        groq_class.return_value.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content=json.dumps({
                'summary': 'Profil.',
                'matching_percentage': 140,
                'strengths': [],
                'gaps': [],
                'first_interview_question': 'Question ?',
            })))
        ]
        with self.assertRaises(AIServiceError):
            analyze_profile('CV text', 'Job description', 'test-key')

    @patch('app.ia.Groq')
    def test_rejects_strengths_with_evidence_not_in_the_cv(self, groq_class):
        groq_class.return_value.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content=json.dumps({
                'summary': 'Profil data.',
                'matching_percentage': 80,
                'strengths': [{'skill': 'Python', 'evidence': 'maîtrise de Java'}],
                'gaps': [],
                'first_interview_question': 'Décrivez un projet.',
            })))
        ]

        with self.assertRaises(AIServiceError):
            analyze_profile('Python et SQL', 'Offre de data analyste.', 'test-key')

    @patch('app.ia.Groq')
    def test_interview_question_uses_structured_output(self, groq_class):
        groq_class.return_value.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content='{"question":"Comment avez-vous utilisé SQL ?"}'))
        ]
        question = generate_interview_question(
            'CV', 'Offre', 'Résumé', [], 'J’ai utilisé SQL.', 'test-key'
        )
        self.assertEqual(question, 'Comment avez-vous utilisé SQL ?')

    @patch('app.ia.Groq')
    def test_transcribes_audio_in_french(self, groq_class):
        groq_class.return_value.audio.transcriptions.create.return_value.text = (
            'Je maîtrise Python et SQL.'
        )

        transcript = transcribe_audio(io.BytesIO(b'audio'), 'answer.webm', 'test-key')

        self.assertEqual(transcript, 'Je maîtrise Python et SQL.')
        call = groq_class.return_value.audio.transcriptions.create.call_args.kwargs
        self.assertEqual(call['model'], 'whisper-large-v3-turbo')
        self.assertEqual(call['language'], 'fr')
        self.assertEqual(call['file'][0], 'answer.webm')

if __name__ == '__main__':
    unittest.main()
