"""Decoupage de texte en chunks pour l'indexation vectorielle.

Strategie : decoupage par paragraphes avec regroupement jusqu'a une taille cible,
et chevauchement entre chunks pour ne pas perdre le contexte aux frontieres.
Adapte aux textes reglementaires, structures en articles et alineas.
"""

TARGET_SIZE = 1500
OVERLAP = 200


def split_paragraphs(text: str) -> list[str]:
    """Coupe sur les lignes vides, en conservant les paragraphes non vides."""
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    return [p for p in paragraphs if p]


def chunk_text(text: str, target_size: int = TARGET_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Regroupe les paragraphes en chunks d'environ target_size caracteres.

    Un paragraphe plus long que target_size est decoupe brutalement par tranches.
    Le chevauchement reprend la fin du chunk precedent au debut du suivant.
    """
    paragraphs = split_paragraphs(text)
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > target_size:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(paragraph), target_size - overlap):
                chunks.append(paragraph[start : start + target_size])
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > target_size and current:
            chunks.append(current)
            tail = current[-overlap:] if overlap and len(current) > overlap else ""
            current = f"{tail}\n\n{paragraph}" if tail else paragraph
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks
