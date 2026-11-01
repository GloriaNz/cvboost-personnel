# Guide de Déploiement Cloud Industriel CVBoost sur AWS

> **Obsolète :** CVBoost est maintenant hébergé sur Render. Ce document est
> conservé comme historique ; suivez le
> [guide de déploiement Render](./RENDER_DEPLOYMENT_GUIDE.md).

Ce guide détaille pas-à-pas la mise en production de **CVBoost** sur **Amazon Web Services (AWS)** en remplacement d'Azure, avec prise en charge de la haute disponibilité multi-modèles (**Gemini → Groq → Mistral**) et de l'architecture hybride Flask + FastAPI.

---

## 📋 Sommaire
1. [Architecture Globale Cloud sur AWS](#1-architecture-globale-cloud-sur-aws)
2. [Gestion des Clés d'API & Haute Disponibilité](#2-gestion-des-clés-dapi--haute-disponibilité)
3. [Option A : Déploiement Managé via AWS App Runner (Recommandé)](#3-option-a--déploiement-managé-via-aws-app-runner-recommandé)
4. [Option B : Déploiement sur Instance AWS EC2 (Docker Compose)](#4-option-b--déploiement-sur-instance-aws-ec2-docker-compose)
5. [Option C : Déploiement Conteneurisé via AWS ECS Fargate & ECR](#5-option-c--déploiement-conteneurisé-via-aws-ecs-fargate--ecr)
6. [Automatisation CI/CD avec GitHub Actions](#6-automatisation-cicd-avec-github-actions)
7. [Surveillance & Métriques MLOps en Production](#7-surveillance--métriques-mlops-en-production)

---

## 1. Architecture Globale Cloud sur AWS

```text
       ┌────────────────────────────────────────────────────────┐
       │                   Utilisateur Web / Client             │
       └───────────────────────────┬────────────────────────────┘
                                   │ HTTPS (:443) / HTTP (:80)
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │     AWS App Runner / Route 53 / Application LB         │
       └───────────────────────────┬────────────────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   ┌───────────────────────┐                 ┌───────────────────────┐
   │  Service Web (Flask)  │                 │ API Fast /speak-smart │
   │  Port 8000 (Gunicorn) │                 │ Port 8001 (Uvicorn)   │
   └──────────┬────────────┘                 └──────────┬────────────┘
              │                                         │
              ▼                                         ▼
 ┌───────────────────────────┐             ┌───────────────────────────┐
 │   Orchestrateur Fallback  │             │   Synthèse Vocale VITS    │
 │ 1. Gemini (Google Flash)  │             │   & Métriques (MOS, WER)  │
 │ 2. Groq (Llama-3.3-70b)   │             └───────────────────────────┘
 │ 3. Mistral (Small Latest) │
 └───────────────────────────┘
```

---

## 2. Gestion des Clés d'API & Haute Disponibilité

L'application intègre un routeur intelligent avec bascule automatique (**Gemini → Groq → Mistral**). Si le quota du premier fournisseur est épuisé (code HTTP 429), la requête est immédiatement transmise au fournisseur suivant sans interruption de service pour l'utilisateur.

### Variables d'environnement requises (.env) :
```bash
# Sécurité & Base de données
SECRET_KEY=REPLACE_WITH_SECRET
DATABASE_URL=sqlite:////app/instance/cvboost.db
COOKIE_SECURE=true

# 1. Google Gemini (Fournisseur Principal)
GEMINI_API_KEY=REPLACE_WITH_SECRET
GEMINI_MODEL=gemini-3.8-flash

# 2. Groq (Premier Fallback)
GROQ_API_KEY=REPLACE_WITH_SECRET
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo

# 3. Mistral AI (Deuxième Fallback)
MISTRAL_API_KEY=REPLACE_WITH_SECRET
MISTRAL_MODEL=mistral-small-latest

# Données Scraping & Parsing
JOB_OFFERS_FILE=/app/data_pipeline/jobs_clean.csv
```

---

## 3. Option A : Déploiement Managé via AWS App Runner (Recommandé)

**AWS App Runner** est la solution PaaS entièrement gérée d'AWS : aucun serveur Linux à maintenir, certificat SSL TLS/HTTPS automatique, mise à l'échelle automatique selon le trafic, et intégration directe avec GitHub ou Amazon ECR.

### Étapes dans la Console AWS :
1. Connectez-vous à la [Console AWS](https://console.aws.amazon.com/apprunner).
2. Cliquez sur **Create an App Runner service**.
3. **Source** :
   - Choisissez soit **Source code repository** (reliez votre repo GitHub et branche `main`),
   - Soit **Container registry** (en pointant vers l'image Amazon ECR créée par GitHub Actions).
4. **Configuration de Build** :
   - Fichier de configuration : utilisez le fichier existant `aws/apprunner.yaml` présent à la racine du projet.
   - Port : `8000`
5. **Variables d'environnement** :
   - Ajoutez `SECRET_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`.
6. Cliquez sur **Deploy**. En 3 à 5 minutes, votre application est en ligne avec une URL HTTPS sécurisée (ex: `https://xyz.eu-west-3.awsapprunner.com`).

---

## 4. Option B : Déploiement sur Instance AWS EC2 (Docker Compose)

Pour une démonstration de deux semaines, une petite instance EC2 évite les services managés dont le coût est plus difficile à prévoir. Les crédits AWS couvrent les coûts admissibles, mais ce n'est pas gratuit sans limite ; une alerte de budget ne coupe pas automatiquement les ressources.

### Étape 1 : Créer l'instance EC2
- AMI : **Ubuntu 24.04 LTS**
- Type : `t3.small` pour le site Flask seul ; prévoir plus de mémoire si l'API audio est activée.
- Région : **Europe (Paris), `eu-west-3`**.
- Security Group : SSH (`22`) depuis **My IP** uniquement ; HTTP (`80`) et HTTPS (`443`) depuis Internet pour DuckDNS et Caddy. Ne pas ouvrir `8000` ni `8001`.
- Pour environ deux semaines d'exécution continue, prévoir à titre indicatif **10 à 13 USD** pour une `t3.small`, 20 Go gp3 et une IPv4 publique. Le total réel dépend des tarifs de la région, des taxes et du trafic. Vérifier le récapitulatif AWS avant de lancer.

### Étape 2 : Configurer une URL HTTPS DuckDNS
1. Créez un sous-domaine gratuit sur [DuckDNS](https://www.duckdns.org/).
2. Dans DuckDNS, faites pointer le sous-domaine vers l'adresse IPv4 publique de l'instance.
3. Gardez l'instance en marche pendant la démo : son adresse IPv4 publique peut changer après un arrêt/redémarrage.

Le fichier `aws/Caddyfile` active automatiquement HTTPS avec Let's Encrypt. Le navigateur communique avec Caddy en HTTPS ; Flask reste uniquement accessible sur le réseau Docker. Le port `8001` de l'API n'est pas publié.

### Étape 3 : Connexion SSH et déploiement
Connectez-vous à votre instance EC2 :
```bash
ssh -i "votre-cle.pem" ubuntu@votre-ip-ec2.compute.amazonaws.com
```

Clonez le projet et lancez le script automatisé :
```bash
git clone https://github.com/votre-compte/cvboost_enterprise.git
cd cvboost_enterprise

# Configuration de votre environnement
cp .env.example .env
# Générez une clé aléatoire à copier dans SECRET_KEY :
python3 -c 'import secrets; print(secrets.token_hex(32))'
nano .env   # Configurez DOMAIN, SECRET_KEY et les clés API nécessaires

# Exécution du script d'installation et de démarrage
chmod +x aws/deploy-ec2.sh
./aws/deploy-ec2.sh
```

Générez une `SECRET_KEY` aléatoire d'au moins 32 caractères, remplacez `DOMAIN` par votre sous-domaine DuckDNS (par exemple `cvboost-demo.duckdns.org`) et renseignez les clés des fournisseurs IA. L'application sera disponible à `https://<votre-sous-domaine>.duckdns.org` après l'obtention du certificat.

Le service FastAPI audio est facultatif et ne démarre pas par défaut ; le site Flask et l'entretien vocal du navigateur fonctionnent sans lui.

Pour une démonstration de deux semaines, terminez l'instance après usage. Vérifiez également la suppression du volume EBS si les CV et la base ne doivent pas être conservés ; l'arrêt de l'instance ne supprime pas automatiquement les ressources de stockage.

---

## 5. Option C : Déploiement Conteneurisé via AWS ECS Fargate & ECR

Pour une infrastructure d'entreprise hautement disponible sans gestion d'instances :

### 1. Créer le dépôt Amazon ECR
```bash
aws ecr create-repository --repository-name cvboost --region eu-west-3
```

### 2. Builder et pousser l'image Docker
```bash
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.eu-west-3.amazonaws.com

docker build -t cvboost:latest .
docker tag cvboost:latest <AWS_ACCOUNT_ID>.dkr.ecr.eu-west-3.amazonaws.com/cvboost:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.eu-west-3.amazonaws.com/cvboost:latest
```

### 3. Créer le Cluster et la Tâche ECS Fargate
- Créez un cluster Fargate dans la console ECS.
- Créez une Task Definition avec le conteneur pointant vers votre image ECR.
- Renseignez les variables d'environnement sécurisées (via AWS Secrets Manager ou Parameter Store).
- Lancez le Service avec un Application Load Balancer (ALB).

---

## 6. Automatisation CI/CD avec GitHub Actions

Le fichier `.github/workflows/deploy.yml` est préconfiguré pour exécuter les tests à chaque commit et déployer automatiquement sur AWS lors d'un push sur `main`.

### Configuration des Secrets dans GitHub :
Rendez-vous dans votre dépôt GitHub : **Settings > Secrets and variables > Actions > New repository secret** :

| Nom du Secret | Description | Exemple |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Clé d'accès IAM avec droits ECR / App Runner / ECS | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | Clé secrète IAM | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | Région AWS cible | `eu-west-3` (Paris) ou `us-east-1` |
| `ECR_REPOSITORY` | Nom du dépôt ECR | `cvboost` |
| `AWS_APP_RUNNER_ARN` *(optionnel)* | ARN du service App Runner pour déclenchement auto | `arn:aws:apprunner:eu-west-3:...:service/cvboost` |
| `AWS_ECS_CLUSTER` *(optionnel)* | Nom du cluster ECS Fargate | `cvboost-cluster` |
| `AWS_ECS_SERVICE` *(optionnel)* | Nom du service ECS Fargate | `cvboost-service` |

---

## 7. Surveillance & Métriques MLOps en Production

### 1. Health Checks
- Web Flask : `GET /` (retourne HTTP 200)
- API FastAPI : `GET /health` :
```json
{
  "status": "healthy",
  "service": "api_service",
  "llm_engine": "Gemini-1.5-flash (with Groq and Mistral fallback)",
  "tts_engine": "Coqui-compatible VITS audio synthesizer"
}
```

### 2. Logs Amazon CloudWatch
Sur AWS App Runner ou ECS, les logs sont automatiquement centralisés dans **CloudWatch Logs** :
- Surveillez les logs applicatifs : chaque bascule de quota affiche l'alerte `[Fallback IA] Gemini a échoué (429). Bascule automatique vers Groq...`
- Suivi des erreurs HTTP et du taux de latence.

### 3. Métriques Audio Documentées
- **MOS (Mean Opinion Score)** : 4.15 / 5.0
- **WER (Word Error Rate)** : < 5.2%
- **CER (Character Error Rate)** : < 2.1%
