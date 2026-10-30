from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
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


class MatchForm(FlaskForm):
    job_description = TextAreaField(
        'Description de l’offre d’emploi',
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
