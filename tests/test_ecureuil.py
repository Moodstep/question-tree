"""L'écureuil du chêne : parcours clavier comparé à la référence, aller-retour avec ←, passages du tronc image par image, remise à zéro,
et la règle « pendant un vote, il ne se pose jamais sur un lien qui part vers l'une des deux questions proposées ».

 A. Même parcours de 18 gestes au clavier sur la référence et sur l'application : à chaque geste, la position, la loge (masque), la pose
    et le calque des pattes sont identiques ; aux états demandés, l'image est identique au pixel près.
 B. Parcours complet puis retour avec ← jusqu'au tronc : à chaque position précédente, l'écureuil revient exactement où il était.
 C. Les trois passages du tronc (et leurs inverses), en mouvement réel, échantillonnés à chaque image de l'écran : il sort par le haut de sa
    loge de dos (la queue pend en dernier), arrive par le bas de la suivante, et n'est JAMAIS visible hors d'une ouverture pendant le déplacement.
 D. Remise à zéro (Maj+R et petit bouton rond) : retour dans la loge 1, comme au départ.
 E. Pendant chaque vote, sur TOUS les états de vote possibles : il n'est jamais sur un lien qui part vers l'une des deux questions proposées,
    SAUF au vote qui suit le tout premier gland (A1 ou D1) : aucun lien n'y arrive, et Joanna veut qu'il soit « toujours assis sur un lien »
    (demande du 05/10/2026, contre la référence qui l'asseyait à côté du gland). Il s'assoit alors au pied de la fourche des deux liens de départ.
 F. Relance après un retour par E en plein passage : aucun passage rejoué.
 G. Il ne cache aucun gland (tous les états de vote et de réponse).
 H. Il est toujours assis sur un lien : sur les 380 états de réponse, de vote et de fin (hors tronc), ses pattes sont à moins de 3 unités d'un lien.
    EXCEPTION (questions subsidiaires, 05/10/2026) : pendant une question subsidiaire (mode « sub »), aucun lien n'arrive au gland tiré : l'écureuil
    s'assoit À CÔTÉ du gland, pas sur un lien. Cet état n'est pas dans les 380 ci-dessus ; il est vérifié par tests/test_sous_questions.py (C).

Usage :  .venv/bin/python tests/test_ecureuil.py
"""
import sys, re, math
from playwright.sync_api import sync_playwright
import _commun as C
import comparer_reference as R

SIG_JS = """() => { const m = document.querySelector('#svg .bird'), p = m.firstElementChild;
  const hash = k => { let h = 0; for (let i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) | 0; return k.length + ':' + h; };
  const bras = [...document.querySelectorAll('#svg > g[pointer-events=none]')].find(g => !g.querySelector('path[fill="url(#lipShade)"]'));
  return [m.style.transform, m.parentElement.getAttribute('clip-path'), hash(p.dataset.k || ''), bras ? bras.getAttribute('transform') + '|' + hash(bras.innerHTML) : '']; }"""
ETAT_JS = "() => ({mode, ti, path: path.slice()})"
GESTES = (["ArrowRight"] * 4) + sum([[("ArrowUp" if v % 2 == 0 else "ArrowDown"), "ArrowRight"] for v in range(7)], [])
NOMS_ETATS = {0: "T1", 1: "T2", 2: "T3", 3: "T4", 4: "premier vote", 9: "après 3 votes"}


def attente(avant):
    return 1250 if avant["mode"] == "trunk" else 120


def tester():
    echecs, infos = [], []
    def att(nom, attendu, obtenu):
        if attendu != obtenu: echecs.append(f"{nom} : attendu {str(attendu)[:150]!r}, obtenu {str(obtenu)[:150]!r}")
    with sync_playwright() as p:
        nav = C.lancer(p)
        blank = C.nouvelle_page(nav, "800x600"); blank.goto("about:blank")

        # ================= A. parcours clavier comparé à la référence =================
        ref, app = R.ouvrir(nav, "1280x720", "chene")
        for pg in (ref, app): pg.mouse.move(1, 1); pg.wait_for_timeout(1300)
        for i in range(len(GESTES) + 1):
            if i > 0:
                for pg in (ref, app):
                    avant = pg.evaluate(ETAT_JS); pg.keyboard.press(GESTES[i - 1]); pg.wait_for_timeout(attente(avant))
            sr, sa = ref.evaluate(SIG_JS), app.evaluate(SIG_JS)
            er, ea = ref.evaluate(ETAT_JS), app.evaluate(ETAT_JS)
            att(f"geste {i} : état du parcours (même chemin, identifiants traduits)", [R.vers_lettres(q) for q in er["path"]], ea["path"])
            if ea["mode"] == "choose" and len(ea["path"]) == 1:      # écart voulu (voir E et H) : on ne compare pas ici la position à la référence
                infos.append(f"A. geste {i} (vote après le 1er gland) : place différente de la référence VOULUE, voir E et H")
            else:
                att(f"geste {i} : position / loge / pose / pattes de l'écureuil", sr, sa)
            if i in NOMS_ETATS or i == len(GESTES):
                nom = NOMS_ETATS.get(i, "fin")
                d = R.comparer_png(blank, ref.locator("#svg").screenshot(), app.locator("#svg").screenshot())
                infos.append(f"A. {nom:14s}: image == référence ({d.get('diff')} pixels différents)")
                if d.get("diff") != 0: echecs.append(f"A. {nom} : {d}")
        att("A. aucune erreur JS", [], ref.erreurs + app.erreurs)
        att("A. aucune requête hors fichier local (application)", [], C.requetes_suspectes(app))

        # ================= B. aller-retour avec ← =================
        cle = lambda e: (e["mode"], e["ti"] if e["mode"] == "trunk" else 3, ">".join(e["path"]))
        app.keyboard.press("Shift+R"); app.wait_for_timeout(300)
        aller = {}
        for i in range(len(GESTES) + 1):
            if i > 0:
                avant = app.evaluate(ETAT_JS); app.keyboard.press(GESTES[i - 1]); app.wait_for_timeout(attente(avant))
            aller[cle(app.evaluate(ETAT_JS))] = app.evaluate(SIG_JS)
        att("B. fin de parcours atteinte", "end", app.evaluate(ETAT_JS)["mode"])
        retours, vus = 0, 0
        for _ in range(60):
            avant = app.evaluate(ETAT_JS)
            if avant["mode"] == "trunk" and avant["ti"] == 0: break
            app.keyboard.press("ArrowLeft"); app.wait_for_timeout(1250 if avant["mode"] == "trunk" else 150)
            k = cle(app.evaluate(ETAT_JS)); retours += 1
            if k in aller: vus += 1; att(f"B. retour vers {k[0]} {k[1]} {k[2][-8:]} : l'écureuil est où il était à l'aller", aller[k], app.evaluate(SIG_JS))
            else: echecs.append(f"B. état {k} atteint au retour mais absent de l'aller")
        att("B. on est revenu au tronc, loge 1", ("trunk", 0), (app.evaluate(ETAT_JS)["mode"], app.evaluate(ETAT_JS)["ti"]))
        infos.append(f"B. retour avec ← : {retours} gestes en arrière, {vus} positions comparées à l'aller")

        # ================= D. remise à zéro =================
        depart = aller[("trunk", 0, "")]
        for geste in ("Shift+R", "bouton"):
            for k in range(7): app.keyboard.press("ArrowRight"); app.wait_for_timeout(1250 if k < 3 else 150)
            for k in range(2): app.keyboard.press("ArrowUp" if k == 0 else "ArrowRight"); app.wait_for_timeout(150)
            if geste == "Shift+R": app.keyboard.press("Shift+R")
            else: app.evaluate("document.getElementById('rst').click()")
            app.wait_for_timeout(1300)
            att(f"D. {geste} : retour au départ (tronc, loge 1)", ("trunk", 0, []), (app.evaluate(ETAT_JS)["mode"], app.evaluate(ETAT_JS)["ti"], app.evaluate(ETAT_JS)["path"]))
            att(f"D. {geste} : l'écureuil est comme au départ", depart, app.evaluate(SIG_JS))
        infos.append("D. Maj+R et bouton rond : l'écureuil revient dans la loge 1, comme au départ")
        ref.context.close(); app.context.close()

        # ================= C. passages du tronc, mouvement réel =================
        passages = [(0, 1, "ArrowRight"), (1, 2, "ArrowRight"), (2, 3, "ArrowRight"), (3, 2, "ArrowLeft"), (2, 1, "ArrowLeft"), (1, 0, "ArrowLeft")]
        page = C.nouvelle_page(nav, "1280x720", reduit=False)
        page.goto((C.CAPTURES / "variante_noms_chene.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page); page.wait_for_timeout(1500)
        for a, b, touche in passages:
            if page.evaluate(ETAT_JS)["ti"] != a: echecs.append(f"C. point de départ inattendu pour {a}->{b}"); break
            page.evaluate("""() => { window.__s = []; const t0 = performance.now(); const m = document.querySelector('#svg .bird');
              (function f() { const y = new DOMMatrix(getComputedStyle(m).transform).m42;
                __s.push([Math.round(performance.now() - t0), m.parentElement.getAttribute('clip-path'), y, m.firstElementChild.dataset.k.length]);
                if (performance.now() - t0 < 1700) requestAnimationFrame(f); })(); }""")
            page.keyboard.press(touche); page.wait_for_timeout(1900)
            s = page.evaluate("__s"); mouv = [x for x in s if 20 <= x[0] <= 940]; clips = [x[1] for x in mouv]
            nom = f"C. loge {a+1} -> {b+1} ({'avant' if touche == 'ArrowRight' else 'arrière'})"
            att(f"{nom} : un masque d'ouverture est posé à chaque image pendant le déplacement", 0, sum(1 for c in clips if not c))
            ordre = []
            for c in clips:
                if c and (not ordre or ordre[-1] != c): ordre.append(c)
            att(f"{nom} : masque de la loge de départ, puis masque de la loge d'arrivée, une seule fois", [f"url(#hc{a})", f"url(#hc{b})"], ordre)
            i_chg = next((i for i, c in enumerate(clips) if c == f"url(#hc{b})"), None)
            if i_chg is None: echecs.append(f"{nom} : pas de changement de masque"); continue
            ys = [x[2] for x in mouv]; sens = -1 if touche == "ArrowRight" else 1
            t1, t2 = ys[:i_chg], ys[i_chg:]
            att(f"{nom} : temps 1, il sort par le {'haut' if sens < 0 else 'bas'} de sa loge (mouvement monotone)", True, all((t1[k + 1] - t1[k]) * sens >= -0.01 for k in range(len(t1) - 1)))
            att(f"{nom} : temps 1, il s'éloigne d'au moins 55 unités sur les 72 prévues avant le changement de masque", True, 55 <= abs(t1[-1] - t1[0]) <= 73)
            att(f"{nom} : temps 1, il garde la pose « de dos, en train de grimper » (queue pendante, donc la queue sort en dernier)", 1, len({x[3] for x in mouv[:i_chg]}))
            att(f"{nom} : temps 2, il arrive par le {'bas' if sens < 0 else 'haut'} de la loge suivante (mouvement monotone)", True, all((t2[k + 1] - t2[k]) * sens >= -0.01 for k in range(len(t2) - 1)))
            final = s[-1][2]
            att(f"{nom} : au changement de masque il repart de 58 unités AU-DELÀ de sa place (côté intérieur du tronc), puis s'y pose", True, abs((t2[0] - final) - (-sens * 58)) < 15 and abs(t2[-1] - final) < 1.5)
            att(f"{nom} : au changement de masque la pose change (il se montre de face, la tête d'abord)", True, mouv[i_chg][3] != mouv[i_chg - 1][3])
            infos.append(f"{nom}: {len(s)} images échantillonnées, masques {ordre}, arrivée y={final:.0f}, masque final {s[-1][1]}")
        att("C. aucune erreur JS", [], page.erreurs)
        att("C. aucune requête hors fichier local", [], C.requetes_suspectes(page))
        page.context.close()

        # ================= F. relance après un retour par E en plein passage =================
        page = C.nouvelle_page(nav, "1280x720", reduit=False)
        page.goto((C.CAPTURES / "variante_noms_chene.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page); page.wait_for_timeout(1400)
        depart = page.evaluate(SIG_JS)
        for _ in range(2): page.keyboard.press("ArrowRight"); page.wait_for_timeout(1250)
        page.keyboard.press("ArrowRight"); page.wait_for_timeout(150); page.keyboard.press("e"); page.wait_for_timeout(200); page.keyboard.press("o"); page.wait_for_timeout(300)
        page.click("#btn-lancer"); page.wait_for_timeout(150)
        if page.locator("#dlg-manques[open]").count(): page.click("#dlg-manques button[value=lancer]")
        page.wait_for_function("ecran === 'scene'")
        page.evaluate("""() => { window.__g = []; const t0 = performance.now(); const m = document.querySelector('#svg .bird');
          (function f() { __g.push([Math.round(performance.now() - t0), m.parentElement.getAttribute('clip-path'), new DOMMatrix(getComputedStyle(m).transform).m42]);
            if (performance.now() - t0 < 1500) requestAnimationFrame(f); })(); }""")
        page.wait_for_timeout(1700); g = page.evaluate("__g")
        att("F. relance : état de départ (tronc, loge 1)", ("trunk", 0), tuple(page.evaluate("[mode, ti]")))
        att("F. relance : l'écureuil ne bouge pas pendant 1,5 s (aucun passage rejoué)", 1, len({x[2] for x in g}))
        att("F. relance : même loge et même pose qu'au premier départ", (depart[1], depart[2]), (page.evaluate(SIG_JS)[1], page.evaluate(SIG_JS)[2]))
        att("F. aucune erreur JS", [], page.erreurs)
        page.context.close()

        # ================= E et G. sur TOUS les états de vote et de réponse =================
        page = C.nouvelle_page(nav, "1280x720")
        page.goto((C.CAPTURES / "variante_noms_chene.html").as_uri()); page.wait_for_timeout(400); C.lancer_scene(page); page.wait_for_timeout(1300)
        dess = page.evaluate("""() => { const svg = document.getElementById('svg'), gr = [...svg.children];
          const olives = gr.find(e => e.tagName.toLowerCase() === 'g' && e.querySelector('title'));
          const glands = {}; olives.querySelectorAll(':scope > g').forEach(g => { const m = g.getAttribute('transform').match(/translate\\(([-\\d.]+) ([-\\d.]+)\\)/); glands[g.querySelector('title').textContent] = [+m[1], +m[2]]; });
          const liens = gr.filter(e => e.tagName.toLowerCase() === 'g' && e.getAttribute('stroke-linecap') === 'round');
          return {glands, liens: [...liens[liens.length - 1].querySelectorAll('path')].map(p => p.getAttribute('d')), structure: D.map(d => ({id: d.id, stay: d.stay, change: d.change, step: d.step})), depart: FICHE.depart}; }""")
        G = dess["glands"]
        def pts(d):
            n = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]; sx, sy, c1x, c1y, c2x, c2y, ex, ey = n
            return (sx, sy, ex, ey), [((1-k/80)**3*sx + 3*(1-k/80)**2*(k/80)*c1x + 3*(1-k/80)*(k/80)**2*c2x + (k/80)**3*ex, (1-k/80)**3*sy + 3*(1-k/80)**2*(k/80)*c1y + 3*(1-k/80)*(k/80)**2*c2y + (k/80)**3*ey) for k in range(81)]
        near = lambda x, y, dy: min(G, key=lambda g: math.hypot(G[g][0] - x, G[g][1] + dy - y))
        LIENS = {}
        for d in dess["liens"]:
            (sx, sy, ex, ey), P = pts(d); LIENS[(near(sx, sy, -8), near(ex, ey, 8))] = P
        dpoly = lambda x, y, P: min(math.hypot(x - a, y - b) for a, b in P)
        by = {d["id"]: d for d in dess["structure"]}
        prefixes = []
        def explorer(path):
            prefixes.append(list(path))
            d = by[path[-1]] if path else None
            if path and d.get("stay") is None: return
            for nxt in (dess["depart"] if not path else [d["stay"], d["change"]]): explorer(path + [nxt])
        explorer([])
        votes = [p_ for p_ in prefixes if len(p_) < 7]            # états de vote : 0 à 6 questions déjà choisies
        reponses = [p_ for p_ in prefixes if len(p_) >= 1]
        pire, trop_pres, sur_le_lien, fourches = 1e9, [], [], []
        for chemin in votes:
            page.evaluate("(c) => { delete panel.dataset.k; applyState({mode:'choose', ti:3, path:c}); }", chemin)
            if not chemin: continue                                  # premier vote : devant la loge du haut, pas de lien en jeu
            x, y = map(float, re.search(r"translate\(([-\d.]+)px,\s*([-\d.]+)px\)", page.evaluate("document.querySelector('#svg .bird').style.transform")).groups())
            if len(chemin) == 1:                                    # vote qui suit le 1er gland : aucun lien d'arrivée, il est assis au pied de la fourche
                d2 = sorted(dpoly(x, y, LIENS[(chemin[-1], nxt)]) for nxt in (by[chemin[-1]]["stay"], by[chemin[-1]]["change"]))
                fourches.append((chemin[0], round(d2[0], 1), round(d2[1], 1)))
                continue
            for nxt in (by[chemin[-1]]["stay"], by[chemin[-1]]["change"]):
                dd = dpoly(x, y, LIENS[(chemin[-1], nxt)]); pire = min(pire, dd)
                if dd < 14: trop_pres.append((">".join(chemin), nxt, round(dd, 1)))
                if dd < 5: sur_le_lien.append((">".join(chemin), nxt, round(dd, 1)))
        infos.append(f"E. {len(votes)} états de vote parcourus ; distance minimale entre l'écureuil et un lien vers une question proposée : {pire:.1f} unités ; trop près (< 14) : {len(trop_pres)}")
        att("E. pendant un vote, jamais SUR un lien qui part vers l'une des deux questions proposées (pattes à moins de 5 unités de ce lien ; demi-épaisseur du lien allumé : 3,75)", [], sur_le_lien[:5])
        att("E. au vote qui suit le 1er gland (A1, D1) : assis SUR l'un des deux liens de départ (pattes à moins de 3 unités de l'un d'eux)", [], [f for f in fourches if not f[1] < 3])
        infos.append(f"E. vote après le 1er gland : (gland, distance au lien le plus proche, distance à l'autre lien) = {fourches}")
        infos.append(f"E. (à titre d'information) pattes à moins de 14 unités d'un tel lien : {len(trop_pres)} cas sur {len(votes)-1} états, le plus proche à {pire:.1f}")
        # H. toujours assis sur un lien, sur tous les états de réponse, de vote et de fin
        hors_lien, n_etats = [], 0
        for chemin in prefixes:
            if not chemin: continue                                  # avant le premier vote : il est dans le tronc, pas sur un lien
            for mode_ in ("answer", "choose"):
                if mode_ == "choose" and len(chemin) >= 7: continue
                fin = mode_ == "answer" and by[chemin[-1]].get("stay") is None
                page.evaluate("(a) => { delete panel.dataset.k; applyState({mode: a[0], ti: 3, path: a[1]}); }", ["end" if fin else mode_, chemin])
                x, y = map(float, re.search(r"translate\(([-\d.]+)px,\s*([-\d.]+)px\)", page.evaluate("document.querySelector('#svg .bird').style.transform")).groups())
                n_etats += 1; dmin = min(dpoly(x, y, P) for P in LIENS.values())
                if dmin >= 3: hors_lien.append((mode_, ">".join(chemin), round(dmin, 1)))
        infos.append(f"H. {n_etats} états de réponse, de vote et de fin : écureuil à plus de 3 unités de tout lien : {len(hors_lien)}")
        att("H. l'écureuil est toujours assis sur un lien (pattes à moins de 3 unités d'un lien) dans tous les états hors tronc", [], hors_lien[:5])
        att("H. le contrôle parcourt bien tous les états hors tronc (380 : 254 réponses + 126 votes)", 380, n_etats)
        # G. aucun gland caché : le navigateur dit ce qui est peint au centre de chaque gland ; si c'est l'écureuil, le gland est recouvert.
        # Un aller-retour avec la page PAR ÉTAT : changer d'état puis interroger le navigateur dans la même tâche peut lui faire lire un dessin périmé
        # (constaté le 05/10/2026 : de faux recouvrements « B5 » et « A3 », absents quand l'image est posée).
        HIT_JS = """(gl) => { const ctm = document.getElementById('svg').getScreenCTM(), out = [];
          for (const [id, x, y] of gl) { const el = document.elementFromPoint(ctm.a * x + ctm.e, ctm.d * y + ctm.f); if (el && el.closest('.bird')) out.push(id); }
          return out; }"""
        gl = [[i_, x_, y_] for i_, (x_, y_) in G.items()]
        out_g, etats_g = [], 0
        for chemin in prefixes:
            if not chemin: continue
            for mode_ in ("answer", "choose"):
                if mode_ == "choose" and len(chemin) >= 7: continue
                etats_g += 1
                page.evaluate("(a) => { delete panel.dataset.k; applyState({mode: a[0], ti: 3, path: a[1]}); }", [mode_, chemin])
                opts = page.evaluate("options()") if mode_ == "choose" else []
                for id_ in page.evaluate(HIT_JS, gl):
                    out_g.append({"mode": mode_, "chemin": ">".join(chemin), "gland": id_, "important": chemin[-1] == id_ or id_ in opts or id_ in chemin or by[id_]["step"] > len(chemin)})
        rec = {"etats": etats_g, "out": out_g}
        importants = [r for r in rec["out"] if r["important"]]
        passes = [r for r in rec["out"] if not r["important"]]
        infos.append(f"G. {rec['etats']} états (réponse ou vote) : glands qui comptent (courant, proposés, du chemin, à venir) recouverts : {len(importants)} ; glands déjà dépassés et non choisis recouverts : {len(passes)} ({sorted({r['gland'] for r in passes})}, uniquement à la dernière question {sorted({r['chemin'].split('>')[-1] for r in passes})})")
        infos.append("G. détail des recouvrements de glands dépassés : " + str([(r["mode"], r["chemin"], r["gland"]) for r in passes]))
        att("G. l'écureuil ne recouvre jamais le centre d'un gland qui compte (courant, proposé, du chemin ou à venir)", [], importants[:4])
        att("G. seul cas connu de recouvrement : le gland C7 (dépassé, non choisi, à 40 %) quand la salle arrive à la dernière question D7, comme dans la référence", True, all(r["gland"] == "C7" and r["chemin"].endswith("D7") for r in passes))
        att("E/G. aucune erreur JS", [], page.erreurs)
        page.context.close()
        nav.close()
    for l in infos: print("  " + l)
    return echecs


if __name__ == "__main__":
    echecs = tester()
    sys.exit(0 if C.bilan("écureuil (parcours, retour, passages du tronc, remise à zéro, règle des votes, glands visibles)", echecs) else 1)
