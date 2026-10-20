"""Structure des votes de chaque arbre, PAR LE CALCUL : on énumère tous les parcours possibles à partir de la table de l'arbre
telle que l'application la charge (DESSINS.<id>.structure + .depart), puis on compte.

 - partout : aucune répétition dans un parcours ; toutes les questions peuvent sortir ; à chaque vote une jaune ET une bleue
 - olivier : 23 questions, 8 votes, 256 parcours
 - chêne   : les chiffres de la fiche n° 15 (26 questions, 7 votes, 128 parcours ; chaque question sort 16 à 64 fois ; 224 visites par
   thème ; 16 sauts vers un thème voisin et 6 à deux thèmes ; « jaune = rester » sur 64 parcours à chaque vote ; 2 à 4 fois sur 6 par parcours)
S'ils diffèrent, c'est que la table ou les identifiants ont été altérés : le test échoue.

Usage :  .venv/bin/python tests/test_structure.py
"""
import sys, json
from collections import Counter
from playwright.sync_api import sync_playwright
import _commun as C


def analyser(fiche):
    by = {d["id"]: d for d in fiche["structure"]}
    ordre = [t["id"] for t in fiche["themes"]]
    parcours = []
    def explorer(chemin):
        d = by[chemin[-1]]
        if "stay" not in d: parcours.append(chemin); return
        explorer(chemin + [d["stay"]]); explorer(chemin + [d["change"]])
    for dep in fiche["depart"]: explorer([dep])
    nb_votes = max(d["step"] for d in fiche["structure"])
    sorties = Counter(q for p in parcours for q in p)
    visites = Counter(by[q]["theme"] for p in parcours for q in p)
    ecarts = Counter(abs(ordre.index(d["theme"]) - ordre.index(by[d["change"]]["theme"])) for d in fiche["structure"] if "change" in d)
    jaune_rester = {k: sum(1 for p in parcours if by[by[p[k - 2]]["stay"]]["color"] == "j") for k in range(2, nb_votes + 1)}
    par_parcours = Counter(sum(1 for k in range(2, nb_votes + 1) if by[by[p[k - 2]]["stay"]]["color"] == "j") for p in parcours)
    sans_paire = [d["id"] for d in fiche["structure"] if "stay" in d and by[d["stay"]]["color"] == by[d["change"]]["color"]]
    if by[fiche["depart"][0]]["color"] == by[fiche["depart"][1]]["color"]: sans_paire.append("départ")
    return dict(questions=len(by), votes=nb_votes, parcours=len(parcours), repetitions=sum(1 for p in parcours if len(set(p)) != len(p)),
                longueurs=sorted(set(len(p) for p in parcours)), jamais=[q for q in by if sorties[q] == 0], sortie_min=min(sorties.values()), sortie_max=max(sorties.values()),
                visites=dict(sorted(visites.items())), ecarts=dict(sorted(ecarts.items())), jaune_rester=jaune_rester, par_parcours=dict(sorted(par_parcours.items())),
                sans_paire=sans_paire, par_theme={t: sum(1 for d in fiche["structure"] if d["theme"] == t) for t in ordre},
                themes_ids_ok=set(d["theme"] for d in fiche["structure"]) == set(ordre), ids_prefixes=all(d["id"].startswith(d["theme"]) and d["id"][len(d["theme"]):] == str(d["step"]) for d in fiche["structure"]))


ATTENDU = {
    "olivier": dict(questions=23, votes=8, parcours=256, par_theme={"I": 8, "L": 7, "A": 8}),
    "chene": dict(questions=26, votes=7, parcours=128, sortie_min=16, sortie_max=64, visites={"A": 224, "B": 224, "C": 224, "D": 224}, ecarts={1: 16, 2: 6},
                  jaune_rester={k: 64 for k in range(2, 8)}, par_theme={"A": 7, "B": 6, "C": 6, "D": 7}, par_parcours={2: 32, 3: 64, 4: 32}),
}


def tester():
    echecs, infos = [], []
    with sync_playwright() as p:
        nav = C.lancer(p); page = C.nouvelle_page(nav, "800x600")
        page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(400)
        fiches = page.evaluate("Object.fromEntries(Object.entries(DESSINS).filter(([k]) => !k.endsWith('_test')).map(([k, f]) => [k, {structure: f.structure, depart: f.depart, themes: f.themes.map(t => ({id: t.id}))}]))")
        nav.close()
    for arbre, fiche in fiches.items():
        r = analyser(fiche); infos.append(f"{arbre} : {json.dumps({k: r[k] for k in ('questions', 'votes', 'parcours', 'sortie_min', 'sortie_max', 'visites', 'ecarts', 'par_parcours')}, ensure_ascii=False)}")
        def att(nom, attendu, obtenu):
            if attendu != obtenu: echecs.append(f"{arbre} : {nom} : attendu {attendu!r}, obtenu {obtenu!r}")
        att("aucune répétition dans un parcours", 0, r["repetitions"])
        att("chaque parcours traverse exactement une question par vote", [r["votes"]], r["longueurs"])
        att("toutes les questions peuvent sortir", [], r["jamais"])
        att("chaque vote propose une jaune et une bleue", [], r["sans_paire"])
        att("nombre de parcours = 2 puissance (nombre de votes)", 2 ** r["votes"], r["parcours"])
        att("les thèmes de la table sont ceux de la fiche", True, r["themes_ids_ok"])
        att("identifiant = identifiant du thème + niveau (comme l'olivier)", True, r["ids_prefixes"])
        for cle, valeur in ATTENDU.get(arbre, {}).items():
            att(cle, valeur, r[cle])
    return echecs, infos


if __name__ == "__main__":
    echecs, infos = tester()
    for l in infos: print("  " + l)
    sys.exit(0 if C.bilan("structure des votes par le calcul (tous les parcours de chaque arbre)", echecs) else 1)
