"""Captures du chêne pour Joanna : les 7 états, un zoom sur le pied du tronc, et les passages du tronc image par image. Sortie : tests/captures/chene/"""
import shutil, base64
from playwright.sync_api import sync_playwright
import _commun as C

SORTIE = C.CAPTURES / "chene"
shutil.rmtree(SORTIE, ignore_errors=True); SORTIE.mkdir(parents=True)
ETATS = [("1_T1", {"mode": "trunk", "ti": 0, "path": []}), ("2_T2", {"mode": "trunk", "ti": 1, "path": []}),
         ("3_T3", {"mode": "trunk", "ti": 2, "path": []}), ("4_T4", {"mode": "trunk", "ti": 3, "path": []}),
         ("5_premier_vote", {"mode": "choose", "ti": 3, "path": []}),
         ("6_apres_3_votes", {"mode": "answer", "ti": 3, "path": ["A1", "A2", "A3"]}),
         ("7_fin", {"mode": "end", "ti": 3, "path": ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]})]
NOMS = ["Le travail", "Le quotidien", "Le territoire", "Demain"]
Q = {"A1": "Quel métier vous semble le plus utile à votre commune, et pourquoi ?", "D1": "Que ferait votre territoire si demain tout devait s'y produire ?",
     "A2": "Quelle compétence aimeriez-vous transmettre avant de partir à la retraite ?", "A3": "Qu'est-ce qui vous fait rester, dans votre travail, malgré tout ?"}
TRONC = ["Commençons par vous : qu'est-ce qui vous a amené ici ce soir ?", "Qu'appelle-t-on la robustesse ?", "Que vous évoque le mot « territoire » ?", "Quelle est la première question que vous aimeriez poser ?"]


def repere(page):
    b = page.evaluate("(() => { const r = document.getElementById('svg').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
    sc = min(b[2] / 900, b[3] / 968)
    return sc, b[0] + (b[2] - 900 * sc) / 2, b[1] + (b[3] - 968 * sc) / 2


with sync_playwright() as p:
    nav = C.lancer(p)
    C.variante_avec_noms(C.CAPTURES / "variante_noms_chene.html", "chene")
    page = C.nouvelle_page(nav, "1440x900")
    page.goto((C.CAPTURES / "variante_noms_chene.html").as_uri()); page.wait_for_timeout(400)
    page.evaluate("([q, t, n]) => { for (const k in q) ARBRE.questions[k] = q[k]; t.forEach((v, i) => ARBRE.tronc[i] = v); ARBRE.themes.forEach((th, i) => th.nom = n[i]); vue = null; vueCle = null; }", [Q, TRONC, NOMS])
    C.lancer_scene(page)
    for nom, e in ETATS:
        page.evaluate("(e) => applyState(e)", e); page.wait_for_timeout(1400)
        page.screenshot(path=str(SORTIE / f"{nom}.png"))
    sc, ox, oy = repere(page)
    page.evaluate("applyState({mode:'trunk', ti:0, path:[]})"); page.wait_for_timeout(1200)
    page.screenshot(path=str(SORTIE / "8_zoom_pied_du_tronc.png"), clip={"x": ox + 200 * sc, "y": oy + 840 * sc, "width": 500 * sc, "height": 128 * sc})
    # le cas du dernier gland : l'écureuil près de D7 recouvre C7 (non choisi, à 40 %)
    page.evaluate("applyState({mode:'answer', ti:3, path:['A1','A2','A3','A4','A5','C6','D7']})"); page.wait_for_timeout(1300)
    page.screenshot(path=str(SORTIE / "9_cas_D7_zoom.png"), clip={"x": ox + 560 * sc, "y": oy + 70 * sc, "width": 300 * sc, "height": 240 * sc})
    page.context.close()

    page = C.nouvelle_page(nav, "1280x720", reduit=False)
    page.goto((C.CAPTURES / "variante_noms_chene.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page); page.wait_for_timeout(1500)
    sc, ox, oy = repere(page)
    ys = [888, 836, 784, 732]; feuilles = {}
    for a, nom in ((0, "loge1_vers_loge2"), (1, "loge2_vers_loge3"), (2, "loge3_vers_loge4")):
        y_haut, y_bas = ys[a + 1] - 70, ys[a] + 60
        clip = {"x": ox + 370 * sc, "y": oy + y_haut * sc, "width": 160 * sc, "height": (y_bas - y_haut) * sc}
        cadres = []; page.keyboard.press("ArrowRight")
        for k in range(16): cadres.append((k, page.screenshot(clip=clip)))
        page.wait_for_timeout(1300); feuilles[nom] = cadres
    page.context.close()
    html = "<body style='margin:10px;background:#fff;font:13px system-ui'>" + "".join(
        f"<p style='margin:8px 0 2px'><b>{nom.replace('_', ' ')}</b> (images successives, de gauche à droite)</p><div style='display:flex;gap:4px'>" +
        "".join(f"<img style='border:1px solid #ddd' src='data:image/png;base64,{base64.b64encode(png).decode()}'>" for k, png in cadres) + "</div>" for nom, cadres in feuilles.items()) + "</body>"
    planche = C.nouvelle_page(nav, "2600x900"); planche.set_content(html); planche.wait_for_timeout(300)
    planche.screenshot(path=str(SORTIE / "10_passages_du_tronc_images_successives.png"), full_page=True)
    nav.close()
print(sorted(f.name for f in SORTIE.iterdir()))
