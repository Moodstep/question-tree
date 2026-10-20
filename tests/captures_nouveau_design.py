"""Captures pour Joanna : les 7 états du nouveau design + les passages du tronc image par image. Sortie : tests/captures/nouveau_design/"""
import pathlib, shutil, base64
from playwright.sync_api import sync_playwright
import _commun as C

SORTIE = C.CAPTURES / "nouveau_design"
shutil.rmtree(SORTIE, ignore_errors=True); SORTIE.mkdir(parents=True)
ETATS = [("1_T1", {"mode": "trunk", "ti": 0, "path": []}), ("2_T2", {"mode": "trunk", "ti": 1, "path": []}),
         ("3_T3", {"mode": "trunk", "ti": 2, "path": []}), ("4_T4", {"mode": "trunk", "ti": 3, "path": []}),
         ("5_premier_vote", {"mode": "choose", "ti": 3, "path": []}),
         ("6_apres_3_votes", {"mode": "answer", "ti": 3, "path": ["I1", "L2", "L3"]}),
         ("7_fin", {"mode": "end", "ti": 3, "path": ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"]})]
Q = {"I1": "Quelle infrastructure de votre quotidien vous semble la plus fragile ?", "A1": "Que mangeriez-vous si les approvisionnements s'arrêtaient pendant une semaine ?",
     "L2": "Que ressentez-vous quand vous regardez la mer, ces temps-ci ?", "I2": "Qu'est-ce qui, dans votre commune, fonctionne grâce à l'entraide plutôt qu'au réseau ?",
     "L3": "Quel geste simple protégerait le plus le littoral près de chez vous ?", "A3": "Quel produit local aimeriez-vous retrouver plus souvent dans votre assiette ?"}
TRONC = ["Commençons par vous : qu'est-ce qui vous a amené ici ce soir ?", "Qu'appelle-t-on la robustesse ?", "Que vous évoque le mot « territoire » ?", "Quelle est la première question que vous aimeriez poser ?"]

def repere(page):
    """Échelle et origine du dessin (900 x 968 unités) dans la page, même quand l'arbre est centré dans une zone plus large."""
    b = page.evaluate("(() => { const r = document.getElementById('svg').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
    sc = min(b[2] / 900, b[3] / 968)
    return sc, b[0] + (b[2] - 900 * sc) / 2, b[1] + (b[3] - 968 * sc) / 2


with sync_playwright() as p:
    nav = C.lancer(p)
    C.variante_avec_noms(C.CAPTURES / "variante_noms.html")
    # --- les 7 états, écran 1440x900, mouvement réduit (les notes sont alors posées, bien visibles) ---
    page = C.nouvelle_page(nav, "1440x900")
    page.goto((C.CAPTURES / "variante_noms.html").as_uri()); page.wait_for_timeout(400)
    page.evaluate("([q, t]) => { for (const k in q) ARBRE.questions[k] = q[k]; t.forEach((v, i) => ARBRE.tronc[i] = v); }", [Q, TRONC])
    C.lancer_scene(page)
    for nom, e in ETATS:
        page.evaluate("(e) => applyState(e)", e); page.wait_for_timeout(1400)
        page.screenshot(path=str(SORTIE / f"{nom}.png"))
    # zoom sur la mésange qui chante, et sur le pied du tronc (mention, fleurs)
    sc, ox, oy = repere(page)
    page.screenshot(path=str(SORTIE / "8_zoom_pied_du_tronc.png"), clip={"x": ox + 170 * sc, "y": oy + 860 * sc, "width": 560 * sc, "height": 108 * sc})
    page.context.close()

    # --- les trois passages du tronc, mouvement réel, une image toutes les ~60 ms ---
    page = C.nouvelle_page(nav, "1280x720", reduit=False)
    page.goto((C.CAPTURES / "variante_noms.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page); page.wait_for_timeout(1500)
    sc, ox, oy = repere(page)
    feuilles = {}
    for a, nom in ((0, "loge1_vers_loge2"), (1, "loge2_vers_loge3"), (2, "loge3_vers_loge4")):
        ys = [884, 826, 770, 716]
        y_haut, y_bas = ys[a + 1] - 60, ys[a] + 50
        clip = {"x": ox + 380 * sc, "y": oy + y_haut * sc, "width": 140 * sc, "height": (y_bas - y_haut) * sc}
        cadres = []
        page.keyboard.press("ArrowRight")
        for k in range(16):
            cadres.append((k, page.screenshot(clip=clip)))
        page.wait_for_timeout(1300)
        feuilles[nom] = cadres
    page.context.close()
    # planche contact : une ligne par passage
    html = "<body style='margin:10px;background:#fff;font:13px system-ui'>" + "".join(
        f"<p style='margin:8px 0 2px'><b>{nom.replace('_', ' ')}</b> (images successives, de gauche à droite)</p><div style='display:flex;gap:4px'>" +
        "".join(f"<img style='border:1px solid #ddd' src='data:image/png;base64,{base64.b64encode(png).decode()}'>" for k, png in cadres) + "</div>" for nom, cadres in feuilles.items()) + "</body>"
    planche = C.nouvelle_page(nav, "2400x900"); planche.set_content(html); planche.wait_for_timeout(300)
    planche.screenshot(path=str(SORTIE / "9_passages_du_tronc_images_successives.png"), full_page=True)
    nav.close()
print(sorted(f.name for f in SORTIE.iterdir()))
