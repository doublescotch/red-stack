// Red Stack : langues de l'interface. Le texte français du code EST la clé ; un catalogue `langues/<code>.json` donne
// le texte d'une autre langue, et ce qui lui manque reste en français. Trois fonctions, les mêmes dans l'extension et
// dans la page (la page reçoit le source de `fabrique` et le catalogue, voir `pourPage`) :
//   T`Aperçu du plan (${n})`      la clé est « Aperçu du plan ({0}) » ; T('texte {0}', a) marche aussi
//   N(n, '{n} fichier', '{n} fichiers')   pluriel : le catalogue porte un objet { one, few, many, other } sous la clé du singulier
// Le banc `tests/langues_test.py` relit le code et dit quelle clé manque à un catalogue, laquelle n'est plus utilisée.
'use strict';
const fs = require('fs');
const path = require('path');

// <fabrique>
function fabrique(langue, textes) {
  textes = textes || {};
  let regles = null;
  try { regles = new Intl.PluralRules(langue); } catch (e) { /* langue inconnue du moteur JavaScript : forme « other » */ }
  const pose = (s, v) => s.replace(/\{(\d+)\}/g, (m, i) => (Number(i) < v.length ? String(v[Number(i)]) : m));
  function T(s, ...v) {
    const cle = typeof s === 'string' ? s : s.reduce((a, x, i) => a + '{' + (i - 1) + '}' + x);
    const t = textes[cle];
    return pose(typeof t === 'string' ? t : cle, v);
  }
  function N(n, un, plusieurs, ...v) {
    const t = textes[un];
    let s = n > 1 ? plusieurs : un;
    if (t && typeof t === 'object') s = t[regles ? regles.select(Math.abs(Number(n)) || 0) : 'other'] || t.other || s;
    else if (typeof t === 'string') s = t;
    return pose(s.replace(/\{n\}/g, String(n)), v);
  }
  return { langue, T, N };
}
// </fabrique>

/** Langues livrées : le français (source, sans catalogue) et un fichier par autre langue dans `langues`. */
function langues(dossier) {
  const out = [{ code: 'fr', nom: 'Français' }];
  try {
    const rang = (f) => (f === 'en.json' ? '0' : '1') + f;          // l'anglais d'abord, puis l'ordre des codes
    for (const f of fs.readdirSync(path.join(dossier, 'langues')).sort((a, b) => (rang(a) < rang(b) ? -1 : 1))) {
      if (!/\.json$/.test(f)) continue;
      const t = JSON.parse(fs.readFileSync(path.join(dossier, 'langues', f), 'utf8'));
      out.push({ code: f.replace(/\.json$/, ''), nom: t._langue || f.replace(/\.json$/, '') });
    }
  } catch { /* dossier absent ou catalogue illisible : le français seul */ }
  return out;
}

/** Langue à montrer et son catalogue. `voulue` : un code, ou « auto » = la langue d'affichage de VS Code (`deVSCode`).
 *  Une langue que Red Stack n'a pas tombe sur l'anglais, puis sur le français. */
function charge(dossier, voulue, deVSCode) {
  const lu = (code) => { try { return JSON.parse(fs.readFileSync(path.join(dossier, 'langues', code + '.json'), 'utf8')); } catch { return null; } };
  const v = String(!voulue || voulue === 'auto' ? deVSCode || 'en' : voulue).toLowerCase();
  for (const code of [v, v.split('-')[0], 'en']) {
    if (code === 'fr') break;
    const textes = lu(code);
    if (textes) return { langue: code, textes };
  }
  return { langue: 'fr', textes: {} };
}

/** Ce que la page reçoit à la place de `{{langue}}` : la même fabrique, branchée sur le catalogue choisi. */
function pourPage(l) {
  const json = (x) => JSON.stringify(x).replace(/</g, '\\x3c').split(String.fromCharCode(0x2028)).join(' ').split(String.fromCharCode(0x2029)).join(' ');
  return `(${fabrique.toString()})(${json(l.langue)}, ${json(l.textes)})`;
}

// Langue en cours de l'extension : le français tant que `regle` n'a rien dit. T et N suivent la langue réglée, y compris
// dans les modules qui les ont pris par `require` avant.
let courante = { langue: 'fr', textes: {} };
let outils = fabrique('fr', {});
function regle(dossier, voulue, deVSCode) {
  courante = charge(dossier, voulue, deVSCode);
  outils = fabrique(courante.langue, courante.textes);
  return courante;
}

module.exports = { fabrique, langues, charge, pourPage, regle, enCours: () => courante, T: (...a) => outils.T(...a), N: (...a) => outils.N(...a) };
