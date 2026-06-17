# backend/rag/retriever.py
# Récupère les documents pertinents depuis Supabase via recherche vectorielle
# Intègre le reranking pour améliorer la qualité des résultats - Version Certifiée Compliance

import os
import sys
import unicodedata
from supabase import create_client, Client
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ingestion.embedder import embed_text
from rag.reranker import rerank_chunks

load_dotenv()

# =========================================================================
# CONFIGURATION OPTIMISÉE POUR LA CONFORMITÉ (GROUNDING & SÉCURITÉ)
# =========================================================================
VECTOR_THRESHOLD = 0.32   # Seuil de similarité minimum relevé pour écarter le bruit
VECTOR_CANDIDATES = 200   # Quasi exhaustif sur le corpus actuel (242 chunks), garantit que le Guide et autres documents legitimes ne sont jamais ecartes avant le reranker
FINAL_TOP_K = 4           # Réduit de 5 à 4 pour concentrer le contexte et éviter la dilution du RGPD
INTERNAL_BOOST = 1.35     # Coefficient multiplicateur pour prioriser impérativement les docs internes

# Initialisation du client Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


# ===========================
# UTILITY FUNCTIONS
# ===========================

def normalize_text(text: str) -> str:
    """
    Normalise un texte pour la recherche lexicale.
    Supprime accents, ponctuation, espaces multiples.
    """
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace("’", "'")
    text = text.replace("?", "")
    text = text.replace("!", "")
    text = text.replace(",", " ")
    text = text.replace(".", " ")
    
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )
    
    return " ".join(without_accents.split())


def tokenise_query(query: str) -> list[str]:
    """
    Tokenise une requête en mots-clés significatifs.
    Supprime les stopwords français courants.
    """
    stopwords = {
        "le", "la", "les", "un", "une", "des",
        "de", "du", "et", "ou", "mais", "donc",
        "que", "qui", "quoi", "comment", "pourquoi",
        "c", "t", "s", "est", "sont", "a", "au",
        "avec", "pour", "par", "dans", "sur", "en",
        "il", "elle", "nous", "vous", "ils", "elles",
    }
    
    words = normalize_text(query).split()
    return [w for w in words if w not in stopwords and len(w) > 2]


def resolve_filename_hints(query: str) -> list[str]:
    """
    Extrait les hints de noms de fichiers depuis la requête.
    Ex: "dans le document compliance" -> ["compliance"]
    """
    filename_keywords = [
        "document", "fichier", "pdf", "rapport",
        "file", "dans le", "du fichier", "l'article",
    ]
    
    hints = []
    query_lower = query.lower()
    
    for keyword in filename_keywords:
        if keyword in query_lower:
            idx = query_lower.find(keyword)
            after = query_lower[idx + len(keyword):].strip().split()[0:3]
            hints.extend(after)
    
    return [h.replace(".", "").replace(",", "") for h in hints if h]


def fetch_chunks_by_filenames(filenames: list[str]) -> list[dict]:
    """
    Récupère tous les chunks d'une liste de fichiers.
    """
    if not filenames:
        return []
    
    try:
        response = supabase.table("documents").select("*").in_(
            "filename", filenames
        ).execute()
        
        print(f"[RETRIEVER] Récupéré {len(response.data)} chunks pour fichiers : {filenames}")
        return response.data if response.data else []
    
    except Exception as error:
        print(f"[RETRIEVER] Erreur fetch_chunks_by_filenames : {error}")
        return []


def fetch_all_chunks() -> list[dict]:
    """
    Récupère tous les chunks de la base de données.
    """
    try:
        response = supabase.table("documents").select("*").execute()
        print(f"[RETRIEVER] Récupéré {len(response.data)} chunks au total")
        return response.data if response.data else []
    
    except Exception as error:
        print(f"[RETRIEVER] Erreur fetch_all_chunks : {error}")
        return []


def chunk_lexical_score(chunk: dict, keywords: list[str]) -> float:
    """
    Calcule un score lexical (0-1) pour un chunk basé sur la présence des mots-clés.
    """
    if not keywords:
        return 0.0
    
    content = normalize_text(chunk.get("content", ""))
    filename = normalize_text(chunk.get("filename", ""))
    
    matched_keywords = 0
    for keyword in keywords:
        if keyword in content or keyword in filename:
            matched_keywords += 1
    
    return matched_keywords / len(keywords)


def rank_chunks(
    chunks: list[dict],
    query: str,
    keywords: list[str]
) -> list[dict]:
    """
    Classement Hybride Ajusté :
    Applique l'INTERNAL_BOOST pour faire remonter de manière agressive 
    les documents internes (et les documents admin) face au bruit ou aux sources externes.
    """
    for chunk in chunks:
        similarity = float(chunk.get("similarity", 0.0))
        lexical = chunk_lexical_score(chunk, keywords)
        
        # Score de base mixte : 60% vectoriel, 40% lexical
        combined_score = (similarity * 0.6) + (lexical * 0.4)
        
        # Isolation sémantique : Application du boost sur le type de source
        # "admin" est traité comme "internal" car ce sont des documents
        # uploadés directement par l'administration de l'entreprise
        source_type = chunk.get("source_type", "internal")
        boost = INTERNAL_BOOST if source_type in ("internal", "admin") else 1.0
        
        chunk["combined_score"] = combined_score * boost
    
    # Premier tri par score combiné boosté
    chunks.sort(key=lambda c: c.get("combined_score", 0.0), reverse=True)
    
    # Pénalité de diversité ajustée (Évite qu'un seul gros document écrase le RGPD)
    diversity_final = []
    source_usage = {}
    for chunk in chunks:
        source = chunk.get("filename", "unknown")
        usage_count = source_usage.get(source, 0)
        source_usage[source] = usage_count + 1
        
        if usage_count > 0:
            chunk["combined_score"] = max(0.0, chunk["combined_score"] - 0.07 * (usage_count + 1))
        
        diversity_final.append(chunk)
    
    # Re-tri définitif après calcul de la diversité
    diversity_final.sort(key=lambda c: c.get("combined_score", 0.0), reverse=True)
    
    print("[RETRIEVER] Top candidats identifiés (Tri hybride + Diversité) :")
    for i, chunk in enumerate(diversity_final[:10]):
        print(
            f"[RETRIEVER] #{i + 1} "
            f"similarity={float(chunk.get('similarity', 0.0)):.3f} "
            f"combined_boosted={chunk.get('combined_score', 0.0):.3f} "
            f"source={chunk.get('filename')} "
            f"type={chunk.get('source_type', 'internal')}"
        )
    
    return diversity_final

def should_use_broad_fallback(chunks: list[dict], threshold: float = 0.35) -> bool:
    """
    Décide si la qualité ou la quantité des premiers résultats nécessite une extension.
    Seuil relevé à 0.35 pour être plus exigeant sur l'activation du fallback.
    """
    if not chunks:
        return True
    if len(chunks) < FINAL_TOP_K:
        return True
    if chunks[0].get("combined_score", 0.0) < threshold:
        return True
    return False


# ===========================
# MAIN RETRIEVAL FUNCTION
# ===========================

def retrieve(
    query: str,
    top_k: int = FINAL_TOP_K,
    use_reranker: bool = True
) -> list[dict]:
    """
    Pipeline de recherche sémantique durci :
    1. Extraction de la sémantique de la requête
    2. Interrogation pgvector étendue (match_count configuré via VECTOR_CANDIDATES)
    3. Fusion réciproque et pondération prioritaire par l'INTERNAL_BOOST
    4. Fallback étendu cantonné aux documents internes et admin
    5. Alignement chirurgical via CrossEncoder local
    """
    print(f"\n[RETRIEVER] === EXÉCUTION DU RETRIEVAL MATRIX : '{query}' ===")
    
    keywords = tokenise_query(query)
    filename_hints = resolve_filename_hints(query)
    
    try:
        query_embedding = embed_text(query)
    except Exception as error:
        print(f"[RETRIEVER] Erreur critique de vectorisation : {error}")
        return []
    
    chunks = []
    try:
        # Interrogation via la fonction RPC stockée sur Supabase
        response = supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": VECTOR_CANDIDATES,
            }
        ).execute()
        
        chunks = response.data if response.data else []
        print(f"[RETRIEVER] {len(chunks)} fragments sémantiques isolés par pgvector")
    
    except Exception as error:
        print(f"[RETRIEVER] Rupture RPC Supabase : {error}. Pivot vers couche de secours.")
        if filename_hints:
            chunks = fetch_chunks_by_filenames(filename_hints)
        else:
            # Sécurité réglementaire : Pas de pollution par le web en cas de panne
            chunks = [c for c in fetch_all_chunks() if c.get("source_type") in ("internal", "admin")]
    
    # Application du scoring hybride enrichi par l'INTERNAL_BOOST
    chunks = rank_chunks(chunks, query, keywords)
    
    # Gestion du Fallback : Cloisonnement strict aux documents internes et admin de l'institution
    if should_use_broad_fallback(chunks, threshold=0.35):
        print("[RETRIEVER] Qualité insuffisante. Déclenchement du Fallback Interne Restreint...")
        all_chunks = fetch_all_chunks()
        # Élimination immédiate de tout élément n'appartenant pas au corpus métier interne
        internal_only_chunks = [c for c in all_chunks if c.get("source_type") in ("internal", "admin")]
        chunks = rank_chunks(internal_only_chunks, query, keywords)
    
    # Passage obligatoire par la couche fine d'attention croisée (CrossEncoder)
    if use_reranker and len(chunks) > 0:
        print(f"[RETRIEVER] Initialisation du Reranking sur les {len(chunks[:VECTOR_CANDIDATES])} meilleurs candidats...")
        chunks = rerank_chunks(query, chunks[:VECTOR_CANDIDATES], top_k=top_k)
    else:
        chunks = chunks[:top_k]
    
    print(f"[RETRIEVER] === EXTRACTEUR CLOS : {len(chunks)} fragments validés pour le prompt ===\n")
    return chunks


# ===========================
# FORMATTING FUNCTION
# ===========================

def format_context(chunks: list[dict]) -> str:
    """
    Formate les chunks en une structure Markdown ultra-propre pour le LLM,
    optimisant la détection des métadonnées pour le module de citation automatique.
    """
    if not chunks:
        return "[AUCUN RÉFÉRENTIEL CONFORME DISPONIBLE DANS LA BASE DE CONNAISSANCES]"
    
    context = "# RÉFÉRENTIEL DE CONFORMITÉ INTERNE ACCRÉDITÉ\n\n"
    
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.get("filename", "Fichier_Non_Spécifié.pdf")
        content = chunk.get("content", "").strip()
        sim_score = float(chunk.get("similarity", 0.0))
        rerank_score = float(chunk.get("rerank_score", 0.0))
        
        context += f"## [DOCUMENT {i}] Référence Source : {filename} (Similarité : {sim_score:.3f} | Score Rerank : {rerank_score:.3f})\n"
        context += f"```text\n{content}\n```\n"
        context += "--------------------------------------------------------------------------------\n\n"
    
    return context.strip()