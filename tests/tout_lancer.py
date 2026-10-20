"""Lance toute la batterie et affiche un tableau : un test qui n'affiche rien n'est PAS un test réussi.

 1. syntaxe de chaque bloc de code (Node)
 2. le dessin de l'olivier == le fichier de référence du nouveau design (7 états, 3 tailles d'écran, pixel par pixel)
 3. mécanique : les 256 parcours possibles == ceux de l'original du 3 novembre, et tous les gestes
 4. écran de préparation  5. éditeur de bout en bout  6. cas limites de robustesse  7. limites de longueur et polices (les deux arbres)
 8. la mésange : parcours clavier comparé à la référence, aller-retour, passages du tronc, remise à zéro, notes, bouton rond
 9. les deux arbres : choix sur l'écran de préparation, verrou, éditeur piloté par la fiche, arbre factice, vrai chêne
10. le chêne : dessin == son brouillon de référence (9 états x 3 tailles, pixels) ; structure par le calcul (26 questions, 128 parcours) ;
    placement des glands et des liens par le calcul ; l'écureuil (clavier, retour, passages du tronc, remise à zéro)
11. les langues : mêmes clés dans les 7 langues, repli sur le français, choix de la langue, aucun texte français visible,
    fichier téléchargé, dessin identique au pixel dans toutes les langues
12. Mes arbres : parcours gardés au tableau final, liste, ouverture d'un fichier, fichier hostile, conflit
13. le PDF d'une conférence : plan du verso, structure du fichier, second lecteur, pixels, recto == écran, pire cas
12. les langues : aucun débordement (7 langues x 4 tailles x 11 écrans) + captures des écrans clés
13. les questions subsidiaires : tirage par le calcul sur tous les parcours, touche = et rond, carte et contraste, mascotte et fruits mesurés,
    retour avec ←, épuisement, tableau final identique à celui d'avant, fichier téléchargé

14. le mode d'emploi : touches rejouées sur la vraie scène, retour exact, jamais sur la scène, chiffres des fiches, fichier téléchargé, scène identique à celle d'avant

Usage :  .venv/bin/python tests/tout_lancer.py
"""
import subprocess, sys, re, time, pathlib, tempfile
import _commun as C

PY = sys.executable
T = C.RACINE / "tests"


def syntaxe():
    s = (C.RACINE / "index.html").read_text(encoding="utf-8")
    manque = []
    for m in re.finditer(r'<script(?P<a>[^>]*)>(?P<c>.*?)</script>', s, re.S):
        if "application/json" in m.group("a"): continue
        nom = re.search(r'id="([^"]+)"', m.group("a")).group(1)
        f = pathlib.Path(tempfile.gettempdir()) / f"syntaxe_{nom}.js"; f.write_text(m.group("c"), encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        if r.returncode: manque.append(f"{nom}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '?'}")
    return (0 if not manque else 1), ("tous les blocs sont valides" if not manque else "; ".join(manque))


def commande(args):
    t0 = time.time()
    r = subprocess.run([PY, *args], cwd=str(T), capture_output=True, text=True)
    sortie = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode, (sortie[-1] if sortie and r.returncode == 0 else "\n      ".join(sortie[:6])), time.time() - t0


if __name__ == "__main__":
    etapes = [
        ("syntaxe du code", syntaxe),
        ("olivier : dessin == référence du nouveau design (7 états x 3 tailles, pixels)", lambda: commande(["comparer_reference.py", "olivier", "7"])),
        ("mécanique : 256 parcours (== original) + gestes + plein écran", lambda: commande(["test_scene.py"])),
        ("écran de préparation, E / Échap", lambda: commande(["test_prepa.py"])),
        ("éditeur de bout en bout (réseau coupé)", lambda: commande(["test_editeur.py"])),
        ("robustesse (mémoire en panne, noms de fichier, titre piégé, vide)", lambda: commande(["test_robustesse.py"])),
        ("limites de longueur et polices", lambda: commande(["test_limites.py"])),
        ("mésange : parcours, retour, passages du tronc, remise à zéro, notes, bouton rond", lambda: commande(["test_mesange.py"])),
        ("deux arbres : choix, verrou, éditeur piloté par la fiche, arbre factice, vrai chêne", lambda: commande(["test_arbres.py"])),
        ("structure des votes par le calcul (olivier : 256 parcours ; chêne : 128 parcours, chiffres de la fiche 15)", lambda: commande(["test_structure.py"])),
        ("chêne : dessin == brouillon de référence (9 états x 3 tailles, pixels)", lambda: commande(["comparer_reference.py", "chene", "5"])),
        ("chêne : placement des glands et des liens par le calcul", lambda: commande(["test_placement.py"])),
        ("écureuil : parcours clavier, retour, passages du tronc, remise à zéro, règle des liens proposés", lambda: commande(["test_ecureuil.py"])),
        ("langues : mêmes clés, repli sur le français, choix, aucun texte français visible, fichier téléchargé, dessin identique", lambda: commande(["test_langues.py"])),
        ("langues : aucun débordement (7 langues x 4 tailles x 11 écrans, 375 px compris) + captures", lambda: commande(["test_langues_debordement.py"])),
        ("questions subsidiaires : tirage sur tous les parcours, touche =, rond, carte, mascotte et fruits, retour, épuisement, téléchargement", lambda: commande(["test_sous_questions.py"])),
        ("Mes arbres : parcours gardés, liste, ouverture d'un fichier, fichier hostile, conflit, 7 langues", lambda: commande(["test_bibliotheque.py"])),
        ("PDF d'une conférence : plan du verso, structure, second lecteur, pixels, recto == écran, pire cas", lambda: commande(["test_pdf.py"])),
        ("mode d'emploi : liste des touches rejouée sur la vraie scène, retour exact, jamais sur la scène, chiffres des fiches, fichier téléchargé, scène identique à avant", lambda: commande(["test_mode_emploi.py"])),
    ]
    echecs = 0
    for nom, f in etapes:
        t0 = time.time(); r = f()
        code, texte = r[0], r[1]
        duree = r[2] if len(r) > 2 else time.time() - t0
        print(f"{'OK   ' if code == 0 else 'ECHEC'} [code {code}] {nom}  ({duree:.0f} s)\n      {texte}")
        echecs += code != 0
    print("\n" + ("TOUT PASSE." if not echecs else f"{echecs} ÉTAPE(S) EN ÉCHEC."))
    sys.exit(1 if echecs else 0)
