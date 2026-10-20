/* Arbre FACTICE pour les tests : 4 thèmes, 10 questions, aucun vrai dessin. Il prouve que l'application sait accueillir un arbre qui n'a pas
   3 thèmes (le vrai chêne, avec son écureuil, viendra de Joanna). Il n'est inséré que dans des copies de test, jamais dans index.html. */
(function(){
DESSINS.chene_test={
 id:'chene_test', nom:'Chêne (arbre de test)', description:"4 thèmes · avec l'écureuil",
 themes:[
  {id:'W',couleur:'#a6c46c',position:'haut gauche',libelle:'Thème en haut à gauche',aide:'Aide W (24 lettres au maximum).',max:24,exemple:'Ex. : Premier'},
  {id:'X',couleur:'#9fcbd0',position:'haut droite',libelle:'Thème en haut à droite',aide:'Aide X (24 lettres au maximum).',max:24,exemple:'Ex. : Deuxième'},
  {id:'Y',couleur:'#f0b294',position:'bas gauche',libelle:'Thème en bas à gauche',aide:'Aide Y (20 lettres au maximum).',max:20,exemple:'Ex. : Troisième'},
  {id:'Z',couleur:'#f3c763',position:'bas droite',libelle:'Thème en bas à droite',aide:'Aide Z (20 lettres au maximum).',max:20,exemple:'Ex. : Quatrième'}],
 depart:['W1','Z1'],
 structure:[
  {"id":"W1","step":1,"theme":"W","color":"b","stay":"W2","change":"X2"},
  {"id":"Z1","step":1,"theme":"Z","color":"j","stay":"Z2","change":"Y2"},
  {"id":"W2","step":2,"theme":"W","color":"j","stay":"W3","change":"X3"},
  {"id":"X2","step":2,"theme":"X","color":"b","stay":"X3","change":"W3"},
  {"id":"Y2","step":2,"theme":"Y","color":"j","stay":"Y3","change":"Z3"},
  {"id":"Z2","step":2,"theme":"Z","color":"b","stay":"Z3","change":"Y3"},
  {"id":"W3","step":3,"theme":"W","color":"b"},
  {"id":"X3","step":3,"theme":"X","color":"j"},
  {"id":"Y3","step":3,"theme":"Y","color":"b"},
  {"id":"Z3","step":3,"theme":"Z","color":"j"}],
 construire(ctx){
  ctx.svg.innerHTML='<image href="data:," x="0" y="0" width="1" height="1"/>';
  window.__factice={noms:ctx.themes.map(t=>t.nom),etats:[]};
  return {afficher(e){window.__factice.etats.push(e.mode+':'+e.path.join('>'));},reset(){window.__factice.etats.push('reset');}};
 }
};
})();
