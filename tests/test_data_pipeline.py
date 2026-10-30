import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_pipeline.analytics import get_upload_kpis, ingest_upload_logs
from data_pipeline.logs_parser import parse_upload_logs
from data_pipeline.pandas_cleaning import clean_jobs, parse_salary


class DataPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def write_log(self, events, malformed_line=None):
        log_path = self.root / 'uploads.jsonl'
        lines = [json.dumps(event) for event in events]
        if malformed_line:
            lines.append(malformed_line)
        log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return log_path

    @staticmethod
    def make_event(event_id, user_id, outcome, reason='', extension='pdf', size=100):
        return {
            'event_id': event_id,
            'timestamp': '2026-10-26T10:00:00+00:00',
            'event': 'upload',
            'user_id': user_id,
            'filename': 'Jean Dupont CV.pdf',
            'extension': extension,
            'size_bytes': size,
            'outcome': outcome,
            'reason': reason,
        }

    def test_upload_parser_flags_unsupported_file_and_repeated_failures(self):
        events = [
            self.make_event('bad-extension', 'user-1', 'rejected', 'unsupported_extension', 'exe'),
            self.make_event('failure-1', 'user-2', 'rejected', 'invalid_form'),
            self.make_event('failure-2', 'user-2', 'rejected', 'invalid_form'),
            self.make_event('failure-3', 'user-2', 'rejected', 'invalid_form'),
        ]
        result = parse_upload_logs(self.write_log(events))

        self.assertEqual(result.errors, [])
        self.assertTrue(result.events[0]['suspicious'])
        self.assertEqual(result.events[0]['suspicious_reason'], 'unsupported_extension')
        self.assertTrue(all(event['suspicious'] for event in result.events[1:]))
        self.assertTrue(all(
            event['suspicious_reason'] == 'repeated_failed_uploads'
            for event in result.events[1:]
        ))
        self.assertEqual(result.events[0]['filename'], 'upload.exe')

    def test_upload_parser_reports_malformed_rows(self):
        result = parse_upload_logs(
            self.write_log(
                [self.make_event('accepted', 'user-1', 'accepted')],
                malformed_line='{invalid json',
            )
        )
        self.assertEqual(len(result.events), 1)
        self.assertEqual(len(result.errors), 1)
        self.assertIn('Ligne 2', result.errors[0])

    def test_analytics_ingestion_is_idempotent_and_kpis_use_having(self):
        events = [
            self.make_event('a1', 'user-1', 'accepted'),
            self.make_event('a2', 'user-1', 'accepted', extension='docx'),
            self.make_event('b1', 'user-2', 'rejected', 'file_too_large'),
        ]
        log_path = self.write_log(events)
        database = self.root / 'analytics.db'

        self.assertEqual(ingest_upload_logs(log_path, database), 3)
        self.assertEqual(ingest_upload_logs(log_path, database), 3)
        kpis = get_upload_kpis(database, minimum_uploads=2)

        self.assertEqual(kpis['totals']['total_uploads'], 3)
        self.assertEqual(kpis['totals']['accepted_uploads'], 2)
        self.assertEqual(kpis['totals']['rejected_uploads'], 1)
        self.assertEqual(len(kpis['by_user']), 1)
        self.assertEqual(kpis['by_user'][0]['user_id'], 'user-1')
        self.assertEqual(len(kpis['by_extension']), 1)
        self.assertEqual(kpis['by_extension'][0]['extension'], 'pdf')

    def test_salary_normalization_preserves_currency_and_range(self):
        self.assertEqual(
            parse_salary('1 200 - 1 500 USD'),
            {'salary_min': 1200.0, 'salary_max': 1500.0, 'salary_currency': 'USD'},
        )
        self.assertEqual(
            parse_salary('2.500,50 CDF'),
            {'salary_min': 2500.5, 'salary_max': 2500.5, 'salary_currency': 'CDF'},
        )
        self.assertEqual(
            parse_salary('Selon profil'),
            {'salary_min': None, 'salary_max': None, 'salary_currency': ''},
        )

    def test_cleaning_deduplicates_normalizes_and_encodes_skills(self):
        input_path = self.root / 'jobs.csv'
        output_path = self.root / 'clean.csv'
        pd.DataFrame([
            {
                'title': '  Analyste  Data ',
                'company': ' Talent RDC ',
                'location': None,
                'published_at': '24.10.2026',
                'salary': '1 200 - 1 500 USD',
                'description': 'Python, SQL et Power BI',
                'source_url': 'https://example.test/job/1',
            },
            {
                'title': 'Analyste Data',
                'company': 'Talent RDC',
                'location': 'Kinshasa',
                'published_at': '24.10.2026',
                'salary': '999 USD',
                'description': 'Excel',
                'source_url': 'https://example.test/job/1',
            },
            {
                'title': '',
                'company': 'Sans titre',
                'location': 'Kinshasa',
                'published_at': '',
                'salary': '',
                'description': '',
                'source_url': 'https://example.test/job/2',
            },
        ]).to_csv(input_path, index=False)

        cleaned = clean_jobs(input_path)
        cleaned.to_csv(output_path, index=False)

        self.assertEqual(len(cleaned), 1)
        row = cleaned.iloc[0]
        self.assertEqual(row['title'], 'Analyste Data')
        self.assertEqual(row['location'], 'Non précisé')
        self.assertEqual(row['salary_min'], 1200.0)
        self.assertEqual(row['salary_max'], 1500.0)
        self.assertEqual(row['salary_currency'], 'USD')
        self.assertEqual(row['published_date'], '2026-10-24')
        self.assertEqual(row['skills'], 'python;sql;power bi')
        self.assertEqual(row['skill_python'], 1)
        self.assertTrue(output_path.exists())

    def test_cleaning_empty_input_returns_empty_frame_with_normalized_fields(self):
        input_path = self.root / 'empty.csv'
        pd.DataFrame(columns=['title', 'salary']).to_csv(input_path, index=False)

        cleaned = clean_jobs(input_path)

        self.assertTrue(cleaned.empty)
        self.assertIn('salary_min', cleaned.columns)
        self.assertIn('published_date', cleaned.columns)


if __name__ == '__main__':
    unittest.main()
