// Banc de l'extension sous Node seul : un faux module `vscode`, le vrai moteur, le dépôt et le jeu synthétiques de
// red_stack_test.py (à lancer d'abord). Joue ce que la page envoie et vérifie ce qu'elle reçoit, la confirmation
// modale avant toute écriture, l'empreinte du plan, et le traitement d'une demande déposée par le serveur MCP.
//   node test/essai.js <chemin de red_stack.py>
'use strict';
const Module = require('module');
const fs = require('fs');
const path = require('path');

const BASE = 'C:\\__DEV\\cyberpunk\\red_stack';
const [DEPOT, JEU, MAGASIN] = ['depot', 'jeu', 'magasin'].map((x) => path.join(BASE, x));
const SCRIPT = process.argv[2];
const DONNEES = path.join(BASE, 'donnees');
const recus = [], modales = [], infos = [], erreurs = [];
let reponse = undefined, versPage = null, etat = {};
const STOCK = path.join(BASE, 'stockage_extension');
const reglagesPoste = { python: 'python', moteur: SCRIPT, donnees: DONNEES };
const echecs = [];
const controle = (nom, ok, detail) => {
  console.log((ok ? '  ok   ' : '  KO   ') + nom + (ok || detail === undefined ? '' : '  ' + JSON.stringify(detail).slice(0, 400)));
  if (!ok) echecs.push(nom);
};

// La page est verrouillée pendant un geste qui écrit : le banc, comme elle, attend la fin du geste avant d'en demander un autre.
const libre = async () => { for (let i = 0; i < 400; i++) { const v = recus.filter((x) => x.t === 'verrou'); if (!v.length || !v[v.length - 1].on) return; await new Promise((r) => setTimeout(r, 50)); } };
const tousPanneaux = [];
const fauxPanneau = () => {
  const p = {
    webview: { html: '', postMessage: (m) => { recus.push(m); }, onDidReceiveMessage: (f) => { versPage = f; } },
    onDidDispose(f) { p.ferme = f; tousPanneaux.push(p); }, reveal() { etat.reveles = (etat.reveles || 0) + 1; }, dispose() { p.jete = true; },
  };
  return p;
};
const faux = {
  StatusBarAlignment: { Left: 1 }, ViewColumn: { Active: 1, Beside: -2 }, ProgressLocation: { Notification: 15 }, ConfigurationTarget: { Global: 1 },
  ThemeIcon: class { constructor(id) { this.id = id; } },
  TreeItem: class { constructor(label) { this.label = label; } }, TreeItemCollapsibleState: { None: 0 },
  EventEmitter: class { constructor() { this.event = () => ({ dispose() {} }); } fire() { etat.arbreDit = (etat.arbreDit || 0) + 1; } },
  Uri: { file: (p) => ({ fsPath: p }), parse: (u) => ({ url: u }) },
  Range: class { constructor(l) { this.l = l; } },
  CancellationTokenSource: class { constructor() { this.token = {}; } cancel() {} dispose() {} },
  window: {
    createStatusBarItem: () => ({ show() { etat.barre = true; }, hide() { etat.barre = false; }, dispose() {} }),
    createTreeView: (id, o) => { etat.arbre = o.treeDataProvider; return { onDidChangeVisibility: (f) => { etat.vue = f; }, dispose() {} }; },
    createWebviewPanel: (type) => { etat.crees = (etat.crees || 0) + 1; etat.dernier = fauxPanneau(); etat.dernier.type = type; return etat.dernier; },
    registerWebviewPanelSerializer: (type, s) => { if (type === 'redStack') etat.serialiseur = s; else if (type === 'redStackCode') etat.serialiseurCode = s; else if (type === 'redStackAide') etat.serialiseurAide = s; else if (type === 'redStackObjets') etat.serialiseurObjets = s; else if (type === 'redStackDependances') etat.serialiseurDeps = s; else etat.serialiseurAnalyse = s; return { dispose() {} }; },
    onDidChangeWindowState: (f) => { etat.fenetre = f; return { dispose() {} }; },
    registerUriHandler: (g) => { etat.adresse = g.handleUri; return { dispose() {} }; },
    showWarningMessage: async (texte, opt) => { modales.push({ texte, detail: opt.detail }); return reponse; },
    showQuickPick: async (items, opt) => {
      modales.push({ texte: opt.title, detail: opt.detail, defaut: items[0].v });
      return reponse === 'Appliquer' ? items.find((i) => i.v) : reponse === 'Entree' ? items[0] : undefined;
    },
    showInformationMessage: async (t) => { infos.push(t); },
    showErrorMessage: async (t) => { erreurs.push(t); },
    showInputBox: async () => 'essai',
    showTextDocument: async (doc, o) => { etat.montre = { chemin: doc.uri.fsPath, ligne: o.selection.l }; },
    withProgress: (o, f) => f(),
  },
  workspace: {
    fs: { delete: async (u, o) => { etat.corbeille = !!(o && o.useTrash); fs.unlinkSync(u.fsPath); } },
    workspaceFolders: [],
    openTextDocument: async (u) => ({ uri: u }),
    getConfiguration: () => ({ get: (k) => reglagesPoste[k], update: async (k, v) => { reglagesPoste[k] = v; etat.posteEcrit = k; } }),
    onDidChangeConfiguration: (f) => { etat.configChange = f; return { dispose() {} }; }, onDidChangeWorkspaceFolders: () => ({ dispose() {} }),
  },
  commands: { registerCommand: (id, f) => { etat[id] = f; return { dispose() {} }; }, executeCommand: async (id) => { (etat.commandes = etat.commandes || []).push(id); } },
  env: { language: 'fr', uriScheme: 'vscode', openExternal: async (u) => { etat.ouvert = u.url; }, clipboard: { writeText: async (t) => { etat.copie = t; } } },
};
const charge = Module._load;
Module._load = function (nom, ...r) { return nom === 'vscode' ? faux : charge.call(this, nom, ...r); };

const pause = (ms) => new Promise((r) => setTimeout(r, ms));
async function attend(t, depuis = 0, max = 30000) {
  for (let i = 0; i < max / 50; i++) {
    const m = recus.slice(depuis).find((x) => x.t === t);
    if (m) return m;
    await pause(50);
  }
  throw new Error(`message « ${t} » jamais reçu ; reçus : ${recus.slice(depuis).map((x) => x.t + (x.message ? ' ' + x.message : ''))}`);
}
const instantane = () => {
  const out = {};
  const marche = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => {
    const p = path.join(d, e.name);
    if (e.isDirectory()) marche(p); else out[p] = fs.statSync(p).size + ':' + fs.statSync(p).mtimeMs;
  });
  marche(JEU);
  return JSON.stringify(out);
};

(async () => {
  if (!SCRIPT || !fs.existsSync(path.join(DONNEES, 'profils', 't.json'))) {
    console.error('Usage : node test/essai.js <red_stack.py>, après red_stack_test.py (profil « t »).');
    process.exit(2);
  }
  // le moteur du banc ne lit pas config.json pour ses chemins : on les lui passe comme le banc Python
  const { Moteur } = require('../moteur');
  const lance = Moteur.prototype.lance;
  Moteur.prototype.lance = function (args, entree, env) { this.base = ['--depot', DEPOT, '--jeu', JEU, '--magasin', MAGASIN, '--donnees', DONNEES]; etat.envVu = env; return lance.call(this, args, entree, env); };
  process.env.RED_STACK_NEXUS_URL = 'http://127.0.0.1:9';   // Nexus injoignable : le banc ne sort jamais sur le réseau
  const coffre = new Map();
  fs.rmSync(path.join(DONNEES, 'demande.json'), { force: true });
  fs.rmSync(path.join(DONNEES, 'profils', 'essai.json'), { force: true });

  const ext = require('../extension');
  const store = new Map([['redStack.profil', 't']]);
  ext.activate({ subscriptions: [], extensionPath: path.join(__dirname, '..'), globalStorageUri: { fsPath: STOCK },
    secrets: { get: async (k) => coffre.get(k), store: async (k, v) => { coffre.set(k, v); }, delete: async (k) => { coffre.delete(k); } },
    globalState: { get: (k, d) => (store.has(k) ? store.get(k) : d), update: async (k, v) => { store.set(k, v); } },
    workspaceState: { get: (k, d) => (store.has(k) ? store.get(k) : d), update: async (k, v) => { store.set(k, v); } } });
  console.log('1. ouverture');
  controle('moteur embarqué : barre d\'état montrée, deux commandes', etat.barre === true && etat['redStack.ouvrir'] && etat['redStack.demande']);
  const rouvert = fauxPanneau();                     // VS Code redémarre avec l'onglet Red Stack resté ouvert
  await etat.serialiseur.deserializeWebviewPanel(rouvert, undefined);
  controle('onglet rouvert par VS Code : page branchée, aucun onglet créé',
    typeof versPage === 'function' && rouvert.webview.html.length > 1000 && rouvert.webview.options.enableScripts && !etat.crees);
  etat.vue({ visible: true });                       // clic sur l'icône de la barre d'activité, page déjà ouverte
  await pause(20);
  controle("icône de la barre d'activité, page ouverte : page ramenée, la barre latérale reste, aucun onglet créé",
    !(etat.commandes || []).includes('workbench.view.explorer') && etat.reveles === 1 && !etat.crees && etat.arbre.getChildren().length === 0, etat);
  rouvert.ferme();                                   // il ferme l'onglet
  versPage = null;
  etat.vue({ visible: true });
  await pause(20);
  controle("icône de la barre d'activité, page fermée : un onglet créé, page branchée", etat.crees === 1 && typeof versPage === 'function');
  const double = fauxPanneau(), branchee = versPage;
  await etat.serialiseur.deserializeWebviewPanel(double, undefined);
  controle('onglet rouvert alors que la page est déjà là : le doublon est fermé', double.jete === true && versPage === branchee);
  versPage({ t: 'pret' });
  let e = await attend('etat');
  const monde = e.data.mods.find((r) => r.cle.includes('Monde-3001'));
  controle('état : mods, piles, profils', e.data.mods.length > 8 && e.data.sections.length >= 4 && e.profils.some((p) => p.nom === 't'), e.data.sections);
  controle('ligne d\'un mod : actif, posé, fichiers posés', monde && monde.actif && monde.etat === 'posé' && monde.fichiers_poses >= 2, monde);
  const cf = await attend('conflits');               // lus à la suite de l'état, sans que la page les demande
  controle('conflits d\'archives envoyés à la suite de l\'état', cf.data.compte.archives > 0 && Array.isArray(cf.data.paires) && cf.data.profil === 't', cf.data.compte);
  await new Promise((r) => setTimeout(r, 50));
  controle('le moteur signale qu\'il travaille puis qu\'il a fini', recus.some((m) => m.t === 'occupe' && m.n > 0) && recus.filter((m) => m.t === 'occupe').pop().n === 0);

  let nr = recus.length;
  versPage({ t: 'conflitsRessources' });
  const cr = await attend('conflitsRessources', nr);
  controle('conflits par ressource : liste rendue à la page', Array.isArray(cr.data.ressources) && cr.data.total === cr.data.ressources.length && Array.isArray(cr.data.ordre), cr.data.compte);
  nr = recus.length;
  versPage({ t: 'conflitsCode' });                   // « Scripts et tweaks… » : lu à la demande, jamais à la suite de l'état
  const cc = await attend('conflitsCode', nr);
  controle('conflits de code : trouvailles, comptes, limites et fichiers lus rendus à la page',
    Array.isArray(cc.data.trouvailles) && Array.isArray(cc.data.limites) && typeof cc.data.compte === 'object' && cc.data.lus.reds >= 0 && cc.data.profil === 't', cc.data.compte);
  versPage({ t: 'ouvreFichier', chemin: SCRIPT, ligne: 12 });
  await pause(30);
  controle("clic sur un fichier de code : ouvert dans l'éditeur, à sa ligne", !!etat.montre && etat.montre.chemin === SCRIPT && etat.montre.ligne === 11, etat.montre);
  const ne = erreurs.length;
  versPage({ t: 'ouvreFichier', chemin: SCRIPT + '.absent', ligne: 1 });
  await pause(30);
  controle('fichier de code absent du disque : dit, rien ouvert', erreurs.length === ne + 1 || recus.some((m) => m.t === 'erreur' && /Absent du disque/.test(m.message)), erreurs.slice(ne));
  const avantAnalyse = etat.crees, pagePrincipale = versPage;
  versPage({ t: 'conflitsFenetre' });
  await pause(20);
  controle("fenêtre d'analyse : un onglet de plus, la même page marquée « analyse »",
    etat.crees === avantAnalyse + 1 && etat.dernier.webview.html.includes('<body class="analyse" data-cle="">') && etat.dernier.type === 'redStackAnalyse', etat.crees);
  nr = recus.length;
  versPage({ t: 'pret' });                           // l'onglet d'analyse s'annonce : état et conflits repartent vers les deux
  await attend('etat', nr);
  await pause(50);
  controle("les deux onglets reçoivent l'état", recus.slice(nr).filter((m) => m.t === 'etat').length === 2, recus.slice(nr).map((m) => m.t));
  etat.dernier.ferme();                              // il ferme l'analyse : la page reste seule à l'écoute
  versPage = pagePrincipale;
  await attend('conflits', nr);
  {
    console.log('1 quater. onglet des scripts, relecture automatique, historique');
    const av = etat.crees;
    versPage({ t: 'codeFenetre' });
    await pause(20);
    controle('« Scripts et tweaks… » : un troisième onglet, marqué « analyse code », à part de celui des archives',
      etat.crees === av + 1 && etat.dernier.type === 'redStackCode' && etat.dernier.webview.html.includes('<body class="analyse code" data-cle="">'), etat.dernier.type);
    const onglet = etat.dernier;
    versPage({ t: 'codeFenetre' });
    await pause(20);
    controle('redemandé : le même onglet ramené devant, aucun de plus', etat.crees === av + 1);
    onglet.ferme();
    versPage = pagePrincipale;
    await pause(300);
    nr = recus.length;
    etat.fenetre({ focused: true });                 // retour sur la fenêtre, rien n'a changé sur le disque
    await pause(2600);
    controle('retour sur la fenêtre sans changement du disque : aucune relecture', !recus.slice(nr).some((m) => m.t === 'etat'), recus.slice(nr).map((m) => m.t));
    const pile = path.join(DEPOT, fs.readdirSync(DEPOT).find((d) => /^\d+_/.test(d)));
    const temoin = path.join(pile, 'veille_essai.txt');
    fs.writeFileSync(temoin, 'x');                   // un fichier arrive dans une pile : le guet du dossier le voit
    const auto = await attend('etat', nr, 15000);
    controle('un fichier arrive dans une pile : état relu seul, marqué automatique', auto.auto === true && auto.veille === true, { auto: auto.auto, veille: auto.veille });
    await attend('conflits', nr);
    nr = recus.length;
    fs.rmSync(temoin);
    const auto2 = await attend('etat', nr, 15000);
    controle('le fichier repart : relu seul une seconde fois', auto2.auto === true);
    await attend('conflits', nr);
    await pause(1800);
    nr = recus.length;
    versPage({ t: 'journal' });
    const jr = await attend('journal', nr);
    controle('historique : entrées rendues à la page, la plus récente d\'abord',
      Array.isArray(jr.data.entrees) && jr.data.total >= jr.data.entrees.length && /historique\.jsonl$/.test(jr.data.fichier), jr.data.total);
    console.log('1 quinquies. magasin, purge, sauvegarde des réglages');
    nr = recus.length;
    versPage({ t: 'magasin' });
    const mg = (await attend('magasin', nr)).data;
    controle('magasin : liens, poids réel et arbres sans mod rendus à la page',
      mg.reel === mg.octets + mg.jeu.octets_copies && mg.explorateur >= mg.reel && Array.isArray(mg.sans_mod) && Array.isArray(mg.retouches), mg.jeu);
    const temoinArbre = path.join(MAGASIN, '1_Core', 'Arbre Orphelin Du Banc');
    fs.mkdirSync(temoinArbre, { recursive: true });
    fs.writeFileSync(path.join(temoinArbre, 'x.archive'), 'orphelin');
    reponse = 'Entree'; modales.length = 0; nr = recus.length;
    await libre(); versPage({ t: 'purge' });
    await pause(2500);
    controle('purge : liste à choix, Entrée = rien supprimé', modales.length === 1 && modales[0].defaut === false && fs.existsSync(temoinArbre), modales);
    reponse = 'Appliquer'; nr = recus.length;
    await libre(); versPage({ t: 'purge' });
    const mg2 = (await attend('magasin', nr, 20000)).data;
    controle('purge confirmée : l\'arbre sans mod part, la page reçoit le magasin relu',
      !fs.existsSync(temoinArbre) && !mg2.sans_mod.some((x) => /Orphelin/.test(x.arbre)) && infos.some((t) => /\d arbres? supprimés? du magasin\./.test(t)), mg2.sans_mod);
    nr = recus.length;
    await libre(); versPage({ t: 'sauvegarde', geste: 'liste' });
    const s0 = (await attend('sauvegarde', nr)).data.sauvegardes.length;
    const cetRegle = path.join(JEU, 'r6', 'storages', 'essai');
    fs.mkdirSync(cetRegle, { recursive: true });
    fs.writeFileSync(path.join(cetRegle, 'etat.json'), 'un');
    nr = recus.length;
    await libre(); versPage({ t: 'sauvegarde', geste: 'cree' });
    const s1 = await attend('sauvegarde', nr, 20000);
    controle('« Sauvegarder maintenant » : une sauvegarde de plus, dite à la page',
      s1.data.sauvegardes.length === s0 + 1 && /Sauvegardé/.test(s1.dit) && fs.existsSync(path.join(s1.data.sauvegardes[0].chemin, 'r6', 'storages', 'essai', 'etat.json')), s1.dit);
    fs.writeFileSync(path.join(cetRegle, 'etat.json'), 'deux');
    reponse = 'Entree'; modales.length = 0; nr = recus.length;
    await libre(); versPage({ t: 'sauvegarde', geste: 'restaure', nom: s1.data.sauvegardes[0].nom });
    const s2 = await attend('sauvegarde', nr, 20000);
    controle('« Restaurer… » : l\'écart est montré, Entrée = rien écrit',
      modales.length === 1 && modales[0].defaut === false && s2.compare.changes.length === 1 && !s2.compare.restaure && fs.readFileSync(path.join(cetRegle, 'etat.json'), 'utf8') === 'deux', s2.compare);
    reponse = 'Appliquer'; nr = recus.length;
    await libre(); versPage({ t: 'sauvegarde', geste: 'restaure', nom: s1.data.sauvegardes[0].nom });
    const s3 = await attend('sauvegarde', nr, 20000);
    controle('restauration confirmée : le réglage revient, celui d\'avant est copié',
      s3.compare.restaure && fs.readFileSync(path.join(cetRegle, 'etat.json'), 'utf8') === 'un' && !!s3.compare.copies && /restauré/.test(s3.dit), s3.compare);
    fs.rmSync(cetRegle, { recursive: true });
    modales.length = 0;
    reponse = undefined;
  }
  console.log('1 ter. barre latérale et noms dans le jeu');
  {
    for (let i = 0; i < 400 && !etat.arbre.getChildren().some((x) => x.label === "Conflits d'archives" && /ressource/.test(x.description)); i++) await pause(50);
    const lignes = etat.arbre.getChildren(), par = Object.fromEntries(lignes.map((i) => [i.label, i]));
    controle('barre latérale : profil, mods actifs, conflits et raccourcis, chacun avec sa commande',
      par.Profil.description === 't' && /^\d+ sur \d+$/.test(par['Mods actifs'].description) && etat.arbreDit >= 2
      && ['Aperçu du plan', 'Arrivages', 'Réglages', 'Actualiser'].every((k) => par[k] && par[k].command.command === 'redStack.vue')
      && par.Profil.command.command === 'redStack.profilChoisir' && etat['redStack.vue'] && etat['redStack.profilChoisir'], lignes.map((i) => i.label));
    let nr = recus.length;
    await etat['redStack.vue']('arrivages');
    controle('raccourci « Arrivages » : la page reçoit la vue demandée', recus.slice(nr).some((x) => x.t === 'vue' && x.v === 'arrivages'));
    const dbl = fauxPanneau(), dbl2 = fauxPanneau();
    await etat.serialiseurAnalyse.deserializeWebviewPanel(dbl, undefined);
    await etat.serialiseurAnalyse.deserializeWebviewPanel(dbl2, undefined);
    controle("onglet « Conflits » rouvert par VS Code : branché sur la page d'analyse, un doublon est fermé",
      (dbl.jete === true || /class="analyse"/.test(dbl.webview.html)) && dbl2.jete === true);
    if (!dbl.jete) dbl.ferme();
    versPage = pagePrincipale;
    const ob = fauxPanneau(), ob2 = fauxPanneau();       // l'onglet « Objets » rouvert : la même page, corps marqué « objets »
    await etat.serialiseurObjets.deserializeWebviewPanel(ob, undefined);
    await etat.serialiseurObjets.deserializeWebviewPanel(ob2, undefined);
    controle("onglet « Objets » rouvert par VS Code : page d'analyse « objets », un doublon est fermé",
      /class="analyse objets"/.test(ob.webview.html) && ob2.jete === true && !!etat.serialiseurAnalyse && !!etat.serialiseurCode);
    ob.ferme();
    versPage = pagePrincipale;
    nr = recus.length;
    await pagePrincipale({ t: 'objets', partie: '' });
    const ob3 = (await attend('objets', nr)).data;
    controle("« Objets » : le moteur répond, dossier des parties dit, liste des mods (rien n'est écrit)",
      ob3 && typeof ob3.dossier === 'string' && Array.isArray(ob3.mods) && Array.isArray(ob3.parties), ob3);
    const dp = fauxPanneau(), dp2 = fauxPanneau();       // l'onglet « Dépendances » rouvert : la même page, corps marqué « dependances »
    await etat.serialiseurDeps.deserializeWebviewPanel(dp, undefined);
    await etat.serialiseurDeps.deserializeWebviewPanel(dp2, undefined);
    controle("onglet « Dépendances » rouvert par VS Code : page d'analyse « dependances », un doublon est fermé",
      /class="analyse dependances"/.test(dp.webview.html) && dp2.jete === true);
    dp.ferme();
    versPage = pagePrincipale;
    nr = recus.length;
    await pagePrincipale({ t: 'dependances' });
    const dep = (await attend('dependances', nr)).data;
    const socle = dep && dep.mods.find((r) => r.requis_par_actifs > 0);
    controle("« Dépendances » : prérequis du dépôt, compte du code pas encore lu (rien n'est écrit)",
      dep && Array.isArray(dep.mods) && Array.isArray(dep.cadres) && typeof dep.code_non_lus === 'number', dep && Object.keys(dep));
    nr = recus.length;
    await pagePrincipale({ t: 'chaine', depart: socle ? socle.cle : 'c:cet', sens: 'chute' });
    const chn = (await attend('chaine', nr)).data;
    nr = recus.length;
    await pagePrincipale({ t: 'chaine', depart: 'c:cet', sens: 'besoin' });
    const chc = (await attend('chaine', nr)).data;
    controle("« Dépendances » : la chaîne d'un mod (ce qui tombe), celle d'un cadre (toujours « chute », même demandée « besoin »)",
      chn && chn.sens === 'chute' && chn.noeuds[chn.depart].palier === 0 && chc && chc.depart === 'c:cet' && chc.sens === 'chute', [chn, chc]);
    const profilAvant = fs.readFileSync(path.join(DONNEES, 'profils', 't.json'), 'utf8'), jeuAvant = instantane();
    const alpha = cf.data.ordre.find((a) => a.genre === 'mod' && a.zip).zip;
    nr = recus.length;
    await pagePrincipale({ t: 'noms', cle: alpha });
    const nm = (await attend('noms', nr)).data, u = nm.unites.find((x) => x.genre === 'archive');
    controle('« Noms dans le jeu… » : les noms du mod, aucun changé', nm.cle === alpha && u && !nm.unites.some((x) => x.renommee), nm.unites);
    nr = recus.length;
    const ni = infos.length;
    await pagePrincipale({ t: 'nomsFixe', cle: alpha, noms: [{ de: u.chemin, vers: '!' + u.nom }] });
    const n2 = await attend('noms', nr);
    controle('noté au profil : la page relit le nouveau nom, le jeu est annoncé à appliquer, jamais écrit ici',
      n2.data.fait.length === 1 && n2.data.unites.find((x) => x.chemin === u.chemin).actuel === '!' + u.nom && /noté/.test(n2.dit)
      && infos.slice(ni).some((t) => /Appliquer/.test(t)) && instantane() === jeuAvant, n2.data.fait);
    nr = recus.length;
    await pagePrincipale({ t: 'nomsFixe', cle: alpha, noms: [{ de: u.chemin, vers: '' }] });
    await attend('noms', nr);
    await attend('conflits', nr);
    controle("champ vide : nom de l'auteur rendu, profil comme avant",
      JSON.stringify(JSON.parse(fs.readFileSync(path.join(DONNEES, 'profils', 't.json'), 'utf8')).mods) === JSON.stringify(JSON.parse(profilAvant).mods));
  }
  console.log('1 bis. ordre de chargement : le profil change, pas le jeu');
  {
    const jeuAvant = instantane(), profilAvant = fs.readFileSync(path.join(DONNEES, 'profils', 't.json'), 'utf8');
    const libres = cf.data.ordre.filter((a) => a.genre === 'mod' && a.zip);
    const tete = libres[0], queue = libres[libres.length - 1];
    reponse = undefined;                              // Échap sur la liste à choix
    const nm = modales.length;
    await pagePrincipale({ t: 'ordrePasse', nom: queue.archive, cible: tete.archive, sens: 'avant' });
    controle('« Passer devant » : une liste à choix, « ne rien changer » d\'office, profil intact sur Échap',
      modales.length === nm + 1 && modales[nm].defaut === '' && fs.readFileSync(path.join(DONNEES, 'profils', 't.json'), 'utf8') === profilAvant, modales[nm]);
    reponse = 'Appliquer';                            // le premier choix qui écrit : le nom proposé
    nr = recus.length;
    await pagePrincipale({ t: 'ordrePasse', nom: queue.archive, cible: tete.archive, sens: 'avant' });
    let c2 = (await attend('conflits', nr)).data;
    const neuve = c2.ordre.find((a) => a.origine === queue.archive && a.zip === queue.zip);
    controle('nom proposé accepté : l\'archive passe devant dans l\'analyse, son nom d\'auteur gardé, changement annoncé',
      neuve && neuve.archive !== queue.archive && neuve.rang < c2.ordre.find((a) => a.archive === tete.archive).rang && c2.a_appliquer > 0, neuve);
    nr = recus.length;
    await pagePrincipale({ t: 'ordreAnnule', nom: neuve.archive });
    c2 = (await attend('conflits', nr)).data;
    controle('nom de l\'auteur rendu : profil comme avant, jeu jamais touché',
      c2.ordre.some((a) => a.archive === queue.archive) && c2.a_appliquer === 0 && instantane() === jeuAvant
      && JSON.stringify(JSON.parse(fs.readFileSync(path.join(DONNEES, 'profils', 't.json'), 'utf8')).mods) === JSON.stringify(JSON.parse(profilAvant).mods));
    reponse = undefined;
    modales.length = nm;                              // la suite compte ses propres confirmations
  }
  console.log('2. cases : le profil change, pas le jeu');
  const avant = instantane();
  let n = recus.length;
  await libre(); versPage({ t: 'bascule', cle: monde.cle, valeur: false });
  e = await attend('etat', n);
  const coupe = e.data.mods.find((r) => r.cle === monde.cle);
  controle('mod coupé dans le profil, retrait en attente', !coupe.actif && coupe.retire === monde.fichiers_poses && coupe.etat === 'coupé, à retirer', coupe);
  n = recus.length;
  versPage({ t: 'detail', cle: monde.cle });
  const det = (await attend('detail', n)).data;
  controle('détail : entrées, zip, arbre', det.entrees.length >= 2 && fs.existsSync(det.zip) && det.arbre.startsWith(MAGASIN), det);
  n = recus.length;
  versPage({ t: 'fichier', nom: 'w1.archive' });
  const fic = (await attend('fichier', n)).data;
  controle('fichier : propriétaire trouvé', fic.total === 1 && fic.fichiers[0].zip === monde.cle, fic);
  n = recus.length;
  versPage({ t: 'plan' });
  let plan = (await attend('plan', n)).data;
  controle('plan : les fichiers du mod à retirer, empreinte', plan.compte.retire === monde.fichiers_poses && plan.empreinte.length === 16, plan.compte);
  controle('LE JEU N\'A PAS BOUGÉ jusqu\'ici', instantane() === avant);

  console.log('3. appliquer : confirmation obligatoire, empreinte du plan vu');
  reponse = undefined;                               // l'utilisateur ferme la modale
  n = recus.length;
  await libre(); versPage({ t: 'applique', empreinte: plan.empreinte });
  await attend('etat', n);
  controle('modale montrée, chiffrée', modales.length === 1 && /à retirer/.test(modales[0].detail) && /Monde/.test(modales[0].detail), modales);
  controle('refus : rien d\'écrit', instantane() === avant && !recus.slice(n).some((m) => m.t === 'applique'));
  reponse = 'Appliquer';
  n = recus.length;
  await libre(); versPage({ t: 'applique', empreinte: '0000000000000000' });
  const err = await attend('erreur', n);
  controle('empreinte périmée : erreur, plan renvoyé, aucune modale de plus, rien d\'écrit',
    /plan a changé/.test(err.message) && recus.slice(n).some((m) => m.t === 'plan') && modales.length === 1 && instantane() === avant, err);
  n = recus.length;
  await libre(); versPage({ t: 'applique', empreinte: plan.empreinte });
  const fait = (await attend('applique', n)).data;
  controle('confirmé : appliqué, fichiers retirés du jeu', fait.compte.retire === monde.fichiers_poses && fait.echecs.length === 0
    && !fs.existsSync(path.join(JEU, 'archive', 'pc', 'mod', 'w1.archive')), fait);
  e = await attend('etat', n);
  controle('état relu : mod coupé, plus rien en attente', e.data.mods.find((r) => r.cle === monde.cle).etat === 'coupé');

  console.log('4. profils');
  n = recus.length;
  await libre(); versPage({ t: 'profilNouveau' });
  e = await attend('etat', n);
  controle('profil « essai » créé par copie et choisi', e.data.profil === 'essai' && e.profils.some((p) => p.nom === 'essai'), e.profils);
  reponse = 'Supprimer';
  n = recus.length;
  await libre(); versPage({ t: 'profilSupprime' });
  e = await attend('etat', n);
  controle('profil supprimé après confirmation, repli sur un profil qui existe',
    !e.profils.some((p) => p.nom === 'essai') && store.get('redStack.profil') === 't' && e.data.profil === 't', e.profils);

  console.log('5. demande d\'une session Claude (serveur MCP)');
  n = recus.length;
  await libre(); versPage({ t: 'bascule', cle: monde.cle, valeur: true });
  await attend('etat', n);
  n = recus.length;
  versPage({ t: 'plan' });
  plan = (await attend('plan', n)).data;
  const depose = (id) => fs.writeFileSync(path.join(DONNEES, 'demande.json'), JSON.stringify(
    { id, etat: 'attente', profil: 't', empreinte: plan.empreinte, compte: plan.compte, motif: 'remettre Monde' }));
  const lue = () => JSON.parse(fs.readFileSync(path.join(DONNEES, 'demande.json'), 'utf8'));
  const jusqua = async (f) => { for (let i = 0; i < 400 && !f(); i++) await pause(50); return f(); };
  reponse = undefined;
  let m0 = modales.length;
  depose('refus1');
  await jusqua(() => lue().etat !== 'attente');
  controle('demande vue toute seule, motif montré, refusée : rien d\'écrit',
    lue().etat === 'refusée' && modales.length === m0 + 1 && /remettre Monde/.test(modales[m0].detail)
    && !fs.existsSync(path.join(JEU, 'archive', 'pc', 'mod', 'w1.archive')), lue());
  reponse = 'Appliquer';
  depose('accord1');
  await jusqua(() => lue().etat !== 'attente');
  controle('demande acceptée : appliquée, résultat écrit dans la demande, mod reposé',
    lue().etat === 'appliquée' && lue().resultat.compte.pose === monde.fichiers_poses
    && fs.existsSync(path.join(JEU, 'archive', 'pc', 'mod', 'w1.archive')), lue());
  console.log('6. réglages');
  controle('moteur et serveur MCP copiés à un chemin stable', fs.existsSync(path.join(STOCK, 'moteur', 'red_stack.py')) && fs.existsSync(path.join(STOCK, 'moteur', 'red_stack_mcp.py'))
    && fs.existsSync(path.join(STOCK, 'moteur', 'red_stack_wk_mcp.py')));
  const confAvant = fs.readFileSync(path.join(DONNEES, 'config.json'), 'utf8');
  n = recus.length;
  versPage({ t: 'reglages' });
  let rg = await attend('reglages', n);
  controle('réglages : chemins, convention, défauts, commande MCP', rg.data.depot === DEPOT && rg.data.existe.jeu && rg.data.convention.piles.length > 0
    && rg.data.reglages_defaut.length > 5 && rg.poste.mcp.includes('red_stack_mcp.py') && rg.poste.mcp.includes(DONNEES)
    && rg.poste.mcpWk.includes('red_stack_wk_mcp.py') && rg.data.wolvenkit === '' && rg.data.existe.wolvenkit === false, rg);
  n = recus.length;
  await libre(); versPage({ t: 'reglagesEcrit', conf: { hors: ['Bin\\x64\\Tiers\\*'], sauvegardes: path.join(BASE, 'sauv'), avant_applique: [], convention: { parques: ['__RAM*', 'Garage é'] } },
    poste: { python: 'python', donnees: DONNEES } });
  rg = await attend('reglages', n);
  controle('enregistré : motif normalisé, accents gardés, le reste de la convention intact',
    rg.enregistre && rg.data.hors.includes('bin/x64/tiers/*') && rg.data.sauvegardes === path.join(BASE, 'sauv')
    && rg.data.convention.parques.includes('Garage é') && rg.data.convention.piles.length > 0 && !etat.posteEcrit, rg.data);
  n = recus.length;
  await libre(); versPage({ t: 'reglagesEcrit', conf: { convention: { piles: [] } }, poste: {} });
  const refus = await attend('erreur', n);
  controle('convention sans pile : refusée par le moteur, dite à la page', /piles/.test(refus.message), refus);
  reponse = undefined;
  n = recus.length; m0 = modales.length;
  await libre(); versPage({ t: 'reglagesEcrit', conf: { jeu: path.join(BASE, 'autre_jeu') }, poste: {} });
  rg = await attend('reglages', n);
  controle('changer le jeu d\'un jeu suivi : confirmation, refus = rien écrit', modales.length === m0 + 1 && rg.data.jeu === JEU && !rg.enregistre, rg.data.jeu);
  n = recus.length;
  await libre(); versPage({ t: 'reference', geste: 'controle' });
  const rf = (await attend('reference', n)).data;
  controle('référence : contrôle rendu (présente ou dite absente)', rf.absente ? /référence/i.test(rf.message) : Array.isArray(rf.modifies), rf);
  versPage({ t: 'copie', texte: 'abc' });
  await jusqua(() => etat.copie === 'abc');
  controle('copie dans le presse-papiers', etat.copie === 'abc');
  console.log('arrivages : noms à la convention');
  const ARRIVE = path.join(DEPOT, '5_World', 'Arrivages', 'Arrive.zip'), ARRIVE2 = path.join(DEPOT, '5_World', 'Arrivages', 'Arrive 2.zip');
  n = recus.length;
  versPage({ t: 'convention' });
  let cvn = (await attend('convention', n)).data;
  controle('arrivages : le zip du dossier d\'arrivée est listé', cvn.lignes.some((r) => r.cle === '5_World/Arrivages/Arrive.zip' && r.statut === 'hors_nexus'), cvn.lignes);
  m0 = modales.length; reponse = 'Entree';         // Entrée sur la liste à choix : le premier choix n'écrit rien
  await libre(); versPage({ t: 'conventionRenomme', noms: [{ cle: '5_World/Arrivages/Arrive.zip', nom: 'Arrive 2.zip' }] });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  controle('renommer : liste à choix, Entrée = rien écrit', modales[m0].defaut === false && /Renommer 1 archive/.test(modales[m0].texte) && fs.existsSync(ARRIVE) && !fs.existsSync(ARRIVE2), modales[m0]);
  n = recus.length; reponse = 'Appliquer';
  await libre(); versPage({ t: 'conventionRenomme', noms: [{ cle: '5_World/Arrivages/Arrive.zip', nom: 'Arrive 2.zip' }] });
  cvn = await attend('convention', n);
  controle('renommer confirmé : le zip porte son nom, la page est prévenue', fs.existsSync(ARRIVE2) && !fs.existsSync(ARRIVE) && /1 archive/.test(cvn.dit), cvn.dit);
  n = recus.length;
  await libre(); versPage({ t: 'conventionRenomme', noms: [{ cle: '5_World/Arrivages/Arrive 2.zip', nom: 'Arrive.zip' }] });
  await attend('convention', n);
  m0 = modales.length; reponse = 'Entree';
  await libre(); versPage({ t: 'deplace', cle: '5_World/Arrivages/Arrive.zip', vers: 'pile' });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  controle('remonter : liste à choix, Entrée = rien écrit', modales[m0].defaut === false && /Remonter/.test(modales[m0].texte) && fs.existsSync(ARRIVE), modales[m0]);
  console.log('contenu d\'un zip');
  n = recus.length;
  versPage({ t: 'contenu', cle: '5_World/Arrivages/Arrive.zip' });
  const ct = await attend('contenu', n);
  const de = 'archive/pc/mod/arrive.archive';
  controle('contenu : plan rendu, l\'archive seule prend le nom du mod', ct.cle === '5_World/Arrivages/Arrive.zip' && ct.data.ops.some((o) => o.de === de && o.vers === 'archive/pc/mod/Arrive.archive'), ct.data);
  m0 = modales.length; reponse = 'Entree';
  await libre(); versPage({ t: 'contenuRenomme', cle: '5_World/Arrivages/Arrive.zip', ops: [{ de, vers: 'archive/pc/mod/Arrive_Voulu.archive' }] });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  const lus = () => require('child_process').execFileSync('python', ['-I', '-c', 'import zipfile,sys;print("|".join(zipfile.ZipFile(sys.argv[1]).namelist()))', ARRIVE]).toString().trim();
  controle('récrire le zip : liste à choix, Entrée = rien écrit', modales[m0].defaut === false && /Renommer 1 fichier/.test(modales[m0].texte) && lus() === de, [modales[m0], lus()]);
  n = recus.length; reponse = 'Appliquer';
  await libre(); versPage({ t: 'contenuRenomme', cle: '5_World/Arrivages/Arrive.zip', ops: [{ de, vers: 'archive/pc/mod/Arrive_Voulu.archive' }] });
  const ct2 = await attend('contenu', n);
  controle('récrire confirmé : le zip porte le chemin retouché, la page est prévenue', lus() === 'archive/pc/mod/Arrive_Voulu.archive' && /1 fichier/.test(ct2.dit), [lus(), ct2.dit]);
  n = recus.length;
  await libre(); versPage({ t: 'contenuRenomme', cle: '5_World/Arrivages/Arrive.zip', ops: [{ de: 'archive/pc/mod/Arrive_Voulu.archive', vers: de }] });
  await attend('contenu', n);
  m0 = modales.length; reponse = 'Entree';         // contenu en lot : une seule liste à choix, aux noms proposés par le moteur
  await libre(); versPage({ t: 'contenuRenommeLot', cles: ['5_World/Arrivages/Arrive.zip', '5_World/absent.zip'] });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  controle("contenu en lot : une seule confirmation, le zip inconnu laissé de côté, Entrée n'écrit rien",
    modales.length === m0 + 1 && /Renommer le contenu de 1 zip/.test(modales[m0].texte) && lus() === de, [modales[m0], lus()]);
  n = recus.length; reponse = 'Appliquer';
  await libre(); versPage({ t: 'contenuRenommeLot', cles: ['5_World/Arrivages/Arrive.zip'] });
  const cl = await attend('convention', n);
  controle('contenu en lot confirmé : le zip porte le nom proposé, la vue est prévenue', lus() === 'archive/pc/mod/Arrive.archive' && /1 zip/.test(cl.dit), [lus(), cl.dit]);
  n = recus.length;
  await libre(); versPage({ t: 'contenuRenomme', cle: '5_World/Arrivages/Arrive.zip', ops: [{ de: 'archive/pc/mod/Arrive.archive', vers: de }] });
  await attend('contenu', n);
  reponse = undefined;
  fs.rmSync(path.join(DONNEES, 'references.json'), { force: true });
  fs.writeFileSync(path.join(DONNEES, 'config.json'), confAvant, 'utf8');
  m0 = modales.length; reponse = 'Entree';         // lot : une seule liste à choix, Entrée = ne rien écrire
  await libre(); versPage({ t: 'deplaceLot', vers: 'pile', cles: ['5_World/Arrivages/Arrive.zip', '5_World/absent.zip'] });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  controle("remonter en lot : une seule confirmation pour le lot, le zip inconnu laissé de côté, Entrée n'écrit rien",
    modales.length === m0 + 1 && /Remonter 1 zip/.test(modales[m0].texte) && fs.existsSync(ARRIVE), modales[m0]);
  m0 = modales.length; reponse = 'Entree';         // retirer en lot depuis la liste : même garde, rien n'est effacé ni écrit sur Entrée
  await libre(); versPage({ t: 'deplaceLot', vers: 'retires', cles: ['5_World/Arrivages/Arrive.zip'], retour: 'liste' });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  controle("retirer en lot : une seule confirmation, Entrée n'écrit rien",
    modales.length === m0 + 1 && /Retirer 1 zip/.test(modales[m0].texte) && fs.existsSync(ARRIVE), modales[m0]);
  m0 = modales.length;
  await libre(); versPage({ t: 'deplace', cle: '5_World/Arrivages/Arrive.zip', vers: 'retires' });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  controle('retirer un zip : liste à choix, Entrée = rien écrit', /Retirer « Arrive » \?/.test(modales[m0].texte) && fs.existsSync(ARRIVE), modales[m0]);
  const iv = recus.length;                          // verrou : posé avant la confirmation, levé à la fin du geste, même sans écriture
  m0 = modales.length;
  await libre(); versPage({ t: 'deplace', cle: '5_World/Arrivages/Arrive.zip', vers: 'parques' });
  await jusqua(() => modales.length === m0 + 1);
  await jusqua(() => recus.slice(iv).filter((x) => x.t === 'verrou').length === 2);
  const vs = recus.slice(iv).filter((x) => x.t === 'verrou');
  controle('un geste qui écrit verrouille la page du début à la fin', vs.length === 2 && vs[0].on === true && vs[1].on === false && fs.existsSync(ARRIVE), vs);
  const ne2 = recus.length;                           // supprimer : les seuls zips des retirés ; un arrivage est refusé, rien n'est supprimé
  await libre(); versPage({ t: 'supprime', cles: ['5_World/Arrivages/Arrive.zip'] });
  await jusqua(() => recus.slice(ne2).some((x) => x.t === 'erreur'));
  controle('supprimer un zip qui n\'est pas dans les retirés : refusé, le zip reste', recus.slice(ne2).some((x) => x.t === 'erreur' && /Aucun zip retiré/.test(x.message)) && fs.existsSync(ARRIVE), recus.slice(ne2).map((x) => x.t));
  const PARTI = path.join(DEPOT, '5_World', 'Corbeille', 'Parti.zip');   // un zip des retirés : supprimé par la corbeille du système, inscrit à l'historique
  fs.mkdirSync(path.dirname(PARTI), { recursive: true }); fs.copyFileSync(ARRIVE, PARTI);
  reponse = 'Appliquer'; n = recus.length;
  await libre(); versPage({ t: 'supprime', cles: ['5_World/Corbeille/Parti.zip'] });
  await attend('etat', n);
  n = recus.length; versPage({ t: 'journal' });
  const js = (await attend('journal', n)).data.entrees;
  controle('supprimer un zip retiré : parti par la corbeille du système, le geste est à l\'historique',
    !fs.existsSync(PARTI) && etat.corbeille === true && js[0].geste === 'supprime' && js[0].de === PARTI, js[0]);
  reponse = 'Entree';
  n = recus.length;                                 // cases cochées à la suite : jouées ensemble, un seul état relu, puis « basculeFait »
  await libre(); versPage({ t: 'basculeLot', mods: [[monde.cle, false], [monde.cle, true]] });
  await attend('basculeFait', n);
  const eb = await attend('etat', n);
  controle('bascules en lot : jouées dans l\'ordre, le mod finit actif', eb.data.mods.find((r) => r.cle === monde.cle).actif === true
    && recus.slice(n).filter((x) => x.t === 'etat').length === 1, recus.slice(n).map((x) => x.t));
  m0 = modales.length; reponse = 'Entree';         // changer de pile : une liste des autres piles, puis la confirmation ; Entrée n'écrit rien
  const ZMONDE = path.join(DEPOT, ...monde.cle.split('/'));
  await libre(); versPage({ t: 'changePile', cle: monde.cle });
  await jusqua(() => modales.length === m0 + 2);
  await pause(300);
  controle("changer de pile : la pile se choisit (jamais la sienne), puis une confirmation ; Entrée n'écrit rien",
    modales.length === m0 + 2 && /de pile/.test(modales[m0].texte) && /de pile \?/.test(modales[m0 + 1].texte) && fs.existsSync(ZMONDE), modales.slice(m0));
  reponse = undefined;
  console.log('mises à jour Nexus : liste, clé au coffre, ignorer');
  n = recus.length;
  versPage({ t: 'maj' });
  let mj = await attend('maj', n, 90000);
  controle('mises à jour : liste rendue, Nexus injoignable dit, aucune clé, aucun environnement passé au moteur',
    /injoignable/.test(mj.data.erreur || '') && mj.data.lignes.length > 0 && mj.compte.cle === false && etat.envVu === undefined, [mj.data.erreur, mj.compte]);
  const uneCle = mj.data.lignes[0].cle;
  n = recus.length;
  await libre(); versPage({ t: 'majTelecharge', lignes: [{ cle: uneCle, fichier: 0, nom: '' }] });
  controle('télécharger sans clé : refus dit à la page, rien demandé au moteur', /clé d'API/.test((await attend('erreur', n)).message));
  n = recus.length;
  versPage({ t: 'majCle' });                         // la boîte de saisie du banc rend « essai »
  mj = await attend('maj', n, 90000);
  controle('clé saisie dans VS Code : gardée au coffre, passée au moteur par son environnement, jamais par ses arguments ni par la page',
    coffre.get('redStack.nexusCle') === 'essai' && mj.compte.cle === true && !!mj.compte.erreur && !JSON.stringify(mj).includes('essai')
    && !fs.readFileSync(path.join(DONNEES, 'config.json'), 'utf8').includes('essai'), mj.compte);
  n = recus.length;
  versPage({ t: 'majIgnore', cle: uneCle, valeur: true });
  mj = await attend('maj', n, 90000);
  controle('ignorer un mod : la ligne revient marquée', mj.data.lignes.find((r) => r.cle === uneCle).ignore === true);
  n = recus.length;
  versPage({ t: 'majIgnore', cle: uneCle, valeur: false });
  mj = await attend('maj', n, 90000);
  controle('ne plus ignorer : la marque tombe', mj.data.lignes.find((r) => r.cle === uneCle).ignore === false);
  n = recus.length; m0 = modales.length;
  await libre(); versPage({ t: 'majTelecharge', lignes: [{ cle: uneCle, fichier: 0, nom: '' }] });
  controle('télécharger une ligne sans nouvelle version : refus du moteur dit à la page, aucune confirmation',
    /Rien à télécharger/.test((await attend('erreur', n)).message) && modales.length === m0);
  controle('barre latérale : raccourci « Mises à jour »', etat.arbre.getChildren().some((x) => x.label === 'Mises à jour' && x.command.arguments[0] === 'maj'));
  console.log('liens nxm:// : registre lu, lien reçu, arrivage rangé à la place de l\'ancienne version');
  const nxm = require('../nxm');
  const CODE = ['C:', 'Program Files', 'Microsoft VS Code', 'Code.exe'].join(path.sep), CLE_NXM = ['HKCU', 'Software', 'Classes', 'nxm'].join(path.sep);
  const SIEN = `"${CODE}" --open-url -- "%1"`;
  controle('commande d\'inscription : celle de vscode:// chez Windows, le lien enveloppé dans l\'adresse de l\'extension ; sinon l\'exécutable',
    nxm.commandePour(SIEN, 'x', 'vscode', 'doublescotch.red-stack') === `"${CODE}" --open-url -- "vscode://doublescotch.red-stack/nxm?%1"`
    && nxm.commandePour('', CODE, 'vscode', 'a.b') === `"${CODE}" --open-url -- "vscode://a.b/nxm?%1"`);
  controle('registre : valeur lue sous un Windows français, programme nommé',
    nxm.valeur('\r\nHKEY_CLASSES_ROOT/vscode/shell/open/command\r\n    (par d\xe9faut)    REG_SZ    ' + SIEN + '\r\n\r\n') === SIEN && nxm.programme(SIEN) === 'Code.exe' && nxm.valeur('') === '');
  const LIEN = 'nxm://cyberpunk2077/mods/7001/files/5?key=abc&expires=9&user_id=1';
  controle('lien reçu de VS Code : brut ou encodé, rien d\'autre', nxm.lienRecu(LIEN) === LIEN && nxm.lienRecu(encodeURIComponent(LIEN)) === LIEN && nxm.lienRecu('https://x') === '');
  if (process.platform === 'win32') {
    const appels = [];
    const fauxReg = (exe, args, o, f) => { appels.push(args); f(args[0] === 'query' && /vscode/.test(args[1]) ? null : Object.assign(new Error('absent'), { code: 1 }), Buffer.from('    (Default)    REG_SZ    ' + SIEN + '\r\n'), Buffer.from('')); };
    const en = await nxm.etat('x', 'vscode', 'doublescotch.red-stack', fauxReg);
    controle('état, registre simulé : aucun programme inscrit, la commande voulue est prête, lecture seule', en.possible && !en.inscrit && en.commande === '' && /nxm\?%1"$/.test(en.voulue) && appels.every((a) => a[0] === 'query'), en);
    appels.length = 0;
    await nxm.inscrit(en.voulue, fauxReg);
    controle('inscription, registre simulé : trois écritures sous la clé de l\'utilisateur seulement',
      appels.filter((a) => a[0] === 'add').length === 3 && appels.every((a) => a[1].startsWith(CLE_NXM)), appels);
    n = recus.length;
    versPage({ t: 'nxmEtat' });
    const vraie = (await attend('nxm', n)).data;
    m0 = modales.length; reponse = 'Entree';
    versPage({ t: vraie.inscrit ? 'nxmRetire' : 'nxmInscrit' });
    await jusqua(() => modales.length === m0 + 1);
    await pause(300);
    n = recus.length;
    versPage({ t: 'nxmEtat' });
    controle('inscrire depuis la page : liste à choix, Entrée = registre inchangé', modales[m0].defaut === false && /nxm/.test(modales[m0].texte)
      && (await attend('nxm', n)).data.commande === vraie.commande, [modales[m0], vraie]);
    reponse = undefined;
  }
  const e0 = erreurs.length;
  coffre.clear();
  etat.adresse({ path: '/nxm', query: LIEN });
  await jusqua(() => erreurs.length === e0 + 1);
  controle('lien reçu sans clé d\'API : dit, rien demandé à Nexus', /aucune clé d'API/.test(erreurs[e0]), erreurs[e0]);
  etat.adresse({ path: '/nxm', query: 'nimporte' });
  await jusqua(() => erreurs.length === e0 + 2);
  controle('adresse sans lien lisible : dite, rien fait', /sans lien lisible/.test(erreurs[e0 + 1]), erreurs[e0 + 1]);
  erreurs.length = e0;
  const W = path.join(DEPOT, '5_World'), VIEUX_R = path.join(W, 'Essai Range-7001-1-0-1700000001.zip'), NEUF_R = path.join(W, 'Arrivages', 'Essai Range-7001-1-1-1700000002.zip');
  fs.copyFileSync(ARRIVE, VIEUX_R); fs.copyFileSync(ARRIVE, NEUF_R);
  n = recus.length;
  versPage({ t: 'convention' });
  const lr = (await attend('convention', n, 90000)).data.lignes.find((r) => r.nom === path.basename(NEUF_R));
  controle('arrivage d\'un mod en place, Nexus injoignable : reconnu par son nom comme la mise à jour, nom proposé',
    lr && lr.maj_de.length === 1 && lr.maj_de[0].sur && lr.maj_de[0].cle === '5_World/' + path.basename(VIEUX_R) && lr.maj_de[0].propose === path.basename(NEUF_R), lr);
  m0 = modales.length; reponse = 'Entree';
  await libre(); versPage({ t: 'conventionRange', cle: lr.cle, de: lr.maj_de[0].cle, nom: lr.maj_de[0].propose });
  await jusqua(() => modales.length === m0 + 1);
  await pause(300);
  controle('ranger la mise à jour : liste à choix, Entrée = rien écrit', modales[m0].defaut === false && /Ranger/.test(modales[m0].texte) && fs.existsSync(NEUF_R) && fs.existsSync(VIEUX_R), modales[m0]);
  n = recus.length; reponse = 'Appliquer';
  await libre(); versPage({ t: 'conventionRange', cle: lr.cle, de: lr.maj_de[0].cle, nom: lr.maj_de[0].propose });
  const rg2 = await attend('convention', n, 90000);
  const RANGE = path.join(W, path.basename(NEUF_R));
  const retires = fs.readdirSync(W, { withFileTypes: true }).filter((d) => d.isDirectory() && fs.existsSync(path.join(W, d.name, path.basename(VIEUX_R)))).map((d) => d.name);
  controle('rangée, confirmé : l\'arrivage à la place, l\'ancienne version dans les retirés, la page prévenue',
    fs.existsSync(RANGE) && !fs.existsSync(NEUF_R) && !fs.existsSync(VIEUX_R) && retires.length === 1 && /Rangé/.test(rg2.dit), [retires, rg2.dit]);
  reponse = undefined;
  fs.rmSync(RANGE, { force: true });
  for (const d of retires) { fs.rmSync(path.join(W, d, path.basename(VIEUX_R)), { force: true }); try { fs.rmdirSync(path.join(W, d)); } catch { /* dossier déjà là avant l'essai, pas vide */ } }
  await pause(200);
  coffre.clear();
  fs.rmSync(path.join(DONNEES, 'nexus.json'), { force: true });
  fs.writeFileSync(path.join(DONNEES, 'config.json'), confAvant, 'utf8');
  // section « Thème » des réglages : un clic écrit le thème de VS Code et la page est prévenue ; la case écrit son réglage
  n = recus.length;
  versPage({ t: 'theme', nom: 'Red Stack Rouge' });
  const th = (await attend('theme', n)).data;
  controle('thème activé depuis les réglages : workbench.colorTheme écrit, la page prévenue', reglagesPoste.colorTheme === 'Red Stack Rouge' && th.theme === 'Red Stack Rouge' && th.themes.length === 2, th);
  n = recus.length;
  versPage({ t: 'theme', nom: 'Un Thème Inconnu', barre: true });
  const th2 = (await attend('theme', n)).data;
  controle('thème inconnu refusé, case des icônes en couleur notée', reglagesPoste.colorTheme === 'Red Stack Rouge' && reglagesPoste.barreEnCouleur === true && th2.barre === true, th2);
  delete reglagesPoste.colorTheme; delete reglagesPoste.barreEnCouleur;
  // le manuel : un onglet à lui, page entière (ni nonce ni version restés en gabarit), rouvert une seule fois
  const pageMessages = versPage, crees = etat.crees;
  n = recus.length;
  await etat['redStack.aide']('maj');
  const man = etat.dernier;
  controle('manuel : onglet « redStackAide » créé, page complète, section demandée envoyée',
    etat.crees === crees + 1 && man.type === 'redStackAide' && /Le principe en une minute/.test(man.webview.html) && !/\{\{/.test(man.webview.html)
    && recus.slice(n).some((x) => x.t === 'section' && x.id === 'maj'), [etat.crees - crees, man.type]);
  await etat['redStack.aide']();
  controle('manuel déjà ouvert : ramené devant, pas de second onglet', etat.crees === crees + 1);
  versPage = pageMessages;
  controle('aucune erreur montrée hors celle attendue', erreurs.length === 0, erreurs);

  console.log('langue : catalogue anglais, repli, page, changement de réglage');
  const lg = require('../langue');
  const racine = path.join(__dirname, '..');
  controle('français d\'office dans ce banc (VS Code dit fr)', lg.enCours().langue === 'fr' && lg.T('Enregistrer') === 'Enregistrer');
  controle('auto suit VS Code, une langue absente passe en anglais, fr-FR reste en français',
    lg.charge(racine, 'auto', 'en-US').langue === 'en' && lg.charge(racine, 'auto', 'nl').langue === 'en' && lg.charge(racine, '', 'fr-FR').langue === 'fr'
    && lg.charge(racine, 'fr', 'en').langue === 'fr' && lg.charge(racine, 'en', 'fr').langue === 'en', lg.charge(racine, 'auto', 'nl').langue);
  controle('auto : de, pt-BR et zh-CN ont leur catalogue, le chinois traditionnel passe en anglais',
    lg.charge(racine, 'auto', 'de').langue === 'de' && lg.charge(racine, 'auto', 'pt-BR').langue === 'pt-br' && lg.charge(racine, 'auto', 'zh-CN').langue === 'zh-cn'
    && lg.charge(racine, 'auto', 'zh-TW').langue === 'en', lg.charge(racine, 'auto', 'pt-BR').langue);
  const ru = lg.fabrique('ru', { '{n} fichier': { one: '{n} файл', few: '{n} файла', many: '{n} файлов', other: '{n} файла' } });
  controle('pluriel par formes : le russe prend one, few, many', [1, 3, 5, 11, 21, 22, 25].map((n) => ru.N(n, '{n} fichier', '{n} fichiers')).join(' | ')
    === '1 файл | 3 файла | 5 файлов | 11 файлов | 21 файл | 22 файла | 25 файлов', ru.N(21, '{n} fichier', '{n} fichiers'));
  controle('langues livrées : le français et dix catalogues', JSON.stringify(lg.langues(racine).map((x) => x.code)) === '["fr","en","de","es","it","ja","ko","pl","pt-br","ru","zh-cn"]', lg.langues(racine));
  const en = lg.fabrique('en', lg.charge(racine, 'en').textes);
  controle('anglais : texte simple, valeurs, pluriels', en.T('Enregistrer') === 'Save' && en.T`Aperçu du plan (${3})` === 'Plan preview (3)'
    && en.N(1, '{n} fichier', '{n} fichiers') === '1 file' && en.N(4, '{n} fichier', '{n} fichiers') === '4 files'
    && en.N(2, '{n} fichier pris sur {0}', '{n} fichiers pris sur {0}', 9) === '2 files taken out of 9', [en.T('Enregistrer'), en.N(4, '{n} fichier', '{n} fichiers')]);
  controle('texte sans traduction : le français reste', en.T('Texte que le catalogue n\'a pas') === 'Texte que le catalogue n\'a pas');
  await etat['redStack.ouvrir']();
  const html = () => tousPanneaux.filter((p) => !p.jete && p.webview.html.includes('id="profil"') && p.webview.html.includes('<body>')).pop().webview.html;
  controle('page française : la fabrique part avec un catalogue vide, plus de marque à remplir', /window\.RS_L = \(function fabrique/.test(html()) && /\}\)\("fr", \{\}\);<\/script>/.test(html()) && !/\{\{/.test(html()));
  reglagesPoste.langue = 'en';
  etat.configChange({ affectsConfiguration: (k) => k === 'redStack.langue' || k === 'redStack' });
  controle('réglage passé à l\'anglais : la page est refaite avec son catalogue, la barre latérale suit',
    /\}\)\("en", \{/.test(html()) && html().includes('"Enregistrer":"Save"') && lg.enCours().langue === 'en'
    && etat.arbre.getChildren().some((x) => x.label === 'Active mods'), lg.enCours().langue);
  controle('manuel resté ouvert : refait en anglais (corps anglais, style et script gardés, plus de marque à remplir)',
    man.webview.html.includes('The idea in one minute') && !man.webview.html.includes('Le principe en une minute') && man.webview.html.includes('<html lang="en">')
    && man.webview.html.includes('acquireVsCodeApi') && man.webview.html.includes('id="lexique"') && !man.webview.html.includes('{{') && man.title === 'Red Stack · Manual', man.title);
  let refusLangue = '';
  try { await versPage({ t: 'ouvreFichier', chemin: 'Z:\\absent.reds' }); } catch (e) { refusLangue = String(e.message || e); }
  controle('message de l\'extension en anglais', recus.concat(erreurs.map((t) => ({ message: t }))).some((x) => /Not on disk: /.test(String(x.message || ''))), refusLangue);
  // le moteur reçoit la langue en cours à chaque appel : ses refus arrivent en anglais, ses états restent des codes
  const dit = async (m, a) => { try { await m.run(a); return ''; } catch (e) { return String(e.message || e); } };
  const mEn = new Moteur({ python: 'python', script: SCRIPT, donnees: DONNEES, langue: () => lg.enCours().langue });
  const refusEn = await dit(mEn, ['etat', '--profil', 'profil_absent_du_banc']);
  const etatEn = await mEn.run(['etat', '--profil', 't']);
  controle('moteur en anglais : refus traduit, états laissés en codes', /^Profile not found: /.test(refusEn) && !/introuvable/.test(refusEn)
    && etatEn.mods.length > 3 && etatEn.mods.every((r) => !/installed|disabled|parked/.test(r.etat)) && etatEn.mods.some((r) => /^(posé|coupé|à poser|jamais posé|parqué|nouveau)/.test(r.etat)),
  [refusEn, etatEn.mods.slice(0, 3).map((r) => r.etat)]);
  reglagesPoste.langue = undefined;
  etat.configChange({ affectsConfiguration: (k) => k === 'redStack.langue' || k === 'redStack' });
  controle('moteur revenu au français', /^Profil introuvable : /.test(await dit(mEn, ['etat', '--profil', 'profil_absent_du_banc'])));
  controle('réglage rendu : retour au français', lg.enCours().langue === 'fr' && /\}\)\("fr", \{\}\)/.test(html()));
  erreurs.length = 0;

  // poste sans Python : la recherche essaie le lanceur de Windows, refuse une version trop ancienne, et la page le dit
  const { cherchePython, PYTHON_MIN } = require('../moteur');
  const { EventEmitter } = require('events');
  const faux = (versions) => (commande, args) => {   // un `spawn` de théâtre : `versions` dit ce que chaque commande répond
    const p = new EventEmitter(), nom = [commande, ...args.slice(0, args.indexOf('-I'))].join(' ');
    p.stdout = Object.assign(new EventEmitter(), { setEncoding() { return this; } }); p.stderr = new EventEmitter(); p.kill = () => {};
    setImmediate(() => { if (versions[nom]) { p.stdout.emit('data', `RS ${versions[nom]}\n`); p.emit('close', 0); } else p.emit('error', new Error('spawn ENOENT')); });
    return p;
  };
  const parPy = await cherchePython('python', faux({ 'py -3': '3.12.1' }));
  controle('Python : « python » absent, le lanceur « py -3 » est pris', parPy.commande === 'py' && parPy.avant.join() === '-3' && parPy.version === '3.12.1', JSON.stringify(parPy));
  const vieux = await cherchePython('python', faux({ python: '3.7.9' }));
  controle('Python trop ancien : refusé, dit avec sa version', !vieux.commande && vieux.vieux && vieux.vieux.version === '3.7.9' && vieux.essais.length === 3, JSON.stringify(vieux));
  const regle = await cherchePython('C:\\ailleurs\\python.exe', faux({ python: '3.12.1' }));
  controle('commande réglée à la main et absente : aucune autre n\'est prise à sa place', !regle.commande && regle.essais.join() === 'C:\\ailleurs\\python.exe', JSON.stringify(regle));
  const sans = new Moteur({ python: 'python_absent_du_banc', script: SCRIPT, donnees: DONNEES });
  let refusPy = null;
  try { await sans.run(['config']); } catch (e) { refusPy = e; }
  controle('moteur sans Python : refus au code « PYTHON », message lisible (plus de plantage muet)',
    !!refusPy && refusPy.code === 'PYTHON' && /^Python introuvable \(« python_absent_du_banc »\)\.$/.test(refusPy.message), refusPy && refusPy.message);
  let nPy = recus.length;
  reglagesPoste.python = 'python_absent_du_banc';
  etat.configChange({ affectsConfiguration: (k) => k === 'redStack' });
  const ecranPy = await attend('python', nPy);
  controle('page : écran « Python introuvable » (commandes essayées, version voulue), pas de bandeau d\'erreur',
    !!ecranPy && ecranPy.essais.join() === 'python_absent_du_banc' && ecranPy.min === PYTHON_MIN.join('.') && !recus.slice(nPy).some((x) => x.t === 'erreur'), JSON.stringify(ecranPy));
  nPy = recus.length;
  reglagesPoste.python = 'python';
  etat.configChange({ affectsConfiguration: (k) => k === 'redStack' });
  const retourPy = await attend('etat', nPy);
  controle('Python revenu : la liste revient, avec ce que la convention ne lit pas', !!retourPy && retourPy.data.mods.length > 3 && !!retourPy.ecarts && Array.isArray(retourPy.ecarts.hors_piles), retourPy && JSON.stringify(retourPy.ecarts));
  erreurs.length = 0;

  ext.deactivate();
  fs.rmSync(path.join(DONNEES, 'demande.json'), { force: true });
  console.log(`\n${echecs.length ? 'ROUGE' : 'VERT'} : ${echecs.length} échec(s)` + echecs.map((x) => '\n  - ' + x).join(''));
  process.exit(echecs.length ? 1 : 0);
})().catch((e) => { console.error('ARRÊT :', e.message); process.exit(1); });
