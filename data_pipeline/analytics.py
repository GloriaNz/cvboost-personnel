import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from data_pipeline.logs_parser import parse_upload_logs


SCHEMA = """
CREATE TABLE IF NOT EXISTS upload_events (
    event_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    user_id TEXT,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    size_bytes INTEGER,
    outcome TEXT NOT NULL,
    reason TEXT NOT NULL,
    suspicious INTEGER NOT NULL CHECK (suspicious IN (0, 1)),
    suspicious_reason TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_upload_events_timestamp
    ON upload_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_upload_events_user
    ON upload_events(user_id);
"""


def initialize_database(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(SCHEMA)


def ingest_upload_logs(log_path, database_path, repeated_failure_threshold=3):
    result = parse_upload_logs(log_path, repeated_failure_threshold)
    if result.errors:
        details = '\n'.join(result.errors)
        raise ValueError(f'Le journal contient des lignes invalides :\n{details}')

    initialize_database(database_path)
    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO upload_events (
                    event_id, timestamp, user_id, filename, extension, size_bytes,
                    outcome, reason, suspicious, suspicious_reason
                ) VALUES (
                    :event_id, :timestamp, :user_id, :filename, :extension, :size_bytes,
                    :outcome, :reason, :suspicious, :suspicious_reason
                )
                """,
                [
                    {**event, 'suspicious': int(event['suspicious'])}
                    for event in result.events
                ],
            )
            return connection.execute('SELECT COUNT(*) FROM upload_events').fetchone()[0]


def get_upload_kpis(database_path, minimum_uploads=1):
    if minimum_uploads < 1:
        raise ValueError('minimum_uploads doit être supérieur ou égal à 1.')

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        return {
            'totals': dict(connection.execute(
                """
                SELECT
                    COUNT(*) AS total_uploads,
                    COALESCE(SUM(outcome = 'accepted'), 0) AS accepted_uploads,
                    COALESCE(SUM(outcome != 'accepted'), 0) AS rejected_uploads,
                    COALESCE(SUM(suspicious), 0) AS suspicious_uploads,
                    AVG(size_bytes) AS average_size_bytes
                FROM upload_events
                """
            ).fetchone()),
            'daily': [
                dict(row) for row in connection.execute(
                    """
                    SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS uploads
                    FROM upload_events
                    GROUP BY day
                    HAVING COUNT(*) >= ?
                    ORDER BY day
                    """,
                    (minimum_uploads,),
                )
            ],
            'by_user': [
                dict(row) for row in connection.execute(
                    """
                    SELECT user_id, COUNT(*) AS uploads,
                           SUM(suspicious) AS suspicious_uploads
                    FROM upload_events
                    WHERE user_id IS NOT NULL AND user_id != ''
                    GROUP BY user_id
                    HAVING COUNT(*) >= ?
                    ORDER BY uploads DESC, user_id
                    """,
                    (minimum_uploads,),
                )
            ],
            'by_extension': [
                dict(row) for row in connection.execute(
                    """
                    SELECT extension, COUNT(*) AS uploads
                    FROM upload_events
                    GROUP BY extension
                    HAVING COUNT(*) >= ?
                    ORDER BY uploads DESC, extension
                    """,
                    (minimum_uploads,),
                )
            ],
        }


def main():
    parser = argparse.ArgumentParser(description='Charge les événements dans SQLite et affiche les KPI.')
    parser.add_argument('--logs', required=True, help='Fichier JSONL de journal d’upload.')
    parser.add_argument('--database', default='instance/analytics.db')
    parser.add_argument('--minimum-uploads', type=int, default=1)
    parser.add_argument('--threshold', type=int, default=3)
    args = parser.parse_args()

    total = ingest_upload_logs(args.logs, args.database, args.threshold)
    print(f'Base analytique mise à jour : {total} événements')
    kpis = get_upload_kpis(args.database, args.minimum_uploads)
    for section, rows in kpis.items():
        print(f'\n{section}:')
        for row in rows if isinstance(rows, list) else [rows]:
            print(row)


if __name__ == '__main__':
    main()
