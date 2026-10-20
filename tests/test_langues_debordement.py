"""Langues : aucune traduction ne déborde (cartes, boutons, étiquettes, fenêtres), aux quatre tailles d'écran testées.

Pour chacune des 7 langues et chacune des 4 tailles (1920x1080, 1280x720, 1024x768 et 375x812, un téléphone), on parcourt les 11 écrans de l'outil (le mode d'emploi compris)
(tests/test_langues.py : ecran_par_ecran) et on mesure, élément visible par élément visible :
  - la page ne défile jamais en largeur ;
  - aucun élément ne sort de l'écran à gauche ou à droite ;
  - aucun texte n'est plus large que sa boîte (bouton, étiquette, carte, cellule) ;
  - une fenêtre de dialogue tient dans l'écran.
Un défaut déjà présent en français n'est pas imputé à une traduction : on compare chaque langue au français.
Le contrôle sait échouer : un test témoin élargit volontairement un bouton et doit être vu.
Il prend aussi les captures des écrans clés dans chaque langue (1280x720) : tests/captures/langues/<langue>_<écran>.png

Usage :  .venv/bin/python tests/test_langues_debordement.py
"""
import os, sys, pathlib
from playwright.sync_api import sync_playwright
import _commun as C
from test_langues import ouvrir, ecran_par_ecran, LOCALES, DOSSIER

FICHIER = pathlib.Path(os.environ.get("ARBRE_FICHIER", str(C.RACINE / "index.html"))).resolve()      # un fichier abîmé exprès peut être passé ici (mutants)

JS_DEBORD = """() => {
  const vw = innerWidth, vh = innerHeight, pb = [];
  const racine = document.scrollingElement;
  if (racine.scrollWidth > vw + 1) pb.push('PAGE|défile en largeur (' + racine.scrollWidth + ' > ' + vw + ')');
  const chemin = e => { const a = []; while (e && e !== document.body) { a.unshift(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].join('.') : '')); e = e.parentElement; } return a.slice(-3).join(' > '); };
  for (const el of document.body.querySelectorAll('*')) {
    if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.closest('svg')) continue;
    if (!el.checkVisibility({checkVisibilityCSS: true})) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const txt = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (r.left < -1 || r.right > vw + 1) pb.push(chemin(el) + '|sort de l\\'écran à gauche ou à droite');
    if (el.clientWidth > 0 && (txt || ['BUTTON', 'SELECT', 'LABEL'].includes(el.tagName)) && el.scrollWidth > el.clientWidth + 1)
      pb.push(chemin(el) + '|texte plus large que sa boîte (' + el.scrollWidth + ' > ' + el.clientWidth + ')');
    if (el.tagName === 'DIALOG' && el.open && (r.top < -1 || r.bottom > vh + 1)) pb.push(chemin(el) + '|fenêtre plus haute que l\\'écran');
  }
  return pb;
}"""


def balayer(nav, langue, taille, captures=False):
    """{écran: [problèmes]} pour une langue et une taille."""
    page = ouvrir(nav, FICHIER, langue, taille)
    res = {}
    for nom in ecran_par_ecran(page):
        res[nom] = sorted(set(page.evaluate(JS_DEBORD)))
        if captures and nom in ("préparation", "éditeur olivier", "fenêtre : textes manquants", "scène : vote", "fenêtre : retour à la préparation", "mode d'emploi"):
            page.screenshot(path=str(DOSSIER / f"{langue}_{nom.replace("'", '').replace(' ', '_').replace(':', '').replace('à', 'a').replace('é', 'e').replace('è', 'e')}.png"))
    erreurs = (page.erreurs, C.requetes_suspectes(page)); page.context.close()
    return res, erreurs


def tester():
    echecs = []
    def att(nom, attendu, obtenu):
        if attendu != obtenu: echecs.append(f"{nom} : attendu {str(attendu)[:300]!r}, obtenu {str(obtenu)[:300]!r}")
    with sync_playwright() as p:
        nav = C.lancer(p)
        # le contrôle sait échouer : un bouton élargi de force est vu, un élément poussé hors de l'écran aussi
        page = ouvrir(nav, FICHIER, "fr", "1024x768")
        avant = page.evaluate(JS_DEBORD)
        page.evaluate("""() => { const b = document.getElementById('btn-lancer'); b.style.whiteSpace = 'nowrap'; b.style.width = '60px'; b.style.overflow = 'visible';
                               b.insertAdjacentText('beforeend', ' — un texte beaucoup trop long pour un bouton de soixante pixels'); }""")
        apres = page.evaluate(JS_DEBORD)
        att("témoin : un bouton trop étroit est vu", True, any("btn-lancer" in x and "plus large" in x for x in apres) and not any("btn-lancer" in x for x in avant))
        page.evaluate("document.getElementById('credit').style.marginLeft = '3000px'")
        att("témoin : un élément hors de l'écran est vu", True, any("credit" in x and "sort de l'écran" in x for x in page.evaluate(JS_DEBORD)))
        page.context.close()

        for taille in list(C.TAILLES) + ["375x812"]:
            ref, _ = balayer(nav, "fr", taille, captures=(taille == "1280x720"))
            att(f"{taille} : le français parcourt 11 écrans", 11, len(ref))
            absolus = sorted({x for v in ref.values() for x in v if x.startswith("PAGE|")})
            att(f"{taille} : le français lui-même ne défile pas en largeur", [], absolus)
            for l in LOCALES:
                if l == "fr": continue
                res, erreurs = balayer(nav, l, taille, captures=(taille == "1280x720"))
                nouveaux = {nom: sorted(set(v) - set(ref.get(nom, []))) for nom, v in res.items()}
                att(f"{taille} {l} : 11 écrans parcourus", 11, len(res))
                att(f"{taille} {l} : aucun débordement nouveau par rapport au français", {}, {n: v for n, v in nouveaux.items() if v})
                att(f"{taille} {l} : aucune erreur JS / requête", ([], []), erreurs)
    return echecs


if __name__ == "__main__":
    ok = C.bilan("langues : aucun débordement (7 langues x 4 tailles x 11 écrans) + captures des écrans clés", tester())
    sys.exit(0 if ok else 1)
