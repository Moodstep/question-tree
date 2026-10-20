"""Planche « application | référence » d'un arbre pour une étape : même état, mêmes couches cachées, côte à côte, avec le nombre de pixels différents.

Usage :  .venv/bin/python tests/planche_etape.py <olivier|chene> <étape> [état ...]      (états : T1 T2 T3 T4 « premier vote » …)
Sortie :  tests/captures/planches/<arbre>_etape<N>.png
"""
import sys, base64
from playwright.sync_api import sync_playwright
import _commun as C
import comparer_reference as R


def planche(arbre, n, noms, taille="1280x720"):
    cible = R.CIBLES[arbre]; VIS = cible["visible"] or R.VISIBLE
    lignes = []
    with sync_playwright() as p:
        nav = C.lancer(p)
        blank = C.nouvelle_page(nav, "800x600"); blank.goto("about:blank")
        ref, app = R.ouvrir(nav, taille, arbre)
        for p_ in (ref, app): p_.evaluate(R.JS_MASQUER, sorted(VIS[n]))
        for nom in noms:
            E = cible["etats"][nom]
            for p_, ids in ((ref, lambda q: q), (app, cible["ids"])):
                p_.evaluate("(e) => applyState(e)", {**E, "path": [ids(q) for q in E["path"]]}); p_.wait_for_timeout(1400)
            a, b = app.locator("#svg").screenshot(), ref.locator("#svg").screenshot()
            d = R.comparer_png(blank, b, a)
            lignes.append((nom, a, b, d.get("diff")))
        nav.close()
    img = lambda x: "data:image/png;base64," + base64.b64encode(x).decode()
    html = "<body style='margin:12px;background:#fff;font:14px system-ui;color:#2b2620'>" + "".join(
        f"<div style='margin-bottom:16px'><b>{arbre} · étape {n} · {nom}</b> : {'identique à la référence (0 pixel de différence)' if diff == 0 else str(diff) + ' pixels différents'}"
        f"<div style='display:flex;gap:12px;margin-top:4px'><div><div style='color:#5d5249'>Application</div><img style='border:1px solid #ddd;height:520px' src='{img(a)}'></div>"
        f"<div><div style='color:#5d5249'>Référence</div><img style='border:1px solid #ddd;height:520px' src='{img(b)}'></div></div></div>" for nom, a, b, diff in lignes) + "</body>"
    return html


if __name__ == "__main__":
    arbre, n = sys.argv[1], int(sys.argv[2]); noms = sys.argv[3:] or ["T1"]
    html = planche(arbre, n, noms)
    sortie = C.CAPTURES / "planches"; sortie.mkdir(exist_ok=True)
    with sync_playwright() as p:
        nav = C.lancer(p); page = C.nouvelle_page(nav, "1480x900"); page.set_content(html); page.wait_for_timeout(400)
        page.screenshot(path=str(sortie / f"{arbre}_etape{n}.png"), full_page=True); nav.close()
    print(sortie / f"{arbre}_etape{n}.png")
