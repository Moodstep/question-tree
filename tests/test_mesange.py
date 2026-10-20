"""La mésange : parcours au clavier comparé à la référence, aller-retour avec ←, passages du tronc image par image,
remise à zéro (Maj+R et bouton rond), notes de musique, bouton rond.

 A. Même parcours de 23 gestes au clavier sur la référence et sur l'application : à chaque geste, la position, la loge
    (clip-path) et la pose de la mésange sont identiques ; aux 7 états demandés, l'image est identique au pixel près.
 B. Parcours complet puis retour avec ← jusqu'au tronc : à chaque position précédente, la mésange revient exactement
    où elle était à l'aller.
 C. Les trois passages du tronc (loge 1 à 2, 2 à 3, 3 à 4), en marche avant et arrière, mouvement réel (animations actives) :
    échantillon à chaque image de l'écran. Elle sort par le haut de sa loge, arrive par le bas de la suivante, et n'est
    JAMAIS visible hors d'une ouverture pendant le déplacement (le masque de l'ouverture est toujours posé).
 D. Remise à zéro : Maj+R et petit bouton rond ramènent la mésange dans la loge 1, comme au départ.
 E. Notes de musique : dessinées en SVG (aucun caractère de police), animées, sans effet sur le reste.
 F. Bouton rond en haut à droite : il ne touche ni la mention de licence, ni une carte de question typique.

Usage :  .venv/bin/python tests/test_mesange.py
"""
import sys, base64, json
from playwright.sync_api import sync_playwright
import _commun as C
import comparer_reference as R

SIG_JS = """() => { const m = document.querySelector('#svg .bird'), p = m.firstElementChild;
  // les notes de musique sont dessinées autrement que dans la référence (SVG au lieu de caractères) : on les écarte de la comparaison de pose
  const k = (p.dataset.k || '').replace(/<text class="note[^]*?<\\/text>/g, '').replace(/<g transform="translate\\([^)]*\\)( scale\\([^)]*\\))?"><g class="note[^]*?<\\/g><\\/g>/g, '');
  let h = 0; for (let i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) | 0;
  return [m.style.transform, m.parentElement.getAttribute('clip-path'), k.length + ':' + h]; }"""
ETAT_JS = "() => ({mode, ti, path: path.slice()})"

# 23 gestes : T1 -> T4 (3 flèches), premier vote, puis 8 votes (choix, suivant)
GESTES = (["ArrowRight"] * 4) + sum([[("ArrowUp" if v % 2 == 0 else "ArrowDown"), "ArrowRight"] for v in range(8)], [])
NOMS_ETATS = {0: "T1", 1: "T2", 2: "T3", 3: "T4", 4: "premier vote", 8: "après 3 votes"}   # indice = nombre de gestes faits
FIN = len(GESTES) - 1


def attente(geste, avant):
    return 1250 if avant["mode"] == "trunk" else 120      # un passage du tronc dure 0,98 s ; ailleurs rien d'animé en mouvement réduit


def tester():
    echecs, infos = [], []
    def att(nom, attendu, obtenu):
        if attendu != obtenu: echecs.append(f"{nom} : attendu {str(attendu)[:160]!r}, obtenu {str(obtenu)[:160]!r}")
    with sync_playwright() as p:
        nav = C.lancer(p)
        blank = C.nouvelle_page(nav, "800x600"); blank.goto("about:blank")

        # ================= A. parcours clavier comparé à la référence =================
        ref, app = R.ouvrir(nav, "1280x720")
        for pg in (ref, app): pg.mouse.move(1, 1); pg.wait_for_timeout(1300)
        sigs = {"ref": [], "app": []}
        for i in range(len(GESTES) + 1):
            if i > 0:
                for pg in (ref, app):
                    avant = pg.evaluate(ETAT_JS); pg.keyboard.press(GESTES[i - 1]); pg.wait_for_timeout(attente(GESTES[i - 1], avant))
            sr, sa = ref.evaluate(SIG_JS), app.evaluate(SIG_JS)
            sigs["ref"].append(sr); sigs["app"].append(sa)
            att(f"geste {i} : état du parcours", ref.evaluate(ETAT_JS), app.evaluate(ETAT_JS))
            att(f"geste {i} : position / loge / pose de la mésange", sr, sa)
            if i in NOMS_ETATS or i == len(GESTES):
                nom = NOMS_ETATS.get(i, "fin")
                for pg in (ref, app):
                    if nom == "fin": pg.add_style_tag(content=".note{visibility:hidden}")
                d = R.comparer_png(blank, ref.locator("#svg").screenshot(), app.locator("#svg").screenshot())
                infos.append(f"A. {nom:14s}: image == référence ({d.get('diff')} pixels différents)")
                if d.get("diff") != 0: echecs.append(f"A. {nom} : {d}")
        att("A. aucune erreur JS", [], ref.erreurs + app.erreurs)
        att("A. aucune requête hors fichier local (application)", [], C.requetes_suspectes(app))

        # ================= B. aller-retour avec ← =================
        cle = lambda e: (e["mode"], e["ti"] if e["mode"] == "trunk" else 3, ">".join(e["path"]))
        # on repart du début avec Maj+R ; l'aller est déjà dans sigs["app"] (même parcours) : on reconstitue les états de l'aller
        app.keyboard.press("Shift+R"); app.wait_for_timeout(300)
        aller = {}
        for i in range(len(GESTES) + 1):
            if i > 0:
                avant = app.evaluate(ETAT_JS); app.keyboard.press(GESTES[i - 1]); app.wait_for_timeout(attente(GESTES[i - 1], avant))
            aller[cle(app.evaluate(ETAT_JS))] = app.evaluate(SIG_JS)
        app.keyboard.press("ArrowRight"); app.wait_for_timeout(150)               # 8e réponse -> fin
        aller[cle(app.evaluate(ETAT_JS))] = app.evaluate(SIG_JS)
        att("B. fin de parcours atteinte", "end", app.evaluate(ETAT_JS)["mode"])
        retours, vus = 0, 0
        for _ in range(60):
            avant = app.evaluate(ETAT_JS)
            if avant["mode"] == "trunk" and avant["ti"] == 0: break
            app.keyboard.press("ArrowLeft"); app.wait_for_timeout(1250 if avant["mode"] == "trunk" else 150)
            e = app.evaluate(ETAT_JS); k = cle(e); retours += 1
            if k in aller:
                vus += 1
                att(f"B. retour vers {k[0]} {k[1]} {k[2][-8:]} : la mésange est où elle était à l'aller", aller[k], app.evaluate(SIG_JS))
            else:
                echecs.append(f"B. état {k} atteint au retour mais absent de l'aller")
        att("B. on est revenu au tronc, loge 1", ("trunk", 0), (app.evaluate(ETAT_JS)["mode"], app.evaluate(ETAT_JS)["ti"]))
        infos.append(f"B. retour avec ← : {retours} gestes en arrière, {vus} positions comparées à l'aller")

        # ================= D. remise à zéro =================
        depart = aller[("trunk", 0, "")]
        for geste in ("Shift+R", "bouton"):
            for _ in range(7): app.keyboard.press("ArrowRight"); app.wait_for_timeout(1250 if _ < 3 else 150)
            for _ in range(2): app.keyboard.press("ArrowUp" if _ == 0 else "ArrowRight"); app.wait_for_timeout(150)
            if geste == "Shift+R": app.keyboard.press("Shift+R")
            else: app.evaluate("document.getElementById('rst').click()")      # le banc cache le bouton pour comparer le dessin ; le vrai clic de souris est testé en F
            app.wait_for_timeout(1300)
            att(f"D. {geste} : retour au départ (tronc, loge 1)", ("trunk", 0, []), (app.evaluate(ETAT_JS)["mode"], app.evaluate(ETAT_JS)["ti"], app.evaluate(ETAT_JS)["path"]))
            att(f"D. {geste} : la mésange est comme au départ", depart, app.evaluate(SIG_JS))
        infos.append("D. Maj+R et bouton rond : la mésange revient dans la loge 1, comme au départ")
        ref.context.close(); app.context.close()

        # ================= C. passages du tronc, mouvement réel =================
        passages = [(0, 1, "ArrowRight"), (1, 2, "ArrowRight"), (2, 3, "ArrowRight"), (3, 2, "ArrowLeft"), (2, 1, "ArrowLeft"), (1, 0, "ArrowLeft")]
        C.variante_avec_noms(C.CAPTURES / "variante_noms.html")
        page = C.nouvelle_page(nav, "1280x720", reduit=False)
        page.goto((C.CAPTURES / "variante_noms.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page); page.wait_for_timeout(1500)
        for a, b, touche in passages:
            if page.evaluate(ETAT_JS)["ti"] != a:
                echecs.append(f"C. point de départ inattendu {page.evaluate(ETAT_JS)} pour {a}->{b}"); break
            page.evaluate("""() => { window.__s = []; const t0 = performance.now(); const m = document.querySelector('#svg .bird');
              (function f() { const y = new DOMMatrix(getComputedStyle(m).transform).m42;      // position réellement animée, pas la valeur demandée
                __s.push([Math.round(performance.now() - t0), m.parentElement.getAttribute('clip-path'), y, m.getBoundingClientRect().top]);
                if (performance.now() - t0 < 1700) requestAnimationFrame(f); })(); }""")
            page.keyboard.press(touche); page.wait_for_timeout(1900)
            s = page.evaluate("__s")
            avant_fin = [x for x in s if 20 <= x[0] <= 940]      # pendant le déplacement (la fin du second temps est à 380 + 600 ms)
            clips = [x[1] for x in avant_fin]
            nom = f"C. loge {a+1} -> {b+1} ({'avant' if touche == 'ArrowRight' else 'arrière'})"
            att(f"{nom} : un masque d'ouverture est posé à chaque image pendant le déplacement", 0, sum(1 for c in clips if not c))
            ordre = []
            for c in clips:
                if c and (not ordre or ordre[-1] != c): ordre.append(c)
            att(f"{nom} : masque de la loge de départ, puis masque de la loge d'arrivée, une seule fois", [f"url(#hc{a})", f"url(#hc{b})"], ordre)
            ys = [x[2] for x in avant_fin if x[2] == x[2]]
            sens = -1 if touche == "ArrowRight" else 1                      # avant : elle monte (y diminue) ; arrière : elle descend
            # temps 1 : jusqu'au changement de masque, elle s'éloigne de sa loge dans le bon sens ; temps 2 : elle arrive par l'autre côté
            i_chg = next((i for i, c in enumerate(clips) if c == f"url(#hc{b})"), None)
            if i_chg is None: echecs.append(f"{nom} : pas de changement de masque"); continue
            t1, t2 = ys[:i_chg], ys[i_chg:]
            att(f"{nom} : temps 1, elle sort par le {'haut' if sens < 0 else 'bas'} de sa loge (mouvement monotone)", True, all((t1[k + 1] - t1[k]) * sens >= -0.01 for k in range(len(t1) - 1)))
            att(f"{nom} : temps 1, elle s'éloigne d'au moins 33 unités sur les 46 prévues avant le changement de masque (le reste est la fin d'une accélération)", True, 33 <= abs(t1[-1] - t1[0]) <= 47)
            att(f"{nom} : temps 2, elle arrive par le {'bas' if sens < 0 else 'haut'} de la loge suivante (mouvement monotone, même sens)", True, all((t2[k + 1] - t2[k]) * sens >= -0.01 for k in range(len(t2) - 1)))
            final = fin_y = s[-1][2]
            att(f"{nom} : au changement de masque elle repart de 34 unités AU-DELÀ de sa place (côté intérieur du tronc), puis s'y pose", True,
                abs((t2[0] - final) - (-sens * 34)) < 12 and abs(t2[-1] - final) < 1.5)
            fin = s[-1]
            infos.append(f"{nom}: {len(s)} images échantillonnées, masques {ordre}, arrivée y={fin[2]:.0f}, masque final {fin[1]}")
        att("C. aucune erreur JS", [], page.erreurs)
        att("C. aucune requête hors fichier local", [], C.requetes_suspectes(page))
        page.context.close()

        # ================= E. notes de musique (SVG), F. bouton rond =================
        for taille in ("1920x1080", "1280x720", "1024x768"):
            page = C.nouvelle_page(nav, taille, reduit=False)
            page.goto((C.CAPTURES / "variante_noms.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page)
            page.evaluate("applyState({mode:'end', ti:3, path:['I1','I2','I3','I4','I5','I6','I7','I8']})"); page.wait_for_timeout(2600)
            if taille == "1280x720":
                att("E. aucune note écrite avec une police (♪ ♫) dans le dessin", 0, page.evaluate("[...document.querySelectorAll('#svg text')].filter(t => /[\\u266a\\u266b]/.test(t.textContent)).length"))
                att("E. deux groupes de notes animés", 2, page.locator("#svg g.note").count())
                att("E. les notes sont des tracés (pas de texte)", True, page.locator("#svg g.note path, #svg g.note ellipse").count() >= 6)
                op = page.evaluate("[...document.querySelectorAll('#svg g.note')].map(g => +getComputedStyle(g).opacity)")
                att("E. les notes sont animées (opacité entre 0 et 1 pendant l'animation)", True, any(0 <= o <= 1 for o in op))
                page.screenshot(path=str(C.CAPTURES / "pour_joanna_mesange_fin.png"))
            r = page.evaluate("""() => { const b = document.getElementById('rst').getBoundingClientRect(), W = innerWidth;
                const lic = [...document.querySelectorAll('#svg text')].find(t => t.textContent === 'CC BY-SA MOODSTEP' && t.getAttribute('fill') === '#3a2a1a').getBoundingClientRect();
                const cartes = [...document.querySelectorAll('#panel .card')].map(c => c.getBoundingClientRect());
                const inter = (a, c) => !(a.right < c.left || a.left > c.right || a.bottom < c.top || a.top > c.bottom);
                return {haut: Math.round(b.top), droite: Math.round(W - b.right), touche_licence: inter(b, lic), touche_carte: cartes.some(c => inter(b, c)), visible: b.width > 0}; }""")
            att(f"F. {taille} : bouton rond en haut à droite", True, r["visible"] and r["haut"] < 40 and r["droite"] < 40)
            att(f"F. {taille} : le bouton rond ne cache plus la mention (fin du parcours)", False, r["touche_licence"])
            for etat, nom in (({"mode": "choose", "ti": 3, "path": []}, "premier vote"), ({"mode": "answer", "ti": 3, "path": ["I1", "I2"]}, "réponse")):
                page.evaluate("(e) => applyState(e)", etat); page.wait_for_timeout(300)
                touche = page.evaluate("""() => { const b = document.getElementById('rst').getBoundingClientRect();
                  return [...document.querySelectorAll('#panel .card')].some(c => { const a = c.getBoundingClientRect(); return !(b.right < a.left || b.left > a.right || b.bottom < a.top || b.top > a.bottom); }); }""")
                att(f"F. {taille} : le bouton rond ne touche pas une carte ({nom}, texte d'exemple)", False, touche)
            # le rond de gauche (sortie) : en haut à gauche, ne cache ni la mention de licence ni une carte, aux deux états les plus chargés
            for etat, nom in (({"mode": "end", "ti": 3, "path": ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"]}, "fin"), ({"mode": "choose", "ti": 3, "path": []}, "premier vote"), ({"mode": "answer", "ti": 3, "path": ["I1", "I2"]}, "réponse")):
                page.evaluate("(e) => applyState(e)", etat); page.wait_for_timeout(300)
                g = page.evaluate("""() => { const b = document.getElementById('sortie').getBoundingClientRect();
                    const lic = [...document.querySelectorAll('#svg text')].find(t => t.textContent === 'CC BY-SA MOODSTEP' && t.getAttribute('fill') === '#3a2a1a').getBoundingClientRect();
                    const inter = (a, c) => !(a.right < c.left || a.left > c.right || a.bottom < c.top || a.top > c.bottom);
                    return {haut: Math.round(b.top), gauche: Math.round(b.left), visible: b.width > 0, licence: inter(b, lic),
                            carte: [...document.querySelectorAll('#panel .card')].some(c => inter(b, c.getBoundingClientRect()))}; }""")
                att(f"F. {taille} ({nom}) : bouton de sortie visible en haut à gauche, sans toucher licence ni carte", (True, False, False), (g["visible"] and g["haut"] < 40 and g["gauche"] < 40, g["licence"], g["carte"]))
            att(f"F. {taille} : le bouton rond reste cliquable (revient au tronc)", ("trunk", 0), (page.click("#rst"), page.wait_for_timeout(300), tuple(page.evaluate("[mode, ti]")))[2])
            att(f"E/F. {taille} : aucune erreur JS", [], page.erreurs)
            page.context.close()
        # ================= G. relance après un retour par E, en plein milieu du tronc =================
        page = C.nouvelle_page(nav, "1280x720", reduit=False)
        page.goto((C.CAPTURES / "variante_noms.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page); page.wait_for_timeout(1400)
        depart = page.evaluate(SIG_JS)
        for _ in range(2): page.keyboard.press("ArrowRight"); page.wait_for_timeout(1250)           # on est dans la loge 3
        att("G. avant le retour : la mésange est dans la loge 3", 2, page.evaluate(ETAT_JS)["ti"])
        page.keyboard.press("ArrowRight")                                                           # passage en cours (loge 3 vers 4)...
        page.wait_for_timeout(150); page.keyboard.press("e"); page.wait_for_timeout(200); page.keyboard.press("o"); page.wait_for_timeout(300)   # ...et on quitte au milieu
        att("G. retour à la préparation", True, page.locator("#prepa").is_visible())
        page.click("#btn-lancer"); page.wait_for_timeout(150)
        if page.locator("#dlg-manques[open]").count(): page.click("#dlg-manques button[value=lancer]")
        page.wait_for_function("ecran === 'scene'")                  # on échantillonne une fois la scène affichée (cachée, la position lue vaudrait 0)
        page.evaluate("""() => { window.__g = []; const t0 = performance.now(); const m = document.querySelector('#svg .bird');
          (function f() { __g.push([Math.round(performance.now() - t0), m.parentElement.getAttribute('clip-path'), new DOMMatrix(getComputedStyle(m).transform).m42, m.firstElementChild.dataset.k.length]);
            if (performance.now() - t0 < 1500) requestAnimationFrame(f); })(); }""")
        page.wait_for_timeout(1700)
        g = page.evaluate("__g")
        att("G. relance : état de départ (tronc, loge 1)", (  "trunk", 0), tuple(page.evaluate("[mode, ti]")))
        att("G. relance : la mésange ne bouge pas pendant 1,5 s (aucune montée rejouée)", 1, len({x[2] for x in g}))
        att("G. relance : même loge et même pose qu'au premier départ", (depart[1], depart[2]), (page.evaluate(SIG_JS)[1], page.evaluate(SIG_JS)[2]))
        infos.append(f"G. retour par E en plein passage puis relance : {len(g)} images, position unique {sorted({x[2] for x in g})}")
        att("G. aucune erreur JS", [], page.erreurs)
        page.context.close()
        nav.close()
    for l in infos: print("  " + l)
    return echecs


if __name__ == "__main__":
    echecs = tester()
    sys.exit(0 if C.bilan("mésange (parcours, retour, passages du tronc, remise à zéro, notes, bouton rond)", echecs) else 1)
