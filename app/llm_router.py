"""
Orchestrateur Multi-Fournisseurs LLM avec Bascule Automatique (Fallback):
Ordre d'exécution prioritaire : Gemini (Google) → Groq → Mistral AI.
Si le quota ou la limite d'un fournisseur est atteint (HTTP 429 / Quota Exceeded),
l'appel bascule automatiquement et de manière transparente vers le fournisseur suivant.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

# Modèles par défaut recommandés
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"
DEFAULT_MISTRAL_MODEL = "mistral-small-latest"

# Endpoints OpenAI-compatibles pour Gemini et Mistral
GEMINI_OPENAI_COMPAT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"

# Limites prudentes pour éviter les erreurs de quota côté Render / modèles gratuits.
# On force une sortie courte pour les réponses JSON, car le message d'erreur Groq montrait
# exactement une dépassement de budget en sortie tokens.
MAX_OUTPUT_TOKENS = 700


class LLMProviderError(RuntimeError):
    """Erreur générique d'un fournisseur LLM."""
    pass


class LLMQuotaExceededError(LLMProviderError):
    """Quota ou limite de requêtes atteint (HTTP 429)."""
    pass


def is_quota_error(status_code: Optional[int], error_text: str) -> bool:
    """Détecte si une erreur correspond à un quota ou rate limit dépassé."""
    if status_code == 429:
        return True
    lowered = error_text.lower()
    quota_keywords = [
        "quota", "rate limit", "resource_exhausted", "tokens per minute",
        "requests per minute", "tpm", "rpm", "too many requests", "exceeded"
    ]
    return any(keyword in lowered for keyword in quota_keywords)


def _build_provider_payload(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    json_mode: bool,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Construit un payload cohérent selon le fournisseur."""
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _call_gemini(
    messages: List[Dict[str, str]],
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.2,
    json_mode: bool = False,
    timeout: float = 40.0,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> str:
    """Appel à l'API Gemini (via endpoint compatible OpenAI officiel de Google)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = _build_provider_payload(
        messages=messages,
        model=model or DEFAULT_GEMINI_MODEL,
        temperature=temperature,
        json_mode=json_mode,
        max_tokens=max_tokens,
    )

    try:
        response = requests.post(
            GEMINI_OPENAI_COMPAT_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise LLMProviderError(f"Connexion Gemini impossible : {exc}") from exc

    if response.status_code != 200:
        err_msg = response.text[:400]
        if is_quota_error(response.status_code, err_msg):
            raise LLMQuotaExceededError(f"Gemini quota atteint (HTTP {response.status_code}) : {err_msg}")
        raise LLMProviderError(f"Gemini a répondu avec le statut HTTP {response.status_code} : {err_msg}")

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if not content:
            raise ValueError("Contenu vide retourné par Gemini")
        return content
    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        raise LLMProviderError(f"Réponse Gemini malformée : {exc}") from exc


def _call_groq(
    messages: List[Dict[str, str]],
    api_key: str,
    model: str = DEFAULT_GROQ_MODEL,
    temperature: float = 0.2,
    json_mode: bool = False,
    timeout: float = 40.0,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> str:
    """Appel à l'API Groq (supporte le mock de app.ia.Groq dans les tests)."""
    import sys
    if 'app.ia' in sys.modules and hasattr(sys.modules['app.ia'], 'Groq'):
        Groq = getattr(sys.modules['app.ia'], 'Groq')
    else:
        try:
            from groq import Groq
        except ImportError:
            raise LLMProviderError("Le package 'groq' n'est pas installé.")

    try:
        client = Groq(api_key=api_key, timeout=timeout, max_retries=1)
        kwargs: Dict[str, Any] = {
            "model": model or DEFAULT_GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Contenu vide retourné par Groq")
        return content
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        err_msg = str(exc)
        if is_quota_error(status_code, err_msg):
            raise LLMQuotaExceededError(f"Groq quota atteint (HTTP {status_code}) : {err_msg}") from exc
        raise LLMProviderError(f"Erreur Groq : {err_msg}") from exc


def _call_mistral(
    messages: List[Dict[str, str]],
    api_key: str,
    model: str = DEFAULT_MISTRAL_MODEL,
    temperature: float = 0.2,
    json_mode: bool = False,
    timeout: float = 40.0,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> str:
    """Appel à l'API Mistral AI (via endpoint chat officiel)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = _build_provider_payload(
        messages=messages,
        model=model or DEFAULT_MISTRAL_MODEL,
        temperature=temperature,
        json_mode=json_mode,
        max_tokens=max_tokens,
    )

    try:
        response = requests.post(
            MISTRAL_CHAT_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise LLMProviderError(f"Connexion Mistral impossible : {exc}") from exc

    if response.status_code != 200:
        err_msg = response.text[:400]
        if is_quota_error(response.status_code, err_msg):
            raise LLMQuotaExceededError(f"Mistral quota atteint (HTTP {response.status_code}) : {err_msg}")
        raise LLMProviderError(f"Mistral a répondu avec le statut HTTP {response.status_code} : {err_msg}")

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if not content:
            raise ValueError("Contenu vide retourné par Mistral")
        return content
    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        raise LLMProviderError(f"Réponse Mistral malformée : {exc}") from exc


def call_llm_with_fallback(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    json_mode: bool = False,
    gemini_key: Optional[str] = None,
    gemini_model: Optional[str] = None,
    groq_key: Optional[str] = None,
    groq_model: Optional[str] = None,
    mistral_key: Optional[str] = None,
    mistral_model: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Exécute la chaîne de fallback dans l'ordre strict :
    1. Gemini (Google)
    2. Groq
    3. Mistral AI

    Retourne le tuple (content, provider_name_used).
    Si un fournisseur est non configuré ou dépasse son quota, l'orchestrateur
    bascule automatiquement au fournisseur suivant avec un avertissement de journalisation.
    """
    gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
    gemini_model = gemini_model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    groq_key = groq_key or os.getenv("GROQ_API_KEY")
    groq_model = groq_model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    mistral_key = mistral_key or os.getenv("MISTRAL_API_KEY")
    mistral_model = mistral_model or os.getenv("MISTRAL_MODEL", DEFAULT_MISTRAL_MODEL)

    errors_summary: List[str] = []

    # 1. TENTATIVE GEMINI
    if gemini_key:
        try:
            logger.info("Tentative de génération LLM via Gemini (modèle: %s)...", gemini_model)
            content = _call_gemini(
                messages=messages,
                api_key=gemini_key,
                model=gemini_model,
                temperature=temperature,
                json_mode=json_mode,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
            return content, "gemini"
        except (LLMQuotaExceededError, LLMProviderError, Exception) as exc:
            msg = f"Gemini a échoué ({exc}). Bascule automatique vers Groq..."
            logger.warning(msg)
            errors_summary.append(f"Gemini: {exc}")
    else:
        logger.debug("GEMINI_API_KEY non renseignée, passage à Groq.")

    # 2. TENTATIVE GROQ
    if groq_key:
        try:
            logger.info("Tentative de génération LLM via Groq (modèle: %s)...", groq_model)
            content = _call_groq(
                messages=messages,
                api_key=groq_key,
                model=groq_model,
                temperature=temperature,
                json_mode=json_mode,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
            return content, "groq"
        except (LLMQuotaExceededError, LLMProviderError, Exception) as exc:
            msg = f"Groq a échoué ({exc}). Bascule automatique vers Mistral..."
            logger.warning(msg)
            errors_summary.append(f"Groq: {exc}")
    else:
        logger.debug("GROQ_API_KEY non renseignée, passage à Mistral.")

    # 3. TENTATIVE MISTRAL
    if mistral_key:
        try:
            logger.info("Tentative de génération LLM via Mistral (modèle: %s)...", mistral_model)
            content = _call_mistral(
                messages=messages,
                api_key=mistral_key,
                model=mistral_model,
                temperature=temperature,
                json_mode=json_mode,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
            return content, "mistral"
        except (LLMQuotaExceededError, LLMProviderError, Exception) as exc:
            msg = f"Mistral a échoué ({exc})."
            logger.error(msg)
            errors_summary.append(f"Mistral: {exc}")
    else:
        logger.debug("MISTRAL_API_KEY non renseignée.")

    if not any([gemini_key, groq_key, mistral_key]):
        raise LLMProviderError(
            "Aucune clé d'API d'IA n'est configurée. Définissez au moins une clé parmi "
            "GEMINI_API_KEY, GROQ_API_KEY ou MISTRAL_API_KEY dans votre fichier .env."
        )

    raise LLMProviderError(
        f"Tous les fournisseurs d'IA configurés ont échoué (quota ou indisponibilité) : "
        + " | ".join(errors_summary)
    )

