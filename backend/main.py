# main.py
# Backend FastAPI principal de Regulor
# Routes :
# - GET  /health
# - POST /chat
# - POST /chat/upload
# - GET  /documents
# - DELETE /documents/{filename}

import os
import json
import sys
from typing import List, Optional, Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, dotenv_values

# Permet d'importer les modules internes du backend
sys.path.append(os.path.dirname(__file__))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

from rag.generator import generate_response
from ingestion.loader import load_file
from ingestion.chunker import chunk_with_metadata
from ingestion.embedder import embed_chunks
from ingestion.indexer import list_documents, delete_document, index_chunks


UPLOAD_CONTEXTS: dict[str, dict[str, str]] = {}
DEFAULT_ADMIN_PASSWORD = "RegulorLocalAdmin2026!"


def get_admin_password() -> str:
    dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    values = dotenv_values(dotenv_path)
    return (
        values.get("ADMIN_PASSWORD")
        or os.getenv("ADMIN_PASSWORD")
        or DEFAULT_ADMIN_PASSWORD
    ).strip()


app = FastAPI(
    title="Regulor API",
    description="Backend IA interne pour conformité bancaire et RAG documentaire",
    version="1.0.0",
)


# CORS pour autoriser le frontend Next.js local
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    question: Optional[str] = None
    history: List[ChatMessage] = []
    session_id: Optional[str] = None


class AdminLoginRequest(BaseModel):
    password: str


@app.get("/")
def root():
    return {
        "name": "Regulor API",
        "status": "running",
        "routes": [
            "GET /health",
            "POST /chat",
            "POST /chat/upload",
            "POST /chat/context/reset",
            "GET /documents",
            "DELETE /documents/{filename}",
            "POST /admin/login",
            "POST /admin/upload",
        ],
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Regulor backend is running",
    }


@app.post("/chat/context/reset")
def reset_chat_context(session_id: str = Form(...)):
    """
    Supprime le contexte temporaire associé à une session de chat.
    Permet de sortir proprement d'un fichier joint.
    """

    UPLOAD_CONTEXTS.pop(session_id, None)

    return {
        "success": True,
        "message": "Contexte de session supprimé.",
    }


@app.post("/admin/login")
def admin_login(request: AdminLoginRequest):
    admin_password = get_admin_password()

    if not admin_password:
        raise HTTPException(
            status_code=500,
            detail="Mot de passe admin non configuré côté backend.",
        )

    if request.password != admin_password:
        raise HTTPException(
            status_code=401,
            detail="Mot de passe admin invalide.",
        )

    return {
        "authenticated": True,
        "token": admin_password,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    """
    Endpoint principal du chat.

    Le frontend envoie :
    {
      "question": "ma question",
      "history": [
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "..."}
      ]
    }
    """

    try:
        history = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in request.history
        ]

        question = request.question
        session_id = request.session_id

        # Fallback si l'ancien frontend envoie uniquement history
        if not question and history:
            last_user_message = next(
                (
                    message["content"]
                    for message in reversed(history)
                    if message["role"] == "user"
                ),
                None,
            )
            question = last_user_message

        if not question or not question.strip():
            raise HTTPException(
                status_code=400,
                detail="Question vide ou absente.",
            )

        print(f"[API] Nouvelle question : {question}")

        temp_context = None
        temp_context_filename = None
        if session_id:
            stored_context = UPLOAD_CONTEXTS.get(session_id) or {}
            temp_context = stored_context.get("content")
            temp_context_filename = stored_context.get("filename")

        result = generate_response(
            question=question.strip(),
            history=history,
            temp_context=temp_context,
            temp_context_filename=temp_context_filename,
        )

        return {
            "response": result["response"],
            "sources": result["sources"],
            "web_sources": result.get("web_sources", []),
            "found": result["found"],
        }

    except HTTPException:
        raise

    except Exception as error:
        print(f"[API] Erreur /chat : {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne backend : {str(error)}",
        )


@app.post("/chat/upload")
async def chat_upload(
    file: UploadFile = File(...),
    question: str = Form(...),
    history: str = Form(default="[]"),
    session_id: str = Form(default=""),
):
    """
    Endpoint chat avec fichier temporaire.

    Le fichier est lu pour cette question uniquement.
    Il n'est pas indexé définitivement dans Supabase.
    """

    try:
        if not question or not question.strip():
            raise HTTPException(
                status_code=400,
                detail="Question vide ou absente.",
            )

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Nom de fichier invalide.",
            )

        allowed_extensions = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp"]
        extension = file.filename.lower().split(".")[-1]

        if extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Format non supporté : {extension}. "
                    f"Formats acceptés : {', '.join(allowed_extensions)}"
                ),
            )

        print(f"[API] Fichier temporaire reçu : {file.filename}")
        print(f"[API] Question avec fichier : {question}")

        file_bytes = await file.read()

        temp_context = load_file(
            file_bytes=file_bytes,
            filename=file.filename,
        )

        if not temp_context.strip():
            raise HTTPException(
                status_code=400,
                detail="Aucun texte exploitable n'a été extrait du fichier.",
            )

        try:
            parsed_history = json.loads(history)
            if not isinstance(parsed_history, list):
                parsed_history = []
        except Exception:
            parsed_history = []

        clean_history = []

        for message in parsed_history:
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            content = message.get("content")

            if role in ["user", "assistant", "system"] and isinstance(content, str):
                clean_history.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

        if session_id:
            UPLOAD_CONTEXTS[session_id] = {
                "content": temp_context,
                "filename": file.filename,
            }

        result = generate_response(
            question=question.strip(),
            history=clean_history,
            temp_context=temp_context,
            temp_context_filename=file.filename,
        )

        return {
            "response": result["response"],
            "sources": result["sources"],
            "web_sources": result.get("web_sources", []),
            "found": result["found"],
            "session_id": session_id or None,
        }

    except HTTPException:
        raise

    except Exception as error:
        print(f"[API] Erreur /chat/upload : {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne backend upload : {str(error)}",
        )


@app.get("/documents")
def get_documents():
    """
    Liste les documents indexés dans Supabase.
    Utilisé par l'admin ou l'interface documents.
    """

    try:
        documents = list_documents()

        return {
            "documents": documents,
            "count": len(documents),
        }

    except Exception as error:
        print(f"[API] Erreur /documents : {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de lister les documents : {str(error)}",
        )


@app.delete("/documents/{filename}")
def remove_document(filename: str):
    """
    Supprime tous les chunks associés à un document.
    """

    try:
        success = delete_document(filename)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Suppression échouée.",
            )

        return {
            "success": True,
            "message": f"Document supprimé : {filename}",
        }

    except HTTPException:
        raise

    except Exception as error:
        print(f"[API] Erreur suppression document : {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur suppression document : {str(error)}",
        )


@app.post("/admin/upload")
async def admin_upload(
    files: list[UploadFile] = File(...),
    admin_token: str = Header(default="", alias="X-Admin-Token"),
    source_type: str = Form(default="internal"),
):
    """
    Ingestion admin directe vers Supabase.
    Les fichiers sont chunkés, vectorisés puis indexés immédiatement.
    """

    admin_password = get_admin_password()
    if not admin_password:
        raise HTTPException(
            status_code=500,
            detail="Mot de passe admin non configuré côté backend.",
        )

    if admin_token != admin_password:
        raise HTTPException(
            status_code=401,
            detail="Accès admin refusé.",
        )

    if not files:
        raise HTTPException(
            status_code=400,
            detail="Aucun fichier fourni.",
        )

    allowed_extensions = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp"]
    results = []

    for file in files:
        if not file.filename:
            results.append(
                {
                    "filename": None,
                    "success": False,
                    "error": "Nom de fichier invalide.",
                }
            )
            continue

        extension = file.filename.lower().split(".")[-1]
        if extension not in allowed_extensions:
            results.append(
                {
                    "filename": file.filename,
                    "success": False,
                    "error": (
                        f"Format non supporté : {extension}. "
                        f"Formats acceptés : {', '.join(allowed_extensions)}"
                    ),
                }
            )
            continue

        try:
            file_bytes = await file.read()
            text = load_file(file_bytes=file_bytes, filename=file.filename)

            if not text.strip():
                results.append(
                    {
                        "filename": file.filename,
                        "success": False,
                        "error": "Aucun texte exploitable n'a été extrait.",
                    }
                )
                continue

            delete_document(file.filename)

            chunks = chunk_with_metadata(
                text=text,
                filename=file.filename,
                source_type=source_type,
                chunk_size=500,
                overlap=100,
            )

            chunks = embed_chunks(chunks)
            inserted = index_chunks(chunks)

            results.append(
                {
                    "filename": file.filename,
                    "success": True,
                    "chunks_indexed": inserted,
                    "source_type": source_type,
                }
            )
        except Exception as error:
            results.append(
                {
                    "filename": file.filename,
                    "success": False,
                    "error": str(error),
                }
            )

    return {
        "success": True,
        "results": results,
        "count": len(results),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
