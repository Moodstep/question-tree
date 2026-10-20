"""Mécanique et gestes de la scène, rejoués sur un fichier HTML (l'original comme le nouveau).

 A. Les 256 parcours possibles (8 votes, 2 choix chacun) : chaque parcours finit à la fin,
    sans jamais repasser par une question déjà posée ; chaque vote propose une jaune ET une bleue.
 B. Les gestes : flèches, Espace, Entrée, PageDown, J / B / 1 / 2, Retour arrière, ←, Maj+R, F,
    les trois boutons, le clic sur une carte, le curseur qui disparaît.

Usage :  .venv/bin/python tests/test_scene.py <fichier.html>
Affiche l'empreinte des 256 parcours : elle doit être identique entre original et nouvelle version.
"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright
import _commun as C

EMPREINTE_ORIGINALE = "db08e6a83c6a6330"

PARCOURS_JS = """() => {
  const tous = [], pb = [];
  for (let m = 0; m < 256; m++) {
    resetAll();
    for (let i = 0; i < 4; i++) next();
    for (let v = 0; v < 8; v++) {
      const o = options();
      if (o.length !== 2) { pb.push(`m${m} vote${v+1} : ${o.length} option(s)`); break; }
      const couleurs = o.map(id => byId[id].color).sort().join('');
      if (couleurs !== 'bj') pb.push(`m${m} vote${v+1} : couleurs ${couleurs}`);
      choose((m >> v) & 1);
      if (mode !== 'answer') { pb.push(`m${m} vote${v+1} : pas en réponse`); break; }
      next();
    }
    if (mode !== 'end') pb.push(`m${m} : pas à la fin (${mode})`);
    if (path.length !== 8) pb.push(`m${m} : ${path.length} questions`);
    if (new Set(path).size !== path.length) pb.push(`m${m} : répétition ${path}`);
    tous.push(path.join('>'));
  }
  resetAll();
  return {tous, pb, distincts: new Set(tous).size};
}"""


def tester(fichier):
    echecs = []
    with sync_playwright() as p:
        nav = C.lancer(p)
        page = C.nouvelle_page(nav, "1280x720")
        page.goto(pathlib.Path(fichier).resolve().as_uri())
        page.wait_for_timeout(500)
        C.lancer_scene(page)

        # --- A. 256 parcours ---
        r = page.evaluate(PARCOURS_JS)
        echecs += r["pb"][:10]
        if r["distincts"] != 256:
            echecs.append(f"{r['distincts']} parcours distincts au lieu de 256")
        empreinte = C.sha("\n".join(r["tous"]))[:16]

        # --- B. gestes ---
        def etat():
            return page.evaluate("() => ({mode, ti, path: path.slice()})")

        def att(nom, attendu, obtenu):
            if attendu != obtenu:
                echecs.append(f"{nom} : attendu {attendu}, obtenu {obtenu}")

        page.evaluate("resetAll()")
        for touche in ["ArrowRight", "Space", "Enter", "PageDown"]:
            avant = etat()["ti"] if etat()["mode"] == "trunk" else None
            page.keyboard.press(touche if touche != "Space" else " ")
        att("4 touches d'avance -> choix", "choose", etat()["mode"])
        page.keyboard.press("ArrowRight")
        att("flèche droite en mode choix : sans effet", "choose", etat()["mode"])
        page.keyboard.press("ArrowUp")
        e = etat(); att("↑ = 1re option", ["I1"], e["path"]); att("mode réponse", "answer", e["mode"])
        page.keyboard.press("ArrowLeft")
        att("← = retour", ([], "choose"), (etat()["path"], etat()["mode"]))
        page.keyboard.press("j")
        att("J = la jaune (A1)", ["A1"], etat()["path"])
        page.keyboard.press("Backspace")
        page.keyboard.press("b")
        att("B = la bleue (I1)", ["I1"], etat()["path"])
        page.keyboard.press("Backspace")
        page.keyboard.press("2")
        att("2 = la bleue", ["I1"], etat()["path"])
        page.keyboard.press("Backspace")
        page.keyboard.press("1")
        att("1 = la jaune", ["A1"], etat()["path"])
        page.keyboard.press("Shift+R")
        att("Maj+R = tout à zéro", ("trunk", 0, []), (etat()["mode"], etat()["ti"], etat()["path"]))
        page.keyboard.press("r")
        att("r minuscule seul : ne remet PAS à zéro", "trunk", etat()["mode"])
        fs = "!!document.fullscreenElement"
        page.keyboard.press("f"); page.wait_for_timeout(400)
        att("F : plein écran", True, page.evaluate(fs))
        page.keyboard.press("F"); page.wait_for_timeout(400)
        att("F encore : on en sort", False, page.evaluate(fs))
        page.dblclick("#svg"); page.wait_for_timeout(400)
        att("double-clic sur l'arbre : plein écran", True, page.evaluate(fs))
        page.dblclick("#svg"); page.wait_for_timeout(400)
        att("double-clic encore : on en sort", False, page.evaluate(fs))
        # boutons
        for _ in range(4):
            page.click("#next")
        att("bouton → x4 -> choix", "choose", etat()["mode"])
        att("bouton → masqué en mode choix", True, page.evaluate("document.getElementById('next').hidden"))
        page.click("#panel button.card >> nth=1")
        att("clic sur la 2e carte (I1 ou A1)", 1, len(etat()["path"]))
        page.click("#prev")
        att("bouton ←", 0, len(etat()["path"]))
        page.click("#rst")
        att("bouton reset", ("trunk", 0), (etat()["mode"], etat()["ti"]))
        att("bouton ← masqué au tout début", True, page.evaluate("document.getElementById('prev').hidden"))
        # curseur qui disparaît
        page.mouse.move(100, 100); page.mouse.move(120, 120)
        att("curseur visible juste après un mouvement", "", page.evaluate("document.body.style.cursor"))
        page.wait_for_timeout(2900)
        att("curseur caché après 2,5 s", "none", page.evaluate("document.body.style.cursor"))
        # bouton de sortie : le rond en haut à gauche, jumeau de celui de droite, ramène au choix de l'arbre (avec la confirmation de la touche E)
        g = page.evaluate("""() => { const s = document.getElementById('sortie').getBoundingClientRect(), r = document.getElementById('rst').getBoundingClientRect();
            return [Math.round(s.left), Math.round(s.top), Math.round(innerWidth - r.right), Math.round(r.top), Math.round(s.width), Math.round(r.width), getComputedStyle(document.getElementById('sortie')).borderRadius]; }""")
        att("bouton de sortie : jumeau du rond de droite (même distance du bord et du haut, même taille 22, rond)", (True, True, 22, "50%"), (g[0] == g[2], g[1] == g[3], 22 if g[4] == g[5] == 22 else False, g[6]))
        att("bouton de sortie : nom accessible", "Revenir au choix de l'arbre", page.get_attribute("#sortie", "aria-label"))
        page.evaluate("applyState({mode:'choose', ti:3, path:[]})")         # en plein vote : c'est là qu'Espace n'est pas intercepté par la scène
        page.click("#sortie"); page.wait_for_timeout(150)
        att("bouton de sortie : ouvre la confirmation « Revenir à la préparation ? »", ("Revenir à la préparation ?", "scene"), (page.inner_text("#dlg-confirmation h2"), page.evaluate("ecran")))
        att("bouton de sortie : le focus ne reste pas sur lui (Espace ne le rappuie pas)", False, page.evaluate("document.activeElement.id === 'sortie'"))
        page.click("#dlg-confirmation button[value=non]"); page.wait_for_timeout(150)
        att("« Non, continuer » : on reste sur la scène, au même endroit (le vote en cours)", ("scene", "choose"), (page.evaluate("ecran"), etat()["mode"]))
        page.keyboard.press("Space"); page.wait_for_timeout(150)
        att("après « Non » : Espace ne rouvre pas la confirmation (le bouton n'a pas gardé le focus)", (False, "choose"), (page.locator("#dlg-confirmation").is_visible(), etat()["mode"]))
        page.click("#sortie"); page.wait_for_timeout(150); page.click("#dlg-confirmation button[value=oui]"); page.wait_for_timeout(200)
        att("« Oui, revenir » : retour à l'écran de préparation, choix de l'arbre visible", ("prepa", 2, False), (page.evaluate("ecran"), page.locator("#choix-arbre .vignette:visible").count(), page.locator("#sortie").is_visible()))
        if page.erreurs: echecs.append(f"erreurs JS : {page.erreurs}")
        if C.requetes_suspectes(page): echecs.append(f"requêtes : {C.requetes_suspectes(page)}")
        nav.close()
    return empreinte, echecs


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else str(C.RACINE / "index.html")
    emp, echecs = tester(f)
    # La mécanique n'a pas changé depuis l'original du 3 novembre : mêmes 256 parcours (empreinte relevée sur ce fichier d'origine, sha256 f3d46e5b…).
    if emp != EMPREINTE_ORIGINALE: echecs.append(f"les 256 parcours diffèrent de ceux de l'original du 3 novembre : {emp} au lieu de {EMPREINTE_ORIGINALE}")
    ok = C.bilan(f"scène {f}  (256 parcours, empreinte {emp})", echecs)
    sys.exit(0 if ok else 1)
