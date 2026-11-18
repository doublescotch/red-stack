// Red Stack : appel du moteur Python (red_stack.py --json). Aucune dépendance à VS Code : testable sous Node seul.
'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { T } = require('./langue');

/**
 * Cherche dans les dossiers ouverts des données Red Stack déjà là : un dossier « red_stack » qui porte un config.json.
 * Sert une fois, au premier lancement, pour proposer de les reprendre. Quatre niveaux au plus, nombre de dossiers borné.
 */
function trouveDonnees(dossiers, profondeur = 4, plafond = 20000) {
  let vus = 0;
  let niveau = dossiers.slice();
  for (let p = 0; p <= profondeur && niveau.length; p++) {
    const suivant = [];
    for (const d of niveau) {
      if (path.basename(d).toLowerCase() === 'red_stack' && fs.existsSync(path.join(d, 'config.json'))) return d;
      if (p === profondeur || ++vus > plafond) continue;
      try {
        for (const e of fs.readdirSync(d, { withFileTypes: true })) {
          if (e.isDirectory() && !e.name.startsWith('.') && e.name !== 'node_modules') suivant.push(path.join(d, e.name));
        }
      } catch { /* dossier illisible : ignoré */ }
    }
    niveau = suivant;
  }
  return '';
}

const PYTHON_MIN = [3, 11];                         // la plus ancienne version sous laquelle le banc du moteur a tourné (3.11 et 3.15)

/** Version d'un Python lancé par `commande` + `avant`, ou un refus : { version: [3, 12, 1] } ou { erreur }. */
function sondePython(commande, avant, lance = spawn) {
  return new Promise((resolve) => {
    let out = '', fini = false;
    const rend = (r) => { if (!fini) { fini = true; clearTimeout(garde); resolve(r); } };
    let p;
    try {
      p = lance(commande, [...avant, '-I', '-c', 'import sys; print("RS %d.%d.%d" % sys.version_info[:3])'], { windowsHide: true });
    } catch (e) {
      return resolve({ erreur: String(e.message || e) });
    }
    const garde = setTimeout(() => { try { p.kill(); } catch { /* déjà fini */ } rend({ erreur: 'délai' }); }, 10000);
    p.stdout.setEncoding('utf8').on('data', (d) => { out += d; });
    p.stderr.on('data', () => {});
    p.on('error', (e) => rend({ erreur: String(e.message || e) }));
    p.on('close', (code) => {
      const m = /^RS (\d+)\.(\d+)\.(\d+)\s*$/m.exec(out);
      rend(m ? { version: [+m[1], +m[2], +m[3]] } : { erreur: `code ${code}` });
    });
  });
}

/**
 * Cherche le Python qui lancera le moteur. La commande réglée d'abord ; si elle est celle par défaut, le lanceur de
 * Windows (`py -3`) et `python3` sont essayés aussi. Rend { commande, avant, version } ou { essais: [...], vieux? }.
 */
async function cherchePython(voulu, lance = spawn) {
  const defaut = !voulu || voulu === 'python';
  const candidats = defaut ? [['python', []], ['py', ['-3']], ['python3', []]] : [[voulu, []]];
  const essais = [];
  let vieux = null;
  for (const [commande, avant] of candidats) {
    const r = await sondePython(commande, avant, lance);
    const nom = [commande, ...avant].join(' ');
    if (r.version && (r.version[0] > PYTHON_MIN[0] || (r.version[0] === PYTHON_MIN[0] && r.version[1] >= PYTHON_MIN[1]))) {
      return { commande, avant, version: r.version.join('.') };
    }
    if (r.version) vieux = vieux || { nom, version: r.version.join('.') };
    essais.push(nom);
  }
  return { essais, vieux };
}

class Moteur {
  /** @param {{python: string, script: string, donnees: string, base?: string[], occupe?: (n: number) => void}} o */
  constructor(o) {
    this.python = o.python || 'python';             // commande réglée ; celle qui sert vraiment est cherchée au premier appel
    this.avant = [];                                // arguments du lanceur (`py -3`)
    this.trouve = null;                             // promesse de cherchePython, une fois par moteur
    this.cherche = o.cherche || cherchePython;
    this.script = o.script;
    this.donnees = o.donnees;                       // config.json, profils, registre de pose, caches, demande.json
    this.base = (o.base || []).concat(['--donnees', o.donnees]);   // arguments ajoutés à chaque appel
    this.langue = o.langue || (() => 'fr');         // langue des textes du moteur, lue à chaque appel (elle peut changer)
    this.occupe = o.occupe || (() => {});
    this.file = Promise.resolve();                  // un appel à la fois : le moteur écrit ses caches et le profil
    this.attente = 0;
  }

  /** Lance une commande du moteur et rend son JSON. `entree` : texte passé sur l'entrée standard (config --fixe -).
   *  `env` : variables d'environnement de cet appel seul (la clé d'API Nexus : jamais sur la ligne de commande). */
  run(args, entree, env) {
    this.occupe(++this.attente);
    const suite = this.file.then(() => this.lance(args, entree, env));
    this.file = suite.catch(() => {});
    return suite.finally(() => this.occupe(--this.attente));
  }

  /** Le Python du moteur, cherché une fois ; aucun : une erreur au code « PYTHON » que la page sait dire. */
  async pret() {
    if (!this.trouve) this.trouve = this.cherche(this.python);
    const r = await this.trouve;
    if (!r.commande) {
      this.trouve = null;                           // « Réessayer » relance la recherche
      throw Object.assign(new Error(T`Python introuvable (« ${r.essais.join(' », « ')} »).`), { code: 'PYTHON', essais: r.essais, vieux: r.vieux || null });
    }
    this.python = r.commande; this.avant = r.avant; this.version = r.version;
  }

  /** La commande Python telle qu'elle se tape (pour les lignes à copier). */
  commande() {
    return [this.python, ...this.avant].join(' ');
  }

  async lance(args, entree, env) {
    await this.pret();
    return new Promise((resolve, reject) => {
      const p = spawn(this.python, [...this.avant, '-I', this.script, ...args, ...this.base, '--langue', this.langue(), '--json'],
        { windowsHide: true, env: env ? { ...process.env, ...env } : process.env });
      let out = '', err = '';
      p.stdout.setEncoding('utf8').on('data', (d) => { out += d; });
      p.stderr.setEncoding('utf8').on('data', (d) => { err += d; });
      p.on('error', (e) => reject(new Error(T`Python introuvable (« ${this.python} ») : ${e.message}`)));
      p.on('close', (code) => {
        if (code) return reject(new Error((err || out).trim().slice(-3000) || T`red_stack.py : code ${code}`));
        try {
          resolve(JSON.parse(out));
        } catch {
          reject(new Error(`${T('Sortie illisible du moteur :')} ` + out.slice(0, 400)));
        }
      });
      p.stdin.on('error', () => {});
      p.stdin.end(entree === undefined ? '' : entree, 'utf8');
    });
  }
}

module.exports = { Moteur, trouveDonnees, cherchePython, PYTHON_MIN };
