// Red Stack : programme des liens `nxm://` (bouton « Mod manager download » de Nexus). Aucune dépendance à VS Code :
// testable sous Node seul. Windows seulement : l'inscription vit dans le registre de l'UTILISATEUR
// (HKCU\Software\Classes\nxm), sans droits d'administrateur, et se défait. Le lien reçu est rendu à VS Code par son
// adresse `vscode://<extension>/nxm?<lien>`, avec la commande même que Windows lance pour une adresse `vscode://`.
'use strict';
const { execFile } = require('child_process');

const CLE = 'HKCU\\Software\\Classes\\nxm';
const COMMANDE = CLE + '\\shell\\open\\command';
const possible = () => process.platform === 'win32';

/** Lance reg.exe ; rend sa sortie, ou '' si la clé n'existe pas (code 1). `lance` : remplaçable au banc. */
function reg(args, lance = execFile) {
  return new Promise((resolve, reject) => {
    lance('reg.exe', args, { windowsHide: true, encoding: 'buffer' }, (e, out, err) => {
      if (e && e.code === 1) return resolve('');
      if (e) return reject(new Error(`reg.exe : ${(err && err.toString('latin1').trim()) || e.message}`));
      resolve(out.toString('latin1'));
    });
  });
}

/** Valeur par défaut d'une clé : la ligne `(…)    REG_SZ    valeur` (le nom entre parenthèses suit la langue de Windows). */
const valeur = (sortie) => { const m = /^\s+\(.*?\)\s+REG(?:_EXPAND)?_SZ\s+(.*?)\s*$/m.exec(sortie); return m ? m[1] : ''; };

/** Commande qui rend un lien `nxm://` à l'extension : celle de `<schema>://` chez Windows, `%1` enveloppé dans notre adresse. */
function commandePour(commandeVscode, exe, schema, extension) {
  const adresse = `${schema}://${extension}/nxm?%1`;
  if (commandeVscode && commandeVscode.includes('%1')) return commandeVscode.replace('%1', adresse);
  return `"${exe}" --open-url -- "${adresse}"`;
}

/** État : { possible, commande (celle en place pour l'utilisateur, ou ''), systeme (celle de tout le poste), voulue, inscrit }. */
async function etat(exe, schema, extension, lance) {
  if (!possible()) return { possible: false, commande: '', systeme: '', voulue: '', inscrit: false };
  const voulue = commandePour(valeur(await reg(['query', `HKCR\\${schema}\\shell\\open\\command`, '/ve'], lance)), exe, schema, extension);
  const commande = valeur(await reg(['query', COMMANDE, '/ve'], lance));
  const systeme = valeur(await reg(['query', 'HKLM\\Software\\Classes\\nxm\\shell\\open\\command', '/ve'], lance));
  return { possible: true, commande, systeme, voulue, inscrit: !!commande && commande.toLowerCase() === voulue.toLowerCase() };
}

/** Écrit l'inscription de l'utilisateur. Rend la commande qui était en place avant ('' : aucune), à garder pour la défaire. */
async function inscrit(voulue, lance) {
  const avant = valeur(await reg(['query', COMMANDE, '/ve'], lance));
  await reg(['add', CLE, '/ve', '/d', 'URL:NXM Protocol', '/f'], lance);
  await reg(['add', CLE, '/v', 'URL Protocol', '/d', '', '/f'], lance);
  await reg(['add', COMMANDE, '/ve', '/d', voulue, '/f'], lance);
  return avant;
}

/** Défait l'inscription : remet la commande d'avant, ou retire la clé de l'utilisateur (celle du poste, s'il y en a une, reprend). */
async function retire(avant, lance) {
  if (avant) await reg(['add', COMMANDE, '/ve', '/d', avant, '/f'], lance);
  else await reg(['delete', CLE, '/f'], lance);
}

/** Le lien `nxm://` porté par l'adresse reçue de VS Code (sa partie requête, brute ou encodée), ou ''. */
function lienRecu(requete) {
  let q = String(requete || '').trim();
  if (/^nxm%3a/i.test(q)) { try { q = decodeURIComponent(q); } catch { return ''; } }
  return /^nxm:\/\/[^/\s]+\/mods\/\d+\/files\/\d+/i.test(q) ? q : '';
}

/** Nom du programme d'une commande du registre, pour le dire à l'écran. */
const programme = (commande) => { const m = /^"([^"]+)"|^(\S+)/.exec(commande || ''); return m ? (m[1] || m[2]).split(/[\\/]/).pop() : ''; };

module.exports = { possible, etat, inscrit, retire, commandePour, lienRecu, programme, valeur, CLE };
