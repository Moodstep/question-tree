# L'Arbre à questions : documentation technique

> Pour découvrir l'outil et s'en servir, voir le [README](../README.md) et le [guide d'utilisation](guide/GUIDE.md). Cette page s'adresse à qui veut comprendre le fichier, ajouter un arbre ou une langue, ou lancer les tests.

Un outil pour animer une conférence-interview : la salle choisit, à chaque étape, entre une question
**jaune** et une question **bleue**, et son parcours dessine un chemin dans un arbre.

Tout tient dans **un seul fichier HTML** (`index.html`) : polices comprises, aucune connexion à Internet,
aucun traçage. Il suffit de l'ouvrir dans un navigateur (testé dans Chrome).

## Utiliser

1. Ouvrir `index.html`.
2. **Entrer mes questions et thèmes** : choisir l'arbre (sur l'écran de préparation), puis saisir le titre, les noms de thèmes, les 4 questions du tronc
   et les questions de la ramure : 3 thèmes et 23 questions pour l'olivier, 4 thèmes et 26 questions pour le chêne.
3. **Télécharger mon arbre** : produit un nouveau fichier `arbre-a-questions-[titre].html`, autonome, qui peut être rouvert et modifié.
   Le téléchargement est la vraie sauvegarde ; le brouillon automatique ne vit que dans le navigateur.
4. **Lancer l'arbre** : plein écran avec `F`. Commandes : `→` / `Espace` suivant, `←` retour, `↑` / `↓` ou `J` / `B` choisir
   la jaune ou la bleue, `Maj+R` tout recommencer, `E` (ou `Échap` deux fois) retour à la préparation.
   Trois petits ronds discrets, en haut de l'écran : celui de droite recommence, celui de gauche ramène au choix de l'arbre
   (avec la même confirmation que `E`), celui du milieu tire une question subsidiaire (touche `=` ou `+`, voir ci-dessous).
5. **Mode d'emploi** : un écran de lecture dans l'outil, en 7 langues, ouvert depuis l'accueil (lien en bas) ou la barre de l'éditeur, jamais depuis la scène ; `← Retour` ou `Échap` ramène au même endroit.

## Les questions subsidiaires

Une question de plus, facultative, quand il reste du temps. Elle se tire **à n'importe quel moment** du parcours (modifié le 12/10/2026 : au départ, uniquement à la fin).

- **Quand** : dès la première réponse du parcours, et jusqu'au tableau final (y compris sur le tableau final). Pas pendant le tronc ni avant la première réponse : à ce moment-là, n'importe quelle question peut encore être proposée par un vote, donc aucune n'est sûre (le rond n'apparaît pas et la touche ne fait rien).
- **Comment** : la touche `=` ou la touche `+` (sur un clavier AZERTY de Mac, `+` est `Maj` + `=`), ou un clic sur le petit rond du milieu, en haut. Le rond n'est visible que quand il y a une question à tirer ; il est caché en mode télécommande.
- **Le tirage** : une question au hasard parmi celles qui n'ont **jamais** été affichées ce soir-là **et qui ne pourront plus l'être dans la suite du parcours** : sont exclues les deux questions de départ, celles du parcours, celles proposées à un vote puis refusées, toutes celles qu'un vote à venir pourrait encore proposer, et les subsidiaires déjà tirées. Le calcul se fait sur la table des votes de l'arbre choisi : aucun chiffre n'est écrit en dur. Plus on avance, plus il en reste : en fin de parcours, 7 pour l'olivier (23 moins 2 fois 8 votes) et 12 pour le chêne (26 moins 2 fois 7 votes). Quand il n'en reste plus, le rond disparaît et la touche ne fait plus rien.
- **Revenir** : `←` depuis une subsidiaire revient à la subsidiaire précédente, puis **exactement là où on s'était arrêté** dans le parcours (la même carte, la même mascotte, les mêmes fruits allumés). Appuyer de nouveau sur `=` **rejoue** la subsidiaire qu'on vient de quitter (pour rattraper une fausse manœuvre), puis tire une nouvelle question.
- **Continuer** : `Entrée` (ou `→`, `Espace`, `PageDown`, le bouton `→`) reprend le parcours là où il en était et avance d'un cran. À la dernière question, il va au tableau final, **exactement celui d'avant** : le parcours seul, sans les subsidiaires ; `←` y ramène alors à la dernière subsidiaire. Pendant un vote, `→` ramène au vote (il faut choisir).
- **Si on recule dans le parcours** : les subsidiaires tirées plus loin que l'endroit où l'on revient sont oubliées (le parcours peut repartir autrement et les reproposer). Elles peuvent donc être tirées de nouveau. Une subsidiaire n'est jamais à la fois dans la liste des subsidiaires et dans les questions du parcours.
- **La carte** : la même grande carte que pour une question du parcours (nom du thème et question, rien d'autre), mais son fond prend la couleur du **thème** de la question : la nuance la plus claire de son feuillage, écrite dans le champ `couleur` de chaque thème de la fiche de l'arbre. Le texte est foncé ou blanc, au plus contrasté (rapport WCAG d'au moins 4,5:1, mesuré par les tests).
- **Dans l'arbre** : le fruit de la question tirée (olive ou gland) s'allume comme le fruit en cours, sans qu'aucun lien soit tracé vers lui ; un seul fruit subsidiaire est allumé à la fois ; le parcours reste affiché (pendant un vote, les deux fruits proposés restent allumés). La mascotte se pose **à côté** du fruit, de profil et tournée vers lui, sans cacher aucun fruit.
  **Exception** : l'écureuil est « toujours assis sur un lien » (voir `tests/test_ecureuil.py`), mais ici aucun lien n'arrive au gland tiré : il s'assoit donc à côté du gland, comme la mésange à côté de l'olive.
- **Recommencer** : `Maj+R` et le rond de droite recommencent tout, subsidiaires comprises.
- **Pour les tests** : le tirage appelle `window.__hasard()` s'il existe (sinon `Math.random()`), ce qui rend les tirages reproductibles. `tests/test_sous_questions.py` vérifie tout cela, dont un parcours de 4 000 gestes au hasard par arbre.

## Mes arbres, les sessions et le PDF

L'accueil, c'est **construire un arbre** : on choisit l'olivier ou le chêne, puis « Entrer mes questions et thèmes » ou « Lancer l'arbre ». **Sous** ces boutons, la section **Mes arbres** garde ce que tu as déjà construit.

- **Une session** = un parcours joué jusqu'au tableau final (conférence, atelier, jeu entre amis : l'outil n'impose pas le contexte). Le mot « conférence » n'apparaît plus dans l'outil.
- **Chaque arbre de la liste a ses propres boutons** : **Lancer** (la scène s'ouvre tout de suite avec cet arbre, sans repasser par le haut de la page) et **Modifier** (l'éditeur s'ouvre sur cet arbre). Plus discrets : **Sauvegarder (fichier)** et **Retirer de la liste** (confirmation ; le fichier déjà sauvegardé sur l'ordinateur n'est jamais touché).
- **Les sessions sont toujours visibles** sous leur arbre (les 3 plus récentes ; les autres dans un volet « Voir les n autres sessions »), chacune avec son bouton **Télécharger le PDF**, un champ pour la nommer (« Lyon, 12 mars ») et **Supprimer** (confirmation).
- **À quoi sert « Sauvegarder (fichier) » ?** Il fabrique **un seul fichier `.html` qui contient l'outil, ton arbre, tes questions et tes sessions**. Trois usages : une copie de sécurité sur le disque (la liste « Mes arbres » vit dans la mémoire du navigateur, qui peut être vidée), jouer d'un double-clic sans passer par l'appli, ou envoyer l'arbre à quelqu'un. Ce n'est pas le PDF, qui n'est que l'impression d'une session. Une ligne d'aide le dit sous le titre « Mes arbres ». La mention « pas encore sauvegardé » indique qu'un arbre a changé depuis son dernier fichier ; elle ne peut pas savoir qu'un fichier a été fabriqué avant l'arrivée de cette fonction.
- **Quand on quitte la scène** (touche `E`) après une session complète, un bandeau apparaît en haut de l'accueil : « Session enregistrée : … » avec **Télécharger le PDF**. Rien ne s'affiche pendant la scène, que la salle ou le groupe regarde.
- **Ouvrir un arbre** (bouton à droite du titre « Mes arbres »). Il recharge un fichier produit par « Sauvegarder (fichier) » et **arrive directement dans l'éditeur** : les questions sont là, « Lancer l'arbre » est en haut. Un fichier est traité comme une donnée non fiable : taille bornée (8 Mo), format vérifié, dessin connu,
  textes bornés, chaque session relue une par une (les abîmées sont ignorées et comptées dans le message). Si l'arbre est déjà dans la liste avec un contenu différent, une boîte propose
  de garder la version de la liste ou de prendre celle du fichier (Échap annule tout) ; les sessions des deux côtés sont toujours réunies.
  **Le fichier de la toute première version (avant l'éditeur) ne peut pas être rouvert ainsi** : c'est l'ancien format, ses questions sont écrites dans le code et non dans des données. Il reste intact.
- **Les sessions gardées.** Chaque fois que tu arrives au **tableau final**, le parcours est gardé automatiquement : les choix du groupe, les questions subsidiaires tirées, la date. Revenir en arrière
  (`←`) puis finir autrement met à jour **la même** session ; `Maj+R` (ou le rond de droite) en commence une autre ; un parcours abandonné avant le tableau final n'est pas gardé.
  Chaque session garde **une copie des textes de ce moment-là** : modifier une question ensuite ne change pas le PDF d'une session passée.
- **Dans le fichier sauvegardé.** Les sessions voyagent dans le bloc `donnees-arbre` (champ facultatif `parcours`, `format` toujours 1). Un arbre sans session donne exactement le même fichier qu'avant.
  Ouvert directement dans un navigateur, un fichier verse ses sessions dans la mémoire de ce navigateur.
- **Le PDF.** Un PDF de **2 pages A4 portrait** (recto-verso, reliure sur le grand côté) :
  *recto* = le titre, la date et l'arbre tel qu'il apparaît au tableau final, chemin allumé ; *verso* = les 4 questions du tronc (numérotées 1 à 4), puis une colonne par thème avec toutes les questions.
  Trois états, lisibles aussi en noir et blanc : **posée** (numéro d'ordre dans un rond jaune ou bleu, texte en gras, fond teinté), **proposée au groupe mais non choisie** (petit rond vide), **pas apparue** (gris clair) ;
  les subsidiaires portent un repère S1, S2… La taille du texte est cherchée de 11 à 7 pt pour que tout tienne (pire cas mesuré : 8,25 pt pour l'olivier, 7,25 pt pour le chêne, avec toutes les questions
  à 120 caractères en majuscules et trois subsidiaires). Les pages sont dessinées avec les polices de l'appli puis assemblées en PDF sans bibliothèque externe : **le texte du PDF n'est pas sélectionnable**
  (choix assumé). Il n'y a **aucun bouton PDF sur le tableau final** : cet écran est projeté.

### Où vit la mémoire

Trois clés dans la mémoire du navigateur, **jamais renommées** : `arbre-a-questions:brouillon:<id>` (la dernière version de l'arbre, c'est elle qui fait exister l'entrée dans la liste),
`arbre-a-questions:parcours:<id>` (ses sessions), `arbre-a-questions:telecharge:<id>` (date du dernier fichier téléchargé). Tout est lu et écrit dans un `try/catch` : si la mémoire est
indisponible ou pleine, l'appli continue, les sessions restent visibles jusqu'à la fermeture de la page et la liste le dit (« télécharge son PDF maintenant »).
La liste vit dans le navigateur où tu travailles et n'est envoyée nulle part. **Constaté dans Firefox le 07/10/2026** : la liste garde ses arbres d'un jour à l'autre quand `index.html` est ouvert. Non vérifié : un arbre sauvegardé puis ouvert depuis un *autre* emplacement du disque (Firefox peut cloisonner la mémoire fichier par fichier). Le fichier téléchargé sur le disque reste, lui, la vraie sauvegarde.

**Différé, annoncé :** importer le fichier de la toute première version dans le nouvel outil ; garder un parcours interrompu ; un PDF « toutes les sessions d'un arbre » ; l'exemple de titre de l'éditeur (« Ex. : Conférence du 12 mars ») dit encore « conférence » ; un texte de PDF sélectionnable ; lire un dossier du disque
(possible dans Chrome seulement). Les nouveaux textes des 7 langues sont une proposition de l'assistant, à faire relire par un locuteur natif de chaque langue.

## Langues

L'outil existe en **7 langues** : français (langue de référence), anglais, espagnol, allemand, italien, portugais (du Portugal) et néerlandais.

- **Choix** : l'outil s'ouvre dans la langue du navigateur (français si elle n'est pas disponible). Un petit **sélecteur en haut à droite de l'écran
  de préparation** permet de la changer ; le choix est mémorisé dans ce navigateur (nouvelle clé `arbre-a-questions:langue`, les brouillons gardent la leur).
  Tout l'éditeur (libellés, aides, exemples, messages, fenêtres) suit la langue choisie.
- **Ce qui n'est jamais traduit** : ce que le conférencier écrit (titre, noms de thèmes, questions), la mention « CC BY-SA MOODSTEP » gravée dans le tronc,
  les dessins, les adresses. Une question laissée vide s'affiche « Question I3 » dans la langue choisie.
- **Fichier téléchargé** : il embarque la langue choisie (`<html lang="pt" data-langue="pt">`) et le sélecteur ; rouvert, il parle cette langue, sauf si
  l'utilisateur a choisi explicitement une autre langue dans ce navigateur. Ordre de priorité : choix fait dans ce navigateur, puis langue du fichier,
  puis langue du navigateur, puis français.
- **Touches** : `J`/`B` (jaune/bleue) et les flèches ne changent pas d'une langue à l'autre. Seule la lettre du « oui » de la fenêtre « Revenir à la préparation ? »
  suit la langue (`O` en français, `Y` en anglais, `S` en espagnol, italien et portugais, `J` en allemand et néerlandais) ; `N` partout pour « non ».
- **Ajouter une langue** : une ligne dans `LANGUES_DISPONIBLES` et un bloc dans `TEXTES` (bloc `i18n`) avec **exactement les mêmes clés** que le français ;
  `tests/test_langues.py` refuse toute clé manquante, vide ou dont les `{paramètres}` diffèrent. Les écritures de droite à gauche (arabe, hébreu) ne sont **pas** gérées.

> ⚠️ **Toutes les traductions sont une proposition de l'assistant : elles sont à faire relire par un locuteur natif de chaque langue.** Aucune n'a été validée.
> Points précis à faire trancher : le titre traduit de l'outil (« The Question Tree », « Der Fragenbaum »… — le nom de marque « L'Arbre à questions »
> n'est conservé qu'en français), le portugais du Portugal (« tu », « ficheiro », « descarregar ») plutôt que du Brésil, et les exemples de thèmes de l'éditeur.

## Comment le fichier est rangé

| Bloc (`<script id=…>`) | Rôle |
|---|---|
| `donnees-arbre` (JSON) | Tout ce que le conférencier saisit : titre, liste de thèmes, tronc, questions. |
| `i18n` | **Les langues** : le tableau `TEXTES` (une entrée par langue, mêmes clés que le français), `tx()` (texte d'une clé, repli sur le français), `ft()` (textes de la fiche d'un arbre), choix de la langue au démarrage. |
| `registre-dessins` | Le registre `DESSINS` et le contrat d'un arbre. |
| `dessin-olivier` | **L'olivier, avec sa mésange** : sa fiche (3 thèmes, longueurs des noms), sa table des votes (23 questions, 8 votes), son dessin (tronc creusé de 4 loges, feuillage, fleurs, mention de licence, liens, olives) et la mésange. |
| `dessin-chene` | **Le chêne, avec son écureuil** : sa fiche (4 thèmes A à D, longueurs des noms 18 / 22 / 22 / 18), sa table des votes (26 questions A1 à D7, 7 votes, 128 parcours), son dessin (tronc creusé de 4 loges, houppier en éventail, glands, liens en lacets, mention de licence) et l'écureuil. |
| `vignettes-arbres` (JSON) | La petite image de chaque arbre, affichée sur l'écran de préparation. |
| `mecanique` | La table des votes (rester / changer de thème, jaune / bleu) et la logique de la scène, dont les questions subsidiaires (mode `sub`, tirage, touche `=`). |
| `ecrans` | Préparation, lancement, retour, aperçu. |
| `editeur-js` | Éditeur, brouillon automatique, téléchargement (de l'arbre courant ou d'un arbre de la liste), chargement d'un arbre. |
| `bibliotheque-js` | Mes arbres : mémoire du navigateur (arbres, sessions), vérification des conférences venues d'un fichier, enregistrement au tableau final, liste, ouverture d'un fichier. |
| `pdf-js` | Le PDF d'une session : plan du verso (fonction pure `planVerso`), dessin des deux pages, écrivain de PDF, téléchargement. |

**Il y a deux arbres, et deux seulement** : l'olivier (3 thèmes, 8 votes, avec la mésange) et le chêne (4 thèmes, 7 votes, avec l'écureuil). L'écran de préparation n'affiche que leur nom et leur nombre de thèmes.
L'utilisateur choisit un arbre sur l'écran de préparation ; le nombre de thèmes en découle. Le choix est verrouillé dès qu'un champ est
rempli (pour en changer : repartir d'un fichier vierge). Chaque arbre est un module complet et fermé : sa fiche, sa table des votes, ses
positions de questions (calculées pour SES thèmes), son dessin et son animal. L'éditeur, la mécanique et les écrans lisent la fiche de
l'arbre choisi et n'écrivent aucun nombre propre à un arbre (le nombre de votes, par exemple, est lu dans la table).

Les questions du chêne s'appellent **A1 à D7** : une lettre par thème (A pour le thème 1, D pour le thème 4), puis le niveau (1 à 7). Il n'y a pas de B1 ni de C1,
car le premier vote oppose A1 à D1. Les 4 questions du tronc s'appellent T1 à T4 pour les deux arbres.

**Ajouter un arbre** : ajouter un `<script id="dessin-…">` qui définit `DESSINS.<id>` (contrat dans `registre-dessins`) : sa fiche (thèmes, aides,
longueurs maximales des noms selon ses arcs), sa table des votes, ses deux questions de départ, son dessin et son animal ; `construire(ctx)`
rend `{afficher(etat), reset()}`. Puis ajouter son identifiant à la liste de `tests/fabriquer_vignette.py` et lancer
`.venv/bin/python tests/fabriquer_vignette.py écrire`. Rien d'autre à toucher.

Pour les noms de thèmes, l'écriture suit un arc : si le nom est trop long pour son arc, elle rétrécit au lieu d'être coupée. Les longueurs
maximales de la fiche sont choisies pour qu'un nom réaliste à sa longueur maximale reste lisible (voir « Limites de longueur »).

## Tester

Les tests pilotent Chrome avec Playwright, réseau coupé.

```bash
python3 -m venv .venv && .venv/bin/pip install playwright
.venv/bin/python tests/tout_lancer.py
```

Ce que la batterie vérifie, en bref :

- **Questions subsidiaires** (`tests/test_sous_questions.py`) : par le calcul, sur les 256 + 128 parcours, aucune question tirable n'a déjà été affichée ; carte, contraste (≥ 4,5:1), mascotte qui ne cache aucun fruit (boîtes mesurées), fruit allumé sans lien, retour avec `←`, épuisement du tirage, clic = touche, `Maj+R`, fichier téléchargé rouvert ; le tableau final est identique, pixel pour pixel, à celui d'avant les questions subsidiaires.
- **Olivier** : son dessin est **identique, pixel pour pixel, au fichier de référence du nouveau design** (`reference/nouveau-design.html`, jamais
  modifié ; il charge Google Fonts : c'est une démo, pas l'application ; le dossier `reference/` reste sur le poste de travail et n'est pas publié) ; les 256 parcours possibles ne répètent aucune question et sont les
  mêmes que dans le fichier de la toute première version ; la mésange passe d'une loge à l'autre sans jamais apparaître sur l'écorce.
- **Chêne** : son dessin est identique, pixel pour pixel, à `reference/chene-brouillon.html` (brouillon de travail, jamais modifié ; démo qui charge
  Google Fonts) dans 9 états et 3 tailles d'écran ; sa structure est recomptée par le calcul sur la table réellement chargée (26 questions,
  128 parcours, 224 visites par thème, 16 sauts vers un thème voisin et 6 à deux thèmes de distance) ; le placement des glands et des
  liens est recalculé sur le dessin produit (aucun gland hors de sa couleur, 22 croisements, aucun lien à moins de 31 d'un gland) ;
  l'écureuil est comparé à la référence (parcours au clavier, retour, trois passages du tronc image par image, remise à zéro). Il est
  **toujours assis sur un lien** (mesuré sur les 380 états possibles) et, pendant un vote, ne se pose pas sur un lien qui part vers l'une des deux
  questions proposées, sauf au vote qui suit le tout premier gland (A1 ou D1) : aucun lien n'y arrive, il s'assoit alors sur l'un des deux liens de départ.
  Cette place est la seule différence voulue avec le brouillon de référence.
- **Langues** (`tests/test_langues.py`, `tests/test_langues_debordement.py`) : les 7 langues ont exactement les mêmes clés, aucune valeur vide, les mêmes
  paramètres, et toute clé utilisée dans le code existe ; une clé manquante retombe sur le français ; aucun texte français ne reste visible dans une autre
  langue (10 écrans x 6 langues) ; le fichier téléchargé embarque la langue ; le dessin des deux arbres est identique, SVG et pixels, dans les 7 langues ;
  aucun débordement (7 langues x 3 tailles x 10 écrans). Chacun de ces contrôles est mis à l'épreuve par une copie volontairement abîmée ou un témoin.
  Les captures des écrans clés de chaque langue sont dans `tests/captures/langues/` (non suivies par git). Le Chrome de test est réglé sur `fr-FR`
  (`tests/_commun.py`), puisque l'outil choisit sa langue d'après le navigateur.
- **Mes arbres** (`tests/test_bibliotheque.py`, outils communs dans `tests/_mes_arbres.py`) : vérification des conférences (chaîne de liens, dates, bornes), fusion sans doublon, liste, pastille « à télécharger »
  (avec une horloge qui avance, pour que l'ordre de deux écritures voisines se voie), boutons Lancer et Modifier qui agissent sur la ligne cliquée, liste sous les boutons de l'accueil, cibles de 44 px, bandeau de fin de session, ouverture d'un fichier valide qui arrive dans l'éditeur, refus clairs, fichier hostile (balises, 3 000 sessions abîmées, 2 Mo de titre),
  conflit, titre piégé affiché tel quel, mémoire en panne, 7 langues. Chaque contrôle a été éprouvé par un **mutant** (copie de `index.html` volontairement abîmée, passée par `ARBRE_FICHIER=…`).
- **PDF** (`tests/test_pdf.py`) : le plan du verso sur 48 parcours des deux arbres ; le fichier lu par un analyseur écrit pour le test (en-tête, table de références, arbre des pages, 2 pages A4, 2 images,
  flux complets), relu par macOS (`sips`) ; les pixels du verso (fonds teintés) ; **le recto comparé à l'écran réel du même parcours** (après réduction, pour que la texture du feuillage ne compte pas) avec un
  témoin « autre parcours », et les noms de thèmes comparés à pleine résolution (police) ; le pire cas dans trois langues, aucun texte hors de la page.
- **Les deux** : choix de l'arbre, verrou, éditeur piloté par la fiche, téléchargement et réouverture (`tests/test_arbres.py`, qui garde aussi
  un arbre factice à 4 thèmes, `tests/arbre_factice.js`, pour attraper tout chiffre d'olivier écrit en dur), limites de longueur, polices,
  et aucune requête réseau.

## Limites de longueur

Question : 120 caractères. Tronc : 160. Noms de thèmes : **olivier** 30 / 16 / 30 (thèmes 1 / 2 / 3) ; **chêne** 18 / 22 / 22 / 18
(thèmes 1 à 4). Les thèmes sont numérotés, jamais « gauche » ni « droite ». Elles ont été mesurées sur 6 tailles d'écran (`tests/test_limites.py`), dans les cas réalistes les plus durs :
questions en majuscules ou pleines de mots longs. Pour le chêne, le test mesure aussi, en pixels, que les noms de thèmes à leur longueur
maximale (minuscules, MAJUSCULES, lettres à queue) restent dans l'écran et dans le cadre du dessin et ne touchent jamais le feuillage.
Un nom à sa longueur maximale en MAJUSCULES s'écrit plus petit (environ la moitié de la taille normale) : c'est le prix de la règle « on
rétrécit, on ne coupe jamais ».

## Crédit

L'Arbre à questions, conçu par [Moodstep](https://www.moodstep.com/) · arbre@moodstep.com.

## Licence

[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr) (Creative Commons Attribution, Partage dans les mêmes conditions).
La mention « CC BY-SA MOODSTEP » est gravée dans le bois du tronc : elle fait partie du dessin et se retrouve dans tout fichier
téléchargé depuis l'éditeur. Voir le fichier `LICENSE`.

Les deux polices intégrées (Caveat et Fraunces) restent sous leur propre licence, la SIL Open Font License 1.1 : voir le fichier
`LICENCE-POLICES.txt`.

**Outil fourni gratuitement, tel quel, sans garantie ni support.** Moodstep ne peut être tenu responsable de son utilisation.
