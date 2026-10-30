import csv
import tempfile
import unittest
from pathlib import Path

from data_pipeline.job_matching import JobOffersError, rank_job_offers


class JobMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_directory.name) / 'jobs.csv'

    def tearDown(self):
        self.temp_directory.cleanup()

    def write_jobs(self, rows):
        with self.path.open('w', encoding='utf-8-sig', newline='') as csv_file:
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
            writer.writerows(rows)

    def test_ranks_offers_by_shared_skills_and_builds_analysis_text(self):
        self.write_jobs([
            {
                'title': 'Assistant administratif',
                'company': 'Organisation A',
                'location': 'Kinshasa',
                'published_at': '',
                'salary': '',
                'description': 'Saisie et suivi des dossiers.',
                'skills': 'excel',
                'source_url': 'https://mediacongo.net/emploi-societe-1_offer.html',
            },
            {
                'title': 'Analyste data Python SQL',
                'company': 'Organisation B',
                'location': 'Kinshasa',
                'published_at': '2026-10-20',
                'salary': '1 000 USD',
                'description': 'Préparer des données avec Python et SQL.',
                'skills': 'python;sql',
                'source_url': 'javascript:alert(1)',
            },
        ])

        jobs = rank_job_offers(self.path, 'Expérience en Python, SQL et Excel.')

        self.assertEqual(jobs[0]['title'], 'Analyste data Python SQL')
        self.assertEqual(jobs[0]['matching_skills'], ['python', 'sql'])
        self.assertIn('Description : Préparer des données', jobs[0]['analysis_text'])
        self.assertEqual(jobs[0]['source_url'], '')
        self.assertEqual(jobs[1]['matching_skills'], ['excel'])

    def test_missing_job_file_returns_no_offers(self):
        self.assertEqual(
            rank_job_offers(self.path, 'CV avec Python.'),
            [],
        )

    def test_csv_without_title_column_is_rejected(self):
        self.path.write_text('company,description\nACME,Python\n', encoding='utf-8')

        with self.assertRaisesRegex(JobOffersError, 'colonne « title »'):
            rank_job_offers(self.path, 'CV avec Python.')

    def test_oversized_offer_remains_visible_but_cannot_be_analyzed(self):
        self.write_jobs([{
            'title': 'Poste analyste des données',
            'company': 'Entreprise',
            'location': '',
            'published_at': '',
            'salary': '',
            'description': 'Python ' * 2000,
            'skills': 'python',
            'source_url': '',
        }])

        jobs = rank_job_offers(self.path, 'CV avec Python.')

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['analysis_text'], '')
        self.assertIn('12 000 caractères', jobs[0]['analysis_error'])


if __name__ == '__main__':
    unittest.main()
