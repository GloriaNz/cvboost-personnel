#!/usr/bin/env bash
# ==============================================================================
# Script de déploiement automatisé CVBoost sur instance AWS EC2 (Ubuntu / Amazon Linux 2023)
# ==============================================================================
set -e

echo "🚀 [1/5] Mise à jour du système et installation de Docker..."
if [ -f /etc/debian_version ]; then
    sudo apt-get update -y
    sudo apt-get install -y docker.io docker-compose git curl
elif [ -f /etc/redhat-release ] || [ -f /etc/system-release ]; then
    sudo dnf update -y
    sudo dnf install -y docker git
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo "🐳 [2/5] Démarrage du service Docker..."
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER || true

echo "📁 [3/5] Préparation de l'environnement CVBoost..."
if [ ! -f .env ]; then
    echo "⚠️ Fichier .env non détecté. Copie depuis .env.example..."
    cp .env.example .env
    echo "❗ Veuillez éditer le fichier .env pour renseigner vos clés GEMINI_API_KEY, GROQ_API_KEY et MISTRAL_API_KEY."
fi

echo "🏗️ [4/5] Construction et lancement des conteneurs via Docker Compose..."
docker-compose -f aws/docker-compose.aws.yml up -d --build

echo "✅ [5/5] CVBoost est déployé et opérationnel sur AWS !"
echo "🌐 Application Flask : http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo 'VOTRE_IP_EC2')"
echo "⚡ FastAPI /speak-smart : http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo 'VOTRE_IP_EC2'):8001/docs"
