"""Repare le mojibake (double encodage UTF-8/cp1252) d'un fichier texte.

Usage : python -m scripts.fix_encoding --file corpus\\ai_act_fr.txt
Le fichier est repare en place, une sauvegarde .bak est creee.
"""

import argparse
from pathlib import Path

import ftfy


def main() -> None:
    parser = argparse.ArgumentParser(description="Reparation d'encodage")
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    path = Path(args.file)
    original = path.read_text(encoding="utf-8")
    repaired = ftfy.fix_text(original)

    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(original, encoding="utf-8")
    path.write_text(repaired, encoding="utf-8")

    print(f"Fichier repare : {path}")
    print(f"Sauvegarde : {backup}")
    print(f"Apercu : {repaired[:200]}")


if __name__ == "__main__":
    main()
