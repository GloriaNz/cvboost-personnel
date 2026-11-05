import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app, db
from app.models import JobOffer, JobSource, JobSyncRun, User
from data_pipeline.job_sync import (
    JobSyncError,
    collect_api_source,
    import_csv,
    sync_job_rows,
)


class JobSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'job-sync-test-secret',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'UPLOAD_FOLDER': str(self.root / 'uploads'),
            'UPLOAD_AUDIT_LOG': str(self.root / 'audit.jsonl'),
        })
        self.root.joinpath('uploads').mkdir(exist_ok=True)
        with self.app.app_context():
            db.create_all()
            self.source = JobSource(
                slug='mediacongo',
                name='MediaCongo',
                base_url='https://mediacongo.net/emplois.html',
            )
            db.session.add(self.source)
            db.session.commit()
            self.source_id = self.source.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temporary_directory.cleanup()

    def row(self, **overrides):
        data = {
            'title': 'Développeur Python junior',
            'company': 'Entreprise RDC',
            'location': 'Kinshasa',
            'published_at': '01.11.2026',
            'description': 'Stage informatique avec Python et Docker.',
            'source_url': 'https://mediacongo.net/emploi-societe-45071_offer.html',
        }
        data.update(overrides)
        return data

    def test_sync_inserts_and_updates_by_url_without_duplicating(self):
        with self.app.app_context():
            source = db.session.get(JobSource, self.source_id)
            first = sync_job_rows(source, [self.row()])
            offer_id = JobOffer.query.one().id
            second = sync_job_rows(source, [
                self.row(description='Stage informatique avec Python, Docker et AWS.')
            ])

            self.assertEqual((first.fetched_count, first.added_count, first.updated_count), (1, 1, 0))
            self.assertEqual((second.added_count, second.updated_count), (0, 1))
            self.assertEqual(JobOffer.query.count(), 1)
            offer = db.session.get(JobOffer, offer_id)
            self.assertIn('aws', offer.skills_json)
            self.assertEqual(offer.contract_type, 'Stage')
            self.assertEqual(offer.experience_level, 'Junior')

    def test_sync_deduplicates_by_content_and_rejects_untrusted_domains(self):
        with self.app.app_context():
            source = db.session.get(JobSource, self.source_id)
            sync_job_rows(source, [self.row()])
            updated = sync_job_rows(source, [
                self.row(source_url='https://www.mediacongo.net/emploi-societe-99999_copy.html')
            ])
            self.assertEqual(updated.added_count, 0)
            self.assertEqual(JobOffer.query.count(), 1)
            with self.assertRaises(JobSyncError):
                sync_job_rows(source, [self.row(source_url='https://example.com/job')])
            failed = JobSyncRun.query.order_by(JobSyncRun.id.desc()).first()
            self.assertEqual(failed.status, 'failed')
            self.assertEqual(JobOffer.query.count(), 1)

    def test_import_csv_records_a_sync_run(self):
        path = self.root / 'offers.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=['title', 'company', 'description', 'source_url'],
                extrasaction='ignore',
            )
            writer.writeheader()
            writer.writerow(self.row())

        with self.app.app_context():
            run = import_csv(path)
            self.assertEqual(run.status, 'completed')
            self.assertEqual(run.added_count, 1)
            self.assertEqual(JobOffer.query.count(), 1)

    def test_api_source_collection_syncs_normalized_jobs(self):
        api_row = {
            'title': 'Analyste Python',
            'company': 'Entreprise distante',
            'location': 'Remote',
            'published_at': '2026-11-05',
            'description': 'Analyse des données Python.',
            'source_url': 'https://himalayas.app/jobs/data-analyst',
            'reference': 'himalayas-1',
        }
        with self.app.app_context(), patch(
            'data_pipeline.job_sync.fetch_source_jobs', return_value=[api_row]
        ):
            run = collect_api_source('himalayas', limit=5)

            offer = JobOffer.query.filter_by(external_id='himalayas-1').one()
            self.assertEqual(run.status, 'completed')
            self.assertEqual(run.added_count, 1)
            self.assertEqual(offer.source.slug, 'himalayas')
            self.assertEqual(offer.title, 'Analyste Python')

    def test_remotive_collection_requires_republication_approval(self):
        with self.app.app_context(), self.assertRaisesRegex(JobSyncError, 'autorisation explicite'):
            collect_api_source('remotive')

    def test_users_are_not_required_to_be_sources_or_admins_to_use_job_models(self):
        with self.app.app_context():
            user = User(
                nom='Test',
                prenom='Candidate',
                email='candidate@example.com',
                password_hash='unused',
            )
            db.session.add(user)
            db.session.commit()
            self.assertEqual(JobSource.query.count(), 1)


if __name__ == '__main__':
    unittest.main()
