"""Le PDF d'une session : 2 pages A4 portrait (recto = l'arbre et son parcours, verso = toutes les questions, les posées en surbrillance).

 A. Le PLAN du verso (une fonction pure, avant de regarder le moindre pixel) : chaque question de la table une seule fois, les posées numérotées dans l'ordre
    (4 du tronc, puis le parcours), les subsidiaires repérées S1…, les « proposées mais non choisies » distinguées des « jamais apparues », textes tirés de la
    COPIE du parcours (jamais de l'arbre vivant), question vide -> « Question I3 ».
 B. Le fichier PDF : structure lue par un analyseur écrit ici, second lecteur (macOS), pixels des deux pages.
 C. Le pire cas : toutes les questions au maximum de longueur, en majuscules, tronc et titre au maximum, 3 subsidiaires.

Usage :  .venv/bin/python tests/test_pdf.py [A B C]
"""
import re, sys, json, random, pathlib, shutil, subprocess
from playwright.sync_api import sync_playwright
import _commun as C
from _mes_arbres import FICHIER, CHEMINS_JS, FABRIQUE_JS, Bilan, ouvrir

TMP = C.CAPTURES / "pdf"
shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir(parents=True)

# l'ensemble de ce qui a été MONTRÉ à la salle, calculé ici indépendamment du code testé : les 2 départs, les 2 options de chaque vote
MONTRE_JS = """([dessin, path]) => { const f = DESSINS[dessin], par = {}; f.structure.forEach(d => par[d.id] = d);
  const vu = new Set(f.depart); path.forEach(i => { const d = par[i]; if (d.stay) { vu.add(d.stay); vu.add(d.change); } }); return [...vu]; }"""
TOUTES_JS = "(dessin) => DESSINS[dessin].structure.map(d => d.id)"


def section_A(nav, b):
    page = ouvrir(nav)
    hasard = random.Random(20261007)
    for dessin in ("olivier", "chene"):
        chemins = page.evaluate(CHEMINS_JS, dessin); toutes = page.evaluate(TOUTES_JS, dessin)
        for essai in range(24):
            path = hasard.choice(chemins)
            montre = set(page.evaluate(MONTRE_JS, [dessin, path]))
            libres = [i for i in toutes if i not in montre]
            subs = hasard.sample(libres, hasard.choice([0, 1, 2, 3]))
            # la copie porte des textes reconnaissables ; une question est laissée vide
            questions = {i: f"Texte de {i}" for i in toutes}
            vide = hasard.choice([i for i in toutes if i not in path])
            questions[vide] = ""
            p = page.evaluate(FABRIQUE_JS, [dessin, path, {"subs": subs}])
            p["copie"]["questions"] = questions; p["copie"]["titre"] = f"Titre {dessin} {essai}"
            plan = page.evaluate("p => PdfParcours.planVerso(p)", p)
            nom = f"A : {dessin} #{essai}"
            lignes = [l for t in plan["themes"] for l in t["lignes"]]
            b.att(f"{nom} : chaque question de la table, une seule fois", sorted(toutes), sorted(l["id"] for l in lignes))
            posees = sorted((l for l in lignes if l["etat"] == "posee" and not l.get("sub")), key=lambda l: l["numero"])
            b.att(f"{nom} : les posées sont le parcours, numérotées 5, 6, 7…", [(i, 5 + k) for k, i in enumerate(path)], [(l["id"], l["numero"]) for l in posees])
            b.att(f"{nom} : les subsidiaires dans l'ordre, repérées 1…n", [(i, 1 + k) for k, i in enumerate(subs)],
                  [(l["id"], l["sub"]) for l in sorted((l for l in lignes if l.get("sub")), key=lambda l: l["sub"])])
            b.att(f"{nom} : les subsidiaires sont des posées", True, all(l["etat"] == "posee" for l in lignes if l.get("sub")))
            propo = {l["id"] for l in lignes if l["etat"] == "proposee"}
            b.att(f"{nom} : « proposée non choisie » = montrée à la salle, ni choisie ni tirée", sorted((montre - set(path)) - set(subs)), sorted(propo))
            b.att(f"{nom} : le reste n'est jamais apparu", sorted(set(toutes) - montre - set(subs)), sorted(l["id"] for l in lignes if l["etat"] == "absente"))
            b.att(f"{nom} : le tronc : 4 questions posées, numérotées 1 à 4", [1, 2, 3, 4], [t["numero"] for t in plan["tronc"]])
            b.att(f"{nom} : textes tirés de la copie", f"Texte de {path[0]}", [l for l in lignes if l["id"] == path[0]][0]["texte"])
            b.att(f"{nom} : question vide -> « Question {vide} »", f"Question {vide}", [l for l in lignes if l["id"] == vide][0]["texte"])
            niveaux = [[l["niveau"] for l in t["lignes"]] for t in plan["themes"]]
            b.vrai(f"{nom} : niveaux croissants dans chaque thème", all(n == sorted(n) for n in niveaux), str(niveaux))
            b.att(f"{nom} : un groupe par thème de la fiche", page.evaluate(f"DESSINS.{dessin}.themes.map(t => t.id)"), [t["id"] for t in plan["themes"]])
            if essai == 0:
                b.att(f"{nom} : le titre vient de la copie", f"Titre {dessin} 0", plan["titre"])
    # la copie ne dépend jamais de l'arbre vivant
    chemins = page.evaluate(CHEMINS_JS, "olivier")
    p = page.evaluate(FABRIQUE_JS, ["olivier", chemins[3], None]); p["copie"]["questions"] = {"I1": "Texte figé"}
    page.evaluate("ARBRE.questions.I1 = 'Texte vivant'; ARBRE.titre = 'Titre vivant'")
    plan = page.evaluate("p => PdfParcours.planVerso(p)", p)
    b.att("A : le texte vient de la copie, pas de l'arbre vivant", "Texte figé", [l for t in plan["themes"] for l in t["lignes"] if l["id"] == "I1"][0]["texte"])
    # « Question I3 » suit la langue
    p["copie"]["questions"] = {}
    page.evaluate("() => { document.getElementById('langue').value = 'de'; document.getElementById('langue').dispatchEvent(new Event('change')); }")
    plan = page.evaluate("p => PdfParcours.planVerso(p)", p)
    attendu = page.evaluate("tx('scene.question', {id: 'I3'})")
    b.att("A : une question vide s'écrit dans la langue courante", attendu, [l for t in plan["themes"] for l in t["lignes"] if l["id"] == "I3"][0]["texte"])
    b.vrai("A : aucune erreur de page", not page.erreurs, str(page.erreurs))
    page.context.close()

# ====================================================================== B
import base64, struct, tempfile

PDF_JS = """async p => { const o = await PdfParcours.fabriquer(p); let s = ''; for (let i = 0; i < o.length; i += 32768) s += String.fromCharCode.apply(null, o.subarray(i, i + 32768)); return btoa(s); }"""
TEXTES_JS = """async ([jpg, rect, png, zones]) => {
  const ouvrir = async (b64, type) => createImageBitmap(await (await fetch('data:' + type + ';base64,' + b64)).blob());
  const ia = await ouvrir(jpg, 'image/jpeg'), ib = await ouvrir(png, 'image/png'), sw = ib.height * 900 / 968, sx = (ib.width - sw) / 2, out = [];
  for (const z of zones) {            // z : {x, y, w, h} en pixels de la capture d'écran
    const u0 = (z.x - sx) / sw, v0 = z.y / ib.height, u1 = (z.x + z.w - sx) / sw, v1 = (z.y + z.h) / ib.height, W = 160, H = Math.max(16, Math.round(160 * z.h / z.w));
    const a = document.createElement('canvas'), b = document.createElement('canvas'); a.width = b.width = W; a.height = b.height = H;
    a.getContext('2d').drawImage(ia, rect.x + u0 * rect.l, rect.y + v0 * rect.h, (u1 - u0) * rect.l, (v1 - v0) * rect.h, 0, 0, W, H);
    b.getContext('2d').drawImage(ib, z.x, z.y, z.w, z.h, 0, 0, W, H);
    const da = a.getContext('2d').getImageData(0, 0, W, H).data, db = b.getContext('2d').getImageData(0, 0, W, H).data; let s = 0;
    for (let i = 0; i < da.length; i += 4) s += (Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2])) / 3;
    out.push(s / (W * H)); }
  return out; }"""
COMPARE_JS = """async ([jpg, rect, png]) => {
  const ouvrir = async (b64, type) => createImageBitmap(await (await fetch('data:' + type + ';base64,' + b64)).blob());
  const W = 360, H = 387, a = document.createElement('canvas'), b = document.createElement('canvas'); a.width = b.width = W; b.height = a.height = H;
  const ia = await ouvrir(jpg, 'image/jpeg'), ib = await ouvrir(png, 'image/png');
  const ca = a.getContext('2d'), cb = b.getContext('2d'); ca.fillStyle = cb.fillStyle = '#fff'; ca.fillRect(0, 0, W, H); cb.fillRect(0, 0, W, H);
  const sw = ib.height * 900 / 968, sx = (ib.width - sw) / 2;      // sur l'écran, l'élément est large : l'arbre en occupe le centre (rapport 900:968)
  ca.drawImage(ia, rect.x, rect.y, rect.l, rect.h, 0, 0, W, H); cb.drawImage(ib, sx, 0, sw, ib.height, 0, 0, W, H);
  // la texture du feuillage se rééchantillonne différemment d'un affichage à l'autre : on compare après deux réductions successives (fruits allumés, liens et noms restent)
  const reduire = (c, w, h) => { const r = document.createElement('canvas'); r.width = w; r.height = h; const x = r.getContext('2d'); x.imageSmoothingQuality = 'high'; x.drawImage(c, 0, 0, w, h); return r; };
  const sa = reduire(reduire(a, W / 2, H / 2), W / 6, H / 6), sb = reduire(reduire(b, W / 2, H / 2), W / 6, H / 6), w6 = W / 6, h6 = H / 6;
  const da = sa.getContext('2d').getImageData(0, 0, w6, h6).data, db = sb.getContext('2d').getImageData(0, 0, w6, h6).data; let somme = 0, forts = 0;
  for (let i = 0; i < da.length; i += 4) { const d = (Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2])) / 3; somme += d; if (d > 60) forts++; }
  const dif = document.createElement('canvas'); dif.width = w6; dif.height = h6; const cd = dif.getContext('2d'), id = cd.createImageData(w6, h6);
  for (let i = 0; i < da.length; i += 4) { const d = (Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2])) / 3; id.data[i] = id.data[i + 1] = id.data[i + 2] = 255 - Math.min(255, d * 3); id.data[i + 3] = 255; }
  cd.putImageData(id, 0, 0); const tri = document.createElement('canvas'); tri.width = W * 3; tri.height = H; const ct = tri.getContext('2d'); ct.drawImage(a, 0, 0); ct.drawImage(b, W, 0); ct.imageSmoothingEnabled = false; ct.drawImage(dif, 2 * W, 0, W, H);
  return {moyenne: somme / (w6 * h6), forts: forts / (w6 * h6), tri: tri.toDataURL('image/png')}; }"""
PIXELS_JS = """async ([jpg, cibles]) => {
  const im = await createImageBitmap(await (await fetch('data:image/jpeg;base64,' + jpg)).blob());
  const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const cx = c.getContext('2d'); cx.drawImage(im, 0, 0);
  const d = cx.getImageData(0, 0, c.width, c.height).data, res = {}; let blanc = 0;
  for (const k in cibles) res[k] = 0;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i] > 245 && d[i + 1] > 245 && d[i + 2] > 245) blanc++;
    for (const k in cibles) { const [r, g, b] = cibles[k]; if (Math.abs(d[i] - r) < 5 && Math.abs(d[i + 1] - g) < 5 && Math.abs(d[i + 2] - b) < 5) res[k]++; } }
  return {w: im.width, h: im.height, blanc: blanc / (c.width * c.height), ...res}; }"""
JAUNE_PALE, BLEU_PALE = (0xfb, 0xef, 0xc2), (0xdb, 0xe5, 0xf8)


def lire_pdf(octets):
    """Analyse minimale écrite pour le test : structure, table de références, pages, images. Renvoie (erreurs, {info})."""
    e, info = [], {}
    if not octets.startswith(b"%PDF-1.4\n"): e.append("pas d'en-tête %PDF-1.4")
    if not octets.endswith(b"%%EOF\n"): e.append("pas de %%EOF final")
    m = re.search(rb"startxref\n(\d+)\n%%EOF\n$", octets)
    if not m: return e + ["startxref introuvable"], info
    xref = int(m.group(1))
    if octets[xref:xref + 11] != b"xref\n0 10\n0": e.append(f"startxref ne pointe pas sur la table (octet {xref} : {octets[xref:xref + 12]!r})")
    else:
        corps = octets[xref + 10:xref + 10 + 200]
        for n in range(10):
            ligne = corps[n * 20:(n + 1) * 20]
            if len(ligne) != 20 or not re.fullmatch(rb"\d{10} \d{5} [nf] \n", ligne): e.append(f"entrée {n} de la table malformée : {ligne!r}"); continue
            if n and octets[int(ligne[:10]):int(ligne[:10]) + len(f"{n} 0 obj\n")] != f"{n} 0 obj\n".encode(): e.append(f"l'objet {n} n'est pas à l'octet annoncé")
    info["pages"] = len(re.findall(rb"/Type /Page /Parent 2 0 R", octets))
    kp = re.search(rb"/Type /Pages /Kids \[([^\]]*)\] /Count (\d+)", octets)
    info["kids"] = (len(kp.group(1).split(b" R")) - 1, int(kp.group(2))) if kp else None      # ce que le document ANNONCE : un lecteur suit cet arbre, pas la liste brute des objets
    info["mediabox"] = re.findall(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", octets)
    info["images"] = []
    for im in re.finditer(rb"/Subtype /Image /Width (\d+) /Height (\d+) /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length (\d+) >>\nstream\n", octets):
        n = int(im.group(3)); flux = octets[im.end():im.end() + n]
        if octets[im.end() + n:im.end() + n + 10] != b"\nendstream": e.append("la longueur d'un flux image ne tombe pas sur endstream")
        if flux[:2] != b"\xff\xd8" or flux[-2:] != b"\xff\xd9": e.append("un flux image n'est pas un JPEG complet")
        info["images"].append((int(im.group(1)), int(im.group(2)), flux))
    t = re.search(rb"/Title <FEFF([0-9A-Fa-f]*)>", octets)
    info["titre"] = bytes.fromhex(t.group(1).decode()).decode("utf-16-be") if t else None
    return e, info


def parcours_type(page, dessin, idx, subs=2, **copie):
    chemins = page.evaluate(CHEMINS_JS, dessin)
    p = page.evaluate(FABRIQUE_JS, [dessin, chemins[idx], None])
    libres = page.evaluate("""([d, path]) => { const f = DESSINS[d], par = {}; f.structure.forEach(x => par[x.id] = x); const vu = new Set(f.depart);
        path.forEach(i => { const x = par[i]; if (x.stay) { vu.add(x.stay); vu.add(x.change); } }); return f.structure.map(x => x.id).filter(i => !vu.has(i)); }""", [dessin, p["path"]])
    p["subs"] = libres[:subs]
    p["copie"]["titre"] = "Conférence d'essai — Lorient"
    p["copie"]["tronc"] = ["Première question du tronc ?", "Deuxième question du tronc ?", "Troisième question du tronc ?", "Quatrième question du tronc ?"]
    p["copie"]["questions"] = {i: f"Question {i} : comment la robustesse se construit-elle ?" for i in page.evaluate("d => DESSINS[d].structure.map(x => x.id)", dessin)}
    p["copie"].update(copie)
    return p


def section_B(nav, b):
    page = ouvrir(nav, "1280x720")
    for dessin, idx in (("olivier", 100), ("chene", 60)):
        p = parcours_type(page, dessin, idx)
        octets = base64.b64decode(page.evaluate(PDF_JS, p))
        f = TMP / f"b_{dessin}.pdf"; f.write_bytes(octets)
        erreurs, info = lire_pdf(octets)
        b.att(f"B : {dessin} : structure du PDF", [], erreurs)
        b.att(f"B : {dessin} : 2 pages", 2, info.get("pages"))
        b.att(f"B : {dessin} : l'arbre des pages annonce bien 2 pages", (2, 2), info.get("kids"))
        b.att(f"B : {dessin} : A4 (595,28 x 841,89 pt) sur les deux pages", [(b"595.28", b"841.89")] * 2, info.get("mediabox"))
        b.att(f"B : {dessin} : 2 images de 2067 x 2923", [(2067, 2923)] * 2, [(w, h) for w, h, _ in info.get("images", [])])
        b.att(f"B : {dessin} : le titre du document", p["copie"]["titre"], info.get("titre"))
        # second lecteur, indépendant : macOS
        png = TMP / f"b_{dessin}.png"
        r = subprocess.run(["sips", "-s", "format", "png", str(f), "--out", str(png)], capture_output=True, text=True)
        b.vrai(f"B : {dessin} : macOS (sips) sait lire et dessiner le PDF", r.returncode == 0 and png.exists() and png.stat().st_size > 50_000, r.stderr[-200:])
        if png.exists():
            g = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(png)], capture_output=True, text=True).stdout
            w, h = [int(x) for x in re.findall(r"pixel(?:Width|Height): (\d+)", g)]
            b.vrai(f"B : {dessin} : …page au bon format (A4 portrait)", abs(w / h - 210 / 297) < .01, f"{w}x{h}")
        # pixels des deux pages
        recto, verso = [base64.b64encode(x[2]).decode() for x in info["images"]]
        plan = page.evaluate("p => PdfParcours.planVerso(p)", p)
        n_j = sum(1 for t in plan["themes"] for l in t["lignes"] if l["etat"] == "posee" and not l["sub"] and l["vote"] == "j")
        n_b = sum(1 for t in plan["themes"] for l in t["lignes"] if l["etat"] == "posee" and not l["sub"] and l["vote"] == "b")
        px_v = page.evaluate(PIXELS_JS, [verso, {"j": JAUNE_PALE, "b": BLEU_PALE}])
        px_r = page.evaluate(PIXELS_JS, [recto, {}])
        b.vrai(f"B : {dessin} : le recto n'est pas vide (moins de 90 % de blanc)", px_r["blanc"] < .90, f"{px_r['blanc']:.2f}")
        b.vrai(f"B : {dessin} : le verso n'est pas vide", px_v["blanc"] < .97, f"{px_v['blanc']:.2f}")
        b.vrai(f"B : {dessin} : verso : fonds jaunes pour {n_j} posées jaunes", n_j == 0 or px_v["j"] >= n_j * 12000, f"{px_v['j']} px pour {n_j}")
        b.vrai(f"B : {dessin} : verso : fonds bleus pour {n_b} posées bleues", n_b == 0 or px_v["b"] >= n_b * 12000, f"{px_v['b']} px pour {n_b}")
        # mutant de contenu : un parcours qui n'a posé que la première question
        p2 = json.loads(json.dumps(p)); p2["path"] = p["path"][:1]; p2["subs"] = []
        plan2 = page.evaluate("p => PdfParcours.planVerso(p)", p2)
        b.vrai(f"B : {dessin} : (témoin) un parcours raccourci change le plan", [l["etat"] for t in plan2["themes"] for l in t["lignes"]] != [l["etat"] for t in plan["themes"] for l in t["lignes"]])
    b.vrai("B : aucune erreur de page", not page.erreurs, str(page.erreurs))
    page.context.close()

    # le bouton PDF de la liste : fichier téléchargé, nom, contenu
    page = ouvrir(nav, "1280x720")
    p = parcours_type(page, "olivier", 40, nom="Lorient", fin="2026-10-05T10:30:00.000Z", debut="2026-10-05T10:00:00.000Z") if False else parcours_type(page, "olivier", 40)
    p["nom"] = "Lorient"; p["fin"] = "2026-10-05T10:30:00.000Z"; p["debut"] = "2026-10-05T10:00:00.000Z"
    page.evaluate("""([p]) => { localStorage.setItem('arbre-a-questions:brouillon:a1', JSON.stringify({modifie: '2026-10-02T09:00:00.000Z',
        donnees: Editeur.nettoyer({id: 'a1', titre: p.copie.titre, dessin: 'olivier', questions: {I1: 'x'}})})); Bibliotheque.fusionner('a1', [p]); }""", [p])
    page.reload(); page.wait_for_timeout(500)
    b.att("B : le bouton PDF de la session est visible sans rien déplier", 1, page.locator("li[data-id=a1] [data-act=pdf]:visible").count())
    with page.expect_download(timeout=60000) as dl:
        page.click("li[data-id=a1] [data-act=pdf]")
    nom = dl.value.suggested_filename; f = TMP / "b_bouton.pdf"; dl.value.save_as(str(f)); page.wait_for_timeout(300)
    b.att("B : nom du fichier PDF", "arbre-a-questions-conference-d-essai-lorient-2026-10-05.pdf", nom)
    e, info = lire_pdf(f.read_bytes())
    b.att("B : le PDF du bouton est un PDF valide de 2 pages", ([], 2), (e, info.get("pages")))
    b.vrai("B : message « PDF téléchargé »", "PDF téléchargé" in page.inner_text("#mes-arbres-etat"), page.inner_text("#mes-arbres-etat"))
    b.att("B : la scène vivante n'a pas été touchée par la fabrication (svg vide, aucun doublon d'identifiant)", 0, page.evaluate("document.querySelectorAll('[id^=arc]').length"))
    b.vrai("B : aucune erreur de page", not page.erreurs, str(page.erreurs))
    page.context.close()

    # le recto ressemble au tableau final de l'appli (même parcours, même dessin)
    page = C.nouvelle_page(nav, "1280x720", init_script="")
    page.goto(FICHIER.as_uri()); page.wait_for_timeout(500)
    page.click("#btn-modifier"); page.fill("#f-titre", "Comparaison"); page.fill("#f-theme-0", "Premier"); page.fill("#f-theme-1", "Deuxième"); page.fill("#f-theme-2", "Troisième")
    page.click("#btn-retour-prepa"); C.lancer_scene(page)
    from _mes_arbres import jouer
    jouer(page); page.wait_for_timeout(1500)
    zones = page.evaluate("""() => { const r = document.getElementById('svg').getBoundingClientRect();
        return [...document.querySelectorAll('#svg text')].filter(t => /Caveat/.test(t.getAttribute('font-family') || '') && t.textContent.trim()).map(t => { const b = t.getBoundingClientRect();
            return {x: b.left - r.left, y: b.top - r.top, w: b.width, h: b.height}; }).filter(z => z.w > 20 && z.h > 8); }""")
    ecran = page.locator("#svg").screenshot()
    conf = page.evaluate("Bibliotheque.parcoursDe(ARBRE.id)")[0]
    octets = base64.b64decode(page.evaluate(PDF_JS, conf))
    _, info = lire_pdf(octets)
    rect = page.evaluate("PdfParcours._dernierRecto.arbre")
    recto = base64.b64encode(info["images"][0][2]).decode()
    d = page.evaluate(COMPARE_JS, [recto, rect, base64.b64encode(ecran).decode()])
    (TMP / "b_ecran.png").write_bytes(ecran)
    (TMP / "b_comparaison.png").write_bytes(base64.b64decode(d.pop("tri").split(",")[1]))      # recto | écran | écart (en gris foncé là où ils diffèrent)
    # témoin : le MÊME recto comparé à l'écran d'un AUTRE parcours doit s'en éloigner nettement
    jouer_autre = lambda: (touche(page, "ArrowLeft"), touche(page, "ArrowLeft"), touche(page, "ArrowLeft"), touche(page, "ArrowRight"))
    page.keyboard.press("Shift+R"); page.wait_for_timeout(100)
    for _ in range(4): page.keyboard.press("ArrowRight")
    for c in ["ArrowDown"] * 8:
        page.keyboard.press(c); page.keyboard.press("ArrowRight")
    page.wait_for_timeout(1500)
    autre = page.locator("#svg").screenshot()
    d_autre = page.evaluate(COMPARE_JS, [recto, rect, base64.b64encode(autre).decode()]); d_autre.pop("tri", None)
    print(f"   (mesure) recto/écran du même parcours : écart moyen {d['moyenne']:.2f}, pixels très différents {d['forts']*100:.2f} % ; autre parcours : {d_autre['moyenne']:.2f} / {d_autre['forts']*100:.2f} %")
    ecarts_textes = page.evaluate(TEXTES_JS, [recto, rect, base64.b64encode(ecran).decode(), zones])
    print(f"   (mesure) noms de thèmes, écart moyen par zone : {[round(x, 1) for x in ecarts_textes]}")
    b.vrai("B : on a trouvé les noms de thèmes à comparer (3 pour l'olivier)", len(zones) == 3, str(zones))
    # mesuré : bien écrits = 5,9 et 8,3 (le nom écrit en biais, à droite, a une boîte pleine de feuillage : 33,7 même quand tout est correct) ; police absente = 26,1 et 25,8
    b.vrai("B : au moins deux noms de thèmes du recto sont écrits dans la même police que sur l'écran (les deux meilleurs écarts < 15)", sorted(ecarts_textes)[1] < 15, str(ecarts_textes))
    # seuils posés d'après la mesure (même parcours : 1,06 et 0,00 % ; autre parcours : 3,53 et 0,83 %), avec de la marge de chaque côté
    b.vrai("B : le recto ressemble à l'écran du même parcours (écart moyen < 2, moins de 0,2 % de pixels très différents)", d["moyenne"] < 2 and d["forts"] < .002, str(d))
    b.vrai("B : …et s'éloigne nettement de l'écran d'un autre parcours (témoin : écart moyen > 2,5 et plus de 0,4 %)", d_autre["moyenne"] > 2.5 and d_autre["forts"] > .004, f"{d} / {d_autre}")
    b.vrai("B : aucune erreur de page", not page.erreurs, str(page.erreurs))
    page.context.close()


# ====================================================================== C
# pire cas RÉALISTE : le maximum de caractères, en majuscules, avec des mots ordinaires (2 à 13 lettres)
LONG_MAJ = ("POURQUOI NOTRE SOCIÉTÉ ACCEPTE-T-ELLE ENCORE CETTE INJUSTICE ENVIRONNEMENTALE QUAND CHACUN CONNAÎT DÉJÀ LEURS CONSÉQUENCES POUR NOS ENFANTS ?" * 2)[:120]
LONG_TRONC = ("EN QUELQUES MOTS, QU'EST-CE QUI VOUS A AMENÉS ICI CE SOIR, ET QU'ATTENDEZ-VOUS DE CETTE RENCONTRE AVEC UN SCIENTIFIQUE, UNE CHANTEUSE ET DES VOISINS ?" * 2)[:160]
# cas extrême à part : des mots de plus de 20 lettres que rien ne permet de couper autrement que par lettres
GEANTS = ("ÉLECTROMAGNÉTIQUEMENT INCONSTITUTIONNELLEMENT " * 4)[:120]
def touche(page, k, t=40): page.keyboard.press(k); page.wait_for_timeout(t)


def section_C(nav, b):
    page = ouvrir(nav, "1280x720")
    for dessin in ("olivier", "chene"):
        toutes = page.evaluate(TOUTES_JS, dessin)
        for langue, nbsub in (("fr", 3), ("de", 3), ("nl", 0)):
            page.evaluate("l => { const s = document.getElementById('langue'); s.value = l; s.dispatchEvent(new Event('change')); }", langue)
            p = parcours_type(page, dessin, 33, subs=nbsub)
            p["copie"]["titre"] = ("TITRE DE CONFÉRENCE TRÈS LONG " * 4)[:80]
            p["copie"]["tronc"] = [LONG_TRONC] * 4
            p["copie"]["questions"] = {i: LONG_MAJ for i in toutes}
            p["copie"]["themes"] = [{"id": t["id"], "nom": ("MAJUSCULES LONGUES " * 3)[:mx]} for t, mx in zip(p["copie"]["themes"], page.evaluate(f"DESSINS.{dessin}.themes.map(t => t.max)"))]
            nom = f"C : {dessin} en {langue}, pire cas"
            m = page.evaluate("p => PdfParcours.mesurerVerso(p)", p)
            b.vrai(f"{nom} : tout le verso tient dans la page", m["ok"] and m["basMm"] <= 283, str(m))
            b.vrai(f"{nom} : …à une taille lisible (7 pt au moins)", m["taille"] >= 7, str(m))
            page.evaluate("PdfParcours._tracer([])")
            octets = base64.b64decode(page.evaluate("async p => { await PdfParcours.fabriquer(p); return 'x'; }", p).encode() or b"") if False else None
            boites = page.evaluate("async p => { const t = []; PdfParcours._tracer(t); await PdfParcours.fabriquer(p); PdfParcours._tracer(null); return t; }", p)
            dehors = [x for x in boites if x["x"] < 11.5 or x["x"] + x["w"] > 198.5 or x["y"] < 11 or x["y"] + x["h"] > 294]
            b.att(f"{nom} : aucun texte ne sort de la page", [], [(x["page"], x["texte"][:30], round(x["x"]), round(x["y"]), round(x["w"])) for x in dehors][:5])
            b.vrai(f"{nom} : les deux pages portent du texte", {1, 2} <= {x["page"] for x in boites})
            titre_lignes = [x for x in boites if x["page"] == 1 and x["y"] < 40 and x["h"] > 6]
            b.vrai(f"{nom} : le titre du recto tient sur 2 lignes au plus", len([x for x in boites if x["page"] == 1 and 10 < x["y"] < 30 and x["h"] > 7]) <= 3, str([(x['texte'][:20], round(x['y'])) for x in boites if x['page'] == 1 and x['y'] < 40]))
            octets = base64.b64decode(page.evaluate(PDF_JS, p)); e, info = lire_pdf(octets)
            b.att(f"{nom} : PDF valide de 2 pages", ([], 2), (e, info.get("pages")))
    # cas extrême : mots géants. Le texte ne doit jamais SORTIR de la page en largeur et le PDF doit rester valide ; qu'il tienne en hauteur n'est pas exigé.
    for dessin in ("olivier", "chene"):
        toutes = page.evaluate(TOUTES_JS, dessin)
        p = parcours_type(page, dessin, 33, subs=3)
        p["copie"]["questions"] = {i: GEANTS for i in toutes}
        boites = page.evaluate("async p => { const t = []; PdfParcours._tracer(t); await PdfParcours.fabriquer(p); PdfParcours._tracer(null); return t; }", p)
        larg = [x for x in boites if x["x"] < 11.5 or x["x"] + x["w"] > 198.5]
        b.att(f"C : {dessin}, mots géants : aucun texte ne sort de la page en largeur", [], [(x["page"], x["texte"][:20], round(x["x"]), round(x["w"])) for x in larg][:5])
        octets = base64.b64decode(page.evaluate(PDF_JS, p)); e, info = lire_pdf(octets)
        b.att(f"C : {dessin}, mots géants : PDF valide de 2 pages", ([], 2), (e, info.get("pages")))
    b.vrai("C : aucune erreur de page", not page.erreurs, str(page.erreurs))
    page.context.close()


SECTIONS = {"A": section_A, "B": section_B, "C": section_C}

if __name__ == "__main__":
    choix = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    b = Bilan()
    with sync_playwright() as p:
        nav = C.lancer(p)
        for s in choix:
            SECTIONS[s](nav, b)
        nav.close()
    sys.exit(0 if C.bilan("PDF : " + ", ".join(choix), b.echecs) else 1)
