"""Fabrique la vignette de chaque arbre (petite image JPEG) à partir du VRAI dessin et l'écrit dans index.html
(bloc « vignettes-arbres »). À relancer quand le dessin d'un arbre change : test_arbres.py vérifie qu'elle est à jour.

Usage :  .venv/bin/python tests/fabriquer_vignette.py [écrire]     (sans argument : calcule et compare seulement)
"""
import sys, re, json, pathlib
from playwright.sync_api import sync_playwright
import _commun as C

LARGEUR, HAUTEUR = 240, 258          # affichée à 120 x 129 px (écrans à double densité)


def _photo(nav, arbre_id):
    import base64
    page = C.nouvelle_page(nav, "1280x720")
    page.goto((C.RACINE / "index.html").as_uri()); page.wait_for_timeout(400)
    page.evaluate("(id) => { installerArbre(id); vue = null; vueCle = null; Editeur.refaire(); }", arbre_id)
    page.evaluate("ouvrirScene()"); page.wait_for_function("ecran === 'scene'"); C.attendre_dessin(page); page.wait_for_timeout(1600)
    page.add_style_tag(content="#rst,#sub,#sortie,#prev,#next{visibility:hidden!important}")
    png = page.locator("#svg").screenshot()
    url = page.evaluate("""async ([b64, W, H]) => {
      const img = await new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = 'data:image/png;base64,' + b64; });
      const ratio = 900 / 968, sh = img.height, sw = sh * ratio, sx = (img.width - sw) / 2;       // on rogne la marge autour du dessin
      const c = document.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d');
      x.fillStyle = '#fff'; x.fillRect(0, 0, W, H); x.imageSmoothingQuality = 'high'; x.drawImage(img, sx, 0, sw, sh, 0, 0, W, H);
      return c.toDataURL('image/jpeg', 0.82); }""", [base64.b64encode(png).decode(), LARGEUR, HAUTEUR])
    page.context.close()
    return url


def fabriquer(arbre_id, nav=None):
    """nav : un navigateur déjà ouvert (sinon on en ouvre un)."""
    if nav is not None:
        return _photo(nav, arbre_id)
    with sync_playwright() as p:
        n = C.lancer(p)
        try: return _photo(n, arbre_id)
        finally: n.close()


if __name__ == "__main__":
    f = C.RACINE / "index.html"; s = f.read_text(encoding="utf-8")
    m = re.search(r'(<script type="application/json" id="vignettes-arbres">)(.*?)(</script>)', s, re.S)
    actuel = json.loads(m.group(2))
    neuf = {k: fabriquer(k) for k in ("olivier", "chene")}
    if "écrire" in sys.argv[1:]:
        f.write_text(s[:m.start(2)] + json.dumps(neuf, separators=(",", ":")) + s[m.end(2):], encoding="utf-8")
        print({k: f"{len(v)} caractères" for k, v in neuf.items()}, "-> écrit dans index.html")
    else:
        print({k: (len(v), "identique" if actuel.get(k) == v else "différente") for k, v in neuf.items()})
