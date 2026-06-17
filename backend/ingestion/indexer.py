# indexer.py
# Envoie les morceaux vectorises dans Supabase

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Charge les variables depuis le fichier .env
load_dotenv()

# Initialisation du client Supabase
# Les clés sont lues depuis .env, jamais ecrites en dur
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def index_chunks(chunks: list[dict]) -> int:
    """
    Insere une liste de morceaux vectorises
    dans la table documents de Supabase.

    Parametres :
    ------------
    chunks : list[dict]
        Liste de morceaux avec contenu,
        metadonnees et vecteur

    Retour :
    --------
    int
        Nombre de morceaux inseres avec succes
    """
    success_count = 0

    for chunk in chunks:
        try:
            # Construction de la ligne a inserer
            row = {
                "filename":    chunk["filename"],
                "content":     chunk["content"],
                "embedding":   chunk["embedding"],
                "source_type": chunk["source_type"],
                "metadata":    chunk["metadata"]
            }

            # Insertion dans Supabase
            supabase.table("documents").insert(row).execute()
            success_count += 1

        except Exception as error:
            print(f"[INDEXER] Erreur insertion : {error}")

    print(
        f"[INDEXER] {success_count}/{len(chunks)} "
        f"morceaux indexes dans Supabase"
    )

    return success_count


def delete_document(filename: str) -> bool:
    """
    Supprime tous les morceaux d un document
    depuis Supabase, par nom de fichier.
    Utilise par l admin quand il remplace un document.

    Parametres :
    ------------
    filename : str
        Nom exact du fichier a supprimer

    Retour :
    --------
    bool
        True si suppression reussie, False sinon
    """
    try:
        supabase.table("documents").delete().eq(
            "filename", filename
        ).execute()

        print(f"[INDEXER] Document supprime : {filename}")
        return True

    except Exception as error:
        print(f"[INDEXER] Erreur suppression : {error}")
        return False


def list_documents() -> list[dict]:
    """
    Retourne la liste des documents uniques
    stockes dans Supabase.
    Utilise par le back-office admin pour
    afficher les documents disponibles.

    Retour :
    --------
    list[dict]
        Liste de dicts avec filename et source_type
    """
    try:
        result = supabase.table("documents").select(
            "filename, source_type, created_at"
        ).execute()

        # Dedoublonnage par nom de fichier
        seen = set()
        unique_docs = []

        for row in result.data:
            if row["filename"] not in seen:
                seen.add(row["filename"])
                unique_docs.append(row)

        return unique_docs

    except Exception as error:
        print(f"[INDEXER] Erreur listing : {error}")
        return []