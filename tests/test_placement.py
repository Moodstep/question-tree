"""Placement des glands et des liens du chêne, PAR LE CALCUL, sur le dessin réellement produit par l'application.

Les positions des glands et les courbes des liens sont relues dans le SVG de l'application (pas dans les données). Les définitions
sont celles du script de placement de Joanna (placer_glands7.js) : contour de 10 points autour du gland pour la couleur, liens
échantillonnés en 17 points, croisements entre liens qui ne partagent aucun gland. La géométrie des thèmes (themeAt, rminAt, rmaxAt,
FAN) est celle du fichier de référence ouvert à côté, jamais celle de l'application.

 - 26 glands, 44 liens
 - aucun gland hors de sa couleur (ni trop près du pied ou du bord du feuillage)
 - plus petite distance entre un lien et un gland qui n'en est pas une extrémité : 31 une fois arrondie (le calcul donne 30,9 ; seuil 30,5)
 - 22 croisements de liens (le minimum possible avec cette structure est 19)
 - plus petite distance entre deux glands de thèmes différents : 79 une fois arrondie (seuil 78,5)

Usage :  .venv/bin/python tests/test_placement.py
"""
import sys, re, math
from playwright.sync_api import sync_playwright
import _commun as C
import comparer_reference as R

RING = [(0, -33), (20, -26), (26, -6), (23, 12), (14, 29), (0, 33), (-14, 29), (-23, 12), (-26, -6), (-20, -26)]
LETTRE_VERS_CHIFFRE = {"A": "1", "B": "2", "C": "3", "D": "4"}


def lire_dessin(page):
    return page.evaluate("""() => {
      const svg = document.getElementById('svg'), groupes = [...svg.children];
      const olives = groupes.find(e => e.querySelector && e.querySelector('title') && e.tagName.toLowerCase() === 'g');
      const glands = {}; olives.querySelectorAll(':scope > g').forEach(g => { const m = /translate\\(([-\\d.]+) ([-\\d.]+)\\)/.exec(g.getAttribute('transform')); glands[g.querySelector('title').textContent] = [+m[1], +m[2]]; });
      const liens = groupes.filter(e => e.tagName.toLowerCase() === 'g' && e.getAttribute('stroke-linecap') === 'round').map(g => [...g.querySelectorAll('path')].map(p => p.getAttribute('d')));
      return {glands, liens: liens[liens.length - 1]};      // le dernier groupe de liens est celui des traits colorés (le premier est la bordure d'encre)
    }""")


def courbe(d):
    n = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]
    sx, sy, c1x, c1y, c2x, c2y, ex, ey = n
    pts = []
    for k in range(17):
        t, u = k / 16, 1 - k / 16
        pts.append((u**3*sx + 3*u*u*t*c1x + 3*u*t*t*c2x + t**3*ex, u**3*sy + 3*u*u*t*c1y + 3*u*t*t*c2y + t**3*ey))
    return (sx, sy, ex, ey), pts


def tester():
    echecs, infos = [], []
    with sync_playwright() as p:
        nav = C.lancer(p)
        app = C.nouvelle_page(nav, "1280x720"); C.variante_avec_noms(C.CAPTURES / "variante_noms_chene.html", "chene")
        app.goto((C.CAPTURES / "variante_noms_chene.html").as_uri()); app.wait_for_timeout(400); C.lancer_scene(app)
        ref = C.nouvelle_page(nav, "1280x720"); C.reference_avec_polices(C.CAPTURES / "ref_test_chene.html", "chene-brouillon.html")
        ref.goto((C.CAPTURES / "ref_test_chene.html").as_uri()); ref.wait_for_timeout(500)
        dess = lire_dessin(app); G = dess["glands"]
        # côté application : id -> thème (lettre), via la table
        theme = app.evaluate("Object.fromEntries(D.map(d => [d.id, d.theme]))")
        # --- 1. couleur : on interroge la géométrie de la RÉFÉRENCE ---
        hors = []
        for gid, (x, y) in G.items():
            viol = ref.evaluate("""([x, y, t, ring]) => { let v = 0; for (const [dx, dy] of ring) { const p = polar(x + dx, y + dy); if (themeAt(x + dx, y + dy) !== t) v += 1;
                if (p.r < rminAt(p.th) + 6 || p.r > rmaxAt(p.th) * .93 || p.th > FAN.thL + 3 || p.th < FAN.thR - 3) v += 1; } return v; }""", [x, y, LETTRE_VERS_CHIFFRE[theme[gid]], RING])
            if viol: hors.append((gid, viol))
        # --- 2. liens : extrémités -> glands, croisements, distances ---
        def gland_proche(x, y, dy):
            return min(G, key=lambda g: math.hypot(G[g][0] - x, G[g][1] + dy - y))
        liens = []
        for d in dess["liens"]:
            (sx, sy, ex, ey), pts = courbe(d)
            a, b = gland_proche(sx, sy, -8), gland_proche(ex, ey, 8)
            liens.append((a, b, pts))
        def inter(p, q, r, s):
            o = lambda a, b, c: (1 if (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]) > 0 else -1 if (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]) < 0 else 0)
            return o(p, q, r) * o(p, q, s) < 0 and o(r, s, p) * o(r, s, q) < 0
        croisements = 0
        for i in range(len(liens)):
            for j in range(i + 1, len(liens)):
                if {liens[i][0], liens[i][1]} & {liens[j][0], liens[j][1]}: continue
                A, B = liens[i][2], liens[j][2]
                if any(inter(A[u], A[u+1], B[v], B[v+1]) for u in range(16) for v in range(16)): croisements += 1
        def dist_poly(px, py, A):
            m = 1e9
            for u in range(len(A) - 1):
                (x1, y1), (x2, y2) = A[u], A[u+1]; dx, dy = x2 - x1, y2 - y1; l2 = dx*dx + dy*dy
                t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / l2)) if l2 else 0
                m = min(m, math.hypot(px - x1 - t*dx, py - y1 - t*dy))
            return m
        mini, ou = 1e9, ""
        for a, b, pts in liens:
            for gid, (x, y) in G.items():
                if gid in (a, b): continue
                dd = dist_poly(x, y, pts)
                if dd < mini: mini, ou = dd, f"{a}→{b} / {gid}"
        entre = min(math.hypot(G[a][0]-G[b][0], G[a][1]-G[b][1]) for a in G for b in G if a < b and theme[a] != theme[b])
        infos.append(f"{len(G)} glands, {len(liens)} liens ; hors couleur : {len(hors)} ; croisements : {croisements} ; lien–gland le plus proche : {mini:.1f} ({ou}) ; entre thèmes : {entre:.1f}")
        def att(nom, attendu, obtenu):
            if attendu != obtenu: echecs.append(f"{nom} : attendu {attendu!r}, obtenu {obtenu!r}")
        att("26 glands", 26, len(G)); att("44 liens", 44, len(liens))
        att("chaque lien relie deux glands distincts", True, all(a != b for a, b, _ in liens))
        att("aucun gland hors de sa couleur", [], hors)
        att("22 croisements de liens", 22, croisements)
        att("lien–gland : au moins 30,5 (« 31 » une fois arrondi ; le calcul donne 30,9)", True, mini >= 30.5)
        att("glands de thèmes différents : au moins 78,5 (« 79 » une fois arrondi)", True, entre >= 78.5)
        att("aucune erreur JS", [], app.erreurs + ref.erreurs)
        nav.close()
    return echecs, infos


if __name__ == "__main__":
    echecs, infos = tester()
    for l in infos: print("  " + l)
    sys.exit(0 if C.bilan("chêne : placement des glands et des liens, par le calcul", echecs) else 1)
