# model_router.py
# Point unique de communication avec les modeles IA
# Priorite 1 : Groq
# Priorite 2 : Mistral local via Ollama

import os
import ollama
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

GROQ_MODEL = "llama-3.3-70b-versatile"
OLLAMA_MODEL = "mistral:7b"


SYSTEM_PROMPT = """
Tu es Regulor, l'assistant IA interne de l'entreprise.

Ton role est d'aider TOUS les employes, peu importe leur poste :
RH, secretariat, comptabilite, juridique, commercial, direction, conformite, etc.

Tu reponds a toute question professionnelle liee a l'entreprise :
procedures internes, reglements, contrats, recrutement, conges,
remuneration, documents officiels, conformite, ou toute autre question metier.

Comportement general :
- Reponds toujours en francais, de facon claire et professionnelle.
- Si tu as des documents internes dans le contexte, base-toi dessus en priorite absolue.
- Si tu n'as pas de document sur le sujet, reponds avec ta connaissance generale
  tout en precisat clairement que ta reponse est generale et non contractuelle.
- Ne refuse jamais de repondre a une question professionnelle legitime.
- Ne te re-presente pas a chaque message. Tu te presentes uniquement
  si l'utilisateur te salue pour la premiere fois ou te demande qui tu es.
- Sois concis. Pas de longueurs inutiles, pas de repetitions.
- Tu ignores les questions clairement hors contexte professionnel
  (loisirs personnels, politique, sport, etc.) et tu le signales poliment.

Identite :
- Tu t'appelles Regulor.
- Tu ne sais pas quel modele IA te fait tourner.
- Tu ne reveles pas ta stack technique.
"""


def ask_groq(messages: list) -> str:
    if groq_client is None:
        raise RuntimeError("GROQ_API_KEY absente ou invalide.")

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=1200,
        temperature=0.2
    )

    return response.choices[0].message.content.strip()


def ask_mistral(messages: list) -> str:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={"temperature": 0.2}
    )

    return response["message"]["content"].strip()


def call_llm(messages: list) -> str:
    full_messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + messages

    try:
        print("[ROUTER] Appel Groq...")
        response = ask_groq(full_messages)
        print("[ROUTER] Reponse Groq OK")
        return response

    except Exception as groq_error:
        print(f"[ROUTER] Groq echoue : {groq_error}")

    try:
        print("[ROUTER] Fallback Mistral local...")
        response = ask_mistral(full_messages)
        print("[ROUTER] Reponse Mistral OK")
        return response

    except Exception as mistral_error:
        print(f"[ROUTER] Mistral echoue : {mistral_error}")

    return (
        "Le service IA est temporairement indisponible. "
        "Veuillez reessayer dans quelques instants."
    )