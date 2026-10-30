import argparse
import csv
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


BASE_URL = 'https://mediacongo.net'
LISTING_URL = f'{BASE_URL}/emplois.html'
USER_AGENT = 'CVBoostJobCollector/1.0 (respecting robots.txt)'
JOB_PATH_PATTERN = re.compile(r'^/emploi-societe-\d+_[^/]+\.html$')
CSV_FIELDS = (
    'title',
    'company',
    'location',
    'published_at',
    'salary',
    'description',
    'source_url',
)


class MediaCongoScraper:
    def __init__(self, session=None, sleep=time.sleep, clock=time.monotonic):
        self.session = session or requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.sleep = sleep
        self.clock = clock
        self._robots = None
        self._crawl_delay = 10
        self._last_request_at = None

    def _load_robots(self):
        robots_url = f'{BASE_URL}/robots.txt'
        response = self.session.get(robots_url, timeout=20)
        response.raise_for_status()
        robots = RobotFileParser(robots_url)
        robots.parse(response.text.splitlines())
        self._robots = robots
        self._crawl_delay = max(10, robots.crawl_delay(USER_AGENT) or 0)
        self._last_request_at = self.clock()

    def _get(self, url):
        if self._robots is None:
            self._load_robots()

        parsed_url = urlparse(url)
        if parsed_url.netloc not in {'mediacongo.net', 'www.mediacongo.net'}:
            raise ValueError(f'URL hors du domaine autorisé : {url}')
        if not self._robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f'URL interdite par robots.txt : {url}')

        elapsed = self.clock() - self._last_request_at
        remaining = self._crawl_delay - elapsed
        if remaining > 0:
            self.sleep(remaining)
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        self._last_request_at = self.clock()
        return response.text

    def scrape(self, limit=50, detail_limit=0):
        if limit < 1:
            raise ValueError('limit doit être supérieur ou égal à 1.')
        if detail_limit < 0 or detail_limit > limit:
            raise ValueError('detail_limit doit être compris entre 0 et limit.')

        listing_html = self._get(LISTING_URL)
        jobs = parse_listing(listing_html, limit=limit)
        if not jobs:
            raise RuntimeError('Aucune offre trouvée : la structure de la page a peut-être changé.')

        for job in jobs[:detail_limit]:
            detail_html = self._get(job['source_url'])
            job.update(parse_detail(detail_html))
        return jobs


def parse_listing(html, limit=50):
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []

    for row in soup.select('table.table_datas tr'):
        link = row.select_one('a[href*="emploi-societe-"]')
        if not link:
            continue

        source_url = urljoin(BASE_URL + '/', link['href'])
        path = urlparse(source_url).path
        if not JOB_PATH_PATTERN.fullmatch(path):
            continue

        cells = row.find_all('td', recursive=False)
        if len(cells) < 5:
            continue

        title_tag = row.select_one('.format_id_emploi')
        title_link = title_tag.find_parent('a') if title_tag else link
        title = ' '.join(
            part.get_text(' ', strip=True)
            for part in title_link.find_all('strong')
            if 'format_id_emploi' not in part.get('class', [])
        ).strip()
        if not title:
            title = title_link.get_text(' ', strip=True)
        reference_tag = row.select_one('.format_id_emploi')
        reference = reference_tag.get_text(' ', strip=True) if reference_tag else ''

        jobs.append({
            'title': title,
            'company': cells[2].get_text(' ', strip=True),
            'location': cells[3].get_text(' ', strip=True),
            'published_at': cells[4].get_text(' ', strip=True),
            'salary': '',
            'description': '',
            'reference': reference,
            'source_url': source_url,
        })
        if len(jobs) >= limit:
            break

    return jobs


def parse_detail(html):
    soup = BeautifulSoup(html, 'html.parser')
    description_parts = []
    salary = ''

    for heading in soup.select('.emploi_section'):
        label = heading.get_text(' ', strip=True).casefold()
        content = heading.find_next_sibling('div', class_='article_ttext')
        if not content:
            continue
        text = content.get_text(' ', strip=True)
        if label == 'description':
            if text:
                description_parts.append(text)
        elif label in {'salaire', 'rémunération', 'remuneration'}:
            salary = text

    return {
        'description': '\n'.join(description_parts),
        'salary': salary,
    }


def write_csv(jobs, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(jobs)
    return output


def main():
    parser = argparse.ArgumentParser(description='Collecte polie des offres MediaCongo en RDC.')
    parser.add_argument('--limit', type=int, default=20, help='Nombre maximal d’offres à lire.')
    parser.add_argument(
        '--details',
        type=int,
        default=0,
        help='Nombre maximal de pages détail à lire (10 secondes minimum entre requêtes).',
    )
    parser.add_argument(
        '--output',
        default='data_pipeline/jobs_mediacongo.csv',
        help='Chemin du fichier CSV généré.',
    )
    args = parser.parse_args()

    try:
        jobs = MediaCongoScraper().scrape(limit=args.limit, detail_limit=args.details)
    except requests.RequestException as error:
        parser.exit(
            1,
            f'Erreur réseau pendant la collecte MediaCongo : {error}\n'
            'Vérifiez votre connexion et réessayez plus tard. '
            'Le fichier CSV n’a pas été créé.\n',
        )
    output = write_csv(jobs, args.output)
    print(f'{len(jobs)} offres enregistrées dans {output.resolve()}')
    print(f'Collecte terminée le {datetime.now().astimezone().isoformat(timespec="seconds")}')


if __name__ == '__main__':
    main()
