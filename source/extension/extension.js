// Red Stack : extension VS Code. Une page (table par pile, cases par mod et par pile, détail, aperçu du plan) au-dessus
// du moteur red_stack.py. Cocher une case ne change que le PROFIL ; le jeu n'est écrit qu'après l'aperçu du plan et une
// confirmation modale, avec l'empreinte du plan vu (`applique --si-plan`) : ce qui est appliqué est ce qui a été montré.
// Les demandes d'une session Claude (serveur MCP, demande.json) passent par la même confirmation.
// Le moteur et le serveur MCP sont dans le paquet (dossier `moteur`) ; les données (config.json, profils, registre) vivent
// dans le dossier de stockage de l'extension, ou dans celui du réglage « redStack.donnees ».
'use strict';
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const { Moteur, trouveDonnees, PYTHON_MIN } = require('./moteur');
const langue = require('./langue');
const { T, N } = langue;
const nxm = require('./nxm');

const ECRIT = ['pose', 'remplace', 'retire', 'lie', 'delie'];
let ctx, moteur, telecharge, panneau, analyse, code, objets, deps, aide, barre, minuterie, veille, demandeVue = '', stable = '';
// actualisation automatique : ce que le moteur dit de veiller, la signature du disque au dernier état lu, celle en cours de contrôle
let cibles = null, vu = '', enVue = '', guets = [], guetCle = '', bientot = null, ronde = null;
let resume = null, vueVoulue = '';                  // barre latérale : chiffres du dernier état lu ; vue demandée avant que la page soit prête
const arbre = new vscode.EventEmitter();

function activate(context) {
  ctx = context;
  regleLangue();
  barre = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  barre.text = '$(layers) Red Stack';
  barre.tooltip = T('Ouvrir Red Stack');
  barre.command = 'redStack.ouvrir';
  // icône de la barre d'activité : la vue porte le profil, les chiffres du dernier état lu et les raccourcis de la page ;
  // la montrer ouvre (ou ramène) la page. Tant que rien n'est lu, le texte d'accueil de package.json tient la place.
  const vue = vscode.window.createTreeView('redStack.accueil', { treeDataProvider: { getChildren: lignesBarre, getTreeItem: (x) => x, onDidChangeTreeData: arbre.event } });
  vue.onDidChangeVisibility((e) => { if (e.visible && moteur) ouvrir(); });
  context.subscriptions.push(barre, vue,
    // page restée ouverte à la fermeture de VS Code : rouverte à sa place, avec les autres onglets
    vscode.window.registerWebviewPanelSerializer('redStack', { deserializeWebviewPanel: async (p) => (panneau ? p.dispose() : monte(p)) }),
    // l'onglet « Conflits » resté ouvert revient lui aussi, à sa place
    vscode.window.registerWebviewPanelSerializer('redStackAnalyse', { deserializeWebviewPanel: async (p) => (analyse ? p.dispose() : monte(p, true)) }),
    // et l'onglet « Scripts et tweaks »
    vscode.window.registerWebviewPanelSerializer('redStackCode', { deserializeWebviewPanel: async (p) => (code ? p.dispose() : monte(p, 'code')) }),
    // et l'onglet « Objets »
    vscode.window.registerWebviewPanelSerializer('redStackObjets', { deserializeWebviewPanel: async (p) => (objets ? p.dispose() : monte(p, 'objets')) }),
    // et l'onglet « Dépendances »
    vscode.window.registerWebviewPanelSerializer('redStackDependances', { deserializeWebviewPanel: async (p) => (deps ? p.dispose() : monte(p, 'dependances')) }),
    // et le manuel
    vscode.window.registerWebviewPanelSerializer('redStackAide', { deserializeWebviewPanel: async (p) => (aide ? p.dispose() : monteAide(p)) }),
    // retour sur la fenêtre : le disque a pu changer pendant qu'on était ailleurs
    vscode.window.onDidChangeWindowState((e) => { if (e.focused) controle(200); }),
    // lien `nxm://` rendu par Windows (bouton « Mod manager download » de Nexus), une fois Red Stack inscrit pour eux
    vscode.window.registerUriHandler({ handleUri: (u) => { if (u.path === '/nxm') recoitNxm(nxm.lienRecu(u.query)).catch(erreurNxm); } }),
    vscode.commands.registerCommand('redStack.vue', (v) => montreVue(v).catch(erreur)),
    vscode.commands.registerCommand('redStack.profilChoisir', () => choisitProfil().catch(erreur)),
    vscode.commands.registerCommand('redStack.ouvrir', ouvrir),
    vscode.commands.registerCommand('redStack.aide', (section) => ouvrirAide(typeof section === 'string' ? section : '')),
    vscode.commands.registerCommand('redStack.demande', () => traiteDemande(true)),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('workbench.colorTheme') || e.affectsConfiguration('redStack.barreEnCouleur')) envoie({ t: 'theme', data: etatTheme() });
      if (e.affectsConfiguration('redStack.barreEnCouleur')) barreEnCouleur();
      else if (e.affectsConfiguration('redStack.langue')) changeLangue();
      else if (e.affectsConfiguration('redStack')) branche();
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(branche),
    { dispose: () => { arreteVeille(); arreteGuets(); } });
  stable = copieMoteur();
  barre.show();
  branche();
  reprendDonnees();
  barreEnCouleur();
}

// Icônes de la barre d'activité en couleur (réglage « redStack.barreEnCouleur », sa demande du 17/11). Un thème n'a pas
// d'option : la couleur des icônes au repos est écrite dans les réglages de l'utilisateur (`workbench.colorCustomizations`),
// sous nos deux thèmes seuls, et retirée quand la case est décochée. Rien d'autre de ce réglage n'est touché.
const ACCENTS = { 'Red Stack Rouge': '#ff2800', 'Red Stack Jaune': '#fcee0a' };
const AU_REPOS = 'activityBar.inactiveForeground';
async function barreEnCouleur() {
  try {
    const voulu = vscode.workspace.getConfiguration('redStack').get('barreEnCouleur') === true;
    const w = vscode.workspace.getConfiguration('workbench');
    const avant = (w.inspect('colorCustomizations') || {}).globalValue || {};
    const apres = JSON.parse(JSON.stringify(avant));
    for (const [nom, accent] of Object.entries(ACCENTS)) {
      // Accent plein (son retour du 17/11 : à 65 % il était fade à côté des boutons) ; l'icône active se reconnaît à son trait.
      const cle = `[${nom}]`, teinte = accent, ancienne = accent + 'a6';   // `ancienne` : valeur écrite jusqu'à la 0.15.0
      const bloc = { ...(apres[cle] || {}) };
      if (voulu) bloc[AU_REPOS] = teinte;
      else if (bloc[AU_REPOS] === teinte || bloc[AU_REPOS] === ancienne) delete bloc[AU_REPOS];
      if (Object.keys(bloc).length) apres[cle] = bloc; else delete apres[cle];
    }
    if (JSON.stringify(apres) !== JSON.stringify(avant)) {
      await w.update('colorCustomizations', Object.keys(apres).length ? apres : undefined, vscode.ConfigurationTarget.Global);
    }
  } catch { /* réglages illisibles ou en lecture seule : la barre garde les couleurs du thème */ }
}

/** Copie le moteur et le serveur MCP à un chemin qui ne change pas d'une version à l'autre (déclaration du serveur MCP). */
function copieMoteur() {
  const de = path.join(ctx.extensionPath, 'moteur'), vers = path.join(ctx.globalStorageUri.fsPath, 'moteur');
  try {
    fs.mkdirSync(vers, { recursive: true });
    for (const f of ['red_stack.py', 'red_stack_mcp.py', 'red_stack_wk_mcp.py']) {
      const neuf = fs.readFileSync(path.join(de, f));
      const cible = path.join(vers, f);
      if (!fs.existsSync(cible) || !fs.readFileSync(cible).equals(neuf)) fs.writeFileSync(cible, neuf);
    }
    return vers;
  } catch {
    return de;
  }
}

const donneesDefaut = () => path.join(ctx.globalStorageUri.fsPath, 'donnees');

/** Premier lancement sans données : si les dossiers ouverts en portent déjà, proposer de les reprendre (une seule fois). */
async function reprendDonnees(modale) {
  const c = vscode.workspace.getConfiguration('redStack');
  if (c.get('donnees') || fs.existsSync(path.join(donneesDefaut(), 'config.json')) || ctx.globalState.get('redStack.reprise')) return;
  const trouve = trouveDonnees((vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath));
  if (!trouve) return false;
  // à l'ouverture de la page : boîte de dialogue, une notification se replie avant qu'on ait répondu
  const ok = modale
    ? await vscode.window.showInformationMessage(T('Red Stack : reprendre les données existantes ?'),
      { modal: true, detail: T`Profils, registre de pose et réglages trouvés dans :
${trouve}

Rien n'est écrit dans le jeu par ce choix.` },
      T('Utiliser ce dossier'), T('Repartir de zéro'))
    : await vscode.window.showInformationMessage(T`Red Stack : des données existent déjà dans ${trouve} (profils, registre de pose). Les utiliser ?`,
      T('Utiliser ce dossier'), T('Repartir de zéro'));
  if (ok === T('Utiliser ce dossier')) {
    if (vscode.workspace.getConfiguration('redStack').get('donnees') === trouve) return true;   // déjà répondu par l'autre voie
    await c.update('donnees', trouve, vscode.ConfigurationTarget.Global);
    branche();
    return true;
  }
  if (ok) await ctx.globalState.update('redStack.reprise', true);
  return false;
}

/** Langue de l'interface : réglage « redStack.langue », ou celle de VS Code (« auto »). Les textes sont dans `langues`. */
function regleLangue() {
  return langue.regle(ctx.extensionPath, vscode.workspace.getConfiguration('redStack').get('langue'), vscode.env.language);
}

/** Le réglage de langue a changé : la barre, la barre latérale et les onglets ouverts sont refaits dans la nouvelle langue. */
function changeLangue() {
  regleLangue();
  barre.tooltip = T('Ouvrir Red Stack');
  arbre.fire();
  for (const [p, seule] of [[panneau, false], [analyse, true], [code, 'code']]) if (p) habille(p, seule);
  if (aide) habilleAide(aide);
  if (panneau) rafraichit();
}

/** Poids lisible, dans la langue en cours (virgule ou point, Go ou GB). */
const poidsDit = (o) => (o >= 1e9 ? T`${(o / 1e9).toLocaleString(langue.enCours().langue, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Go`
  : T`${Math.max(1, Math.round(o / 1e6))} Mo`);

function deactivate() {
  arreteVeille();
  arreteGuets();
}

// ---------------------------------------------------------------- actualisation automatique
// Le moteur dit quoi veiller (`config` : piles du dépôt et leurs dossiers, archive\pc\mod, profils, registre de pose).
// Une signature (noms, tailles, dates) est prise à chaque état lu ; un guet de dossier, le retour sur la fenêtre ou une
// ronde lente la refont, et l'état n'est relu que si elle a changé ET s'est stabilisée (un zip en cours de copie attend).

function arreteGuets() {
  for (const g of guets) { try { g.close(); } catch { /* déjà fermé */ } }
  guets = []; guetCle = '';
  clearTimeout(bientot); clearInterval(ronde);
  bientot = ronde = null;
}

const autoVoulue = () => vscode.workspace.getConfiguration('redStack').get('actualisationAuto') !== false;
const PASSAGERS = /\.(tmp|part|partial|crdownload|download)$/i;

function signature() {
  if (!cibles) return '';
  const out = [];
  const pese = (f) => { try { const st = fs.statSync(f); out.push(`${f}:${st.size}:${st.mtimeMs}`); } catch { out.push(f + ':absent'); } };
  for (const d of cibles.dossiers) {
    try {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        if (e.isDirectory()) out.push(path.join(d, e.name) + path.sep);
        else if (!PASSAGERS.test(e.name)) pese(path.join(d, e.name));
      }
    } catch { out.push(d + ':absent'); }
  }
  cibles.fichiers.forEach(pese);
  return out.join('\n');
}

/** Après chaque état lu : la signature du disque devient la référence, et les guets suivent la liste du moteur. */
function poseGuets(v) {
  cibles = v || null;
  vu = signature(); enVue = '';
  if (!cibles || !autoVoulue()) return arreteGuets();
  const cle = cibles.dossiers.join('|');
  if (cle === guetCle) return;
  arreteGuets();
  guetCle = cle;
  for (const d of cibles.dossiers) {
    try { guets.push(fs.watch(d, { persistent: false }, () => controle(1500)).on('error', () => {})); } catch { /* dossier absent : la ronde le verra */ }
  }
  ronde = setInterval(() => controle(0), 30000);    // un dossier synchronisé ne prévient pas toujours
  if (ronde.unref) ronde.unref();
}

function controle(delai) {
  if (!cibles || !autoVoulue() || !(panneau || analyse || code)) return;
  clearTimeout(bientot);
  bientot = setTimeout(() => {
    if (moteur.attente) return controle(1500);       // le moteur écrit peut-être : on repasse
    const s = signature();
    if (s === vu) { enVue = ''; return; }
    if (s !== enVue) { enVue = s; return controle(1500); }   // changé : attendre qu'il ne bouge plus
    rafraichit(0, true);
  }, delai);
}

/** (Re)crée le moteur d'après les réglages du poste (commande Python, dossier des données). */
function branche() {
  arreteVeille();
  const c = vscode.workspace.getConfiguration('redStack');
  const script = c.get('moteur') || path.join(ctx.extensionPath, 'moteur', 'red_stack.py');
  moteur = new Moteur({ python: c.get('python'), script, donnees: c.get('donnees') || donneesDefaut(), langue: () => langue.enCours().langue, occupe: (n) => envoie({ t: 'occupe', n }) });
  // file à part pour les téléchargements Nexus : un gros zip ne fige pas la page pendant qu'il arrive
  telecharge = new Moteur({ python: c.get('python'), script, donnees: moteur.donnees, langue: () => langue.enCours().langue });
  if (!autoVoulue()) arreteGuets();
  if (panneau) rafraichit();
  const f = path.join(moteur.donnees, 'demande.json');
  veille = f;                                       // sondage : un dossier synchronisé ne prévient pas toujours
  fs.watchFile(f, { interval: 1500 }, () => traiteDemande(false));
  traiteDemande(false);
}

function arreteVeille() {
  if (veille) fs.unwatchFile(veille);
  veille = null;
}

const profil = () => ctx.workspaceState.get('redStack.profil', 'actuel');
// la page et la fenêtre d'analyse reçoivent les mêmes messages ; chacune ne garde que ce qui la regarde
const envoie = (m) => { for (const p of [panneau, analyse, code, objets, deps]) if (p) p.webview.postMessage(m); };
const erreur = (e) => {
  const message = String((e && e.message) || e);
  if (e && e.code === 'PYTHON') {                   // poste sans Python : un écran qui dit quoi faire, pas un bandeau
    envoie({ t: 'python', essais: e.essais, vieux: e.vieux, min: PYTHON_MIN.join('.'), voulu: vscode.workspace.getConfiguration('redStack').get('python') || 'python' });
    if (!panneau) vscode.window.showErrorMessage(`${T('Red Stack :')} ` + message);
    return;
  }
  envoie({ t: 'erreur', message });
  if (!panneau) vscode.window.showErrorMessage(`${T('Red Stack :')} ` + message);
};

function ouvrir() {
  if (panneau) return panneau.reveal();
  monte(vscode.window.createWebviewPanel('redStack', 'Red Stack', vscode.ViewColumn.Active,
    { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] }));
}

/** Analyse des conflits dans un onglet à elle : il se pose à côté, et se détache en fenêtre (« Déplacer dans une nouvelle fenêtre »). */
function ouvrirAnalyse(cle = '') {
  if (analyse) {                                    // déjà ouverte : ramenée devant, recentrée sur le mod demandé
    analyse.reveal();
    return analyse.webview.postMessage({ t: 'conflitsCible', cle });
  }
  monte(vscode.window.createWebviewPanel('redStackAnalyse', T('Red Stack · Conflits'), vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] }), true, cle);
}

/** Conflits de code (« Scripts et tweaks ») : un troisième onglet, rangé avec celui des conflits d'archives. */
function ouvrirCode() {
  if (code) return code.reveal();
  monte(vscode.window.createWebviewPanel('redStackCode', T('Red Stack · Scripts et tweaks'), (analyse && analyse.viewColumn) || vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] }), 'code');
}

/** Objets des mods face à une sauvegarde de partie : un quatrième onglet, rangé avec les analyses. */
function ouvrirObjets() {
  if (objets) return objets.reveal();
  monte(vscode.window.createWebviewPanel('redStackObjets', T('Red Stack · Objets'), (analyse && analyse.viewColumn) || (code && code.viewColumn) || vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] }), 'objets');
}

/** Chaîne des prérequis d'un mod, en liste ou en graphe : un cinquième onglet, rangé avec les analyses.
 *  `cle` = « clé du zip|sens » (sens : chute ou besoin) ; vide = la liste des socles. */
function ouvrirDependances(cle = '') {
  if (deps) {
    deps.reveal();
    return cle ? deps.webview.postMessage({ t: 'conflitsCible', cle }) : undefined;
  }
  monte(vscode.window.createWebviewPanel('redStackDependances', T('Red Stack · Dépendances'), (analyse && analyse.viewColumn) || (objets && objets.viewColumn) || vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] }), 'dependances', cle);
}

/** Manuel : une page d'aide statique (`media/aide.html`, corps anglais dans `media/aide.en.html`) dans un onglet à elle ; `section` = l'ancre à montrer. */
function ouvrirAide(section = '') {
  if (!aide) {
    monteAide(vscode.window.createWebviewPanel('redStackAide', T('Red Stack · Manuel'), vscode.ViewColumn.Beside,
      { enableScripts: true, enableFindWidget: true, retainContextWhenHidden: true, localResourceRoots: [] }));
  } else aide.reveal();
  if (section) aide.webview.postMessage({ t: 'section', id: section });
}

function monteAide(p) {
  aide = p;
  p.webview.options = { enableScripts: true, localResourceRoots: [] };
  p.iconPath = new vscode.ThemeIcon('book');
  p.onDidDispose(() => { if (aide === p) aide = null; });
  p.webview.onDidReceiveMessage((m) => { if (m && m.t === 'ouvrir') ouvrir(); });
  habilleAide(p);
}

/** Écrit le manuel dans son onglet : `media/aide.html` en français ; dans toute autre langue, son corps (entre les deux
 *  repères « corps ») est remplacé par celui de `media/aide.en.html`. Style et script n'existent qu'une fois. */
function habilleAide(p) {
  const lu = (f) => fs.readFileSync(path.join(ctx.extensionPath, 'media', f), 'utf8');
  let html = lu('aide.html');
  if (langue.enCours().langue !== 'fr') {
    const a = html.indexOf('<!-- corps -->'), b = html.indexOf('<!-- /corps -->');
    let corps = '';
    try { corps = lu('aide.en.html'); } catch { /* paquet sans manuel anglais : le français reste */ }
    if (corps && a > 0 && b > a) {
      html = (html.slice(0, a) + corps + html.slice(b)).replace('<html lang="fr">', '<html lang="en">').replace('<title>Red Stack · Manuel</title>', '<title>Red Stack · Manual</title>');
    }
  }
  const nonce = [...Array(32)].map(() => Math.floor(Math.random() * 36).toString(36)).join('');
  p.title = T('Red Stack · Manuel');
  p.webview.html = html.replace(/\{\{nonce\}\}/g, nonce).replace(/\{\{version\}\}/g, String(ctx.extension ? ctx.extension.packageJSON.version : ''));
}

/** Thème de couleurs et icônes de la barre d'activité, depuis la page « Réglages » : écrit les réglages de l'utilisateur, tout de suite. */
const etatTheme = () => ({ theme: vscode.workspace.getConfiguration('workbench').get('colorTheme') || '',
  barre: vscode.workspace.getConfiguration('redStack').get('barreEnCouleur') === true, themes: Object.keys(ACCENTS) });
async function regleTheme(m) {
  if (m.nom && ACCENTS[m.nom]) await vscode.workspace.getConfiguration('workbench').update('colorTheme', m.nom, vscode.ConfigurationTarget.Global);
  if (typeof m.barre === 'boolean') {                 // déclenche barreEnCouleur() par le changement de réglage
    await vscode.workspace.getConfiguration('redStack').update('barreEnCouleur', m.barre || undefined, vscode.ConfigurationTarget.Global);
  }
  if (m.choisir) return void vscode.commands.executeCommand('workbench.action.selectTheme');
  envoie({ t: 'theme', data: etatTheme() });
}

/** Branche la page sur un onglet : celui qu'on vient de créer, ou celui que VS Code rouvre à son démarrage.
 *  `seule` : la même page, réduite à l'analyse des conflits (classe `analyse` du corps) ; 'code' : aux conflits de code. */
function monte(p, seule = false, cle = '') {
  if (seule === 'code') code = p; else if (seule === 'objets') objets = p; else if (seule === 'dependances') deps = p; else if (seule) analyse = p; else panneau = p;
  p.webview.options = { enableScripts: true, localResourceRoots: [] };
  p.iconPath = new vscode.ThemeIcon(seule === 'code' ? 'code' : seule === 'objets' ? 'package' : seule === 'dependances' ? 'type-hierarchy' : seule ? 'git-compare' : 'layers');
  p.onDidDispose(() => { if (panneau === p) panneau = null; if (analyse === p) analyse = null; if (code === p) code = null; if (objets === p) objets = null; if (deps === p) deps = null; });
  if (p.onDidChangeViewState) p.onDidChangeViewState((e) => { if (e.webviewPanel.visible) controle(200); });
  p.webview.onDidReceiveMessage((m) => recoitGarde(m).catch(erreur));
  habille(p, seule, cle);
}

/** Écrit la page dans l'onglet, dans la langue en cours (le catalogue part avec elle). */
function habille(p, seule = false, cle = '') {
  const nonce = [...Array(32)].map(() => Math.floor(Math.random() * 36).toString(36)).join('');
  p.title = seule === 'code' ? T('Red Stack · Scripts et tweaks') : seule === 'objets' ? T('Red Stack · Objets') : seule === 'dependances' ? T('Red Stack · Dépendances') : seule ? T('Red Stack · Conflits') : 'Red Stack';
  p.webview.html = fs.readFileSync(path.join(ctx.extensionPath, 'media', 'page.html'), 'utf8')
    .replace(/\{\{nonce\}\}/g, nonce).replace('{{langue}}', () => langue.pourPage(langue.enCours()))
    .replace('<body>', seule ? `<body class="analyse${seule === 'code' ? ' code' : seule === 'objets' ? ' objets' : seule === 'dependances' ? ' dependances' : ''}" data-cle="${cle.replace(/[&"<>]/g, (c) => '&#' + c.charCodeAt(0) + ';')}">` : '<body>');
}

/** Lignes de la barre latérale : profil, chiffres du dernier état lu, raccourcis vers les vues de la page. */
function lignesBarre() {
  if (!resume) return [];
  const ligne = (texte, description, icone, commande, arg, aide) => {
    const i = new vscode.TreeItem(texte, vscode.TreeItemCollapsibleState.None);
    i.description = description; i.iconPath = new vscode.ThemeIcon(icone); i.tooltip = aide || `${texte} ${description || ''}`.trim();
    if (commande) i.command = { command: commande, title: texte, arguments: arg === undefined ? [] : [arg] };
    return i;
  };
  const r = resume, c = r.conflits;
  const out = [
    ligne(T('Profil'), r.profil, 'account', 'redStack.profilChoisir', undefined, T('Changer de profil')),
    ligne(T('Mods actifs'), T`${r.actifs} sur ${r.total}`, 'layers', 'redStack.vue', 'liste', T('Ouvrir la liste des mods')),
  ];
  if (r.attente) out.push(ligne(T('À appliquer'), N(r.attente, '{n} mod', '{n} mods'), 'warning', 'redStack.vue', 'plan', T("Des mods attendent « Appliquer » : ouvrir l'aperçu du plan")));
  if (r.neufs) out.push(ligne(T('Nouveaux dans le dépôt'), String(r.neufs), 'sparkle', 'redStack.vue', 'liste', T('Zips arrivés dans une pile, pas encore cochés')));
  if (r.conflitsPlan) out.push(ligne(T('Conflits de fichiers à trancher'), String(r.conflitsPlan), 'error', 'redStack.vue', 'plan'));
  out.push(ligne(T("Conflits d'archives"), c ? T`${N(c.en_conflit, '{n} ressource', '{n} ressources')}, ${N(c.paires, '{n} paire', '{n} paires')}` : T('lecture…'), 'git-compare', 'redStack.vue', 'conflits', T("Ouvrir l'analyse des conflits")));
  out.push(ligne(T('Scripts et tweaks'), T('conflits de code'), 'code', 'redStack.vue', 'code', T("Ouvrir l'analyse des conflits de code (lue à l'ouverture)")));
  out.push(ligne(T('Objets'), T('face à une sauvegarde'), 'package', 'redStack.vue', 'objets', T('Objets des mods (armes, vêtements, implants, accessoires d\'armes, mods d\'équipement) : ce qui sert dans une sauvegarde de partie, et ce qui ne sert pas')));
  out.push(ligne(T('Dépendances'), T('chaîne des prérequis'), 'type-hierarchy', 'redStack.vue', 'dependances', T("Ce qui ne se charge plus si un mod part, et tout ce qu'il lui faut : en liste ou en graphe")));
  if (r.demande) out.push(ligne(T("Demande d'une session Claude"), T('en attente'), 'bell', 'redStack.demande'));
  out.push(ligne(T('Aperçu du plan'), '', 'checklist', 'redStack.vue', 'plan'), ligne(T('Arrivages'), '', 'inbox', 'redStack.vue', 'arrivages'),
    ligne(T('Mises à jour'), 'Nexus', 'cloud-download', 'redStack.vue', 'maj', T('Chercher sur Nexus les nouvelles versions des zips du dépôt, les télécharger')),
    ligne(T('Historique'), '', 'history', 'redStack.vue', 'historique'),
    ligne(T('Magasin'), T('liens et poids réel'), 'database', 'redStack.vue', 'magasin', T('État des liens, poids réel sur le disque, arbres à purger, retouches')),
    ligne(T('Réglages'), '', 'gear', 'redStack.vue', 'reglages'), ligne(T('Actualiser'), '', 'refresh', 'redStack.vue', 'actualise'),
    ligne(T('Manuel'), '', 'book', 'redStack.aide', undefined, T('Le manuel de Red Stack, vue par vue')));
  return out;
}

/** Raccourci de la barre latérale : la page vient devant, puis montre la vue demandée (dès qu'elle est prête). */
async function montreVue(v) {
  if (v === 'conflits') return ouvrirAnalyse();
  if (v === 'code') return ouvrirCode();
  if (v === 'objets') return ouvrirObjets();
  if (v === 'dependances') return ouvrirDependances();
  const prete = !!panneau;
  ouvrir();
  if (v === 'actualise') return prete ? rafraichit() : undefined;
  if (v === 'liste') return;
  if (prete) envoie({ t: 'vue', v }); else vueVoulue = v;
}

async function choisitProfil() {
  const p = (await moteur.run(['profils'])).profils;
  const ok = await vscode.window.showQuickPick(p.map((x) => ({ label: x.nom, description: x.nom === profil() ? T('profil courant') : '', v: x.nom })),
    { title: T('Profil Red Stack'), placeHolder: T('Changer de profil ne change que ce que la page montre ; le jeu suit à « Appliquer ».') });
  if (!ok || ok.v === profil()) return;
  await ctx.workspaceState.update('redStack.profil', ok.v);
  ouvrir();
  return rafraichit();
}

function demandeEnAttente() {
  try {
    return JSON.parse(fs.readFileSync(path.join(moteur.donnees, 'demande.json'), 'utf8')).etat === 'attente';
  } catch {
    return false;
  }
}

/** État complet (mods, profils) vers la page ; regroupe les demandes rapprochées (une rafale de cases). */
function rafraichit(delai = 0, auto = false) {
  clearTimeout(minuterie);
  minuterie = setTimeout(async () => {
    try {
      const conf = await moteur.run(['config']);
      if (!conf.depot || !conf.jeu || !conf.existe.depot || !conf.existe.jeu) {   // rien à lire tant que ces deux dossiers manquent
        if (await reprendDonnees(true)) return;       // des données existent dans les dossiers ouverts : les reprendre d'abord
        return envoie({ t: 'reglages', data: conf, poste: poste(), premier: true });
      }
      const p = await moteur.run(['profils']);
      if (!p.profils.length) return envoie({ t: 'aucunProfil', ecarts: conf.ecarts });
      if (!p.profils.some((x) => x.nom === profil())) {          // profil supprimé, ou premier lancement
        const repli = p.profils.find((x) => x.nom === 'actuel') || p.profils[0];
        await ctx.workspaceState.update('redStack.profil', repli.nom);
      }
      const et = await moteur.run(['etat', '--profil', profil()]);
      envoie({ t: 'etat', data: et, profils: p.profils, auto, veille: autoVoulue(), ecarts: conf.ecarts });
      poseGuets(conf.veille);
      const piles = et.mods.filter((x) => !x.lieu);
      resume = { profil: profil(), actifs: piles.filter((x) => x.actif).length, total: piles.length, conflits: null, demande: demandeEnAttente(),
        attente: piles.filter((x) => /^à /.test(x.etat)).length, neufs: piles.filter((x) => x.etat === 'nouveau dans le dépôt').length,
        conflitsPlan: (et.conflits || []).length };
      arbre.fire();
      if (vueVoulue) { envoie({ t: 'vue', v: vueVoulue }); vueVoulue = ''; }
      // conflits d'archives du profil, à la suite : pastilles de la liste et vue d'analyse (lecture seule)
      moteur.run(['conflits', '--profil', profil()]).then((data) => {
        envoie({ t: 'conflits', data });
        if (resume) { resume.conflits = data.compte; arbre.fire(); }
      }, () => {});
    } catch (e) {
      erreur(e);
    }
  }, delai);
}

// Gestes qui écrivent le dépôt, le magasin ou le jeu : de leur confirmation à leur fin, la page est verrouillée (message
// `verrou`), et tout autre geste qui écrit ou qui change le profil est refusé, d'où qu'il vienne (page, onglets d'analyse).
const GESTES_ECRIT = new Set(['adopte', 'deplace', 'deplaceLot', 'supprime', 'conventionRange', 'conventionRenomme', 'conventionConvertit', 'conventionConvertitLot', 'contenuRenomme', 'contenuRenommeLot', 'zipRenomme',
  'purge', 'retoucheAnnule', 'applique']);
const CHANGE = new Set(['profilNouveau', 'profilSupprime', 'bascule', 'basculeLot', 'option', 'priorite', 'fomodFixe', 'nomsFixe', 'ordrePasse', 'ordreRenomme',
  'ordreAnnule', 'ordreModlistStop', 'planRemplace', 'reglagesEcrit', 'reference', 'sauvegarde', 'majTelecharge']);
let verrou = '';
// Fichiers présents dans le jeu, pas posés par Red Stack, que l'utilisateur a désignés dans le plan pour être remplacés par
// ceux du zip : gardés le temps de la session, passés à chaque plan et à l'application, vidés après un « Appliquer ».
const aRemplacer = new Set();
const argsRemplace = () => [...aRemplacer].flatMap((d) => ['--remplace', d]);
async function recoitGarde(m) {
  if (verrou && m && (GESTES_ECRIT.has(m.t) || CHANGE.has(m.t))) throw new Error(T('Red Stack écrit encore : attendre la fin du geste en cours.'));
  if (!m || !GESTES_ECRIT.has(m.t)) return recoit(m);
  verrou = m.t;
  envoie({ t: 'verrou', on: true });
  try { return await recoit(m); } finally { verrou = ''; envoie({ t: 'verrou', on: false }); }
}
async function recoit(m) {
  const P = ['--profil', profil()];
  switch (m.t) {
    case 'pret':
    case 'actualise':
      return rafraichit();
    case 'pythonSite':                              // écran « Python introuvable » : la page des téléchargements
      return void vscode.env.openExternal(vscode.Uri.parse('https://www.python.org/downloads/'));
    case 'pythonCommande': {                        // ... ou la commande à utiliser, dite à la main (réglage du poste)
      const c = vscode.workspace.getConfiguration('redStack');
      const v = await vscode.window.showInputBox({ title: T('Red Stack : commande Python'), value: c.get('python') || 'python', ignoreFocusOut: true,
        prompt: T('Commande ou chemin complet de python.exe (3.11 ou plus récent). Vide = « python ».') });
      if (v === undefined) return;
      await c.update('python', v.trim() || undefined, vscode.ConfigurationTarget.Global);
      branche();                                    // sans changement de valeur, VS Code ne prévient pas : on rebranche ici
      return;
    }
    case 'pythonEncore':
      return rafraichit();
    case 'adopte':                                  // premier lancement : lit le jeu, n'y écrit rien
      await moteur.run(['adopte', '--profil', 'actuel']);
      await ctx.workspaceState.update('redStack.profil', 'actuel');
      return rafraichit();
    case 'profil':
      await ctx.workspaceState.update('redStack.profil', m.nom);
      return rafraichit();
    case 'profilNouveau': {
      const nom = await vscode.window.showInputBox({
        title: T`Nouveau profil, copie de « ${profil()} »`, prompt: T('Nom du profil'),
        validateInput: (v) => (/^[\w .\-]{1,60}$/.test(v) ? null : T('Lettres, chiffres, espaces, points et tirets, 60 au plus')),
      });
      if (!nom) return;
      await moteur.run(['profils', '--profil', nom, '--copie', profil()]);
      await ctx.workspaceState.update('redStack.profil', nom);
      return rafraichit();
    }
    case 'profilSupprime': {
      const nom = profil();
      const ok = await vscode.window.showWarningMessage(T`Supprimer le profil « ${nom} » ?`,
        { modal: true, detail: T('Le jeu ne change pas : seul le fichier du profil est supprimé.') }, T('Supprimer'));
      if (ok !== T('Supprimer')) return;
      await moteur.run(['profils', '--profil', nom, '--supprime']);
      return rafraichit();
    }
    case 'basculeLot':                              // les cases cochées à la suite dans la page : jouées dans l'ordre, UN seul état relu à la fin
      try {
        for (const [cle, valeur] of m.mods || []) await moteur.run(['bascule', valeur ? 'on' : 'off', ...P, '--mod', cle]);
      } finally { envoie({ t: 'basculeFait' }); }
      return rafraichit(250);
    case 'supprime': {                              // un zip des retirés part à la corbeille du système ; rien d'autre ne se supprime d'ici
      const et = await moteur.run(['etat', ...P]);
      const lignes = (m.cles || []).map((k) => et.mods.find((x) => x.cle === k)).filter((r) => r && r.lieu && r.genre === 'retiré');
      if (!lignes.length) throw new Error(T('Aucun zip retiré à supprimer.'));
      const n = lignes.length;
      const ok = await confirme(N(n, 'Supprimer {n} zip ?', 'Supprimer {n} zips ?'), N(n, 'Supprimer {n} zip', 'Supprimer {n} zips'),
        lignes.slice(0, 3).map((r) => r.nom.replace(/\.zip$/i, '')).join(' · ') + (n > 3 ? ` · ${N(n - 3, '… et {n} autre', '… et {n} autres')}` : ''),
        T('Entrée = ne rien supprimer. Les zips quittent le dépôt pour la corbeille de Windows.'));
      if (!ok) return;
      for (const r of lignes) {
        await vscode.workspace.fs.delete(vscode.Uri.file(r.zip), { useTrash: true });
        await moteur.run(['journal', '--supprime', '--de', r.zip]);   // le moteur tient l'historique : il inscrit ce que l'extension vient de faire
      }
      vscode.window.showInformationMessage(N(n, '{n} zip supprimé.', '{n} zips supprimés.'));
      return rafraichit();
    }
    case 'bascule':
      await moteur.run(['bascule', m.valeur ? 'on' : 'off', ...P, ...(m.section ? ['--section', m.section] : ['--mod', m.cle])]);
      return rafraichit(250);
    case 'option':
      await moteur.run(['option', m.valeur ? 'on' : 'off', ...P, '--mod', m.cle, ...(m.entree ? ['--entree', m.entree] : ['--nom', m.nom || 'direct']), ...(m.mien ? ['--mien'] : [])]);
      envoie({ t: 'detail', data: await moteur.run(['detail', ...P, '--mod', m.cle]) });
      return rafraichit(250);
    case 'priorite':
      if (m.fichier) await moteur.run(['priorite', ...P, '--gagnant', m.gagnant, '--fichier', m.fichier, ...(m.oublie ? ['--annule'] : [])]);
      else for (const perdant of m.perdants) await moteur.run(['priorite', ...P, '--gagnant', m.gagnant, '--perdant', perdant, ...(m.oublie ? ['--annule'] : [])]);
      if (m.retour === 'detail') envoie({ t: 'detail', data: await moteur.run(['detail', ...P, '--mod', m.gagnant]) });
      else envoie({ t: 'plan', data: await moteur.run(['plan', ...P, ...argsRemplace()]) });
      return rafraichit(250);
    case 'detail':
      return envoie({ t: 'detail', data: await moteur.run(['detail', ...P, '--mod', m.cle]) });
    case 'prerequisIgnore':                         // « ce prérequis ne compte pas pour ce mod » : noté aux réglages, réversible
      await moteur.run(['prerequis', m.valeur ? 'on' : 'off', ...P, '--cle', m.cle, '--ignore', '--requis', m.requis]);
      envoie({ t: 'detail', data: await moteur.run(['detail', ...P, '--mod', m.cle]) });
      return rafraichit(250);
    case 'prerequisLit': {                          // prérequis déclarés sur Nexus, pour ce mod seul : un appel, sans clé d'API
      const r = await moteur.run(['prerequis', ...P, '--mod', m.cle, '--nexus']);
      if (r.erreur) vscode.window.showWarningMessage(r.erreur);
      envoie({ t: 'detail', data: await moteur.run(['detail', ...P, '--mod', m.cle]) });
      return rafraichit(250);
    }
    case 'fichier':
      return envoie({ t: 'fichier', nom: m.nom, data: await moteur.run(['fichier', '--nom', m.nom]) });
    case 'plan':
      return envoie({ t: 'plan', data: await moteur.run(['plan', ...P, ...argsRemplace()]) });
    case 'deplace': {                               // parquer / remonter : écrit le dépôt, toujours confirmé
      gardeMaj(m.cle);
      const vu = await moteur.run(['deplace', ...P, '--cle', m.cle, '--vers', m.vers]);   // sans --go : dit la cible, ou refuse
      const nom = m.cle.split('/').pop().replace(/\.zip$/i, '');
      const haut = m.vers === 'pile', sort = m.vers === 'retires';
      const ok = await confirme(haut ? T`Remonter « ${nom} » ?` : sort ? T`Retirer « ${nom} » ?` : T`Parquer « ${nom} » ?`, haut ? T('Remonter le zip') : sort ? T('Retirer le zip') : T('Parquer le zip'), T`vers ${path.dirname(vu.vers)}`,
        haut ? T('Entrée = ne rien écrire. Remonté, il revient comme un zip nouveau ; le jeu ne change qu\'au prochain « Appliquer ».')
          : sort ? T('Entrée = ne rien écrire. Retiré, le zip passe dans le dossier des retirés de sa pile : rien n\'est effacé, il se remonte depuis le filtre « Retirés ».')
          : T('Entrée = ne rien écrire. Parqué, le zip change de dossier ; ses choix restent au profil pour son retour.'));
      if (!ok) return;
      await moteur.run(['deplace', ...P, '--cle', m.cle, '--vers', m.vers, '--go']);
      if (m.retour === 'convention') envoie({ t: 'convention', data: await moteur.run(['convention']) });
      return rafraichit();
    }
    case 'deplaceLot': {                            // remonter, parquer ou retirer les zips cochés : une seule confirmation
      const haut = m.vers === 'pile', sort = m.vers === 'retires', prets = [], refus = [];
      for (const cle of m.cles) {                     // sans --go : chaque zip dit sa cible, ou son refus
        try { gardeMaj(cle); prets.push({ cle, vu: await moteur.run(['deplace', ...P, '--cle', cle, '--vers', m.vers]) }); }
        catch (e) { refus.push(`${cle.split('/').pop()} : ${String((e && e.message) || e).split('\n')[0]}`); }
      }
      const rien = refus.join(' ; ') || T('rien de coché');
      if (!prets.length) throw new Error(haut ? T`Aucun zip à remonter : ${rien}` : sort ? T`Aucun zip à retirer : ${rien}` : T`Aucun zip à parquer : ${rien}`);
      const n = prets.length;
      const ok = await confirme(haut ? N(n, 'Remonter {n} zip ?', 'Remonter {n} zips ?') : sort ? N(n, 'Retirer {n} zip ?', 'Retirer {n} zips ?') : N(n, 'Parquer {n} zip ?', 'Parquer {n} zips ?'),
        haut ? N(n, 'Remonter {n} zip', 'Remonter {n} zips') : sort ? N(n, 'Retirer {n} zip', 'Retirer {n} zips') : N(n, 'Parquer {n} zip', 'Parquer {n} zips'),
        prets.slice(0, 3).map((x) => x.cle.split('/').pop().replace(/\.zip$/i, '')).join(' · ') + (n > 3 ? ` · ${N(n - 3, '… et {n} autre', '… et {n} autres')}` : ''),
        (haut ? T('Entrée = ne rien écrire. Remontés, ils reviennent comme des zips nouveaux ; le jeu ne change qu\'au prochain « Appliquer ».')
          : sort ? T('Entrée = ne rien écrire. Retirés, les zips passent dans le dossier des retirés de leur pile : rien n\'est effacé.')
            : T('Entrée = ne rien écrire. Parqués, les zips changent de dossier dans leur pile.'))
        + (refus.length ? ` ${T`Laissés de côté : ${refus.length}.`}` : ''));
      if (!ok) return;
      for (const x of prets) await moteur.run(['deplace', ...P, '--cle', x.cle, '--vers', m.vers, '--go']);
      const dit = (haut ? N(n, '{n} zip remonté.', '{n} zips remontés.') : sort ? N(n, '{n} zip retiré.', '{n} zips retirés.') : N(n, '{n} zip parqué.', '{n} zips parqués.')) + (refus.length ? ` ${T`Laissés : ${refus.join(' ; ')}`}` : '');
      if (m.retour === 'liste') vscode.window.showInformationMessage(dit);   // demandé depuis la liste : la vue « Arrivages » n'est pas ouverte
      else envoie({ t: 'convention', data: await moteur.run(['convention']), dit });
      return rafraichit();
    }
    case 'maj':                                     // mises à jour : chaque zip comparé à Nexus, lecture seule
      return envoieMaj(m.frais && !majEnCours);
    case 'majCle': {                                // clé d'API personnelle : saisie dans VS Code, gardée dans son coffre
      const cle = await vscode.window.showInputBox({ title: T('Clé d\'API Nexus Mods'), password: true, ignoreFocusOut: true,
        prompt: T('Sur nexusmods.com : « Site preferences », onglet « API keys », puis TOUT EN BAS de la page, sous les dizaines d\'applications listées : « Personal API Key ». Gardée dans le coffre de VS Code, jamais dans un fichier. Vide : oublier la clé.') });
      if (cle === undefined) return;
      if (cle.trim()) await ctx.secrets.store(CLE_NEXUS, cle.trim()); else await ctx.secrets.delete(CLE_NEXUS);
      return envoieMaj(false, cle.trim() ? '' : T('Clé oubliée.'));
    }
    case 'majPageCle':                              // la page des clés du compte Nexus, dans le navigateur
      return void vscode.env.openExternal(vscode.Uri.parse('https://next.nexusmods.com/settings/api-keys'));
    case 'majIgnore':
      if (majEnCours) throw new Error(MAJ_OCCUPEE());
      await moteur.run(['nexus', m.valeur ? 'on' : 'off', '--cle', m.cle, '--ignore']);
      return envoieMaj();
    case 'majTelecharge':
      return telechargeMaj(m.lignes || []);
    case 'nxmEtat':                                 // programme des liens nxm:// : état lu dans le registre (lecture seule)
      return envoie({ t: 'nxm', data: await etatNxm() });
    case 'nxmInscrit':
    case 'nxmRetire':
      return inscritNxm(m.t === 'nxmInscrit');
    case 'conventionRange': {                       // un arrivage est la mise à jour d'un zip en place : il prend sa place
      gardeMaj(m.de);
      const args = ['convention', '--range', '--cle', m.cle, '--de', m.de].concat(m.nom ? ['--nom', m.nom] : [], m.designe ? ['--designe'] : []);
      const vu = await moteur.run(args);              // sans --go : dit les cibles, ou refuse
      const ok = await confirme(T`Ranger « ${path.basename(vu.arrivage)} » à la place de l'ancienne version ?`, T('Ranger la mise à jour'),
        T`${path.basename(vu.vers)} · l'ancienne part dans ${path.basename(path.dirname(vu.ancienne_vers))}`,
        T('Entrée = ne rien écrire. Le profil suit la nouvelle version ; le jeu ne change qu\'au prochain « Appliquer ».'));
      if (!ok) return;
      await moteur.run(args.concat(['--go']));
      envoie({ t: 'convention', data: await moteur.run(['convention']), dit: T`Rangé : ${path.basename(vu.vers)}. Lire l'aperçu du plan, puis appliquer.` });
      return rafraichit();
    }
    case 'convention':                              // arrivages : noms proposés d'après Nexus, lecture seule
      return envoie({ t: 'convention', data: await moteur.run(['convention'].concat(m.frais ? ['--force'] : [])) });
    case 'conventionRenomme': {                     // renomme les archives cochées, aux noms retouchés dans la page
      const vu = await moteur.run(['convention', '--fixe', '-'], JSON.stringify(m.noms));   // sans --go : contrôle, ou refuse
      const n = vu.renommes.length;
      if (!n) return envoie({ t: 'convention', data: await moteur.run(['convention']), dit: T('Rien à renommer : ces noms sont déjà en place.') });
      const ok = await confirme(N(n, 'Renommer {n} archive du dépôt ?', 'Renommer {n} archives du dépôt ?'), N(n, 'Renommer {n} archive', 'Renommer {n} archives'),
        vu.renommes.slice(0, 3).map((r) => path.basename(r.vers)).join(' · ') + (n > 3 ? ` · ${N(n - 3, '… et {n} autre', '… et {n} autres')}` : ''),
        T('Entrée = ne rien écrire. Seul le nom du fichier change : le contenu et le jeu ne sont pas touchés.'));
      if (!ok) return;
      await moteur.run(['convention', '--fixe', '-', '--go'], JSON.stringify(m.noms));
      envoie({ t: 'convention', data: await moteur.run(['convention']), dit: N(n, '{n} archive renommée.', '{n} archives renommées.') });
      return rafraichit();
    }
    case 'conventionConvertit': {                   // .7z / .rar -> .zip, l'original supprimé après contrôle du zip
      const vu = await moteur.run(['convention', '--convertit', '--cle', m.cle]);
      const ok = await confirme(T`Convertir « ${path.basename(vu.de)} » en .zip ?`, T('Convertir en .zip'), T`par ${vu.outil}`,
        T('Entrée = ne rien écrire. Le zip est écrit à côté, relu, puis l\'archive d\'origine est supprimée.'));
      if (!ok) return;
      const r = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : conversion en .zip…') },
        () => moteur.run(['convention', '--convertit', '--cle', m.cle, '--go']));
      envoie({ t: 'convention', data: await moteur.run(['convention']), dit: T`Converti : ${path.basename(r.vers)} (${r.fichiers} fichiers).` });
      return rafraichit();
    }
    case 'conventionConvertitLot': {                // les .7z / .rar cochés -> .zip, une seule confirmation
      const prets = [], refus = [];
      for (const cle of m.cles || []) {               // sans --go : chaque archive dit son outil, ou son refus
        try { prets.push({ cle, vu: await moteur.run(['convention', '--convertit', '--cle', cle]) }); }
        catch (e) { refus.push(`${cle.split('/').pop()} : ${String((e && e.message) || e).split('\n')[0]}`); }
      }
      if (!prets.length) throw new Error(T`Aucune archive à convertir : ${refus.join(' ; ') || T('rien de coché')}`);
      const n = prets.length;
      const ok = await confirme(N(n, 'Convertir {n} archive en .zip ?', 'Convertir {n} archives en .zip ?'), N(n, 'Convertir {n} archive', 'Convertir {n} archives'),
        prets.slice(0, 3).map((x) => path.basename(x.vu.de)).join(' · ') + (n > 3 ? ` · ${N(n - 3, '… et {n} autre', '… et {n} autres')}` : ''),
        T('Entrée = ne rien écrire. Le zip est écrit à côté, relu, puis l\'archive d\'origine est supprimée.') + (refus.length ? ` ${T`Laissés de côté : ${refus.length}.`}` : ''));
      if (!ok) return;
      let faits = 0;
      await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : conversion en .zip…') }, async (avance) => {
        for (const x of prets) {                      // une archive qui échoue ne retient pas les suivantes
          if (avance) avance.report({ message: `${faits + refus.length + 1} / ${m.cles.length} · ${path.basename(x.vu.de)}`, increment: 100 / prets.length });
          try { await moteur.run(['convention', '--convertit', '--cle', x.cle, '--go']); faits += 1; }
          catch (e) { refus.push(`${x.cle.split('/').pop()} : ${String((e && e.message) || e).split('\n')[0]}`); }
        }
      });
      envoie({ t: 'convention', data: await moteur.run(['convention']), dit: N(faits, '{n} archive convertie en .zip.', '{n} archives converties en .zip.') + (refus.length ? ` ${T`Laissés : ${refus.join(' ; ')}`}` : '') });
      return rafraichit();
    }
    case 'contenu':                                 // contenu d'un zip : plan de renommage, lecture seule (index des références)
      return envoie({ t: 'contenu', cle: m.cle, data: await moteur.run(['contenu', '--cle', m.cle].concat(m.nom ? ['--nom', m.nom] : [])) });
    case 'contenuRenomme': {                        // récrit le zip aux chemins validés dans la page
      gardeMaj(m.cle);
      const vu = await moteur.run(['contenu', '--cle', m.cle, '--fixe', '-'], JSON.stringify(m.ops));   // sans --go : contrôle, ou refuse
      if (!vu.renommes) return envoie({ t: 'contenu', cle: m.cle, data: await moteur.run(['contenu', '--cle', m.cle]), dit: T('Rien à renommer.') });
      const nom = m.cle.split('/').pop().replace(/\.zip$/i, '');
      const ok = await confirme(N(vu.renommes, 'Renommer {n} fichier dans « {0} » ?', 'Renommer {n} fichiers dans « {0} » ?', nom), N(vu.renommes, 'Récrire le zip ({n} fichier renommé)', 'Récrire le zip ({n} fichiers renommés)'),
        vu.poses ? N(vu.poses, '{n} fichier de ce mod est dans le jeu : le plan le remplacera', '{n} fichiers de ce mod sont dans le jeu : le plan les remplacera') : T('le jeu n\'est pas touché'),
        T('Entrée = ne rien écrire. Le zip est récrit avec les nouveaux noms, relu, puis remplace l\'ancien ; le contenu des fichiers ne change pas.'));
      if (!ok) return;
      await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : réécriture du zip…') },
        () => moteur.run(['contenu', '--cle', m.cle, '--fixe', '-', '--go'], JSON.stringify(m.ops)));
      envoie({ t: 'contenu', cle: m.cle, data: await moteur.run(['contenu', '--cle', m.cle]), dit: N(vu.renommes, '{n} fichier renommé dans le zip.', '{n} fichiers renommés dans le zip.') });
      envoie({ t: 'convention', data: await moteur.run(['convention']) });
      return rafraichit();
    }
    case 'zipRenomme': {                            // le nom du zip lui-même, depuis la fiche du mod : saisi dans VS Code, confirmé
      gardeMaj(m.cle);
      const actuel = m.cle.split('/').pop();
      const saisi = await vscode.window.showInputBox({ title: T('Red Stack : nom du zip'), value: actuel, valueSelection: [0, actuel.length - 4], ignoreFocusOut: true,
        prompt: T('Nouveau nom du fichier, avec son extension .zip. Garder le numéro Nexus dans le nom garde les mises à jour et les prérequis lus sur Nexus.') });
      const nom = (saisi || '').trim();
      if (!nom || nom === actuel) return;
      const noms = JSON.stringify([{ cle: m.cle, nom }]);
      const vu = await moteur.run(['convention', '--fixe', '-'], noms);   // sans --go : contrôle, ou refuse
      if (!vu.renommes.length) return;
      const ok = await confirme(N(1, 'Renommer {n} archive du dépôt ?', 'Renommer {n} archives du dépôt ?'), N(1, 'Renommer {n} archive', 'Renommer {n} archives'), path.basename(vu.renommes[0].vers),
        T('Entrée = ne rien écrire. Seul le nom du fichier change : le contenu et le jeu ne sont pas touchés.'));
      if (!ok) return;
      await moteur.run(['convention', '--fixe', '-', '--go'], noms);
      await rafraichit();                           // l'état relu fait suivre le profil, l'arbre et le registre au nouveau nom
      return envoie({ t: 'detail', data: await moteur.run(['detail', ...P, '--mod', m.cle.split('/').slice(0, -1).concat(nom).join('/')]) });
    }
    case 'contenuRenommeLot': {                     // le contenu des zips cochés, aux noms que le moteur propose : une confirmation
      const prets = [], refus = [];
      let deja = 0;
      const propose = async (cle) => (await moteur.run(['contenu', '--cle', cle])).ops.filter((o) => o.vers !== o.de).map((o) => ({ de: o.de, vers: o.vers }));
      for (const cle of m.cles || []) {               // sans --go : chaque zip dit ce qu'il renommerait, ou son refus
        try {
          gardeMaj(cle);
          const ops = await propose(cle);
          const vu = ops.length ? await moteur.run(['contenu', '--cle', cle, '--fixe', '-'], JSON.stringify(ops)) : { renommes: 0 };
          if (vu.renommes) prets.push({ cle, n: vu.renommes, poses: vu.poses || 0 }); else deja += 1;
        } catch (e) { refus.push(`${cle.split('/').pop()} : ${String((e && e.message) || e).split('\n')[0]}`); }
      }
      if (!prets.length) throw new Error(T`Aucun contenu à renommer : ${refus.join(' ; ') || (deja ? T('ces zips sont déjà à la convention') : T('rien de coché'))}`);
      const n = prets.length, total = prets.reduce((a, x) => a + x.n, 0);
      const ok = await confirme(N(n, 'Renommer le contenu de {n} zip ?', 'Renommer le contenu de {n} zips ?'), N(n, 'Récrire {n} zip', 'Récrire {n} zips'),
        N(total, '{n} fichier à renommer en tout', '{n} fichiers à renommer en tout') + ' · ' + prets.slice(0, 3).map((x) => x.cle.split('/').pop().replace(/\.zip$/i, '')).join(' · ') + (n > 3 ? ` · ${N(n - 3, '… et {n} autre', '… et {n} autres')}` : ''),
        T('Entrée = ne rien écrire. Chaque zip est récrit aux noms que Red Stack propose, relu, puis remplace l\'ancien ; le contenu des fichiers ne change pas.') + (refus.length ? ` ${T`Laissés de côté : ${refus.length}.`}` : ''));
      if (!ok) return;
      let faits = 0;
      await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : réécriture du zip…') }, async (avance) => {
        for (const x of prets) {                      // proposition relue juste avant d'écrire : un zip récrit peut changer ce que les suivants citent
          if (avance) avance.report({ message: `${faits + 1} / ${prets.length} · ${x.cle.split('/').pop()}`, increment: 100 / prets.length });
          try {
            const ops = await propose(x.cle);
            if (ops.length) await moteur.run(['contenu', '--cle', x.cle, '--fixe', '-', '--go'], JSON.stringify(ops));
            faits += 1;
          } catch (e) { refus.push(`${x.cle.split('/').pop()} : ${String((e && e.message) || e).split('\n')[0]}`); }
        }
      });
      envoie({ t: 'convention', data: await moteur.run(['convention']), dit: N(faits, 'Contenu renommé dans {n} zip.', 'Contenu renommé dans {n} zips.') + (refus.length ? ` ${T`Laissés : ${refus.join(' ; ')}`}` : '') });
      return rafraichit();
    }
    case 'fomod':                                   // installateur FOMOD d'un zip : ses pages et les choix du profil (lecture seule)
      return envoie({ t: 'fomod', cle: m.cle, data: await moteur.run(['fomod', ...P, '--cle', m.cle]) });
    case 'fomodFixe': {                             // un choix, « hors du jeu » ou « piocher à la main » : noté au profil, le jeu suit à « Appliquer »
      const r = await moteur.run(['fomod', ...P, '--cle', m.cle, '--fixe', '-'], JSON.stringify(m.neuf || {}));
      envoie({ t: 'fomod', cle: m.cle, data: r, dit: N(r.compte.poses, 'Noté au profil : {n} fichier à poser pour ces choix.', 'Noté au profil : {n} fichiers à poser pour ces choix.') });
      return rafraichit();
    }
    case 'fomodImage': {                            // image d'un choix, lue dans le zip à la demande
      let image = '';
      try { image = (await moteur.run(['fomod', ...P, '--cle', m.cle, '--entree', m.entree])).image || ''; } catch { /* dite illisible dans la page */ }
      return envoie({ t: 'fomodImage', cle: m.cle, entree: m.entree, image });
    }
    case 'noms':                                    // noms dans le jeu de ce qu'un mod pose, et qui les cite (lecture seule)
      return envoie({ t: 'noms', cle: m.cle, data: await moteur.run(['noms', ...P, '--mod', m.cle]) });
    case 'nomsFixe': {                              // note les nouveaux noms au profil ; le zip ne change pas, le jeu suit à « Appliquer »
      const r = await moteur.run(['noms', ...P, '--mod', m.cle, '--fixe', '-'], JSON.stringify(m.noms));
      const n = r.fait.length, cites = r.fait.filter((f) => f.cites.length);
      envoie({ t: 'noms', cle: m.cle, data: r, dit: n ? N(n, '{n} nom noté au profil.', '{n} noms notés au profil.') : T('Rien à changer.') });
      if (n) {
        const msg = N(n, "Red Stack : {n} nom noté au profil. « Aperçu du plan » puis « Appliquer » pour l'écrire dans le jeu.", "Red Stack : {n} noms notés au profil. « Aperçu du plan » puis « Appliquer » pour les écrire dans le jeu.");
        if (cites.length) {
          vscode.window.showWarningMessage(msg + ` ${T('À relire, cités par leur ancien nom :')} `
            + cites.slice(0, 4).map((f) => `${f.avant} (${[...new Set(f.cites.map((c) => c.zip.split('/').pop().replace(/[.]zip$/i, '')))].slice(0, 3).join(', ')})`).join(' ; ') + '.');
        } else vscode.window.showInformationMessage(msg);
      }
      return rafraichit();
    }
    case 'conflits':                                // conflits dans les archives : lecture seule
      return envoie({ t: 'conflits', data: await moteur.run(['conflits', ...P]) });
    case 'conflitsRessources':                      // toutes les ressources en conflit, pour la lecture « par ressource »
      return envoie({ t: 'conflitsRessources', data: await moteur.run(['conflits', ...P, '--ressources']) });
    case 'conflitsCode':                            // conflits de code (Redscript, TweakXL, SetFlat) : lecture seule, à la demande
      return envoie({ t: 'conflitsCode', data: await moteur.run(['scripts', ...P]) });
    case 'ouvreFichier': {                          // un fichier de code du jeu, à sa ligne, dans l'éditeur
      if (!m.chemin || !fs.existsSync(m.chemin)) return erreur(T`Absent du disque : ${m.chemin}`);
      const n = Math.max(0, (parseInt(m.ligne, 10) || 1) - 1);
      const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(m.chemin));
      return vscode.window.showTextDocument(doc, { viewColumn: (panneau && panneau.viewColumn) || vscode.ViewColumn.Active, selection: new vscode.Range(n, 0, n, 0), preview: true });
    }
    case 'aide':                                    // le manuel, à la section de la vue d'où l'on vient
      return ouvrirAide(m.section || '');
    case 'theme':                                   // « Réglages », section « Thème »
      return regleTheme(m);
    case 'langue':                                  // « Réglages », section « Langue » : réglage de l'utilisateur, la page se refait
      return void vscode.workspace.getConfiguration('redStack').update('langue', m.code && m.code !== 'auto' ? m.code : undefined, vscode.ConfigurationTarget.Global);
    case 'codeFenetre':                             // « Scripts et tweaks… » : son onglet à lui
      return ouvrirCode();
    case 'objetsFenetre':                           // « Objets » : son onglet à lui
      return ouvrirObjets();
    case 'dependancesFenetre':                      // « Dépendances » : son onglet à lui, sur la chaîne d'un mod si demandée
      return ouvrirDependances(m.cle || '');
    case 'dependances':                             // prérequis de tout le dépôt ; `code` : lire d'abord le code de tous les zips
      return envoie({ t: 'dependances', data: await moteur.run(['prerequis', ...P].concat(m.code ? ['--code'] : [])) });
    case 'chaine': {                                // la chaîne d'un mod ou d'un cadre : lecture seule
      const depart = String(m.depart || '');
      const qui = depart.startsWith('c:') ? ['--cadre', depart.slice(2)] : ['--mod', depart];
      return envoie({ t: 'chaine', data: await moteur.run(['prerequis', ...P, ...qui, m.sens === 'besoin' && !depart.startsWith('c:') ? '--besoin' : '--chute']) });
    }
    case 'objets':                                  // objets des mods face à une sauvegarde de partie : lecture seule, à la demande
      return envoie({ t: 'objets', data: await moteur.run(['objets', ...P].concat(m.partie ? ['--partie', m.partie] : [])) });
    case 'ouvreReglages':                           // depuis un onglet d'analyse : la page, à ses « Réglages »
      return montreVue('reglages');
    case 'journal':                                 // historique des gestes qui ont écrit le jeu ou le dépôt (lecture seule)
      return envoie({ t: 'journal', data: await moteur.run(['journal', '--limite', '200'].concat(m.mod ? ['--mod', m.mod] : [])) });
    case 'magasin':                                 // état des liens, poids réel, arbres sans mod actif, retouches (lecture seule)
      return envoie({ t: 'magasin', data: await moteur.run(['magasin', ...P]) });
    case 'purge': {                                 // supprime les arbres qu'aucun mod actif ne tient ; les zips ne sont pas touchés
      const vu = await moteur.run(['purge', ...P]);
      if (vu.arbres.length) {
        const poids = poidsDit(vu.octets);
        if (!await confirme(N(vu.arbres.length, 'Supprimer {n} arbre du magasin ?', 'Supprimer {n} arbres du magasin ?'), N(vu.arbres.length, 'Purger {n} arbre', 'Purger {n} arbres'), T`${poids} ; les zips ne sont pas touchés`,
          T('Entrée = ne rien supprimer. Un arbre se refait depuis son zip ; une retouche est copiée dans les sauvegardes avant.'))) return;
        const r = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : purge du magasin…') },
          () => moteur.run(['purge', ...P, '--go']));
        vscode.window.showInformationMessage(N(r.arbres.length, 'Red Stack : {n} arbre supprimé du magasin.', 'Red Stack : {n} arbres supprimés du magasin.')
          + (r.retouches_sauvees ? ' ' + N(r.retouches_sauvees, '{n} retouche copiée dans les sauvegardes.', '{n} retouches copiées dans les sauvegardes.') : ''));
      }
      return envoie({ t: 'magasin', data: await moteur.run(['magasin', ...P]) });
    }
    case 'retoucheAnnule': {                        // l'arbre reprend les fichiers du zip ; le jeu suit à « Appliquer »
      const nom = String(m.cle || '').split('/').pop().replace(/\.zip$/i, '');
      if (!await confirme(T`Annuler les retouches de « ${nom} » ?`, T('Remettre les fichiers du zip dans l\'arbre'), T('le jeu suit au prochain « Appliquer »'),
        T('Entrée = ne rien changer. La retouche est perdue dans l\'arbre ; le jeu garde son fichier jusqu\'à « Appliquer ».'))) return;
      const r = await moteur.run(['retouche', ...P, '--mod', m.cle, '--annule']);
      vscode.window.showInformationMessage(N(r.retouches.length, 'Red Stack : {n} retouche annulée. « Aperçu du plan » puis « Appliquer » pour remettre le fichier du zip dans le jeu.', 'Red Stack : {n} retouches annulées. « Aperçu du plan » puis « Appliquer » pour remettre les fichiers du zip dans le jeu.'));
      envoie({ t: 'magasin', data: await moteur.run(['magasin', ...P]) });
      return rafraichit();
    }
    case 'sauvegarde':
      return sauvegarde(m);
    case 'conflitsFenetre':                         // « Conflits », ou la pastille d'un mod (m.cle) : l'onglet d'analyse
      return ouvrirAnalyse(m.cle || '');
    case 'montreMod':                               // depuis la fenêtre d'analyse : le détail s'ouvre dans la page
      ouvrir();
      return envoie({ t: 'detail', data: await moteur.run(['detail', ...P, '--mod', m.cle]) });
    case 'conflitsToutes':                          // toutes les ressources d'un mod ou d'une archive, celles sans conflit comprises
      return envoie({ t: 'conflitsToutes', id: m.id, data: await moteur.run(['conflits', ...P, m.mod ? '--mod=' + m.mod : '--nom=' + m.nom, '--tout']) });
    case 'conflitsDetail':
      return envoie({ t: 'conflitsDetail', nom: m.nom, data: await moteur.run(['conflits', ...P, '--nom=' + m.nom]) });
    case 'ordrePasse': {                            // « Passer devant / derrière » : par le nom dans le jeu, ou par modlist.txt
      const avant = m.sens === 'avant', drapeau = avant ? '--avant=' : '--apres=';
      const vu = (await moteur.run(['ordre', ...P, '--nom=' + m.nom, drapeau + m.cible])).propose;
      const cites = vu.cites.length ? ` · ${N(vu.cites.length, 'citée par son nom dans {n} fichier du dépôt : à relire', 'citée par son nom dans {n} fichiers du dépôt : à relire')}` : '';
      const choix = [{ label: T('$(close) Ne rien changer'), description: T('choix par défaut'), v: '' }];
      if (vu.nom && vu.atteint && vu.nom !== vu.archive) {
        choix.push({ label: T`$(edit) Renommer dans le jeu : ${vu.nom}`, description: T`rang ${vu.rang} → ${vu.rang_apres} ; le zip ne change pas${cites}`, v: 'nom' });
      }
      if (!vu.hors) choix.push({ label: T('$(pencil) Choisir un autre nom…'), description: vu.par_modlist ? T('sans effet sur les archives que modlist.txt cite') : T('la place suit le nom'), v: 'autre' });
      choix.push({ label: T('$(list-ordered) Tenir l\'ordre par modlist.txt'), description: T('aucun nom ne change ; le fichier est écrit par « Appliquer »'), v: 'modlist' });
      const ok = await vscode.window.showQuickPick(choix, { title: avant ? T`Charger ${m.nom} avant ${m.cible} ?` : T`Charger ${m.nom} après ${m.cible} ?`, ignoreFocusOut: true,
        placeHolder: T('Entrée = ne rien changer. Seul le profil est écrit ; le jeu suit au prochain « Appliquer ».') });
      if (!ok || !ok.v) return;
      if (ok.v === 'autre') return renommeArchive(m.nom, vu.nom || m.nom);
      const r = (await moteur.run(ok.v === 'nom' ? ['ordre', ...P, '--nom=' + m.nom, '--renomme=' + vu.nom]
        : ['ordre', ...P, '--nom=' + m.nom, drapeau + m.cible, '--voie', 'modlist'])).fait;
      vscode.window.showInformationMessage(r.geste === 'renomme' ? T`Red Stack : ${r.archive} s'appellera ${r.vers} dans le jeu. « Aperçu du plan » puis « Appliquer » pour l'écrire.`
        : N(r.lignes, "Red Stack : modlist.txt noté au profil ({n} ligne). « Aperçu du plan » puis « Appliquer » pour l'écrire.", "Red Stack : modlist.txt noté au profil ({n} lignes). « Aperçu du plan » puis « Appliquer » pour l'écrire."));
      return rafraichit();
    }
    case 'ordreRenomme':
      return renommeArchive(m.nom, m.nom);
    case 'ordreAnnule':
      await moteur.run(['ordre', ...P, '--nom=' + m.nom, '--annule']);
      return rafraichit();
    case 'ordreModlistStop':
      if (!await confirme(T('Ne plus tenir modlist.txt ?'), T('Ne plus le tenir'), T('l\'ordre revient aux noms des archives'),
        T('Entrée = ne rien changer. Le fichier part du jeu au prochain « Appliquer », copié dans les sauvegardes.'))) return;
      await moteur.run(['ordre', ...P, '--modlist', '--annule']);
      return rafraichit();
    case 'planRemplace':                            // plan : ces fichiers présents seront remplacés par ceux du zip (ou laissés)
      for (const d of m.dests || []) { if (m.on) aRemplacer.add(d); else aRemplacer.delete(d); }
      return envoie({ t: 'plan', data: await moteur.run(['plan', ...P, ...argsRemplace()]) });
    case 'applique': {
      const r = await applique(profil(), m.empreinte, '');
      if (r) aRemplacer.clear();
      if (r) envoie({ t: 'applique', data: r });
      if (r) vscode.window.showInformationMessage(`${T('Red Stack :')} ` + (r.message || T('appliqué.')));
      return rafraichit();
    }
    case 'reglages':
      return envoie({ t: 'reglages', data: await moteur.run(['config']), poste: poste() });
    case 'reglagesEcrit':
      return ecritReglages(m);
    case 'parcourir': {
      const r = await vscode.window.showOpenDialog({ canSelectFolders: true, canSelectFiles: false, canSelectMany: false,
        openLabel: T('Choisir ce dossier'), defaultUri: m.depuis && fs.existsSync(m.depuis) ? vscode.Uri.file(m.depuis) : undefined });
      if (r && r[0]) envoie({ t: 'chemin', champ: m.champ, chemin: r[0].fsPath });
      return;
    }
    case 'reference':
      return reference(m.geste);
    case 'copie':
      await vscode.env.clipboard.writeText(String(m.texte || ''));
      vscode.window.showInformationMessage(T('Red Stack : copié dans le presse-papiers.'));
      return;
    case 'montre':                                  // un zip ou un arbre du magasin, dans l'Explorateur
      if (m.chemin && fs.existsSync(m.chemin)) await vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(m.chemin));
      else erreur(T`Absent du disque : ${m.chemin}`);
      return;
    case 'nexus':
      if (/^\d{1,7}$/.test(String(m.id))) {
        await vscode.env.openExternal(vscode.Uri.parse(`https://www.nexusmods.com/cyberpunk2077/mods/${m.id}`));
      }
      return;
  }
}

/** Nom d'une archive DANS LE JEU, noté au profil (le zip ne change pas) : champ de saisie, puis ce que le moteur en dit. */
async function renommeArchive(nom, propose) {
  const saisi = await vscode.window.showInputBox({
    title: T`Nom de ${nom} dans le jeu`, value: propose, ignoreFocusOut: true,
    prompt: T('Les archives se chargent dans l\'ordre des noms : ! # chiffres MAJUSCULES _ minuscules. La première chargée gagne. Échap = ne rien changer.'),
    validateInput: (v) => (/^[^\\/:*?"<>|]{1,120}$/.test(v.trim()) ? null : T('Un nom de fichier, sans dossier')),
  });
  if (!saisi || saisi.trim() === nom) return;
  const r = (await moteur.run(['ordre', '--profil', profil(), '--nom=' + nom, '--renomme=' + saisi.trim()])).fait;
  const msg = T`Red Stack : ${r.archive} s'appellera ${r.vers} dans le jeu. « Aperçu du plan » puis « Appliquer » pour l'écrire.`;
  if (r.cites.length) {
    vscode.window.showWarningMessage(msg + ` ${N(r.cites.length, 'Son ancien nom est cité dans {n} fichier du dépôt :', 'Son ancien nom est cité dans {n} fichiers du dépôt :')} `
      + r.cites.slice(0, 4).map((c) => `${c.zip.split('/').pop().replace(/\.zip$/i, '')} (${path.basename(c.fichier)})`).join(', ') + '.');
  } else vscode.window.showInformationMessage(msg);
  return rafraichit();
}

/** Ce qui se règle par poste (réglages de VS Code) et non dans config.json, plus la commande qui déclare le serveur MCP. */
function poste() {
  const c = vscode.workspace.getConfiguration('redStack');
  const q = (x) => `"${x}"`;
  return {
    theme: etatTheme(),
    langue: { voulue: vscode.workspace.getConfiguration('redStack').get('langue') || 'auto', enCours: langue.enCours().langue, deVSCode: vscode.env.language, langues: langue.langues(ctx.extensionPath) },
    python: c.get('python') || 'python', donnees: c.get('donnees') || '', donneesDefaut: donneesDefaut(), moteur: moteur.script,
    mcp: `claude mcp add red-stack -- ${moteur.commande()} -I ${q(path.join(stable, 'red_stack_mcp.py'))} --donnees ${q(moteur.donnees)}`,
    mcpWk: `claude mcp add red-stack-wolvenkit -- ${moteur.commande()} -I ${q(path.join(stable, 'red_stack_wk_mcp.py'))} --donnees ${q(moteur.donnees)}`,
  };
}

const CLE_NEXUS = 'redStack.nexusCle';
/** Téléchargement en cours : { cles, fait, nom } ; un seul lot à la fois, et ses zips ne se déplacent ni ne se récrivent. */
let majEnCours = null;
const MAJ_OCCUPEE = () => T('Un téléchargement de mises à jour est en cours : attendre sa fin (ou l\'arrêter dans sa notification).');
function gardeMaj(cle) {
  if (majEnCours && majEnCours.cles.includes(cle)) throw new Error(T('Ce zip est en cours de mise à jour : attendre la fin du téléchargement.'));
}
const ditMaj = () => envoie({ t: 'majOccupe', enCours: majEnCours });
/** Avancée d'un téléchargement : le moteur écrit dans `vu.part`, relu deux fois par seconde (octets reçus, débit lissé,
 *  octets du lot). Rend la fonction qui arrête la relecture. */
function suitPart(vu, avant, total) {
  let dernier = 0, quand = Date.now(), debit = 0;
  const t = setInterval(() => {
    if (!vu.part) return;
    fs.stat(vu.part, (e, st) => {
      if (e || !majEnCours) return;
      const m = Date.now(), d = Math.max(0, st.size - dernier) * 1000 / Math.max(1, m - quand);
      debit = debit ? 0.7 * debit + 0.3 * d : d;
      dernier = st.size; quand = m;
      majEnCours.avance = { recu: st.size, taille: (vu.neuf && vu.neuf.taille) || 0, debit, lotRecu: avant + st.size, lotTotal: total };
      envoie({ t: 'majAvance', avance: majEnCours.avance });
    });
  }, 500);
  return () => clearInterval(t);
}
/** Environnement d'un appel au moteur qui a besoin du compte Nexus : la clé sort du coffre, pour cet appel seulement. */
async function envNexus() {
  const cle = await ctx.secrets.get(CLE_NEXUS);
  return cle ? { RED_STACK_NEXUS_KEY: cle } : undefined;
}

/** Liste des mises à jour vers la page, avec le compte de la clé d'API s'il y en a une. */
async function envoieMaj(frais = false, dit = '') {
  const env = await envNexus();
  const data = await moteur.run(['nexus'].concat(frais ? ['--force'] : []));
  const compte = env ? await moteur.run(['nexus', '--compte'], undefined, env) : { cle: false };
  envoie({ t: 'maj', data, compte, dit, enCours: majEnCours });
}

/** Télécharge les mises à jour cochées : contrôle de chacune, une confirmation pour le lot, puis une par une.
 *  Compte gratuit : Nexus exige le bouton « Mod manager download » du site ; la page s'ouvre et le lien `nxm://` se colle. */
async function telechargeMaj(lignes) {
  if (majEnCours) throw new Error(MAJ_OCCUPEE());
  majEnCours = { cles: lignes.map((x) => x.cle), fait: [], nom: '', prepare: true };
  ditMaj();                                         // la vue se verrouille dès le clic, avant même la confirmation
  try {
    await telechargeLot(lignes);
  } finally {
    majEnCours = null;
    ditMaj();
  }
}

async function telechargeLot(lignes) {
  const env = await envNexus();
  if (!env) throw new Error(T('Aucune clé d\'API Nexus : bouton « Clé d\'API Nexus… » de la vue « Mises à jour ».'));
  const args = (x, lien) => ['nexus', '--cle', x.cle].concat(x.fichier ? ['--fichier', String(x.fichier)] : [], x.nom ? ['--nom', x.nom] : [], lien ? ['--lien', lien] : []);
  const court = (e) => String((e && e.message) || e).split('\n')[0];
  const prets = [], refus = [];
  for (const x of lignes) {                         // sans --go : chaque ligne dit sa cible, ou son refus
    try {
      const vu = await moteur.run(args(x), undefined, env);
      if (vu.erreur) throw new Error(vu.erreur);
      prets.push({ x, vu });
    } catch (e) { refus.push(`${x.cle.split('/').pop()} : ${court(e)}`); }
  }
  if (!prets.length) throw new Error(T`Rien à télécharger : ${refus.join(' ; ') || T('aucune ligne cochée')}`);
  const gratuit = prets.some((q) => q.vu.besoin_lien);
  const octets = prets.reduce((n, q) => n + (q.vu.neuf.taille || 0), 0);
  const poids = poidsDit(octets);
  const ok = await confirme(N(prets.length, 'Télécharger {n} mise à jour depuis Nexus ?', 'Télécharger {n} mises à jour depuis Nexus ?'), N(prets.length, 'Télécharger {n} zip, {0}', 'Télécharger {n} zips, {0}', poids),
    prets.slice(0, 3).map((q) => path.basename(q.vu.vers)).join(' · ') + (prets.length > 3 ? ` · ${N(prets.length - 3, '… et {n} autre', '… et {n} autres')}` : ''),
    T('Entrée = ne rien écrire. Chaque nouvelle version prend la place de l\'ancienne, rangée dans les retirés de sa pile ; le jeu ne change qu\'au prochain « Appliquer ».')
    + (gratuit ? ` ${T('Compte gratuit : la page de chaque fichier s\'ouvrira, cliquez « Mod manager download » puis collez le lien.')}` : ''));
  if (!ok) return;
  const faits = [];
  let octetsFaits = 0;
  majEnCours = { cles: prets.map((q) => q.x.cle), fait: [], nom: '', prepare: false };
  await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : téléchargement depuis Nexus'), cancellable: true },
    async (progres, arret) => {
      for (const [i, q] of prets.entries()) {
        if (arret.isCancellationRequested) { refus.push(N(prets.length - i, '{n} non téléchargé : arrêt demandé', '{n} non téléchargés : arrêt demandé')); break; }
        progres.report({ message: T`${i + 1} sur ${prets.length} : ${path.basename(q.vu.vers)}`, increment: 100 / prets.length });
        majEnCours.nom = q.x.cle;
        ditMaj();
        try {
          let lien = '';
          if (q.vu.besoin_lien) {
            await vscode.env.openExternal(vscode.Uri.parse(q.vu.page));
            lien = await attendLien(path.basename(q.vu.vers), /\/mods\/(\d+)/.exec(q.vu.page)[1]);
            if (!lien || !lien.trim()) { refus.push(T`${path.basename(q.vu.vers)} : passé`); continue; }
          }
          const arrete = suitPart(q.vu, octetsFaits, octets);
          let r;
          try { r = await telecharge.run(args(q.x, lien && lien.trim()).concat(['--go']), undefined, env); } finally { arrete(); }
          if (!r.ecrit) throw new Error(r.erreur || T('rien écrit'));
          faits.push(r);
          if (r.ancienne_restee) refus.push(T`${path.basename(q.vu.vers)} : reçu, mais l'ancienne version a bougé pendant le téléchargement et n'a pas été rangée`);
        } catch (e) { refus.push(`${path.basename(q.vu.vers)} : ${court(e)}`); }
        majEnCours.fait.push(q.x.cle);
        octetsFaits += (q.vu.neuf && q.vu.neuf.taille) || 0;
      }
    });
  majEnCours = null;
  await envoieMaj(false, N(faits.length, "{n} mise à jour téléchargée : lire l'aperçu du plan, puis appliquer.", "{n} mises à jour téléchargées : lire l'aperçu du plan, puis appliquer.") + (refus.length ? ` ${T`À relire : ${refus.join(' ; ')}`}` : ''));
  rafraichit();
}

// ---------------------------------------------------------------- liens nxm:// (bouton « Mod manager download » de Nexus)
// Inscrit pour ces liens (registre de l'utilisateur, à son clic, réversible), Red Stack reçoit de Windows l'adresse
// `vscode://<extension>/nxm?<lien>`. Le lien dit un mod et un fichier : le moteur dit quel zip du dépôt il met à jour ;
// sinon c'est un mod nouveau, rangé dans le dossier d'arrivée d'une pile choisie. Rien n'est écrit sans un choix.
const NXM_AVANT = 'redStack.nxmAvant';
let attenteNxm = null;                              // téléchargement d'un compte gratuit qui attend le lien d'un mod : { mod, donne }
const erreurNxm = (e) => vscode.window.showErrorMessage(`${T('Red Stack, lien nxm:// :')} ` + String((e && e.message) || e).split('\n')[0]);
const etatNxm = async () => {
  const e = await nxm.etat(process.execPath, vscode.env.uriScheme || 'vscode', ctx.extension ? ctx.extension.id : 'doublescotch.red-stack');
  return { ...e, programme: nxm.programme(e.commande || e.systeme), avant: ctx.globalState.get(NXM_AVANT, null) };
};

/** Inscrit Red Stack comme programme des liens nxm:// de l'utilisateur, ou défait cette inscription (confirmé). */
async function inscritNxm(oui) {
  const e = await etatNxm();
  if (!e.possible) throw new Error(T('L\'inscription pour les liens nxm:// n\'est écrite que pour Windows.'));
  if (oui && !e.inscrit) {
    const autre = e.commande || e.systeme;
    if (!await confirme(T('Recevoir les liens nxm:// dans Red Stack ?'), T('Inscrire Red Stack'),
      autre ? T`à la place de ${nxm.programme(autre)} pour votre compte Windows ; réversible` : T('aucun programme ne les reçoit aujourd\'hui ; réversible'),
      T('Entrée = ne rien écrire. Une clé du registre de votre compte Windows est écrite (HKCU\\Software\\Classes\\nxm), sans droits d\'administrateur.'))) return;
    await ctx.globalState.update(NXM_AVANT, await nxm.inscrit(e.voulue));
  } else if (!oui && e.inscrit) {
    const avant = ctx.globalState.get(NXM_AVANT, '') || '';
    if (!await confirme(T('Ne plus recevoir les liens nxm:// dans Red Stack ?'), T('Défaire l\'inscription'),
      avant ? T`${nxm.programme(avant)} les reçoit de nouveau` : T('la clé de votre compte Windows est retirée'),
      T('Entrée = ne rien écrire.'))) return;
    await nxm.retire(avant);
    await ctx.globalState.update(NXM_AVANT, undefined);
  }
  envoie({ t: 'nxm', data: await etatNxm() });
}

/** Compte gratuit : attend le lien du mod, venu seul par Windows (Red Stack inscrit) ou collé dans la boîte ; '' = passer. */
async function attendLien(nom, mod) {
  const inscrit = await etatNxm().then((e) => e.inscrit, () => false);
  const arret = new vscode.CancellationTokenSource();
  try {
    return await new Promise((resolve) => {
      attenteNxm = { mod: String(mod), donne: resolve };
      vscode.window.showInputBox({ title: T`Lien de téléchargement : ${nom}`, ignoreFocusOut: true,
        prompt: (inscrit ? T('Sur la page ouverte, cliquez « Mod manager download » (ou « Slow download ») : le lien arrive seul ici. Sinon, collez-le.')
          : T('Sur la page ouverte, cliquez « Mod manager download » (ou « Slow download »), copiez le lien nxm:// proposé, collez-le ici.')) + ` ${T('Vide : passer ce zip.')}`,
        validateInput: (v) => (!v.trim() || /^nxm:\/\//i.test(v.trim()) ? null : T('Un lien qui commence par nxm:// est attendu')) }, arret.token)
        .then((v) => resolve(v || ''), () => resolve(''));
    });
  } finally {
    attenteNxm = null;
    arret.cancel();                                 // lien venu par Windows : la boîte de saisie se ferme
    arret.dispose();
  }
}

/** Un lien nxm:// arrive : il sert le téléchargement qui l'attend, sinon il met à jour un zip du dépôt ou range un mod nouveau. */
async function recoitNxm(lien) {
  if (!lien) throw new Error(T('adresse reçue sans lien lisible.'));
  const mod = /\/mods\/(\d+)/.exec(lien)[1];
  if (attenteNxm) {
    if (attenteNxm.mod !== mod) throw new Error(T`un téléchargement attend le lien du mod ${attenteNxm.mod}, celui-ci est du mod ${mod} : ignoré.`);
    return attenteNxm.donne(lien);
  }
  if (majEnCours) throw new Error(MAJ_OCCUPEE());
  const env = await envNexus();
  if (!env) {
    ouvrir(); montreVue('maj').catch(() => {});
    throw new Error(T('aucune clé d\'API Nexus. Donnez-la dans la vue « Mises à jour », puis recliquez « Mod manager download ».'));
  }
  const r = await moteur.run(['nexus', '--lien', lien]);
  const f = r.fichier, quoi = `${f.nom}${f.version ? ' ' + f.version : ''}`;
  if (r.deja) return void vscode.window.showInformationMessage(T`Red Stack : ${quoi} est déjà dans le dépôt (${r.deja}).`);
  const choix = [{ label: T('$(close) Ne rien télécharger'), description: T('choix par défaut') }];
  for (const c of r.cibles) {
    choix.push({ label: `$(arrow-up) ${c.sur ? T('Mettre à jour') : T('Remplacer (autre fichier du même mod)')} : ${c.nom.replace(/\.zip$/i, '')}`,
      description: `→ ${c.propose} · ${c.section}${c.lieu ? '/' + c.lieu : ''}${c.annotation ? ` · ${T`zip annoté « ${c.annotation} »`}` : ''}`, v: { cle: c.cle } });
  }
  for (const p of r.piles) choix.push({ label: T`$(inbox) Mod nouveau : arrivages de ${p}`, description: T('rangé dans le dossier d\'arrivée de cette pile'), v: { pile: p } });
  const ok = await vscode.window.showQuickPick(choix, { title: T`Nexus envoie « ${quoi} » (mod ${r.mod})${f.taille ? ', ' + poidsDit(f.taille) : ''}`,
    ignoreFocusOut: true, matchOnDescription: true,
    placeHolder: r.cibles.length ? T('Entrée = ne rien télécharger. La nouvelle version prend la place du zip choisi, l\'ancienne part dans les retirés de sa pile.')
      : T('Entrée = ne rien télécharger. Aucun zip de ce mod dans le dépôt : choisir la pile qui le reçoit.') });
  if (!ok || !ok.v) return;
  if (majEnCours) throw new Error(MAJ_OCCUPEE());
  const args = ok.v.cle ? ['nexus', '--cle', ok.v.cle, '--lien', lien, '--go'] : ['nexus', '--lien', lien, '--section', ok.v.pile, '--go'];
  majEnCours = { cles: ok.v.cle ? [ok.v.cle] : [], fait: [], nom: ok.v.cle || '', prepare: false };
  ditMaj();
  let res;
  try {
    res = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T`Red Stack : téléchargement de ${quoi}…` },
      () => telecharge.run(args, undefined, env));
  } finally {
    majEnCours = null;
    ditMaj();
  }
  if (!res.ecrit) throw new Error(res.erreur || (res.besoin_lien ? T('compte gratuit : ce lien ne porte pas sa clé de téléchargement, recliquer le bouton du site.') : T('rien écrit.')));
  vscode.window.showInformationMessage(ok.v.cle ? T`Red Stack : ${path.basename(res.vers)} téléchargé à la place de l'ancienne version. « Aperçu du plan », puis « Appliquer ».`
    : T`Red Stack : ${path.basename(res.vers)} téléchargé dans les arrivages de ${ok.v.pile}.`);
  if (panneau) {
    envoie({ t: 'convention', data: await moteur.run(['convention']) });
    rafraichit();
  }
}

/** Confirmation d'un geste qui écrit : liste à choix en haut de la fenêtre, le premier choix (actif d'office) n'écrit rien. */
async function confirme(titre, action, description, aide) {
  const ok = await vscode.window.showQuickPick([
    { label: T('$(close) Ne rien écrire'), description: T('choix par défaut'), v: false },
    { label: `$(check) ${action}`, description, v: true },
  ], { title: titre, ignoreFocusOut: true, placeHolder: aide });
  return !!(ok && ok.v);
}

/** Enregistre la page de réglages : config.json par le moteur (qui contrôle), puis les réglages du poste. */
async function ecritReglages(m) {
  const avant = await moteur.run(['config']);
  const deplace = ['depot', 'jeu', 'magasin'].filter((k) => {
    if (!(k in m.conf)) return false;
    const vieux = avant[k] || avant.effectif[k] || '', neuf = (m.conf[k] || '').trim();
    if (!neuf) return k === 'magasin' && !!avant.magasin;      // retour au magasin par défaut
    return !!vieux && path.resolve(neuf).toLowerCase() !== path.resolve(vieux).toLowerCase();
  });
  if (avant.adopte && deplace.length) {
    const ok = await vscode.window.showWarningMessage(T`Changer ${deplace.map((k) => ({ depot: T('le dépôt'), jeu: T('le jeu'), magasin: T('le magasin') }[k])).join(', ')} ?`, {
      modal: true,
      detail: T('Ce jeu est déjà suivi par Red Stack. Un autre dossier de jeu repart sans registre de pose (une lecture du jeu sera proposée) ; un autre magasin sera rempli au prochain « Appliquer », l\'ancien reste sur le disque ; un autre dépôt doit porter les mêmes zips. Rien n\'est écrit dans le jeu ici.'),
    }, T('Changer'));
    if (ok !== T('Changer')) return envoie({ t: 'reglages', data: avant, poste: poste() });
  }
  const data = await moteur.run(['config', '--fixe', '-'], JSON.stringify(m.conf));
  const c = vscode.workspace.getConfiguration('redStack');
  const p = m.poste || {};
  let rebranche = false;
  for (const k of ['python', 'donnees']) {
    if (typeof p[k] === 'string' && p[k].trim() !== (c.get(k) || '')) {
      await c.update(k, p[k].trim() || undefined, vscode.ConfigurationTarget.Global);   // déclenche branche()
      rebranche = true;
    }
  }
  if (rebranche) branche();
  envoie({ t: 'reglages', data: rebranche ? await moteur.run(['config']) : data, poste: poste(), enregistre: true });
  return rafraichit();
}

/** Sauvegardes des réglages des mods : en faire une, comparer le jeu à l'une d'elles, la restaurer (confirmé, jeu fermé). */
async function sauvegarde(m) {
  let dit = '', compare = null;
  if (m.geste === 'cree') {
    const r = (await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : sauvegarde des réglages…') },
      () => moteur.run(['sauvegarde', '--cree']))).cree;
    dit = N(r.fichiers, 'Sauvegardé : {n} fichier dans {0}.', 'Sauvegardé : {n} fichiers dans {0}.', r.nom) + (r.jeu_lance ? ` ${T('Le jeu tournait : un fichier en cours d\'écriture peut être incomplet.')}` : '');
  } else if ((m.geste === 'compare' || m.geste === 'restaure') && m.nom) {
    compare = await moteur.run(['sauvegarde', '--restaure', '--nom', m.nom]);
    const n = compare.changes.length + compare.absents.length;
    if (m.geste === 'restaure' && n && await confirme(N(n, 'Restaurer {n} réglage de {0} ?', 'Restaurer {n} réglages de {0} ?', m.nom), N(n, 'Restaurer {n} fichier', 'Restaurer {n} fichiers'),
      T('ceux d\'aujourd\'hui sont copiés dans les sauvegardes'), T('Entrée = ne rien écrire. Le jeu doit être fermé.'))) {
      compare = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : restauration des réglages…') },
        () => moteur.run(['sauvegarde', '--restaure', '--nom', m.nom, '--go', '--vrai-jeu']));
      dit = N(n, '{n} réglage restauré.', '{n} réglages restaurés.');
    }
  }
  envoie({ t: 'sauvegarde', data: await moteur.run(['sauvegarde']), compare, dit });
}

/** Référence du jeu : contrôle (lecture seule), création (copie du jeu sans ses archives), restauration du socle. */
async function reference(geste) {
  const conf = await moteur.run(['config']);
  const lit = async () => {
    try {
      return await moteur.run(['reference']);
    } catch (e) {
      return { absente: true, message: String(e.message || e) };
    }
  };
  if (geste === 'cree') {
    const ok = await vscode.window.showWarningMessage(T('Créer la référence du jeu ?'), {
      modal: true,
      detail: T`Copie tout le jeu sauf ${conf.reference_exclus.join(', ')} dans :\n${conf.effectif.reference}` + '\n\n'
        + (conf.adopte ? T('Le jeu porte déjà des mods : inutile de le vider. Les fichiers posés par Red Stack sont laissés hors de la copie ; la référence fige le reste du socle tel qu\'il est aujourd\'hui et sera marquée « non vierge » (un fichier du jeu qu\'un mod remplace n\'y sera pas : Steam sait le remettre).') + '\n\n' : '')
        + T('Le jeu n\'est pas modifié. Il doit être fermé ; la copie peut prendre plusieurs minutes.'),
    }, T('Créer la référence'));
    if (ok !== T('Créer la référence')) return;
    const r = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : copie de la référence du jeu…') },
      () => moteur.run(['reference', '--cree'].concat(conf.adopte ? ['--force'] : [])));
    vscode.window.showInformationMessage(T`Red Stack : référence créée, ${r.fichiers} fichiers.`);
  } else if (geste === 'restaure') {
    const etat = await lit();
    const n = etat.absente ? 0 : etat.modifies.length + etat.manquants.length;
    if (!n) return envoie({ t: 'reference', data: etat });
    const ok = await vscode.window.showQuickPick([
      { label: T('$(close) Ne rien écrire'), description: T('choix par défaut'), v: false },
      { label: N(n, '$(check) Restaurer {n} fichier du socle', '$(check) Restaurer {n} fichiers du socle'), description: T('ceux d\'aujourd\'hui sont copiés dans les sauvegardes'), v: true },
    ], { title: T('Remettre le socle du jeu comme dans la référence ?'), ignoreFocusOut: true,
      placeHolder: T('Entrée = ne rien écrire. Le jeu doit être fermé.') });
    if (!ok || !ok.v) return;
    await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : restauration du socle…') },
      () => moteur.run(['reference', '--restaure', '--go', '--vrai-jeu']));
    vscode.window.showInformationMessage(N(n, 'Red Stack : {n} fichier du socle restauré.', 'Red Stack : {n} fichiers du socle restaurés.'));
  }
  envoie({ t: 'reference', data: await lit() });
  if (geste === 'cree') envoie({ t: 'reglages', data: await moteur.run(['config']), poste: poste() });
}

/** Montre le plan chiffré, attend la confirmation, applique CE plan (empreinte). Rend le résultat, ou null si refusé. */
async function applique(nom, empreinte, motif) {
  const plan = await moteur.run(['plan', '--profil', nom, ...argsRemplace()]);
  if (plan.empreinte !== empreinte) {
    envoie({ t: 'plan', data: plan });
    throw new Error(T('Le plan a changé depuis l\'aperçu : rien écrit, le revoici.'));
  }
  if (plan.compte.conflit) throw new Error(N(plan.compte.conflit, "{n} conflit à trancher avant d'appliquer.", "{n} conflits à trancher avant d'appliquer."));
  if (plan.jeu_lance) throw new Error(T('Le jeu tourne : le fermer avant d\'appliquer.'));
  const c = plan.compte;
  const parZip = {};
  for (const k of ECRIT) for (const r of plan[k]) (parZip[r.zip] = parZip[r.zip] || {})[k] = (parZip[r.zip][k] || 0) + 1;
  const lignes = Object.entries(parZip).slice(0, 14).map(([z, n]) =>
    `${z.split('/').pop().replace(/\.zip$/i, '')} : ` + Object.entries(n).map(([k, v]) => MOT[k](v)).join(T(', ')));
  if (Object.keys(parZip).length > 14) lignes.push(N(Object.keys(parZip).length - 14, '… et {n} autre mod', '… et {n} autres mods'));
  const detail = (motif ? T`Demande d'une session Claude : ${motif}` + '\n\n' : '')
    + [T`${c.pose} à poser, ${c.remplace} à remplacer, ${c.retire} à retirer`]     // des propositions entières, jointes par le séparateur de la langue
      .concat(c.lie || c.delie ? [T`${c.lie} à lier`, N(c.delie, '{n} réglage à délier', '{n} réglages à délier')] : [])
      .concat(c.pris || c.rendu ? [N(c.pris || 0, '{n} fichier pris au registre', '{n} fichiers pris au registre'), N(c.rendu || 0, "{n} rendu à l'installateur tiers", "{n} rendus à l'installateur tiers")] : [])
      .concat(c.modlist ? [plan.modlist[0].action === 'ecrire' ? T('modlist.txt à écrire') : T('modlist.txt à retirer')] : [])
      .join(T(', '))
    + '.\n\n' + lignes.join('\n')
    + (c.garde_modifie ? '\n\n' + N(c.garde_modifie, '{n} fichier modifié en jeu : gardé tel quel.', '{n} fichiers modifiés en jeu : gardés tels quels.') : '')
    + '\n\n' + T('Le jeu doit être fermé.');
  // Liste à choix plutôt que boîte modale : le premier choix, actif d'office, n'écrit rien ; Espace ne valide pas.
  const ok = await vscode.window.showQuickPick([
    { label: T('$(close) Ne rien écrire'), description: T('choix par défaut'), v: false },
    { label: T`$(check) Appliquer ${plan.reel ? T('au jeu') : T('au jeu de banc')}`, description: detail.split('\n\n')[motif ? 1 : 0], v: true },
  ], {
    title: T`Appliquer le profil « ${nom} » ${plan.reel ? T('au jeu') : T('au jeu de banc')} ?`, ignoreFocusOut: true, detail,
    placeHolder: T('Entrée = ne rien écrire. Descendre sur « Appliquer » puis Entrée pour écrire le jeu (jeu fermé).'),
  });
  if (!ok || !ok.v) return null;
  const args = ['applique', '--profil', nom, '--go', '--si-plan', empreinte, ...argsRemplace()].concat(plan.reel ? ['--vrai-jeu'] : []);
  return vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: T('Red Stack : application au jeu…') },
    () => moteur.run(args));
}
const MOT = { pose: (n) => T`${n} à poser`, remplace: (n) => T`${n} à remplacer`, retire: (n) => T`${n} à retirer`, lie: (n) => T`${n} à lier`, delie: (n) => T`${n} à délier` };

/** Demande déposée par le serveur MCP : même confirmation que le bouton de la page, résultat écrit dans la demande. */
async function traiteDemande(aLaMain) {
  const f = path.join(moteur.donnees, 'demande.json');
  let d;
  try {
    d = JSON.parse(fs.readFileSync(f, 'utf8'));
  } catch {
    d = null;
  }
  if (!d || d.etat !== 'attente') {
    if (aLaMain) vscode.window.showInformationMessage(T('Red Stack : aucune demande en attente.'));
    return;
  }
  if (d.id === demandeVue && !aLaMain) return;      // déjà montrée dans cette fenêtre
  demandeVue = d.id;
  const clos = (etat, plus) => fs.writeFileSync(f, JSON.stringify(
    { ...d, etat, traitee: new Date().toISOString().slice(0, 19), ...plus }, null, 1), 'utf8');
  try {
    const r = await applique(d.profil, d.empreinte, d.motif || T('(sans motif)'));
    if (!r) return clos('refusée', { message: T('Refusée par l\'utilisateur.') });
    clos(r.echecs && r.echecs.length ? 'échec' : 'appliquée', { resultat: r });
    vscode.window.showInformationMessage(`${T('Red Stack :')} ` + (r.message || T('appliqué.')));
    if (panneau) rafraichit();
  } catch (e) {
    clos('échec', { message: String(e.message || e) });
    vscode.window.showErrorMessage(`${T('Red Stack, demande non appliquée :')} ` + (e.message || e));
  }
}

module.exports = { activate, deactivate };
