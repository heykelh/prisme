# PRISME

Plateforme d'audit de conformite AI Act pour les systemes IA de recrutement.

Les systemes IA de recrutement sont classes a haut risque par l'annexe III du reglement europeen sur l'IA. PRISME les audite contre les exigences des articles 9 a 15, sur la base de documents publics reels (audits de biais NYC Local Law 144, registres publics, system cards), avec des verdicts structures, sources et mesures.

## Principes

- **Verdicts encadres** : conforme / non conforme / non verifiable. Citation source obligatoire, sinon le verdict est non verifiable, jamais invente.
- **Corpus reel** : aucune donnee fictive. Tout le corpus est public, primaire et citable.
- **Auditabilite** : chaque run est journalise (versions du referentiel, provider LLM, verdicts, citations).
- **Multi-provider** : Gemini 2.5 Flash en primaire, Mistral en fallback.

## Stack

FastAPI (Python 3.12) | Supabase (Postgres + pgvector) | Gemini 2.5 Flash + Mistral | Next.js 15 | GitHub Actions | Render + Vercel

## Explication RAG

La version générale (celle pour un recruteur non technique)
Un LLM a deux limites fondamentales : il ne connaît pas tes documents, et quand il ne sait pas, il a tendance à inventer. Le RAG (Retrieval-Augmented Generation) corrige les deux : au lieu de demander au modèle de répondre de mémoire, on va d'abord chercher les passages pertinents dans une base documentaire, puis on les donne au modèle en lui disant "réponds uniquement à partir de ça".
Analogie : un juriste à qui tu poses une question ne récite pas le code de mémoire. Il va chercher les bons articles, les pose sur la table, et raisonne dessus. Le RAG, c'est ça : la recherche documentaire d'abord, la génération ensuite. Dans PRISME, la base documentaire c'est l'AI Act, et la question c'est "ce système IA respecte-t-il ce critère".
La mécanique, étape par étape
Le RAG a deux phases : l'indexation (une fois, en amont, c'est ce qui tourne chez toi en ce moment) et la requête (à chaque question).
Phase 1 : l'indexation
1. Le chunking, ce qui répond à ta question. On ne peut pas chercher dans un document de 5000 lignes d'un bloc : c'est trop gros pour être comparé finement à une question. Donc on le découpe en morceaux, les chunks, d'environ 1500 caractères chez toi. Chaque chunk devient une unité de recherche indépendante : quand tu chercheras "qualité des données", tu ne récupéreras pas tout l'AI Act, mais les 3 ou 4 chunks qui en parlent. Le découpage est un arbitrage : trop petit, un chunk perd son contexte (une phrase orpheline ne veut rien dire) ; trop gros, il dilue l'information (le passage pertinent noyé dans du hors-sujet, et la similarité baisse). D'où aussi l'overlap de 200 caractères dans ton code : chaque chunk reprend la fin du précédent, pour qu'une idée à cheval sur deux chunks ne soit jamais coupée en deux et perdue.
2. L'embedding. C'est le cœur magique du système. Un modèle d'embedding (chez toi gemini-embedding-001) transforme chaque chunk en un vecteur : une liste de 768 nombres qui encode le sens du texte, pas ses mots. La propriété clé : deux textes qui parlent de la même chose ont des vecteurs proches, même s'ils n'ont aucun mot en commun. "Qualité des jeux de données d'entraînement" et "les datasets doivent être représentatifs et exempts d'erreurs" seront voisins dans cet espace à 768 dimensions. C'est ce qui rend la recherche sémantique possible, là où une recherche par mots-clés classique échouerait.
3. Le stockage vectoriel. Les vecteurs sont rangés dans une base qui sait chercher "les plus proches voisins" : chez toi, Postgres avec l'extension pgvector, dans Supabase. Ton schéma a un index HNSW, une structure qui permet de trouver les vecteurs les plus proches parmi des milliers sans tous les comparer un par un, un peu comme un index de livre évite de lire toutes les pages.
Voilà ce qui tourne en ce moment sur ta machine : découpe du texte, un appel d'embedding par chunk, insertion du couple (texte, vecteur) dans Supabase. C'est pour ça que c'est long, et c'est pour ça qu'on ne le fait qu'une fois.
Phase 2 : la requête (le "retrieve" puis le "generate")
4. L'embedding de la question. Quand une question arrive ("ce document démontre-t-il une gestion des risques documentée ?"), elle subit le même traitement : transformée en vecteur de 768 dimensions par le même modèle. Détail pro dans ton code : le task_type diffère (RETRIEVAL_QUERY pour la question, RETRIEVAL_DOCUMENT pour les chunks), le modèle optimise légèrement différemment les deux côtés, ça améliore l'appariement.
5. Le retrieval. La base compare le vecteur de la question à tous les vecteurs stockés et retourne les k plus proches (chez toi k=8 par défaut), classés par similarité cosinus : l'angle entre les vecteurs, 1 = même direction = même sens, 0 = sans rapport. C'est la fonction match_chunks de ton schéma SQL. Résultat : les 8 passages de l'AI Act les plus pertinents pour la question, avec leur score.
6. L'augmentation. On construit le prompt final en y injectant ces passages : "Voici des extraits du règlement : [chunks]. Voici le critère à vérifier et le document à auditer. Réponds uniquement sur cette base." C'est le A de RAG : on augmente le contexte du LLM avec de la connaissance fraîche et sourcée.
7. La génération. Le LLM (Gemini, ou Mistral en fallback via ton router) produit la réponse. Dans PRISME ce n'est pas du texte libre : c'est un verdict structuré (conforme / non conforme / non vérifiable) avec citation obligatoire, et on vérifiera de façon déterministe que la citation existe verbatim dans le document. Si le modèle ne trouve pas de preuve dans les passages fournis, il doit dire "non vérifiable" plutôt qu'inventer. C'est la parade anti-hallucination, et c'est ce qui rend un RAG défendable en environnement régulé.
Le résumé en une phrase :
"Un RAG, c'est une recherche sémantique branchée sur un LLM : on découpe les documents en chunks, on les encode en vecteurs qui capturent le sens, on stocke dans une base vectorielle ; à chaque question, on encode la question pareil, on récupère les passages les plus proches par similarité cosinus, et on force le LLM à répondre uniquement à partir de ces passages, avec citations. Dans mon cas, le corpus c'est l'AI Act dans pgvector, l'embedding c'est gemini-embedding-001 en 768 dimensions, et la sortie c'est un verdict d'audit structuré dont chaque citation est vérifiée par programme."
Et les deux questions pièges qu'on te posera derrière, avec les réponses courtes : "pourquoi 768 dimensions ?" (arbitrage qualité/stockage, c'est une des dimensions recommandées du modèle, et ça fixe la taille de la colonne vector en base) ; "que se passe-t-il si le retrieval rate le bon passage ?" (le LLM ne peut pas répondre mieux que ce qu'on lui donne, d'où la métrique recall@k dans mon harness d'éval : je mesure la qualité du retrieval séparément de la qualité du verdict). Cette dernière phrase, retiens-la, elle fait la différence entre quelqu'un qui a suivi un tuto et quelqu'un qui comprend son système.

## Demarrage local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # puis remplir les cles
uvicorn app.main:app --reload
```

API sur http://127.0.0.1:8000, documentation interactive sur http://127.0.0.1:8000/docs

## Tests

```powershell
pytest -v
ruff check .
```

## Statut

Phase P0 : fondations. Referentiel d'exigences et pipeline RAG en cours (P1).

## Methodologie et limites

Les analyses portent exclusivement sur des documents publics. L'outil produit des evaluations indicatives, pas des certifications. Les verdicts LLM sont encadres par des citations obligatoires verifiees de facon deterministe et des mesures de stabilite publiees dans ce README a partir de la phase P2.