from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from app.models import User


class RegisterForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    prenom = StringField('Prénom', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirmer le mot de passe',
        validators=[DataRequired(), EqualTo('password', message='Les mots de passe ne correspondent pas.')]
    )
    submit = SubmitField("S'inscrire")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cet email est déjà utilisé. Veuillez en choisir un autre.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')


class UploadForm(FlaskForm):
    cv = FileField(
        'Votre CV (PDF ou DOCX)',
        validators=[
            FileRequired(message='Veuillez sélectionner un fichier.'),
            FileAllowed(['pdf', 'docx'], 'Seuls les fichiers PDF et DOCX sont acceptés.')
        ]
    )
    submit = SubmitField('Envoyer mon CV')


class LogoutForm(FlaskForm):
    submit = SubmitField('Déconnexion')


class DeleteCVForm(FlaskForm):
    pass


class MatchForm(FlaskForm):
    job_description = TextAreaField(
        'Description de l’offre d’emploi à cibler',
        validators=[DataRequired(), Length(min=30, max=12000)],
    )
    submit = SubmitField('Analyser mon profil')


class InterviewAnswerForm(FlaskForm):
    answer = TextAreaField(
        'Votre réponse',
        validators=[DataRequired(), Length(min=2, max=4000)],
    )
    submit = SubmitField('Répondre')


class InterviewAudioForm(FlaskForm):
    audio = FileField(
        'Enregistrement audio',
        validators=[
            FileRequired(message='Veuillez enregistrer une réponse audio.'),
            FileAllowed(
                ['webm', 'mp4', 'm4a', 'wav', 'mp3', 'mpeg', 'mpga'],
                'Format audio non pris en charge.',
            ),
        ],
    )


class JobAlertPreferencesForm(FlaskForm):
    keywords = StringField('Mots-clés', validators=[Optional(), Length(max=500)])
    skills = StringField('Compétences', validators=[Optional(), Length(max=500)])
    location = StringField('Localisation', validators=[Optional(), Length(max=200)])
    contract_type = SelectField(
        'Type de contrat',
        choices=[
            ('', 'Tous les contrats'),
            ('Stage', 'Stage'),
            ('Alternance', 'Alternance'),
            ('CDI', 'CDI'),
            ('CDD', 'CDD'),
            ('Freelance', 'Freelance'),
        ],
    )
    experience_level = SelectField(
        'Expérience',
        choices=[
            ('', 'Tous les niveaux'),
            ('Junior', 'Junior'),
            ('Confirmé', 'Confirmé'),
            ('Senior', 'Senior'),
        ],
    )
    is_remote = BooleanField('Télétravail')
    enabled = BooleanField('Activer mes préférences d’alerte')
    submit = SubmitField('Enregistrer mes préférences')
