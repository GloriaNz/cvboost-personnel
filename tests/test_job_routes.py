from datetime import date, timedelta
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import AIAnalysis, CV, JobAlertPreference, JobOffer, JobSource, User


class JobRouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.uploads = self.root / 'uploads'
        self.uploads.mkdir()
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'jobs-test-secret',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'WTF_CSRF_ENABLED': False,
            'UPLOAD_FOLDER': str(self.uploads),
            'UPLOAD_AUDIT_LOG': str(self.root / 'audit.jsonl'),
            'JOB_ADMIN_EMAILS': '',
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            candidate = User(
                nom='Candidate',
                prenom='Gloria',
                email='gloria@example.com',
                password_hash=generate_password_hash('password-test'),
            )
            other = User(
                nom='Other',
                prenom='Candidate',
                email='other@example.com',
                password_hash=generate_password_hash('password-test'),
            )
            db.session.add_all([candidate, other])
            db.session.flush()
            self.candidate_id = candidate.id
            self.cv = CV(
                filename_original='CV.pdf',
                filename_stored='candidate.pdf',
                user_id=candidate.id,
            )
            self.other_cv = CV(
                filename_original='CV autre.pdf',
                filename_stored='other.pdf',
                user_id=other.id,
            )
            source = JobSource(
                slug='mediacongo',
                name='MediaCongo',
                base_url='https://mediacongo.net/emplois.html',
            )
            db.session.add_all([self.cv, self.other_cv, source])
            db.session.flush()
            self.cv_id = self.cv.id
            self.other_cv_id = self.other_cv.id
            self.offer = JobOffer(
                source_id=source.id,
                external_id='45071',
                source_url='https://mediacongo.net/emploi-societe-45071_offer.html',
                content_hash='test-hash',
                title='Développeur Python',
                company='Entreprise RDC',
                description='Développer une API Python et Docker.',
                skills_json=json.dumps(['python', 'docker']),
                location='Kinshasa',
                contract_type='CDI',
                experience_level='Junior',
                is_remote=True,
                status='active',
            )
            db.session.add(self.offer)
            db.session.commit()
        (self.uploads / 'candidate.pdf').write_bytes(b'PDF')
        (self.uploads / 'other.pdf').write_bytes(b'PDF')
        self.client.post(
            '/login',
            data={'email': 'gloria@example.com', 'password': 'password-test'},
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temporary_directory.cleanup()

    def test_job_search_filters_offers_and_matches_only_the_current_users_cv(self):
        with self.app.app_context():
            self.app.config['JOB_OFFERS_FILE'] = str(self.root / 'missing.csv')
        with patch(
            'app.routes.extract_cv_text',
            return_value='Compétence Python et analyse de données.',
        ):
            response = self.client.get('/jobs?' + urlencode({
                'q': 'Développeur',
                'location': 'Kinshasa',
                'skills': 'python',
                'contract_type': 'CDI',
                'experience_level': 'Junior',
                'remote': '1',
                'cv_id': self.cv_id,
            }))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'D\xc3\xa9veloppeur Python', response.data)
        self.assertIn(b'50 % de comp\xc3\xa9tences communes', response.data)
        self.assertIn(b'python', response.data)

    def test_job_search_does_not_allow_matching_against_another_users_cv(self):
        response = self.client.get(f'/jobs?cv_id={self.other_cv_id}')
        self.assertEqual(response.status_code, 404)

    def test_job_search_displays_all_active_offers(self):
        with self.app.app_context():
            source_id = JobSource.query.filter_by(slug='mediacongo').one().id
            db.session.add_all([
                JobOffer(
                    source_id=source_id,
                    external_id=f'all-offers-{index}',
                    source_url=f'https://mediacongo.net/emploi-societe-{index}_offer.html',
                    content_hash=f'all-offers-hash-{index}',
                    title=f'Offre complète {index}',
                    description='Description détaillée de cette offre.',
                    skills_json='[]',
                    status='active',
                )
                for index in range(500)
            ])
            db.session.commit()

        response = self.client.get('/jobs')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Offre compl\xc3\xa8te 499', response.data)

    def test_deadline_filter_excludes_expired_offers_and_matches_the_selected_window(self):
        with self.app.app_context():
            source_id = JobSource.query.filter_by(slug='mediacongo').one().id
            db.session.add_all([
                JobOffer(
                    source_id=source_id,
                    external_id='deadline-soon',
                    source_url='https://mediacongo.net/emploi-societe-101_soon.html',
                    content_hash='deadline-soon',
                    title='Deadline soon',
                    skills_json='[]',
                    deadline=date.today() + timedelta(days=5),
                ),
                JobOffer(
                    source_id=source_id,
                    external_id='deadline-passed',
                    source_url='https://mediacongo.net/emploi-societe-102_expired.html',
                    content_hash='deadline-passed',
                    title='Deadline passed',
                    skills_json='[]',
                    deadline=date.today() - timedelta(days=1),
                ),
            ])
            db.session.commit()

        response = self.client.get('/jobs?deadline=7')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Deadline soon', response.data)
        self.assertNotIn(b'Deadline passed', response.data)
        self.assertNotIn(b'D\xc3\xa9veloppeur Python', response.data)

    def test_database_offer_uses_the_existing_cv_analysis_flow(self):
        response = self.client.get(f'/jobs?cv_id={self.cv_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Analyser cette offre avec ce CV', response.data)
        self.assertIn(
            f'action="/result/{self.cv_id}/analyze"'.encode(),
            response.data,
        )

        with patch(
            'app.routes.extract_cv_text',
            return_value='Expérience professionnelle en Python.',
        ), patch(
            'app.routes.analyze_profile',
            return_value={
                'summary': 'Profil adapté.',
                'matching_percentage': 75,
                'strengths': ['Python'],
                'gaps': ['Docker'],
                'first_interview_question': 'Parlez de Python.',
            },
        ):
            response = self.client.post(
                f'/result/{self.cv_id}/analyze',
                data={
                    'job_description': (
                        'Intitulé : Développeur Python\n'
                        'Entreprise : Entreprise RDC\n'
                        'Localisation : Kinshasa\n'
                        'Description : Développer une API Python et Docker.'
                    )
                },
            )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            analysis = AIAnalysis.query.filter_by(cv_id=self.cv_id).one()
            self.assertIn('Développeur Python', analysis.job_description)

    def test_saves_alert_preferences_per_user_without_claiming_delivery(self):
        response = self.client.post('/jobs/preferences', data={
            'keywords': 'backend développeur',
            'skills': 'Python, Docker',
            'location': 'Kinshasa',
            'contract_type': 'CDI',
            'experience_level': 'Junior',
            'is_remote': 'y',
            'enabled': 'y',
        })

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            preference = JobAlertPreference.query.filter_by(user_id=self.candidate_id).one()
            self.assertEqual(preference.skills_json, '["python", "docker"]')
            self.assertEqual(preference.contract_type, 'CDI')
            self.assertTrue(preference.is_remote)
            self.assertTrue(preference.enabled)

    def test_job_admin_page_requires_an_allowlisted_email(self):
        response = self.client.get('/admin/job-intelligence')
        self.assertEqual(response.status_code, 404)

        self.app.config['JOB_ADMIN_EMAILS'] = ' Gloria@Example.com '
        response = self.client.get('/admin/job-intelligence')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sources & synchronisations', response.data)


if __name__ == '__main__':
    unittest.main()
