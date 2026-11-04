import json
import logging
import smtplib
from datetime import date
from email.message import EmailMessage
from email.utils import parseaddr

from flask import current_app
from sqlalchemy import or_

from app import db
from app.models import (
    JobAlertDelivery,
    JobAlertPreference,
    JobOffer,
    User,
    utc_now,
)


logger = logging.getLogger(__name__)


class JobAlertConfigurationError(RuntimeError):
    pass


def job_alert_mail_configured():
    config = current_app.config
    sender = config.get('JOB_ALERT_FROM_EMAIL') or config.get('JOB_ALERT_SMTP_USERNAME')
    username = config.get('JOB_ALERT_SMTP_USERNAME')
    password = config.get('JOB_ALERT_SMTP_PASSWORD')
    return bool(
        config.get('JOB_ALERTS_ENABLED')
        and config.get('JOB_ALERT_SMTP_HOST')
        and 1 <= config.get('JOB_ALERT_SMTP_PORT', 0) <= 65535
        and sender
        and '@' in parseaddr(sender)[1]
        and bool(username) == bool(password)
        and not (
            config.get('JOB_ALERT_SMTP_USE_TLS')
            and config.get('JOB_ALERT_SMTP_USE_SSL')
        )
    )


def _validate_mail_config():
    config = current_app.config
    if not job_alert_mail_configured():
        raise JobAlertConfigurationError(
            'Les alertes e-mail sont désactivées ou incomplètement configurées.'
        )
    if config.get('JOB_ALERT_SMTP_USE_TLS') and config.get('JOB_ALERT_SMTP_USE_SSL'):
        raise JobAlertConfigurationError(
            'Choisissez STARTTLS ou SSL pour le serveur SMTP, pas les deux.'
        )
    username = config.get('JOB_ALERT_SMTP_USERNAME')
    password = config.get('JOB_ALERT_SMTP_PASSWORD')
    if bool(username) != bool(password):
        raise JobAlertConfigurationError(
            'Les identifiants SMTP doivent être configurés ensemble.'
        )


def _matches_preference(preference, offer):
    searchable_text = ' '.join((
        offer.title,
        offer.company,
        offer.description,
    )).casefold()
    terms = [term.casefold() for term in preference.keywords.split() if term]
    if terms and not any(term in searchable_text for term in terms):
        return False

    required_skills = set(json.loads(preference.skills_json))
    if required_skills and not required_skills.issubset(set(json.loads(offer.skills_json))):
        return False
    if preference.location and preference.location.casefold() not in offer.location.casefold():
        return False
    if (
        preference.contract_type
        and preference.contract_type.casefold() != offer.contract_type.casefold()
    ):
        return False
    if (
        preference.experience_level
        and preference.experience_level.casefold() != offer.experience_level.casefold()
    ):
        return False
    if preference.is_remote and not offer.is_remote:
        return False
    return True


def _send_email(recipient, offer):
    config = current_app.config
    sender = config.get('JOB_ALERT_FROM_EMAIL') or config['JOB_ALERT_SMTP_USERNAME']
    message = EmailMessage()
    message['Subject'] = f"Nouvelle offre correspondant à vos critères : {offer.title}"
    message['From'] = sender
    message['To'] = recipient
    message.set_content(
        f"Bonjour,\n\n"
        f"Une nouvelle offre correspond à vos préférences CVBoost :\n"
        f"{offer.title}\n"
        f"{offer.company or 'Entreprise non précisée'} · "
        f"{offer.location or 'Lieu non précisé'}\n\n"
        f"Consultez l’annonce originale : {offer.source_url}\n\n"
        "Vous pouvez modifier ou désactiver vos préférences d’alerte depuis "
        "la page Offres d’emploi de CVBoost.\n"
    )
    smtp_class = smtplib.SMTP_SSL if config.get('JOB_ALERT_SMTP_USE_SSL') else smtplib.SMTP
    with smtp_class(
        config['JOB_ALERT_SMTP_HOST'],
        config['JOB_ALERT_SMTP_PORT'],
        timeout=20,
    ) as server:
        if config.get('JOB_ALERT_SMTP_USE_TLS'):
            server.starttls()
        username = config.get('JOB_ALERT_SMTP_USERNAME')
        if username:
            server.login(username, config['JOB_ALERT_SMTP_PASSWORD'])
        server.send_message(message)


def send_matching_job_alerts(max_deliveries=100):
    _validate_mail_config()
    if max_deliveries < 1:
        raise ValueError('max_deliveries doit être supérieur à zéro.')

    sent_count = 0
    remaining = max_deliveries
    for preference in JobAlertPreference.query.filter_by(enabled=True).order_by(
        JobAlertPreference.id.asc()
    ).all():
        if remaining <= 0:
            break
        user = db.session.get(User, preference.user_id)
        if user is None:
            continue
        offer_query = JobOffer.query.filter(
            JobOffer.status == 'active',
            or_(JobOffer.deadline.is_(None), JobOffer.deadline >= date.today()),
            JobOffer.first_seen_at >= preference.updated_at,
        ).order_by(JobOffer.first_seen_at.asc())
        offset = 0

        while remaining > 0:
            offers = offer_query.limit(100).offset(offset).all()
            if not offers:
                break
            offset += len(offers)
            for offer in offers:
                if remaining <= 0:
                    break
                if not _matches_preference(preference, offer):
                    continue
                delivery = JobAlertDelivery.query.filter_by(
                    user_id=user.id,
                    job_offer_id=offer.id,
                ).first()
                if delivery is not None and delivery.status == 'sent':
                    continue
                if delivery is None:
                    delivery = JobAlertDelivery(
                        user_id=user.id,
                        job_offer_id=offer.id,
                    )
                    db.session.add(delivery)
                    db.session.flush()
                delivery.status = 'sending'
                delivery.attempts += 1
                delivery.last_attempt_at = utc_now()
                delivery.error_message = ''
                db.session.commit()
                remaining -= 1

                try:
                    _send_email(user.email, offer)
                except (OSError, smtplib.SMTPException, ValueError) as error:
                    delivery.status = 'failed'
                    delivery.error_message = type(error).__name__[:160]
                    db.session.commit()
                    logger.warning(
                        'Job alert delivery failed (user_id=%s, offer_id=%s, error=%s).',
                        user.id,
                        offer.id,
                        type(error).__name__,
                    )
                    continue

                delivery.status = 'sent'
                delivery.sent_at = utc_now()
                db.session.commit()
                sent_count += 1
                if remaining <= 0:
                    break

    return sent_count
