"""Mode d'emploi : la liste des touches dit-elle vrai ? (et, plus loin, le retour, la portée, les chiffres)

 A. le tableau de l'écran est construit à partir de la liste unique ModeEmploi.touches : mêmes lignes, mêmes touches dessinées, même « quand »
 B. POUR CHAQUE LIGNE de la liste, la touche est jouée sur la VRAIE scène, au bon moment et au mauvais moment, et l'effet annoncé est constaté
    (si une ligne est fausse, c'est la liste qu'on corrige, jamais la scène) ; chaque ligne de la liste doit avoir son contrôle ci-dessous
 C. la lettre du « oui » et du « non » dessinée dans le tableau est celle de la langue (et c'est elle qui répond dans la fenêtre)
 D. les cinq boutons du schéma : chaque rond est à la place du vrai bouton de la scène

 E. le retour (Échap ou « ← Retour ») ramène au même écran, à la même position, au même champ, au même curseur : depuis l'accueil et depuis l'éditeur
 F. le mode d'emploi ne s'ouvre JAMAIS depuis la scène ni depuis l'aperçu : aucune touche, aucun bouton visible, et l'ouverture refuse d'elle-même
 G. les chiffres du tableau des arbres sont ceux des fiches : les deux vrais arbres, et un arbre factice qui doit afficher SES chiffres
 H. le fichier téléchargé depuis l'éditeur embarque le mode d'emploi, et il marche une fois rouvert (dans la langue choisie)
 I. la scène est identique à celle d'AVANT le chantier (commit de référence) : même dessin, mêmes cartes, mêmes pixels (hors bruit de rendu mesuré)

Usage :  .venv/bin/python tests/test_mode_emploi.py
         ARBRE_FICHIER=chemin/vers/une_copie.html .venv/bin/python tests/test_mode_emploi.py     (pour passer un mutant)
"""
import os, sys, pathlib, re, subprocess
from playwright.sync_api import sync_playwright
import _commun as C

FICHIER = pathlib.Path(os.environ.get("ARBRE_FICHIER", str(C.RACINE / "index.html"))).resolve()
INIT = ("window.__hasard=()=>0.5;"                                                # tirages reproductibles
        "Element.prototype.requestFullscreen=function(){window.__fs=(window.__fs||0)+1;return Promise.resolve();};")   # on compte les demandes de plein écran
ETAT = "({ecran, mode, ti, path: path.slice(), subs: subs.slice(), dlg: !!document.querySelector('dialog[open]')})"
# Le « quand » de chaque ligne, tel que les contrôles B le constatent (écrit ici à la main, indépendamment de la liste de l'écran).
QUAND = {"suivant": "pasvote", "retour": "pasdebut", "jaune": "vote", "bleue": "vote", "haut": "vote", "bas": "vote", "subs": "subs", "plein": "toujours",
         "reset": "toujours", "sortir": "toujours", "sortir2": "toujours", "oui": "fenetre", "non": "fenetre"}
_nouvelle_page = C.nouvelle_page
def _page_vive(*a, **k):
    pg = _nouvelle_page(*a, **k); pg.set_default_timeout(5000); return pg      # un bouton introuvable fait échouer en 5 s, pas en 30 s
C.nouvelle_page = _page_vive

AVANT = "67b8fd4"      # dernier commit avant le chantier « Mode d'emploi » : la scène doit être la même
FACTICE = (C.RACINE / "tests" / "arbre_factice.js").read_text(encoding="utf-8")
LANGUES = {"fr": ("fr-FR", "O", "N"), "en": ("en-GB", "Y", "N"), "de": ("de-DE", "J", "N"), "es": ("es-ES", "S", "N")}


def ouvrir_scene(nav, locale="fr-FR"):
    page = C.nouvelle_page(nav, "1280x720", locale=locale, init_script=INIT)
    page.goto(FICHIER.as_uri()); page.wait_for_timeout(500)
    C.lancer_scene(page)
    return page


def presser(page, k):
    page.keyboard.press(k); page.wait_for_timeout(70)


def etat(page):
    return page.evaluate(ETAT)


def vers(page, lieu):
    """Replace la scène à un endroit précis du parcours (la remise à zéro est la touche Maj+R elle-même)."""
    if etat(page)["dlg"]: presser(page, "Escape")
    presser(page, "Shift+R")
    if lieu == "trunk0": return
    if lieu == "trunk1": presser(page, "ArrowRight"); return
    for _ in range(4): presser(page, "ArrowRight")
    if lieu == "vote1": return
    presser(page, "j")
    if lieu == "reponse1": return
    presser(page, "ArrowRight")
    if lieu == "vote2": return
    assert lieu == "fin", lieu
    for _ in range(40):
        m = etat(page)["mode"]
        if m == "end": return
        presser(page, "j" if m == "choose" else "ArrowRight")
    raise AssertionError("le parcours n'arrive pas au tableau final")


def tester():
    echecs = []
    def att(nom, attendu, obtenu):
        if attendu != obtenu:
            echecs.append(f"{nom} : attendu {attendu!r}, obtenu {obtenu!r}")

    class section:
        """Tout ce qui plante dans une section est rapporté comme un échec de cette section : un test qui se perd en route ne prouve rien."""
        def __init__(self, nom): self.nom = nom
        def __enter__(self): return self
        def __exit__(self, et, ev, tb):
            if et is not None:
                echecs.append(f"{self.nom} le test a planté avant la fin de la section : {et.__name__} : {str(ev).strip().splitlines()[0][:160] if str(ev).strip() else ''}")
            return True

    with sync_playwright() as p:
        nav = C.lancer(p)

        # ============ A. le tableau est construit à partir de la liste ============
        with section("A."):
            page = C.nouvelle_page(nav, "1280x720", init_script=INIT)
            page.goto(FICHIER.as_uri()); page.wait_for_timeout(500)
            page.click("#btn-aide-pied"); page.wait_for_timeout(200)
            liste = page.evaluate("ModeEmploi.touches")
            ids = [t["id"] for t in liste]
            att("A. aucune ligne en double dans la liste", len(ids), len(set(ids)))
            att("A. chaque ligne de la liste est connue du test (et inversement)", sorted(QUAND), sorted(ids))
            for t in liste: att(f"A. {t['id']} : le « quand » de la liste est celui que le test constate", QUAND.get(t["id"]), t["ou"])
            lignes = page.evaluate("""() => [...document.querySelectorAll('.aide-touches tbody tr')].map(tr => ({
                kbd: [...tr.children[0].querySelectorAll('kbd')].map(k => k.textContent), effet: tr.children[1].textContent.trim(), quand: tr.children[2].textContent.trim()}))""")
            att("A. une ligne de tableau par ligne de la liste", len(liste), len(lignes))
            nom = lambda c: page.evaluate("(c) => { if (c[0] !== '@') return c; const v = tx(c.slice(1)); return /\\.(oui|non)$/.test(c) ? v.toUpperCase() : v; }", c)
            for t, l in zip(liste, lignes):
                attendu = []
                for a in t["aff"]: attendu += [nom(x) for x in a] if isinstance(a, list) else [nom(a)]
                att(f"A. {t['id']} : touches dessinées", attendu, l["kbd"])
                att(f"A. {t['id']} : « quand » lu dans les textes", page.evaluate("(o) => tx('mode.q.' + o)", t["ou"]), l["quand"])
                att(f"A. {t['id']} : effet écrit", True, len(l["effet"]) > 3)
            # ce qui est DESSINÉ doit être ce qui est JOUÉ : chaque touche affichée correspond à une touche de « cles » (table de correspondance indépendante de la liste)
            CORRESP = {"→": "ArrowRight", "←": "ArrowLeft", "↑": "ArrowUp", "↓": "ArrowDown", "⌫": "Backspace", "@touche.espace": " ", "@touche.entree": "Enter",
                       "@touche.pagesuiv": "PageDown", "@touche.echap": "Escape", "@touche.maj": "Shift"}
            def joue(c):
                if c in CORRESP: return CORRESP[c]
                if c in ("@touche.oui", "@touche.non"): return c
                return c
            for t in liste:
                affiches = []
                for x in t["aff"]:
                    affiches.append("+".join(joue(y) for y in x) if isinstance(x, list) else joue(x))
                cles_jouees = [k.lower() if len(k) == 1 and k.isalpha() else k for k in t["cles"]]
                if t["id"] == "sortir2":                                  # deux appuis sur la même touche
                    att("A. sortir2 : dessinée comme jouée", ["Escape+Escape"], affiches); continue
                for a_ in affiches:
                    a_n = a_.lower() if len(a_) == 1 and a_.isalpha() else a_
                    att(f"A. {t['id']} : la touche dessinée {a_!r} fait partie de celles qui sont jouées", True, a_n in cles_jouees)
                for k in cles_jouees:
                    if k in ("J", "B") or (len(k) == 1 and k.isalpha()):   # une lettre jouée en minuscule ou en majuscule : une seule est dessinée
                        continue
                    att(f"A. {t['id']} : la touche jouée {k!r} est dessinée", True, k in [x.lower() if len(x) == 1 and x.isalpha() else x for x in affiches] or k.startswith("Shift"))
            att("A. le tableau a 3 colonnes partout", [3], sorted({n for n in page.evaluate("[...document.querySelectorAll('.aide-touches tr')].map(r => r.children.length)")}))
            page.context.close()

        # ============ B. chaque ligne, jouée sur la vraie scène ============
        with section("B."):
            page = ouvrir_scene(nav)
            page.evaluate("window.__fs = 0")
            cles_de = lambda i: [k for k in next(t for t in liste if t["id"] == i)["cles"]]

            def oracle_suivant():
                for k in cles_de("suivant"):
                    vers(page, "trunk0"); presser(page, k); e = etat(page)
                    att(f"B. suivant : {k!r} au tronc avance d'une question", ("trunk", 1), (e["mode"], e["ti"]))
                    vers(page, "vote1"); presser(page, k)
                    att(f"B. suivant : {k!r} ne fait rien pendant un vote", ("choose", []), (etat(page)["mode"], etat(page)["path"]))
                    vers(page, "reponse1"); presser(page, k)
                    att(f"B. suivant : {k!r} après une réponse amène le vote suivant", "choose", etat(page)["mode"])

            def oracle_retour():
                for k in cles_de("retour"):
                    vers(page, "trunk1"); presser(page, k)
                    att(f"B. retour : {k!r} revient d'une question du tronc", 0, etat(page)["ti"])
                    vers(page, "trunk0"); presser(page, k)
                    att(f"B. retour : {k!r} ne fait rien sur la toute première question", ("trunk", 0), (etat(page)["mode"], etat(page)["ti"]))
                    vers(page, "vote1"); presser(page, k)
                    att(f"B. retour : {k!r} depuis le premier vote revient à la dernière question du tronc", ("trunk", 3), (etat(page)["mode"], etat(page)["ti"]))
                    vers(page, "reponse1"); presser(page, k)
                    att(f"B. retour : {k!r} depuis une réponse revient au vote", ("choose", []), (etat(page)["mode"], etat(page)["path"]))

            def choix_couleur(i, couleur):
                for k in cles_de(i):
                    vers(page, "vote1")
                    voulu = page.evaluate(f"options().find(id => byId[id].color === '{couleur}')")
                    presser(page, k)
                    att(f"B. {i} : {k!r} choisit la question de la couleur {couleur}", [voulu], etat(page)["path"])
                    vers(page, "trunk1"); presser(page, k)
                    att(f"B. {i} : {k!r} ne fait rien hors vote", ("trunk", []), (etat(page)["mode"], etat(page)["path"]))

            def choix_carte(i, rang):
                for k in cles_de(i):
                    vers(page, "vote1")
                    voulu = page.evaluate(f"options()[{rang}]")
                    presser(page, k)
                    att(f"B. {i} : {k!r} choisit la carte n°{rang + 1} de l'écran", [voulu], etat(page)["path"])
                    vers(page, "trunk1"); presser(page, k)
                    att(f"B. {i} : {k!r} ne fait rien hors vote", ("trunk", []), (etat(page)["mode"], etat(page)["path"]))

            def oracle_subs():
                for k in cles_de("subs"):
                    for lieu in ("trunk0", "trunk1", "vote1"):
                        vers(page, lieu); presser(page, k)
                        att(f"B. subs : {k!r} ne fait rien avant la première réponse ({lieu})", False, etat(page)["mode"] == "sub")
                    for lieu in ("reponse1", "vote2", "fin"):
                        vers(page, lieu); presser(page, k)
                        e = etat(page)
                        att(f"B. subs : {k!r} tire une subsidiaire dès la première réponse ({lieu})", ("sub", 1), (e["mode"], len(e["subs"])))

            def oracle_plein():
                for k in cles_de("plein"):
                    for lieu in ("trunk0", "vote1"):
                        vers(page, lieu); avant = page.evaluate("window.__fs"); presser(page, k)
                        att(f"B. plein : {k!r} demande le plein écran ({lieu})", avant + 1, page.evaluate("window.__fs"))

            def oracle_reset():
                for lieu in ("reponse1", "vote2", "fin"):
                    vers(page, lieu); presser(page, "Shift+R"); e = etat(page)
                    att(f"B. reset : Maj+R recommence tout, sans confirmation ({lieu})", ("trunk", 0, [], False), (e["mode"], e["ti"], e["path"], e["dlg"]))

            def oracle_sortir():
                for k in cles_de("sortir"):
                    for lieu in ("trunk0", "vote1", "fin"):
                        vers(page, lieu); presser(page, k)
                        att(f"B. sortir : {k!r} ouvre la confirmation ({lieu})", (True, "scene"), (etat(page)["dlg"], etat(page)["ecran"]))
                        presser(page, "n")                                # on reste sur la scène
                        att(f"B. sortir : la confirmation se ferme, on reste sur la scène ({lieu})", (False, "scene"), (etat(page)["dlg"], etat(page)["ecran"]))

            def oracle_sortir2():
                vers(page, "vote1"); presser(page, "Escape")
                att("B. sortir2 : un seul Échap n'ouvre rien", False, etat(page)["dlg"])
                presser(page, "Escape")
                att("B. sortir2 : deux Échap rapprochés ouvrent la confirmation", True, etat(page)["dlg"])
                presser(page, "n")
                vers(page, "vote1"); presser(page, "Escape"); page.wait_for_timeout(1700); presser(page, "Escape")
                att("B. sortir2 : deux Échap à plus d'une seconde et demie d'écart n'ouvrent rien", False, etat(page)["dlg"])

            ORACLES = {"suivant": oracle_suivant, "retour": oracle_retour, "jaune": lambda: choix_couleur("jaune", "j"), "bleue": lambda: choix_couleur("bleue", "b"),
                       "haut": lambda: choix_carte("haut", 0), "bas": lambda: choix_carte("bas", 1), "subs": oracle_subs, "plein": oracle_plein, "reset": oracle_reset,
                       "sortir": oracle_sortir, "sortir2": oracle_sortir2}
            for i in ids:
                if i in ("oui", "non"): continue                           # contrôlés en C, dans chaque langue
                if i not in ORACLES: echecs.append(f"B. la ligne « {i} » de la liste n'a aucun contrôle : en écrire un"); continue
                ORACLES[i]()
            # une touche mentionnée dans le mode d'emploi comme sans effet : Page précédente (conseil du jour J)
            vers(page, "trunk1"); presser(page, "PageUp")
            att("B. « Page précédente » n'a aucun effet (conseil du jour J)", ("trunk", 1), (etat(page)["mode"], etat(page)["ti"]))
            att("B. aucune erreur dans la console", [], page.erreurs)
            att("B. aucune requête réseau", [], C.requetes_suspectes(page))
            page.context.close()

        # ============ C. le oui et le non de la langue ============
        with section("C."):
            for code, (locale, oui, non) in LANGUES.items():
                page = ouvrir_scene(nav, locale)
                att(f"C. {code} : langue de l'outil", code, page.evaluate("LANGUE"))
                # la lettre répond vraiment dans la fenêtre de confirmation
                presser(page, "e"); presser(page, oui.lower())
                att(f"C. {code} : la lettre « {oui} » dit oui (retour à l'accueil)", ("prepa", False), (etat(page)["ecran"], etat(page)["dlg"]))
                C.lancer_scene(page); presser(page, "e"); presser(page, non.lower())
                att(f"C. {code} : la lettre « {non} » dit non (on reste sur la scène)", ("scene", False), (etat(page)["ecran"], etat(page)["dlg"]))
                # et c'est bien elle qui est dessinée dans le tableau
                page.evaluate("montrer('prepa')"); page.click("#btn-aide-pied"); page.wait_for_timeout(150)
                vus = page.evaluate("""() => [...document.querySelectorAll('.aide-touches tbody tr')].slice(-2).map(tr => tr.children[0].textContent)""")
                att(f"C. {code} : le tableau dessine {oui} et {non}", [oui, non], vus)
                page.context.close()

        # ============ D. le schéma : chaque rond est à la place du vrai bouton ============
        with section("D."):
            page = ouvrir_scene(nav)
            page.evaluate("window.__fs = 0")
            # on met la scène dans un état où les cinq boutons existent : dernière question du parcours (le rond du milieu), pas la première
            vers(page, "reponse1")
            for _ in range(40):
                if etat(page)["mode"] == "answer" and page.evaluate("options().length === 0"): break
                presser(page, "j" if etat(page)["mode"] == "choose" else "ArrowRight")
            boutons = page.evaluate("ModeEmploi.boutons")
            att("D. cinq boutons dans le schéma", [1, 2, 3, 4, 5], [b["n"] for b in boutons])
            W, H = 1280, 720
            for b in boutons:
                r = page.evaluate(f"(() => {{ const e = document.getElementById('{b['el']}'); const r = e.getBoundingClientRect(); return {{x: r.x + r.width / 2, y: r.y + r.height / 2, vu: e.checkVisibility({{checkVisibilityCSS: true}})}}; }})()")
                att(f"D. le bouton {b['n']} ({b['el']}) est visible sur la dernière question", True, r["vu"])
                h = "g" if r["x"] < W / 3 else "d" if r["x"] > 2 * W / 3 else "c"
                v = "h" if r["y"] < H / 2 else "b"
                att(f"D. le bouton {b['n']} ({b['el']}) est à la place indiquée par le schéma", (b["h"], b["v"]), (h, v))
            page.context.close()

        # ============ E. le retour ============
        with section("E."):
            def etat_retour(pg):
                return pg.evaluate("({ecran, y: Math.round(scrollY), id: document.activeElement.id, s: document.activeElement.selectionStart})")
            def ouvrir_accueil(taille, nom_champ):
                pg = C.nouvelle_page(nav, taille, init_script=INIT)
                pg.goto(FICHIER.as_uri()); pg.wait_for_timeout(500)
                return pg
            # E1-E3 : depuis l'accueil, dans une fenêtre assez basse pour que la page défile
            for sortie in ("Escape", "bouton"):
                pg = ouvrir_accueil("1280x400", None)
                # la page défile à 560 (le maximum est 614 : un retour « tout en bas » serait vu) ; le bouton est déjà visible, le clic ne fait donc pas défiler
                pg.evaluate("window.scrollTo(0, 560); document.getElementById('langue').focus({preventScroll: true})"); avant = etat_retour(pg)
                att(f"E. accueil ({sortie}) : le départ est bien défilé (pas tout en bas) et sur le sélecteur de langue", (True, "langue"), (500 < avant["y"] < 600, avant["id"]))
                att(f"E. accueil ({sortie}) : le bouton est visible sans défiler", True, pg.evaluate("(() => { const r = document.getElementById('btn-aide-pied').getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; })()"))
                pg.click("#btn-aide-pied"); pg.wait_for_timeout(150)
                pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")           # on lit jusqu'en bas avant de revenir
                att(f"E. accueil ({sortie}) : le mode d'emploi est ouvert", "aide", pg.evaluate("ecran"))
                if sortie == "Escape": pg.keyboard.press("Escape")
                else: pg.click("#btn-retour-aide")
                pg.wait_for_timeout(150)
                att(f"E. accueil ({sortie}) : retour au même endroit, au même champ", ("prepa", avant["y"], "langue"), (lambda e: (e["ecran"], e["y"], e["id"]))(etat_retour(pg)))
                pg.context.close()
            # E3 : au clavier seul, le focus revient sur le bouton qui a ouvert
            pg = ouvrir_accueil("1280x420", None); pg.focus("#btn-aide-pied"); pg.keyboard.press("Enter"); pg.wait_for_timeout(150)
            att("E. clavier : Entrée sur le bouton ouvre le mode d'emploi", "aide", pg.evaluate("ecran"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
            att("E. clavier : Échap rend le focus au bouton", ("prepa", "btn-aide-pied"), (pg.evaluate("ecran"), pg.evaluate("document.activeElement.id")))
            pg.context.close()
            # E4-E6 : depuis l'éditeur, tout en bas, curseur au milieu d'une question
            for sortie in ("Escape", "bouton"):
                pg = ouvrir_accueil("1280x720", None); pg.click("#btn-modifier")
                champs = pg.locator("#editeur textarea"); dernier = champs.nth(champs.count() - 1); dernier.scroll_into_view_if_needed(); dernier.click()
                pg.keyboard.type("bonjour tout le monde")
                for _ in range(5): pg.keyboard.press("ArrowLeft")
                avant = etat_retour(pg)
                att(f"E. éditeur ({sortie}) : départ tout en bas, curseur dans la dernière question", (True, "f-q-A8", 16), (avant["y"] > 1000, avant["id"], avant["s"]))
                pg.click("#btn-aide-editeur"); pg.wait_for_timeout(150)
                pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                if sortie == "Escape": pg.keyboard.press("Escape")
                else: pg.click("#btn-retour-aide")
                pg.wait_for_timeout(150)
                apres = etat_retour(pg)
                att(f"E. éditeur ({sortie}) : même écran, même position, même champ, même curseur", ("editeur", avant["y"], avant["id"], avant["s"]), (apres["ecran"], apres["y"], apres["id"], apres["s"]))
                att(f"E. éditeur ({sortie}) : le texte tapé est intact", "bonjour tout le monde", pg.evaluate("document.activeElement.value"))
                # on peut recommencer : la mémoire ne reste pas collée à la première ouverture
                pg.evaluate("window.scrollTo(0, 400)"); pg.click("#btn-aide-editeur"); pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
                att(f"E. éditeur ({sortie}) : une deuxième ouverture revient aussi à la bonne position", 400, etat_retour(pg)["y"])
                pg.context.close()
            # Échap ne fait rien en dehors du mode d'emploi (il ne doit pas fermer l'éditeur)
            pg = ouvrir_accueil("1280x720", None); pg.click("#btn-modifier"); pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
            att("E. Échap dans l'éditeur seul ne change pas d'écran", "editeur", pg.evaluate("ecran")); pg.context.close()

        # ============ F. jamais sur la scène ============
        with section("F."):
            pg = ouvrir_scene(nav)
            att("F. scène : aucun bouton « Mode d'emploi » visible", [False, False], [pg.evaluate("document.getElementById('btn-aide-pied').checkVisibility()"), pg.evaluate("document.getElementById('btn-aide-editeur').checkVisibility()")])
            for lieu in ("trunk0", "vote1", "reponse1", "fin"):
                vers(pg, lieu)
                for k in ["h", "H", "?", "m", "M", "a", "i", "F1", "F2", "Tab", "Shift+/", "Control+h", "Meta+/"]:
                    pg.keyboard.press(k); pg.wait_for_timeout(30)
                    if pg.evaluate("ecran") == "aide": echecs.append(f"F. la touche {k!r} a ouvert le mode d'emploi sur la scène ({lieu})"); break
                att(f"F. scène ({lieu}) : toujours sur la scène après 13 touches inconnues", "scene", pg.evaluate("ecran"))
            pg.evaluate("ModeEmploi.ouvrir()")
            att("F. scène : l'ouverture elle-même refuse", "scene", pg.evaluate("ecran"))
            att("F. scène : le mode d'emploi reste caché", True, pg.evaluate("document.getElementById('mode-emploi').hidden"))
            pg.context.close()
            pg = ouvrir_accueil("1280x720", None); pg.click("#btn-modifier"); pg.locator(".q-ligne button").first.click(); pg.wait_for_selector("#barre-apercu", state="visible")
            pg.evaluate("ModeEmploi.ouvrir()")
            att("F. aperçu « Voir sur scène » : l'ouverture refuse aussi", "apercu", pg.evaluate("ecran"))
            att("F. aperçu : aucun bouton « Mode d'emploi » visible", False, pg.evaluate("document.getElementById('btn-aide-editeur').checkVisibility()"))
            # le bouton « Fermer l'aperçu » est hors des écrans habituels : il doit quand même avoir la police des autres boutons (il était en Times)
            att("F. aperçu : « Fermer l'aperçu » a la même police que les autres boutons", pg.evaluate("getComputedStyle(document.getElementById('btn-retour-prepa')).fontFamily"), pg.evaluate("getComputedStyle(document.getElementById('btn-fermer-apercu')).fontFamily"))
            pg.context.close()

        # ============ G. les chiffres sont ceux des fiches ============
        with section("G."):
            VRAIS = {"olivier": ("3", "4", "23", "8"), "chene": ("4", "4", "26", "7")}      # thèmes, tronc, ramure, votes : README, guide
            def lire_tableau(pg):
                pg.click("#btn-aide-pied"); pg.wait_for_timeout(150)
                return pg.evaluate("""() => { const t = document.querySelector('.aide-tableau'); const col = [...t.querySelectorAll('thead th')].map(x => x.textContent);
                  const lignes = [...t.querySelectorAll('tbody tr')].map(r => [...r.children].map(c => c.textContent)); return {col, lignes}; }""")
            pg = ouvrir_accueil("1280x720", None); tab = lire_tableau(pg)
            att("G. deux colonnes : olivier et chêne", ["Olivier", "Chêne"], tab["col"])
            for j, arbre in enumerate(("olivier", "chene")):
                lus = tuple(l[j + 1] for l in tab["lignes"][:4])
                att(f"G. {arbre} : thèmes, tronc, ramure, votes du tableau = chiffres connus", VRAIS[arbre], lus)
                calcul = pg.evaluate(f"(() => {{ const f = DESSINS['{arbre}']; return [String(f.themes.length), String(ARBRE.tronc.length), String(f.structure.length), String(Math.max(...f.structure.map(d => d.step)))]; }})()")
                att(f"G. {arbre} : = ce que la fiche contient", list(calcul), list(lus))
            att("G. mascotte et fruits (olivier, chêne)", [["une mésange", "un écureuil"], ["des olives", "des glands"]], [tab["lignes"][4][1:], tab["lignes"][5][1:]])
            pg.context.close()
            fac = C.CAPTURES / "mode_emploi_arbre_factice.html"
            fac.write_text(FICHIER.read_text(encoding="utf-8").replace('<script id="mecanique">', '<script id="dessin-factice">\n' + FACTICE + '</script>\n<script id="mecanique">', 1), encoding="utf-8")
            pg = C.nouvelle_page(nav, "1280x720", init_script=INIT); pg.goto(fac.as_uri()); pg.wait_for_timeout(500); tab = lire_tableau(pg)
            att("G. arbre factice : une troisième colonne, avec son nom", ["Olivier", "Chêne", "Chêne (arbre de test)"], tab["col"])
            att("G. arbre factice : SES chiffres (4 thèmes, tronc 4, 10 questions, 3 votes)", ["4", "4", "10", "3"], [l[3] for l in tab["lignes"][:4]])
            att("G. arbre factice : mascotte et fruits inconnus = un tiret", ["–", "–"], [tab["lignes"][4][3], tab["lignes"][5][3]])
            att("G. arbre factice : les vrais arbres gardent leurs chiffres", [["3", "4"], ["4", "4"], ["23", "26"], ["8", "7"]], [l[1:3] for l in tab["lignes"][:4]])
            pg.context.close()

        # ============ H. le fichier téléchargé ============
        with section("H."):
            pg = C.nouvelle_page(nav, "1280x720", locale="en-GB", init_script=INIT); pg.goto(FICHIER.as_uri()); pg.wait_for_timeout(500)
            pg.click("#btn-modifier"); pg.fill("#f-titre", "Essai du mode d'emploi"); pg.wait_for_timeout(700)
            with pg.expect_download() as dl: pg.click("#btn-telecharger")
            chemin = C.CAPTURES / "mode_emploi_telecharge.html"; dl.value.save_as(str(chemin)); pg.context.close()
            html = chemin.read_text(encoding="utf-8")
            att("H. le fichier téléchargé contient l'écran et son code", (True, True), ('id="mode-emploi"' in html, 'id="mode-emploi-js"' in html))
            att("H. le corps du mode d'emploi n'est pas écrit en dur dans le fichier (il se construit à l'ouverture)", False, "aide-s1" in html.split('id="mode-emploi-js"')[0])
            pg = C.nouvelle_page(nav, "1280x720", locale="fr-FR", init_script=INIT); pg.goto(chemin.as_uri()); pg.wait_for_timeout(500)
            att("H. rouvert : la langue embarquée (anglais) est gardée", "en", pg.evaluate("LANGUE"))
            att("H. rouvert : le lien « How to use » est là", "How to use", pg.inner_text("#btn-aide-pied"))
            pg.click("#btn-aide-pied"); pg.wait_for_timeout(150)
            att("H. rouvert : le mode d'emploi s'ouvre, en anglais, avec ses 8 sections", ("aide", "How to use", 8), (pg.evaluate("ecran"), pg.inner_text("#mode-emploi h1"), pg.locator("#mode-emploi h2").count()))
            att("H. rouvert : le tableau des touches a ses 13 lignes", 13, pg.locator(".aide-touches tbody tr").count())
            pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
            att("H. rouvert : Échap ramène à l'accueil", "prepa", pg.evaluate("ecran"))
            att("H. rouvert : aucune erreur console, aucune requête réseau", ([], []), (pg.erreurs, C.requetes_suspectes(pg)))
            pg.context.close()

        # ============ I. la scène est celle d'avant ============
        with section("I."):
            avant_f = C.CAPTURES / f"mode_emploi_scene_avant_{AVANT}.html"
            try:
                avant_f.write_bytes(subprocess.run(["git", "show", f"{AVANT}:index.html"], cwd=str(C.RACINE), capture_output=True, check=True).stdout)
            except Exception as e:
                echecs.append(f"I. impossible de lire le fichier de référence {AVANT} avec git : {e}"); avant_f = None
            if avant_f:
                def parcours_scene(chemin, arbre):
                    pg = C.nouvelle_page(nav, "1280x720", init_script=INIT); pg.goto(pathlib.Path(chemin).as_uri()); pg.wait_for_timeout(500)
                    pg.click(f'.vignette[data-arbre="{arbre}"]'); pg.evaluate("ARBRE.themes.forEach((t,i)=>{t.nom=['Alpha','Bêta','Gamma','Delta'][i];})")
                    C.lancer_scene(pg); res = []
                    def prendre(nom):
                        pg.wait_for_timeout(1300)
                        dom = C.sha(pg.evaluate("document.getElementById('svg').outerHTML + '|' + document.getElementById('panel').innerHTML + '|' + document.getElementById('screen').className + '|' + [...document.querySelectorAll('.prev,.next,.rst')].map(b => b.id + b.hidden).join()"))
                        res.append((nom, dom, C.sha(pg.screenshot().hex())))
                    prendre("tronc 1")
                    for i in range(2, 5): pg.keyboard.press("ArrowRight"); prendre(f"tronc {i}")
                    pg.keyboard.press("ArrowRight"); prendre("premier vote")
                    pg.keyboard.press("j"); prendre("réponse 1")
                    pg.keyboard.press("="); prendre("subsidiaire")
                    pg.keyboard.press("ArrowLeft"); prendre("retour de la subsidiaire")
                    pg.keyboard.press("ArrowRight"); prendre("vote 2")
                    for _ in range(40):
                        m = pg.evaluate("mode")
                        if m == "end": break
                        pg.keyboard.press("b" if m == "choose" else "ArrowRight"); pg.wait_for_timeout(50)
                    prendre("tableau final")
                    pg.keyboard.press("Shift+R"); prendre("tout recommencé")
                    erreurs = (pg.erreurs, C.requetes_suspectes(pg)); pg.context.close()
                    return res, erreurs
                for arbre in ("olivier", "chene"):
                    ref, _ = parcours_scene(avant_f, arbre)
                    temoin, _ = parcours_scene(avant_f, arbre)
                    actuel, err = parcours_scene(FICHIER, arbre)
                    att(f"I. {arbre} : même nombre d'états", len(ref), len(actuel))
                    att(f"I. {arbre} : aucune erreur JS / requête", ([], []), err)
                    bruit = [r[0] for r, t in zip(ref, temoin) if r[2] != t[2]]
                    for r, a in zip(ref, actuel):
                        att(f"I. {arbre} / {r[0]} : même dessin, mêmes cartes, mêmes boutons (DOM)", r[1], a[1])
                        if r[0] not in bruit: att(f"I. {arbre} / {r[0]} : mêmes pixels", r[2], a[2])
                    print(f"   {arbre} : {len(ref)} états comparés (DOM) ; pixels comparés sur {len(ref) - len(bruit)}" + (f" ; bruit de rendu constaté (avant contre avant) sur : {bruit}" if bruit else ""), flush=True)
        nav.close()
    return echecs


if __name__ == "__main__":
    ok = C.bilan("mode d'emploi : liste des touches, oui/non par langue, schéma (" + FICHIER.name + ")", tester())
    sys.exit(0 if ok else 1)
