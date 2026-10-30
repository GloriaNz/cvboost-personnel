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

---

## 6️⃣ Déconnexion

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
permettent les essais, mais ne remplacent pas un stockage durable de production
sur AWS : les CV devront être migrés vers S3 et la base vers RDS avant un
déploiement avec des données réelles.

### État du socle web et tests

Le MVP Flask comprend l'authentification, le téléversement, l'historique et
l'interface. Le socle a été renforcé : secrets configurables, cookies de session
durcis, fichiers PDF/DOCX limités à 5 Mo, redirections de connexion validées et
déconnexion par POST avec protection CSRF. Le score aléatoire de démonstration a
été retiré afin de ne pas présenter un résultat fictif comme une analyse réelle.

L'Assistant DRH du Sprint 3 est implémenté : extraction locale des textes PDF/DOCX,
analyse d'une offre par Groq, score indicatif et simulation d'entretien avec
dictée des réponses et lecture audio des questions. L'infrastructure AWS reste
à construire. Le développement se fera et sera testé localement avant tout
déploiement ou création de ressources AWS.

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

### Sprint 3 — Assistant DRH et moteur NLP

L'analyse d'un CV est déclenchée depuis sa page de résultat : collez l'offre,
lancez l'analyse. Les fichiers PDF/DOCX sont extraits localement avant
l'appel au modèle `llama-3.3-70b-versatile`. Le résultat comprend un résumé,
un score indicatif sur 100, des points forts, des compétences à vérifier et la
première question d'une simulation d'entretien. Les réponses peuvent être suivies par
jusqu'à 10 questions. Le score est une aide explicable, jamais une décision
d'embauche/rejet ; l'analyse ne doit utiliser que les compétences et expériences.
Chaque point fort doit maintenant être accompagné d'une citation exacte du CV,
vérifiée localement avant affichage ; une réponse du modèle dont la preuve ne
figure pas dans le document est rejetée.
La simulation d'entretien propose aussi la lecture audio des questions via la
synthèse vocale du navigateur et la dictée des réponses via Groq. La transcription
est présentée dans le champ de réponse pour être relue et corrigée avant envoi.
Les enregistrements ne sont pas stockés par CVBoost ; l'audio est transmis à
Groq pour transcription. La lecture audio des questions ne transmet pas leur
texte à un fournisseur externe. La dictée nécessite l'accès au microphone et
une clé API configurée.
Le navigateur doit autoriser l'accès au microphone ; hors de `localhost`,
l'enregistrement nécessite une connexion HTTPS.

Configurez une clé Groq dans `.env` pour activer l'analyse et la transcription :

```dotenv
GROQ_API_KEY=your-key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
```

Ne partagez pas cette clé et n'envoyez pas de CV réels à un fournisseur externe
sans consentement approprié. Les appels Groq peuvent être soumis à des limites
ou à des frais selon votre compte. Le texte du CV et de l'offre est transmis au
fournisseur.

Pour tester l'application sans clé, les pages web et les fonctions locales
restent accessibles ; l'analyse affiche alors un message indiquant que
`GROQ_API_KEY` manque. Ajoutez la valeur uniquement dans votre `.env` local
quand vous êtes prêt à tester les appels réels.

La préparation de données d'entraînement est indépendante de l'Assistant DRH.
Elle accepte un fichier JSONL avec un exemple par ligne, sous la forme
`{"prompt":"...","completion":"..."}`. Les exemples exacts sont dédupliqués par
SHA-256 et les exemples partageant un prompt ou une réponse sont regroupés dans
la même partition afin d'éviter les fuites train/validation/test.

```powershell
python -m ai_engine.prepare_dataset --input chemin\vers\exemples.jsonl
```

Le fine-tuning LoRA est facultatif et nécessite un dataset d'entraînement licencié,
un téléchargement de modèle et suffisamment de mémoire (GPU recommandé). Les
dépendances lourdes ne sont pas requises pour lancer le site. Avant de les charger,
les scripts vérifient que chaque partition JSONL est présente, non vide et contient
des champs `prompt` et `completion` valides :

```powershell
python -m pip install -r requirements-training.txt
python -m ai_engine.train_lora
python -m ai_engine.evaluate_model --adapter ai_engine\models\cvboost-lora
```

Le script d'entraînement utilise un modèle causal compatible LoRA avec `q_proj`
et `v_proj`. Si ces noms diffèrent pour le modèle choisi, fournissez
`--target-modules`. L'évaluation SacreBLEU porte sur le jeu de test isolé ;
elle complète, mais ne remplace pas, une revue qualitative des sorties.
