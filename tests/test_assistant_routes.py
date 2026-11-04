import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docx import Document
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import AssistantConversation, AssistantMessage, CV, User


class AssistantRouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.uploads = self.root / 'uploads'
        self.uploads.mkdir()
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'assistant-test-secret',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'WTF_CSRF_ENABLED': False,
            'UPLOAD_FOLDER': str(self.uploads),
            'UPLOAD_AUDIT_LOG': str(self.root / 'audit.jsonl'),
            'GROQ_API_KEY': 'test-groq-key',
            'GROQ_MODEL': 'test-model',
            'GROQ_TRANSCRIPTION_MODEL': 'whisper-large-v3-turbo',
            'ASSISTANT_RATE_LIMIT_PER_MINUTE': 10,
            'NLLB_ADAPTER_PATH': str(self.root / 'missing-adapter'),
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self.user = User(
                nom='Nziengi',
                prenom='Gloria',
                email='gloria@example.com',
                password_hash=generate_password_hash('password-test'),
            )
            other_user = User(
                nom='Autre',
                prenom='Compte',
                email='autre@example.com',
                password_hash=generate_password_hash('password-test'),
            )
            db.session.add_all([self.user, other_user])
            db.session.flush()
            self.user_id = self.user.id
            self.other_user_id = other_user.id
            self.cv = CV(
                filename_original='CV Gloria.docx',
                filename_stored='gloria.docx',
                user_id=self.user.id,
            )
            self.other_cv = CV(
                filename_original='CV autre.docx',
                filename_stored='autre.docx',
                user_id=other_user.id,
            )
            db.session.add_all([self.cv, self.other_cv])
            db.session.commit()
            self.cv_id = self.cv.id
            self.other_cv_id = self.other_cv.id
        self._write_docx(self.uploads / 'gloria.docx', 'Expérience professionnelle en Python.')
        self._write_docx(self.uploads / 'autre.docx', 'Données privées du compte tiers.')
        self.client.post(
            '/login',
            data={'email': 'gloria@example.com', 'password': 'password-test'},
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temporary_directory.cleanup()

    @staticmethod
    def _write_docx(path, content):
        document = Document()
        document.add_paragraph(content)
        document.save(path)

    def csrf_token(self):
        response = self.client.get('/assistant')
        self.assertEqual(response.status_code, 200)
        token = re.search(rb'data-csrf-token="([^"]+)"', response.data)
        self.assertIsNotNone(token)
        return token.group(1).decode()

    def create_conversation(self, csrf, **overrides):
        data = {
            'language': 'fr',
            'use_personal_context': False,
        }
        data.update(overrides)
        response = self.client.post(
            '/api/assistant/conversations',
            json=data,
            headers={'X-CSRFToken': csrf},
        )
        self.assertEqual(response.status_code, 201)
        return response.json['id']

    def test_assistant_page_requires_login_and_displays_chat_ui(self):
        client = self.app.test_client()
        response = client.get('/assistant')
        self.assertEqual(response.status_code, 302)

        response = self.client.get('/assistant')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CVBoost AI', response.data)
        self.assertIn(b'profil (nom et pr\xc3\xa9nom) et mon CV', response.data)
        self.assertIn(b'Lingala', response.data)

    def test_creates_lists_and_deletes_owned_conversation_and_messages(self):
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(csrf)
        with self.app.app_context():
            db.session.add(AssistantMessage(
                conversation_id=conversation_id,
                role='user',
                content='Question de test',
            ))
            db.session.commit()

        detail = self.client.get(f'/api/assistant/conversations/{conversation_id}')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json['messages'][0]['content'], 'Question de test')
        self.assertIn(
            conversation_id,
            [item['id'] for item in self.client.get('/api/assistant/conversations').json['conversations']],
        )

        response = self.client.delete(
            f'/api/assistant/conversations/{conversation_id}',
            headers={'X-CSRFToken': csrf},
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertIsNone(db.session.get(AssistantConversation, conversation_id))
            self.assertEqual(AssistantMessage.query.count(), 0)

    def test_cannot_read_or_delete_another_users_conversation(self):
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(csrf)
        other_client = self.app.test_client()
        other_client.post(
            '/login',
            data={'email': 'autre@example.com', 'password': 'password-test'},
        )

        response = other_client.get(f'/api/assistant/conversations/{conversation_id}')
        self.assertEqual(response.status_code, 404)
        response = other_client.delete(
            f'/api/assistant/conversations/{conversation_id}',
            headers={'X-CSRFToken': csrf},
        )
        self.assertEqual(response.status_code, 404)

    def test_rejects_context_cv_owned_by_another_user(self):
        response = self.client.post(
            '/api/assistant/conversations',
            json={
                'language': 'fr',
                'use_personal_context': True,
                'cv_id': self.other_cv_id,
            },
            headers={'X-CSRFToken': self.csrf_token()},
        )
        self.assertEqual(response.status_code, 404)

    def test_rejects_invalid_csrf_and_invalid_message(self):
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(csrf)
        response = self.client.post(
            '/api/assistant/conversations',
            json={'language': 'fr'},
            headers={'X-CSRFToken': 'invalid'},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            f'/api/assistant/conversations/{conversation_id}/messages',
            json={'message': ' '},
            headers={'X-CSRFToken': csrf},
        )
        self.assertEqual(response.status_code, 400)

    @patch('app.routes.generate_reply', return_value='Voici une réponse utile.')
    def test_sends_groq_reply_and_persists_conversation_messages(self, generate_reply):
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(csrf)
        response = self.client.post(
            f'/api/assistant/conversations/{conversation_id}/messages',
            json={'message': 'Comment améliorer mon CV ?'},
            headers={'X-CSRFToken': csrf},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['assistant_message']['content'], 'Voici une réponse utile.')
        self.assertEqual(
            generate_reply.call_args.args[1:],
            ('test-groq-key', 'test-model'),
        )
        self.assertEqual(generate_reply.call_args.args[0][-1]['content'], 'Comment améliorer mon CV ?')
        with self.app.app_context():
            conversation = db.session.get(AssistantConversation, conversation_id)
            self.assertEqual(conversation.title, 'Comment améliorer mon CV ?')
            self.assertEqual(
                [message.role for message in conversation.messages],
                ['user', 'assistant'],
            )

    @patch('app.routes.generate_reply', return_value='Une réponse liée au CV.')
    def test_personal_context_is_included_only_after_explicit_selection(self, generate_reply):
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(
            csrf,
            use_personal_context=True,
            cv_id=self.cv_id,
        )
        response = self.client.post(
            f'/api/assistant/conversations/{conversation_id}/messages',
            json={'message': 'Quelles sont mes compétences ?'},
            headers={'X-CSRFToken': csrf},
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn(
            'Expérience professionnelle en Python.',
            generate_reply.call_args.args[0][-1]['content'],
        )
        self.assertIn(
            'Profil candidat : Gloria Nziengi',
            generate_reply.call_args.args[0][-1]['content'],
        )
        self.assertNotIn(
            'gloria@example.com',
            generate_reply.call_args.args[0][-1]['content'],
        )

    def test_lingala_message_uses_nllb_and_reports_missing_local_adapter(self):
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(csrf, language='ln')
        with patch('app.routes.generate_reply') as generate_reply:
            response = self.client.post(
                f'/api/assistant/conversations/{conversation_id}/messages',
                json={'message': 'Mbote'},
                headers={'X-CSRFToken': csrf},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn('NLLB-LoRA', response.json['error'])
        generate_reply.assert_not_called()

    def test_rate_limit_is_per_user_and_returns_429(self):
        self.app.config['ASSISTANT_RATE_LIMIT_PER_MINUTE'] = 1
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(csrf)
        with patch('app.routes.generate_reply', return_value='Réponse.'):
            first = self.client.post(
                f'/api/assistant/conversations/{conversation_id}/messages',
                json={'message': 'Question une'},
                headers={'X-CSRFToken': csrf},
            )
            second = self.client.post(
                f'/api/assistant/conversations/{conversation_id}/messages',
                json={'message': 'Question deux'},
                headers={'X-CSRFToken': csrf},
            )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

    @patch('app.routes.transcribe_audio', return_value='Question dictée')
    def test_audio_is_transcribed_without_being_saved_and_lingala_falls_back_to_text(self, transcribe):
        csrf = self.csrf_token()
        conversation_id = self.create_conversation(csrf)
        response = self.client.post(
            f'/api/assistant/conversations/{conversation_id}/audio',
            data={'audio': (io.BytesIO(b'audio bytes'), 'question.webm')},
            headers={'X-CSRFToken': csrf},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['transcript'], 'Question dictée')
        transcribe.assert_called_once()
        self.assertEqual(
            {path.name for path in self.uploads.iterdir()},
            {'gloria.docx', 'autre.docx'},
        )

        lingala_id = self.create_conversation(csrf, language='ln')
        response = self.client.post(
            f'/api/assistant/conversations/{lingala_id}/audio',
            data={'audio': (io.BytesIO(b'audio bytes'), 'question.webm')},
            headers={'X-CSRFToken': csrf},
        )
        self.assertEqual(response.status_code, 422)
        transcribe.assert_called_once()


if __name__ == '__main__':
    unittest.main()
