"""Outils communs aux tests de « Mes arbres » (test_bibliotheque.py, test_pdf.py) : fabrique de parcours, déroulé de la scène au clavier."""
import os, pathlib
import _commun as C

FICHIER = pathlib.Path(os.environ.get("ARBRE_FICHIER") or (C.RACINE / "index.html"))   # ARBRE_FICHIER : un fichier volontairement abîmé (mutant)

# tous les parcours terminés d'un dessin, par le calcul sur sa table des votes (aucune variable de la page n'est modifiée)
CHEMINS_JS = """(id) => { const f = DESSINS[id], par = {}; f.structure.forEach(d => par[d.id] = d); const out = [];
  const aller = p => { const d = par[p[p.length - 1]]; if (!d.stay) { out.push(p); return; } [d.stay, d.change].forEach(c => aller(p.concat(c))); };
  f.depart.forEach(s => aller([s])); return out; }"""
FABRIQUE_JS = """([dessin, path, extra]) => Object.assign({id: 'p' + Math.random().toString(36).slice(2, 10), debut: '2026-10-07T10:00:00.000Z', fin: '2026-10-07T11:00:00.000Z',
  nom: '', path, subs: [], copie: {dessin, titre: 'Titre de test', themes: DESSINS[dessin].themes.map(t => ({id: t.id, nom: 'Nom ' + t.id})),
  tronc: ['T un', 'T deux', 'T trois', 'T quatre'], questions: {}}}, extra || {})"""


class Bilan:
    def __init__(self): self.echecs = []
    def att(self, nom, attendu, obtenu):
        if attendu != obtenu:
            self.echecs.append(f"{nom} : attendu {str(attendu)[:160]!r}, obtenu {str(obtenu)[:160]!r}")
    def vrai(self, nom, cond, detail=""):
        if not cond:
            self.echecs.append(f"{nom} {detail}")


def ouvrir(nav, taille="1280x720", **kw):
    page = C.nouvelle_page(nav, taille, **kw)
    page.goto(FICHIER.as_uri()); page.wait_for_timeout(500)
    return page


# horloge qui avance de 5 ms à chaque lecture : sans elle, deux écritures voisines portent la même milliseconde et leur ordre ne se voit pas
HORLOGE = """(() => { const R = Date; let t = R.now(); const N = function (...a) { if (a.length) return new R(...a); t += 5; return new R(t); };
  N.now = () => (t += 5); N.prototype = R.prototype; N.parse = R.parse; N.UTC = R.UTC; window.Date = N; })();"""
HASARD = "window.__hasard = () => { window.__h = (window.__h || 0) + 1; return (window.__h * 0.3819) % 1; };"
CHOIX = ["ArrowUp", "ArrowDown", "ArrowDown", "ArrowUp", "ArrowDown", "ArrowUp", "ArrowUp", "ArrowDown"]
AUTRE = {"ArrowUp": "ArrowDown", "ArrowDown": "ArrowUp"}


def touche(page, k, attente=40):
    page.keyboard.press(k); page.wait_for_timeout(attente)


def jouer(page, choix=CHOIX, fin=True):
    """Du premier écran de la scène jusqu'au tableau final (fin=True) ou jusqu'à la réponse du dernier vote (fin=False)."""
    for _ in range(4): touche(page, "ArrowRight")
    for i, c in enumerate(choix):
        touche(page, c)
        if i < len(choix) - 1 or fin: touche(page, "ArrowRight")


def parcours_ici(page): return page.evaluate("Bibliotheque.parcoursDe(ARBRE.id)")


def preparer(nav, taille="1280x720"):
    """Un arbre d'olivier avec un titre et deux questions écrites, la scène lancée, réseau coupé."""
    page = ouvrir(nav, taille, init_script=HASARD)
    page.click("#btn-modifier"); page.wait_for_timeout(100)
    page.fill("#f-titre", "Conférence d'essai"); page.fill("#f-q-I1", "Première question écrite"); page.fill("#f-q-I2", "Deuxième question écrite")
    page.click("#btn-retour-prepa"); page.wait_for_timeout(100)
    C.lancer_scene(page)
    return page
