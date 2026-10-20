"""Langues : les 7 langues de l'outil (français, anglais, espagnol, allemand, italien, portugais, néerlandais).

 1. toutes les langues ont EXACTEMENT les mêmes clés, aucune valeur vide, mêmes paramètres {…}, et toute clé utilisée dans le code existe
 2. ce contrôle sait ÉCHOUER : 4 copies volontairement abîmées (clé retirée, paramètre perdu, valeur vide, clé mal écrite dans le code)
 3. une clé manquante retombe sur le français (jamais une case vide, jamais le nom technique) ; une phrase restée en français est vue
 4. choix de la langue : celle du navigateur, sélecteur sur l'écran de préparation, mémorisé, texte saisi jamais touché, touche « oui » de la langue
 5. aucun texte français visible quand une autre langue est choisie : 11 écrans (dont le mode d'emploi) x 6 langues (ce contrôle sait aussi échouer)
 6. le fichier téléchargé embarque la langue choisie (et le sélecteur) et se rouvre dans cette langue
 7. le dessin des deux arbres est identique au pixel dans les 7 langues (le témoin : le français comparé à lui-même)

Usage :  .venv/bin/python tests/test_langues.py
"""
import re, sys, json, pathlib
from playwright.sync_api import sync_playwright
import _commun as C

FICHIER = C.RACINE / "index.html"
LOCALES = {"fr": "fr-FR", "en": "en-GB", "es": "es-ES", "de": "de-DE", "it": "it-IT", "pt": "pt-PT", "nl": "nl-NL"}
DOSSIER = C.CAPTURES / "langues"; DOSSIER.mkdir(parents=True, exist_ok=True)

# Valeurs volontairement identiques au français : mots que ces langues écrivent comme nous (vérifié à la main, un par un).
# Toute AUTRE valeur identique au français est un oubli de traduction et fait échouer le test.
IDENTIQUES_LEGITIMES = {
    "en": {"scene.question", "ed.tronc.q", "touche.non", "bib.conf.1", "bib.conf.n", "bib.conf.titre", "mode.bth.vis"},      # « session » et « visible » s'écrivent pareil en anglais
    "es": {"touche.non", "mode.bth.vis"},      # « visible » aussi en espagnol
    "de": {"touche.non"},
    "it": {"touche.non", "mode.arbres.mascotte"},      # « mascotte » est un mot italien
    "pt": {"touche.non"},
    "nl": {"ed.niveau", "manques.niveau", "touche.non", "pdf.verso.niveau", "mode.arbres.mascotte"},      # « niveau » et « mascotte » aussi en néerlandais
}

JS_VISIBLES = """() => {
  const out = [], sel = document.getElementById('langue');
  for (const el of document.body.querySelectorAll('*')) {
    if (el === sel || sel.contains(el)) continue;                   // les noms de langues (Français, English…) sont écrits dans leur propre langue
    if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE') continue;
    if (el.closest('svg') && el.tagName !== 'svg') continue;       // le dessin lui-même ne contient aucun texte de l'outil (voir test 7)
    if (!el.checkVisibility({checkVisibilityCSS: true})) continue;
    for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) out.push(n.textContent.trim());
    for (const a of ['aria-label', 'placeholder', 'title', 'alt']) { const v = el.getAttribute(a); if (v) out.push(v); }
  }
  out.push(document.title);
  return out;
}"""


def lire_table(page):
    return page.evaluate("JSON.parse(JSON.stringify(TEXTES))")


def source_sans_textes(html):
    return re.sub(r'(?s)<script id="i18n">.*?</script>', '', html)


def analyser(table, html):
    """Liste des problèmes de cohérence entre les langues (vide = tout va bien)."""
    pb = []
    fr = table.get("fr", {})
    for l in LOCALES:
        if l not in table: pb.append(f"langue absente : {l}")
    for l, t in table.items():
        manque, extra = sorted(set(fr) - set(t)), sorted(set(t) - set(fr))
        if manque: pb.append(f"{l} : clés manquantes {manque[:4]}{'…' if len(manque) > 4 else ''}")
        if extra: pb.append(f"{l} : clés en trop {extra[:4]}")
        for k, v in t.items():
            if not isinstance(v, str) or not v.strip(): pb.append(f"{l}.{k} : valeur vide"); continue
            if k in fr and set(re.findall(r"\{(\w+|/b)\}", v)) != set(re.findall(r"\{(\w+|/b)\}", fr[k])):
                pb.append(f"{l}.{k} : paramètres différents du français")
            if v.count("{b}") != v.count("{/b}"): pb.append(f"{l}.{k} : gras non refermé")
    code = source_sans_textes(html)
    pour_usage = set(re.findall(r"""['"]((?:ed|prepa|dlg|scene|err|manques|touche|theme|app|apercu|langue)\.[a-z0-9.]*)['"]""", code))
    pour_usage |= set(re.findall(r'data-tx="([^"]+)"', code))
    for a in re.findall(r'data-tx-attr="([^"]+)"', code): pour_usage |= {x.split(":")[1] for x in a.split(";")}
    pour_usage |= set(re.findall(r"""\btx[r]?\('([a-z][\w.]*)'""", code))
    for k in sorted(pour_usage):
        if k.endswith("."):
            if not any(c.startswith(k) for c in fr): pb.append(f"préfixe utilisé dans le code mais inconnu : {k}")
        elif k not in fr: pb.append(f"clé utilisée dans le code mais absente du français : {k}")
    return pb


def ouvrir(nav, fichier, langue="fr", taille="1280x720", **kw):
    page = C.nouvelle_page(nav, taille, locale=LOCALES[langue], **kw)
    page.goto(pathlib.Path(fichier).resolve().as_uri()); page.wait_for_timeout(350)
    return page


def chunks_francais_seuls(table, langue):
    """Morceaux de phrases françaises qui n'existent dans AUCUN texte de la langue choisie (donc impossibles à afficher en légitime)."""
    autre = "\n".join(table[langue].values()).lower()
    res = set()
    for v in table["fr"].values():
        for ch in re.split(r"\{[^}]*\}", v):
            ch = ch.strip(" .:·«»()—-").strip()
            if len(ch) >= 5 and ch.lower() not in autre: res.add(ch)
    return res


def francais_visible(page, table, langue):
    """Texte français encore visible à l'écran (liste vide = aucun)."""
    chunks = chunks_francais_seuls(table, langue)
    trouves = []
    for s in page.evaluate(JS_VISIBLES):
        s = s.replace('arbre-a-questions-', '')           # préfixe technique des noms de fichiers (identifiant du projet), pas un texte de l'outil
        for ch in chunks:
            if ch.lower() in s.lower(): trouves.append(f"« {ch} » dans « {s[:60]} »")
    return trouves


def ecran_par_ecran(page):
    """Parcourt 11 écrans de l'outil et rend, pour chacun, (nom, page prête à être inspectée)."""
    # 1 préparation
    yield "préparation"
    # 2 bandeau « brouillon plus récent »
    page.evaluate("""() => localStorage.setItem('arbre-a-questions:brouillon:modele', JSON.stringify({modifie: new Date().toISOString(), donnees: {titre: 'x'}}))""")
    page.reload(); page.wait_for_timeout(300)
    yield "brouillon proposé"
    page.evaluate("localStorage.removeItem('arbre-a-questions:brouillon:modele')"); page.reload(); page.wait_for_timeout(300)
    # 3 éditeur olivier + message d'enregistrement
    page.click("#btn-modifier"); page.fill("#f-titre", "ZZ 12"); page.fill("#f-theme-0", "Alpha"); page.wait_for_timeout(900)
    yield "éditeur olivier"
    page.fill("#f-titre", ""); page.fill("#f-theme-0", ""); page.wait_for_timeout(700)
    # 4 fenêtre « il manque des textes »
    page.click("#btn-lancer-editeur"); page.wait_for_timeout(200)
    yield "fenêtre : textes manquants"
    # 5 scène : tronc + vote, textes vides
    page.click("#dlg-manques button[value=lancer]"); page.wait_for_selector("#screen", state="visible"); C.attendre_dessin(page); page.mouse.move(1, 1); page.wait_for_timeout(250)
    yield "scène : tronc"
    for _ in range(4): page.keyboard.press("ArrowRight"); page.wait_for_timeout(60)
    yield "scène : vote"
    # 6 fenêtre de confirmation
    page.keyboard.press("e"); page.wait_for_timeout(200)
    yield "fenêtre : retour à la préparation"
    page.keyboard.press("n"); page.wait_for_timeout(150)
    page.keyboard.press("e"); page.wait_for_timeout(150); page.click("#dlg-confirmation button[value=oui]"); page.wait_for_timeout(250)
    # 7 éditeur du chêne, aperçu, téléchargement
    page.click('.vignette[data-arbre="chene"]'); page.click("#btn-modifier")
    yield "éditeur chêne"
    page.click("#btn-telecharger"); page.wait_for_timeout(500)
    yield "message de téléchargement"
    page.locator(".q-ligne button").first.click(); page.wait_for_selector("#barre-apercu", state="visible"); page.wait_for_timeout(500)
    yield "aperçu d'une question"
    # 8 mode d'emploi (ouvert depuis l'éditeur, après avoir fermé l'aperçu)
    page.keyboard.press("Escape"); page.wait_for_timeout(200)
    page.click("#btn-aide-editeur"); page.wait_for_timeout(250)
    yield "mode d'emploi"


def tester():
    echecs = []
    def att(nom, attendu, obtenu):
        if attendu != obtenu: echecs.append(f"{nom} : attendu {str(attendu)[:200]!r}, obtenu {str(obtenu)[:200]!r}")
    html = FICHIER.read_text(encoding="utf-8")
    with sync_playwright() as p:
        nav = C.lancer(p)

        # ============ 1. mêmes clés partout ============
        page = ouvrir(nav, FICHIER)
        table = lire_table(page)
        att("langues déclarées == langues du tableau", sorted(LOCALES), sorted(table))
        att("liste affichée == langues du tableau", sorted(LOCALES), sorted(l[0] for l in page.evaluate("LANGUES_DISPONIBLES")))
        pb = analyser(table, html)
        att("1. cohérence des 7 langues", [], pb)
        att("1. nombre de clés (témoin que le contrôle lit bien quelque chose)", True, len(table["fr"]) >= 90 and all(len(t) == len(table["fr"]) for t in table.values()))
        for l in LOCALES:
            if l == "fr": continue
            ident = {k for k, v in table[l].items() if v == table["fr"][k]} - IDENTIQUES_LEGITIMES[l]
            att(f"1. {l} : aucune valeur restée identique au français", set(), ident)
        page.context.close()

        # ============ 2. le contrôle sait échouer ============
        mutants = {
            "cle_retiree": (r'  "dlg.man.titre":"Faltan textos",\n', ""),                  # une clé disparaît de l'espagnol
            "parametre_perdu": (r'"Faltam {n} textos por preencher:"', '"Faltam textos por preencher:"'),     # le portugais perd {n}
            "valeur_vide": (r'"ed.voir":"Op het podium bekijken"', '"ed.voir":""'),         # le néerlandais a une valeur vide
            "cle_mal_ecrite": (r"tx('ed.voir')", "tx('ed.voirr')"),                         # une faute de frappe dans le code
        }
        for nom, (old, new) in mutants.items():
            if old.startswith(r'  "dlg'): src = html.replace('  "dlg.man.titre":"Faltan textos",\n', "", 1)
            else: src = html.replace(old, new, 1)
            att(f"2. {nom} : la copie abîmée diffère bien de l'original", True, src != html)
            f = C.CAPTURES / f"mut_langue_{nom}.html"; f.write_text(src, encoding="utf-8")
            pm = ouvrir(nav, f); tm = lire_table(pm)
            att(f"2. {nom} : le contrôle voit le défaut", True, len(analyser(tm, src)) >= 1)
            if nom == "cle_retiree":
                # 3. repli sur le français
                pm.evaluate("localStorage.setItem('arbre-a-questions:langue','es')"); pm.reload(); pm.wait_for_timeout(300)
                pm.evaluate("Editeur.relangue ? 0 : 0")
                att("3. clé manquante en espagnol : le texte français prend le relais", "Il manque des textes", pm.evaluate("tx('dlg.man.titre')"))
                att("3. … et la case n'est pas vide", "Il manque des textes", pm.inner_text("#dlg-manques-titre") if False else pm.evaluate("document.getElementById('dlg-manques-titre').textContent"))
                att("3. … les autres textes restent en espagnol", table["es"]["prepa.lancer"], pm.inner_text("#btn-lancer"))
            if nom == "valeur_vide":
                pm.evaluate("localStorage.setItem('arbre-a-questions:langue','nl')"); pm.reload(); pm.wait_for_timeout(300)
                att("3. valeur vide en néerlandais : repli sur le français", "Voir sur scène", pm.evaluate("tx('ed.voir')"))
            pm.context.close()
        # une phrase du code qui retombe sur du français en dur est vue par le contrôle « texte français visible »
        src = html.replace("tx('ed.voir')", "'Voir sur scène'", 1); assert src != html
        f = C.CAPTURES / "mut_langue_francais_en_dur.html"; f.write_text(src, encoding="utf-8")
        pm = ouvrir(nav, f, "de"); pm.click("#btn-modifier")
        vus = francais_visible(pm, table, "de")
        att("2. un « Voir sur scène » resté en dur est vu dans l'éditeur allemand", True, any("Voir sur scène" in v for v in vus))
        pm.context.close()

        # ============ 4. choix de la langue ============
        detect = {"fr-FR": "fr", "en-US": "en", "es-MX": "es", "de-AT": "de", "it-IT": "it", "pt-BR": "pt", "nl-BE": "nl", "ja-JP": "fr", "ar-EG": "fr"}
        for loc, attendu in detect.items():
            pg = C.nouvelle_page(nav, "1280x720", locale=loc); pg.goto(FICHIER.as_uri()); pg.wait_for_timeout(300)
            att(f"4. navigateur en {loc} → {attendu}", (attendu, attendu, table[attendu]["app.titre"]), (pg.input_value("#langue") if False else pg.eval_on_selector("#langue", "e=>e.value"), pg.evaluate("document.documentElement.lang"), pg.inner_text("#prepa h1")))
            pg.context.close()
        page = ouvrir(nav, FICHIER, "fr")
        att("4. sélecteur visible sur l'écran de préparation", True, page.locator("#langue").is_visible())
        att("4. sélecteur : 7 langues, chacune dans sa propre langue", ["Français", "English", "Español", "Deutsch", "Italiano", "Português", "Nederlands"], page.locator("#langue option").all_inner_texts())
        att("4. sélecteur absent des autres écrans (éditeur)", False, (page.click("#btn-modifier"), page.locator("#langue").is_visible())[1])
        page.click("#btn-retour-prepa")
        # le texte saisi n'est jamais traduit ni perdu
        page.click("#btn-modifier"); page.fill("#f-titre", "Conférence « Été »"); page.fill("#f-theme-0", "Le travail"); page.fill("#f-tronc-0", "Pourquoi ?"); page.fill("#f-q-I1", "Une question en français ?"); page.click("#btn-retour-prepa")
        for l in ["de", "nl", "fr"]:
            page.select_option("#langue", l); page.wait_for_timeout(200)
            att(f"4. {l} : titre saisi intact sur la préparation", "Conférence « Été »", page.inner_text("#prepa-titre"))
            att(f"4. {l} : le titre de l'onglet reste le titre saisi", "Conférence « Été »", page.title())
            page.click("#btn-modifier")
            att(f"4. {l} : champs saisis intacts", ("Conférence « Été »", "Le travail", "Pourquoi ?", "Une question en français ?"),
                (page.input_value("#f-titre"), page.input_value("#f-theme-0"), page.input_value("#f-tronc-0"), page.input_value("#f-q-I1")))
            att(f"4. {l} : libellés de l'éditeur dans la langue", (table[l]["ed.h1"], table[l]["ed.titre.label"], table[l]["theme.libelle"].replace("{n}", "1"), table[l]["ed.titre.ex"]),
                (page.inner_text("#editeur h1"), page.inner_text("#editeur label[for=f-titre]"), page.inner_text("#editeur label[for=f-theme-0]"), page.get_attribute("#f-titre", "placeholder")))
            page.click("#btn-retour-prepa")
        page.select_option("#langue", "it"); page.reload(); page.wait_for_timeout(300)
        att("4. le choix est mémorisé (rechargement)", ("it", table["it"]["prepa.lancer"]), (page.eval_on_selector("#langue", "e=>e.value"), page.inner_text("#btn-lancer")))
        att("4. la clé de stockage est nouvelle et les brouillons gardent leur clé", True, page.evaluate("Object.keys(localStorage).every(k=>k==='arbre-a-questions:langue'||k.startsWith('arbre-a-questions:brouillon:'))"))
        att("4. aucune erreur JS / requête", ([], []), (page.erreurs, C.requetes_suspectes(page)))
        page.context.close()
        # la touche « oui » de la fenêtre de confirmation suit la langue
        for l in LOCALES:
            pg = ouvrir(nav, FICHIER, l); C.lancer_scene(pg)
            pg.keyboard.press("e"); pg.wait_for_timeout(150)
            att(f"4. {l} : fenêtre de confirmation en {l}", table[l]["dlg.conf.titre"], pg.inner_text("#dlg-confirmation-titre"))
            pg.keyboard.press(table[l]["touche.oui"]); pg.wait_for_timeout(250)
            att(f"4. {l} : la touche « {table[l]['touche.oui']} » ramène à la préparation", (True, False), (pg.locator("#prepa").is_visible(), pg.locator("#dlg-confirmation").evaluate("e=>e.open")))
            C.lancer_scene(pg); pg.keyboard.press("e"); pg.wait_for_timeout(150); pg.keyboard.press(table[l]["touche.non"]); pg.wait_for_timeout(250)
            att(f"4. {l} : la touche « {table[l]['touche.non']} » garde la scène", True, pg.locator("#screen").is_visible())
            pg.context.close()

        # ============ 5. aucun français visible ============
        for l in LOCALES:
            if l == "fr": continue
            pg = ouvrir(nav, FICHIER, l)
            tous = []
            for nom in ecran_par_ecran(pg):
                tous.append((nom, francais_visible(pg, table, l)))
            att(f"5. {l} : parcours complet (11 écrans vus)", 11, len(tous))
            att(f"5. {l} : aucun texte français visible", [], [(n, v) for n, v in tous if v])
            att(f"5. {l} : aucune erreur JS / requête", ([], []), (pg.erreurs, C.requetes_suspectes(pg)))
            pg.context.close()

        # ============ 6. le fichier téléchargé ============
        pg = ouvrir(nav, FICHIER, "fr"); pg.select_option("#langue", "pt"); pg.click("#btn-modifier"); pg.fill("#f-titre", "Conferência"); pg.fill("#f-theme-1", "O dia a dia")
        with pg.expect_download() as dl: pg.click("#btn-telecharger")
        chemin = DOSSIER / "telecharge_pt.html"; dl.value.save_as(chemin)
        fichier = chemin.read_text(encoding="utf-8")
        att("6. le fichier embarque la langue", True, bool(re.search(r'<html lang="pt" data-langue="pt">', fichier)))
        att("6. le fichier contient le sélecteur et le tableau des 7 langues", True, 'id="langue"' in fichier and 'id="i18n"' in fichier)
        att("6. le message de téléchargement est en portugais", True, table["pt"]["ed.msg.telecharge"].split("{")[0] in pg.inner_text("#statut"))
        pg.context.close()
        pg = ouvrir(nav, chemin, "fr")            # navigateur neuf, réglé sur le français
        att("6. rouvert dans un navigateur en français : l'outil parle portugais", ("pt", table["pt"]["prepa.lancer"], "Conferência"), (pg.eval_on_selector("#langue", "e=>e.value"), pg.inner_text("#btn-lancer"), pg.inner_text("#prepa-titre")))
        att("6. rouvert : titre de l'onglet = titre saisi", "Conferência", pg.title())
        pg.select_option("#langue", "nl")
        with pg.expect_download() as dl2: pg.click("#btn-modifier") if False else (pg.click("#btn-modifier"), pg.click("#btn-telecharger"))
        c2 = DOSSIER / "retelecharge_nl.html"; dl2.value.save_as(c2)
        att("6. on change de langue dans le fichier puis on retélécharge : la nouvelle langue est embarquée", True, '<html lang="nl" data-langue="nl">' in c2.read_text(encoding="utf-8"))
        pg.context.close()
        # fichier vierge ouvert dans un navigateur en allemand sans choix préalable : allemand
        pg = ouvrir(nav, FICHIER, "de")
        att("6. fichier vierge + navigateur allemand → allemand", table["de"]["prepa.lancer"], pg.inner_text("#btn-lancer"))
        pg.context.close()

        # ============ 7. le dessin ne bouge pas d'une langue à l'autre ============
        def empreintes(langue, arbre):
            pg = ouvrir(nav, FICHIER, langue, "1280x720")
            pg.click(f'.vignette[data-arbre="{arbre}"]')
            pg.evaluate("ARBRE.themes.forEach((t,i)=>{t.nom=['Alpha','Bêta','Gamma','Delta'][i];})")
            C.lancer_scene(pg)
            res = []
            def prendre():
                res.append((C.sha(pg.evaluate("document.getElementById('svg').innerHTML")), C.sha(str(pg.locator("#svg").screenshot().hex()))))
            prendre()
            for i in range(30):
                m = pg.evaluate("mode")
                if m == "end": break
                pg.keyboard.press("ArrowRight" if m in ("trunk", "answer") else ("j" if i % 2 else "b")); pg.wait_for_timeout(1050)       # les animaux ont des temporisations de 0,4 s + 0,6 s : on photographie quand tout est posé
                prendre()
            res.append(pg.evaluate("mode"))
            erreurs = (pg.erreurs, C.requetes_suspectes(pg)); pg.context.close()
            return res, erreurs
        for arbre in ("olivier", "chene"):
            ref, e0 = empreintes("fr", arbre)
            att(f"7. {arbre} : le parcours va jusqu'à la fin", "end", ref[-1])
            att(f"7. {arbre} : {len(ref) - 1} états comparés", True, len(ref) - 1 >= 12)
            temoin, _ = empreintes("fr", arbre)
            att(f"7. {arbre} : témoin — le français comparé à lui-même est identique (le test n'invente pas de différence)", ref, temoin)
            for l in LOCALES:
                if l == "fr": continue
                res, e = empreintes(l, arbre)
                att(f"7. {arbre} : dessin en {l} identique au français (SVG et pixels, {len(ref) - 1} états)", ref, res)
                att(f"7. {arbre} {l} : aucune erreur JS / requête", ([], []), e)
        # le test sait échouer : un seul trait déplacé change l'empreinte
        pg = ouvrir(nav, FICHIER, "fr"); C.lancer_scene(pg)
        avant = C.sha(pg.evaluate("document.getElementById('svg').innerHTML"))
        pg.evaluate("document.querySelector('#svg path').setAttribute('transform','translate(1 0)')")
        att("7. l'empreinte change si un élément du dessin bouge d'un pixel", False, avant == C.sha(pg.evaluate("document.getElementById('svg').innerHTML")))
        pg.context.close()
    return echecs


if __name__ == "__main__":
    ok = C.bilan("langues (7 langues : clés, repli, choix, aucun français visible, fichier téléchargé, dessin identique)", tester())
    sys.exit(0 if ok else 1)
