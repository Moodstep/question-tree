"""Compare deux jeux de captures : les dessins (SVG), les textes affichés, l'état des
boutons ET les pixels doivent être identiques, étape par étape, taille par taille.

Usage :  .venv/bin/python tests/comparer.py <variante_A> <variante_B>
Code de sortie 0 = strictement identique ; 1 = au moins une différence (listée).
"""
import sys
import _commun as C


def comparer(a, b, champs=("svg_sha", "panel_sha", "screen", "nextHidden", "prevHidden", "png_sha")):
    A = C.lire_json(C.CAPTURES / a / "etat.json")
    B = C.lire_json(C.CAPTURES / b / "etat.json")
    echecs, n = [], 0
    for taille in A:
        if taille not in B:
            echecs.append(f"taille {taille} absente de {b}")
            continue
        for etape, ea in A[taille].items():
            eb = B[taille].get(etape)
            if eb is None:
                echecs.append(f"{taille}/{etape} absente de {b}")
                continue
            for c in champs:
                n += 1
                if ea[c] != eb[c]:
                    echecs.append(f"{taille}/{etape} : « {c} » diffère")
    return n, echecs


if __name__ == "__main__":
    n, echecs = comparer(sys.argv[1], sys.argv[2])
    ok = C.bilan(f"{sys.argv[1]} == {sys.argv[2]} ({n} comparaisons)", echecs)
    sys.exit(0 if ok else 1)
