# chunker.py
# Découpe le texte brut en morceaux exploitables


def get_chunk_config(word_count: int) -> tuple[int, int]:
    """
    Détermine automatiquement la taille des chunks
    selon la taille du document.
    """

    if word_count < 3000:
        return 300, 50

    elif word_count < 10000:
        return 400, 75

    else:
        return 500, 100


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None
) -> list[str]:
    """
    Découpe un texte en morceaux avec chevauchement.

    Paramètres :
    ------------
    text : str
        Texte brut extrait par loader.py

    chunk_size : int | None
        Taille d'un chunk en nombre de mots.
        Si None, calcul automatique.

    overlap : int | None
        Nombre de mots partagés entre deux chunks.
        Si None, calcul automatique.

    Retour :
    --------
    list[str]
        Liste de morceaux prêts à être vectorisés.
    """

    # Nettoyage du texte
    text = " ".join(text.split())

    words = text.split()

    word_count = len(words)

    if chunk_size is None or overlap is None:
        chunk_size, overlap = get_chunk_config(word_count)

    print(
        f"[CHUNKER] Document : {word_count} mots | "
        f"chunk_size={chunk_size} | "
        f"overlap={overlap}"
    )

    chunks = []
    start = 0

    while start < len(words):

        end = start + chunk_size

        chunk_words = words[start:end]

        chunk = " ".join(chunk_words)

        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())

        start += max(1, chunk_size - overlap)

    print(f"[CHUNKER] {len(chunks)} morceaux créés")

    return chunks


def chunk_with_metadata(
    text: str,
    filename: str,
    source_type: str,
    chunk_size: int | None = None,
    overlap: int | None = None
) -> list[dict]:
    """
    Version enrichie du chunker.
    Chaque morceau est accompagné de ses métadonnées.

    Paramètres :
    ------------
    text : str
        Texte brut extrait du document

    filename : str
        Nom du fichier source

    source_type : str
        internal / official / web / temp

    Retour :
    --------
    list[dict]
        Morceaux enrichis avec métadonnées
    """

    raw_chunks = chunk_text(
        text=text,
        chunk_size=chunk_size,
        overlap=overlap
    )

    total_chunks = len(raw_chunks)

    result = []

    for i, chunk in enumerate(raw_chunks):

        result.append(
            {
                "content": chunk,
                "filename": filename,
                "source_type": source_type,
                "metadata": {
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "filename": filename,
                    "chunk_length_words": len(chunk.split())
                }
            }
        )

    return result