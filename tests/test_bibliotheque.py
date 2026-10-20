"""« Mes arbres » : la mémoire des parcours, leur enregistrement à l'arrivée au tableau final, la liste, l'ouverture d'un fichier.

 A. La logique seule (sans écran) : un parcours venu de la mémoire ou d'un fichier est vérifié ; fusion sans doublon ; liste des arbres ;
    migration de l'id « modele » ; mémoire du navigateur en panne.
 B. L'enregistrement : rien avant le tableau final, rien en aperçu, UN parcours par conférence (revenir en arrière puis finir autrement le met à jour,
    Maj+R en commence un autre), les questions subsidiaires y sont, la copie des textes ne bouge plus quand l'arbre est modifié.
 C. L'éditeur : le fichier téléchargé porte les parcours (et rien quand il n'y en a pas), le premier téléchargement d'un arbre « modele » déplace ses parcours.
 D. La liste à l'écran (préparation) : lignes, pastille « à télécharger », ouvrir, télécharger, retirer, nommer, supprimer, titre piégé, 7 langues.
 E. « Ouvrir un arbre » : fichiers valides, refus clairs, fichiers hostiles, conflit, doublons.

Usage :  .venv/bin/python tests/test_bibliotheque.py
"""
import os, re, sys, json, pathlib, shutil, hashlib
from playwright.sync_api import sync_playwright
import _commun as C
from _mes_arbres import (FICHIER, CHEMINS_JS, FABRIQUE_JS, Bilan, ouvrir, HORLOGE, HASARD, CHOIX, AUTRE, touche, jouer, parcours_ici, preparer)

TMP = C.CAPTURES / "bibliotheque"
shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir(parents=True)
ORIGINAL_3_NOV = pathlib.Path.home() / "Downloads" / "arbre-a-questions-autonome.html"
SHA_3_NOV = "f3d46e5b"

def brouillon(page, id_, titre="Un arbre", dessin="olivier", modifie="2026-10-06T09:00:00.000Z"):
    """Dépose un brouillon dans la mémoire du navigateur de la page (comme le ferait l'éditeur)."""
    page.evaluate("""([id, titre, dessin, modifie]) => localStorage.setItem('arbre-a-questions:brouillon:' + id,
        JSON.stringify({modifie, donnees: Editeur.nettoyer({id, titre, dessin})}))""", [id_, titre, dessin, modifie])


# ====================================================================== A
def section_A(nav, b):
    page = ouvrir(nav)
    olivier = page.evaluate(CHEMINS_JS, "olivier"); chene = page.evaluate(CHEMINS_JS, "chene")
    b.att("A : 256 parcours d'olivier", 256, len(olivier)); b.att("A : 128 parcours de chêne", 128, len(chene))

    def fab(dessin, path, **extra): return page.evaluate(FABRIQUE_JS, [dessin, path, extra or None])
    def net(p): return page.evaluate("p => Bibliotheque.nettoyerParcours(p)", p)

    ok = fab("olivier", olivier[37]); r = net(ok)
    b.vrai("A : un parcours valide d'olivier est gardé", r is not None and r["path"] == ok["path"] and r["id"] == ok["id"] and r["copie"]["dessin"] == "olivier")
    ok2 = fab("chene", chene[90], subs=[])
    b.vrai("A : un parcours valide de chêne est gardé", net(ok2) is not None)
    b.att("A : le nom est borné à 60 caractères", 60, len(net(fab("olivier", olivier[5], nom="x" * 400))["nom"]))
    b.att("A : le nom perd ses retours à la ligne", "a b", net(fab("olivier", olivier[5], nom=" a\n\nb "))["nom"])

    # refus : chaque cas est un parcours abîmé d'UNE seule façon
    p = olivier[10]
    refus = {
        "dessin inconnu": fab("olivier", p, copie=None),
        "id de question inconnu": fab("olivier", p[:-1] + ["Z99"]),
        "ne suit pas les liens": None,
        "parcours non terminé": fab("olivier", p[:-1]),
        "date non ISO": fab("olivier", p, debut="hier"),
        "id de parcours piégé": fab("olivier", p, id="<img src=x>"),
        "sub déjà dans le parcours": fab("olivier", p, subs=[p[1]]),
        "sub en double": fab("olivier", p, subs=["I3", "I3"]),
    }
    # « ne suit pas les liens » : UNE seule anomalie : la 3e question est remplacée par une question qui existe mais n'est pas voisine de la 2e
    q = page.evaluate("""p => { const par = {}; DESSINS.olivier.structure.forEach(d => par[d.id] = d); const v = par[p[1]];
        return DESSINS.olivier.structure.map(d => d.id).find(i => i !== v.stay && i !== v.change && !p.includes(i)); }""", p)
    refus["ne suit pas les liens"] = fab("olivier", p[:2] + [q] + p[3:])
    refus["dessin inconnu"]["copie"] = {"dessin": "sapin", "titre": "", "themes": [], "tronc": [], "questions": {}}
    for nom, par in refus.items():
        b.att(f"A : refusé — {nom}", None, net(par))
    b.att("A : refusé — n'importe quoi", [None, None, None], [net(x) for x in (None, "texte", 12)])

    # fusion : sans doublon, parcours invalide écarté et compté
    a, c, d_ = fab("olivier", olivier[1]), fab("olivier", olivier[2]), fab("olivier", olivier[3])
    mauvais = fab("olivier", olivier[4], debut="x")
    r1 = page.evaluate("([id, l]) => Bibliotheque.fusionner(id, l)", ["arbre1", [a, c, mauvais]])
    b.att("A : fusion de 3 dont 1 invalide", {"ajoutes": 2, "ecartes": 1}, r1)
    r2 = page.evaluate("([id, l]) => Bibliotheque.fusionner(id, l)", ["arbre1", [a, c]])
    b.att("A : la même fusion une 2e fois n'ajoute rien", 0, r2["ajoutes"])
    b.att("A : 2 parcours en mémoire", 2, len(page.evaluate("Bibliotheque.parcoursDe('arbre1')")))
    r3 = page.evaluate("([id, l]) => Bibliotheque.fusionner(id, l)", ["arbre1", [dict(a, fin="2026-10-08T10:00:00.000Z"), d_]])
    b.att("A : un parcours de même id plus récent le remplace, un nouveau s'ajoute", 3, len(page.evaluate("Bibliotheque.parcoursDe('arbre1')")))
    b.att("A : …et c'est bien la version récente", "2026-10-08T10:00:00.000Z",
          [x for x in page.evaluate("Bibliotheque.parcoursDe('arbre1')") if x["id"] == a["id"]][0]["fin"])

    # liste des arbres
    brouillon(page, "arbre1", "Premier", modifie="2026-10-01T09:00:00.000Z")
    brouillon(page, "arbre2", "Deuxième", "chene", modifie="2026-10-05T09:00:00.000Z")
    brouillon(page, "vide", "", modifie="2026-10-09T09:00:00.000Z")           # aucun champ rempli : pas listé
    page.evaluate("localStorage.setItem('arbre-a-questions:brouillon:vide', JSON.stringify({modifie:'2026-10-09T09:00:00.000Z', donnees: Editeur.nettoyer({id:'vide'})}))")
    page.evaluate("([id, l]) => Bibliotheque.fusionner(id, l)", ["seulement-parcours", [fab("chene", chene[3])]])
    e = page.evaluate("Bibliotheque.entrees().map(x => [x.id, x.donnees.dessin, x.donnees.titre, x.parcours.length, x.aTelecharger])")
    ids = [x[0] for x in e]
    b.vrai("A : liste sans l'arbre vide", "vide" not in ids, str(ids))
    b.vrai("A : liste avec arbre1, arbre2 et celui qui n'a que des parcours", {"arbre1", "arbre2", "seulement-parcours"} <= set(ids), str(ids))
    b.att("A : l'arbre qui n'a que des parcours est reconstitué depuis la copie (chêne)", "chene", [x for x in e if x[0] == "seulement-parcours"][0][1])
    b.vrai("A : tout est « à télécharger » tant que rien n'a été téléchargé", all(x[4] for x in e), str(e))
    page.evaluate("Bibliotheque.marquerTelecharge('arbre2', '2026-10-06T00:00:00.000Z')")
    b.att("A : arbre2 modifié avant son téléchargement n'est plus à télécharger", False,
          page.evaluate("Bibliotheque.entrees().find(x => x.id === 'arbre2').aTelecharger"))
    page.evaluate("Bibliotheque.marquerTelecharge('arbre2', '2026-10-04T00:00:00.000Z')")
    b.att("A : …et l'est de nouveau si le téléchargement est plus ancien que la modification", True,
          page.evaluate("Bibliotheque.entrees().find(x => x.id === 'arbre2').aTelecharger"))

    # migration de « modele »
    brouillon(page, "modele", "Pas encore téléchargé")
    page.evaluate("([id, l]) => Bibliotheque.fusionner(id, l)", ["modele", [fab("olivier", olivier[8])]])
    page.evaluate("Bibliotheque.migrer('modele', 'vraiid')")
    cles = page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('arbre-a-questions:')).sort()")
    b.vrai("A : migrer déplace brouillon et parcours", "arbre-a-questions:parcours:vraiid" in cles and "arbre-a-questions:parcours:modele" not in cles
           and "arbre-a-questions:brouillon:modele" not in cles, str(cles))
    b.att("A : le parcours migré est lisible sous le nouvel id", 1, len(page.evaluate("Bibliotheque.parcoursDe('vraiid')")))

    # nommer, supprimer, retirer
    pid = page.evaluate("Bibliotheque.parcoursDe('arbre1')[0].id")
    page.evaluate("([i, p]) => Bibliotheque.nommer(i, p, 'Lorient, 3 nov.')", ["arbre1", pid])
    b.att("A : nommer un parcours", "Lorient, 3 nov.", [x for x in page.evaluate("Bibliotheque.parcoursDe('arbre1')") if x["id"] == pid][0]["nom"])
    page.evaluate("([i, p]) => Bibliotheque.supprimerParcours(i, p)", ["arbre1", pid])
    b.att("A : supprimer un parcours", 2, len(page.evaluate("Bibliotheque.parcoursDe('arbre1')")))
    page.evaluate("Bibliotheque.marquerTelecharge('arbre1', '2026-10-01T00:00:00.000Z')")
    avant = sorted(k for k in page.evaluate("Object.keys(localStorage)") if k.endswith(":arbre1"))
    b.att("A : arbre1 a bien ses trois clés avant d'être retiré", 3, len(avant))
    page.evaluate("Bibliotheque.retirer('arbre1')")
    b.vrai("A : retirer efface les trois clés", not [k for k in page.evaluate("Object.keys(localStorage)") if k.endswith(":arbre1")])
    page.context.close()

    # mémoire du navigateur en panne : rien ne casse, le parcours reste visible pendant la session
    page = ouvrir(nav)
    page.evaluate("() => { Storage.prototype.setItem = function () { throw new DOMException('plein', 'QuotaExceededError'); }; }")
    olivier = page.evaluate(CHEMINS_JS, "olivier")
    sortie = page.evaluate("""([l]) => { try { const r = Bibliotheque.fusionner('panne', l); return {r, n: Bibliotheque.parcoursDe('panne').length}; } catch (e) { return {erreur: String(e)}; } }""",
                           [[page.evaluate(FABRIQUE_JS, ["olivier", olivier[0], None])]])
    b.vrai("A : mémoire en panne, pas d'exception", "erreur" not in sortie, str(sortie))
    b.att("A : mémoire en panne, le parcours reste lisible", 1, sortie.get("n"))
    b.vrai("A : aucune erreur de page", not page.erreurs, str(page.erreurs))
    page.context.close()

# ====================================================================== B
def section_B(nav, b):
    page = preparer(nav)
    # 1. rien tant qu'on n'est pas au tableau final
    nb = []
    for _ in range(4): touche(page, "ArrowRight"); nb.append(len(parcours_ici(page)))
    for i, c in enumerate(CHOIX):
        touche(page, c); nb.append(len(parcours_ici(page)))
        if i < len(CHOIX) - 1: touche(page, "ArrowRight"); nb.append(len(parcours_ici(page)))
    b.att("B : aucun parcours gardé avant le tableau final", [0] * len(nb), nb)
    touche(page, "ArrowRight")
    # 2. à l'arrivée : un parcours, qui est bien celui de la page
    l = parcours_ici(page)
    b.att("B : un parcours à l'arrivée au tableau final", 1, len(l))
    chemin = page.evaluate("path.slice()")
    b.att("B : son chemin est celui de la page", chemin, l[0]["path"] if l else None)
    b.att("B : sans subsidiaire", [], l[0]["subs"] if l else None)
    b.att("B : copie du titre", "Conférence d'essai", l[0]["copie"]["titre"] if l else None)
    b.att("B : copie d'une question écrite", "Première question écrite", l[0]["copie"]["questions"]["I1"] if l else None)
    b.vrai("B : début et fin en dates ISO, début <= fin", l and l[0]["debut"] <= l[0]["fin"])
    pid = l[0]["id"] if l else None
    # 3. retour arrière, autre choix, retour au tableau final : le MÊME parcours est mis à jour
    touche(page, "ArrowLeft")
    b.att("B : revenir en arrière ne crée rien", 1, len(parcours_ici(page)))
    touche(page, AUTRE[CHOIX[-1]]); touche(page, "ArrowRight")
    l2 = parcours_ici(page)
    b.att("B : après un autre choix, toujours un seul parcours", 1, len(l2))
    b.att("B : …le même (même id)", pid, l2[0]["id"] if l2 else None)
    b.att("B : …avec le nouveau chemin", page.evaluate("path.slice()"), l2[0]["path"] if l2 else None)
    b.vrai("B : …et ce chemin a bien changé", l2 and l2[0]["path"] != chemin)
    # 4. Maj+R : une autre conférence
    touche(page, "Shift+R"); jouer(page)
    l3 = parcours_ici(page)
    b.att("B : après Maj+R puis un parcours complet : 2 sessions", 2, len(l3))
    b.att("B : …d'id différents", 2, len({x["id"] for x in l3}))
    # 5. questions subsidiaires
    touche(page, "Shift+R"); jouer(page, fin=False)
    for _ in range(3): touche(page, "=")
    subs = page.evaluate("subs.slice()")
    b.att("B : trois subsidiaires tirées", 3, len(subs))
    touche(page, "Enter")
    l4 = parcours_ici(page)
    b.att("B : 3 sessions", 3, len(l4))
    b.att("B : les subsidiaires sont dans le parcours, dans l'ordre", subs, sorted(l4, key=lambda x: x["fin"])[-1]["subs"] if l4 else None)
    # 6. texte de la boîte de retour
    touche(page, "e")
    b.vrai("B : depuis le tableau final, la boîte dit que le parcours est gardé", "gardé" in page.inner_text("#dlg-confirmation"), page.inner_text("#dlg-confirmation"))
    touche(page, "n")
    touche(page, "ArrowLeft"); touche(page, "ArrowLeft")      # on remonte dans le vote
    touche(page, "e")
    b.vrai("B : en plein vote, la boîte garde le texte d'origine", "sera perdu" in page.inner_text("#dlg-confirmation"), page.inner_text("#dlg-confirmation"))
    touche(page, "n")
    # 7. la copie ne bouge plus quand l'arbre est modifié
    touche(page, "e"); touche(page, "o")
    b.vrai("B : en quittant la scène après une session complète, le bandeau « Session enregistrée » est sur l'accueil", page.locator("#session-enregistree").is_visible() and "Session enregistrée" in page.inner_text("#session-enregistree"), page.inner_text("#prepa")[:200])
    with page.expect_download(timeout=60000) as dl:
        page.click("#btn-fin-pdf")
    b.vrai("B : …son bouton donne le PDF", dl.value.suggested_filename.endswith(".pdf"), dl.value.suggested_filename)
    page.wait_for_timeout(300)
    b.vrai("B : …et la confirmation s'affiche dans le bandeau lui-même", "PDF téléchargé" in page.inner_text("#session-enregistree"), page.inner_text("#session-enregistree"))
    page.click("#btn-fin-fermer"); page.wait_for_timeout(100)
    b.vrai("B : « Fermer » fait disparaître le bandeau", not page.locator("#session-enregistree").is_visible())
    C.lancer_scene(page); touche(page, "ArrowRight"); touche(page, "ArrowRight"); touche(page, "e"); touche(page, "o")
    b.vrai("B : quitter en plein tronc n'annonce aucune session", not page.locator("#session-enregistree").is_visible())
    C.lancer_scene(page); jouer(page); touche(page, "e"); touche(page, "o")
    b.vrai("B : une nouvelle session complète est de nouveau annoncée", page.locator("#session-enregistree").is_visible())
    C.lancer_scene(page); touche(page, "e"); touche(page, "o")
    b.vrai("B : relancer puis quitter tout de suite efface l'annonce précédente (rien de nouveau n'a été joué)", not page.locator("#session-enregistree").is_visible())
    page.click("#btn-modifier"); page.wait_for_timeout(100)
    page.fill("#f-q-I1", "Question réécrite après coup"); page.wait_for_timeout(700)
    anciens = parcours_ici(page)
    b.att("B : la copie de chaque session garde le texte d'origine", {"Première question écrite"}, {x["copie"]["questions"]["I1"] for x in anciens})
    b.att("B : …alors que l'arbre, lui, a changé", "Question réécrite après coup", page.evaluate("ARBRE.questions.I1"))
    # 8. l'aperçu d'une question de l'éditeur n'enregistre rien
    n_avant = len(parcours_ici(page))
    page.locator("#editeur .q-ligne button", has_text="Voir").first.click(); page.wait_for_timeout(500)
    touche(page, "Escape"); page.wait_for_timeout(200)
    b.att("B : l'aperçu n'enregistre rien", n_avant, len(parcours_ici(page)))
    b.vrai("B : aucune erreur de page", not page.erreurs, str(page.erreurs))
    b.vrai("B : aucune requête réseau", not C.requetes_suspectes(page), str(C.requetes_suspectes(page)))
    page.context.close()

# ====================================================================== C
def donnees_du_fichier(chemin):
    html = pathlib.Path(chemin).read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="donnees-arbre">\n(.*?)\n</script>', html, re.S)
    return json.loads(m.group(1))


def telecharger_arbre(page, nom):
    chemin = TMP / nom
    with page.expect_download() as d:
        page.click("#btn-telecharger")
    d.value.save_as(str(chemin)); page.wait_for_timeout(200)
    return chemin


def section_C(nav, b):
    # (a) un arbre sans conférence : le fichier ne porte AUCUN champ « parcours »
    page = ouvrir(nav, init_script=HORLOGE)
    page.click("#btn-modifier"); page.fill("#f-titre", "Sans conférence"); page.fill("#f-q-I1", "Une question")
    f = telecharger_arbre(page, "c_sans.html")
    d = donnees_du_fichier(f)
    b.vrai("C : pas de champ parcours quand il n'y a rien à garder", "parcours" not in d, str(list(d)))
    b.vrai("C : l'arbre a reçu un vrai identifiant", page.evaluate("ARBRE.id") != "modele")
    e = page.evaluate("Bibliotheque.entrees().map(x => [x.id, x.aTelecharger])")
    b.att("C : juste après le téléchargement, l'arbre n'est plus « à télécharger »", [[page.evaluate("ARBRE.id"), False]], e)
    page.context.close()

    # (b) + (c) deux sessions jouées sous l'id « modele », puis le premier téléchargement
    page = preparer(nav)
    jouer(page); touche(page, "Shift+R"); jouer(page)
    b.att("C : deux sessions sous « modele »", 2, len(page.evaluate("Bibliotheque.parcoursDe('modele')")))
    touche(page, "e"); touche(page, "o"); page.click("#btn-modifier"); page.wait_for_timeout(100)
    f = telecharger_arbre(page, "c_avec.html")
    nouvel = page.evaluate("ARBRE.id")
    b.vrai("C : l'id n'est plus « modele »", nouvel != "modele", nouvel)
    d = donnees_du_fichier(f)
    b.att("C : le fichier porte les 2 sessions", 2, len(d.get("parcours", [])))
    b.att("C : …et son id est le nouvel id", nouvel, d["id"])
    cles = sorted(k for k in page.evaluate("Object.keys(localStorage)") if k.startswith("arbre-a-questions:") and not k.endswith(":langue"))
    b.vrai("C : plus rien sous « modele »", not [k for k in cles if k.endswith(":modele")], str(cles))
    b.att("C : les 2 sessions ont suivi sous le nouvel id", 2, len(page.evaluate("Bibliotheque.parcoursDe(ARBRE.id)")))
    b.vrai("C : la marque de téléchargement existe sous le nouvel id", "arbre-a-questions:telecharge:" + nouvel in cles, str(cles))
    page.context.close()

    # le fichier, ouvert directement dans un navigateur vierge : ses sessions sont retrouvées
    page = C.nouvelle_page(nav, "1280x720")
    page.goto(f.as_uri()); page.wait_for_timeout(500)
    b.att("C : fichier ouvert dans un navigateur vierge : 2 sessions retrouvées", 2, len(page.evaluate("Bibliotheque.parcoursDe(ARBRE.id)")))
    b.att("C : …et sans champ parcours résiduel dans les données de la page", False, page.evaluate("'parcours' in ARBRE"))
    # …et un 2e téléchargement n'en perd aucune
    page.click("#btn-modifier"); page.fill("#f-titre", "Modifié après coup")
    f2 = telecharger_arbre(page, "c_deuxieme.html")
    b.att("C : un 2e téléchargement garde les 2 sessions", 2, len(donnees_du_fichier(f2).get("parcours", [])))
    page.context.close()

    # (d) Editeur.charger : un chêne dans un olivier
    page = ouvrir(nav)
    page.click("#btn-modifier"); page.fill("#f-titre", "Mon olivier"); page.wait_for_timeout(700)
    avant = page.evaluate("localStorage.getItem('arbre-a-questions:brouillon:modele')")
    chene = {"id": "autre1", "titre": "Mon chêne", "dessin": "chene", "themes": [{"id": t, "nom": "Thème " + t} for t in "ABCD"],
             "tronc": ["a", "b", "c", "d"], "questions": {"A1": "Une question du chêne"}}
    page.evaluate("d => Editeur.charger(d, {modifie: '2026-10-03T08:00:00.000Z'})", chene)
    b.att("C : charger installe le chêne", ("chene", "autre1", "2026-10-03T08:00:00.000Z"), tuple(page.evaluate("[ARBRE.dessin, ARBRE.id, ARBRE.modifie]")))
    b.att("C : le titre est repris", "Mon chêne", page.evaluate("ARBRE.titre"))
    b.att("C : 4 thèmes dans l'éditeur", 4, page.locator("[id^=f-theme-]").count())
    b.att("C : la question du chêne est dans son champ", "Une question du chêne", page.input_value("#f-q-A1"))
    b.att("C : le brouillon de l'olivier quitté est intact", avant, page.evaluate("localStorage.getItem('arbre-a-questions:brouillon:modele')"))
    page.click("#btn-retour-prepa"); page.wait_for_timeout(100)
    C.lancer_scene(page)
    b.att("C : la scène lancée est celle du chêne", True, page.evaluate("DESSINS.chene.id === FICHE.id && !!document.querySelector('#svg image')"))
    b.vrai("C : aucune erreur de page", not page.erreurs, str(page.erreurs))
    page.context.close()

# ====================================================================== D
PIEGE = '<img src=x onerror="window.__pwn=1"> </script><b>gras</b> & "guillemets"'


def parcours_pour(page, dessin, n, debut="2026-10-07T10:00:00.000Z"):
    chemins = page.evaluate(CHEMINS_JS, dessin)
    out = []
    for i in range(n):
        p = page.evaluate(FABRIQUE_JS, [dessin, chemins[17 * (i + 1)], {"fin": f"2026-10-0{5 + i}T1{i}:30:00.000Z", "debut": f"2026-10-0{5 + i}T1{i}:00:00.000Z"}])
        out.append(p)
    return out


def lignes(page):
    return page.evaluate("[...document.querySelectorAll('#liste-arbres > li.arbre-ligne')].map(l => ({id: l.dataset.id, texte: l.innerText.replace(/\\s+/g, ' '), actes: [...l.querySelectorAll('.arbre-actions button')].map(b => b.dataset.act)}))")


def section_D(nav, b):
    # état vide
    page = ouvrir(nav)
    b.att("D : sans arbre, aucune ligne", 0, len(lignes(page)))
    b.vrai("D : …et la phrase d'aide est visible", page.locator("#mes-arbres-vide").is_visible())
    b.vrai("D : le bouton « Ouvrir un arbre » est toujours là", page.locator("#btn-ouvrir-fichier").is_visible())
    page.context.close()

    page = ouvrir(nav, "1280x720")
    parc = parcours_pour(page, "olivier", 2)
    page.evaluate("""([piege, parc]) => {
        const dep = (id, titre, dessin, modifie, q) => localStorage.setItem('arbre-a-questions:brouillon:' + id,
            JSON.stringify({modifie, donnees: Editeur.nettoyer({id, titre, dessin, questions: q})}));
        dep('a1', 'Conférence Lorient', 'olivier', '2026-10-02T09:00:00.000Z', {I1: 'Une question'});
        dep('a2', 'Le chêne de test', 'chene', '2026-10-04T09:00:00.000Z', {A1: 'Une question de chêne'});
        dep('a3', '', 'olivier', '2026-10-03T09:00:00.000Z', {I1: 'Question sans titre'});
        dep('a4', piege, 'olivier', '2026-10-01T09:00:00.000Z', {I1: 'x'});
        Bibliotheque.fusionner('a1', parc);
    }""", [PIEGE, parc])
    page.reload(); page.wait_for_timeout(500)
    L = lignes(page)
    b.att("D : quatre arbres, le plus récent d'abord (celui qui a des sessions)", ["a1", "a2", "a3", "a4"], [x["id"] for x in L])
    t = {x["id"]: x["texte"] for x in L}
    b.vrai("D : a1 : « 2 sessions » et « pas encore sauvegardé »", "2 sessions" in t.get("a1", "") and "pas encore sauvegardé" in t.get("a1", ""), t.get("a1"))
    b.vrai("D : a2 : le chêne, 4 thèmes, aucune conférence", "4 thèmes" in t.get("a2", "") and "aucune session" in t.get("a2", ""), t.get("a2"))
    b.vrai("D : a3 : « Sans titre »", "Sans titre" in t.get("a3", ""), t.get("a3"))
    b.vrai("D : le titre piégé s'affiche tel quel", PIEGE in page.locator("li[data-id=a4] .arbre-titre").inner_text(), page.locator("li[data-id=a4] .arbre-titre").inner_text())
    b.att("D : …et ne s'exécute pas", None, page.evaluate("window.__pwn ?? null"))
    b.att("D : …et ne crée aucune image dans la liste", 0, page.locator("#liste-arbres img[src=x]").count())
    b.att("D : chaque ligne a lancer / modifier / sauvegarder / retirer", ["lancer", "modifier", "telecharger", "retirer"], L[0]["actes"])
    b.att("D : le bouton PDF de chaque session est visible tout de suite, sans rien déplier", 2, page.locator("li[data-id=a1] [data-act=pdf]:visible").count())
    b.vrai("D : …et il dit « Télécharger le PDF »", "Télécharger le PDF" in page.inner_text("li[data-id=a1] [data-act=pdf] >> nth=0"))
    b.vrai("D : la liste « Mes arbres » est SOUS les boutons « Lancer l'arbre » de l'accueil", page.evaluate("document.getElementById('mes-arbres').getBoundingClientRect().top >= document.getElementById('btn-lancer').getBoundingClientRect().bottom"))
    b.vrai("D : …et les deux arbres sont AU-DESSUS", page.evaluate("document.getElementById('choix-arbre').getBoundingClientRect().bottom <= document.getElementById('btn-modifier').getBoundingClientRect().top"))
    b.vrai("D : une ligne d'aide explique le fichier de sauvegarde", "fichier" in page.inner_text("#mes-arbres-aide") and "double-clic" in page.inner_text("#mes-arbres-aide"), page.inner_text("#mes-arbres-aide"))
    petits = page.evaluate("[...document.querySelectorAll('#liste-arbres button, #btn-ouvrir-fichier')].filter(b => b.getBoundingClientRect().height < 43.5).map(b => b.textContent)")
    b.att("D : tous les boutons de la liste font au moins 44 px de haut", [], petits)
    page.screenshot(path=str(TMP / "d_liste_1280x720.png"), full_page=True)

    # Modifier : un clic, l'éditeur s'ouvre sur CET arbre
    page.click("li[data-id=a2] [data-act=modifier]"); page.wait_for_timeout(300)
    b.vrai("D : « Modifier » ouvre directement l'éditeur", page.locator("#editeur").is_visible() and not page.locator("#prepa").is_visible())
    b.att("D : …sur le chêne a2", ("chene", "a2", "Le chêne de test"), tuple(page.evaluate("[ARBRE.dessin, ARBRE.id, ARBRE.titre]")))
    b.att("D : …avec ses textes dans les champs", "Une question de chêne", page.input_value("#f-q-A1"))
    page.click("#btn-retour-prepa"); page.wait_for_timeout(200)
    b.att("D : la liste est toujours complète au retour", ["a1", "a2", "a3", "a4"], [x["id"] for x in lignes(page)])
    b.att("D : le choix d'arbre est verrouillé sur le chêne", "true", page.get_attribute("[data-arbre=chene]", "aria-checked"))
    # Lancer : un clic, la scène s'ouvre avec CET arbre (il manque des textes : la boîte habituelle s'ouvre, on lance quand même)
    page.click("li[data-id=a2] [data-act=lancer]"); page.wait_for_timeout(300)
    if page.locator("#dlg-manques[open]").count(): page.click("#dlg-manques button[value=lancer]")
    page.wait_for_selector("#screen", state="visible"); C.attendre_dessin(page)
    b.att("D : « Lancer » ouvre directement la scène du chêne a2", (True, "chene", "a2"), (page.locator("#screen").is_visible(), page.evaluate("FICHE.id"), page.evaluate("ARBRE.id")))
    page.keyboard.press("e"); page.wait_for_timeout(100); page.keyboard.press("o"); page.wait_for_timeout(300)
    page.click("li[data-id=a1] [data-act=modifier]"); page.wait_for_timeout(300)
    b.att("D : « Modifier » sur a1 installe l'olivier", ("olivier", "a1"), tuple(page.evaluate("[ARBRE.dessin, ARBRE.id]")))
    page.click("#btn-retour-prepa"); page.wait_for_timeout(200)
    b.att("D : …et ne change pas la date de modification de a1", "2026-10-02T09:00:00.000Z", page.evaluate("JSON.parse(localStorage.getItem('arbre-a-questions:brouillon:a1')).modifie"))

    # télécharger depuis la liste == télécharger depuis l'éditeur (aux dates près)
    with page.expect_download() as dl:
        page.click("li[data-id=a1] [data-act=telecharger]")
    f_liste = TMP / "d_liste.html"; dl.value.save_as(str(f_liste)); page.wait_for_timeout(300)
    d_liste = donnees_du_fichier(f_liste)
    texte_a1 = [x["texte"] for x in lignes(page) if x["id"] == "a1"][0]
    b.vrai("D : tout de suite après un téléchargement depuis la liste, a1 n'est plus « pas encore sauvegardé »", "pas encore sauvegardé" not in texte_a1, texte_a1)
    page.click("#btn-modifier")
    f_ed = telecharger_arbre(page, "d_editeur.html"); d_ed = donnees_du_fichier(f_ed)
    for d_ in (d_liste, d_ed): d_.pop("modifie", None)
    b.att("D : fichier téléchargé depuis la liste == depuis l'éditeur", d_ed, d_liste)
    b.att("D : …il porte les 2 sessions", 2, len(d_liste.get("parcours", [])))
    page.click("#btn-retour-prepa"); page.wait_for_timeout(200)
    b.vrai("D : après le téléchargement, a1 n'est plus « pas encore sauvegardé »", "pas encore sauvegardé" not in lignes(page)[[x["id"] for x in lignes(page)].index("a1")]["texte"])

    # retirer : « non » ne change rien, « oui » efface les clés
    page.click("li[data-id=a3] [data-act=retirer]"); page.wait_for_timeout(150)
    b.vrai("D : retirer demande confirmation", page.locator("#dlg-retirer[open]").count() == 1)
    page.click("#dlg-retirer button[value=non]"); page.wait_for_timeout(150)
    b.att("D : « Non, garder » ne retire rien", 4, len(lignes(page)))
    page.click("li[data-id=a3] [data-act=retirer]"); page.wait_for_timeout(150)
    page.click("#dlg-retirer button[value=oui]"); page.wait_for_timeout(150)
    b.att("D : « Oui, retirer » retire l'arbre", ["a1", "a2", "a4"], [x["id"] for x in lignes(page)])
    b.vrai("D : …et ses clés de mémoire", not [k for k in page.evaluate("Object.keys(localStorage)") if k.endswith(":a3")])

    # sessions : nommer, supprimer
    b.att("D : les 2 sessions sont visibles sans rien déplier", 2, page.locator("li[data-id=a1] .conf-ligne:visible").count())
    b.vrai("D : la ligne d'une conférence dit combien de questions ont été posées", re.search(r"\b(1[2-9]|2\d) questions posées", page.inner_text("li[data-id=a1] .conf-ligne")) is not None, page.inner_text("li[data-id=a1] .conf-ligne"))
    page.fill("li[data-id=a1] .conf-ligne >> nth=0 >> .conf-nom", "Lorient, 3 nov."); page.keyboard.press("Tab"); page.wait_for_timeout(150)
    page.reload(); page.wait_for_timeout(500)
    noms = page.evaluate("Bibliotheque.parcoursDe('a1').map(p => p.nom).sort()")
    b.att("D : un nom donné à une conférence est gardé après rechargement", ["", "Lorient, 3 nov."], noms)
    page.click("li[data-id=a1] .conf-ligne >> nth=0 >> [data-act=suppr]"); page.wait_for_timeout(150)
    b.vrai("D : supprimer une conférence demande confirmation", page.locator("#dlg-suppr[open]").count() == 1)
    page.click("#dlg-suppr button[value=non]"); page.wait_for_timeout(150)
    b.att("D : « Non, garder » : 2 sessions", 2, len(page.evaluate("Bibliotheque.parcoursDe('a1')")))
    page.click("li[data-id=a1] .conf-ligne >> nth=0 >> [data-act=suppr]"); page.wait_for_timeout(150)
    page.click("#dlg-suppr button[value=oui]"); page.wait_for_timeout(150)
    b.att("D : « Oui, supprimer » : 1 conférence", 1, len(page.evaluate("Bibliotheque.parcoursDe('a1')")))

    # un arbre pas encore téléchargé (« modele ») : seulement ouvrir et retirer
    page.evaluate("""() => localStorage.setItem('arbre-a-questions:brouillon:modele', JSON.stringify({modifie: '2026-10-06T09:00:00.000Z',
        donnees: Editeur.nettoyer({id: 'modele', titre: 'Premier jet', dessin: 'olivier', questions: {I1: 'q'}})}))""")
    page.reload(); page.wait_for_timeout(500)
    m = [x for x in lignes(page) if x["id"] == "modele"]
    b.vrai("D : le brouillon « modele » est listé", len(m) == 1)
    if m:
        b.att("D : …avec lancer, modifier et retirer (pas de sauvegarde depuis la liste)", ["lancer", "modifier", "retirer"], m[0]["actes"])
        b.vrai("D : …et la mention « brouillon, pas encore sauvegardé »", "brouillon, pas encore sauvegardé" in m[0]["texte"], m[0]["texte"])

    # en anglais
    page.select_option("#langue", "en"); page.wait_for_timeout(300)
    tout = page.inner_text("#mes-arbres")
    b.vrai("D : en anglais, le titre de la section", "My trees" in tout, tout[:80])
    b.vrai("D : …et les boutons de la ligne", "Launch" in tout and "Edit" in tout and "Save (file)" in tout, tout[:300])
    b.vrai("D : …aucun mot de français dans la liste", not re.search(r"Lancer|Modifier|Retirer|Sauvegarder|conférence|télécharger|Sans titre|thèmes|Ouvrir", tout), tout)
    page.select_option("#langue", "fr"); page.wait_for_timeout(300)

    # taille d'écran
    for taille in ("1280x720", "1024x768"):
        page.set_viewport_size({"width": int(taille.split("x")[0]), "height": int(taille.split("x")[1])}); page.wait_for_timeout(200)
        debord = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        b.vrai(f"D : pas de défilement horizontal à {taille}", debord <= 0, f"{debord}px")
        r = page.evaluate("(() => { const r = document.getElementById('mes-arbres').getBoundingClientRect(); return [r.left, r.right, innerWidth]; })()")
        b.vrai(f"D : la section tient dans l'écran à {taille}", r[0] >= 0 and r[1] <= r[2], str(r))
    page.screenshot(path=str(TMP / "d_liste_1024x768.png"), full_page=True)
    b.vrai("D : aucune erreur de page", not page.erreurs, str(page.erreurs))
    b.vrai("D : aucune requête réseau", not C.requetes_suspectes(page), str(C.requetes_suspectes(page)))
    page.context.close()

# ====================================================================== E
def fichier_arbre(page, nom, **champs):
    """Un fichier d'arbre fabriqué par l'appli elle-même (comme « Télécharger mon arbre ») ; champs : ce qu'on y met en plus ou en pire."""
    parcours = champs.pop("parcours", None); modifie = champs.pop("modifie", "2026-10-03T08:00:00.000Z")
    html = page.evaluate("""([champs, parcours, modifie]) => { const d = Object.assign(Editeur.nettoyer(champs), {modifie});
        if (parcours) d.parcours = parcours; return Editeur.fabriquer(d); }""", [champs, parcours, modifie])
    chemin = TMP / nom; chemin.write_text(html, encoding="utf-8"); return chemin


def ouvrir_fichier(page, chemin):
    page.set_input_files("#fichier-arbre", str(chemin)); page.wait_for_timeout(500)


def etat(page): return page.inner_text("#mes-arbres-etat")      # le message de l'accueil (refus)


def statut(page): return page.inner_text("#statut")            # le message de l'éditeur (arbre ouvert) : on y arrive après une ouverture réussie


def retour_accueil(page):
    if page.locator("#editeur").is_visible():
        page.click("#btn-retour-prepa"); page.wait_for_timeout(150)


def section_E(nav, b):
    page = ouvrir(nav, "1280x720")
    olivier = page.evaluate(CHEMINS_JS, "olivier"); chene = page.evaluate(CHEMINS_JS, "chene")
    p2 = [page.evaluate(FABRIQUE_JS, ["olivier", olivier[i], {"id": f"po{i}", "fin": f"2026-10-0{3 + i % 3}T10:30:00.000Z", "debut": f"2026-10-0{3 + i % 3}T10:00:00.000Z"}]) for i in (4, 9)]
    pc = [page.evaluate(FABRIQUE_JS, ["chene", chene[5], {"id": "pc1", "fin": "2026-10-04T11:30:00.000Z", "debut": "2026-10-04T11:00:00.000Z"}])]
    ids = lambda: [x["id"] for x in page.evaluate("Bibliotheque.entrees()")]

    # 1. fichiers valides
    f_o = fichier_arbre(page, "e_olivier.html", id="eo1", titre="Olivier du fichier", dessin="olivier", questions={"I1": "Question du fichier"}, parcours=p2)
    ouvrir_fichier(page, f_o)
    b.att("E : olivier ouvert : arbre installé", ("olivier", "eo1", "Olivier du fichier"), tuple(page.evaluate("[ARBRE.dessin, ARBRE.id, ARBRE.titre]")))
    b.vrai("E : …on arrive directement dans l'éditeur, « Lancer l'arbre » en haut", page.locator("#editeur").is_visible() and page.locator("#btn-lancer-editeur").is_visible() and not page.locator("#prepa").is_visible())
    b.att("E : …avec ses textes dans les champs", "Question du fichier", page.input_value("#f-q-I1"))
    b.att("E : …ses 2 sessions sont dans la mémoire", 2, len(page.evaluate("Bibliotheque.parcoursDe('eo1')")))
    b.vrai("E : …message de succès dans l'éditeur", "Olivier du fichier" in statut(page) and "2 sessions" in statut(page), statut(page))
    retour_accueil(page)
    b.vrai("E : …l'arbre est dans la liste, et n'est pas « à télécharger » (le fichier EST son téléchargement)",
           "eo1" in ids() and not page.evaluate("Bibliotheque.entrees().find(x => x.id === 'eo1').aTelecharger"))
    b.att("E : …la date de modification est celle du fichier", "2026-10-03T08:00:00.000Z", page.evaluate("JSON.parse(localStorage.getItem('arbre-a-questions:brouillon:eo1')).modifie"))
    f_c = fichier_arbre(page, "e_chene.html", id="ec1", titre="Chêne du fichier", dessin="chene", questions={"A1": "Question chêne"}, parcours=pc)
    ouvrir_fichier(page, f_c)
    b.att("E : chêne ouvert", ("chene", "ec1"), tuple(page.evaluate("[ARBRE.dessin, ARBRE.id]")))
    retour_accueil(page)
    ouvrir_fichier(page, f_o); retour_accueil(page)
    b.att("E : rouvrir le même fichier ne double pas les sessions", 2, len(page.evaluate("Bibliotheque.parcoursDe('eo1')")))

    # 2. refus : un message dédié chacun, et AUCUN changement
    def refus(nom, chemin, motif):
        avant = (ids(), page.evaluate("[ARBRE.id, ARBRE.titre]"))
        ouvrir_fichier(page, chemin)
        b.vrai(f"E : refusé — {nom} : on reste à l'accueil", page.locator("#prepa").is_visible() and not page.locator("#editeur").is_visible())
        b.vrai(f"E : refusé — {nom} : message", re.search(motif, etat(page)) is not None, etat(page))
        b.att(f"E : refusé — {nom} : rien n'a changé", avant, (ids(), page.evaluate("[ARBRE.id, ARBRE.titre]")))
    (TMP / "e_texte.html").write_text("juste du texte, pas un arbre", encoding="utf-8")
    refus("texte quelconque", TMP / "e_texte.html", "n'est pas un arbre")
    (TMP / "e_page.html").write_text("<html><body><h1>Une page</h1></body></html>", encoding="utf-8")
    refus("page sans arbre", TMP / "e_page.html", "n'est pas un arbre")
    if ORIGINAL_3_NOV.exists():
        refus("ancien format (le fichier du 3 novembre)", ORIGINAL_3_NOV, "ancienne version")
    html = f_o.read_text(encoding="utf-8")
    (TMP / "e_f2.html").write_text(re.sub(r'"format": 1', '"format": 2', html, count=1), encoding="utf-8")
    refus("format plus récent", TMP / "e_f2.html", "plus récente")
    (TMP / "e_casse.html").write_text(re.sub(r'(<script type="application/json" id="donnees-arbre">\n).*?(\n</script>)', r'\1{oops\2', html, count=1, flags=re.S), encoding="utf-8")
    refus("JSON cassé", TMP / "e_casse.html", "illisible")
    refus("arbre vierge", fichier_arbre(page, "e_vierge.html"), "vierge")
    (TMP / "e_sapin.html").write_text(re.sub(r'"dessin": "olivier"', '"dessin": "sapin"', html, count=1), encoding="utf-8")
    refus("dessin inconnu", TMP / "e_sapin.html", "illisible")
    (TMP / "e_gros.html").write_text(html + "<!--" + "x" * 9_000_000 + "-->", encoding="utf-8")      # un VRAI fichier d'arbre, gonflé : seule la taille doit le faire refuser
    refus("vrai arbre de plus de 8 Mo", TMP / "e_gros.html", "illisible")

    # 3. fichier hostile : valeurs bornées, parcours invalides écartés et comptés, rien ne s'exécute
    mauvais = [{"id": f"m{i}", "debut": "x", "fin": "y", "path": ["Z"], "subs": [], "copie": {"dessin": "olivier"}} for i in range(3000)]
    f_h = fichier_arbre(page, "e_hostile.html", id="eh1", titre=PIEGE * 5 + "T" * 2_000_000, dessin="olivier", questions={"I1": "<script>window.__pwn=1</script>" * 50},
                        parcours=p2[:1] + mauvais)
    t0 = __import__("time").time(); ouvrir_fichier(page, f_h); duree = __import__("time").time() - t0
    b.vrai("E : fichier hostile : rapide (moins de 5 s)", duree < 5, f"{duree:.1f} s")
    b.att("E : …ne s'exécute pas", None, page.evaluate("window.__pwn ?? null"))
    b.vrai("E : …titre borné à 80 caractères", len(page.evaluate("ARBRE.titre")) <= 80)
    b.vrai("E : …question bornée à 120 caractères", len(page.evaluate("ARBRE.questions.I1")) <= 120)
    b.att("E : …1 bonne session gardée", 1, len(page.evaluate("Bibliotheque.parcoursDe('eh1')")))
    b.vrai("E : …les 3000 sessions abîmées sont comptées dans le message", "3000 session(s) abîmée" in statut(page), statut(page))
    retour_accueil(page)

    # 4. conflit : l'arbre est déjà connu avec un contenu différent
    page.evaluate("""() => localStorage.setItem('arbre-a-questions:brouillon:eo1', JSON.stringify({modifie: '2026-10-06T09:00:00.000Z',
        donnees: Editeur.nettoyer({id: 'eo1', titre: 'Version de la liste', dessin: 'olivier', questions: {I1: 'Question de la liste'}})}))""")
    p_extra = page.evaluate(FABRIQUE_JS, ["olivier", olivier[20], {"id": "poX", "fin": "2026-10-05T10:30:00.000Z", "debut": "2026-10-05T10:00:00.000Z"}])
    f_conf = fichier_arbre(page, "e_conflit.html", id="eo1", titre="Version du fichier", dessin="olivier", questions={"I1": "Question du fichier"}, parcours=[p_extra])
    ouvrir_fichier(page, f_conf)
    b.vrai("E : conflit : la boîte s'ouvre", page.locator("#dlg-conflit[open]").count() == 1)
    b.vrai("E : …elle montre les deux dates", "06/10/2026" in page.inner_text("#dlg-conflit") and "03/10/2026" in page.inner_text("#dlg-conflit"), page.inner_text("#dlg-conflit"))
    page.keyboard.press("Escape"); page.wait_for_timeout(200)
    b.att("E : Échap annule tout : la liste garde sa version", "Version de la liste", page.evaluate("Bibliotheque.entrees().find(x => x.id === 'eo1').donnees.titre"))
    b.att("E : …et n'a pas fusionné les sessions", 2, len(page.evaluate("Bibliotheque.parcoursDe('eo1')")))
    b.vrai("E : …et on reste à l'accueil", page.locator("#prepa").is_visible())
    ouvrir_fichier(page, f_conf)
    page.click("#dlg-conflit button[value=liste]"); page.wait_for_timeout(300)
    b.vrai("E : « Garder la liste » : on arrive aussi dans l'éditeur", page.locator("#editeur").is_visible()); retour_accueil(page)
    b.att("E : « Garder la liste » : le titre de la liste", "Version de la liste", page.evaluate("Bibliotheque.entrees().find(x => x.id === 'eo1').donnees.titre"))
    b.att("E : …mais les sessions des deux sont réunies", 3, len(page.evaluate("Bibliotheque.parcoursDe('eo1')")))
    b.vrai("E : …et l'arbre devient « à télécharger » (la liste a une session que le fichier n'a pas)", page.evaluate("Bibliotheque.entrees().find(x => x.id === 'eo1').aTelecharger"))
    ouvrir_fichier(page, f_conf)
    page.click("#dlg-conflit button[value=fichier]"); page.wait_for_timeout(300)
    b.vrai("E : « Prendre celle du fichier » : on arrive dans l'éditeur", page.locator("#editeur").is_visible()); retour_accueil(page)
    b.att("E : « Prendre celle du fichier » : le titre du fichier", "Version du fichier", page.evaluate("Bibliotheque.entrees().find(x => x.id === 'eo1').donnees.titre"))
    b.att("E : …et l'arbre est celui qui est ouvert", ("eo1", "Version du fichier"), tuple(page.evaluate("[ARBRE.id, ARBRE.titre]")))

    # 4bis. un fichier qui s'appelle « modele » ne prend pas la place du brouillon « modele » de ce navigateur
    page.evaluate("""() => localStorage.setItem('arbre-a-questions:brouillon:modele', JSON.stringify({modifie: '2026-10-06T09:00:00.000Z',
        donnees: Editeur.nettoyer({id: 'modele', titre: 'Premier jet', dessin: 'olivier', questions: {I1: 'q'}})}))""")
    ouvrir_fichier(page, fichier_arbre(page, "e_modele.html", id="modele", titre="Venu d'un fichier", dessin="olivier", questions={"I1": "autre"})); retour_accueil(page)
    b.att("E : un fichier d'id « modele » est bien ouvert", "Venu d'un fichier", page.evaluate("ARBRE.titre"))
    b.vrai("E : …sous un autre id", page.evaluate("ARBRE.id") != "modele", page.evaluate("ARBRE.id"))
    b.att("E : …et le brouillon « modele » est intact", "Premier jet", page.evaluate("JSON.parse(localStorage.getItem('arbre-a-questions:brouillon:modele')).donnees.titre"))

    # 5. le fichier d'origine du 3 novembre n'a pas bougé
    if ORIGINAL_3_NOV.exists():
        b.vrai("E : le fichier du 3 novembre est intact", hashlib.sha256(ORIGINAL_3_NOV.read_bytes()).hexdigest().startswith(SHA_3_NOV))
    b.vrai("E : aucune erreur de page", not page.erreurs, str(page.erreurs))
    b.vrai("E : aucune requête réseau", not C.requetes_suspectes(page), str(C.requetes_suspectes(page)))
    page.screenshot(path=str(TMP / "e_apres.png"), full_page=True)
    page.context.close()


SECTIONS = {"A": section_A, "B": section_B, "C": section_C, "D": section_D, "E": section_E}

if __name__ == "__main__":
    choix = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    b = Bilan()
    with sync_playwright() as p:
        nav = C.lancer(p)
        for s in choix:
            SECTIONS[s](nav, b)
        nav.close()
    sys.exit(0 if C.bilan("Mes arbres : " + ", ".join(choix), b.echecs) else 1)
