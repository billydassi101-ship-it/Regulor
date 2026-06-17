# backend/rag/generator.py
# Orchestre l'analyse d'intention + le retriever + le prompt strict + le LLM Router
# Version durcie pour la conformité réglementaire (Zéro Hallucination & Reranking Mandatoire)

import os
import sys
import unicodedata

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rag.retriever import retrieve, format_context
from rag.prompt import build_rag_prompt, build_no_context_prompt
from model_router import call_llm

MAX_HISTORY_MESSAGES = 6


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace("â€™", "'").replace("’", "'")
    text = text.replace("?", "").replace("!", "").replace(",", " ").replace(".", " ")

    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )

    return " ".join(without_accents.split())


def detect_intent(question: str) -> str:
    q = normalize_text(question)

    greetings = ["salut", "bonjour", "bonsoir", "coucou", "hello", "hey", "yo"]

    identity_patterns = [
        "qui es tu", "qui es-tu", "tu es qui", 
        "c'est quoi regulor", "c est quoi regulor", 
        "presente toi", "présente toi"
    ]

    capability_patterns = [
        "que fais tu", "que fais-tu", "tu fais quoi", "tu fais quoi ici", 
        "que fais tu ici", "que fais-tu ici", "que peux tu faire", 
        "que peux-tu faire", "tu peux faire quoi", "aide moi", 
        "comment tu peux m'aider", "comment tu peux m aider"
    ]

    latency_patterns = [
        "pourquoi tu prends du temps", "pourquoi tu as pris du temps", 
        "pourquoi t as pris du temps", "pourquoi t'as pris du temps", 
        "tu as pris trop de temps", "t as pris trop de temps", 
        "t'as pris trop de temps", "trop de temps", "c es lent", 
        "c'est lent", "pourquoi c es long", "pourquoi c'est long", 
        "ca prend du temps", "ça prend du temps"
    ]

    thanks_patterns = ["merci", "ok merci", "d accord merci", "daccord merci"]

    obvious_out_of_domain_keywords = [
        "football", "entraineur", "nagelsmann", "bayern", "psg", 
        "real madrid", "barcelone", "metaphore", "film", "musique", 
        "recette", "jeu video"
    ]

    banking_keywords = [
        "banque", "bancaire", "conformite", "conformité", "reglementation", 
        "réglementation", "acpr", "amf", "bce", "kyc", "lcb", "ft", 
        "blanchiment", "terrorisme", "credit", "crédit", "client", "risque", 
        "audit", "controle", "contrôle", "procedure", "procédure", "document", 
        "regle", "règle", "regles", "règles", "institution", "etablissement", 
        "établissement", "delit", "délit", "fraude", "sanction", "obligation", "obligations"
    ]

    if q in greetings:
        return "greeting"

    if any(pattern in q for pattern in identity_patterns):
        return "identity"

    if any(pattern in q for pattern in capability_patterns):
        return "capabilities"

    if any(pattern in q for pattern in latency_patterns):
        return "latency_explanation"

    if q in thanks_patterns or q.startswith("merci"):
        return "thanks"

    if any(keyword in q for keyword in obvious_out_of_domain_keywords):
        return "out_of_domain"

    if any(keyword in q for keyword in banking_keywords):
        return "rag"

    return "unclear"


def direct_response_for_intent(intent: str) -> str | None:
    if intent == "greeting":
        return (
            "Bonjour 👋 Je suis Regulor, votre assistant IA interne spécialisé "
            "dans la conformité bancaire, les procédures internes et les documents réglementaires."
        )

    if intent == "identity":
        return (
            "Je suis Regulor, un assistant IA interne conçu pour aider les employés "
            "à consulter les procédures internes, les documents de conformité bancaire "
            "et les textes réglementaires disponibles dans la base documentaire."
        )

    if intent == "capabilities":
        return (
            "Je peux rechercher dans les documents indexés, expliquer des règles de conformité, "
            "résumer des procédures internes, retrouver des passages réglementaires et citer les sources utilisées."
        )

    if intent == "latency_explanation":
        return (
            "J’ai pris du temps parce que je dois exécuter une recherche hybride multicritères, "
            "vérifier la proximité sémantique des segments documentaires via un modèle CrossEncoder local, "
            "puis synthétiser les informations valides via le grand modèle de langage pour éviter toute hallucination."
        )

    if intent == "thanks":
        return "Avec plaisir. Posez-moi une autre question sur les documents ou la conformité bancaire."

    if intent == "out_of_domain":
        return (
            "Cette question semble sortir de mon périmètre d'action principal. "
            "Je suis exclusivement spécialisé dans la conformité bancaire, les procédures internes "
            "et les documents réglementaires de l'établissement."
        )

    return None


def clean_history(history: list) -> list:
    """
    Garde seulement les derniers messages utiles pour l'historique contextuel.
    """
    cleaned = []
    for message in history:
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content")

        if role not in ["user", "assistant"]:
            continue

        if not isinstance(content, str) or not content.strip():
            continue

        cleaned.append(
            {
                "role": role,
                "content": content.strip(),
            }
        )

    return cleaned[-MAX_HISTORY_MESSAGES:]


def build_sources(chunks: list[dict]) -> list[dict]:
    """
    Extrait et compile proprement les métadonnées de traçabilité des fragments documentaires.
    """
    sources = []
    seen = set()

    for chunk in chunks:
        key = (
            chunk.get("filename"),
            chunk.get("source_type", "internal"),
        )

        if key in seen:
            continue

        seen.add(key)

        # Extraction prioritaire du score sémantique fin calculé par le CrossEncoder Reranker
        score = chunk.get("rerank_score")
        if score is None:
            score = chunk.get("combined_score", chunk.get("similarity", 0.0))
        
        sources.append(
            {
                "filename": chunk.get("filename", "Source_Inconnue.pdf"),
                "source_type": chunk.get("source_type", "internal"),
                "similarity": round(float(score), 3),
            }
        )

    return sources


def generate_response(
    question: str,
    history: list,
    temp_context: str = None,
    temp_context_filename: str | None = None,
) -> dict:
    """
    Fonction maîtresse d'orchestration de l'inférence RAG :
    1. Interception des intentions directes hors pipeline
    2. Extraction et alignement sémantique via le retriever (Top 4 avec CrossEncoder activé)
    3. Injection du contexte cloisonné dans le template de prompt restrictif
    4. Appel asynchrone sécurisé de la couche de calcul LLM (Groq / Ollama Fallback)
    """
    intent = detect_intent(question)
    direct_answer = direct_response_for_intent(intent)

    if direct_answer:
        return {
            "response": direct_answer,
            "sources": [],
            "web_sources": [],
            "found": False,
        }

    chunks = []

    # Exécution du retriever avec activation explicite et obligatoire du Reranker par CrossEncoder
    if not temp_context:
        chunks = retrieve(
            query=question,
            top_k=4,            # Aligné sur la constante d'attention restrictive du retriever
            use_reranker=True   # Forcé à True pour garantir l'ordre chirurgical (Correction RGPD)
        )

    # Structuration formelle de la fenêtre de contexte informatique
    if temp_context:
        if temp_context_filename:
            context = f"[FICHIER CLOISONNÉ EN SESSION - {temp_context_filename}]\n{temp_context}"
        else:
            context = f"[FICHIER CLOISONNÉ EN SESSION]\n{temp_context}"
    elif chunks:
        context = format_context(chunks)
    else:
        context = None

    # Application des templates de prompt restrictifs (Grounding strict ou Blocage d'hallucination)
    if context:
        prompt = build_rag_prompt(question, context)
        found = True
    else:
        prompt = build_no_context_prompt(question)
        found = False

    # Fusion de la mémoire glissante de session avec l'instruction système courante
    messages = clean_history(history) + [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    # Inférence via l'orchestrateur de modèles de calcul (Groq Llama 3.3 70B / Ollama Mistral 7B)
    response_text = call_llm(messages)

    # Compilation des sources pour l'inspecteur d'interface graphique
    sources = build_sources(chunks)

    if temp_context and temp_context_filename:
        temp_source = {
            "filename": temp_context_filename,
            "source_type": "temp",
            "similarity": 1.0,
        }
        sources = [temp_source] + [
            source for source in sources
            if source.get("filename") != temp_context_filename
        ]

    return {
        "response": response_text,
        "sources": sources,
        "web_sources": [],
        "found": found,
    }