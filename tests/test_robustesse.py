"""Cas limites : mémoire du navigateur en panne, noms de fichier tordus, titre piégé, champs vides.

Usage :  .venv/bin/python tests/test_robustesse.py
"""
import sys, re, json, pathlib, shutil
from playwright.sync_api import sync_playwright
import _commun as C

DOSSIER = C.CAPTURES / "robustesse"
shutil.rmtree(DOSSIER, ignore_errors=True); DOSSIER.mkdir(parents=True)
FICHIER = (pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else C.RACINE / "index.html").as_uri()

ECRITURE_REFUSEE = "Storage.prototype.setItem = function () { throw new DOMException('quota', 'QuotaExceededError'); };"
STOCKAGE_INACCESSIBLE = "Object.defineProperty(window, 'localStorage', { configurable: true, get() { throw new DOMException('denied', 'SecurityError'); } });"


def telecharger(page, nom_fichier):
    with page.expect_download() as dl:
        page.click("#btn-telecharger")
    d = dl.value; chemin = DOSSIER / (nom_fichier or d.suggested_filename); d.save_as(chemin)
    return d.suggested_filename, chemin


def tester():
    echecs = []
    def att(nom, attendu, obtenu):
        if attendu != obtenu: echecs.append(f"{nom} : attendu {str(attendu)[:120]!r}, obtenu {str(obtenu)[:120]!r}")
    with sync_playwright() as p:
        nav = C.lancer(p)

        # ---- 1 & 2. mémoire du navigateur en panne : l'appli doit continuer à marcher ----
        for nom, script in (("écriture refusée (quota)", ECRITURE_REFUSEE), ("stockage inaccessible (SecurityError)", STOCKAGE_INACCESSIBLE)):
            page = C.nouvelle_page(nav, "1280x720", init_script=script)
            page.goto(FICHIER); page.wait_for_timeout(400)
            att(f"{nom} : la préparation s'affiche", True, page.locator("#prepa").is_visible())
            page.click("#btn-modifier"); page.fill("#f-titre", "Essai sans mémoire"); page.fill("#f-q-I1", "Une question qui survit")
            page.wait_for_timeout(900)
            att(f"{nom} : message clair", True, "Sauvegarde automatique indisponible" in page.inner_text("#statut"))
            att(f"{nom} : la saisie est conservée dans la page", "Une question qui survit", page.input_value("#f-q-I1"))
            fichier, chemin = telecharger(page, None)
            data = json.loads(re.search(r'id="donnees-arbre">\n(.*?)\n</script>', chemin.read_text(encoding="utf-8"), re.S).group(1))
            att(f"{nom} : le téléchargement marche quand même", ("arbre-a-questions-essai-sans-memoire.html", "Une question qui survit"), (fichier, data["questions"]["I1"]))
            page.click("#btn-lancer-editeur"); page.click("#dlg-manques button[value=lancer]")
            C.attendre_dessin(page)
            page.keyboard.press("ArrowRight")
            att(f"{nom} : la scène se lance et répond", ("scene", 1), tuple(page.evaluate("[ecran, ti]")))
            att(f"{nom} : aucune erreur JS", [], page.erreurs)
            att(f"{nom} : aucune requête", [], C.requetes_suspectes(page))
            page.context.close()

        # ---- 3. noms de fichier tordus et titre piégé ----
        page = C.nouvelle_page(nav, "1280x720"); page.goto(FICHIER); page.wait_for_timeout(400); page.click("#btn-modifier")
        cas = [("   ", "arbre-a-questions-sans-titre.html"), ("😀😀", "arbre-a-questions-sans-titre.html"), ("", "arbre-a-questions-sans-titre.html"),
               ("Œuvre & Æther", "arbre-a-questions-oeuvre-aether.html"), ("a/b\\c:d*e?f", "arbre-a-questions-a-b-c-d-e-f.html"),
               ("Été 2026 — Saint-Nazaire", "arbre-a-questions-ete-2026-saint-nazaire.html"),
               ("x" * 80, "arbre-a-questions-" + "x" * 60 + ".html"), ("Mot " * 20, "arbre-a-questions-" + "mot-" * 14 + "mot.html")]
        for titre, attendu in cas:
            page.fill("#f-titre", titre)
            fichier, _ = telecharger(page, "n.html")
            att(f"nom de fichier pour {titre[:20]!r}", attendu, fichier)
        # titre qui tente de sortir de la balise <title> et d'exécuter du code
        piege = "</title><script>window.__xss=1</script><h1>pwn</h1>"
        page.fill("#f-titre", piege)
        _, chemin = telecharger(page, "piege.html"); html = chemin.read_text(encoding="utf-8")
        entete = re.search(r"(?s)<head>.*?</head>", html).group(0)
        att("titre piégé : échappé dans <title>", True, "&lt;/title&gt;&lt;script&gt;" in entete and entete.count("</title>") == 1)
        page2 = C.nouvelle_page(nav, "1280x720"); page2.goto(chemin.as_uri()); page2.wait_for_timeout(400)
        att("titre piégé : aucun code exécuté à la réouverture", None, page2.evaluate("window.__xss"))
        att("titre piégé : aucun élément injecté", 0, page2.locator("#prepa h1:has-text('pwn'), h1:has-text('pwn')").count())
        att("titre piégé : affiché tel quel", piege, page2.inner_text("#prepa-titre"))
        att("titre piégé : onglet", piege, page2.title())
        page2.context.close()
        att("aucune erreur JS (noms de fichier)", [], page.erreurs)
        page.context.close()

        # ---- 4. tout vide, puis lancé quand même ----
        page = C.nouvelle_page(nav, "1280x720"); page.goto(FICHIER); page.wait_for_timeout(400)
        page.click("#btn-lancer"); page.wait_for_timeout(150)
        att("tout vide : 30 textes manquants", "30 textes sont encore vides :", page.inner_text("#dlg-manques-resume"))
        lignes = [l.strip() for l in page.locator("#dlg-manques-liste li").all_inner_texts()]
        att("tout vide : la liste commence par les noms de thèmes", "Noms des thèmes : 1, 2, 3", lignes[0])
        att("tout vide : thèmes sans nom -> « Thème 1… »", ["Thème 1", "Thème 2", "Thème 3"], [l.split(" : ")[0] for l in lignes[2:]])
        page.click("#dlg-manques button[value=lancer]"); C.attendre_dessin(page)
        att("tout vide : la scène s'affiche, tronc = « Question T1 »", "Question T1", page.text_content("#panel .q"))
        att("tout vide : aucune étiquette de thème n'est dessinée de travers", 3, page.locator("svg text textPath").count())
        att("tout vide : aucune erreur JS", [], page.erreurs)
        page.context.close()
        nav.close()
    return echecs


if __name__ == "__main__":
    echecs = tester()
    sys.exit(0 if C.bilan("robustesse", echecs) else 1)
