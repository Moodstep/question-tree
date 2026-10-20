"""Rejoue le parcours de référence sur un fichier HTML et garde, pour chaque étape et
chaque taille d'écran : une capture PNG + l'empreinte de ce que voit le public.

Usage :  .venv/bin/python tests/capturer.py <nom_variante> <fichier.html>
Résultat : tests/captures/<nom_variante>/<taille>/<etape>.png  et  .../etat.json
"""
import sys
import pathlib
from playwright.sync_api import sync_playwright
import _commun as C


def capturer(nom, fichier):
    fichier = pathlib.Path(fichier).resolve()
    sortie = C.CAPTURES / nom
    resume = {}
    with sync_playwright() as p:
        nav = C.lancer(p)
        for taille in C.TAILLES:
            dossier = sortie / taille
            dossier.mkdir(parents=True, exist_ok=True)
            page = C.nouvelle_page(nav, taille)
            page.goto(fichier.as_uri())
            page.wait_for_timeout(800)
            C.lancer_scene(page)
            resume[taille] = {}
            for etape in C.parcours(page):
                e = C.etat_dom(page)
                png = page.screenshot(path=str(dossier / f"{etape}.png"))
                resume[taille][etape] = {
                    "svg_sha": C.sha(e["svg"]), "panel_sha": C.sha(e["panel"]),
                    "panel": e["panel"], "screen": e["screen"],
                    "nextHidden": e["nextHidden"], "prevHidden": e["prevHidden"],
                    "png_sha": C.sha(png.hex()),
                }
            assert not page.erreurs, f"erreurs JS : {page.erreurs}"
            assert not C.requetes_suspectes(page), f"requêtes : {C.requetes_suspectes(page)}"
            page.context.close()
        nav.close()
    C.ecrire_json(sortie / "etat.json", resume)
    n = sum(len(v) for v in resume.values())
    print(f"{nom} : {n} captures ({len(C.TAILLES)} tailles) -> {sortie}")


if __name__ == "__main__":
    fichier = sys.argv[2]
    if "--noms" in sys.argv[3:]:        # avec les noms de thèmes de l'original (pour comparer à lui)
        fichier = C.variante_avec_noms(C.CAPTURES / "variante_noms.html")
    capturer(sys.argv[1], fichier)
