"""Compare le dessin de l'application au fichier de référence d'un arbre (olivier : reference/nouveau-design.html ; chêne : reference/chene-brouillon.html),
couche par couche.

La référence (jamais modifiée) est ouverte dans une copie de TEST qui a les polices intégrées
de index.html à la place du lien Google Fonts. Les deux côtés sont mis dans le même état (applyState), les couches pas
encore portées sont cachées des deux côtés, et l'on compare l'image de l'arbre pixel par pixel.

Usage :  .venv/bin/python tests/comparer_reference.py [olivier|chene] <étape>
  olivier : 1 cadre · 2 tronc · 3 loges · 4 licence + fleurs · 5 positions des olives · 6 liens · 7 mésange (tout)
  chêne   : 2 tronc, loges, feuillage, fleurs, licence · 3 noms des thèmes · 4 glands et liens · 5 écureuil (tout)
"""
import sys, re, base64
from playwright.sync_api import sync_playwright
import _commun as C

ETATS_OLIVIER = {
    "T1": {"mode": "trunk", "ti": 0, "path": []}, "T2": {"mode": "trunk", "ti": 1, "path": []},
    "T3": {"mode": "trunk", "ti": 2, "path": []}, "T4": {"mode": "trunk", "ti": 3, "path": []},
    "premier vote": {"mode": "choose", "ti": 3, "path": []},
    "après 3 votes": {"mode": "answer", "ti": 3, "path": ["I1", "L2", "L3"]},
    "fin": {"mode": "end", "ti": 3, "path": ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"]},
}
# le chêne : mêmes états, écrits avec les identifiants de la RÉFÉRENCE (T<thème>-<niveau>) ; l'application les reçoit traduits (A1 à D7)
ETATS_CHENE = {
    "T1": {"mode": "trunk", "ti": 0, "path": []}, "T2": {"mode": "trunk", "ti": 1, "path": []},
    "T3": {"mode": "trunk", "ti": 2, "path": []}, "T4": {"mode": "trunk", "ti": 3, "path": []},
    "premier vote": {"mode": "choose", "ti": 3, "path": []},
    "après 3 votes": {"mode": "answer", "ti": 3, "path": ["T1-1", "T1-2", "T1-3"]},
    "fin": {"mode": "end", "ti": 3, "path": ["T1-1", "T1-2", "T1-3", "T1-4", "T1-5", "T1-6", "T1-7"]},
    # en plus de ta liste : un parcours qui change de thème à chaque vote (les lacets les plus longs)
    "vote 4 (lacets)": {"mode": "choose", "ti": 3, "path": ["T4-1", "T3-2", "T1-3"]},
    "fin (lacets)": {"mode": "end", "ti": 3, "path": ["T4-1", "T3-2", "T1-3", "T2-4", "T1-5", "T3-6", "T4-7"]},
}
LETTRES = {"1": "A", "2": "B", "3": "C", "4": "D"}
vers_lettres = lambda q: re.sub(r"T(\d)-(\d)", lambda m: LETTRES[m.group(1)] + m.group(2), q)
VISIBLE_CHENE = {
    2: {"image", "loges", "licence"}, 3: {"image", "loges", "licence", "labels"},
    4: {"image", "loges", "licence", "labels", "olives", "halos", "liens"},
    5: {"image", "loges", "licence", "labels", "olives", "halos", "liens", "oiseau", "ombre", "bras"},
}
CIBLES = {
    "olivier": dict(reference="nouveau-design.html", etats=ETATS_OLIVIER, visible=None, par_etape={2: ["T1", "T4"], 3: ["T1", "T4"], 4: ["T1", "T4"], 5: ["T1", "T2", "T3", "T4"]},
                    haut_seul={2, 3}, ids=lambda q: q, canvas_exact_des=4, couches_des=3, masque_fin=".note{visibility:hidden}"),
    "chene": dict(reference="chene-brouillon.html", etats=ETATS_CHENE, visible=VISIBLE_CHENE, par_etape={2: ["T1", "T4"], 3: ["T1", "T4"]},
                  haut_seul=set(), ids=vers_lettres, canvas_exact_des=2, couches_des=2, masque_fin=None),
}
# couches visibles à chaque étape (les autres sont cachées des deux côtés)
VISIBLE = {
    2: {"image"}, 3: {"image", "loges", "labels"}, 4: {"image", "loges", "labels", "licence"},
    5: {"image", "loges", "labels", "licence", "olives"},
    6: {"image", "loges", "labels", "licence", "olives", "halos", "liens"},
    7: {"image", "loges", "labels", "licence", "olives", "halos", "liens", "oiseau", "ombre"},
}
# états comparables à chaque étape (avant l'étape 6, la mise en évidence des olives et des liens est encore l'ancienne)
ETATS_PAR_ETAPE = {2: ["T1", "T4"], 3: ["T1", "T4"], 4: ["T1", "T4"], 5: ["T1", "T2", "T3", "T4"]}
# avant l'étape 4 il n'y a ni fleurs ni licence : on ne compare que le haut du dessin (y < 915 sur 968)
HAUT_SEUL = {2, 3}

JS_ROLES = """() => [...document.getElementById('svg').children].map(e => {
  const t = e.tagName.toLowerCase();
  if (t === 'defs' || t === 'image') return t;
  if (t === 'ellipse') return 'emplacements';
  if (t === 'text') return 'labels';
  if (t !== 'g') return t;
  if (e.querySelector('path[fill="url(#lip)"]')) return 'loges';
  if ([...e.querySelectorAll('text')].some(x => x.textContent === 'CC BY-SA MOODSTEP')) return 'licence';
  if (e.querySelector('title')) return 'olives';
  if (e.querySelector('circle[filter]')) return 'halos';
  if (e.querySelector('.bird')) return 'oiseau';
  if (e.getAttribute('pointer-events') === 'none') return e.querySelector('path[fill="url(#lipShade)"]') ? 'ombre' : 'bras';
  if (e.getAttribute('stroke-linecap') === 'round') return 'liens';
  return 'g?';
})"""
JS_MASQUER = ("(visibles) => { const roles = (" + JS_ROLES + ")(); [...document.getElementById('svg').children].forEach((e, i) => { "
              "if (roles[i] !== 'defs' && !visibles.includes(roles[i])) e.style.display = 'none'; }); }")
JS_DIFF = """async ([a, b, yMax]) => {
  const load = s => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = s; });
  const [A, B] = await Promise.all([load(a), load(b)]);
  if (A.width !== B.width || A.height !== B.height) return {taille: [[A.width, A.height], [B.width, B.height]]};
  const g = i => { const c = document.createElement('canvas'); c.width = i.width; c.height = i.height; const x = c.getContext('2d'); x.drawImage(i, 0, 0); return x.getImageData(0, 0, i.width, yMax ? Math.min(i.height, yMax) : i.height).data; };
  const dA = g(A), dB = g(B); let n = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1; const W = A.width;
  for (let i = 0; i < dA.length; i += 4) {
    if (dA[i] !== dB[i] || dA[i+1] !== dB[i+1] || dA[i+2] !== dB[i+2] || dA[i+3] !== dB[i+3]) { n++; const p = i / 4, x = p % W, y = (p / W) | 0; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  }
  return {diff: n, boite: n ? [x0, y0, x1, y1] : null};
}"""


def ouvrir(nav, taille, arbre="olivier"):
    nom_test = "ref_test.html" if arbre == "olivier" else f"ref_test_{arbre}.html"
    nom_var = "variante_noms.html" if arbre == "olivier" else f"variante_noms_{arbre}.html"
    C.reference_avec_polices(C.CAPTURES / nom_test, CIBLES[arbre]["reference"])
    C.variante_avec_noms(C.CAPTURES / nom_var, arbre)
    ref = C.nouvelle_page(nav, taille)
    ref.goto((C.CAPTURES / nom_test).as_uri()); ref.wait_for_timeout(700)
    app = C.nouvelle_page(nav, taille)
    app.goto((C.CAPTURES / nom_var).as_uri()); app.wait_for_timeout(500)
    C.lancer_scene(app)
    for p in (ref, app):   # les trois boutons de la scène ne font pas partie du dessin
        p.add_style_tag(content="#rst,#sub,#sortie,#prev,#next{visibility:hidden!important}")
    return ref, app


def comparer_png(blank, a, b, yMax=0):
    r = blank.evaluate(JS_DIFF, ["data:image/png;base64," + base64.b64encode(a).decode(), "data:image/png;base64," + base64.b64encode(b).decode(), yMax])
    return r


def etape(n, tailles=("1280x720", "1920x1080", "1024x768"), arbre="olivier"):
    cible = CIBLES[arbre]
    ETATS = cible["etats"]; HAUT = cible["haut_seul"]
    VIS = cible["visible"] or VISIBLE
    echecs, lignes = [], []
    with sync_playwright() as p:
        nav = C.lancer(p)
        blank = C.nouvelle_page(nav, "800x600"); blank.goto("about:blank")
        for taille in tailles:
            ref, app = ouvrir(nav, taille, arbre)
            # --- cadre : mêmes dimensions de dessin et d'image ---
            geo = lambda pg: pg.evaluate("""() => { const s = document.getElementById('svg'), r = s.getBoundingClientRect(), i = s.querySelector('image');
                return {viewBox: s.getAttribute('viewBox'), rect: [r.left, r.top, r.width, r.height].map(v => Math.round(v * 10) / 10), image: [i.getAttribute('width'), i.getAttribute('height')]}; }""")
            gr, ga = geo(ref), geo(app)
            if gr != ga: echecs.append(f"{taille} cadre : référence {gr} / application {ga}")
            lignes.append(f"{taille} cadre : {ga['viewBox']}, dessin {ga['rect'][2]}x{ga['rect'][3]} px" + (" == référence" if gr == ga else " DIFFÈRE"))
            if n >= 2:
                href = lambda pg: pg.evaluate("document.querySelector('#svg image').getAttribute('href')")
                hr, ha = href(ref), href(app)
                ymax_img = 915 * 2 if n in HAUT else 0
                d = comparer_png(blank, base64.b64decode(hr.split(",")[1]), base64.b64decode(ha.split(",")[1]), ymax_img)
                ok = d.get("diff") == 0
                lignes.append(f"{taille} image du tronc et du feuillage{' (haut seul)' if ymax_img else ''} : " + (f"{d['diff']} pixels différents" if "diff" in d else f"tailles {d['taille']}") + (" == référence" if ok else ""))
                if not ok: echecs.append(f"{taille} image : {d}")
                if n >= cible['canvas_exact_des'] and hr != ha: echecs.append(f"{taille} l'image du canevas n'est pas identique octet pour octet à la référence")
            if n >= cible['couches_des']:
                for nom_p, p_ in (("référence", ref), ("application", app)):
                    p_.evaluate(JS_MASQUER, sorted(VIS[n]))
                    # garde-fou : si une couche était mal reconnue, elle serait cachée des deux côtés et la comparaison réussirait pour rien
                    vues = p_.evaluate("(" + JS_ROLES + ")()")
                    reste = p_.evaluate("[...document.getElementById('svg').children].filter(e => e.style.display !== 'none').length")
                    connus = {"defs", "image", "loges", "licence", "labels", "olives", "halos", "liens", "oiseau", "ombre", "bras", "emplacements"}
                    inconnus = [r for r in vues if r not in connus]
                    manquants = [r for r in VIS[n] if r not in vues]
                    if inconnus: echecs.append(f"{taille} {nom_p} : couche non reconnue {inconnus}")
                    if manquants: echecs.append(f"{taille} {nom_p} : couche absente {manquants}")
                    if nom_p == "application": lignes.append(f"{taille} couches comparées ({nom_p}) : " + ", ".join(sorted({r for r in vues if r in VIS[n]})))
                for nom in cible["par_etape"].get(n, list(ETATS)):
                    for p_, ids in ((ref, lambda q: q), (app, cible["ids"])):
                        e = {**ETATS[nom], "path": [ids(q) for q in ETATS[nom]["path"]]}      # la référence reçoit ses identifiants, l'application les siens
                        p_.evaluate("(e) => applyState(e)", e); p_.wait_for_timeout(1300)
                        if nom == "fin" and cible["masque_fin"]: p_.add_style_tag(content=cible["masque_fin"])   # les notes de la mésange sont dessinées autrement, volontairement
                    def photo(pg):
                        if n not in HAUT: return pg.locator("#svg").screenshot()
                        b = pg.locator("#svg").bounding_box()      # avant l'étape 4 : ni fleurs ni licence, on laisse la bande du bas (y >= 915 sur 968)
                        return pg.screenshot(clip={"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"] * 915 / 968})
                    sr, sa = photo(ref), photo(app)
                    d = comparer_png(blank, sr, sa)
                    ok = d.get("diff") == 0
                    lignes.append(f"{taille} {nom:14s}: " + (f"{d['diff']} pixels différents {d['boite']}" if "diff" in d else f"tailles {d['taille']}") + (" == référence" if ok else ""))
                    if not ok: echecs.append(f"{taille} {nom} : {d}")
                    if not ok:
                        (C.CAPTURES / "diff").mkdir(exist_ok=True)
                        (C.CAPTURES / "diff" / f"{arbre}_e{n}_{taille}_{nom.replace(' ', '_')}_ref.png").write_bytes(sr)
                        (C.CAPTURES / "diff" / f"{arbre}_e{n}_{taille}_{nom.replace(' ', '_')}_app.png").write_bytes(sa)
            for p_ in (ref, app):
                if p_.erreurs: echecs.append(f"{taille} erreurs JS : {p_.erreurs[:2]}")
            ref.context.close(); app.context.close()
        nav.close()
    for l in lignes: print("  " + l)
    return echecs


if __name__ == "__main__":
    args = sys.argv[1:]
    arbre = args.pop(0) if args and not args[0].isdigit() else "olivier"
    n = int(args[0])
    echecs = etape(n, arbre=arbre)
    sys.exit(0 if C.bilan(f"{arbre} : étape {n} comparée à la référence", echecs) else 1)
