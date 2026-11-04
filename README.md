[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/89Qc2aKD)
# CVBoost – MVP Web Platform

## 📌 Description du projet

**CVBoost** est une plateforme web développée avec **Flask** permettant aux utilisateurs de télécharger et gérer leurs CV, puis d'obtenir une analyse indicative de leur adéquation avec une offre d'emploi grâce à l'intelligence artificielle.

Cette première version correspond à un **MVP (Minimum Viable Product)** dont l'objectif est de poser les bases techniques de la plateforme :

* Gestion des utilisateurs (inscription / connexion)
* Upload sécurisé de CV
* Association des CV aux utilisateurs
* Historique des CV envoyés
* Analyse IA d'un CV par rapport à une offre et simulation d'entretien

Le rapprochement automatique des CV avec les offres collectées reste une évolution future ; l'offre à analyser est saisie par l'utilisateur.

---

# 🧰 Technologies utilisées

| Composant            | Technologie           |
| -------------------- | --------------------- |
| Backend              | Python / Flask        |
| Authentification     | Flask-Login           |
| Hashage mot de passe | Werkzeug              |
| Base de données      | SQLite                |
| ORM                  | SQLAlchemy            |
| Frontend             | HTML5 / CSS3 / Jinja2 |
| UI Framework         | Bootstrap ou Tailwind |
| Sécurité fichiers    | UUID                  |

---

# 📁 Structure du projet

```
cvboost/
│
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── forms.py
│   │
│   ├── templates/
│   │   ├── index.html
│   │   ├── register.html
│   │   ├── login.html
│   │   ├── upload.html
│   │   ├── history.html
│   │   └── result.html
│   │
│   ├── static/
│   │   ├── css/
│   │   └── js/
│
├── uploads/
│
├── instance/
│   └── cvboost.db
│
├── requirements.txt
├── run.py
└── README.md
```

---

# 👤 Fonctionnalités implémentées

## 1️⃣ Page d'accueil

Route : `/`

* Présentation du projet CVBoost
* Barre de navigation dynamique

  * Utilisateur anonyme : **Connexion / Inscription**
  * Utilisateur connecté : **Upload / Historique / Déconnexion**

---

## 2️⃣ Inscription utilisateur

Route : `/register`

Formulaire :

* Nom
* Prénom
* Email
* Mot de passe
* Confirmation du mot de passe

Fonctionnalités :

* Vérification unicité email
* Hashage sécurisé du mot de passe (Werkzeug)

---

## 3️⃣ Connexion utilisateur

Route : `/login`

Formulaire :

* Email
* Mot de passe

Fonctionnalités :

* Authentification des utilisateurs (Flask-Login)
* Messages de retour (flash) en cas d'erreur (identifiants incorrects)
* Redirection vers la page d'accueil ou l'upload après connexion réussie

---

## 4️⃣ Upload de CV

Route : `/upload`

Fonctionnalités :

* Interface de téléchargement de fichiers (PDF, DOCX)
* Génération d'un nom de fichier unique (UUID) pour la sécurité
* Sauvegarde du fichier dans le répertoire `uploads/`
* Enregistrement dans la base de données, associé à l'utilisateur connecté

---

## 5️⃣ Historique des CV

Route : `/history`

Fonctionnalités :

* Liste des CV téléchargés par l'utilisateur connecté
* Affichage de la date d'upload et du nom du fichier
* Statut du CV et de son analyse (ex : "En attente", "Analyse terminée")
* Suppression d'un CV depuis l'historique, avec son fichier, son analyse et sa simulation d'entretien

---

## 6️⃣ Simulation d’entretien

Route : `/interview` (accessible depuis le menu après connexion)

Choisissez un CV déjà téléversé. Pour démarrer une simulation, ouvrez son
analyse, collez une offre d’emploi d’au moins 30 caractères et lancez
« Analyser mon profil ». La première question apparaît ensuite dans la section
« Simulation d’entretien » ; répondez pour obtenir les questions suivantes.
Dans la salle, cliquez sur « Démarrer l’entretien vocal » : Sarah vous salue,
lit la première question, écoute votre réponse en français puis enchaîne avec la
question suivante après une courte pause. Le mode vocal nécessite un navigateur
compatible (Chrome ou Edge), l’autorisation du microphone et une connexion
sécurisée (HTTPS ou localhost). La réponse écrite reste disponible. Les erreurs
Groq indiquent si la clé, le quota ou le modèle doit être vérifié.

---

## 7️⃣ Déconnexion

Route : `POST /logout` (formulaire protégé par CSRF)

Fonctionnalités :

* Fermeture de la session utilisateur
* Redirection vers la page de connexion ou la page d'accueil

---

# 🚀 Installation et exécution en local

Depuis le dossier du projet, dans PowerShell :

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$secret = python -c "import secrets; print(secrets.token_hex(32))"
(Get-Content .env) -replace '^SECRET_KEY=.*$', "SECRET_KEY=$secret" | Set-Content .env
python run.py
```

L'application sera accessible sur [http://127.0.0.1:5000/](http://127.0.0.1:5000/).
Le fichier `.env` est ignoré par Git. Ne le publiez pas. En production sous
HTTPS, réglez `COOKIE_SECURE=true`.

### Exécuter avec Docker

Docker Compose démarre le site Flask avec Gunicorn sur
[http://127.0.0.1:8000/](http://127.0.0.1:8000/). Il conserve la base SQLite,
les CV et les journaux dans des volumes nommés, même après le redémarrage du
conteneur.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$secret = python -c "import secrets; print(secrets.token_hex(32))"
(Get-Content .env) -replace '^SECRET_KEY=.*$', "SECRET_KEY=$secret" | Set-Content .env
docker compose up --build
```

Renseignez également `GROQ_API_KEY` dans `.env` pour les fonctions IA.
N'exposez pas le port de développement sur Internet. Les volumes locaux
permettent les essais, mais ne remplacent pas le stockage persistant de Render.
Le Blueprint Render gratuit est destiné aux démonstrations : sa base SQLite et
les CV peuvent être perdus au redémarrage (voir le
[guide de déploiement Render](./RENDER_DEPLOYMENT_GUIDE.md)).

### État du socle web et tests

Le MVP Flask comprend l'authentification, le téléversement, l'historique et
l'interface. Le socle a été renforcé : secrets configurables, cookies de session
durcis, fichiers PDF/DOCX limités à 5 Mo, redirections de connexion validées et
déconnexion par POST avec protection CSRF. Le score aléatoire de démonstration a
été retiré afin de ne pas présenter un résultat fictif comme une analyse réelle.

L'Assistant DRH du Sprint 3 est implémenté : extraction locale des textes PDF/DOCX,
analyse d'une offre par Groq, score indicatif et simulation d'entretien avec
dictée des réponses et lecture audio des questions. Le déploiement cloud est
prévu sur Render ; le développement et les tests restent exécutés localement
et dans GitHub Actions.

Depuis la page de résultat d'un CV, vous pouvez également générer un pitch de
présentation basé sur son contenu et l'écouter avec la synthèse vocale française
du navigateur. Une clé Gemini, Groq ou Mistral doit être configurée pour générer
le texte ; la disponibilité de la voix dépend du navigateur et de l'appareil.

### Assistant CVBoost AI

La page `/assistant` fournit des conversations persistantes privées par compte,
alimentées exclusivement par Groq. L'utilisateur choisit s'il souhaite partager
son nom/prénom de profil et un CV qu'il possède ; ce contexte est désactivé par
défaut et l'adresse e-mail n'est jamais transmise. Les messages sont limités à
10 par minute et le serveur ne journalise pas leur contenu. Les
conversations, leurs messages et le compteur de requêtes sont créés de façon
additive au démarrage de l'application avec les tables SQLAlchemy.

Les routes JSON sont :

* `GET/POST /api/assistant/conversations` : lister/créer une conversation.
* `GET/DELETE /api/assistant/conversations/<id>` : lire/supprimer ses propres
  conversations.
* `POST /api/assistant/conversations/<id>/messages` : envoyer un message à
  Groq et enregistrer les deux réponses.
* `POST /api/assistant/conversations/<id>/audio` : transcrire temporairement un
  audio français via Groq Whisper ; le fichier n'est pas conservé.

Toutes les modifications d'état demandent le jeton CSRF de la page. Pour le
Lingala, l'application attend l'adaptateur NLLB-LoRA déjà entraîné et le modèle
de base disponibles localement. Aucun poids de modèle n'est inclus au dépôt et
aucun téléchargement automatique ni réentraînement n'est effectué. Installer
les dépendances optionnelles après avoir choisi la version PyTorch adaptée à la
machine :

```powershell
pip install -r requirements-translation.txt
```

Le notebook `ai_engine/sprint3_colab.ipynb` confirme que l'adaptateur entraîné
est sauvegardé dans Google Drive sous
`CVBoost/checkpoints/nllb-lora-lin-fra`. Ses sorties Colab listent
`adapter_config.json`, `adapter_model.safetensors` et les fichiers du tokenizer.
Le notebook ne contient pas les poids eux-mêmes dans le dépôt : `ai_engine/models/`
est volontairement ignoré par Git.

Après avoir téléchargé le dossier de l'adaptateur depuis Google Drive, le placer
dans `ai_engine/models/nllb-lora-lin-fra/` à la racine du projet, en conservant
au minimum `adapter_config.json` et `adapter_model.safetensors`. On peut vérifier
le contenu depuis Colab et télécharger une archive avec :

```python
import shutil
from google.colab import files

adapter_dir = "/content/drive/MyDrive/CVBoost/checkpoints/nllb-lora-lin-fra"
archive = shutil.make_archive("/content/nllb-lora-lin-fra", "zip", adapter_dir)
files.download(archive)
```

Configurer `NLLB_BASE_MODEL` et `NLLB_ADAPTER_PATH` dans `.env`. Le chemin
par défaut `ai_engine/models/nllb-lora-lin-fra` correspond au dossier local
après extraction. Le modèle de base NLLB doit également être présent dans le
cache local de Hugging Face : l'application charge les modèles avec
`local_files_only=True` et ne télécharge aucun poids automatiquement. En
l'absence du modèle de base ou de l'adaptateur, la conversation française reste
opérationnelle et l'interface indique que la traduction Lingala n'est pas
disponible. La dictée et la lecture vocale Lingala ne sont pas annoncées comme prises en charge :
la transcription utilise le service français et la lecture dépend des voix
Lingala réellement installées dans le navigateur.

Lancer les tests ciblés avec :

```powershell
python -m unittest discover -s tests
```

### Collecte d'offres d'emploi en RDC

Le collecteur implémenté pour l'instant utilise la page publique des offres
MediaCongo (`https://mediacongo.net/emplois.html`). Il lit les règles
`robots.txt`, impose au moins 10 secondes entre les requêtes et exporte les
résultats en CSV. Par défaut, il lit les annonces de la page de liste uniquement ;
les pages détail peuvent contenir des images au lieu de texte pour la description.

```powershell
python -m pip install -r requirements.txt
python -m data_pipeline.scraper_jobs --limit 20
python -m data_pipeline.scraper_jobs --limit 10 --details 2
```

L'option `--details` lit les pages individuelles séquentiellement ; avec le délai
imposé, 2 pages détail nécessitent au minimum 30 secondes en comptant la page de
liste et `robots.txt`. Le collecteur ne télécharge pas les images ni les documents
liés. Il faut vérifier les conditions d'utilisation du site avant une collecte
régulière ou une réutilisation commerciale.

`emploie.cd` ne résolvait pas depuis l'environnement au moment de la vérification.
Pour `optioncarriere.cd`, son `robots.txt` interdit les chemins de recherche et de
fiches d'offres ; ces deux sources ne sont donc pas collectées.

### Audit des uploads, KPI et nettoyage Pandas

L'application écrit les événements d'upload en JSONL dans
`instance/upload_audit.jsonl` (chemin configurable avec `UPLOAD_AUDIT_LOG`). Les
noms personnels des CV ne sont pas conservés dans ces journaux : seules
l'extension, la taille, l'identifiant utilisateur, le résultat et le motif sont
enregistrés. Les journaux sont ignorés par Git.

Après avoir utilisé l'application et collecté les événements :

```powershell
python -m data_pipeline.logs_parser --input instance/upload_audit.jsonl
python -m data_pipeline.analytics --logs instance/upload_audit.jsonl
python -m data_pipeline.scraper_jobs --limit 20 --output data_pipeline/jobs_mediacongo.csv
python -m data_pipeline.pandas_cleaning --input data_pipeline/jobs_mediacongo.csv --output data_pipeline/jobs_clean.csv
```

`logs_parser` valide les entrées JSONL, extrait les métadonnées et signale les
extensions/refus suspects ou au moins trois échecs pour un même utilisateur.
Ces indicateurs sont des signaux d'audit, pas une conclusion automatique de
fraude. Les lignes illisibles sont rapportées et font échouer la commande.

`analytics` alimente `instance/analytics.db` de manière idempotente et calcule
les volumes quotidiens, par utilisateur et par extension, avec `GROUP BY` et
`HAVING`. Pour n'afficher que les groupes contenant au moins deux uploads :

```powershell
python -m data_pipeline.analytics --logs instance/upload_audit.jsonl --minimum-uploads 2
```

`pandas_cleaning` supprime les annonces sans titre et les doublons, uniformise
les champs texte, normalise les fourchettes de salaire sans mélanger USD et CDF,
convertit les dates et produit la liste ainsi que les colonnes indicatrices des
compétences reconnues.

Le fichier nettoyé `data_pipeline/jobs_clean.csv` est lu localement sur la page
de résultat du CV. CVBoost classe les offres par mots-clés de compétences
communs, sans fabriquer un score de compatibilité ; choisissez une annonce pour
préremplir et lancer l'analyse IA. Le fichier peut être déplacé avec
`JOB_OFFERS_FILE` dans `.env`. Les descriptions absentes ou trop longues sont
signalées et ne sont pas envoyées à l'analyse.

#### Recherche persistante et synchronisation

La page `/jobs` recherche dans les annonces stockées en base, avec filtres par
mots-clés, compétences reconnues, lieu, contrat, expérience, télétravail, date
de publication et date limite. Les offres dont la date limite est passée sont
exclues.
La comparaison avec un CV affiche seulement la part des compétences détectées en
commun ; ce n'est pas une prédiction d'embauche. Une offre peut ensuite être
envoyée au formulaire d'analyse CV existant. Les nouvelles tables `job_sources`,
`job_offers`, `job_sync_runs`, `job_alert_preferences` et `job_alert_deliveries`
sont ajoutées sans supprimer les tables existantes.

Seul le connecteur MediaCongo déjà présent est activé. Il conserve son contrôle
`robots.txt`, son délai minimum et les liens limités à `mediacongo.net`. Une
collecte périodique doit être exécutée dans un processus distinct du serveur web,
afin d'éviter une synchronisation par worker Gunicorn :

```powershell
python -m data_pipeline.job_scheduler
python -m data_pipeline.job_scheduler --input-csv data_pipeline/jobs_clean.csv
python -m data_pipeline.job_scheduler --interval-hours 4
```

Le premier appel collecte MediaCongo ; le second importe les données locales ;
le dernier répète la collecte à l'intervalle choisi (2 à 4 heures). Le processus
peut être arrêté avec Ctrl+C. `JOB_ADMIN_EMAILS` accepte une liste d'adresses
séparées par des virgules pour accéder à `/admin/job-intelligence`. Les alertes
ne sont envoyées qu'aux utilisateurs qui les activent et pour les offres
ajoutées après la dernière mise à jour de leurs préférences. La livraison est
dédupliquée par compte et par offre ; les erreurs SMTP sont enregistrées et
réessayées lors de la prochaine exécution.

Pour activer l'envoi, configurer dans `.env` `JOB_ALERTS_ENABLED=true`,
`JOB_ALERT_SMTP_HOST`, `JOB_ALERT_SMTP_PORT`, `JOB_ALERT_SMTP_USERNAME`,
`JOB_ALERT_SMTP_PASSWORD`, `JOB_ALERT_FROM_EMAIL` et les paramètres TLS/SSL.
Laisser `JOB_ALERTS_ENABLED=false` tant que le fournisseur e-mail n'est pas
configuré. Ne jamais commiter les identifiants SMTP.

Par prudence, la collecte réseau est désactivée par défaut. Après avoir vérifié
et accepté les conditions d'utilisation du site, régler
`MEDIACONGO_COLLECTION_APPROVED=true` dans `.env` avant de lancer une collecte
live. Sans cette confirmation, l'import du CSV déjà collecté reste disponible.

Emploi.cd, CongoJob et ONEM n'ont pas de connecteur actif. Vérification du
04/11/2026 : `emploi.cd` annonce `search=yes` et `use=reference` dans ses
signaux robots, mais l'accès aux pages renvoie HTTP 403 depuis l'environnement ;
CongoJob publie un sitemap d'offres et son `robots.txt` autorise les pages
publiques, mais une URL d'offre vérifiée redirige vers l'accueil et ses
conditions de réutilisation n'ont pas pu être confirmées ; ONEM affiche un
portail d'offres sur son site, mais `robots.txt` et les sitemaps usuels renvoient
404 et l'accès aux services candidats redirige vers une authentification. Ces
sources ne sont donc pas aspirées tant qu'un flux public stable et les règles
de réutilisation ne sont pas confirmés. Aucune page de source n'est collectée sans vérification de ses
conditions d'utilisation. Les champs d'expérience, de type de contrat et de
télétravail sont extraits par mots-clés quand ils apparaissent dans le titre ou
la description ; ils restent inconnus autrement. Les dates limites ne sont pas
encore extraites par le collecteur MediaCongo.

### Sprint 3 — Assistant DRH Multi-Fournisseurs (Gemini → Groq → Mistral)

L'analyse d'un CV est déclenchée depuis sa page de diagnostic. Les fichiers PDF/DOCX sont extraits localement avant l'appel aux LLM.

#### 🛡️ Haute Disponibilité Multi-Fournisseurs (Fallback Automatique)
Pour garantir une disponibilité ininterrompue en production et pallier l'épuisement des quotas gratuits de chaque fournisseur d'IA, l'application orchestre automatiquement les requêtes selon la chaîne prioritaire suivante :

1. **Google Gemini (Priorité 1)** : modèle `gemini-3.8-flash` rapide et performant.
2. **Groq (Priorité 2)** : modèle `qwen/qwen3.8-27b`, activé automatiquement si Gemini est indisponible ou atteint son quota.
3. **Mistral AI (Priorité 3)** : modèle `mistral-small-latest`, activé automatiquement si les quotas Gemini et Groq sont dépassés.

Si un fournisseur rencontre une limite de jetons ou de requêtes, l'orchestrateur bascule instantanément vers le fournisseur suivant de manière transparente pour l'utilisateur.

```dotenv
# Configuration des 3 Fournisseurs dans .env
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.8-flash

GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo

MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-small-latest
```

#### 🎙️ Séparation Claire : Diagnostic CV vs Salle d'Entretien Dédiée
Pour offrir une expérience utilisateur professionnelle, claire et aérée :
- **Page Diagnostic CV (`/result/<cv_id>`)** : se concentre exclusivement sur le bilan de compétences, le score de compatibilité calculé par l'IA, les points forts prouvés par le CV, les écarts professionnels et les offres d'emploi ciblées.
- **Salle d'Entretien Dédiée (`/interview/<analysis_id>`)** : plateau immersif d'entraînement avec Sarah, la recruteuse IA, ondes sonores interactives, synthèse vocale des questions, et reconnaissance vocale temps réel au micro.

### 📓 Notebook Fine-Tuning Colab (Sprint 3)
Le notebook de fine-tuning exécuté sur Google Colab est archivé dans [`ai_engine/sprint3_colab.ipynb`](file:///c:/Users/utilisitateur/OneDrive/Documents/26-01-kd-dev-ia-midi-c-mon-thu-kin-projet-capstone-final-cvb-glorianz/ai_engine/sprint3_colab.ipynb).
Il détaille :
- La préparation et le filtrage des paires sans fuite de données (train/validation/test).
- Le fine-tuning PEFT/LoRA sur le modèle NLLB ciblant les projections d'attention.
- Les checkpoints de sauvegarde (`/content/nllb-lora-fr-lin-final` ou Google Drive).
- L'évaluation comparative avec SacreBLEU (score BLEU obtenu : **21.71**, chrF : **51.44** démontrant le gain par rapport au modèle d'origine).

---

# 🚀 Sprint 4 : API Multimodale, Synthèse Vocale & Déploiement Render

### 1. Orchestrateur FastAPI (`/speak-smart`)
L'orchestrateur multimodal combine la reformulation intelligente et la synthèse vocale :
- **Étape 1 : Reformulation LLM** avec fallback multi-providers (Gemini → Groq → Mistral) via `api_service/services/llm_reformulator.py`, générant un pitch fluide à la 1ère personne (~30s).
- **Étape 2 : Synthèse vocale TTS** (`api_service/services/tts_engine.py`) produisant un fichier audio `.wav` haute fidélité.
- **Métriques audio MLOps journalisées** : MOS estimé (4.15 / 5.0), WER cible (< 5.2%), CER cible (< 2.1%).

Démarrer l'API localement :
```powershell
uvicorn api_service.main:app --host 0.0.0.0 --port 8001 --reload
```

Test de l'endpoint :
```bash
curl -X POST http://127.0.0.1:8001/speak-smart \
  -H "Content-Type: application/json" \
  -d '{"cv_text": "Gloria NZ - Développeuse IA et Full Stack...", "job_target": "Ingénieure IA"}'
```

### 2. Conteneurisation Multi-Services (Docker & Docker Compose)
L'application web Flask et l'API FastAPI sont orchestrées via `docker-compose.yml` :
```powershell
docker-compose up --build
```
- **Application Web (Flask)** : accessible sur `http://localhost:8000`
- **Orchestrateur Vocal (FastAPI)** : accessible sur `http://localhost:8001`
- **Volumes persistants** : `cvboost_instance`, `cvboost_uploads`, `cvboost_audio`.

### 3. Pipeline CI/CD GitHub Actions & Déploiement Render
Le workflow automatisé se trouve dans `.github/workflows/deploy.yml` :
1. **Tests automatiques** : la suite de tests s'exécute dans GitHub Actions.
2. **Déploiement continu** : Render déploie les deux services définis dans
   `render.yaml` après la réussite des vérifications CI GitHub.

Consultez le [guide de déploiement Render](./RENDER_DEPLOYMENT_GUIDE.md).
