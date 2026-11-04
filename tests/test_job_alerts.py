import json
import smtplib
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from app import create_app, db
from app.job_alerts import (
    JobAlertConfigurationError,
    send_matching_job_alerts,
)
from app.models import (
    JobAlertDelivery,
    JobAlertPreference,
    JobOffer,
    JobSource,
    User,
    utc_now,
)


class JobAlertTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'job-alert-test-secret',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'UPLOAD_FOLDER': str(self.root / 'uploads'),
            'JOB_ALERTS_ENABLED': True,
            'JOB_ALERT_SMTP_HOST': 'smtp.example.com',
            'JOB_ALERT_SMTP_PORT': 587,
            'JOB_ALERT_SMTP_USERNAME': 'alerts@example.com',
            'JOB_ALERT_SMTP_PASSWORD': 'test-password',
            'JOB_ALERT_SMTP_USE_TLS': False,
            'JOB_ALERT_SMTP_USE_SSL': False,
            'JOB_ALERT_FROM_EMAIL': 'alerts@example.com',
        })
        with self.app.app_context():
            db.create_all()
            user = User(
                nom='Nziengi',
                prenom='Gloria',
                email='gloria@example.com',
                password_hash='unused',
            )
            source = JobSource(
                slug='mediacongo',
                name='MediaCongo',
                base_url='https://mediacongo.net/emplois.html',
            )
            db.session.add_all([user, source])
            db.session.flush()
            self.user_id = user.id
            self.source_id = source.id
            preference = JobAlertPreference(
                user_id=user.id,
                keywords='backend python',
                skills_json=json.dumps(['python']),
                location='Kinshasa',
                contract_type='CDI',
                experience_level='Junior',
                is_remote=True,
                enabled=True,
                updated_at=utc_now() - timedelta(minutes=5),
            )
            db.session.add(preference)
            self.matched_offer = JobOffer(
                source_id=source.id,
                external_id='alert-match',
                source_url='https://mediacongo.net/emploi-societe-301_match.html',
                content_hash='alert-match',
                title='Backend Python developer',
                company='Entreprise RDC',
                description='Développer une API.',
                skills_json=json.dumps(['python', 'docker']),
                location='Kinshasa',
                contract_type='CDI',
                experience_level='Junior',
                is_remote=True,
            )
            self.unmatched_offer = JobOffer(
                source_id=source.id,
                external_id='alert-no-match',
                source_url='https://mediacongo.net/emploi-societe-302_no-match.html',
                content_hash='alert-no-match',
                title='Comptable',
                company='Entreprise RDC',
                description='Suivi financier.',
                skills_json=json.dumps(['excel']),
                location='Lubumbashi',
                contract_type='CDI',
                experience_level='Junior',
                is_remote=False,
                first_seen_at=utc_now() - timedelta(minutes=1),
            )
            db.session.add_all([self.matched_offer, self.unmatched_offer])
            db.session.commit()
            self.matched_offer_id = self.matched_offer.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temporary_directory.cleanup()

    def test_sends_a_matching_email_once_per_user_and_offer(self):
        with self.app.app_context(), patch('app.job_alerts.smtplib.SMTP') as smtp:
            smtp_client = smtp.return_value.__enter__.return_value

            self.assertEqual(send_matching_job_alerts(), 1)
            self.assertEqual(send_matching_job_alerts(), 0)

            smtp.assert_called_once_with('smtp.example.com', 587, timeout=20)
            smtp_client.login.assert_called_once_with(
                'alerts@example.com',
                'test-password',
            )
            smtp_client.send_message.assert_called_once()
            message = smtp_client.send_message.call_args.args[0]
            self.assertEqual(message['To'], 'gloria@example.com')
            self.assertIn('Backend Python developer', message.get_content())
            self.assertEqual(
                JobAlertDelivery.query.filter_by(status='sent').count(),
                1,
            )

    def test_failed_email_is_recorded_and_can_be_retried(self):
        with self.app.app_context(), patch('app.job_alerts.smtplib.SMTP') as smtp:
            smtp_client = smtp.return_value.__enter__.return_value
            smtp_client.send_message.side_effect = smtplib.SMTPException('temporary failure')

            self.assertEqual(send_matching_job_alerts(), 0)
            delivery = JobAlertDelivery.query.filter_by(
                user_id=self.user_id,
                job_offer_id=self.matched_offer_id,
            ).one()
            self.assertEqual(delivery.status, 'failed')
            self.assertEqual(delivery.attempts, 1)

            smtp_client.send_message.side_effect = None
            self.assertEqual(send_matching_job_alerts(), 1)
            self.assertEqual(delivery.status, 'sent')
            self.assertEqual(delivery.attempts, 2)

    def test_unmatched_offers_do_not_starve_later_matching_offers(self):
        with self.app.app_context(), patch('app.job_alerts.smtplib.SMTP') as smtp:
            smtp_client = smtp.return_value.__enter__.return_value

            self.assertEqual(send_matching_job_alerts(max_deliveries=1), 1)

            smtp_client.send_message.assert_called_once()
            message = smtp_client.send_message.call_args.args[0]
            self.assertIn('Backend Python developer', message['Subject'])

    def test_email_alerts_require_explicit_server_configuration(self):
        self.app.config['JOB_ALERTS_ENABLED'] = False
        with self.app.app_context():
            with self.assertRaises(JobAlertConfigurationError):
                send_matching_job_alerts()


if __name__ == '__main__':
    unittest.main()
