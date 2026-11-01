"""
Service LLM de reformulation pour FastAPI /speak-smart.
"""
import os
from typing import Optional
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()


def reformulate_pitch(cv_text: str, job_target: Optional[str] = None) -> str:
    """
    Reformule le CV brut en un discours fluide, percutant et engageant via Groq.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    mistral_key = os.getenv("MISTRAL_API_KEY")

    if not any([gemini_key, groq_key, mistral_key]):
        lines = [line.strip() for line in cv_text.splitlines() if line.strip()]
        intro = lines[0] if lines else "Candidat qualifié"
        target_str = f" pour le poste de {job_target}" if job_target else ""
        return (
            f"Bonjour, je suis ravi de vous présenter mon profil{target_str}. "
            f"Fort de mon parcours en {intro[:100]}, j'ai développé des compétences clés "
            f"orientées résultats et impact. Passionné par l'innovation, je serais honoré d'échanger avec vous."
        )

    try:
        from app.llm_router import call_llm_with_fallback

        prompt = (
            "Tu es un coach expert en communication et pitch de recrutement. "
            "À partir du texte brut du CV suivant, rédige un pitch professionnel, captivant, fluide "
            "et à la première personne ('Je') d'environ 60 à 90 mots (30 secondes de parole). "
            "Ne rajoute aucun commentaire méta, réponds uniquement avec le texte exact du pitch."
        )
        if job_target:
            prompt += f"\nPoste ciblé : {job_target}"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"CV :\n{cv_text[:4000]}"}
        ]

        pitch, provider_used = call_llm_with_fallback(
            messages=messages,
            temperature=0.3,
            json_mode=False,
            gemini_key=gemini_key,
            groq_key=groq_key,
            mistral_key=mistral_key,
        )
        pitch = pitch.strip()
        if pitch.startswith('"') and pitch.endswith('"'):
            pitch = pitch[1:-1]
        return pitch
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erreur lors de la reformulation LLM : {str(error)}"
        )
