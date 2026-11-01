# Déploiement de CVBoost sur Render

Le fichier [`render.yaml`](./render.yaml) définit les deux services CVBoost :

- `cvboost-web` : application Flask lancée par Gunicorn.
- `cvboost-audio-api` : API FastAPI lancée par Uvicorn.

## Mise en ligne

1. Connectez le dépôt GitHub à Render et créez un **Blueprint** à partir de ce dépôt.
2. Render lit `render.yaml` et prépare les deux services sur le plan gratuit.
3. Renseignez les clés des fournisseurs IA demandées lors de la création du
   Blueprint (`GEMINI_API_KEY`, `GROQ_API_KEY` et `MISTRAL_API_KEY`) dans
   l'interface Render. Ne les stockez pas dans Git.
4. Les déploiements sont déclenchés après la réussite des vérifications CI
   GitHub (`autoDeployTrigger: checksPass`).

Render génère automatiquement `SECRET_KEY` et fournit `PORT`. Les cookies
sécurisés et la confiance du proxy HTTPS sont activés pour l'application Web.
Les deux services gratuits peuvent se mettre en veille après une période
d'inactivité.

## Limites importantes du plan gratuit

Le plan gratuit n'a pas de disque persistant. La base SQLite, les CV téléversés,
le journal d'audit et les fichiers audio temporaires peuvent être supprimés lors
d'un redémarrage, d'une mise en veille ou d'un nouveau déploiement. Utilisez
cette configuration uniquement pour une démonstration sans données importantes.

Pour conserver les données, passez le service Web à un plan payant avec disque
persistant ou migrez vers PostgreSQL et un stockage objet. Le code est déployé
depuis la branche connectée à Render ; les anciennes configurations AWS ne sont
plus utilisées.
