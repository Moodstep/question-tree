"""L'éditeur de bout en bout, réseau coupé : saisir -> brouillon -> télécharger -> rouvrir le fichier
téléchargé -> relancer l'édition -> lancer -> parcours complet au clavier.

Usage :  .venv/bin/python tests/test_editeur.py [fichier.html]     (par défaut : index.html)
"""
import sys, re, json, pathlib, shutil
from playwright.sync_api import sync_playwright
import _commun as C

FICHIER = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else C.RACINE / "index.html").resolve()
DOSSIER = C.CAPTURES / "telechargements"
shutil.rmtree(DOSSIER, ignore_errors=True); DOSSIER.mkdir(parents=True)

TITRE = "Conférence « Robustesse » : l'été à Lorient — 3/11"
SLUG_ATTENDU = "conference-robustesse-l-ete-a-lorient-3-11"
THEMES = ["Éducation & culture", "Mer <b>", "L'été ’ \"x\""]
PIEGES = " « Qu’est-ce que l'on pourrait changer ? » \"ok\" <b>gras</b> & ${1+1} `x` </script><img src=x onerror=alert(1)> 😀"


def texte(cle):
    return (cle + PIEGES)[:120]


def attendu():
    from_ids = [f"{t}{n}" for t, rng in (("I", range(1, 9)), ("L", range(2, 9)), ("A", range(1, 9))) for n in rng]
    return {"titre": TITRE, "themes": THEMES, "tronc": [texte(f"T{i+1}") for i in range(4)],
            "questions": {i: texte(i) for i in from_ids}}


def remplir(page, att):
    page.fill("#f-titre", att["titre"])
    for i, v in enumerate(att["themes"]): page.fill(f"#f-theme-{i}", v)
    for i, v in enumerate(att["tronc"]): page.fill(f"#f-tronc-{i}", v)
    for k, v in att["questions"].items(): page.fill(f"#f-q-{k}", v)


def donnees(page):
    return page.evaluate("Editeur.extraire()")


def lire_json_fichier(chemin):
    html = pathlib.Path(chemin).read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="donnees-arbre">\n(.*?)\n</script>', html, re.S)
    return html, json.loads(m.group(1))


def tester():
    echecs = []
    def att(nom, attendu_, obtenu):
        if attendu_ != obtenu:
            echecs.append(f"{nom} : attendu {str(attendu_)[:140]!r}, obtenu {str(obtenu)[:140]!r}")
    A = attendu()
    with sync_playwright() as p:
        nav = C.lancer(p)

        # ============ 1. structure de l'éditeur ============
        page = C.nouvelle_page(nav, "1280x720")
        page.goto(FICHIER.as_uri()); page.wait_for_timeout(400)
        page.click("#btn-modifier"); page.wait_for_timeout(100)
        vis = lambda s: page.locator(s).is_visible()
        att("éditeur visible", (True, False), (vis("#editeur"), vis("#prepa")))
        att("phrase sur la vraie sauvegarde", True, "Le téléchargement est la vraie sauvegarde" in page.inner_text("#editeur .rappel"))
        att("champs : 1 titre + 3 thèmes + 4 tronc + 23 questions", 31, page.locator("#editeur input[type=text], #editeur textarea").count())
        att("limites thèmes (30/16/30)", ["30", "16", "30"], [page.get_attribute(f"#f-theme-{i}", "maxlength") for i in range(3)])
        att("limite tronc", {"160"}, {page.get_attribute(f"#f-tronc-{i}", "maxlength") for i in range(4)})
        att("limite questions", {"120"}, {page.get_attribute(s, "maxlength") for s in [f"#f-q-{k}" for k in A["questions"]]})
        att("23 questions", 23, page.locator("#editeur [id^=f-q-]").count())
        # couleurs et niveaux conformes à la table des votes
        reel = page.evaluate("""() => D.map(d => { const l = document.getElementById('f-q-'+d.id).closest('.q-ligne');
            return [d.id, d.color, l.classList.contains(d.color), l.querySelector('.pastille').className.includes(d.color),
                    l.querySelector('.pastille').textContent, l.querySelector('.q-niveau').textContent, l.querySelector('.q-meta').textContent]; })""")
        for (i, coul, a_, b_, pastille, niveau, meta) in reel:
            n = int(i[1:])
            # la ligne ne porte que : le niveau, la couleur de vote, le repère. AUCUN commentaire sur la manière d'écrire la question (décision de Joanna, 07/10/2026).
            if not (a_ and b_ and pastille == ("Jaune" if coul == "j" else "Bleu") and niveau == f"Niveau {n}" and meta == f"Niveau {n}{pastille}repère {i}"):
                echecs.append(f"ligne {i} incohérente : {pastille}/{niveau}/{meta}")
        att("jaunes / bleus", (sum(1 for r in reel if r[1] == "j"), sum(1 for r in reel if r[1] == "b")), (12, 11))
        att("groupes (8, 7, 8 lignes)", [8, 7, 8], page.evaluate("[...document.querySelectorAll('#editeur h3')].map(h => { let n=0, e=h.nextElementSibling; while(e && e.classList.contains('q-ligne')){n++; e=e.nextElementSibling;} return n; })"))
        att("Littoral commence au niveau 2", "Niveau 2", page.evaluate("document.querySelector('#f-q-L2').closest('.q-ligne').querySelector('.q-niveau').textContent"))
        # plus aucun commentaire d'orientation sous les questions, dans aucune des 7 langues (les 21 anciennes phrases)
        ANCIENNES = ["début : question ouverte", "milieu : on approfondit", "fin : question plus engagée", "start: open question", "middle: going deeper", "end: more committed question",
                     "inicio: pregunta abierta", "mitad: se profundiza", "final: pregunta más comprometida", "Anfang: offene Frage", "Mitte: es wird vertieft", "Ende: engagiertere Frage",
                     "inizio: domanda aperta", "metà: si approfondisce", "fine: domanda più impegnata", "início: pergunta aberta", "meio: aprofunda-se", "fim: pergunta mais empenhada",
                     "begin: open vraag", "midden: we gaan dieper", "einde: meer geëngageerde vraag"]
        reste = []
        for code in ("fr", "en", "es", "de", "it", "pt", "nl"):
            page.evaluate("c => { const s = document.getElementById('langue'); s.value = c; s.dispatchEvent(new Event('change')); }", code)
            contenu_ed = page.inner_text("#editeur-contenu")
            reste += [f"{code}: {x}" for x in ANCIENNES if x in contenu_ed]
        att("aucun commentaire d'orientation sous les questions, dans les 7 langues", [], reste)
        page.evaluate("() => { const s = document.getElementById('langue'); s.value = 'fr'; s.dispatchEvent(new Event('change')); }")
        att("compteur initial", "0 / 120", page.inner_text("#f-q-I1 >> xpath=../div[@class='pied-champ']/span[contains(@class,'compteur')]"))

        # ============ 2. saisie, limites, nettoyage ============
        remplir(page, A)
        d = donnees(page)
        att("données = saisie (titre, thèmes, tronc)", (A["titre"], A["themes"], A["tronc"]), (d["titre"], [t["nom"] for t in d["themes"]], d["tronc"]))
        att("données = saisie (23 questions)", A["questions"], d["questions"])
        page.fill("#f-theme-1", "x" * 40)
        att("centre limité à 16 même par collage", 16, len(page.input_value("#f-theme-1")))
        page.fill("#f-theme-1", THEMES[1])
        page.fill("#f-q-I1", "a" * 300)
        att("question limitée à 120 par collage", 120, len(page.input_value("#f-q-I1")))
        att("compteur plein", "120 / 120", page.inner_text("#f-q-I1 >> xpath=../div[@class='pied-champ']/span[contains(@class,'compteur')]"))
        att("compteur plein : classe", True, "plein" in page.get_attribute("#f-q-I1 >> xpath=../div[@class='pied-champ']/span[contains(@class,'compteur')]", "class"))
        page.fill("#f-q-I1", ""); page.focus("#f-q-I1"); page.keyboard.type("b" * 150, delay=0)
        att("frappe limitée à 120", 120, len(page.input_value("#f-q-I1")))
        page.fill("#f-q-I1", "ligne un\nligne deux\r\n\r\nligne trois")
        att("retours à la ligne collés -> espaces", "ligne un ligne deux ligne trois", page.input_value("#f-q-I1"))
        page.fill("#f-q-I1", ""); page.focus("#f-q-I1"); page.keyboard.type("avant"); page.keyboard.press("Enter"); page.keyboard.type("après")
        att("Entrée ne crée pas de ligne", "avantaprès", page.input_value("#f-q-I1"))
        page.fill("#f-q-I1", texte("I1"))
        att("titre des groupes suit les noms de thèmes", ["Éducation & culture", "Mer <b>", "L'été ’ \"x\""], page.locator("#editeur h3").all_inner_texts())
        att("aucun HTML injecté dans l'éditeur", 0, page.locator("#editeur b, #editeur img, #editeur script").count())

        # ============ 3. brouillon automatique ============
        page.wait_for_timeout(900)
        att("message d'enregistrement", True, "Brouillon enregistré dans ce navigateur" in page.inner_text("#statut"))
        brut_ls = page.evaluate("localStorage.getItem('arbre-a-questions:brouillon:modele')")
        att("brouillon présent dans le navigateur", True, bool(brut_ls) and json.loads(brut_ls)["donnees"]["questions"]["A8"] == A["questions"]["A8"])
        page.reload(); page.wait_for_timeout(500)
        att("après rechargement : proposition de reprise", True, vis("#brouillon-trouve"))
        att("la proposition cite la date", True, "plus récent que ce fichier" in page.inner_text("#brouillon-texte"))
        page.click("#btn-ignorer")
        att("« Ignorer » masque la proposition", False, vis("#brouillon-trouve"))
        page.reload(); page.wait_for_timeout(500)
        page.click("#btn-reprendre"); page.click("#btn-modifier")
        att("« Reprendre » restaure tout", A["questions"], donnees(page)["questions"])
        att("champ restauré visible", A["questions"]["A8"], page.input_value("#f-q-A8"))
        att("titre restauré sur la préparation", TITRE, (page.click("#btn-retour-prepa"), page.inner_text("#prepa-titre"))[1])

        # ============ 4. aperçu d'une question ============
        page.click("#btn-modifier"); bouton_a3 = page.locator("#f-q-A3 >> xpath=../div[@class='pied-champ']/button")
        bouton_a3.scroll_into_view_if_needed(); page.evaluate("window.scrollBy(0, 60)"); y0 = page.evaluate("window.scrollY")
        att("l'éditeur défile (test de la position)", True, y0 > 500)
        bouton_a3.click()
        page.wait_for_selector("#screen", state="visible"); C.attendre_dessin(page); page.wait_for_timeout(150)
        att("aperçu : texte exact sur scène", A["questions"]["A3"], page.text_content("#panel .q"))
        att("aperçu : bon titre de carte", THEMES[2], page.text_content("#panel .th"))
        att("aperçu : le HTML saisi n'est pas interprété", 0, page.locator("#panel b, #panel img").count())
        att("aperçu : boutons de la scène masqués", [False] * 4, [vis("#prev"), vis("#next"), vis("#rst"), vis("#sortie")])
        att("aperçu : bouton Fermer visible", True, vis("#barre-apercu"))
        page.keyboard.press("ArrowRight"); page.keyboard.press("Backspace"); page.keyboard.press("j")
        att("aperçu : les touches de la scène sont inactives", A["questions"]["A3"], page.text_content("#panel .q"))
        page.keyboard.press("Escape"); page.wait_for_timeout(150)
        att("Échap ferme l'aperçu", (True, False), (vis("#editeur"), vis("#screen")))
        att("on retrouve sa place", True, abs(page.evaluate("window.scrollY") - y0) < 3)
        page.click("#f-q-I3 >> xpath=../div[@class='pied-champ']/button"); page.wait_for_timeout(500)
        att("aperçu tronc / niveau 3 gauche", A["questions"]["I3"], page.text_content("#panel .q"))
        page.click("#btn-fermer-apercu")
        page.click("#f-tronc-2 >> xpath=../div[@class='pied-champ']/button"); page.wait_for_timeout(500)
        att("aperçu du tronc T3", A["tronc"][2], page.text_content("#panel .q"))
        page.keyboard.press("Escape"); page.wait_for_timeout(100)

        # ============ 5. textes manquants (champ vidé) ============
        page.fill("#f-q-L5", ""); page.fill("#f-tronc-3", "")
        page.click("#btn-lancer-editeur"); page.wait_for_timeout(150)
        att("manquants : résumé", "2 textes sont encore vides :", page.inner_text("#dlg-manques-resume"))
        att("manquants : liste", ["Tronc : T4", "L'été ’ \"x\" : niveau 5".replace("L'été ’ \"x\"", "Mer <b>")], [l.strip() for l in page.locator("#dlg-manques-liste li").all_inner_texts()])
        page.click("#dlg-manques button[value=completer]"); page.wait_for_timeout(150)
        att("« Compléter » met le curseur sur le premier champ vide", "f-tronc-3", page.evaluate("document.activeElement.id"))
        page.fill("#f-q-L5", A["questions"]["L5"]); page.fill("#f-tronc-3", A["tronc"][3])

        # ============ 6. téléchargement ============
        with page.expect_download() as dl:
            page.click("#btn-telecharger")
        telecharge = dl.value
        att("nom du fichier téléchargé", f"arbre-a-questions-{SLUG_ATTENDU}.html", telecharge.suggested_filename)
        chemin1 = DOSSIER / telecharge.suggested_filename; telecharge.save_as(chemin1)
        page.wait_for_timeout(200)
        att("message de téléchargement", True, "Arbre téléchargé" in page.inner_text("#statut"))
        html1, data1 = lire_json_fichier(chemin1)
        att("fichier : données = saisie", (A["titre"], A["themes"], A["tronc"], A["questions"]),
            (data1["titre"], [t["nom"] for t in data1["themes"]], data1["tronc"], data1["questions"]))
        att("fichier : nouvel identifiant", True, data1["id"] != "modele" and len(data1["id"]) > 6)
        att("fichier : date de modification", True, bool(re.match(r"\d{4}-\d\d-\d\dT", data1.get("modifie", ""))))
        att("fichier : la mention « CC BY-SA MOODSTEP » fait partie du dessin téléchargé", True, "CC BY-SA MOODSTEP" in html1)
        att("fichier : l'encadré de l'éditeur n'est pas animé comme une note de musique", 0, page.locator("#editeur .rappel.note, #editeur .note").count())
        att("fichier : lien « nouvelles options »", True, 'href="https://www.moodstep.com/arbre/"' in html1)
        att("fichier : lien Moodstep et mailto dans le crédit", True, 'href="https://www.moodstep.com/"' in html1 and 'href="mailto:arbre@moodstep.com"' in html1)
        compter = lambda h: len(re.findall(r"<script\b[^>]*>", re.sub(r"(?s)<script.*?</script>", lambda m: m.group(0)[:80] + "</script>", h)))
        att("fichier : aucun bloc de code ajouté ni retiré (autant que dans le fichier de départ)", compter(FICHIER.read_text(encoding="utf-8")), compter(html1))
        entete = re.search(r"(?s)<head>.*?</head>", html1).group(0)
        att("fichier : <title> de l'en-tête unique et échappé", True, entete.count("<title>") == 1 and "<title>Conférence « Robustesse » : l&#39;été à Lorient — 3/11</title>" in entete)
        att("fichier : aucun '<' brut dans les données", True, "<" not in re.search(r'(?s)id="donnees-arbre">(.*?)</script>', html1).group(1))
        att("modèle vierge : brouillon 'modele' effacé", None, page.evaluate("localStorage.getItem('arbre-a-questions:brouillon:modele')"))
        att("nouveau brouillon rattaché à l'identifiant du fichier", True, bool(page.evaluate(f"localStorage.getItem('arbre-a-questions:brouillon:{data1['id']}')")))
        att("aucune erreur JS / requête (session 1)", ([], []), (page.erreurs, C.requetes_suspectes(page)))
        page.context.close()

        # ============ 7. on rouvre le fichier téléchargé, dans un navigateur neuf ============
        page = C.nouvelle_page(nav, "1920x1080")
        page.goto(chemin1.as_uri()); page.wait_for_timeout(500)
        vis = lambda s: page.locator(s).is_visible()
        att("fichier rouvert : titre sur la préparation", TITRE, page.inner_text("#prepa-titre"))
        att("fichier rouvert : titre de l'onglet", TITRE, page.title())
        att("fichier rouvert : crédit présent", "L'Arbre à questions, conçu par Moodstep · arbre@moodstep.com", page.inner_text("#credit"))
        att("fichier rouvert : lien nouveautés présent", "https://www.moodstep.com/arbre/", page.get_attribute("#nouveautes a", "href"))
        att("fichier rouvert : pas de brouillon proposé (navigateur neuf)", False, vis("#brouillon-trouve"))
        page.click("#btn-modifier")
        att("fichier rouvert : réédition, tout est là", (A["titre"], A["themes"], A["tronc"], A["questions"]),
            (page.input_value("#f-titre"), [page.input_value(f"#f-theme-{i}") for i in range(3)], [page.input_value(f"#f-tronc-{i}") for i in range(4)], {k: page.input_value(f"#f-q-{k}") for k in A["questions"]}))
        # modifier puis retélécharger : le fichier réédité porte le même identifiant
        page.fill("#f-q-I2", "Version éditée de I2 — l'été")
        with page.expect_download() as dl2:
            page.click("#btn-telecharger")
        chemin2 = DOSSIER / ("reedite_" + dl2.value.suggested_filename); dl2.value.save_as(chemin2)
        _, data2 = lire_json_fichier(chemin2)
        att("réédition : même identifiant", data1["id"], data2["id"])
        att("réédition : la modification est dans le fichier", "Version éditée de I2 — l'été", data2["questions"]["I2"])
        att("réédition : le reste est intact", {k: v for k, v in A["questions"].items() if k != "I2"}, {k: v for k, v in data2["questions"].items() if k != "I2"})
        page.fill("#f-q-I2", A["questions"]["I2"])
        # idempotence : télécharger sans rien changer redonne le même fichier (à la date près)
        with page.expect_download() as dl3:
            page.click("#btn-telecharger")
        chemin3 = DOSSIER / ("idem_" + dl3.value.suggested_filename); dl3.value.save_as(chemin3)
        norm = lambda t: re.sub(r'"modifie": "[^"]+"', '"modifie": "X"', t)
        att("retélécharger sans modifier = même fichier (hors date)", norm(html1) == norm(chemin3.read_text(encoding="utf-8")), True)
        att("fichier réédité : même taille qu'au départ (± 0)", len(norm(html1)), len(norm(chemin3.read_text(encoding="utf-8"))))
        att("aucune erreur JS / requête (session 2)", ([], []), (page.erreurs, C.requetes_suspectes(page)))

        # ============ 8. lancement et parcours complet au clavier ============
        page.click("#btn-retour-prepa"); page.click("#btn-lancer")
        page.wait_for_selector("#screen", state="visible"); C.attendre_dessin(page)
        att("données complètes : pas de message de manquants", False, vis("#dlg-manques"))
        att("scène du fichier rouvert : mention de licence gravée dans le dessin", 2, page.locator("#svg text", has_text="CC BY-SA MOODSTEP").count())
        att("scène du fichier rouvert : la mésange est là", 1, page.locator("#svg .bird").count())
        att("tronc T1 sur scène", A["tronc"][0], page.text_content("#panel .q"))
        for i in range(1, 4):
            page.keyboard.press("ArrowRight"); att(f"tronc T{i+1}", A["tronc"][i], page.text_content("#panel .q"))
        page.keyboard.press("ArrowRight")
        cartes = page.locator("#panel button.card")
        att("premier vote : deux cartes", 2, cartes.count())
        att("noms de thèmes sur les cartes", [THEMES[0], THEMES[2]], page.locator("#panel .th").all_inner_texts())
        att("premier vote : les deux textes", {A["questions"]["I1"], A["questions"]["A1"]}, set(page.locator("#panel .q").all_inner_texts()))
        for v in range(8):
            page.keyboard.press("ArrowUp" if v % 2 == 0 else "ArrowDown"); page.wait_for_timeout(40)
            ident = page.evaluate("path[path.length-1]")
            att(f"vote {v+1} ({ident}) : texte exact", A["questions"][ident], page.text_content("#panel .q"))
            att(f"vote {v+1} : rien d'interprété", 0, page.locator("#panel b, #panel img, #panel script").count())
            page.keyboard.press("ArrowRight"); page.wait_for_timeout(40)
        att("fin de parcours", ("end", 8), tuple(page.evaluate("[mode, path.length]")))
        att("aucune erreur JS / requête (session 3, parcours)", ([], []), (page.erreurs, C.requetes_suspectes(page)))
        nav.close()
    return echecs


if __name__ == "__main__":
    echecs = tester()
    sys.exit(0 if C.bilan(f"éditeur de bout en bout ({FICHIER.name})", echecs) else 1)
