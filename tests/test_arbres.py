"""Deux arbres figés : le choix d'arbre (écran de préparation), le verrouillage dès qu'on a écrit, l'éditeur piloté par la fiche
de l'arbre, la mécanique sur une autre table de votes, le téléchargement et la réouverture. Les sections 1 à 6 prouvent le MÉCANISME
sur une COPIE de test où l'on insère un arbre factice à 4 thèmes (tests/arbre_factice.js) : il reste utile pour attraper les chiffres
d'olivier écrits en dur. La section 7 fait la même chose sur le VRAI chêne de l'application (écureuil, 4 thèmes, 26 questions, 7 votes).

Usage :  .venv/bin/python tests/test_arbres.py
"""
import sys, re, json, pathlib, shutil
from playwright.sync_api import sync_playwright
import _commun as C
import fabriquer_vignette as FV

FACTICE = (C.RACINE / "tests" / "arbre_factice.js").read_text(encoding="utf-8")
DOSSIER = C.CAPTURES / "arbres"
shutil.rmtree(DOSSIER, ignore_errors=True); DOSSIER.mkdir(parents=True)


def copie_avec_factice():
    s = (C.RACINE / "index.html").read_text(encoding="utf-8")
    assert s.count('<script id="mecanique">') == 1
    f = C.CAPTURES / "avec_arbre_factice.html"
    f.write_text(s.replace('<script id="mecanique">', '<script id="dessin-factice">\n' + FACTICE + '</script>\n<script id="mecanique">', 1), encoding="utf-8")
    return f


def tester():
    echecs = []
    def att(nom, attendu, obtenu):
        if attendu != obtenu: echecs.append(f"{nom} : attendu {str(attendu)[:150]!r}, obtenu {str(obtenu)[:150]!r}")
    fac = copie_avec_factice()
    with sync_playwright() as p:
        nav = C.lancer(p)

        # ============ 1. l'application livrée : un seul arbre, l'olivier ============
        page = C.nouvelle_page(nav, "1280x720"); page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(500)
        v = page.evaluate("[...document.querySelectorAll('#choix-arbre .vignette')].map(b => [b.dataset.arbre, b.getAttribute('aria-checked'), b.getAttribute('aria-disabled'), b.querySelector('.nom').textContent, b.querySelector('.desc').textContent, b.querySelector('img') ? b.querySelector('img').naturalWidth : 0])")
        att("livré : deux vignettes, l'olivier choisi, le chêne libre, avec leurs noms", [["olivier", "true", None, "Olivier", "3 thèmes"], ["chene", "false", None, "Chêne", "4 thèmes"]], [x[:5] for x in v])
        att("livré : l'olivier a son image", 240, v[0][5])
        att("livré : phrase d'invite à choisir", "Choisis ton arbre : il fixe le nombre de thèmes.", page.inner_text("#choix-note").strip())
        att("livré : les arbres connus", ["olivier", "chene"], page.evaluate("Object.keys(DESSINS)"))
        att("livré : la fiche de l'olivier", ("olivier", 3, ["I1", "A1"], 23), tuple(page.evaluate("[FICHE.id, FICHE.themes.length, FICHE.depart, FICHE.structure.length]")))
        att("livré : aucune erreur / requête", ([], []), (page.erreurs, C.requetes_suspectes(page)))
        page.context.close()

        # ============ 2. la vignette est à jour (elle vient du vrai dessin) ============
        page = C.nouvelle_page(nav, "800x600"); page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(300)
        for arbre in ("olivier", "chene"):
          neuf = FV.fabriquer(arbre, nav)
          embarquee = page.evaluate("(id) => JSON.parse(document.getElementById('vignettes-arbres').textContent)[id]", arbre)
          ecart = page.evaluate("""async ([a, b]) => { const load = s => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = s; });
          const [A, B] = await Promise.all([load(a), load(b)]); const g = i => { const c = document.createElement('canvas'); c.width = i.width; c.height = i.height; const x = c.getContext('2d'); x.drawImage(i, 0, 0); return x.getImageData(0, 0, i.width, i.height).data; };
          if (A.width !== B.width || A.height !== B.height) return 999; const dA = g(A), dB = g(B); let s = 0; for (let i = 0; i < dA.length; i++) if (i % 4 < 3) s += Math.abs(dA[i] - dB[i]); return s / (dA.length * 3 / 4); }""", [embarquee, neuf])
          att(f"la vignette embarquée de {arbre} correspond au dessin actuel (écart moyen < 2 sur 255) : sinon lancer tests/fabriquer_vignette.py écrire", True, ecart < 2)
        page.context.close()

        # ============ 3. avec un 2e arbre (à 4 thèmes) : choix, éditeur, verrou ============
        page = C.nouvelle_page(nav, "1280x720"); page.goto(fac.as_uri()); page.wait_for_timeout(500)
        vis = lambda s: page.locator(s).is_visible()
        # (le vrai chêne a son propre test plus bas : ici on regarde le mécanisme avec l'olivier et l'arbre factice)
        etat = lambda: tuple(x for x in page.evaluate("[...document.querySelectorAll('#choix-arbre .vignette')].map(b => [b.dataset.arbre, b.getAttribute('aria-checked'), b.getAttribute('aria-disabled')])") if x[0] != "chene")
        att("2 arbres : deux vignettes, l'olivier choisi, aucune verrouillée", (("olivier", "true", None), ("chene_test", "false", None)), tuple(map(tuple, etat())))
        att("2 arbres : phrase d'invite", "Choisis ton arbre : il fixe le nombre de thèmes.", page.inner_text("#choix-note"))
        page.click("#choix-arbre .vignette[data-arbre=chene_test]")
        att("choisir le chêne de test", ("chene_test", 4), tuple(page.evaluate("[ARBRE.dessin, ARBRE.themes.length]")))
        att("le chêne de test est coché", (("olivier", "false", None), ("chene_test", "true", None)), tuple(map(tuple, etat())))
        page.click("#btn-modifier")
        att("éditeur : 'Les quatre thèmes'", True, "Les quatre thèmes" in page.inner_text("#editeur-contenu"))
        att("éditeur : rappel de l'arbre choisi", True, "Chêne (arbre de test)" in page.inner_text("#editeur-contenu"))
        att("éditeur : 4 champs de thèmes, limites de la fiche (24, 24, 20, 20)", ["24", "24", "20", "20"], [page.get_attribute(f"#f-theme-{i}", "maxlength") for i in range(4)])
        att("éditeur : libellés et exemples de la fiche", (["Thème en haut à gauche", "Thème en haut à droite", "Thème en bas à gauche", "Thème en bas à droite"], ["Ex. : Premier", "Ex. : Deuxième", "Ex. : Troisième", "Ex. : Quatrième"]),
            (page.locator("#editeur label[for^=f-theme-]").all_inner_texts(), [page.get_attribute(f"#f-theme-{i}", "placeholder") for i in range(4)]))
        att("éditeur : 1 titre + 4 thèmes + 4 tronc + 10 questions", 19, page.locator("#editeur input[type=text], #editeur textarea").count())
        att("éditeur : groupes de 3, 2, 2, 3 questions", [3, 2, 2, 3], page.evaluate("[...document.querySelectorAll('#editeur h3')].map(h => { let n=0, e=h.nextElementSibling; while(e && e.classList.contains('q-ligne')){n++; e=e.nextElementSibling;} return n; })"))
        att("éditeur : titres des groupes = libellés tant que les noms sont vides", ["Thème en haut à gauche", "Thème en haut à droite", "Thème en bas à gauche", "Thème en bas à droite"], page.locator("#editeur h3").all_inner_texts())
        att("éditeur : aucun commentaire d'orientation sous les questions (début / milieu / fin)", "", "".join(x for x in ("question ouverte", "on approfondit", "plus engagée") if x in page.inner_text("#editeur-contenu")))
        att("éditeur : limites lues dans la fiche", [24, 24, 20, 20], page.evaluate("Editeur.limites.theme"))
        # un nom trop long venu d'un brouillon ou d'un fichier retouché à la main est tronqué à la longueur de la fiche de SON arbre
        page.evaluate("ARBRE.themes.forEach(t => { t.nom = 'x'.repeat(60); })")
        att("données : noms de thèmes tronqués aux longueurs de la fiche (24, 24, 20, 20)", [24, 24, 20, 20], page.evaluate("Editeur.extraire().themes.map(t => t.nom.length)"))
        page.evaluate("ARBRE.themes.forEach(t => { t.nom = ''; })")
        # verrou : dès qu'on a écrit, l'autre arbre est grisé
        page.click("#btn-retour-prepa")
        att("rien d'écrit : le choix est libre", (None, None), tuple(x[2] for x in etat()))
        page.click("#btn-modifier"); page.fill("#f-titre", "Essai"); page.click("#btn-retour-prepa")
        att("titre écrit : l'olivier est verrouillé, le chêne reste coché", (("olivier", "false", "true"), ("chene_test", "true", None)), tuple(map(tuple, etat())))
        att("verrou : explication affichée", True, "choisi dès que tu commences à écrire" in page.inner_text("#choix-note"))
        page.click("#choix-arbre .vignette[data-arbre=olivier]", force=True)
        att("verrou : un clic sur l'autre arbre ne change rien", "chene_test", page.evaluate("ARBRE.dessin"))
        page.click("#btn-modifier"); page.fill("#f-titre", ""); page.click("#btn-retour-prepa")
        att("tout vidé : le verrou saute", (None, None), tuple(x[2] for x in etat()))
        page.click("#choix-arbre .vignette[data-arbre=olivier]")
        page.click("#btn-modifier")
        att("retour à l'olivier : le formulaire repasse à 3 thèmes (31 champs, limites 30/16/30)", (31, ["30", "16", "30"]),
            (page.locator("#editeur input[type=text], #editeur textarea").count(), [page.get_attribute(f"#f-theme-{i}", "maxlength") for i in range(3)]))
        att("aucune erreur JS (choix et verrou)", [], page.erreurs)

        # ============ 4. le chêne de test : saisie, textes manquants, lancement, parcours, aperçu ============
        page.click("#btn-retour-prepa"); page.click("#choix-arbre .vignette[data-arbre=chene_test]"); page.click("#btn-modifier")
        for i, nom in enumerate(["Alpha", "Bêta", "Gamma", "Delta"]): page.fill(f"#f-theme-{i}", nom)
        page.fill("#f-titre", "Quatre thèmes")
        for i in range(3): page.fill(f"#f-tronc-{i}", f"Tronc {i + 1}")
        for k in ["W1", "Z1", "W2", "X2", "Y2", "Z2", "W3", "X3", "Y3"]: page.fill(f"#f-q-{k}", f"Question {k} « test »")     # Z3 et T4 restent vides
        page.click("#btn-lancer-editeur"); page.wait_for_timeout(150)
        att("manquants (4 thèmes) : résumé", "2 textes sont encore vides :", page.inner_text("#dlg-manques-resume"))
        att("manquants (4 thèmes) : liste", ["Tronc : T4", "Delta : niveau 3"], [l.strip() for l in page.locator("#dlg-manques-liste li").all_inner_texts()])
        page.click("#dlg-manques button[value=completer]"); page.wait_for_timeout(100)
        att("compléter : le curseur va au premier champ vide", "f-tronc-3", page.evaluate("document.activeElement.id"))
        page.fill("#f-tronc-3", "Tronc 4"); page.fill("#f-q-Z3", "Question Z3 « test »")
        page.click("#btn-lancer-editeur"); page.wait_for_function("ecran === 'scene'"); page.wait_for_timeout(300)
        att("lancement du 2e arbre : la mécanique lit sa table (départ W1 / Z1)", (["W1", "Z1"], "trunk"), (page.evaluate("options()"), page.evaluate("mode")) if False else (page.evaluate("FICHE.depart"), page.evaluate("mode")))
        att("le dessin du 2e arbre reçoit les noms de thèmes", ["Alpha", "Bêta", "Gamma", "Delta"], page.evaluate("window.__factice.noms"))
        for _ in range(4): page.keyboard.press("ArrowRight")
        att("premier vote : les deux questions de départ de CET arbre", ["W1", "Z1"], page.evaluate("options()"))
        att("premier vote : leurs textes sur les cartes", {"Question W1 « test »", "Question Z1 « test »"}, set(page.locator("#panel .q").all_inner_texts()))
        page.keyboard.press("ArrowUp"); att("choix 1 (W1)", ["W1"], page.evaluate("path.slice()")); page.keyboard.press("ArrowRight")
        att("vote 2 : stay / change de la table de cet arbre", ["W2", "X2"], page.evaluate("options()"))
        page.keyboard.press("ArrowDown"); page.keyboard.press("ArrowRight")                     # X2
        att("vote 3 : X2 propose X3 / W3", ["X3", "W3"], page.evaluate("options()"))
        page.keyboard.press("ArrowUp"); page.keyboard.press("ArrowRight")
        att("fin de parcours après 3 votes (la table de cet arbre n'en a que 3)", ("end", ["W1", "X2", "X3"]), tuple(page.evaluate("[mode, path.slice()]")))
        att("le dessin de l'arbre a été appelé à chaque étape", True, len(page.evaluate("window.__factice.etats")) > 8)
        # retour par E, aperçu
        page.keyboard.press("e"); page.keyboard.press("o"); page.wait_for_timeout(200)
        page.click("#btn-modifier"); page.click("#f-q-Y3 >> xpath=../div[@class='pied-champ']/button"); page.wait_for_function("ecran === 'apercu'"); page.wait_for_timeout(200)
        chemin_apercu = page.evaluate("path.slice()")
        valide = chemin_apercu[0] in ("W1", "Z1") and chemin_apercu[-1] == "Y3" and all(chemin_apercu[i + 1] in (page.evaluate("(id) => [byId[id].stay, byId[id].change]", chemin_apercu[i])) for i in range(len(chemin_apercu) - 1))
        att("aperçu : un chemin VALIDE de la table de cet arbre, depuis son départ, jusqu'à Y3", True, valide)
        att("aperçu : texte exact", "Question Y3 « test »", page.text_content("#panel .q"))
        page.keyboard.press("Escape")

        # ============ 5. brouillon d'un autre arbre ============
        page.fill("#f-titre", "Brouillon du chêne"); page.wait_for_timeout(900)
        att("brouillon : enregistré avec l'arbre", "chene_test", page.evaluate("JSON.parse(localStorage.getItem('arbre-a-questions:brouillon:modele')).donnees.dessin"))
        page.reload(); page.wait_for_timeout(500)
        att("après rechargement : l'arbre revient à celui du fichier (l'olivier)", "olivier", page.evaluate("ARBRE.dessin"))
        att("après rechargement : le brouillon est proposé", True, vis("#brouillon-trouve"))
        page.click("#btn-reprendre")
        att("reprendre le brouillon reprend AUSSI son arbre", ("chene_test", 4, "Brouillon du chêne"), tuple(page.evaluate("[ARBRE.dessin, ARBRE.themes.length, ARBRE.titre]")))
        att("reprise : la vignette du chêne est cochée et l'olivier verrouillé", (("olivier", "false", "true"), ("chene_test", "true", None)), tuple(map(tuple, etat())))

        # ============ 6. téléchargement du 2e arbre, réouverture, arbre inconnu ============
        page.click("#btn-modifier")
        with page.expect_download() as dl:
            page.click("#btn-telecharger")
        chemin = DOSSIER / dl.value.suggested_filename; dl.value.save_as(chemin)
        html = chemin.read_text(encoding="utf-8")
        data = json.loads(re.search(r'id="donnees-arbre">\n(.*?)\n</script>', html, re.S).group(1))
        att("fichier du 2e arbre : arbre et thèmes", ("chene_test", ["W", "X", "Y", "Z"], ["Alpha", "Bêta", "Gamma", "Delta"]), (data["dessin"], [t["id"] for t in data["themes"]], [t["nom"] for t in data["themes"]]))
        att("fichier du 2e arbre : 10 questions de sa table", sorted(["W1", "Z1", "W2", "X2", "Y2", "Z2", "W3", "X3", "Y3", "Z3"]), sorted(data["questions"]))
        att("fichier du 2e arbre : lien, crédit et mention de licence toujours là", True, all(x in html for x in ("https://www.moodstep.com/arbre/", "mailto:arbre@moodstep.com", "CC BY-SA MOODSTEP")))
        page.context.close()

        page = C.nouvelle_page(nav, "1280x720"); page.goto(chemin.as_uri()); page.wait_for_timeout(500)
        att("réouverture : l'arbre du fichier est choisi, l'autre est verrouillé", (("olivier", "false", "true"), ("chene_test", "true", None)), tuple(map(tuple, etat())))
        page.click("#btn-modifier")
        att("réouverture : l'éditeur a 4 thèmes remplis", ["Alpha", "Bêta", "Gamma", "Delta"], [page.input_value(f"#f-theme-{i}") for i in range(4)])
        att("réouverture : titre", "Brouillon du chêne", page.input_value("#f-titre"))
        att("réouverture : aucune erreur / requête", ([], []), (page.erreurs, C.requetes_suspectes(page)))
        page.context.close()
        # le même fichier ouvert dans une application qui ne connaît pas cet arbre : repli sur l'olivier, sans planter
        sans = re.sub(r'<script id="dessin-factice">.*?</script>\n', "", html, flags=re.S); assert sans != html
        f2 = DOSSIER / "arbre_inconnu.html"; f2.write_text(sans, encoding="utf-8")
        page = C.nouvelle_page(nav, "1280x720"); page.goto(f2.as_uri()); page.wait_for_timeout(500)
        att("arbre inconnu : repli sur l'olivier, sans erreur", ("olivier", 3, []), (page.evaluate("ARBRE.dessin"), page.evaluate("ARBRE.themes.length"), page.erreurs))
        page.click("#btn-modifier")
        att("arbre inconnu : l'éditeur reste utilisable (31 champs)", 31, page.locator("#editeur input[type=text], #editeur textarea").count())
        page.context.close()
        # ============ 7. le VRAI chêne (écureuil) : choix, éditeur, lancement, parcours, téléchargement, réouverture ============
        def texte(n, graine):                                     # un texte d'exactement n caractères, fait de vrais mots
            mots = ("Comment la mer et la terre se parlent-elles quand le vent tourne sur le littoral chaque matin " + graine + " ").split()
            t = ""; i = 0
            while len(t) < n: t += mots[i % len(mots)] + " "; i += 1
            t = t[:n].rstrip()
            return t + "x" * (n - len(t))
        NOMS = [texte(m, "A")[:m] for m in (18, 22, 22, 18)]
        assert [len(x) for x in NOMS] == [18, 22, 22, 18]
        page = C.nouvelle_page(nav, "1280x720"); page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(500)
        etat7 = lambda: tuple(tuple(x) for x in page.evaluate("[...document.querySelectorAll('#choix-arbre .vignette')].map(b => [b.dataset.arbre, b.getAttribute('aria-checked'), b.getAttribute('aria-disabled')])"))
        page.click("#choix-arbre .vignette[data-arbre=chene]")
        att("chêne : choisi, 4 thèmes, 26 questions, 7 votes (lus dans sa table)", ("chene", 4, 26, 7), tuple(page.evaluate("[ARBRE.dessin, ARBRE.themes.length, FICHE.structure.length, NB_VOTES]")))
        att("chêne : départ A1 / D1", ["A1", "D1"], page.evaluate("FICHE.depart"))
        att("chêne : la vignette du chêne est cochée, rien de verrouillé", (("olivier", "false", None), ("chene", "true", None)), etat7())
        page.click("#btn-modifier")
        att("éditeur du chêne : 35 champs (titre + 4 thèmes + 4 tronc + 26 questions)", 35, page.locator("#editeur input[type=text], #editeur textarea").count())
        att("éditeur du chêne : limites des noms 18 / 22 / 22 / 18", ["18", "22", "22", "18"], [page.get_attribute(f"#f-theme-{i}", "maxlength") for i in range(4)])
        att("éditeur du chêne : limites lues dans la fiche", [18, 22, 22, 18], page.evaluate("Editeur.limites.theme"))
        att("éditeur du chêne : libellés des thèmes", ["Thème 1", "Thème 2", "Thème 3", "Thème 4"], page.locator("#editeur label[for^=f-theme-]").all_inner_texts())
        att("éditeur du chêne : 'Les quatre thèmes'", True, "Les quatre thèmes" in page.inner_text("#editeur-contenu"))
        att("éditeur du chêne : groupes de 7, 6, 6, 7 questions", [7, 6, 6, 7], page.evaluate("[...document.querySelectorAll('#editeur h3')].map(h => { let n=0, e=h.nextElementSibling; while(e && e.classList.contains('q-ligne')){n++; e=e.nextElementSibling;} return n; })"))
        att("éditeur du chêne : identifiants A1…D7, sans B1 ni C1", ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "B2", "B3", "B4", "B5", "B6", "B7", "C2", "C3", "C4", "C5", "C6", "C7", "D1", "D2", "D3", "D4", "D5", "D6", "D7"],
            page.evaluate("[...document.querySelectorAll('#editeur [id^=f-q-]')].map(e => e.id.slice(4))"))
        txt = page.inner_text("#editeur-contenu")
        att("éditeur du chêne : l'aide de chaque nom dit sa longueur (18, 22, 22, 18 lettres)", True, txt.count("18 lettres au maximum") == 2 and txt.count("22 lettres au maximum") == 2)
        att("éditeur du chêne : aucun commentaire d'orientation sous les questions", "", "".join(x for x in ("question ouverte", "on approfondit", "plus engagée") if x in page.inner_text("#editeur-contenu")))
        page.evaluate("ARBRE.themes.forEach(t => { t.nom = 'x'.repeat(60); })")
        att("données : noms de thèmes tronqués aux longueurs de la fiche du chêne", [18, 22, 22, 18], page.evaluate("Editeur.extraire().themes.map(t => t.nom.length)"))
        page.evaluate("ARBRE.themes.forEach(t => { t.nom = ''; })")
        # remplissage au maximum de tout : noms, tronc (160), questions (120)
        page.fill("#f-titre", "Le chêne et l'écureuil")
        for i, nom in enumerate(NOMS): page.fill(f"#f-theme-{i}", nom)
        for i in range(3): page.fill(f"#f-tronc-{i}", texte(160, f"T{i}"))
        QT = {}
        ids = page.evaluate("[...document.querySelectorAll('#editeur [id^=f-q-]')].map(e => e.id.slice(4))")
        for k in ids:
            if k == "D7": continue
            QT[k] = texte(120, k); page.fill(f"#f-q-{k}", QT[k])
        att("remplissage au maximum : aucune coupe (120 / 160 conservés)", (120, 160), (len(page.input_value("#f-q-A1")), len(page.input_value("#f-tronc-0"))))
        page.screenshot(path=str(DOSSIER / "editeur_chene_maximum.png"), full_page=True)                     # tout l'éditeur, de haut en bas
        page.evaluate("window.scrollTo(0, 0)"); page.set_viewport_size({"width": 1280, "height": 1500}); page.wait_for_timeout(200)
        page.screenshot(path=str(DOSSIER / "editeur_chene_maximum_haut.png"))                                # titre, 4 noms au maximum, tronc, début des questions
        page.set_viewport_size({"width": 1280, "height": 720}); page.wait_for_timeout(100)
        page.click("#btn-lancer-editeur"); page.wait_for_timeout(150)
        att("chêne, manquants : résumé", "2 textes sont encore vides :", page.inner_text("#dlg-manques-resume"))
        att("chêne, manquants : liste (tronc T4 et niveau 7 du thème 4)", ["Tronc : T4", f"{NOMS[3]} : niveau 7"], [l.strip() for l in page.locator("#dlg-manques-liste li").all_inner_texts()])
        page.click("#dlg-manques button[value=completer]"); page.wait_for_timeout(100)
        att("compléter : le curseur va au premier champ vide", "f-tronc-3", page.evaluate("document.activeElement.id"))
        TRONC3 = texte(160, "T3"); QT["D7"] = texte(120, "D7")
        page.fill("#f-tronc-3", TRONC3); page.fill("#f-q-D7", QT["D7"])
        page.click("#btn-lancer-editeur"); page.wait_for_function("ecran === 'scene'"); C.attendre_dessin(page); page.wait_for_timeout(400)
        att("lancement du chêne : au tronc, T1", ("trunk", 0, ["A1", "D1"]), tuple(page.evaluate("[mode, ti, FICHE.depart]")))
        noms_dessin = page.evaluate("[...document.querySelectorAll('#svg textPath')].map(t => t.textContent)")
        att("le dessin écrit les 4 noms, dans l'ordre des thèmes 1 → 4", NOMS, noms_dessin)
        for _ in range(4): page.keyboard.press("ArrowRight")
        att("premier vote : A1 contre D1, avec leurs textes", (["A1", "D1"], {QT["A1"], QT["D1"]}), (page.evaluate("options()"), set(page.locator("#panel .q").all_inner_texts())))
        parcours_ok = True; tailles = []
        for v in range(7):
            o = page.evaluate("options()")
            attendus = {QT[x] for x in o}
            tailles.append((len(o), attendus == set(page.locator("#panel .q").all_inner_texts())))
            page.keyboard.press("ArrowUp" if v % 2 == 0 else "ArrowDown"); page.keyboard.press("ArrowRight")
        att("sept votes au clavier : deux cartes à chaque fois, avec le bon texte", [(2, True)] * 7, tailles)
        fin = page.evaluate("[mode, path.slice()]")
        valide = fin[0] == "end" and len(fin[1]) == 7 and fin[1][0] in ("A1", "D1") and all(fin[1][i + 1] in page.evaluate("(id) => [byId[id].stay, byId[id].change]", fin[1][i]) for i in range(6))
        att("fin de parcours après 7 votes, chemin valide dans la table du chêne", True, valide)
        att("à la fin, l'arbre est affiché seul (aucune carte)", 0, page.locator("#panel .q").count())
        page.keyboard.press("ArrowLeft")
        att("retour arrière depuis la fin : on revient au 7e vote", ("choose", 6), tuple(page.evaluate("[mode, path.length]")))
        att("chêne : aucune erreur / requête pendant le parcours", ([], []), (page.erreurs, C.requetes_suspectes(page)))
        # gestes de la scène sur le chêne : remise à zéro, plein écran, curseur, retour à la préparation
        page.keyboard.press("Shift+R")
        att("chêne : Maj+R remet tout à zéro", ("trunk", 0, []), tuple(page.evaluate("[mode, ti, path.slice()]")))
        for _ in range(5): page.keyboard.press("ArrowRight")
        page.click("#rst")
        att("chêne : le bouton rond remet tout à zéro", ("trunk", 0, []), tuple(page.evaluate("[mode, ti, path.slice()]")))
        fs = "!!document.fullscreenElement"
        page.keyboard.press("f"); page.wait_for_timeout(400)
        att("chêne : F = plein écran", True, page.evaluate(fs))
        page.keyboard.press("F"); page.wait_for_timeout(400)
        att("chêne : F encore = on en sort", False, page.evaluate(fs))
        page.dblclick("#svg"); page.wait_for_timeout(400)
        att("chêne : double-clic sur l'arbre = plein écran", True, page.evaluate(fs))
        page.dblclick("#svg"); page.wait_for_timeout(400)
        att("chêne : double-clic encore = on en sort", False, page.evaluate(fs))
        page.mouse.move(100, 100); page.mouse.move(120, 120)
        att("chêne : curseur visible juste après un mouvement", "", page.evaluate("document.body.style.cursor"))
        page.wait_for_timeout(2900)
        att("chêne : curseur caché après 2,5 s", "none", page.evaluate("document.body.style.cursor"))
        # aperçu d'une question depuis l'éditeur
        page.keyboard.press("e"); page.keyboard.press("o"); page.wait_for_timeout(200)
        att("chêne : E puis confirmer = retour à la préparation", "prepa", page.evaluate("ecran"))
        page.click("#btn-modifier"); page.click("#f-q-C5 >> xpath=../div[@class='pied-champ']/button"); page.wait_for_function("ecran === 'apercu'"); page.wait_for_timeout(300)
        ch = page.evaluate("path.slice()")
        ok = ch[0] in ("A1", "D1") and ch[-1] == "C5" and all(ch[i + 1] in page.evaluate("(id) => [byId[id].stay, byId[id].change]", ch[i]) for i in range(len(ch) - 1))
        att("aperçu du chêne : un chemin valide de la table du chêne, de son départ jusqu'à C5", True, ok)
        att("aperçu du chêne : texte exact", QT["C5"], page.text_content("#panel .q"))
        page.keyboard.press("Escape")
        # brouillon puis téléchargement
        page.wait_for_timeout(900)
        att("brouillon du chêne : enregistré avec son arbre", "chene", page.evaluate("JSON.parse(localStorage.getItem('arbre-a-questions:brouillon:modele')).donnees.dessin"))
        with page.expect_download() as dl:
            page.click("#btn-telecharger")
        chemin = DOSSIER / dl.value.suggested_filename; dl.value.save_as(chemin)
        att("fichier téléchargé : nom d'après le titre", "arbre-a-questions-le-chene-et-l-ecureuil.html", chemin.name)
        html = chemin.read_text(encoding="utf-8")
        data = json.loads(re.search(r'id="donnees-arbre">\n(.*?)\n</script>', html, re.S).group(1))
        att("fichier du chêne : arbre, thèmes A–D et noms", ("chene", ["A", "B", "C", "D"], NOMS), (data["dessin"], [t["id"] for t in data["themes"]], [t["nom"] for t in data["themes"]]))
        att("fichier du chêne : 26 questions, tronc de 4 textes", (sorted(QT), 4), (sorted(data["questions"]), len([x for x in data["tronc"] if x])))
        att("fichier du chêne : les textes y sont, au caractère près", (QT, TRONC3), ({k: data["questions"][k] for k in QT}, data["tronc"][3]))
        att("fichier du chêne : lien, crédit et mention de licence « CC BY-SA MOODSTEP » présents", True, all(x in html for x in ("https://www.moodstep.com/arbre/", "mailto:arbre@moodstep.com", "CC BY-SA MOODSTEP")))
        att("fichier du chêne : le bouton de sortie (rond en haut à gauche) fait partie du fichier téléchargé", True, 'id="sortie"' in html)
        att("fichier du chêne : les deux modules d'arbre sont dans le fichier", 1, html.count('<script id="dessin-chene">') * html.count('<script id="dessin-olivier">'))
        page.context.close()

        page = C.nouvelle_page(nav, "1280x720"); page.goto(chemin.as_uri()); page.wait_for_timeout(500)
        att("réouverture du chêne : arbre choisi, l'olivier est verrouillé", (("olivier", "false", "true"), ("chene", "true", None)), etat7())
        page.click("#btn-modifier")
        att("réouverture du chêne : 4 noms, titre et une question retrouvés", (NOMS, "Le chêne et l'écureuil", QT["B4"]), ([page.input_value(f"#f-theme-{i}") for i in range(4)], page.input_value("#f-titre"), page.input_value("#f-q-B4")))
        page.click("#btn-retour-prepa"); page.click("#btn-lancer"); page.wait_for_function("ecran === 'scene'"); C.attendre_dessin(page); page.wait_for_timeout(300)
        att("réouverture du chêne : il se lance, avec les 4 noms écrits sur l'arbre", NOMS, page.evaluate("[...document.querySelectorAll('#svg textPath')].map(t => t.textContent)"))
        att("réouverture du chêne : « CC BY-SA MOODSTEP » est gravé dans le dessin", True, page.evaluate("[...document.querySelectorAll('#svg text')].some(t => t.textContent.includes('CC BY-SA MOODSTEP'))"))
        att("réouverture du chêne : aucune erreur / requête", ([], []), (page.erreurs, C.requetes_suspectes(page)))
        page.click("#sortie"); page.wait_for_timeout(150); page.click("#dlg-confirmation button[value=oui]"); page.wait_for_timeout(200)
        att("réouverture du chêne : le bouton de sortie ramène à la préparation, chêne toujours choisi (olivier verrouillé)", ("prepa", (("olivier", "false", "true"), ("chene", "true", None))), (page.evaluate("ecran"), etat7()))
        page.context.close()
        # le fichier du chêne ouvert dans une application qui ne connaît pas le chêne : repli sur l'olivier, sans planter
        sans = re.sub(r'<script id="dessin-chene">.*?</script>\n', "", html, flags=re.S); assert sans != html
        f3 = DOSSIER / "chene_inconnu.html"; f3.write_text(sans, encoding="utf-8")
        page = C.nouvelle_page(nav, "1280x720"); page.goto(f3.as_uri()); page.wait_for_timeout(500)
        att("fichier de chêne sans le module du chêne : repli sur l'olivier, sans erreur", ("olivier", 3, []), (page.evaluate("ARBRE.dessin"), page.evaluate("ARBRE.themes.length"), page.erreurs))
        page.context.close()
        nav.close()
    return echecs


if __name__ == "__main__":
    echecs = tester()
    sys.exit(0 if C.bilan("arbres (choix, verrou, éditeur piloté par la fiche, arbre factice, vrai chêne)", echecs) else 1)
