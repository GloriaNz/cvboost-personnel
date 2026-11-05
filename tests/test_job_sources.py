import unittest
from unittest.mock import Mock

from data_pipeline.job_sources import (
    fetch_source_jobs,
    parse_adzuna,
    parse_himalayas,
    parse_jobicy,
    parse_remotive,
)


class JobSourceParsingTests(unittest.TestCase):
    def test_parses_himalayas_fields_and_strips_description_html(self):
        jobs = parse_himalayas({
            'jobs': [{
                'title': 'Analyste Python',
                'companyName': 'Entreprise',
                'locationRestrictions': ['RDC', 'Remote'],
                'pubDate': 1793883221,
                'minSalary': 1000,
                'maxSalary': 2000,
                'currency': 'USD',
                'salaryPeriod': 'monthly',
                'description': '<p>Python <strong>et SQL</strong></p>',
                'applicationLink': 'https://himalayas.app/jobs/analyste-python',
                'guid': 'himalayas-1',
            }],
        })

        self.assertEqual(jobs[0]['title'], 'Analyste Python')
        self.assertEqual(jobs[0]['location'], 'RDC, Remote')
        self.assertEqual(jobs[0]['description'], 'Python et SQL')
        self.assertEqual(jobs[0]['salary'], '1000 - 2000 USD monthly')
        self.assertEqual(jobs[0]['reference'], 'himalayas-1')

    def test_parses_jobicy_remotive_and_adzuna_shapes(self):
        jobicy = parse_jobicy({'jobs': [{
            'id': 42,
            'jobTitle': 'Comptable',
            'companyName': 'ACME',
            'jobGeo': 'RDC',
            'jobDescription': '<p>Finance</p>',
            'url': 'https://jobicy.com/jobs/42-comptable',
        }]})
        remotive = parse_remotive({'jobs': [{
            'id': 43,
            'title': 'Infirmier',
            'company_name': 'Santé',
            'candidate_required_location': 'Worldwide',
            'description': '<p>Soins</p>',
            'url': 'https://remotive.com/remote-jobs/healthcare/infirmier-43',
        }]})
        adzuna = parse_adzuna({'results': [{
            'id': '44',
            'title': 'Ingénieur',
            'company': {'display_name': 'Tech'},
            'location': {'display_name': 'Kinshasa'},
            'description': 'Python',
            'redirect_url': 'https://adzuna.com/jobs/land/ad/44',
        }]})

        self.assertEqual(jobicy[0]['title'], 'Comptable')
        self.assertEqual(remotive[0]['company'], 'Santé')
        self.assertEqual(adzuna[0]['location'], 'Kinshasa')
        self.assertEqual(adzuna[0]['reference'], '44')

    def test_adzuna_requires_credentials_and_uses_configured_country(self):
        with self.assertRaisesRegex(RuntimeError, 'ADZUNA_APP_ID'):
            fetch_source_jobs('adzuna', {}, session=Mock())

        session = Mock()
        response = Mock()
        response.json.return_value = {'results': []}
        session.get.return_value = response
        jobs = fetch_source_jobs(
            'adzuna',
            {
                'ADZUNA_APP_ID': 'app-id',
                'ADZUNA_APP_KEY': 'app-key',
                'ADZUNA_COUNTRY': 'za',
            },
            limit=12,
            session=session,
        )

        self.assertEqual(jobs, [])
        self.assertIn('/jobs/za/search/1', session.get.call_args.args[0])
        self.assertEqual(session.get.call_args.kwargs['params']['results_per_page'], 12)


if __name__ == '__main__':
    unittest.main()
