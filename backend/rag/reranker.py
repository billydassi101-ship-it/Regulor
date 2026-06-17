# backend/rag/reranker.py
# Reclasse les chunks récupérés par Supabase avec un CrossEncoder local.
# Objectif : maximiser la pertinence finale et la sécurité sémantique avant l'inférence LLM.

import math
from sentence_transformers import CrossEncoder

# Modèle open-source léger, performant et souverain (exécuté localement en arrière-plan)
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker = None


def get_reranker() -> CrossEncoder:
    """
    Charge le reranker une seule fois en mémoire de type Singleton.
    Évite de recharger le modèle asymétrique à chaque nouvelle itération de question.
    """
    global _reranker

    if _reranker is None:
        print(f"[RERANKER] Initialisation du modèle d'attention croisée : {RERANKER_MODEL_NAME}")
        _reranker = CrossEncoder(RERANKER_MODEL_NAME)

    return _reranker


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 4
) -> list[dict]:
    """
    Ré-ordonne les fragments documentaires (chunks) selon leur pertinence sémantique fine.
    Calcule une attention croisée mot à mot entre la requête utilisateur et le texte cible.
    Applique une normalisation Sigmoïde pour éliminer les scores négatifs dans l'interface.

    Paramètres :
    ------------
    query : str
        Question ou instruction formulée par l'utilisateur métier.
    chunks : list[dict]
        Liste des candidats extraits par la recherche hybride (Supabase pgvector + BM25).
    top_k : int
        Nombre final restreint de chunks à conserver pour la fenêtre de contexte (par défaut : 4).

    Retour :
    --------
    list[dict]
        Top K fragments documentaires triés par score d'attention croisée décroissant.
    """
    if not chunks:
        return []

    reranker = get_reranker()

    # Préparation des paires pour l'analyse bidirectionnelle du Transformer CrossEncoder
    pairs = [
        [query, chunk.get("content", "")]
        for chunk in chunks
    ]

    # Inférence locale : Calcul des logits de pertinence sémantique fine (scores bruts de -10 à +10)
    scores = reranker.predict(pairs)

    reranked = []
    for chunk, score in zip(chunks, scores):
        new_chunk = dict(chunk)
        
        # =========================================================================
        # TRAITEMENT MATHÉMATIQUE : NORMALISATION PAR SIGMOÏDE
        # Les CrossEncoders retournent des logits non bornés (positifs ou négatifs).
        # On applique la fonction sigmoïde pour écraser le score entre 0.0 et 1.0.
        # Gère l'écrêtage pour éviter les erreurs d'overflow mathématique.
        # =========================================================================
        try:
            logit = float(score)
            # Écrêtage de sécurité pour éviter l'erreur de dépassement de capacité (OverflowError)
            logit = max(-20.0, min(20.0, logit))
            sigmoide_score = 1.0 / (1.0 + math.exp(-logit))
        except Exception:
            sigmoide_score = 0.0
            
        new_chunk["rerank_score"] = sigmoide_score
        reranked.append(new_chunk)

    # Ré-ordonnancement de l'arborescence basé sur la note normalisée par la Sigmoïde
    reranked.sort(
        key=lambda c: c.get("rerank_score", 0.0),
        reverse=True
    )

    print("[RERANKER] Alignement chirurgical de la fenêtre de contexte clos (Normalisé) :")
    for i, chunk in enumerate(reranked[:top_k]):
        similarity_score = chunk.get("similarity")
        sim_str = f"{float(similarity_score):.3f}" if similarity_score is not None else "N/A"
        
        print(
            f"   -> Fragment [{i + 1}] "
            f"Confiance Rerank={chunk.get('rerank_score'):.3f} | "
            f"Similarité Initiale={sim_str} | "
            f"Source={chunk.get('filename', 'Source_Non_Spécifiée.pdf')} | "
            f"Type={chunk.get('source_type', 'internal')}"
        )

    return reranked[:top_k]