from app.rag.chunking import chunk_text, split_paragraphs


def test_split_paragraphs_ignores_empty():
    text = "Premier paragraphe.\n\n\n\nDeuxieme paragraphe.\n\n"
    assert split_paragraphs(text) == ["Premier paragraphe.", "Deuxieme paragraphe."]


def test_short_text_single_chunk():
    chunks = chunk_text("Un texte court.")
    assert chunks == ["Un texte court."]


def test_paragraphs_grouped_up_to_target():
    paragraphs = [f"Paragraphe numero {i}. " * 5 for i in range(20)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, target_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 600 for c in chunks)


def test_oversized_paragraph_is_sliced():
    text = "x" * 5000
    chunks = chunk_text(text, target_size=1500, overlap=200)
    assert len(chunks) == 4
    assert all(len(c) <= 1500 for c in chunks)


def test_full_content_preserved():
    paragraphs = [f"Contenu unique {i}" for i in range(30)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, target_size=300, overlap=0)
    joined = "\n\n".join(chunks)
    for p in paragraphs:
        assert p in joined
