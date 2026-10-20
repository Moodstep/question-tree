"""Captures d'écran pour validation à l'œil (texte d'exemple, aucune toile). Sortie : tests/captures/pour_joanna/"""
import pathlib, shutil
from playwright.sync_api import sync_playwright
import _commun as C

SORTIE = C.CAPTURES / "pour_joanna"
shutil.rmtree(SORTIE, ignore_errors=True); SORTIE.mkdir(parents=True)
Q = {
 "I1": "Quelle infrastructure de votre quotidien vous semble la plus fragile ?",
 "A1": "Que mangeriez-vous si les approvisionnements s'arrêtaient pendant une semaine ?",
 "I2": "Qu'est-ce qui, dans votre commune, fonctionne grâce à l'entraide plutôt qu'au réseau ?",
 "A2": "Quel produit local aimeriez-vous retrouver plus souvent dans votre assiette ?",
 "L2": "Que ressentez-vous quand vous regardez la mer, ces temps-ci ?",
}
LONGUE = "Si la salle devait renoncer ce soir à une habitude pour protéger le littoral, laquelle choisirait-elle, et pourquoi ?"
assert len(LONGUE) <= 120

with sync_playwright() as p:
    nav = C.lancer(p)
    page = C.nouvelle_page(nav, "1440x900")
    page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(500)
    page.screenshot(path=str(SORTIE / "01_preparation.png"))
    # éditeur : titre, thèmes, tronc et quelques questions saisies, le reste vide
    page.click("#btn-modifier")
    page.fill("#f-titre", "Conférence du 3 novembre"); page.fill("#f-theme-0", "Infrastructures"); page.fill("#f-theme-1", "Littoral"); page.fill("#f-theme-2", "Alimentation")
    page.fill("#f-tronc-0", "Commençons par vous : qu'est-ce qui vous a amené ici ce soir ?"); page.fill("#f-tronc-1", "Qu'appelle-t-on la robustesse ?")
    for k, v in Q.items(): page.fill(f"#f-q-{k}", v)
    page.fill("#f-q-I3", LONGUE)
    page.wait_for_timeout(700); page.mouse.move(1, 1); page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(150)
    page.screenshot(path=str(SORTIE / "02_editeur_haut.png"))
    page.evaluate("document.getElementById('f-q-I1').closest('.q-ligne').scrollIntoView({block:'start'}); window.scrollBy(0,-90)")
    page.wait_for_timeout(200); page.screenshot(path=str(SORTIE / "03_editeur_ramure.png"))
    page.screenshot(path=str(SORTIE / "03b_editeur_complet.png"), full_page=True)
    # message des textes manquants
    page.click("#btn-lancer-editeur"); page.wait_for_timeout(250)
    page.screenshot(path=str(SORTIE / "04_message_manquants.png"))
    page.click("#dlg-manques button[value=lancer]")
    C.attendre_dessin(page); page.mouse.move(1, 1); page.wait_for_timeout(400)
    # scène : premier vote (deux cartes), puis une réponse (grande carte), puis question longue
    for _ in range(4): page.keyboard.press("ArrowRight")
    page.wait_for_timeout(300); page.screenshot(path=str(SORTIE / "05_scene_vote_1440x900.png"))
    page.keyboard.press("ArrowDown"); page.wait_for_timeout(300); page.screenshot(path=str(SORTIE / "06_scene_reponse_1440x900.png"))
    page.keyboard.press("e"); page.wait_for_timeout(250); page.screenshot(path=str(SORTIE / "07_scene_confirmation_retour.png"))
    page.keyboard.press("n")
    page.context.close()

    # question à la limite des 120 caractères, vote à deux cartes, sur l'écran le plus serré testé (1280x720)
    page = C.nouvelle_page(nav, "1280x720"); page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(400)
    page.evaluate("""([longue, q]) => { ARBRE.themes[0].nom='Infrastructures'; ARBRE.themes[1].nom='Littoral'; ARBRE.themes[2].nom='Alimentation';
        for (const k in q) ARBRE.questions[k] = q[k]; ARBRE.questions.I2 = longue; ARBRE.questions.A2 = longue.toUpperCase().slice(0,118); }""", [LONGUE, Q])
    page.evaluate("ouvrirScene()"); C.attendre_dessin(page)
    page.evaluate("applyState({mode:'choose', ti:3, path:['I1']})"); page.mouse.move(1, 1); page.wait_for_timeout(400)
    page.screenshot(path=str(SORTIE / "08_scene_limite_120_1280x720.png"))
    page.context.close()
    nav.close()
print(sorted(f.name for f in SORTIE.iterdir()))
