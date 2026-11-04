import json
import io
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import AIAnalysis, CV, User


class AIRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.upload_directory = Path(self.temp_directory.name) / 'uploads'
        self.upload_directory.mkdir()
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-secret-key',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'WTF_CSRF_ENABLED': False,
            'UPLOAD_FOLDER': str(self.upload_directory),
            'UPLOAD_AUDIT_LOG': str(Path(self.temp_directory.name) / 'audit.jsonl'),
            'GROQ_API_KEY': 'test-key',
            'GEMINI_API_KEY': None,
            'MISTRAL_API_KEY': None,
            'GROQ_MODEL': 'qwen/qwen3.8-27b',
            'GROQ_TRANSCRIPTION_MODEL': 'whisper-large-v3-turbo',
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
            self.other_user_id = other_user.id
            self.cv = CV(
                filename_original='CV.pdf',
                filename_stored='document.pdf',
                user_id=self.user.id,
            )
            self.other_cv = CV(
                filename_original='CV autre.pdf',
                filename_stored='autre.pdf',
                user_id=other_user.id,
            )
            db.session.add_all([self.cv, self.other_cv])
            db.session.commit()
            self.cv_id = self.cv.id
            self.other_cv_id = self.other_cv.id
        (self.upload_directory / 'document.pdf').write_bytes(b'PDF test')
        (self.upload_directory / 'autre.pdf').write_bytes(b'PDF test')
        self.client.post(
            '/login',
            data={'email': 'gloria@example.com', 'password': 'password-test'},
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_directory.cleanup()

    def test_interview_landing_lists_cv_and_links_to_analysis(self):
        response = self.client.get('/interview')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Simulation entretien', response.data)
        self.assertIn(b'CV.pdf', response.data)
        self.assertIn(b'Analyser ce CV', response.data)
        self.assertIn(f'/result/{self.cv_id}'.encode(), response.data)

    def test_interview_landing_links_to_existing_simulation(self):
        self.create_pending_analysis()

        response = self.client.get('/interview')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Continuer l\xe2\x80\x99entra\xc3\xaenement', response.data)
        self.assertIn(f'/result/{self.cv_id}#interview'.encode(), response.data)

    def test_interview_landing_requires_authentication(self):
        client = self.app.test_client()

        response = client.get('/interview')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_interview_room_offers_a_voice_conversation(self):
        analysis_id = self.create_pending_analysis()

        response = self.client.get(f'/interview/{analysis_id}')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'D\xc3\xa9marrer l\xe2\x80\x99entretien vocal', response.data)
        self.assertIn(b'Madame Gloria vous accueille', response.data)
        self.assertIn(b'data-voice-pause', response.data)
        self.assertIn(b'Mettre en pause', response.data)
        self.assertIn(b'data-voice-resume', response.data)
        self.assertIn(b'data-voice-stop', response.data)
        self.assertIn(b'Arr\xc3\xaater l\xe2\x80\x99entretien vocal', response.data)
        self.assertIn(b'Madame Gloria', response.data)
        self.assertIn(b'Parlez-moi de votre exp\xc3\xa9rience avec Python.', response.data)

    def test_history_shows_a_confirmed_delete_action_for_each_cv(self):
        response = self.client.get('/history')

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'/history/{self.cv_id}/delete'.encode(),
            response.data,
        )
        self.assertIn(b'Supprimer ce CV, son analyse et son historique', response.data)

    def test_delete_cv_history_removes_file_cv_and_linked_analysis(self):
        analysis_id = self.create_pending_analysis()
        stored_path = self.upload_directory / self.cv.filename_stored

        response = self.client.post(f'/history/{self.cv_id}/delete')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/history')
        self.assertFalse(stored_path.exists())
        with self.app.app_context():
            self.assertIsNone(db.session.get(CV, self.cv_id))
            self.assertIsNone(db.session.get(AIAnalysis, analysis_id))

    def test_delete_cv_history_cannot_delete_another_users_cv(self):
        response = self.client.post(f'/history/{self.other_cv_id}/delete')

        self.assertEqual(response.status_code, 404)
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(CV, self.other_cv_id))

    def test_delete_cv_history_requires_post(self):
        response = self.client.get(f'/history/{self.cv_id}/delete')

        self.assertEqual(response.status_code, 405)

    @staticmethod
    def analysis_response():
        return {
            'summary': 'Gloria possède une expérience solide en analyse de données.',
            'matching_percentage': 85,
            'strengths': ['Python', 'SQL'],
            'gaps': ['Power BI'],
            'first_interview_question': 'Parlez-moi de votre dernier projet data.',
        }

    def test_analysis_persists_results_and_displays_interview_question(self):
        with patch('app.routes.extract_cv_text', return_value='CV text') as extraction, patch(
            'app.routes.analyze_profile', return_value=self.analysis_response()
        ) as analysis_service:
            response = self.client.post(
                f'/result/{self.cv_id}/analyze',
                data={'job_description': 'Poste analyste de données avec Python et SQL.'},
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/result/{self.cv_id}#interview', response.headers['Location'])
        extraction.assert_called_once()
        analysis_service.assert_called_once_with(
            'CV text',
            'Poste analyste de données avec Python et SQL.',
            'test-key',
            'qwen/qwen3.8-27b',
        )
        with self.app.app_context():
            analysis = AIAnalysis.query.filter_by(cv_id=self.cv_id).one()
            analysis_id = analysis.id
            self.assertEqual(analysis.match_score, 85)
            self.assertEqual(analysis.strengths, ['Python', 'SQL'])
            self.assertEqual(analysis.interview_history[0]['question'], 'Parlez-moi de votre dernier projet data.')

        page = self.client.get(f'/result/{self.cv_id}')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'85%', page.data)
        self.assertIn('sans saisie ni copier-coller'.encode(), page.data)
        self.assertNotIn('Description de l’offre d’emploi à cibler'.encode(), page.data)
        self.assertIn('Parlez-moi de votre dernier projet data.'.encode(), page.data)
        self.assertIn(b'Gloria', page.data)
        self.assertIn('Simulation d’entretien'.encode(), page.data)
        self.assertIn(b'0 / 10 r\xc3\xa9ponses', page.data)
        self.assertIn(b'Envoyer ma r\xc3\xa9ponse', page.data)
        self.assertIn(b'data-answer-length', page.data)

        with patch('app.routes.extract_cv_text', return_value='CV text'), patch(
            'app.routes.generate_interview_question',
            return_value='Comment validez-vous la qualité des données ?',
        ):
            answer_response = self.client.post(
                f'/analysis/{analysis_id}/interview',
                data={'answer': 'Je vérifie les valeurs manquantes et les doublons.'},
            )
        self.assertEqual(answer_response.status_code, 302)
        self.assertIn('#interview', answer_response.headers['Location'])
        with self.app.app_context():
            analysis = db.session.get(AIAnalysis, analysis_id)
            history = analysis.interview_history
            self.assertEqual(history[0]['answer'], 'Je vérifie les valeurs manquantes et les doublons.')
            self.assertEqual(history[1]['question'], 'Comment validez-vous la qualité des données ?')

    def test_cv_pitch_uses_owned_cv_and_returns_text_for_voice_playback(self):
        pitch = 'Je suis analyste de données et je transforme les chiffres en décisions.'
        with patch('app.routes.extract_cv_text', return_value='CV text with professional experience') as extraction, patch(
            'app.routes.generate_pitch', return_value=pitch
        ) as pitch_service:
            response = self.client.post(f'/result/{self.cv_id}/pitch')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'pitch': pitch})
        extraction.assert_called_once()
        pitch_service.assert_called_once_with(
            'CV text with professional experience',
            groq_key='test-key',
            gemini_key=None,
            mistral_key=None,
            groq_model='qwen/qwen3.8-27b',
            gemini_model='gemini-3.8-flash',
            mistral_model='mistral-small-latest',
        )

        page = self.client.get(f'/result/{self.cv_id}')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Préparer votre présentation orale'.encode(), page.data)
        self.assertIn(b'pitch-form', page.data)
        self.assertIn(b'pitch-play', page.data)

    def test_cv_pitch_cannot_use_another_users_cv(self):
        with patch('app.routes.generate_pitch') as pitch_service:
            response = self.client.post(f'/result/{self.other_cv_id}/pitch')

        self.assertEqual(response.status_code, 404)
        pitch_service.assert_not_called()

    def test_cv_pitch_requires_authentication(self):
        client = self.app.test_client()

        response = client.post(f'/result/{self.cv_id}/pitch')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_cv_pitch_returns_actionable_error_when_no_provider_is_configured(self):
        self.app.config.update(
            GROQ_API_KEY=None,
            GEMINI_API_KEY=None,
            MISTRAL_API_KEY=None,
        )
        with patch('app.routes.extract_cv_text', return_value='CV text with professional experience'):
            response = self.client.post(f'/result/{self.cv_id}/pitch')

        self.assertEqual(response.status_code, 503)
        self.assertIn('Configurez une clé'.encode(), response.json['error'].encode())

    def test_result_ranks_local_offers_and_submits_selected_offer(self):
        jobs_path = Path(self.temp_directory.name) / 'jobs.csv'
        with jobs_path.open('w', encoding='utf-8-sig', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=[
                'title',
                'company',
                'location',
                'published_at',
                'salary',
                'description',
                'skills',
                'source_url',
            ])
            writer.writeheader()
            writer.writerow({
                'title': 'Analyste data Python SQL',
                'company': 'Entreprise locale',
                'location': 'Kinshasa',
                'published_at': '',
                'salary': '',
                'description': 'Analyser des jeux de données avec Python et SQL.',
                'skills': 'python;sql',
                'source_url': 'https://mediacongo.net/emploi-societe-123_data.html',
            })
        self.app.config['JOB_OFFERS_FILE'] = str(jobs_path)

        with patch('app.routes.extract_cv_text', return_value='CV data Python SQL') as extraction:
            page = self.client.get(f'/result/{self.cv_id}')

        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Analyste data Python SQL', page.data)
        self.assertIn(b'Comp\xc3\xa9tences communes : python, sql', page.data)
        self.assertIn(b'Analyser cette offre', page.data)
        self.assertIn(b'sans saisie ni copier-coller', page.data)
        self.assertNotIn(b'Collez ici', page.data)
        extraction.assert_called_once()

        selected_offer = (
            'Intitulé : Analyste data Python SQL\n'
            'Entreprise : Entreprise locale\n'
            'Lieu : Kinshasa\n'
            'Compétences mentionnées : python, sql\n'
            'Description : Analyser des jeux de données avec Python et SQL.'
        )
        with patch('app.routes.extract_cv_text', return_value='CV data Python SQL'), patch(
            'app.routes.analyze_profile',
            return_value=self.analysis_response(),
        ) as analysis_service:
            response = self.client.post(
                f'/result/{self.cv_id}/analyze',
                data={'job_description': selected_offer},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            analysis_service.call_args.args[1],
            selected_offer,
        )

    def test_user_cannot_analyze_another_users_cv(self):
        with patch('app.routes.analyze_profile') as analysis_service:
            response = self.client.post(
                f'/result/{self.other_cv_id}/analyze',
                data={'job_description': 'Poste analyste de données avec Python et SQL.'},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/history', response.headers['Location'])
        analysis_service.assert_not_called()

    def test_missing_groq_key_shows_actionable_message(self):
        self.app.config['GROQ_API_KEY'] = None
        with patch('app.routes.extract_cv_text', return_value='CV text'):
            response = self.client.post(
                f'/result/{self.cv_id}/analyze',
                data={'job_description': 'Poste analyste de données avec Python et SQL.'},
                follow_redirects=True,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GROQ_API_KEY est manquante', response.data)

    def test_tenth_answer_is_saved_without_generating_an_eleventh_question(self):
        with self.app.app_context():
            analysis = AIAnalysis(
                cv_id=self.cv_id,
                job_description='Offre analyste de données avec Python et SQL.',
                summary='Profil expérimenté.',
                match_score=80,
                strengths_json='[]',
                gaps_json='[]',
                interview_history_json=json.dumps([
                    {'question': f'Question {index}', 'answer': 'Réponse précédente'}
                    for index in range(1, 10)
                ] + [{'question': 'Question 10', 'answer': ''}]),
            )
            db.session.add(analysis)
            db.session.commit()
            analysis_id = analysis.id

        with patch('app.routes.generate_interview_question') as next_question:
            response = self.client.post(
                f'/analysis/{analysis_id}/interview',
                data={'answer': 'Ma dernière réponse.'},
            )

        self.assertEqual(response.status_code, 302)
        next_question.assert_not_called()
        with self.app.app_context():
            saved_analysis = db.session.get(AIAnalysis, analysis_id)
            self.assertEqual(len(saved_analysis.interview_history), 10)
            self.assertEqual(saved_analysis.interview_history[-1]['answer'], 'Ma dernière réponse.')

    def test_voice_answer_returns_the_next_question_as_json(self):
        analysis_id = self.create_pending_analysis()
        with patch('app.routes.extract_cv_text', return_value='CV text'), patch(
            'app.routes.generate_interview_question',
            return_value='Quel projet vous a rendu le plus fier ?',
        ):
            response = self.client.post(
                f'/analysis/{analysis_id}/interview',
                data={'answer': 'J’ai construit un outil de suivi des candidatures.'},
                headers={'Accept': 'application/json'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['question'], 'Quel projet vous a rendu le plus fier ?')
        self.assertEqual(response.json['question_number'], 2)
        self.assertFalse(response.json['completed'])
        with self.app.app_context():
            saved_analysis = db.session.get(AIAnalysis, analysis_id)
            self.assertEqual(saved_analysis.interview_history[0]['answer'], 'J’ai construit un outil de suivi des candidatures.')
            self.assertEqual(saved_analysis.interview_history[1]['question'], 'Quel projet vous a rendu le plus fier ?')

    def test_voice_answer_returns_completion_after_the_tenth_answer(self):
        with self.app.app_context():
            analysis = AIAnalysis(
                cv_id=self.cv_id,
                job_description='Offre analyste de données avec Python et SQL.',
                summary='Profil expérimenté.',
                match_score=80,
                strengths_json='[]',
                gaps_json='[]',
                interview_history_json=json.dumps([
                    {'question': f'Question {index}', 'answer': 'Réponse précédente'}
                    for index in range(1, 10)
                ] + [{'question': 'Question 10', 'answer': ''}]),
            )
            db.session.add(analysis)
            db.session.commit()
            analysis_id = analysis.id

        response = self.client.post(
            f'/analysis/{analysis_id}/interview',
            data={'answer': 'Voici ma dernière réponse.'},
            headers={'Accept': 'application/json'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'answered_count': 10, 'completed': True})
        with self.app.app_context():
            saved_analysis = db.session.get(AIAnalysis, analysis_id)
            self.assertEqual(saved_analysis.interview_history[-1]['answer'], 'Voici ma dernière réponse.')

    def create_pending_analysis(self, cv_id=None):
        with self.app.app_context():
            analysis = AIAnalysis(
                cv_id=cv_id or self.cv_id,
                job_description='Offre analyste de données avec Python et SQL.',
                summary='Profil expérimenté.',
                match_score=80,
                strengths_json='[]',
                gaps_json='[]',
                interview_history_json=json.dumps([
                    {'question': 'Parlez-moi de votre expérience avec Python.', 'answer': ''}
                ]),
            )
            db.session.add(analysis)
            db.session.commit()
            return analysis.id

    def test_audio_transcription_returns_text_without_saving_it(self):
        analysis_id = self.create_pending_analysis()
        with patch(
            'app.routes.transcribe_audio',
            return_value='Je maîtrise Python et SQL.',
        ) as transcription:
            response = self.client.post(
                f'/analysis/{analysis_id}/interview/audio',
                data={'audio': (io.BytesIO(b'audio data'), 'answer.webm')},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'transcript': 'Je maîtrise Python et SQL.'})
        self.assertEqual(
            transcription.call_args.args[1:],
            ('answer.webm', 'test-key', 'whisper-large-v3-turbo'),
        )
        with self.app.app_context():
            analysis = db.session.get(AIAnalysis, analysis_id)
            self.assertEqual(analysis.interview_history[0]['answer'], '')

    def test_audio_transcription_rejects_oversized_recordings(self):
        analysis_id = self.create_pending_analysis()
        self.app.config['MAX_AUDIO_SIZE'] = 10
        with patch('app.routes.transcribe_audio') as transcription:
            response = self.client.post(
                f'/analysis/{analysis_id}/interview/audio',
                data={'audio': (io.BytesIO(b'x' * 11), 'answer.webm')},
            )

        self.assertEqual(response.status_code, 413)
        self.assertIn('5 Mo', response.json['error'])
        transcription.assert_not_called()

    def test_audio_transcription_rejects_unsupported_formats(self):
        analysis_id = self.create_pending_analysis()
        with patch('app.routes.transcribe_audio') as transcription:
            response = self.client.post(
                f'/analysis/{analysis_id}/interview/audio',
                data={'audio': (io.BytesIO(b'not audio'), 'answer.exe')},
            )

        self.assertEqual(response.status_code, 400)
        transcription.assert_not_called()

    def test_audio_transcription_reports_missing_api_key(self):
        analysis_id = self.create_pending_analysis()
        self.app.config['GROQ_API_KEY'] = None
        response = self.client.post(
            f'/analysis/{analysis_id}/interview/audio',
            data={'audio': (io.BytesIO(b'audio data'), 'answer.webm')},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn('GROQ_API_KEY est manquante', response.json['error'])

    def test_audio_transcription_rejects_too_long_transcript(self):
        analysis_id = self.create_pending_analysis()
        with patch('app.routes.transcribe_audio', return_value='x' * 4001):
            response = self.client.post(
                f'/analysis/{analysis_id}/interview/audio',
                data={'audio': (io.BytesIO(b'audio data'), 'answer.webm')},
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn('4 000 caractères', response.json['error'])

    def test_audio_transcription_rejects_other_users_analysis(self):
        analysis_id = self.create_pending_analysis(self.other_cv_id)
        with patch('app.routes.transcribe_audio') as transcription:
            response = self.client.post(
                f'/analysis/{analysis_id}/interview/audio',
                data={'audio': (io.BytesIO(b'audio data'), 'answer.webm')},
            )

        self.assertEqual(response.status_code, 404)
        transcription.assert_not_called()

if __name__ == '__main__':
    unittest.main()
