import argparse
import logging
import time

from app import create_app, db
from app.job_alerts import JobAlertConfigurationError, send_matching_job_alerts
from data_pipeline.job_sync import JobSyncError, collect_mediacongo, import_csv, refresh_expired_offers


logger = logging.getLogger(__name__)


def _interval(value):
    try:
        hours = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('L’intervalle doit être un nombre entier d’heures.') from error
    if hours < 2 or hours > 4:
        raise argparse.ArgumentTypeError('L’intervalle doit être compris entre 2 et 4 heures.')
    return hours


def _run_once(app, limit, input_csv=None):
    with app.app_context():
        db.create_all()
        run = import_csv(input_csv) if input_csv else collect_mediacongo(limit=limit)
        expired_count = refresh_expired_offers()
        try:
            alert_count = send_matching_job_alerts()
        except JobAlertConfigurationError as error:
            logger.warning('%s', error)
            alert_count = 0
        print(
            f'Synchronisation {run.source.name} terminée : {run.fetched_count} récupérées, '
            f'{run.added_count} ajoutées, {run.updated_count} mises à jour, '
            f'{expired_count} expirées, {alert_count} alertes e-mail envoyées.'
        )


def main():
    parser = argparse.ArgumentParser(
        description='Synchronise les offres MediaCongo dans la base CVBoost.'
    )
    parser.add_argument('--limit', type=int, default=50, help='Nombre maximal d’offres à collecter.')
    parser.add_argument(
        '--input-csv',
        help='Importe un CSV existant au lieu de contacter MediaCongo.',
    )
    parser.add_argument(
        '--interval-hours',
        type=_interval,
        help='Répète la collecte dans un processus dédié (intervalle de 2 à 4 heures).',
    )
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 500:
        parser.error('--limit doit être compris entre 1 et 500.')
    if args.input_csv and args.interval_hours:
        parser.error('--input-csv ne peut pas être utilisé avec --interval-hours.')

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    while True:
        try:
            _run_once(app, args.limit, args.input_csv)
        except JobSyncError as error:
            logger.error('%s', error)
            if not args.interval_hours:
                return 1
        if not args.interval_hours:
            return 0
        logger.info('Prochaine synchronisation dans %s heures.', args.interval_hours)
        try:
            time.sleep(args.interval_hours * 60 * 60)
        except KeyboardInterrupt:
            logger.info('Synchronisation périodique arrêtée.')
            return 0


if __name__ == '__main__':
    raise SystemExit(main())
