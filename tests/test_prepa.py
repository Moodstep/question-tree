"""Écran de préparation : contenu, liens, lancement, textes manquants, retour (touche E / Échap x2).

Usage :  .venv/bin/python tests/test_prepa.py <fichier.html>
"""
import sys, pathlib
from playwright.sync_api import sync_playwright
import _commun as C

NOMS = "(() => { ARBRE.themes[0].nom='Alpha'; ARBRE.themes[1].nom='Bêta'; ARBRE.themes[2].nom='Gamma'; })()"


def tester(fichier):
    echecs = []
    def att(nom, attendu, obtenu):
        if attendu != obtenu:
            echecs.append(f"{nom} : attendu {attendu!r}, obtenu {obtenu!r}")
    with sync_playwright() as p:
        nav = C.lancer(p)
        ctx_page = C.nouvelle_page(nav, "1280x720")
        page = ctx_page
        page.goto(pathlib.Path(fichier).resolve().as_uri())
        page.wait_for_timeout(500)
        page.evaluate(NOMS)
        vis = lambda sel: page.locator(sel).is_visible()
        etat = lambda: page.evaluate("({mode, ti, path: path.slice(), ecran})")

        # ---- contenu de l'écran de préparation ----
        att("préparation visible", True, vis("#prepa"))
        att("scène invisible à l'ouverture", False, vis("#screen"))
        att("boutons de la scène invisibles", [False] * 4, [vis("#prev"), vis("#rst"), vis("#sortie"), vis("#next")])
        att("bouton 1", "Entrer mes questions et thèmes", page.inner_text("#btn-modifier"))
        att("bouton 2", "Lancer l'arbre", page.inner_text("#btn-lancer"))
        lien = page.locator("#nouveautes a")
        att("lien nouveautés : texte", "Pour être prévenu des améliorations ou nouvelles créations", lien.inner_text())
        att("lien nouveautés : adresse", "https://www.moodstep.com/arbre/", lien.get_attribute("href"))
        att("lien nouveautés : nouvel onglet", "_blank", lien.get_attribute("target"))
        att("lien nouveautés : sans fuite", "noopener noreferrer", lien.get_attribute("rel"))
        att("crédit : texte", "L'Arbre à questions, conçu par Moodstep · arbre@moodstep.com", page.inner_text("#credit"))
        att("crédit : lien Moodstep", "https://www.moodstep.com/", page.locator("#credit a >> nth=0").get_attribute("href"))
        att("crédit : Moodstep en nouvel onglet", "_blank", page.locator("#credit a >> nth=0").get_attribute("target"))
        att("crédit : mailto", "mailto:arbre@moodstep.com", page.locator("#credit a >> nth=1").get_attribute("href"))

        # ---- les touches de la scène ne font rien ici ----
        for t in ["ArrowRight", "Space", "Enter", "j", "Backspace"]:
            page.keyboard.press(" " if t == "Space" else t)
        att("touches de la scène ignorées en préparation", ("trunk", 0, []), (etat()["mode"], etat()["ti"], etat()["path"]))
        page.evaluate("document.getElementById('prepa-titre').textContent='deux mots'")
        page.dblclick("#prepa-titre")
        att("double-clic : le texte peut être sélectionné", True, page.evaluate("getSelection().toString().length>0"))
        page.mouse.move(100, 100); page.mouse.move(130, 130); page.wait_for_timeout(2800)
        att("curseur non masqué hors scène", "", page.evaluate("document.body.style.cursor"))

        # ---- lancer avec des textes manquants ----
        page.click("#btn-lancer"); page.wait_for_timeout(150)
        att("message des manquants ouvert", True, vis("#dlg-manques"))
        att("résumé", "27 textes sont encore vides :", page.inner_text("#dlg-manques-resume"))
        lignes = [l.strip() for l in page.locator("#dlg-manques-liste li").all_inner_texts()]
        att("liste des manquants",
            ["Tronc : T1, T2, T3, T4", "Alpha : niveaux 1, 2, 3, 4, 5, 6, 7, 8", "Bêta : niveaux 2, 3, 4, 5, 6, 7, 8", "Gamma : niveaux 1, 2, 3, 4, 5, 6, 7, 8"], lignes)
        att("« Compléter » a le focus par défaut", "completer", page.evaluate("document.activeElement.value"))
        page.keyboard.press("Escape"); page.wait_for_timeout(100)
        att("Échap ferme le message sans lancer", (False, True), (vis("#dlg-manques"), vis("#prepa")))
        page.click("#btn-lancer"); page.click("#dlg-manques button[value=completer]"); page.wait_for_timeout(100)
        att("« Compléter » mène à l'éditeur", (True, False), (vis("#editeur"), vis("#prepa")))
        page.click("#btn-retour-prepa")

        # ---- lancer pour de bon ----
        C.lancer_scene(page)
        att("scène visible", True, vis("#screen"))
        att("plus aucune trace de la préparation", (False, False, False, False, False),
            tuple(vis(s) for s in ["#prepa", "#btn-lancer", "#credit", "#nouveautes", "#dlg-manques"]))
        att("aucun élément de préparation sous un point de la scène", True,
            page.evaluate("[[100,100],[640,360],[1100,300],[1200,600]].every(([x,y])=>!document.elementFromPoint(x,y).closest('#prepa'))"))
        att("classe hors-scene retirée", False, page.evaluate("document.body.classList.contains('hors-scene')"))
        att("scène : départ au tronc T1", ("trunk", 0), (etat()["mode"], etat()["ti"]))
        page.keyboard.press("ArrowRight"); page.keyboard.press("ArrowRight")
        att("la scène répond aux touches", 2, etat()["ti"])
        att("texte du tronc vide = « Question T3 »", "Question T3", page.inner_text("#panel .q"))

        # ---- retour par E ----
        page.keyboard.press("e"); page.wait_for_timeout(120)
        att("E ouvre la confirmation", True, vis("#dlg-confirmation"))
        att("« Non » a le focus (Entrée est sans danger)", "non", page.evaluate("document.activeElement.value"))
        page.keyboard.press("Enter"); page.wait_for_timeout(120)
        att("Entrée = Non : on reste sur la scène, parcours intact", (False, True, "trunk", 2), (vis("#dlg-confirmation"), vis("#screen"), etat()["mode"], etat()["ti"]))
        page.keyboard.press("E"); page.keyboard.press("n"); page.wait_for_timeout(120)
        att("N = Non", (False, 2), (vis("#dlg-confirmation"), etat()["ti"]))
        page.keyboard.press("Control+e"); page.wait_for_timeout(100)
        att("Ctrl+E : sans effet", False, vis("#dlg-confirmation"))
        page.keyboard.press("e"); page.keyboard.press("Escape"); page.wait_for_timeout(120)
        att("Échap dans la confirmation = Non", (False, True), (vis("#dlg-confirmation"), vis("#screen")))
        page.keyboard.press("e"); page.keyboard.press("o"); page.wait_for_timeout(150)
        att("E puis O : retour à la préparation", (True, False), (vis("#prepa"), vis("#screen")))
        C.lancer_scene(page)
        att("relancer : on repart du début", ("trunk", 0, []), (etat()["mode"], etat()["ti"], etat()["path"]))

        # ---- Échap deux fois ----
        page.keyboard.press("Escape"); page.wait_for_timeout(100)
        att("un seul Échap : rien", False, vis("#dlg-confirmation"))
        page.wait_for_timeout(1700); page.keyboard.press("Escape"); page.wait_for_timeout(100)
        att("deux Échap trop espacés (>1,5 s) : rien", False, vis("#dlg-confirmation"))
        page.keyboard.press("Escape"); page.wait_for_timeout(150)
        att("deux Échap rapprochés : confirmation", True, vis("#dlg-confirmation"))
        page.keyboard.press("Escape"); page.wait_for_timeout(100)

        att("cliquer dans la confirmation ne fait pas avancer la scène", 0, etat()["ti"])
        att("curseur masqué sur la scène après 2,5 s", "none", (page.mouse.move(60, 60), page.mouse.move(70, 70), page.wait_for_timeout(2900), page.evaluate("document.body.style.cursor"))[3])

        if page.erreurs: echecs.append(f"erreurs JS : {page.erreurs}")
        if C.requetes_suspectes(page): echecs.append(f"requêtes : {C.requetes_suspectes(page)}")
        nav.close()
    return echecs


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else str(C.RACINE / "index.html")
    echecs = tester(f)
    sys.exit(0 if C.bilan(f"préparation {f}", echecs) else 1)
