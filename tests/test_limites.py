"""Les limites tiennent-elles ? Cas réalistes difficiles à la limite exacte, sur 6 tailles d'écran.

 A. OBLIGATOIRE : questions de 120 car. et tronc de 160 car., en texte courant, en MOTS LONGS réalistes
    (« intercommunalité »…) et en MAJUSCULES, avec des titres de thème de 30 lettres : aucune carte coupée,
    pour chaque paire proposée à la salle, chaque carte seule, chaque question du tronc.
 B. INFORMATIF : textes absurdes (tout en M, mots de 25 lettres) : peuvent être coupés, c'est signalé sans échec.
 C. Étiquettes de thème : un nom réaliste ne rétrécit pas sous 26 ; le pire cas tient toujours sur son arc.
 D. Polices : les caractères français courants existent-ils dans les polices intégrées ? (avec auto-contrôle)
 E. Encre des noms de thème (les DEUX arbres) : avec des noms à la longueur maximale (minuscules, MAJUSCULES, lettres à queue, lettres
    larges), sur 6 tailles d'écran, l'écriture reste dans l'écran et dans le cadre du dessin, et ne mord jamais le feuillage
    (mesuré en pixels : on photographie l'arbre avec puis sans les noms, et on compare).
Une carte est « coupée » si elle dépasse le haut, le bas ou le côté de l'écran.
Les sections A à C tournent pour chaque arbre : l'olivier (3 thèmes) et le chêne (4 thèmes), chacun avec SA liste de limites.

Usage :  .venv/bin/python tests/test_limites.py
"""
import sys, pathlib, base64
from playwright.sync_api import sync_playwright
import _commun as C

FICHIER = (pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else C.RACINE / "index.html").as_uri()

C.TAILLES.update({"1366x768": (1366, 768), "1440x900": (1440, 900), "1600x900": (1600, 900)})
# Les limites ne sont PAS écrites ici : elles sont lues dans l'éditeur (Editeur.limites), pour tester ce qui est réellement livré.
COURANT = "Comment imaginez-vous la vie quotidienne dans votre commune dans trente ans, et que faudrait-il changer dès aujourd'hui ? " * 4
LONGS_REEL = "Institutionnalisation de l'intercommunalité, responsabilités environnementales, décentralisation, interdépendance, développement soutenable. " * 4
REALISTES = [("courant", COURANT), ("mots longs réalistes", LONGS_REEL), ("MAJUSCULES", COURANT.upper())]
ABSURDES = [("25 lettres", "Anticonstitutionnellement Intergouvernementalisation Hippopotomonstrosesquippedaliophobie " * 4), ("lettres larges", "MMWW Wmmw MWMW wwMM mWmW WMWM MWwm WWmm MMww wMMW " * 5)]
THEME_REALISTES = ["Vivre ensemble", "Mobilités douces", "Économie locale", "Climat & énergie", "Alimentation", "Infrastructures", "Mémoire commune", "Démocratie locale"]
# Ce qui change d'un arbre à l'autre : ses arcs (les noms s'écrivent dessus), ses noms de thème « à la limite », la place de chaque arc.
ARBRES = {
    "olivier": {"arcs": ["I", "A", "L"], "cote": ["I"], "centre": ["L"], "hors_feuillage": False,    # ses noms s'écrivent SUR le feuillage : c'est son dessin
                "themes_max": ["Culture, éducation, lien social", "Mobilités douces", "Santé, soin et bien-être"]},
    "chene": {"arcs": ["A", "B", "C", "D"], "cote": ["A", "D"], "centre": ["B", "C"], "hors_feuillage": True,    # ses noms sont écrits AU-DESSUS du feuillage
              "themes_max": ["Culture et savoirs", "Santé, soin, bien-être", "Alimentation et climat", "Habitat et énergie"]},
}
# E. Les noms à la longueur maximale : chaque ligne donne, pour un cas, la façon de fabriquer le nom d'un thème de longueur n.
def _remplir(motif, n): return (motif * (n // len(motif) + 1))[:n]
CAS_ENCRE = [("minuscules réalistes", "reel", True), ("MAJUSCULES réalistes", "maj", True), ("lettres à queue (g p y j q)", lambda n: _remplir("gypjq ", n), True),
             ("lettres larges (M)", lambda n: "M" * n, False), ("lettres larges (W)", lambda n: "W" * n, False)]

JS_CARTES = """() => {
  const H = innerHeight, W = innerWidth, p = document.getElementById('panel');
  const rects = [...p.querySelectorAll('.card')].map(c => c.getBoundingClientRect());
  const q = [...p.querySelectorAll('.q')];
  return rects.length === 0 ? 'aucune carte' : (rects.some(r => r.top < -1 || r.bottom > H + 1 || r.right > W + 1 || r.left < -1) || q.some(e => e.scrollWidth > e.clientWidth + 1)) ? 'COUPÉE' : 'ok';
}"""
JS_ETIQ = """(arcs) => arcs.map(t => { const path = document.getElementById('arc'+t);
  const tx = [...document.querySelectorAll('svg text')].find(e => e.firstChild && e.firstChild.getAttribute && e.firstChild.getAttribute('href') === '#arc'+t);
  return {t, taille: parseFloat(tx.getAttribute('font-size')), largeur: tx.getComputedTextLength(), arc: path.getTotalLength()}; })"""
JS_PAIRES = "() => { const s = new Set(); D.forEach(d => { if (d.stay) s.add([d.stay, d.change].join(',')); }); s.add(FICHE.depart.join(',')); return [...s].map(x => x.split(',')); }"


def coupe(t, n): return t[:n].rstrip()


def installer(page, arbre):
    """Met l'arbre demandé en place (comme le fait un clic sur sa vignette) et rend les limites de SA fiche."""
    page.evaluate("(id) => { installerArbre(id); vue = null; vueCle = null; Editeur.refaire(); }", arbre)
    return page.evaluate("Editeur.limites")


def regler_et_lancer(page, q, tronc, themes):
    page.evaluate("""([q, tr, th]) => { for (const k in ARBRE.questions) ARBRE.questions[k] = q; ARBRE.tronc = [tr, tr, tr, tr];
        ARBRE.themes.forEach((t, i) => { t.nom = th[i]; }); vue = null; vueCle = null; }""", [q, tronc, themes])
    page.evaluate("ouvrirScene()"); page.wait_for_function("ecran === 'scene'"); C.attendre_dessin(page)


def cartes_coupees(page):
    mauvais = []
    for a, b in page.evaluate(JS_PAIRES):
        page.evaluate("([a]) => { delete panel.dataset.k; applyState({mode:'choose', ti:3, path: cheminVers(a).slice(0, -1)}); }", [a, b])
        if sorted(page.evaluate("options()")) != sorted([a, b]): continue     # paire déjà couverte par un autre chemin
        if page.evaluate(JS_CARTES) == "COUPÉE": mauvais.append(f"{a}/{b}")
    for ident in page.evaluate("D.map(d => d.id)"):
        page.evaluate("(id) => { delete panel.dataset.k; applyState({mode:'answer', ti:3, path: cheminVers(id)}); }", ident)
        if page.evaluate(JS_CARTES) == "COUPÉE": mauvais.append(ident)
    for i in range(4):
        page.evaluate("(i) => { delete panel.dataset.k; applyState({mode:'trunk', ti:i, path:[]}); }", i)
        if page.evaluate(JS_CARTES) == "COUPÉE": mauvais.append(f"T{i+1}")
    return mauvais


JS_ENCRE = """async ([visible, cache, cache2]) => {
  // trois photos : sans les noms, avec les noms, de nouveau sans les noms. Un pixel qui diffère déjà entre les deux photos SANS noms est du
  // bruit de rendu (mesuré : quelques pixels isolés), pas de l'écriture : on ne le compte pas.
  const charger = b64 => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = 'data:image/png;base64,' + b64; });
  const [A, B, B2] = await Promise.all([charger(visible), charger(cache), charger(cache2)]);
  const lire = i => { const c = document.createElement('canvas'); c.width = i.width; c.height = i.height; const x = c.getContext('2d'); x.drawImage(i, 0, 0); return x.getImageData(0, 0, i.width, i.height).data; };
  const a = lire(A), b = lire(B), b2 = lire(B2), W = A.width, H = A.height, fond = [b[0], b[1], b[2]];
  let x0 = W, y0 = H, x1 = -1, y1 = -1, encre = 0, mord = 0, bruit = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 4;
    const d = Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2]));
    if (d <= 40) continue;                                        // ce pixel n'a pas changé : ce n'est pas de l'écriture
    if (Math.max(Math.abs(b2[i] - b[i]), Math.abs(b2[i + 1] - b[i + 1]), Math.abs(b2[i + 2] - b[i + 2])) > 40) { bruit++; continue; }
    encre++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    if (Math.max(Math.abs(b[i] - fond[0]), Math.abs(b[i + 1] - fond[1]), Math.abs(b[i + 2] - fond[2])) > 40) mord++;   // il y avait déjà du dessin dessous
  }
  const m = document.getElementById('svg').getScreenCTM(), vb = document.getElementById('svg').viewBox.baseVal;
  const cadre = [m.e, m.f, m.e + vb.width * m.a, m.f + vb.height * m.d];
  return {encre, bbox: [x0, y0, x1, y1], mord, bruit, ecran: [W, H], cadre};
}"""


def nom_de_cas(cas, arbre, i, n):
    """Le nom d'un thème, de longueur exactement n, pour un cas d'encre."""
    base = ARBRES[arbre]["themes_max"][i]
    if cas == "reel": t = base
    elif cas == "maj": t = base.upper()
    else: t = cas(n)
    return (t + "x" * n)[:n] if len(t) < n else t[:n]


def encre_des_noms(page, arbre, lim):
    """Photographie l'arbre avec puis sans ses noms de thème ; rend {cas: résultat de JS_ENCRE}."""
    rendu = {}
    for nom, cas, _ in CAS_ENCRE:
        noms = [nom_de_cas(cas, arbre, i, n) for i, n in enumerate(lim["theme"])]
        regler_et_lancer(page, "", "", noms)
        page.evaluate("document.querySelectorAll('svg text').forEach(t => { if (t.querySelector('textPath')) t.style.visibility = 'hidden'; })")
        page.wait_for_timeout(120); cache = page.screenshot()
        page.evaluate("document.querySelectorAll('svg text').forEach(t => { t.style.visibility = ''; })")
        page.wait_for_timeout(120); visible = page.screenshot()
        page.evaluate("document.querySelectorAll('svg text').forEach(t => { if (t.querySelector('textPath')) t.style.visibility = 'hidden'; })")
        page.wait_for_timeout(120); cache2 = page.screenshot()
        page.evaluate("document.querySelectorAll('svg text').forEach(t => { t.style.visibility = ''; })")
        rendu[nom] = page.evaluate(JS_ENCRE, [base64.b64encode(x).decode() for x in (visible, cache, cache2)])
    return rendu


def tester():
    echecs, lignes, encres, limites = [], [], [], {}
    with sync_playwright() as p:
        nav = C.lancer(p)
        for arbre, cfg in ARBRES.items():
            for taille in C.TAILLES:
                page = C.nouvelle_page(nav, taille)
                page.goto(FICHIER); page.wait_for_timeout(250)
                lim = installer(page, arbre); LIM_Q, LIM_T = lim["question"], lim["tronc"]; limites[arbre] = lim
                themes_max = [t[:n] for t, n in zip(cfg["themes_max"], lim["theme"])]
                for obligatoire, jeux in ((True, REALISTES), (False, ABSURDES)):
                    for nom, base in jeux:
                        regler_et_lancer(page, coupe(base, LIM_Q), coupe(base, LIM_T), themes_max)
                        m = cartes_coupees(page)
                        lignes.append((arbre, taille, nom, "obligatoire" if obligatoire else "informatif", "tout tient" if not m else "COUPÉ : " + ", ".join(m[:5])))
                        if m and obligatoire: echecs.append(f"{arbre} / {taille} / {nom} : {m[:6]}")
                        for e in page.evaluate(JS_ETIQ, cfg["arcs"]):
                            if e["largeur"] > e["arc"] * 0.93 + 0.5: echecs.append(f"{arbre} / {taille} / {nom} : étiquette {e['t']} dépasse son arc")
                # ----- E. l'encre des noms, à la longueur maximale -----
                for cas, r in encre_des_noms(page, arbre, lim).items():
                    x0, y0, x1, y1 = r["bbox"]; W, H = r["ecran"]; c0, c1, c2, c3 = r["cadre"]
                    obligatoire = next(o for n, _, o in CAS_ENCRE if n == cas)
                    dedans_ecran = r["encre"] > 0 and x0 >= 1 and y0 >= 1 and x1 <= W - 2 and y1 <= H - 2
                    dedans_cadre = r["encre"] > 0 and x0 >= c0 + 1 and y0 >= c1 + 1 and x1 <= c2 - 1 and y1 <= c3 - 1
                    encres.append((arbre, taille, cas, "obligatoire" if obligatoire else "informatif", r["encre"], r["mord"], dedans_ecran, dedans_cadre, r["bruit"]))
                    if r["encre"] == 0: echecs.append(f"{arbre} / {taille} / {cas} : aucune écriture mesurée (le contrôle ne voit rien)")
                    elif obligatoire:
                        if not dedans_ecran: echecs.append(f"{arbre} / {taille} / {cas} : l'écriture sort de l'écran {r['bbox']} sur {r['ecran']}")
                        if not dedans_cadre: echecs.append(f"{arbre} / {taille} / {cas} : l'écriture sort du cadre du dessin {r['bbox']} dans {[round(v) for v in r['cadre']]}")
                        if cfg["hors_feuillage"] and r["mord"] > 0: echecs.append(f"{arbre} / {taille} / {cas} : l'écriture mord le feuillage ({r['mord']} pixels)")
                page.context.close()
        # ----- C. étiquettes de thème : taille d'écriture après ajustement à l'arc -----
        reels, pires = {}, {}
        for arbre, cfg in ARBRES.items():
            page = C.nouvelle_page(nav, "1280x720"); page.goto(FICHIER); page.wait_for_timeout(250)
            lim = installer(page, arbre); arcs = cfg["arcs"]; nb = len(arcs); limites[arbre] = lim

            def tailles(noms):
                regler_et_lancer(page, "", "", noms)
                return {x["t"]: x["taille"] for x in page.evaluate(JS_ETIQ, arcs)}
            reel = {}
            for nom in THEME_REALISTES + [t for t in cfg["themes_max"] if t not in THEME_REALISTES] * (arbre != "olivier"):
                e = tailles([nom] * nb)
                reel[nom] = (len(nom), min(e[a] for a in cfg["cote"]), min(e[a] for a in cfg["centre"]), e)
            pire = {}
            if arbre == "olivier":
                for lib, noms, cle in (("côté, 30 'M'", ["M" * 30] * 3, "I"), ("centre, 16 'M'", ["M" * 16] * 3, "L"), ("centre, 16 'W'", ["W" * 16] * 3, "L")):
                    pire[lib] = tailles(noms)[cle]
            else:
                for lib, noms in (("minuscules au maximum", cfg["themes_max"]), ("MAJUSCULES au maximum", [t.upper() for t in cfg["themes_max"]]),
                                  ("'M' au maximum", ["M" * n for n in lim["theme"]]), ("'W' au maximum", ["W" * n for n in lim["theme"]])):
                    pire[lib] = min(tailles(noms).values())
                # plancher de lisibilité : un nom réaliste à sa longueur maximale ne descend pas sous 26 (minuscules) ni 18 (MAJUSCULES)
                if pire["minuscules au maximum"] < 26: echecs.append(f"chene : noms au maximum en minuscules rétrécis à {pire['minuscules au maximum']} (seuil 26)")
                if pire["MAJUSCULES au maximum"] < 18: echecs.append(f"chene : noms au maximum en MAJUSCULES rétrécis à {pire['MAJUSCULES au maximum']} (seuil 18)")
                for nom, (n, _, _, e) in reel.items():
                    for a, lim_a in zip(arcs, lim["theme"]):
                        if n <= lim_a and e[a] < 26: echecs.append(f"chene : nom réaliste « {nom} » ({n} lettres) rétréci à {e[a]} sur l'arc {a} (seuil 26)")
            reels[arbre], pires[arbre] = reel, pire
            page.context.close()
        nav.close()
    for nom, (n, i, l, _) in reels["olivier"].items():
        if n <= 16 and l < 26: echecs.append(f"nom réaliste « {nom} » rétréci à {l} au centre (seuil 26)")
        if i < 40: echecs.append(f"nom réaliste « {nom} » rétréci sur le côté ({i})")
    print("OLIVIER. Taille d'écriture des étiquettes de thème (40 = normale ; l'arc du centre est court) :")
    print(f"  {'nom':22s} {'car.':>4s} {'côté':>6s} {'centre':>7s}")
    for nom, (n, i, l, _) in reels["olivier"].items(): print(f"  {nom:22s} {n:4d} {i:6.1f} {l:7.1f}")
    for k, v in pires["olivier"].items(): print(f"  pire cas, {k:16s} -> {v:5.1f}")
    arcs = ARBRES["chene"]["arcs"]
    print(f"\nCHÊNE. Taille d'écriture par arc (limites lues dans l'éditeur : {limites['chene']['theme']} ; 40 = normale) :")
    print(f"  {'nom':24s} {'car.':>4s} " + " ".join(f"{a:>6s}" for a in arcs))
    for nom, (n, _, _, e) in reels["chene"].items(): print(f"  {nom:24s} {n:4d} " + " ".join(f"{e[a]:6.1f}" for a in arcs))
    for k, v in pires["chene"].items(): print(f"  cas extrême, {k:24s} -> plus petite taille {v:5.1f}")
    print("\nE. Encre des noms à la longueur maximale, 6 tailles d'écran :")
    for arbre in ARBRES:
        for cas, _, o in CAS_ENCRE:
            ligne = [t for t in encres if t[0] == arbre and t[2] == cas]
            print(f"  {arbre:8s} {cas:30s} {'obligatoire' if o else 'informatif':12s} dans l'écran {sum(t[6] for t in ligne)}/{len(ligne)}, dans le cadre {sum(t[7] for t in ligne)}/{len(ligne)}, pixels qui mordent le feuillage : {sum(t[5] for t in ligne)}{'' if ARBRES[arbre]['hors_feuillage'] else ' (non jugé : ses noms sont écrits sur le feuillage)'}, bruit de rendu écarté : {sum(t[8] for t in ligne)}")
    for arbre in ARBRES:
        lim = limites[arbre]
        print(f"\n{arbre.upper()}. Questions à {lim['question']} car., tronc à {lim['tronc']} car., noms de thème de {' / '.join(map(str, lim['theme']))} lettres (lus dans l'éditeur), cartes sur 6 tailles :")
        for t in [x for x in lignes if x[0] == arbre and x[1] in ("1024x768", "1920x1080")]: print(f"  {t[1]:10s} {t[2]:22s} {t[3]:12s} {t[4]}")
    return echecs


POLICES_JS = """async (extra) => {
  const chars = extra + "àâäçéèêëîïôöùûüÿœæÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ«»’‘“”…–—·€°&?!:;,.'\\"()-/0123456789e";
  await Promise.all([document.fonts.load('600 24px Fraunces', chars), document.fonts.load('700 24px Caveat', chars)]);
  const c = document.createElement('canvas').getContext('2d');
  const m5 = (police, ch) => { c.font = police; const m = c.measureText(ch);
    return [m.width, m.actualBoundingBoxLeft, m.actualBoundingBoxRight, m.actualBoundingBoxAscent, m.actualBoundingBoxDescent].map(x => Math.round(x * 100)).join(','); };
  const absent = {};
  for (const [nom, poids] of [['Fraunces', 600], ['Caveat', 700]])   // absent = mêmes mesures qu'une police inexistante (police par défaut)
    absent[nom] = [...chars].filter(ch => m5(`${poids} 24px ${nom}`, ch) === m5(`${poids} 24px ZzzInexistante`, ch));
  return absent;
}"""


def polices():
    with sync_playwright() as p:
        nav = C.lancer(p); page = C.nouvelle_page(nav, "1280x720"); page.goto(FICHIER); page.wait_for_timeout(250)
        temoin = page.evaluate(POLICES_JS, "\u2603")      # bonhomme de neige : n'existe dans aucune des deux polices, doit être signalé absent
        m = page.evaluate(POLICES_JS, "")
        nav.close()
    return temoin, m


if __name__ == "__main__":
    echecs = tester()
    temoin, manque = polices()
    print("\nPolices : caractères français courants ABSENTS des polices intégrées")
    for nom, l in manque.items(): print(f"  {nom:9s}:", "".join(l) if l else "aucun")
    for nom in ("Fraunces", "Caveat"):
        if "\u2603" not in temoin[nom]: echecs.append(f"auto-contrôle polices ({nom}) : un caractère inexistant n'est pas détecté")
        if "e" in temoin[nom]: echecs.append(f"auto-contrôle polices ({nom}) : « e » signalé absent à tort")
    print("  auto-contrôle (☃ détecté absent, « e » présent) :", "réussi" if not [e for e in echecs if "auto-contrôle" in e] else "ÉCHEC")
    for nom, l in manque.items():
        if l: echecs.append(f"{nom} : caractères absents {''.join(l)}")
    sys.exit(0 if C.bilan("limites et polices", echecs) else 1)
