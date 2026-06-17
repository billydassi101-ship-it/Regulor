import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ingestion.loader import load_file
from ingestion.chunker import chunk_with_metadata
from ingestion.embedder import embed_chunks
from ingestion.indexer import index_chunks


DATA_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data"
)


def ingest_all_pdfs():

    total_files = 0
    total_chunks = 0

    for root, _, files in os.walk(DATA_FOLDER):

        for file in files:

            if not file.lower().endswith(".pdf"):
                continue

            filepath = os.path.join(root, file)

            print("\n" + "=" * 60)
            print(f"[INGEST] Traitement : {file}")

            try:

                with open(filepath, "rb") as f:
                    file_bytes = f.read()

                # Extraction texte
                text = load_file(file_bytes, file)

                if not text.strip():
                    print("[INGEST] Aucun texte extrait")
                    continue

                # Chunking
                chunks = chunk_with_metadata(
                text=text,
                filename=file,
                source_type="official"
            )

                # Embeddings
                chunks = embed_chunks(chunks)

                # Indexation
                inserted = index_chunks(chunks)

                total_files += 1
                total_chunks += inserted

                print(
                    f"[INGEST] OK : {inserted} chunks indexes"
                )

            except Exception as e:

                print(f"[INGEST] Erreur : {e}")

    print("\n" + "=" * 60)
    print("[INGEST] TERMINE")
    print(f"Fichiers indexes : {total_files}")
    print(f"Chunks indexes : {total_chunks}")


if __name__ == "__main__":
    ingest_all_pdfs()