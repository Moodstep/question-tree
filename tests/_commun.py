"""Outils communs aux scripts de test (Playwright piloté sur le Chrome installé).

Tout ce qui sert à plusieurs scripts vit ici : un seul endroit à corriger.
Lancer un script avec :  .venv/bin/python tests/<script>.py
"""
import hashlib
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

RACINE = pathlib.Path(__file__).resolve().parent.parent
CAPTURES = RACINE / "tests" / "captures"
CAPTURES.mkdir(parents=True, exist_ok=True)

# Tailles d'écran testées : projecteur Full HD, portable courant, projecteur 4:3
TAILLES = {"1920x1080": (1920, 1080), "1280x720": (1280, 720), "1024x768": (1024, 768)}


def sha(texte):
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


# Dessin logiciel obligatoire : avec l'accélération graphique par défaut, le feuillage
# (canvas 1800x1800) varie parfois d'un cheveu d'un lancement à l'autre (constaté le
# 04/10 : 3 empreintes différentes sur 12 chargements du MÊME fichier). Sans elle : 12/12 identiques.
ARGS_STABLES = ["--disable-gpu", "--disable-accelerated-2d-canvas"]


def lancer(p, **kw):
    """Chrome installé sur le Mac (aucun navigateur téléchargé), rendu déterministe."""
    return p.chromium.launch(channel="chrome", headless=True, args=ARGS_STABLES, **kw)


def nouvelle_page(navigateur, taille="1920x1080", reduit=True, hors_ligne=True, init_script=None, **ctx):
    """Page prête. reduit=True : prefers-reduced-motion, donc plus aucune animation
    (le halo des olives pulse en continu, ce qui rendrait les captures instables)."""
    w, h = TAILLES[taille] if taille in TAILLES else map(int, taille.split('x'))   # « 1440x900 » est accepté tel quel
    ctx.setdefault("locale", "fr-FR")      # langue du navigateur de test : l'outil choisit sa langue d'après elle (français = situation de référence)
    contexte = navigateur.new_context(
        viewport={"width": w, "height": h},
        reduced_motion="reduce" if reduit else "no-preference",
        accept_downloads=True,
        **ctx,
    )
    if hors_ligne:
        contexte.set_offline(True)      # réseau coupé : toute tentative de connexion échouerait et serait vue
    if init_script:
        contexte.add_init_script(init_script)
    page = contexte.new_page()
    page.erreurs = []
    page.requetes = []
    page.on("pageerror", lambda e: page.erreurs.append(str(e)))
    page.on("console", lambda m: page.erreurs.append(m.text) if m.type == "error" else None)
    page.on("request", lambda r: page.requetes.append(r.url))
    page.on("requestfailed", lambda r: page.requetes.append("ECHEC " + r.url))
    return page


def requetes_suspectes(page):
    """Toute requête qui n'est ni le fichier local lui-même ni un contenu embarqué."""
    ok = ("file://", "data:", "blob:", "about:")
    return [u for u in page.requetes if not u.startswith(ok)]


def etat_dom(page):
    """Empreinte de ce que voit le public : uniquement le DOM, donc comparable
    entre l'original et la version réorganisée (leurs variables internes diffèrent)."""
    return page.evaluate(
        """() => ({
            svg: document.getElementById('svg').outerHTML,
            panel: document.getElementById('panel').innerHTML,
            screen: document.getElementById('screen').className,
            nextHidden: document.getElementById('next').hidden,
            prevHidden: document.getElementById('prev').hidden,
            title: document.title,
        })"""
    )


# Parcours de référence : 4 questions du tronc, puis 8 votes, puis la fin.
# Les choix alternent sur les deux options pour passer par « rester » et « changer ».
CHOIX = ["ArrowUp", "ArrowDown", "ArrowDown", "ArrowUp", "ArrowDown", "ArrowUp", "ArrowUp", "ArrowDown"]


def parcours(page):
    """Génère (nom_etape) après chaque geste ; l'appelant capture ce qu'il veut."""
    yield "00_tronc_T1"
    for i in range(1, 4):
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(60)
        yield f"0{i}_tronc_T{i + 1}"
    page.keyboard.press("ArrowRight")  # T4 -> premier vote
    page.wait_for_timeout(60)
    yield "04_vote1_choix"
    for v in range(8):
        page.keyboard.press(CHOIX[v])
        page.wait_for_timeout(60)
        yield f"{5 + 2 * v:02d}_vote{v + 1}_reponse"
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(60)
        yield f"{6 + 2 * v:02d}_vote{v + 2}_choix" if v < 7 else f"{6 + 2 * v:02d}_fin"
    page.keyboard.press("Backspace")  # retour arrière depuis la fin
    page.wait_for_timeout(60)
    yield "99_retour_arriere"
    page.keyboard.press("Shift+R")  # remise à zéro
    page.wait_for_timeout(60)
    yield "99_reset"


def attendre_dessin(page):
    """Le dessin de l'arbre est prêt. Il se construit d'un seul tenant (aucune pause pendant la construction) : dès que l'image du
    feuillage est posée, tout le reste l'est aussi. Valable pour les deux arbres (3 ou 4 noms de thèmes)."""
    page.wait_for_function("!!document.querySelector('#svg image')")


def lancer_scene(page):
    """Depuis l'écran de préparation : Lancer l'arbre (puis « Lancer quand même » s'il manque des textes)."""
    if page.locator("#prepa").count() == 0:
        return                                   # fichier d'origine : la scène est déjà là
    page.click("#btn-lancer")
    page.wait_for_timeout(150)
    if page.locator("#dlg-manques[open]").count():
        page.click("#dlg-manques button[value=lancer]")
    page.wait_for_selector("#screen", state="visible")
    attendre_dessin(page)
    page.mouse.move(1, 1)                        # la souris ne doit survoler aucune carte (l'original n'a jamais eu de souris)
    page.wait_for_timeout(250)


def variante_avec_noms(destination):
    """Copie de index.html dont les 3 noms de thèmes sont ceux de l'original (comparaison pixel à pixel)."""
    import re as _re
    s = (RACINE / "index.html").read_text(encoding="utf-8")
    m = _re.search(r'(<script type="application/json" id="donnees-arbre">\n)(.*?)(\n</script>)', s, _re.S)
    d = json.loads(m.group(2))
    for t, nom in zip(d["themes"], ["Infrastructures", "Littoral", "Alimentation"]):
        t["nom"] = nom
    s = s[:m.start(2)] + json.dumps(d, ensure_ascii=False, indent=1) + s[m.end(2):]
    pathlib.Path(destination).write_text(s, encoding="utf-8")
    return destination


def reference_avec_polices(destination, nom="nouveau-design.html"):
    """Copie de TEST d'un fichier de référence (reference/<nom>, jamais modifié) dont le lien Google Fonts est remplacé par les
    polices intégrées de index.html : mêmes polices des deux côtés, aucune requête réseau."""
    import re as _re
    ref = (RACINE / "reference" / nom).read_text(encoding="utf-8")
    polices = _re.search(r'<style id="polices">.*?</style>', (RACINE / "index.html").read_text(encoding="utf-8"), _re.S).group(0)
    lien = _re.search(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', ref)
    assert lien, "lien Google Fonts introuvable dans la référence"
    copie = ref.replace(lien.group(0), polices, 1)
    # Depuis le 05/10/2026 la mention gravée dans les troncs s'écrit « CC BY-SA MOODSTEP » (demande de Joanna). Le fichier de référence,
    # lui, garde l'ancienne graphie : seule cette COPIE DE TEST est alignée, pour que la comparaison pixel à pixel porte sur tout le reste.
    assert copie.count("CC BY-SA Moodstep") == 2, "la mention de licence n'est plus 2 fois dans la référence"
    copie = copie.replace("CC BY-SA Moodstep", "CC BY-SA MOODSTEP")
    # Depuis le 11/10/2026 l'écureuil n'a plus de liseré crème (demande de Joanna). Même principe : seule la COPIE DE TEST de la référence du
    # chêne perd son liseré (appliqué par défaut dans sq / sqx), pour que la comparaison pixel à pixel porte sur tout le reste.
    if "sqHaloP" in copie:
        assert copie.count("halo=true)=>") == 2, "le liseré de l'écureuil n'est plus appliqué par défaut dans la référence"
        copie = copie.replace("halo=true)=>", "halo=false)=>")
    pathlib.Path(destination).write_text(copie, encoding="utf-8")
    return destination


# noms de thèmes des fichiers de référence (comparaison pixel à pixel avec les mêmes textes des deux côtés)
NOMS_REFERENCE = {"olivier": [("I", "Infrastructures"), ("L", "Littoral"), ("A", "Alimentation")],
                  "chene": [("A", "Thème 1"), ("B", "Thème 2"), ("C", "Thème 3"), ("D", "Thème 4")]}


def variante_avec_noms(destination, arbre="olivier"):
    """Copie de index.html avec l'arbre choisi et les noms de thèmes du fichier de référence de cet arbre."""
    import re as _re
    s = (RACINE / "index.html").read_text(encoding="utf-8")
    m = _re.search(r'(<script type="application/json" id="donnees-arbre">\n)(.*?)(\n</script>)', s, _re.S)
    d = json.loads(m.group(2))
    d["dessin"] = arbre
    d["themes"] = [{"id": i, "nom": n} for i, n in NOMS_REFERENCE[arbre]]
    s = s[:m.start(2)] + json.dumps(d, ensure_ascii=False, indent=1) + s[m.end(2):]
    pathlib.Path(destination).write_text(s, encoding="utf-8")
    return destination


def ecrire_json(chemin, obj):
    pathlib.Path(chemin).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def lire_json(chemin):
    return json.loads(pathlib.Path(chemin).read_text(encoding="utf-8"))


def bilan(titre, echecs):
    print(("OK   " if not echecs else "ECHEC ") + titre)
    for e in echecs:
        print("   -", e)
    return not echecs


if __name__ == "__main__":
    # Test de bon fonctionnement du banc d'essai : Chrome se lance-t-il, lit-il un fichier local ?
    with sync_playwright() as p:
        nav = lancer(p)
        page = nouvelle_page(nav)
        page.goto((RACINE / "index.html").as_uri())
        page.wait_for_timeout(500)
        print("Chrome piloté :", nav.version)
        print("Titre de la page :", page.title())
        print("Erreurs JS :", page.erreurs or "aucune")
        print("Requêtes hors fichier local :", requetes_suspectes(page) or "aucune")
        nav.close()
    sys.exit(0)
