# embedder.py
# Transforme le texte en vecteurs numeriques

from sentence_transformers import SentenceTransformer

# Chargement du modele d embedding
# Le modele est telecharge une seule fois
# puis mis en cache sur votre machine
# Taille : environ 80MB
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """
    Transforme un texte en vecteur de 384 dimensions.
    Utilise pour vectoriser un morceau avant stockage
    ou une question avant recherche.

    Parametres :
    ------------
    text : str
        Texte a vectoriser

    Retour :
    --------
    list[float]
        Vecteur de 384 nombres decimaux
    """
    # encode() retourne un numpy array
    # tolist() le convertit en liste Python standard
    # compatible avec Supabase et JSON
    vector = EMBEDDING_MODEL.encode(text).tolist()

    return vector


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Vectorise une liste de morceaux produits
    par chunker.chunk_with_metadata().
    Ajoute le vecteur a chaque morceau.

    Parametres :
    ------------
    chunks : list[dict]
        Liste de morceaux avec metadonnees

    Retour :
    --------
    list[dict]
        Meme liste avec le champ "embedding" ajoute
    """
    print(f"[EMBEDDER] Vectorisation de {len(chunks)} morceaux...")

    for i, chunk in enumerate(chunks):
        # Vectorise le contenu textuel du morceau
        chunk["embedding"] = embed_text(chunk["content"])

        # Affiche la progression toutes les 10 iterations
        if (i + 1) % 10 == 0:
            print(f"[EMBEDDER] {i + 1}/{len(chunks)} traites")

    print(f"[EMBEDDER] Vectorisation terminee")

    return chunks