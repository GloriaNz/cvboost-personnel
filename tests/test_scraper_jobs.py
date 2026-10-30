import io
import sys
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

import requests
from data_pipeline.scraper_jobs import (
    BASE_URL,
    MediaCongoScraper,
    main,
    parse_detail,
    parse_listing,
)


LISTING_HTML = """
<table class="table_datas">
  <tr><th>Fonction</th><th>Organisme</th><th>Lieu</th><th>Publiée</th></tr>
  <tr>
    <td></td>
    <td><a href="emploi-societe-123_job.html">
      <strong>Analyste de données</strong>
      <strong class="format_id_emploi">OEM123</strong>
    </a></td>
    <td class="grey">Talent RDC</td>
    <td>Kinshasa</td>
    <td>24.10.2026</td>
  </tr>
</table>
"""


DETAIL_HTML = """
<h1>Analyste de données</h1>
<div class="emploi_section">Lieu</div>
<div class="article_ttext"><p>Kinshasa</p></div>
<div class="emploi_section">Organisme</div>
<div class="article_ttext"><p>Talent RDC</p></div>
<div class="emploi_section">Description</div>
<div class="article_ttext"><p>Analyser et préparer les données.</p></div>
<div class="emploi_section">Rémunération</div>
<div class="article_ttext"><p>Selon profil</p></div>
"""


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.urls = []

    def get(self, url, timeout):
        self.urls.append(url)
        return FakeResponse(self.responses.pop(0))


class ScraperJobsTests(unittest.TestCase):
    def test_parses_listing_fields_and_ignores_non_job_links(self):
        html = LISTING_HTML.replace(
            '<tr><th>Fonction</th>',
            '<tr><td><a href="not-a-job.html">Autre lien</a></td></tr>'
            '<tr><th>Fonction</th>',
        )
        jobs = parse_listing(html)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['title'], 'Analyste de données')
        self.assertEqual(jobs[0]['company'], 'Talent RDC')
        self.assertEqual(jobs[0]['location'], 'Kinshasa')
        self.assertEqual(jobs[0]['reference'], 'OEM123')
        self.assertEqual(
            jobs[0]['source_url'],
            f'{BASE_URL}/emploi-societe-123_job.html',
        )

    def test_parses_detail_description_and_salary(self):
        result = parse_detail(DETAIL_HTML)
        self.assertEqual(result['description'], 'Analyser et préparer les données.')
        self.assertEqual(result['salary'], 'Selon profil')

    def test_parses_absent_salary_as_empty(self):
        html = DETAIL_HTML.replace('Rémunération', 'Informations')
        result = parse_detail(html)
        self.assertEqual(result['salary'], '')

    def test_scraper_honors_ten_second_minimum_crawl_delay(self):
        session = FakeSession([
            'User-agent: *\nCrawl-delay: 1',
            LISTING_HTML,
            DETAIL_HTML,
        ])
        sleeps = []
        scraper = MediaCongoScraper(
            session=session,
            sleep=sleeps.append,
            clock=lambda: 0.0,
        )
        jobs = scraper.scrape(limit=1, detail_limit=1)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['description'], 'Analyser et préparer les données.')
        self.assertEqual(sleeps, [10.0, 10.0])
        self.assertEqual(
            session.urls,
            [
                f'{BASE_URL}/robots.txt',
                f'{BASE_URL}/emplois.html',
                f'{BASE_URL}/emploi-societe-123_job.html',
            ],
        )

    def test_cli_reports_network_failure_without_traceback(self):
        error_output = io.StringIO()
        with patch.object(sys, 'argv', ['scraper_jobs.py']), patch(
            'data_pipeline.scraper_jobs.MediaCongoScraper.scrape',
            side_effect=requests.ConnectionError('connexion interrompue'),
        ), redirect_stderr(error_output):
            with self.assertRaises(SystemExit) as error:
                main()

        self.assertEqual(error.exception.code, 1)
        self.assertIn('Erreur réseau pendant la collecte MediaCongo', error_output.getvalue())
        self.assertIn('Le fichier CSV n’a pas été créé.', error_output.getvalue())
        self.assertNotIn('Traceback', error_output.getvalue())


if __name__ == '__main__':
    unittest.main()
