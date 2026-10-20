"""Les questions subsidiaires : une question de plus, facultative, À N'IMPORTE QUEL MOMENT du parcours (touche = ou +, rond du milieu).
 Depuis le 12/10/2026 : plus seulement à la fin. « ← » depuis une subsidiaire ramène exactement là où on s'était arrêté (blocs L à N).

 A. Par le calcul, sur TOUS les parcours (256 olivier, 128 chêne) : aucune question tirable n'a été affichée pendant le parcours ; leur nombre est
    (questions de la table) - 2 x (nombre de votes) ; le tirage de l'application = l'ensemble calculé ici, indépendamment. Le contrôle est lui-même
    éprouvé : on lui donne un tirage truqué (une question du parcours glissée dedans) et il doit l'attraper.
 B. Parcours complet au clavier, réseau coupé, puis = trois fois : capture de chaque question subsidiaire, carte au fond de la couleur du thème,
    contraste mesuré sur la page (nom du thème ET question, au moins 4,5:1). Puis Entrée : le tableau final est identique, pixel pour pixel,
    à celui de la version d'AVANT les questions subsidiaires (commit 696ab2c) et à celui du même parcours sans subsidiaires.
 C. Chaque fruit qui peut sortir au tirage (olive ou gland) : la mascotte ne recouvre AUCUN fruit (boîtes mesurées dans la page) ; son fruit seul s'allume
    en plus du parcours ; aucun lien n'est tracé vers lui ; un seul fruit subsidiaire allumé à la fois.
    EXCEPTION ÉCRITE ICI : l'écureuil est « toujours assis sur un lien » (test_ecureuil, H) MAIS PAS pour une question subsidiaire : aucun lien
    n'arrive au gland tiré, il s'assoit à côté du gland. Même chose pour la mésange. On vérifie qu'ils sont bien à côté (de profil, tournés vers le fruit).
 D. Depuis le tableau final après trois subsidiaires : ← jusqu'au tronc ; chaque état de l'aller est retrouvé (carte, mascotte, fruits allumés).
 E. Épuisement du tirage : le rond disparaît, = ne fait plus rien, aucune erreur ; toutes les questions tirées sont différentes.
 F. = au tronc et avant la première réponse : rien ne se passe (tout peut encore être proposé : aucune question n'est sûre).
 L. À chaque moment du parcours (réponses et votes, des deux arbres) : = tire une subsidiaire, ← ramène à l'état identique (mascotte, carte, fruits), = la rejoue,
    → reprend le parcours là où il en était. + fait comme =. Au tableau final : = puis ← ramène au même tableau, pixel pour pixel.
 M. Par le calcul, sur chaque position de chaque parcours : le tirage = les questions qui ne s'afficheront dans AUCUNE suite possible du parcours (ni trop, ni trop peu).
 N. Parcours au hasard (tirages, retours, choix, = et +, 4000 gestes par arbre) : une subsidiaire n'est jamais en double ni dans le parcours (« Mes arbres » l'exige) ; le contrôle sait échouer.
 G. Un clic sur le rond fait exactement la même chose que =.
 H. Maj+R pendant une question subsidiaire : retour au tronc, tout est remis à zéro (même mascotte qu'au premier lancement).
 I. Après ←, = rejoue la question quittée (décision de Joanna), puis tire une nouvelle.
 J. Un arbre téléchargé depuis l'éditeur, rouvert : les questions subsidiaires marchent aussi (le rond fait partie du fichier).
 K. Le rond n'est jamais visible aux états des images de référence comparées ; aucune erreur, aucune requête réseau.

Usage :  .venv/bin/python tests/test_sous_questions.py
"""
import re, subprocess, sys, json, pathlib
from playwright.sync_api import sync_playwright
import _commun as C

DOSSIER = C.CAPTURES / "sous_questions"; DOSSIER.mkdir(exist_ok=True)
HASARD = "window.__hasard = () => { window.__h = (window.__h || 0) + 1; return (window.__h * 0.3819) % 1; };"
CHEMINS_JS = """() => { const out = []; const aller = (path, vues) => { const d = byId[path[path.length - 1]];
  if (!d.stay) { out.push([path, [...vues]]); return; }
  for (const c of [d.stay, d.change]) aller(path.concat(c), new Set([...vues, d.stay, d.change])); };
  for (const f of FICHE.depart) aller([f], new Set(FICHE.depart)); return out; }"""
SIG_JS = """() => { const m = document.querySelector('#svg .bird'), p = m.firstElementChild;
  const halos = [...document.querySelectorAll('#svg circle[filter]')].filter(c => c.getAttribute('opacity') === '0.85').map(c => c.getAttribute('cx') + ',' + c.getAttribute('cy'));
  let h = 0; const k = p.dataset.k || ''; for (let i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) | 0;
  return {mode, ti, path: path.slice(), subs: subs.slice(), pos, bird: [m.style.transform, m.parentElement.getAttribute('clip-path'), k.length + ':' + h],
          carte: document.getElementById('panel').innerHTML, halos, rond: !document.getElementById('sub').hidden}; }"""
CHOIX = ["ArrowUp", "ArrowDown", "ArrowDown", "ArrowUp", "ArrowDown", "ArrowUp", "ArrowUp", "ArrowDown"]
BOITES_JS = """() => { const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
  const fruits = {}; document.querySelectorAll('#svg title').forEach(t => { if (byId[t.textContent]) fruits[t.textContent] = r(t.parentElement); });
  const oiseau = document.querySelector('#svg .bird').firstElementChild;
  return {fruits, oiseau: oiseau.getBoundingClientRect().width ? r(oiseau) : null}; }"""
LIENS_JS = "[...document.querySelectorAll('#svg path.lk')].map(p => p.style.opacity + '|' + p.style.strokeWidth + '|' + p.getAttribute('stroke'))"
HALOS_JS = "[...document.querySelectorAll('#svg circle[filter]')].map(c => c.getAttribute('opacity'))"


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def rapport(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + .05) / (min(x, y) + .05)


def rgb_hex(css):
    n = [int(v) for v in re.findall(r"\d+", css)[:3]]
    return "#%02x%02x%02x" % tuple(n)


def recouvre(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 0.01 and min(a[3], b[3]) - max(a[1], b[1]) > 0.01


def affichees(table, depart, path):
    return set(depart) | set(path) | {x for i in path for x in (table[i].get("stay"), table[i].get("change")) if x}


def controle_tirables(chemins, table, depart, tirage):
    """Violations : pour un parcours, le tirage ne doit contenir aucune question affichée (départ, parcours, refusées)."""
    mal = []
    for path, _ in chemins:
        vues = affichees(table, depart, path)
        for q in tirage(path):
            if q in vues: mal.append((">".join(path), q))
    return mal


def jouer_parcours(page, nb_votes):
    for _ in range(4): page.keyboard.press("ArrowRight")
    for v in range(nb_votes):
        page.keyboard.press(CHOIX[v % 8])
        if v < nb_votes - 1: page.keyboard.press("ArrowRight")
    page.wait_for_timeout(120)


def ouvrir(nav, arbre, fichier=None, **kw):
    f = fichier or C.variante_avec_noms(DOSSIER / f"v_{arbre}.html", arbre)
    page = C.nouvelle_page(nav, "1280x720", init_script=HASARD, **kw)
    page.goto(pathlib.Path(f).as_uri()); page.wait_for_timeout(300); C.lancer_scene(page)
    return page


def tester():
    echecs, infos = [], []
    def att(nom, attendu, obtenu):
        if attendu != obtenu: echecs.append(f"{nom} : attendu {str(attendu)[:200]!r}, obtenu {str(obtenu)[:200]!r}")
    avant = DOSSIER / "avant_questions_subsidiaires.html"      # la version d'AVANT, relue dans git : « le tableau final d'aujourd'hui »
    avant.write_text(subprocess.run(["git", "show", "696ab2c:index.html"], cwd=str(C.RACINE), capture_output=True, text=True, check=True).stdout, encoding="utf-8")
    with sync_playwright() as p:
        nav = C.lancer(p)
        for arbre in ("olivier", "chene"):
            page = ouvrir(nav, arbre)
            nb_votes = page.evaluate("NB_VOTES"); total = page.evaluate("D.length")
            table = {d["id"]: d for d in page.evaluate("D")}
            depart = page.evaluate("FICHE.depart")
            # ============ A. par le calcul, tous les parcours ============
            chemins = page.evaluate(CHEMINS_JS)
            att(f"A. {arbre} : nombre de parcours", {"olivier": 256, "chene": 128}[arbre], len(chemins))
            tirages = page.evaluate("""(cs) => cs.map(([c]) => { applyState({mode:'answer', ti:3, path:c, subs:[], pos:-1}); return subRestantes(); })""", chemins)
            res = {tuple(c[0]): t for c, t in zip(chemins, tirages)}
            mal = controle_tirables(chemins, table, depart, lambda path: res[tuple(path)])
            att(f"A. {arbre} : aucune question tirable n'a été affichée pendant le parcours ({len(chemins)} parcours)", [], mal[:5])
            tailles = sorted({len(t) for t in tirages})
            att(f"A. {arbre} : le nombre de questions au tirage = questions - 2 x votes, pour tous les parcours", [total - 2 * nb_votes], tailles)
            infos.append(f"A. {arbre} : {len(chemins)} parcours, {total} questions, {nb_votes} votes : il reste {min(tailles)} (minimum) à {max(tailles)} (maximum) questions au tirage")
            att(f"A. {arbre} : le tirage de l'application = l'ensemble recalculé ici, parcours par parcours", True,
                all(set(t) == set(table) - affichees(table, depart, c[0]) for c, t in zip(chemins, tirages)))
            truque = controle_tirables(chemins[:1], table, depart, lambda path: list(res[tuple(path)]) + [path[-1]])
            att(f"A. {arbre} : le contrôle attrape un tirage truqué (question du parcours glissée dedans)", True, bool(truque))
            truque2 = controle_tirables(chemins[:1], table, depart, lambda path: list(res[tuple(path)]) + [table[path[0]]["change"]])
            att(f"A. {arbre} : le contrôle attrape un tirage truqué (question refusée glissée dedans)", True, bool(truque2))
            tirables = sorted({q for t in tirages for q in t})
            infos.append(f"A. {arbre} : {len(tirables)} fruits sur {total} peuvent sortir dans au moins un parcours (ne sortent jamais : {sorted(set(table) - set(tirables))})")
            att(f"A. {arbre} : aucune erreur / requête", ([], []), (page.erreurs, C.requetes_suspectes(page)))
            page.context.close()

            # ============ B. parcours au clavier, trois =, capture, contraste, tableau final ============
            page = ouvrir(nav, arbre)
            jouer_parcours(page, nb_votes)
            att(f"B. {arbre} : le rond est visible à la dernière question", True, page.evaluate(SIG_JS)["rond"])
            themes = {t["id"]: t for t in page.evaluate("FICHE.themes")}
            rond = page.evaluate("""(() => { const g = id => document.getElementById(id).getBoundingClientRect(); const a = g('sub'), b = g('rst'); return [a.left + a.width / 2, a.top, a.width, b.top, b.width]; })()""")
            att(f"B. {arbre} : le rond est centré en haut, même taille et même hauteur que le rond de droite", (640, True), (round(rond[0]), abs(rond[1] - rond[3]) < .5 and abs(rond[2] - rond[4]) < .5))
            vus = []
            for k in range(3):
                page.keyboard.press("="); page.wait_for_timeout(400)
                st = page.evaluate("[mode, subs.slice(), pos]")
                att(f"B. {arbre} : = n°{k + 1} affiche une question subsidiaire", ("sub", k), (st[0], st[2]))
                q = st[1][-1]; vus.append(q)
                th = table[q]["theme"]
                fond = rgb_hex(page.evaluate("getComputedStyle(document.querySelector('#panel .card')).backgroundColor"))
                c_th = page.evaluate("[getComputedStyle(document.querySelector('#panel .th')).color, getComputedStyle(document.querySelector('#panel .th')).opacity, getComputedStyle(document.querySelector('#panel .q')).color]")
                att(f"B. {arbre} : question {q} : fond de la carte = couleur du thème {th} de la fiche", themes[th]["couleur"], fond)
                r_th, r_q = rapport(fond, rgb_hex(c_th[0])), rapport(fond, rgb_hex(c_th[2]))
                att(f"B. {arbre} : question {q} : nom du thème à pleine opacité", "1", c_th[1])
                att(f"B. {arbre} : question {q} : contraste ≥ 4,5 pour le nom du thème ET pour la question (mesuré {r_th:.2f} / {r_q:.2f})", True, r_th >= 4.5 and r_q >= 4.5)
                att(f"B. {arbre} : question {q} : la carte ne porte que le thème et la question, sans bouton", [2, 1, 0], page.evaluate("[document.querySelectorAll('#panel .card > span').length, document.querySelectorAll('#panel .card').length, document.querySelectorAll('#panel button').length]"))
                page.screenshot(path=str(DOSSIER / f"{arbre}_subsidiaire_{k + 1}_{q}.png"))
            att(f"B. {arbre} : trois questions différentes", 3, len(set(vus)))
            page.keyboard.press("Enter"); page.wait_for_timeout(500)
            att(f"B. {arbre} : Entrée = tableau final", "end", page.evaluate("mode"))
            page.add_style_tag(content="#sub{visibility:hidden!important}")      # le rond est nouveau : il n'existait pas dans la version d'avant
            fin_sub = (page.screenshot(), page.evaluate("document.getElementById('svg').outerHTML"), page.evaluate("document.getElementById('screen').className"))
            page.context.close()
            for nom, ancien in (("du même parcours sans subsidiaires", False), ("de la version d'avant (696ab2c)", True)):
                if not ancien:
                    pg = ouvrir(nav, arbre)
                else:
                    f2 = C.variante_avec_noms(DOSSIER / f"avant_{arbre}.html", arbre)
                    donnees = re.search(r'(<script type="application/json" id="donnees-arbre">\n)(.*?)(\n</script>)', pathlib.Path(f2).read_text(encoding="utf-8"), re.S).group(2)
                    s2 = re.sub(r'(<script type="application/json" id="donnees-arbre">\n)(.*?)(\n</script>)', lambda mm: mm.group(1) + donnees + mm.group(3), avant.read_text(encoding="utf-8"), count=1, flags=re.S)
                    if "sqHaloP" in s2:   # depuis le 11/10/2026 l'écureuil n'a plus de liseré crème : seule cette COPIE de la vieille version le perd aussi
                        assert s2.count("halo=true)=>") == 2, "le liseré de l'écureuil n'est plus appliqué par défaut dans la version d'avant"
                        s2 = s2.replace("halo=true)=>", "halo=false)=>")
                        s2, nb = re.subn(r"defs\.insertAdjacentHTML\('beforeend',`<filter id=\"sqHaloP\".*?</filter>`\);\n", "", s2, count=1, flags=re.S)
                        assert nb == 1, "filtre du liseré introuvable dans la version d'avant"
                    pathlib.Path(f2).write_text(s2, encoding="utf-8")
                    pg = ouvrir(nav, arbre, fichier=f2)
                jouer_parcours(pg, nb_votes); pg.keyboard.press("Enter"); pg.wait_for_timeout(500)
                att(f"B. {arbre} : tableau final {nom} : état", "end", pg.evaluate("mode"))
                pg.add_style_tag(content="#sub{visibility:hidden!important}")
                ref = (pg.screenshot(), pg.evaluate("document.getElementById('svg').outerHTML"), pg.evaluate("document.getElementById('screen').className"))
                if ancien and arbre == "chene":
                    infos.append("B. chene : comparaison avec la version d'avant (696ab2c) non faite : l'écureuil du chêne a été redessiné le 11/10/2026 (liseré retiré, demande de Joanna) ; la comparaison avec le même parcours sans subsidiaires de la version actuelle, elle, est faite")
                    pg.context.close(); continue
                att(f"B. {arbre} : tableau final après 3 subsidiaires = tableau {nom}, pixel pour pixel (rond masqué)", True, fin_sub[0] == ref[0])
                att(f"B. {arbre} : tableau final après 3 subsidiaires = tableau {nom}, dessin identique (SVG)", True, fin_sub[1] == ref[1] and fin_sub[2] == ref[2])
                pg.context.close()

            # ============ C. chaque fruit tirable : mascotte, allumage, liens ============
            page = ouvrir(nav, arbre)
            chemin_de = {}
            for c, vues in chemins:
                for q in table:
                    if q not in vues and q not in chemin_de: chemin_de[q] = c
            marges = []
            for q in tirables:
                c = chemin_de[q]
                page.evaluate("([c]) => applyState({mode:'answer', ti:3, path:c, subs:[], pos:-1})", [c]); page.wait_for_timeout(60)
                liens_rep, halos_rep = page.evaluate(LIENS_JS), page.evaluate(HALOS_JS)
                page.evaluate("([c, q]) => applyState({mode:'sub', ti:3, path:c, subs:[q], pos:0})", [c, q]); page.wait_for_timeout(60)
                liens_sub, halos_sub = page.evaluate(LIENS_JS), page.evaluate(HALOS_JS)
                att(f"C. {arbre} {q} : aucun lien tracé vers lui (liens identiques à ceux de la dernière réponse)", liens_rep, liens_sub)
                diff = [i for i, (a, b) in enumerate(zip(halos_rep, halos_sub)) if a != b]
                att(f"C. {arbre} {q} : un seul halo de plus que pendant le parcours : celui de son fruit, à 0,85 (comme le fruit en cours)", ["0.85"], [halos_sub[i] for i in diff])
                att(f"C. {arbre} {q} : fruits allumés = parcours ({nb_votes}) + 1", nb_votes + 1, halos_sub.count("0.85"))
                b = page.evaluate(BOITES_JS)
                if b["oiseau"] is None: echecs.append(f"C. {arbre} {q} : la mascotte est introuvable"); continue
                ob = b["oiseau"]
                for fq, fb in b["fruits"].items():
                    if recouvre(ob, fb): echecs.append(f"C. {arbre} {q} : la mascotte recouvre le fruit {fq} (mascotte {[round(v) for v in ob]}, fruit {[round(v) for v in fb]})")
                fr = b["fruits"][q]
                cote = (fr[0] + fr[2]) / 2 - (ob[0] + ob[2]) / 2
                marge = max(fr[0] - ob[2], ob[0] - fr[2])
                marges.append(marge)
                att(f"C. {arbre} {q} : la mascotte est à côté du fruit (séparés horizontalement, pas au-dessus ni au-dessous)", True, marge >= -0.01)
                fx = page.evaluate("""() => { const g = document.querySelector('#svg .bird').firstElementChild.firstElementChild; const t = (g && g.getAttribute('transform')) || ''; const k = t.match(/scale\\((-?[\\d.]+)/); return k ? Math.sign(+k[1]) : 0; }""")
                att(f"C. {arbre} {q} : tournée vers le fruit", 1 if cote > 0 else -1, fx)
            infos.append(f"C. {arbre} : {len(tirables)} fruits mesurés ; la mascotte ne recouvre aucun fruit ; écart horizontal le plus petit avec son fruit : {min(marges):.1f} px")
            c = chemin_de[tirables[0]]
            seconde = next(q for q in tirables if q != tirables[0] and q not in c and chemin_de[q] is not None)
            page.evaluate("([c, a]) => applyState({mode:'sub', ti:3, path:c, subs:[a], pos:0})", [c, tirables[0]])
            h1 = page.evaluate(HALOS_JS)
            page.evaluate("([c, a, b]) => applyState({mode:'sub', ti:3, path:c, subs:[a, b], pos:1})", [c, tirables[0], seconde])
            h2 = page.evaluate(HALOS_JS)
            att(f"C. {arbre} : au tirage suivant, un seul fruit subsidiaire allumé (le précédent est redevenu normal)", (nb_votes + 1, nb_votes + 1), (h1.count("0.85"), h2.count("0.85")))
            att(f"C. {arbre} : aucune erreur / requête", ([], []), (page.erreurs, C.requetes_suspectes(page)))
            page.context.close()

            # ============ D. retour avec ← jusqu'au tronc, chaque état retrouvé ============
            page = ouvrir(nav, arbre)
            aller = []
            def noter(attente=150):
                page.wait_for_timeout(attente); aller.append(page.evaluate(SIG_JS))
            noter(1300)
            for _ in range(4): page.keyboard.press("ArrowRight"); noter(1300)
            for v in range(nb_votes):
                page.keyboard.press(CHOIX[v % 8]); noter()
                if v < nb_votes - 1: page.keyboard.press("ArrowRight"); noter()
            for _ in range(3): page.keyboard.press("="); noter()
            page.keyboard.press("Enter"); noter()
            att(f"D. {arbre} : après Entrée on est au tableau final avec 3 subsidiaires", ("end", 3), (aller[-1]["mode"], len(aller[-1]["subs"])))
            cle = lambda s: json.dumps([s["mode"], s["ti"], s["path"], s["subs"][s["pos"]] if s["mode"] == "sub" else None])   # l'identité d'un état : où on est, et quelle subsidiaire est affichée
            par_cle = {cle(s): s for s in aller}
            retour, manque = [], []
            for i in range(200):
                page.keyboard.press("ArrowLeft")
                page.wait_for_timeout(1300 if (page.evaluate("mode") == "trunk" or (retour and retour[-1]["mode"] == "trunk")) else 160)
                s = page.evaluate(SIG_JS); retour.append(s)
                if s["mode"] == "trunk" and s["ti"] == 0: break
                if i > 0 and cle(s) == cle(retour[-2]): echecs.append(f"D. {arbre} : ← n'a rien changé à l'étape {i}"); break
            att(f"D. {arbre} : le retour arrive au tronc (T1)", ("trunk", 0), (retour[-1]["mode"], retour[-1]["ti"]))
            for s in retour:
                k = cle(s)
                if k not in par_cle: manque.append(k); continue
                a = par_cle[k]
                if (a["bird"], a["carte"], a["halos"], a["rond"]) != (s["bird"], s["carte"], s["halos"], s["rond"]):
                    echecs.append(f"D. {arbre} : l'état {k[:70]} n'est pas retrouvé à l'identique (mascotte / carte / fruits / rond)")
            att(f"D. {arbre} : chaque état du retour existait à l'aller", [], manque[:3])
            att(f"D. {arbre} : les 3 subsidiaires font partie du retour (n°3 depuis le tableau final, puis 2, puis 1)", [2, 1, 0], [s["pos"] for s in retour if s["mode"] == "sub"])
            infos.append(f"D. {arbre} : {len(retour)} états rejoués en marche arrière depuis le tableau final jusqu'au tronc, tous retrouvés à l'identique (mascotte, carte, fruits allumés, rond), dont les 3 subsidiaires")
            att(f"D. {arbre} : aucune erreur", [], page.erreurs)
            page.context.close()

            # ============ E. épuisement ============
            page = ouvrir(nav, arbre)
            jouer_parcours(page, nb_votes)
            for _ in range(total): page.keyboard.press("=")
            page.wait_for_timeout(150)
            e = page.evaluate("[mode, subs.slice(), subRestantes().length, !document.getElementById('sub').hidden]")
            att(f"E. {arbre} : le tirage est épuisé ({total - 2 * nb_votes} questions, chacune tirée une fois)", (total - 2 * nb_votes, 0, False, "sub"), (len(e[1]), e[2], e[3], e[0]))
            att(f"E. {arbre} : toutes les questions tirées sont différentes", len(e[1]), len(set(e[1])))
            avant_etat = page.evaluate(SIG_JS); page.keyboard.press("="); page.wait_for_timeout(100)
            att(f"E. {arbre} : = ne fait plus rien, rien d'autre ne s'affiche", avant_etat, page.evaluate(SIG_JS))
            att(f"E. {arbre} : le rond a disparu", True, page.evaluate("document.getElementById('sub').hidden"))
            att(f"E. {arbre} : aucune erreur", [], page.erreurs)
            page.context.close()

            # ============ F. = au tronc et avant la première réponse ============
            page = ouvrir(nav, arbre)
            def rien(nom):
                s0 = page.evaluate(SIG_JS); page.keyboard.press("="); page.keyboard.press("+"); page.wait_for_timeout(120)
                att(f"F. {arbre} : = et + ne font rien : {nom}", s0, page.evaluate(SIG_JS))
                att(f"F. {arbre} : le rond est caché : {nom}", False, page.evaluate("!document.getElementById('sub').hidden"))
            rien("au tronc T1"); page.keyboard.press("ArrowRight"); page.wait_for_timeout(1300); rien("au tronc T2")
            for _ in range(3): page.keyboard.press("ArrowRight"); page.wait_for_timeout(1300)
            rien("pendant le premier vote")
            page.context.close()

            # ============ G. clic = touche ============
            res_g = []
            for geste in ("touche", "clic"):
                page = ouvrir(nav, arbre); jouer_parcours(page, nb_votes)
                for _ in range(2):
                    if geste == "touche": page.keyboard.press("=")
                    else: page.click("#sub")
                    page.wait_for_timeout(250)
                res_g.append(page.evaluate(SIG_JS)); page.context.close()
            att(f"G. {arbre} : deux clics sur le rond = deux touches = (même état, même mascotte, même carte)", res_g[0], res_g[1])
            page = ouvrir(nav, arbre); jouer_parcours(page, nb_votes); page.click("#sub"); page.wait_for_timeout(100)
            page.keyboard.press("Enter"); page.wait_for_timeout(100)
            att(f"G. {arbre} : après un clic, Entrée fait « suivant » (le rond ne garde pas le focus)", "end", page.evaluate("mode"))
            page.context.close()

            # ============ H. Maj+R pendant une subsidiaire ============
            page = ouvrir(nav, arbre); depart_sig = page.evaluate(SIG_JS)
            jouer_parcours(page, nb_votes); page.keyboard.press("="); page.keyboard.press("="); page.wait_for_timeout(200)
            page.keyboard.press("Shift+R"); page.wait_for_timeout(1500)
            s = page.evaluate(SIG_JS)
            att(f"H. {arbre} : Maj+R pendant une subsidiaire : retour au tronc, rien en mémoire, rond caché", ("trunk", 0, [], [], -1, False), (s["mode"], s["ti"], s["path"], s["subs"], s["pos"], s["rond"]))
            att(f"H. {arbre} : même mascotte, même carte, mêmes fruits allumés qu'au premier lancement", (depart_sig["bird"], depart_sig["carte"], depart_sig["halos"]), (s["bird"], s["carte"], s["halos"]))
            jouer_parcours(page, nb_votes); page.keyboard.press("="); page.wait_for_timeout(100)
            att(f"H. {arbre} : après remise à zéro, le tirage repart de zéro", 1, page.evaluate("subs.length"))
            page.click("#rst"); page.wait_for_timeout(1500)
            att(f"H. {arbre} : le rond de droite remet aussi tout à zéro, subsidiaires comprises", ["trunk", [], -1], page.evaluate("[mode, subs.slice(), pos]"))
            page.context.close()

            # ============ I. ← puis = rejoue la question quittée ============
            page = ouvrir(nav, arbre); jouer_parcours(page, nb_votes)
            for _ in range(3): page.keyboard.press("=")
            tires = page.evaluate("subs.slice()")
            page.keyboard.press("ArrowLeft"); page.keyboard.press("ArrowLeft")
            att(f"I. {arbre} : ← deux fois : on est revenu à la 1re subsidiaire", ["sub", 0], page.evaluate("[mode, pos]"))
            page.keyboard.press("=")
            att(f"I. {arbre} : = rejoue la 2e subsidiaire, celle qu'on vient de quitter", tires[1], page.evaluate("subs[pos]"))
            page.keyboard.press("="); page.keyboard.press("=")
            s = page.evaluate("[subs.slice(), pos]")
            att(f"I. {arbre} : puis la 3e rejouée, puis une NOUVELLE (4e)", (tires, 3), (s[0][:3], s[1]))
            att(f"I. {arbre} : la nouvelle n'est aucune des trois premières", True, s[0][3] not in tires)
            for _ in range(4): page.keyboard.press("ArrowLeft")
            att(f"I. {arbre} : ← jusqu'à la dernière question du parcours", ["answer", -1], page.evaluate("[mode, pos]"))
            att(f"I. {arbre} : le rond y est de nouveau visible (des questions à rejouer)", True, page.evaluate("!document.getElementById('sub').hidden"))
            page.context.close()

        # ============ J. fichier téléchargé depuis l'éditeur, rouvert ============
        for arbre in ("olivier", "chene"):
            page = C.nouvelle_page(nav, "1280x720", init_script=HASARD)
            page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(400)
            page.click(f"#choix-arbre button[data-arbre={arbre}]"); page.click("#btn-modifier"); page.wait_for_timeout(200)
            with page.expect_download() as dl: page.click("#btn-telecharger")
            chemin = DOSSIER / f"telecharge_{arbre}.html"; dl.value.save_as(chemin)
            html = chemin.read_text(encoding="utf-8")
            att(f"J. {arbre} : le rond (#sub) et la touche = sont dans le fichier téléchargé", (True, True, True), ('id="sub"' in html, "scene.sub" in html, "subTirer" in html))
            page.context.close()
            page = ouvrir(nav, arbre, fichier=chemin)
            nb = page.evaluate("NB_VOTES"); jouer_parcours(page, nb)
            att(f"J. {arbre} : fichier rouvert : le rond est visible à la dernière question", True, page.evaluate("!document.getElementById('sub').hidden"))
            page.keyboard.press("="); page.wait_for_timeout(300)
            att(f"J. {arbre} : fichier rouvert : = affiche une question subsidiaire, carte au fond du thème", ("sub", True), (page.evaluate("mode"), page.evaluate("document.querySelector('#panel .card').style.background !== ''")))
            page.click("#sub"); page.wait_for_timeout(200)
            att(f"J. {arbre} : fichier rouvert : le clic sur le rond tire la suivante", 2, page.evaluate("subs.length"))
            page.keyboard.press("Enter"); page.wait_for_timeout(300)
            att(f"J. {arbre} : fichier rouvert : Entrée -> tableau final", "end", page.evaluate("mode"))
            att(f"J. {arbre} : fichier rouvert : aucune erreur, aucune requête", ([], []), (page.erreurs, C.requetes_suspectes(page)))
            page.context.close()

        # ============ K. les comparaisons aux images de référence masquent le rond, comme les trois autres ============
        # (le rond peut maintenant être visible à plusieurs des états comparés ; il recouvre le coin du cadre du dessin : sans masque, ces états ne seraient plus identiques)
        import comparer_reference as R
        for arbre, etats in (("olivier", R.ETATS_OLIVIER), ("chene", R.ETATS_CHENE)):
            page = ouvrir(nav, arbre)
            visibles = []
            for nom, e in etats.items():
                chemin = [R.CIBLES[arbre]["ids"](q) for q in e["path"]]
                page.evaluate("(e) => applyState(e)", {"mode": e["mode"], "ti": e["ti"], "path": chemin}); page.wait_for_timeout(60)
                if page.evaluate("!document.getElementById('sub').hidden"): visibles.append(nom)
            infos.append(f"K. {arbre} : le rond est visible à {len(visibles)} des {len(etats)} états comparés aux images de référence ({visibles}) : le banc de comparaison le masque, les références ne sont pas touchées")
            att(f"K. {arbre} : le banc de comparaison masque le rond (#sub) comme #rst, #sortie, #prev, #next", True, "#sub" in pathlib.Path(C.RACINE / "tests" / "comparer_reference.py").read_text(encoding="utf-8"))
            page.context.close()

        # ============ L. à chaque moment du parcours ============
        for arbre in ("olivier", "chene"):
            page = ouvrir(nav, arbre); nb_votes = page.evaluate("NB_VOTES")
            for _ in range(4): page.keyboard.press("ArrowRight"); page.wait_for_timeout(1300)
            page.keyboard.press("ArrowRight"); page.wait_for_timeout(200)          # premier vote
            positions = []
            for v in range(nb_votes):
                page.keyboard.press(CHOIX[v % 8]); page.wait_for_timeout(120)
                positions.append(("réponse", v + 1, page.evaluate(SIG_JS)))
                if v < nb_votes - 1:
                    page.keyboard.press("ArrowRight"); page.wait_for_timeout(120)
                    positions.append(("vote", v + 2, page.evaluate(SIG_JS)))
            page.context.close()
            vus = 0
            for nom, k, sig0 in positions:
                if not sig0["rond"]: continue
                vus += 1
                page = ouvrir(nav, arbre)
                page.evaluate("(e) => applyState({mode: e.mode, ti: 3, path: e.path})", sig0)
                page.wait_for_timeout(150)
                avant = page.evaluate(SIG_JS)
                touche = "+" if vus % 2 == 0 else "="
                page.keyboard.press(touche); page.wait_for_timeout(250)
                s1 = page.evaluate(SIG_JS)
                att(f"L. {arbre} {nom} {k} : {touche} tire une subsidiaire (carte au fond d'un thème, un fruit de plus allumé)", ("sub", 1, True), (s1["mode"], len(s1["subs"]), s1["carte"] != avant["carte"] and "card s" in s1["carte"]))
                att(f"L. {arbre} {nom} {k} : le parcours reste le même (chemin) pendant la subsidiaire", avant["path"], s1["path"])
                att(f"L. {arbre} {nom} {k} : un fruit de plus allumé, sans en éteindre aucun", True, set(avant["halos"]) < set(s1["halos"]) and len(s1["halos"]) == len(avant["halos"]) + 1)
                page.keyboard.press("ArrowLeft"); page.wait_for_timeout(250)
                s2 = page.evaluate(SIG_JS)
                att(f"L. {arbre} {nom} {k} : ← ramène EXACTEMENT là où on s'était arrêté (état, mascotte, carte, fruits)", (avant["mode"], avant["path"], avant["bird"], avant["carte"], avant["halos"]), (s2["mode"], s2["path"], s2["bird"], s2["carte"], s2["halos"]))
                page.keyboard.press("="); page.wait_for_timeout(250)
                s3 = page.evaluate(SIG_JS)
                att(f"L. {arbre} {nom} {k} : = rejoue la subsidiaire qu'on vient de quitter (même question, même mascotte)", (s1["subs"], s1["bird"], s1["carte"]), (s3["subs"], s3["bird"], s3["carte"]))
                page.keyboard.press("ArrowRight"); page.wait_for_timeout(1300)
                s4 = page.evaluate(SIG_JS)
                ref = ouvrir(nav, arbre); ref.evaluate("(e) => applyState({mode: e.mode, ti: 3, path: e.path})", sig0); ref.wait_for_timeout(150)
                ref.keyboard.press("ArrowRight"); ref.wait_for_timeout(1300); r4 = ref.evaluate(SIG_JS)
                att(f"L. {arbre} {nom} {k} : → reprend le parcours là où il en était : même suite que sans subsidiaire (état, mascotte, carte, fruits)", (r4["mode"], r4["path"], r4["bird"], r4["carte"], r4["halos"]), (s4["mode"], s4["path"], s4["bird"], s4["carte"], s4["halos"]))
                att(f"L. {arbre} {nom} {k} : après → la subsidiaire est mémorisée une fois pour la liste du soir, et le parcours repart sans escapade en cours", (1 if r4["mode"] != "end" else 1, True), (len(s4["subs"]), page.evaluate("pos") == -1 or r4["mode"] == "end"))
                att(f"L. {arbre} {nom} {k} : aucune erreur", [], page.erreurs)
                page.context.close(); ref.context.close()
            infos.append(f"L. {arbre} : {vus} positions du parcours sur {len(positions)} offrent des subsidiaires (les autres : aucune question n'est sûre), toutes vérifiées")
            att(f"L. {arbre} : la plupart des positions offrent des subsidiaires", True, vus >= len(positions) - 1)
            # tableau final : = puis ← ramène au même tableau, pixel pour pixel
            page = ouvrir(nav, arbre); jouer_parcours(page, nb_votes); page.keyboard.press("Enter"); page.wait_for_timeout(400)
            fin0 = (page.screenshot(), page.evaluate(SIG_JS))
            page.keyboard.press("="); page.wait_for_timeout(250)
            att(f"L. {arbre} tableau final : = tire une subsidiaire", "sub", page.evaluate("mode"))
            page.keyboard.press("ArrowLeft"); page.wait_for_timeout(400)
            fin1 = (page.screenshot(), page.evaluate(SIG_JS))
            att(f"L. {arbre} tableau final : ← ramène au tableau final, identique pixel pour pixel", True, fin0[0] == fin1[0])
            att(f"L. {arbre} tableau final : la subsidiaire tirée à cet endroit est comptée", (fin0[1]["subs"], len(fin1[1]["subs"])), ([], 1))
            page.context.close()
            # au vote : les deux cartes restent proposées au retour, et choisir après coup efface l'escapade
            page = ouvrir(nav, arbre)
            for _ in range(4): page.keyboard.press("ArrowRight"); page.wait_for_timeout(1300)
            page.keyboard.press("ArrowRight"); page.keyboard.press("ArrowUp"); page.keyboard.press("ArrowRight"); page.wait_for_timeout(200)
            cartes0 = page.evaluate("document.getElementById('panel').innerHTML")
            page.keyboard.press("="); page.wait_for_timeout(200)
            att(f"L. {arbre} vote 2 : pendant la subsidiaire les deux questions du vote restent allumées dans l'arbre", True, page.evaluate("document.querySelectorAll('#svg .cand').length") == 2)
            page.keyboard.press("ArrowLeft"); page.wait_for_timeout(200)
            att(f"L. {arbre} vote 2 : ← ramène les deux cartes du vote, identiques", cartes0, page.evaluate("document.getElementById('panel').innerHTML"))
            page.keyboard.press("ArrowUp"); page.wait_for_timeout(100)
            att(f"L. {arbre} vote 2 : on peut choisir après être revenu (la réponse s'affiche)", "answer", page.evaluate("mode"))
            page.context.close()

        # ============ M. par le calcul, chaque position de chaque parcours : le tirage = ce qui ne s'affichera dans AUCUNE suite possible ============
        for arbre in ("olivier", "chene"):
            page = ouvrir(nav, arbre)
            table = {d["id"]: d for d in page.evaluate("D")}; depart = page.evaluate("FICHE.depart")
            complets = []
            def descendre(path):
                d = table[path[-1]]
                if not d.get("stay"): complets.append(path); return
                for c in (d["stay"], d["change"]): descendre(path + [c])
            for f in depart: descendre([f])
            def montre(path):
                v = set(depart)
                for i in path:
                    v.add(i); d = table[i]
                    if d.get("stay"): v.update((d["stay"], d["change"]))
                return v
            positions = [("trunk", 0, [])] + [("choose", 3, [])]
            def poser(path):
                positions.append(("answer", 3, path)); d = table[path[-1]]
                if d.get("stay"):
                    positions.append(("choose", 3, path))
                    for c in (d["stay"], d["change"]): poser(path + [c])
                else: positions.append(("end", 3, path))
            for f in depart: poser([f])
            etats = [dict(mode=m, ti=t, path=p_) for m, t, p_ in positions]
            pools = page.evaluate("(es) => es.map(e => { applyState({...e, subs: []}); return subRestantes(); })", etats)
            fautes = []
            for e, pool in zip(etats, pools):
                suites = [c for c in complets if c[:len(e["path"])] == e["path"]]
                a_venir = set().union(*[montre(c) for c in suites]) if suites else set()
                attendu = sorted(set(table) - a_venir - montre(e["path"]) - (set(depart) if e["mode"] != "trunk" else set(depart)))
                if sorted(pool) != attendu: fautes.append((e["mode"], ">".join(e["path"]), sorted(pool), attendu))
            att(f"M. {arbre} : sur les {len(etats)} positions, le tirage = exactement ce qui ne s'affichera dans aucune suite possible", [], fautes[:3])
            # le contrôle sait échouer : un tirage qui contiendrait une question à venir, ou qui en oublierait une, doit être attrapé
            e0 = next(e for e, pl in zip(etats, pools) if e["mode"] == "answer" and len(e["path"]) == 3 and pl)
            pool0 = pools[etats.index(e0)]
            suites = [c for c in complets if c[:3] == e0["path"]]
            futur = sorted(set().union(*[montre(c) for c in suites]) - montre(e0["path"]))
            attendu0 = sorted(set(table) - set().union(*[montre(c) for c in suites]) - montre(e0["path"]))
            att(f"M. {arbre} : (contrôle) un tirage avec une question à venir en trop est attrapé", True, sorted(pool0 + [futur[0]]) != attendu0)
            att(f"M. {arbre} : (contrôle) un tirage qui oublie une question sûre est attrapé", True, sorted(pool0[1:]) != attendu0)
            tailles = {}
            for e, pl in zip(etats, pools):
                k = e["mode"] + (str(len(e["path"])) if e["mode"] != "trunk" else "")
                tailles.setdefault(k, []).append(len(pl))
            infos.append(f"M. {arbre} : nombre de questions disponibles selon la position (min-max) : " + ", ".join(f"{k} {min(v)}-{max(v)}" for k, v in tailles.items() if k.startswith(('answer', 'trunk', 'choose0'))))
            page.context.close()

        # ============ N. parcours au hasard : jamais en double, jamais dans le parcours ============
        MARCHE_JS = """(args) => { const [graine, n, mutant] = args; let s = graine; const R = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
          const vieux = oublierSubsApres; if (mutant) oublierSubsApres = () => { avancer(); };       // le mutant : on n'oublie plus rien en revenant en arrière
          const fautes = [], vus = {sub: 0, fin: 0, recul: 0, choix: 0};
          resetAll();
          for (let i = 0; i < n; i++) { const r = R();
            if (r < .40) { if (mode === 'choose') { choose(R() < .5 ? 0 : 1); vus.choix++; } else next(); }
            else if (r < .55) { const avant = subs.length; subTirer(); if (subs.length > avant) vus.sub++; }
            else if (r < .76) { undo(); vus.recul++; }
            else if (r < .78) { resetAll(); }
            else if (mode === 'choose') { choose(R() < .5 ? 0 : 1); vus.choix++; } else next();
            if (new Set(subs).size !== subs.length) fautes.push(['doublon', i, subs.join()]);
            if (subs.some(q => path.includes(q))) fautes.push(['dans le parcours', i, subs.join(), path.join('>')]);
            if (subs.some(q => subRestantes().includes(q))) fautes.push(['retirable', i]);
            if (mode === 'end') vus.fin++;
            if (subs.length !== tags.length) fautes.push(['tags', i]);
            if (fautes.length > 3) break; }
          oublierSubsApres = vieux; resetAll(); return {fautes, vus}; }"""
        for arbre in ("olivier", "chene"):
            page = ouvrir(nav, arbre)
            r = page.evaluate(MARCHE_JS, [20261012, 4000, False])
            att(f"N. {arbre} : 4000 gestes au hasard : aucune subsidiaire en double ni dans le parcours", [], r["fautes"])
            att(f"N. {arbre} : le hasard a vraiment tout fait (tirages, retours, choix, tableau final)", True, all(r["vus"][k] > 30 for k in r["vus"]))
            m = page.evaluate(MARCHE_JS, [20261012, 4000, True])
            att(f"N. {arbre} : (contrôle) sans l'oubli des subsidiaires au retour en arrière, le test attrape une faute", True, bool(m["fautes"]))
            infos.append(f"N. {arbre} : {r['vus']} (gestes au hasard) ; sans l'oubli au retour, première faute attrapée : {m['fautes'][:1]}")
            att(f"N. {arbre} : aucune erreur", [], page.erreurs)
            page.context.close()
    return echecs, infos


if __name__ == "__main__":
    echecs, infos = tester()
    for i in infos: print("   ·", i)
    ok = C.bilan("les questions subsidiaires (touche =, rond, tirage, carte, mascotte, retour, téléchargement)", echecs)
    sys.exit(0 if ok else 1)
