"""Rendu de la page hors VS Code : Chrome sans tête, vrai état lu du moteur (lecture seule), faux `acquireVsCodeApi`.

  python -I test/rendu.py <red_stack.py> <dossier de sortie> <dossier des données> [chrome.exe]
Écrit une capture par vue (scripts et tweaks, liste, filtre par ressource, puces des conflits (paires d'archives, copies identiques), noms dans le jeu, conflits, ordre de chargement, paires de mods, ressources (onglet d'analyse), détail d'un pack, plan, tri, arrivages, réglages) et le DOM de chacune ; échoue si la table est vide, si la console
porte une erreur (CSP comprise) ou si un texte attendu manque. La politique de sécurité de la page est gardée telle quelle.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL, OUT = sys.argv[1], os.path.abspath(sys.argv[2])
DONNEES = os.path.abspath(sys.argv[3])
CHROME = sys.argv[4] if len(sys.argv) > 4 else r"C:\Program Files\Google\Chrome\Application\chrome.exe"
os.makedirs(OUT, exist_ok=True)
LANGUE = os.environ.get("RED_STACK_LANGUE", "fr")   # langue du rendu : fr (le code), ou un catalogue de langues/


def rs(*a):
    r = subprocess.run([sys.executable, "-I", TOOL, *a, "--donnees", DONNEES, "--langue", LANGUE, "--json"], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(r.stderr)
    return json.loads(r.stdout)


etat, profils, plan, conf, conflits = rs("etat"), rs("profils")["profils"], rs("plan"), rs("config"), rs("conflits")
convention = rs("convention")
maj = rs("nexus")                           # mises à jour : la vraie comparaison à Nexus (gardée six heures), compte d'exemple
maj_compte = {"cle": True, "nom": "vous", "premium": False, "reste_jour": 19990, "reste_heure": 500}
MAJ_VIDE = not maj["lignes"]              # dépôt entièrement à jour : rien à dessiner dans les vues qui jouent des lignes de mise à jour
for _i in range(len(maj["lignes"]), 4 if maj["lignes"] else 0):   # dépôt presque à jour : lignes d'exemple, la vue verrouillée en veut trois
    maj["lignes"].append(dict(maj["lignes"][0], cle=maj["lignes"][0]["cle"].replace(".zip", f" exemple {_i}.zip")))
if maj["lignes"]:                           # une ligne ignorée d'exemple, pour voir son rang et son bouton
    maj["lignes"][-1] = dict(maj["lignes"][-1], ignore=True)
cfr = rs("conflits", "--ressources")
objets = rs("objets")                      # objets des mods face à la sauvegarde la plus récente (lue, jamais écrite)
dep = rs("prerequis")                       # « Dépendances » : prérequis du dépôt (socles), puis la chaîne de CET (ou d'un cadre du jeu)
_cet = next((c for c in dep["cadres"] if c["cadre"] == "cet"), {"par": []})["par"]
chaine = rs("prerequis", "--mod", _cet[0], "--chute") if _cet else rs("prerequis", "--cadre", "redscript", "--chute")
code = rs("scripts")                        # conflits de code : tout ce qui est à regarder ou à revoir, soixante « sans action » pour la capture
code["trouvailles"] = ([t for t in code["trouvailles"] if t["niveau"] in ("attention", "revoir")]
                       + [t for t in code["trouvailles"] if t["niveau"] not in ("attention", "revoir")][:60])
# le plan réel est souvent vide : un mod coupé, un lien repris et un fichier pris d'exemple, pour voir ces lignes
_z = [m["cle"] for m in etat["mods"] if m["actif"]][:2]
plan = dict(plan, coupes=plan.get("coupes", []) + [{"zip": _z[0], "au_registre": 2, "retire": 0, "garde": 0, "rendu": 0,
                                                     "repris": [{"zip": _z[1], "n": 2}], "tenu_par": [{"zip": _z[1], "n": 14}]}],
            lie=plan["lie"] + [{"dest": "archive/pc/mod/exemple.archive", "zip": _z[1], "entree": "exemple.archive", "crc": 0, "taille": 1, "ancien": _z[0]}],
            pris=plan.get("pris", []) + [{"dest": "bin/x64/reshade-shaders/Shaders/Exemple.fx", "zip": _z[1], "entree": "x", "crc": 0, "taille": 1}])
plan["modlist"] = [{"dest": "archive/pc/mod/modlist.txt", "zip": "", "crc": 0, "action": "ecrire", "lignes": ["exemple.archive"]}]
plan["compte"] = dict(plan["compte"], lie=len(plan["lie"]), pris=len(plan["pris"]), modlist=1)
# prérequis : un cadre absent d'exemple dans le plan et sur une ligne de la liste ; la fiche d'un vrai mod à qui un mod déclaré
# sur Nexus manque (sinon le premier mod actif), complétée d'un cadre absent, d'un prérequis hors Nexus et d'un « exigé par »
_cadre = {"cadre": "tweakxl", "mod": 4197, "nom": "TweakXL", "notes": "", "url": "", "sources": ["fichiers"], "par": [], "etat": "absent", "optionnel": False, "ident": "c:tweakxl", "ignore": False}
plan["prerequis"] = plan.get("prerequis", []) + [{"zip": _z[0], "requis": [_cadre]}]
for _m in etat["mods"]:
    if _m["cle"] == _z[0]:
        _m["prerequis"] = dict(_m["prerequis"] or {"a_voir": 0, "optionnels": 0, "requis_par_actifs": 0}, manque=1)
_req = next((m["cle"] for m in etat["mods"] if m["actif"] and (m.get("prerequis") or {}).get("a_voir")), _z[1])
detail_req = rs("detail", "--mod", _req)
detail_req["actif"] = False
detail_req["prerequis"] = dict(detail_req["prerequis"], nexus="jamais lu", requis_par=[_z[0]], requis_par_actifs=1,
                               requis=detail_req["prerequis"]["requis"] + [_cadre, {"cadre": None, "mod": 0, "nom": "ReShade", "notes": "Download and install it", "url": "https://reshade.me/",
                                                                                     "sources": ["nexus"], "par": [], "etat": "externe", "optionnel": False, "ident": "x:reshade", "ignore": False},
                                                                                    dict(_cadre, nom="Codeware", cadre="codeware", ident="c:codeware", ignore=True),
                                                                                    dict(_cadre, nom="RedFunctions", cadre=None, mod=0, ident="r:redfunctions|", sources=["code"], etat="coupé",
                                                                                         souple=False, usages=4, preuves=[{"fichier": "r6/scripts/Exemple/Main.reds", "ligne": 3, "genre": "i",
                                                                                                                           "cible": "RedFunctions.Storage", "souple": False, "zip": ""}])])
# dépôt sans arrivage (dossiers d'arrivée vides) : une ligne d'exemple, tirée d'un zip rangé du dépôt, pour voir la vue
if not any(not r["convertir"] for r in convention["lignes"]):
    import fnmatch                          # un zip rangé, pas un retiré : « Contenu… » refuse les zips des retirés
    _ret = lambda m: any(fnmatch.fnmatch((m["lieu"] or "").lower(), x.lower()) for x in conf["convention"]["retires"])
    _x = next((m for m in etat["mods"] if m["lieu"] and not _ret(m)), etat["mods"][0])
    convention["lignes"].append({"cle": _x["cle"], "section": _x["section"], "lieu": _x["lieu"] or "__NEW", "genre": "nouveau", "nom": _x["nom"],
                                 "taille": _x["taille"], "convertir": False, "statut": "hors_nexus", "mod": None})
    convention["compte"] = dict(convention.get("compte") or {}, hors_nexus=1)
# arrivages : une mise à jour reconnue d'exemple sur la première ligne (un zip sûr, un autre du même mod), pour voir le geste
for _r in convention["lignes"]:
    if not _r["convertir"]:
        _r["maj_de"] = [{"cle": _z[0], "nom": _z[0].split("/")[-1], "section": _z[0].split("/")[0], "lieu": "", "version": "1.0", "annotation": "", "sur": True,
                         "propose": "Exemple-1234-1-1-1700000999.zip"},
                        {"cle": _z[1], "nom": _z[1].split("/")[-1], "section": _z[1].split("/")[0], "lieu": "", "version": "0.9", "annotation": "", "sur": False,
                         "propose": "Exemple Addon-1234-1-1-1700000999.zip"}]
        break
nxm_etat = {"possible": True, "inscrit": False, "commande": "", "systeme": r'"C:\Program Files\Vortex\Vortex.exe" -d "%1"', "programme": "Vortex.exe", "avant": None, "voulue": ""}
contenu_cle = next(r["cle"] for r in convention["lignes"] if not r["convertir"])
contenu = rs("contenu", "--cle", contenu_cle)
if not contenu["ops"]:                      # la première ligne n'a rien à renommer : une proposition d'exemple, pour voir la table
    contenu = dict(contenu, etat="a_renommer", base="Exemple", ops=[{"de": "archive/pc/mod/exemple.archive", "vers": "archive/pc/mod/Exemple.archive"}],
                   gardes=[{"chemin": "r6/scripts/zz_commun", "raison": "dossier à préfixe d'ordre du créateur"}])
poste = {"langue": {"voulue": "auto", "enCours": LANGUE, "deVSCode": "en", "langues": [{"code": "fr", "nom": "Français"}, {"code": "en", "nom": "English"}]},
         "theme": {"theme": "Red Stack Jaune", "barre": False, "themes": ["Red Stack Rouge", "Red Stack Jaune"]}, "python": "python", "donnees": DONNEES, "donneesDefaut": r"C:\Users\vous\AppData\Roaming\Code\User\globalStorage\doublescotch.red-stack\donnees",
         "moteur": TOOL, "mcp": "claude mcp add red-stack -- python -I \"...\\red_stack_mcp.py\" --donnees \"" + DONNEES + "\""}
poste["mcpWk"] = poste["mcp"].replace("red-stack --", "red-stack-wolvenkit --").replace("red_stack_mcp.py", "red_stack_wk_mcp.py")
pack = next((m["cle"] for m in etat["mods"] if not m["lieu"] and m["actif"] and len(m["options"]) > 2), etat["mods"][0]["cle"])
detail = rs("detail", "--mod", pack)
noms = rs("noms", "--mod", pack)
if not any(u["cites"] for u in noms["unites"]) and noms["unites"]:   # un avertissement d'exemple, pour voir la ligne
    noms["unites"][0] = dict(noms["unites"][0], cites=[{"zip": pack, "fichier": "r6/scripts/exemple.reds", "soi": False}])
# historique : deux applications et un geste du dépôt d'exemple, sur de vrais mods du profil (le vrai est souvent court)
journal = {"fichier": os.path.join(DONNEES, "historique.jsonl"), "total": 3, "trouve": 3, "entrees": [
    {"date": "2026-11-17T14:02:11", "geste": "applique", "profil": "actuel", "reel": True, "compte": {"pose": 3, "retire": 2, "lie": 3},
     "mods": [{"cle": _z[0], "version": "1.1", "fait": "mis à jour", "depuis": "1.0", "pose": 2, "lie": 2},
              {"cle": _z[1], "version": "2.0", "fait": "posé", "pose": 1, "lie": 1},
              {"cle": "12_Weapons/Ancien Mod-1234-1-0-1700000000.zip", "version": "1.0", "fait": "retiré", "retire": 2}],
     "echecs": [], "sauvegarde": None},
    {"date": "2026-11-17T13:40:00", "geste": "parque", "de": r"D:\Depot\12_Weapons\Ancien Mod-1234-1-0-1700000000.zip",
     "vers": r"D:\Depot\12_Weapons\__RAM\Ancien Mod-1234-1-0-1700000000.zip"},
    {"date": "2026-11-17T09:12:00", "geste": "supprime", "de": r"D:\Depot\12_Weapons\__DEL\Ancien Mod-1234-0-9-1690000000.zip"},
    {"date": "2026-11-16T22:15:40", "geste": "applique", "profil": "actuel", "reel": True, "compte": {"modlist": 1}, "mods": [], "echecs": [], "sauvegarde": None}]}
# magasin et sauvegardes : le vrai magasin, plus un arbre sans mod et une retouche d'exemple, pour voir ces lignes
magasin = rs("magasin")
magasin["sans_mod"] = magasin["sans_mod"] + [{"arbre": "12_Weapons/Ancien Mod-1234-1-0-1700000000", "chemin": r"E:\Jeu - Red Stack\12_Weapons\Ancien Mod-1234-1-0-1700000000", "fichiers": 12, "octets": 734003200}]
magasin["octets_sans_mod"] = sum(x["octets"] for x in magasin["sans_mod"])
magasin["retouches"] = magasin["retouches"] + [{"zip": _z[0], "entree": "r6/tweaks/exemple.yaml", "dest": "r6/tweaks/exemple.yaml"}]
sauve = {"dossier": r"D:\Sauvegardes", "sauvegardes": [
    {"nom": "_reglages_2026-11-17_140211", "cree": "2026-11-17 14:02", "fichiers": 343, "octets": 38602089, "chemin": r"D:\Sauvegardes\_reglages_2026-11-17_140211", "jeu_lance": False},
    {"nom": "_reglages_2026-11-16_091500", "cree": "2026-11-16 09:15", "fichiers": 338, "octets": 38100000, "chemin": r"D:\Sauvegardes\_reglages_2026-11-16_091500", "jeu_lance": True}]}
sauve_compare = {"sauvegarde": sauve["sauvegardes"][0], "changes": ["bin/x64/plugins/cyber_engine_tweaks/mods/Exemple/settings.json"],
                 "absents": ["r6/storages/Exemple/etat.json"], "identiques": 341, "restaure": False, "copies": None}
# FOMOD : le vrai installateur le plus fourni du dépôt (lu seul), montré comme s'il était à la racine de sa pile et suivi
_fo = max((m for m in etat["mods"] if m.get("fomod") and not m["fomod"].get("erreur")), key=lambda m: m["fomod"]["choix"], default=None)
if _fo:
    fomod = dict(rs("fomod", "--cle", _fo["cle"]), lieu="", genre="actif", par_fomod=True, actif=True, libre=False)
else:
    fomod = {"cle": pack, "nom": "Exemple.zip", "module": "Exemple", "actif": True, "lieu": "", "genre": "actif", "par_fomod": True, "libre": False,
             "regle": False, "hors_jeu": True, "choix": {}, "limites": [], "compte": {"poses": 1, "hors_jeu": 0, "zip": 2},
             "fichiers": [{"entree": "a/x.archive", "dest": "archive/pc/mod/x.archive", "hors_jeu": False}],
             "pages": [{"nom": "Couleur", "visible": True, "groupes": [{"cle": "Couleur › Couleur", "nom": "Couleur", "type": "SelectExactlyOne", "plugins": [
                 {"nom": "Rouge", "desc": "", "image": None, "usage": "Recommended", "choisi": True, "fichiers": 1, "fige": False}]}]}]}
_g = next((g for p in fomod["pages"] if p["visible"] for g in p["groupes"] if g["plugins"]), None)
if _g:                                      # une image d'exemple sur le premier choix : la politique de sécurité doit la laisser passer
    _g["plugins"][0] = dict(_g["plugins"][0], image="fomod/exemple.png")
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
detail_fo = dict(detail, fomod={"actif": True, "module": fomod["module"], "fichiers": fomod["compte"]["poses"], "choix": 2, "regle": False})
maj_occupe = {"cles": [r["cle"] for r in maj["lignes"][:3]], "fait": [r["cle"] for r in maj["lignes"][:1]],
              "nom": maj["lignes"][1]["cle"] if len(maj["lignes"]) > 1 else "", "prepare": False}
# langue : la fabrique de `langue.js` (entre ses deux marques), branchée sur le catalogue demandé, comme le fait l'extension
_lj = open(os.path.join(HERE, "..", "langue.js"), encoding="utf-8").read()
FABRIQUE = _lj[_lj.index("// <fabrique>") + len("// <fabrique>"):_lj.index("// </fabrique>")].strip()
TEXTES = json.load(open(os.path.join(HERE, "..", "langues", LANGUE + ".json"), encoding="utf-8")) if LANGUE != "fr" else {}
page = (open(os.path.join(HERE, "..", "media", "page.html"), encoding="utf-8").read().replace("{{nonce}}", "banc")
        .replace("{{langue}}", "(" + FABRIQUE + ")(" + json.dumps(LANGUE) + ", " + json.dumps(TEXTES, ensure_ascii=False).replace("</", "<\\/") + ")"))
# textes attendus dans une autre langue que le français (RED_STACK_LANGUE=en) : quelques-uns par vue, pris au catalogue
AILLEURS = {"en": {"liste": ["active mods out of", "Plan preview", "Fold / unfold all", "Full names"], "historique": ["recorded actions", "Applied"],
                   "magasin": ["Real size", "Windows Explorer adds up", "Trees without an active mod", "Purge "], "conflits": ["archives loaded", "per archive", "Wins over"],
                   "code": ["to look at", "to review", "Code conflict", "Filter: mod, method"],
                   "objets": ["with no item owned", "Saves folder…", "Filter: mod or item", "Mod detail", "<b>Owned</b>", "Weapon attachments", "Equipment mods"], "detail": ["Pack options", "Show the zip", "Rename the content…"],
                   "plan": ["already in place", "Apply to the game…", "Plan of the profile", "mod disabled"], "arrivages": ["Wanted name", "Re-read Nexus", "File the update…"],
                   "maj": ["Zip of the repository", "New version", "free account", "Stop ignoring"], "fomod": ["Installer of “", "What the installer installs"],
                   "dependances": ["Here, the mods that the most active mods depend on", "Filter: mod…", "required by "],
                   "chaine": ["← Foundations", "What falls without it", "What it needs", "Tier 1", "falls with: ", "Its chain", "Mod detail"],
                   "graphe": ["Tier 1 · "],
                   "prerequis": ["read in its code", "What falls without it…", "Everything it needs…", "<h3>Requirements</h3>", "deduced from its files", "Read on Nexus", "⚠ requirement", "outside Nexus, not checked", "Required by 1 mod of the repository, 1 of them active"],
                   "noms": ["In-game names of", "Author's name"], "ressource": ["per resource", "taken from", "lost by"],
                   "reglages": ["<legend>Language</legend>", "Automatic (VS Code: en)", "Settings backups", "Back up now", "Save", "<legend>Theme</legend>", "Current theme: <b>Red Stack Jaune</b>"]}}
fails = []
for vue, suite, attendu in (("liste", "", ["mods actifs sur", "Aperçu du plan", 'class="pile"', 'class="cf"', 'data-act="parque"', 'id="histo"', 'id="scripts"', "Dernière lecture à", 'aria-label="Actualiser"', 'id="plieTout"', 'id="aide"']),
                            ("plie", "document.getElementById('plieTout').click();"
                                     "document.title = 'plie ' + document.querySelectorAll('#liste details.pile[open]').length + ' sur ' + (document.querySelectorAll('#liste details.pile').length > 3 ? 'n' : 'trop peu');",
                             ["<title>plie 0 sur n</title>"]),
                            ("deplie", "document.getElementById('plieTout').click(); document.getElementById('plieTout').click();"
                                       "document.title = 'deplie ' + (document.querySelectorAll('#liste details.pile:not([open])').length);",
                             ["<title>deplie 0</title>"]),
                            ("plie_conflits", "document.getElementById('plieTout').click();"
                                              "const n = document.querySelectorAll('#conflits details.arch').length;"
                                              "document.title = 'ouverts ' + (n > 3 && document.querySelectorAll('#conflits details.arch[open]').length === n ? 'tous' : 'non');",
                             ["<title>ouverts tous</title>", "Gagne sur"]),
                            ("historique", "recoit({t:'journal', data: D.journal});",
                             ["Historique", "gestes enregistrés", "Appliqué", "mis à jour", "(depuis 1.0)", "Parqué", "→ dossier __RAM", "Supprimé", "→ corbeille du système", "red_stack_journal", 'class="pastille vert"']),
                            ("magasin", "document.getElementById('magasin').click(); recoit({t:'magasin', data: D.magasin});",
                             ["Poids réel", "L'Explorateur de Windows additionne", "au magasin", "aucune place en plus", "Arbres sans mod actif", "Ancien Mod-1234", "Purger ",
                              'data-purge="1"', "Retouches", 'data-retouche="', "red_stack_magasin"]),
                            ("conflits", "document.querySelector('[data-grille=mod]').click();"
                                         "document.querySelector('#conflits details.arch summary').click();",
                             ["archives chargées", "par archive", "perd ", "Gagne sur", 'class="res"', "remplacent le jeu de base", '<body class="analyse conf"', "Scripts et tweaks…", 'data-codefen="1"']),
                            ("code", "recoit({t:'conflitsCode', data: D.code});"
                                     "document.querySelectorAll('#conflits details.code summary').forEach((x, i) => { if (i < 3) x.click(); });",
                             ["à regarder", "à revoir", "sans action", "de lecture", "Conflits d'archives…", "Conflit de code", '<body class="analyse code conf"', "Filtrer : mod, méthode", 'data-csorte="', 'data-cniv="limites"',
                              'data-ouvre="', "Ouvrir le détail de ce mod", "prévu, pas observé en jeu", "de code sur"]),
                            ("objets", "recoit({t:'objets', data: D.objets});"
                                       "document.querySelectorAll('#conflits details.code summary').forEach((x, i) => { if (i < 2) x.click(); });",
                             ['<body class="analyse objets conf"', "sans objet possédé", "Dossier des parties…", 'id="opartie"', 'data-ofiltre="aucun"',
                              'data-osorte="', "Filtrer : mod ou objet", "Détail du mod", 'data-ouvre="', "<b>Possédé</b>",
                              'data-osorte="accessoire"', 'data-osorte="module"', "Accessoires d'armes", "Mods d'équipement", "tweakdb.bin"]),
                            # transfert : des objets cochés (case d'un mod, « possédés montrés »), rangés par sorte, une commande de console copiée ; rien d'autre n'est envoyé
                            ("objets_transfert", "recoit({t:'objets', data: D.objets});"
                                                 "const q = (s) => document.querySelector('#conflits ' + s), n0 = (window.POSTES || []).length;"
                                                 "const vide = q('button[data-ocopie]').disabled;"
                                                 "const cm = q('input[data-ochoixmod]'); cm.checked = true; cm.dispatchEvent(new Event('change', {bubbles: true}));"
                                                 "const duMod = D.objets.mods.find((m) => m.prov === cm.dataset.ochoixmod).objets.length;"
                                                 "q('button[data-ocoche=rien]').click(); q('button[data-ocoche=possedes]').click();"
                                                 "const possedes = new Set(D.objets.mods.flatMap((m) => m.objets.filter((x) => x.lieux.length).map((x) => x.rec))).size;"
                                                 "q('button[data-opar=sorte]').click(); const dt = q('details[data-groupe^=\"os:\"]'); dt.open = true; dt.dispatchEvent(new Event('toggle'));"
                                                 "const cases = document.querySelectorAll('#conflits input[data-ochoix]').length, cochees = document.querySelectorAll('#conflits input[data-ochoix]:checked').length;"
                                                 "q('button[data-ocopie]').click();"
                                                 "const envois = window.POSTES.slice(n0), c = envois.filter((x) => x.t === 'copie');"
                                                 "const sur = vide && duMod > 0 && cases > 0 && (possedes === 0 || (cochees > 0 && c.length === 1 && c[0].texte.split('; ').length === possedes && /^Game\\.AddToInventory\\(\"[\\w.\\-]+\", 1\\)/.test(c[0].texte)));"
                                                 "document.title = 'transfert ' + (sur && envois.every((x) => x.t === 'copie') ? 'ok' : 'non ' + [vide, duMod, cases, cochees, possedes, c.length]);",
                             ["<title>transfert ok</title>", '<body class="analyse objets conf"', 'data-opar="sorte" class="on"', 'data-ocopie="1"', "Copier la commande de console", "Transfert vers une autre partie", 'data-groupe="os:']),
                            ("dependances", "recoit({t:'dependances', data: D.dep});",
                             ['<body class="analyse dependances conf"', "Ici, les mods dont dépendent le plus de mods actifs", 'class="socles"', 'data-ddepart="',
                              "exigé par ", "mods actifs", "lu dans le code", "Filtrer : mod…"]),
                            ("chaine", "recoit({t:'conflitsCible', cle: D.chaine.depart + '|chute'}); recoit({t:'dependances', data: D.dep}); recoit({t:'chaine', data: D.chaine});",
                             ["← Socles", "Ce qui tombe sans lui", "Ce qu'il lui faut", "Palier 1", "tombe avec : ", "Sa chaîne", 'data-dsens="chute" class="on"',
                              'data-dvue="graphe"', "ne se chargent plus.", "Détail du mod"]),
                            ("graphe", "recoit({t:'conflitsCible', cle: D.chaine.depart + '|chute'}); recoit({t:'dependances', data: D.dep}); recoit({t:'chaine', data: D.chaine});"
                                       "document.querySelector('[data-dvue=graphe]').click();"
                                       "const g = document.querySelector('#conflits g.noeud[data-ddepart]'); g.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));"
                                       "document.title = 'graphe ' + document.querySelectorAll('#conflits g.noeud').length + ' mods, ' + document.querySelectorAll('#conflits path.lien').length + ' traits, '"
                                       " + document.querySelectorAll('#conflits path.lien.lit').length + ' éclairé(s)';",
                             ['<svg viewBox="0 0', 'class="noeud depart"', 'class="lien ferme"', 'class="palier"', 'data-dzoom="1.25"', 'data-dvue="graphe" class="on"']),
                            ("ordre", "document.querySelectorAll('#conflits details.arch summary').forEach((x, i) => { if (i < 4) x.click(); });",
                             ["Changer l'ordre", "Renommer dans le jeu…", "Passer de", 'data-sens="']),
                            ("paires", "document.querySelector('[data-grille=paires]').click();"
                                       "document.querySelector('#conflits details.arch summary').click();",
                             ["par paire de mods", 'class="verbe">gagne sur', "d'archives", 'class="res"']),
                            ("puces", "document.querySelector('[data-puce=paires]').click();",
                             ["par paire d'archives", "d'archives sur", 'class="paire"', 'data-puce="paires"', 'class="puce on"']),
                            ("fichier", "recoit({t:'conflitsRessources', data: D.cfr});"
                                        "document.getElementById('cherche').value = D.cfr.ressources[0].ressource.split('\\\\').pop().slice(0, 12);"
                                        "document.getElementById('cherche').dispatchEvent(new Event('input'));",
                             ["Filtrer : mod, archive ou ressource", "en copie identique", 'details class="arch"', "Les conflits se jouent ressource par ressource"]),
                            ("identiques", "document.querySelector('[data-puce=identiques]').click();"
                                           "recoit({t:'conflitsRessources', data: D.cfr});",
                             ["livrées à l'identique", "copie identique dans", 'data-resmode="identiques" class="on"']),
                            ("ressource", "document.querySelector('[data-grille=ressource]').click();"
                                          "recoit({t:'conflitsRessources', data: D.cfr});",
                             ["par ressource", "prise dans", "perdue par", "remplace le jeu de base", "Jeu de base seulement"]),
                            ("detail", "recoit({t:'detail', data: D.detail});", ["Options du pack", "Montrer le zip", 'data-zipnom="', "Renommer le zip…", 'data-zippile="', "Changer de pile…", "Fichiers", "Renommer le contenu…", 'details class="dossier"', 'id="poignee"']),
                            ("noms", "recoit({t:'detail', data: D.detail}); document.querySelector('[data-nomsmod]').click();"
                                     "E_noms();",
                             ["Noms dans le jeu de", "Nom de l'auteur", "Dans le jeu", 'id="nmNote"', "data-nomde=", "Cité par son nom"]),
                            ("prerequis", "recoit({t:'detail', data: D.detailReq}); document.querySelector('button[data-filtre=prerequis]').click();",
                             ["<h3>Prérequis</h3>", "déduit de ses fichiers", "Lire sur Nexus", 'data-reqlit="', 'data-reqignore="c:tweakxl"', 'data-reqreprend="c:codeware"', "Exigé par 1 mod du dépôt, dont 1 actifs", "hors Nexus, non contrôlé", "Note de l'auteur : Download and install it",
                              "⚠ prérequis", 'data-filtre="prerequis" class="on"', "1 mod actif exige ce mod, qui n'est pas actif.", 'class="pastille rouge"', "lu dans son code", "vu dans r6/scripts/Exemple/Main.reds, ligne 3 : RedFunctions.Storage", "3 autres usages",
                              "Ce qui tombe sans lui…", "Tout ce qu'il lui faut…", 'data-depfen="']),
                            ("plan", "recoit({t:'plan', data: D.plan});", ["mod actif sans un de ses prérequis", "exige TweakXL (absent)", "Voir les fichiers", "déjà en place", "Appliquer au jeu", "Plan du profil", "mod coupé", "repris à l'identique", "déjà tenus avec un autre contenu", "fichiers communs repris de", "pris au registre pour un mod", "modlist.txt à écrire (1 ligne)"]),
                            ("tri", "for (const i of [1, 2]) document.querySelector('th[data-tri=taille]').click();"
                                    "document.querySelector('button[data-filtre=actifs]').click();",
                             ["Taille ▼", 'data-filtre="actifs" class="on"', 'data-act="nexus"']),
                            ("filtre_neufs", "document.querySelector('button[data-filtre=neufs]').click();"
                                             "const n = D.etat.mods.filter((r) => (r.lieu ? r.genre === 'nouveau' : r.etat === 'nouveau dans le dépôt')).length;"
                                             "document.title = 'neufs ' + (document.querySelectorAll('#liste tr[data-cle]').length === n ? 'ok' : 'non ' + n);",
                             ["<title>neufs ok</title>", 'data-filtre="neufs" class="on"']),
                            ("filtre_parques", "document.querySelector('button[data-filtre=parques]').click();"
                                               "const n = D.etat.mods.filter((r) => r.lieu && r.genre === 'parqué').length;"
                                               "const p = document.querySelectorAll('#liste tr[data-cle]').length, q = document.querySelectorAll('#liste button[data-act=retire]').length;"
                                               "document.querySelector('button[data-filtre=retires]').click();"
                                               "const m = D.etat.mods.filter((r) => r.lieu && r.genre === 'retiré').length;"
                                               "const base = n > 0 && p === n && q === n && document.querySelectorAll('#liste tr[data-cle]').length === m && !document.querySelector('#liste button[data-act=retire]');"
                                               # la case d'une pile, dans ces filtres, coche un lot : elle ne bascule rien au profil ; le lot part en une demande
                                               "document.querySelector('button[data-filtre=parques]').click();"
                                               "const c = document.querySelector('#liste input[data-pile-lot]'); c.checked = true; c.dispatchEvent(new Event('change', {bubbles: true}));"
                                               "const coches = document.querySelectorAll('#liste input[data-lot]:checked').length, barre = !!document.querySelector('#puces .lot');"
                                               "document.querySelector('#puces button[data-lotvers=retires]').click();"
                                               "const lot = window.POSTES.filter((x) => x.t === 'deplaceLot');"
                                               "const sur = !window.POSTES.some((x) => x.t === 'bascule') && coches > 0 && barre && lot.length === 1 && lot[0].vers === 'retires' && lot[0].retour === 'liste' && lot[0].cles.length === coches && document.querySelectorAll('#liste input[data-lot]:checked').length === coches;"
                                               "document.title = 'ranges ' + (base && sur ? 'ok' : 'non ' + base + ' ' + sur);",
                             ["<title>ranges ok</title>", 'data-filtre="parques" class="on"', 'data-pile-lot="1"', 'data-act="retire"']),
                            # filtre « Coupés » : la case coche un lot, la ligne reste ; « Activer » part par la voie des cases ; un bouton sans objet n'est pas montré
                            ("filtre_coupes", "const deux = D.etat.mods.filter((r) => !r.lieu).slice(0, 2); deux.forEach((r) => { r.actif = false; r.etat = 'coupé'; r.fichiers_poses = 0; });"
                                              "recoit({t:'etat', data: D.etat, profils: D.profils});"
                                              "document.querySelector('button[data-filtre=coupes]').click();"
                                              "const n = D.etat.mods.filter((r) => !r.lieu && !r.actif && r.etat.startsWith('coupé')).length, lignes = () => document.querySelectorAll('#liste tr[data-cle]').length;"
                                              "const q = (s) => !!document.querySelector('#puces ' + s), coche = (x) => { x.checked = true; x.dispatchEvent(new Event('change', {bubbles: true})); };"
                                              "const vue = lignes() === n && !document.querySelector('#liste input[data-case]') && !q('.lot');"
                                              "coche(document.querySelector('#liste input[data-lot]'));"
                                              "const barre = lignes() === n && q('button[data-lotactive]') && q('button[data-lotvers=parques]') && q('button[data-lotvers=retires]') && !q('button[data-lotvers=pile]') && !(window.POSTES || []).some((x) => /^bascule/.test(x.t));"
                                              "document.querySelector('#puces button[data-lotactive]').click();"
                                              "const b = window.POSTES.filter((x) => x.t === 'basculeLot');"
                                              "const actif = b.length === 1 && b[0].mods.length === 1 && b[0].mods[0][1] === true && lignes() === n - 1 && !q('.lot');"
                                              "document.querySelector('button[data-filtre=parques]').click();"
                                              "const p = document.querySelector('#liste input[data-lot]'); if (p) coche(p);"
                                              "const sans = !p || (q('button[data-lotvers=pile]') && q('button[data-lotvers=retires]') && !q('button[data-lotvers=parques]') && !q('button[data-lotactive]'));"
                                              "document.querySelector('button[data-filtre=coupes]').click();"
                                              "coche(document.querySelector('#liste input[data-pile-lot]'));"
                                              "document.title = 'coupes ' + (vue && barre && actif && sans ? 'ok' : 'non ' + [vue, barre, actif, sans]);",
                             ["<title>coupes ok</title>", 'data-filtre="coupes" class="on"', 'data-lotactive="1"', 'data-pile-lot="1"', "Cocher ce mod coupé pour"]),
                            ("plie_vues", "document.getElementById('maj').click(); recoit({t:'maj', data: D.maj, compte: D.majCompte, dit: ''});"
                                          "const b = document.querySelectorAll('#majs tr.tpile').length; document.getElementById('plieTout').click();"
                                          "const plie = document.querySelectorAll('#majs tr.tpile.plie').length === b && !document.querySelector('#majs tr[data-cle]');"
                                          "document.getElementById('plieTout').click();"
                                          "const ouvert = !document.querySelector('#majs tr.tpile.plie') && !!document.querySelector('#majs tr[data-cle]');"
                                          "document.title = 'vues ' + (b > 0 && plie && ouvert ? 'ok' : 'non');",
                             ["<title>vues ok</title>"]),
                            # pile de la racine : un zip d'exemple posé à la racine du dépôt ; la bande dit son nom dans la langue, le code reste dans les données
                            ("racine", "const z = Object.assign({}, D.etat.mods.find((r) => !r.lieu), {cle: '(racine)/Exemple-1234-1-0-1700000000.zip', section: '(racine)', nom: 'Exemple-1234-1-0-1700000000.zip'});"
                                       "const e = Object.assign({}, D.etat, {sections: D.etat.sections.concat(['(racine)']), mods: D.etat.mods.concat([z])});"
                                       "recoit({t:'etat', data: e, profils: D.profils});"
                                       "const b = document.querySelector('#liste details.pile[data-pile=\"(racine)\"]');"
                                       "const dit = b ? b.querySelector('summary .nom').textContent : '';"
                                       "if (b) b.scrollIntoView();"
                                       "document.title = 'racine ' + (b && dit !== '(racine)' && dit.startsWith('(') && b.querySelectorAll('tr[data-cle]').length === 1 ? 'ok' : 'non ' + dit);",
                             ["<title>racine ok</title>", 'data-pile="(racine)"']),
                            ("verrou", "recoit({t:'verrou', on: true});"
                                       "const pris = document.querySelector('body > main').inert && document.getElementById('puces').inert && getComputedStyle(document.getElementById('verrou')).display === 'block';"
                                       "recoit({t:'verrou', on: false});"
                                       "const rendu = !document.querySelector('body > main').inert && getComputedStyle(document.getElementById('verrou')).display === 'none';"
                                       # cases cochées à la suite : rien ne part tout de suite, et un état relu entre-temps ne défait pas les coches
                                       "const cs = [...document.querySelectorAll('#liste input[data-case]:checked')].slice(0, 3);"
                                       "for (const c of cs) { c.checked = false; c.dispatchEvent(new Event('change', {bubbles: true})); }"
                                       "const rienParti = !window.POSTES.some((x) => x.t === 'bascule' || x.t === 'basculeLot');"
                                       "const cles = cs.map((c) => c.dataset.case); recoit({t:'etat', data: D.etat, profils: D.profils});"
                                       "const gardees = cles.every((k) => { const c = [...document.querySelectorAll('#liste input[data-case]')].find((x) => x.dataset.case === k); return c && !c.checked; });"
                                       "document.title = 'verrou ' + (pris && rendu && cs.length === 3 && rienParti && gardees ? 'ok' : 'non ' + [pris, rendu, cs.length, rienParti, gardees]);",
                             ["<title>verrou ok</title>", 'id="verrou"']),
                            ("arrivages", "document.getElementById('arriv').click(); recoit({t:'convention', data: D.convention});"
                                          "document.querySelector('[data-contenu]').click(); recoit({t:'contenu', cle: D.contenuCle, data: D.contenu});",
                             ["Nom voulu", "Renommer ", 'id="arrConvertit"', 'id="arrContenu"', "Relire Nexus", "← Liste des mods", 'data-nom="', "Remonter dans la pile", "Parquer…", 'id="arrTout"', 'id="arrRemonte"', "Nom du mod dans les fichiers", "dans le zip…", "data-vers=",
                              "Mise à jour de «", "Ranger la mise à jour…", 'data-range="', "Ou à la place de…", "sans clé d'API", "peut aussi changer de dossier"]),
                            ("dossier", "document.getElementById('arriv').click(); recoit({t:'convention', data: D.convention});"
                                        "document.querySelector('[data-contenu]').click();"
                                        "recoit({t:'contenu', cle: D.contenuCle, data: {etat: 'a_renommer', base: 'Exemple', notes: [], gardes: [], fichiers: ['archive/pc/mod/Exemple.archive'],"
                                        " ops: [{de: 'r6/tweaks/exemple.yaml', vers: 'r6/tweaks/Exemple.yaml'}, {de: 'r6/scripts/Exemple/a.reds', vers: 'r6/scripts/Exemple/a.reds'}]}});"
                                        "const champ = document.getElementById('ctDossier'); champ.value = 'Famille'; champ.dispatchEvent(new Event('input', {bubbles: true}));"
                                        "document.getElementById('ctAjoute').click();"
                                        "const vus = [...document.querySelectorAll('input[data-vers]')].map((x) => x.value).join(' | ');"
                                        "const attendu = 'r6/tweaks/Famille/Exemple.yaml | r6/scripts/Famille/Exemple/a.reds | archive/pc/mod/Exemple.archive';"
                                        "document.getElementById('ctAjoute').click();"
                                        "const encore = [...document.querySelectorAll('input[data-vers]')].map((x) => x.value).join(' | ');"
                                        "const large = getComputedStyle(document.getElementById('arrivages')).getPropertyValue('--l-ou');"
                                        "document.title = 'dossier ' + (vus === attendu && encore === attendu && /^[0-9]+px$/.test(large.trim()) ? 'ok' : 'non ' + vus + ' / ' + encore + ' / ' + large);",
                             ["<title>dossier ok</title>", 'id="ctDossier"', "Ajouter le dossier", "déjà sous ce dossier"]),
                            ("maj", "document.getElementById('maj').click(); recoit({t:'maj', data: D.maj, compte: D.majCompte, dit: ''});",
                             ["Zip du dépôt", "Nouvelle version", "Relire Nexus", "← Liste des mods", "compte gratuit", "Changer la clé…", "Mod manager download", "Le lien arrive seul si Red Stack est inscrit", 'id="majPrend"',
                              'id="majTout"', "à jour</span>", "Ignorer", "Ne plus ignorer", 'class="ignore"', "non comparés"]),
                            ("maj_sans_cle", "document.getElementById('maj').click(); recoit({t:'maj', data: D.maj, compte: {cle: false}, dit: ''});",
                             ["aucune clé d'API", "Où la trouver ?", "tout en bas de la page", "Personal API Key", "<b>Sans clé</b>", "la vue « Arrivages » le reconnaît"]),
                            ("maj_verrou", "document.getElementById('maj').click(); recoit({t:'maj', data: D.maj, compte: D.majCompte, dit: ''});"
                                           "recoit({t:'majOccupe', enCours: D.majOccupe});"
                                           "recoit({t:'majAvance', avance: {recu: 12400000, taille: 45000000, debit: 3200000, lotRecu: 30400000, lotTotal: 99000000}});",
                             ['id="majBarre" max="99000000" value="30400000"', "12,4 Mo sur 45,0 Mo · 3,2 Mo/s · ≈ 0:21", "Téléchargement en cours : 2 sur 3", "Cette vue est verrouillée", "reçu</span>", "en cours…</span>", "en attente</span>",
                              'id="majRelit" disabled', 'id="majTout" aria-label="Cocher ou décocher toutes les mises à jour" title="Tout cocher, tout décocher" disabled']),
                            ("fomod", "recoit({t:'detail', data: D.detailFo}); document.querySelector('[data-fomodmod]').click();"
                                      "recoit({t:'fomod', cle: D.detailFo.cle, data: Object.assign({}, D.fomod, {cle: D.detailFo.cle})});"
                                      "document.querySelector('[data-foimage]').click();"
                                      "recoit({t:'fomodImage', cle: D.detailFo.cle, entree: 'fomod/exemple.png', image: D.png});",
                             ["Installateur de «", 'class="fo-groupe"', 'data-fochoix="', "Ce que l'installateur pose", "Voir les fichiers et leur destination",
                              "Ignorer l'installateur : piocher à la main", '<img src="data:image/png', "← Détail du mod"]),
                            ("detail_fomod", "recoit({t:'detail', data: D.detailFo});",
                             ["Installateur FOMOD", "Installateur…", "est posé par son installateur", "Choisi par l'installateur"]),
                            ("reglages", "recoit({t:'reglages', data: D.conf, poste: D.poste}); recoit({t:'sauvegarde', data: D.sauve, compare: D.sauveCompare, dit: ''});"
                                         "recoit({t:'nxm', data: D.nxm});",
                             ["Sauvegardes des réglages", "Sauvegarder maintenant", "Comparer au jeu", "Restaurer…", "du jeu diffèrent d'elle", "(jeu lancé)", "Convention du dépôt", "Hors Red Stack", "Créer la référence", "Enregistrer", "Convention du contenu des zips", 'id="k_prefixes"', 'id="c_depot"', 'id="c_nouveaux"', "claude mcp add", 'id="c_wolvenkit"', 'id="c_atelier"', 'id="copieMcpWk"', "claude mcp add red-stack-wolvenkit", "avant d'extraire",
                              "vont aujourd'hui à <b>Vortex.exe</b>", 'id="nxmInscrit"', "Recevoir les liens nxm:// dans Red Stack…",
                              "<legend>Thème</legend>", "<legend>Langue</legend>", 'id="p_langue"', "Automatique (VS Code : en)", "Thème en cours : <b>Red Stack Jaune</b>", 'data-theme="Red Stack Rouge">Activer Red Stack Rouge', "✓ Red Stack Jaune", 'id="p_barre"', "Autre thème…"])):
    if MAJ_VIDE and vue in ("plie_vues", "maj_verrou"):
        print(f"  --   {vue} : sans objet, aucune mise à jour à montrer dans ce dépôt")
        continue
    stub = ("<script nonce=\"banc\">const D = " + json.dumps({"etat": etat, "profils": profils, "plan": plan, "detail": detail, "detailReq": detail_req, "conf": conf, "poste": poste, "conflits": conflits, "cfr": cfr, "code": code, "objets": objets, "dep": dep, "chaine": chaine, "convention": convention, "maj": maj, "majCompte": maj_compte, "contenu": contenu, "contenuCle": contenu_cle, "noms": noms, "journal": journal, "magasin": magasin, "sauve": sauve, "sauveCompare": sauve_compare, "fomod": fomod, "detailFo": detail_fo, "png": PNG, "majOccupe": maj_occupe, "nxm": nxm_etat}).replace("</", "<\\/")
            + ";\nconst recoit = (m) => window.dispatchEvent(new MessageEvent('message', {data: m}));\n"
            + "window.onerror = (m) => { document.title = 'ERREUR ' + m; };\n"
            + "const E_noms = () => recoit({t:'noms', cle: D.detail.cle, data: Object.assign({}, D.noms, {cle: D.detail.cle})});\n"
            + "function acquireVsCodeApi() { return { getState: () => null, setState() {}, postMessage(m) { (window.POSTES = window.POSTES || []).push(m); if (m.t === 'pret') "
            + "setTimeout(() => { recoit({t:'etat', data: D.etat, profils: D.profils}); recoit({t:'conflits', data: D.conflits}); " + suite + " }, 0); } }; }\n</script>\n")
    html = page.replace("<script nonce=\"banc\">\n(function () {", stub + "<script nonce=\"banc\">\n(function () {", 1)
    assert stub in html
    if vue in ("plie_conflits", "conflits", "code", "objets", "objets_transfert", "dependances", "chaine", "graphe", "ordre", "paires", "ressource", "puces", "identiques", "fichier"):   # l'onglet d'analyse : la même page, corps marqué par l'extension
        html = html.replace("<body>", '<body class="analyse code">' if vue == "code" else '<body class="analyse objets">' if vue in ("objets", "objets_transfert") else '<body class="analyse dependances">' if vue in ("dependances", "chaine", "graphe") else '<body class="analyse">', 1)
    f = os.path.join(OUT, vue + ".html")
    open(f, "w", encoding="utf-8").write(html)
    url = "file:///" + f.replace("\\", "/").replace(" ", "%20")
    common = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--window-size=1500,950", "--virtual-time-budget=4000",
              "--force-dark-mode", "--user-data-dir=" + os.path.join(OUT, "_profil_chrome")]
    subprocess.run(common + ["--screenshot=" + os.path.join(OUT, vue + ".png"), url], capture_output=True, timeout=120)
    dom = subprocess.run(common + ["--dump-dom", "--enable-logging=stderr", "--v=0", url], capture_output=True, timeout=120)
    text = dom.stdout.decode("utf-8", "replace")
    open(os.path.join(OUT, vue + ".dom.html"), "w", encoding="utf-8").write(text)
    rows = len(re.findall(r"<tr data-cle=", text))
    errs = [l for l in dom.stderr.decode("utf-8", "replace").splitlines() if "CONSOLE" in l and ("rror" in l or "Refused" in l)]
    if LANGUE != "fr":                      # autre langue : les marques de structure restent, les textes attendus sont ceux de la langue
        attendu = [a for a in attendu if a.startswith(("<title>", "id=", "data-", "class=", "<body")) and not re.search(r"[à-ÿ]|> ?[a-zA-Z]", a)] + AILLEURS.get(LANGUE, {}).get(vue, [])
    bad = [a for a in attendu if a not in text]
    title = re.search(r"<title>(.*?)</title>", text).group(1)
    # « fichier » : le champ de filtre vide aussi la liste, cachée dans cet onglet
    ok = (rows > 100 or vue in ("fichier", "filtre_neufs", "filtre_parques", "filtre_coupes", "graphe") or (vue == "verrou" and rows > 50) or (vue == "prerequis" and rows > 0)) and not errs and not bad and not title.startswith("ERREUR")
    print(("  ok   " if ok else "  KO   ") + f"{vue} : {rows} lignes de mods, {len(errs)} erreur(s) de console, manquants {bad}, titre « {title} »")
    for l in errs[:5]:
        print("       " + l[:300])
    if not ok:
        fails.append(vue)
# le manuel : page statique à part ; son sommaire se construit seul, ses ancres mènent toutes à une section, la console reste muette
aide = open(os.path.join(HERE, "..", "media", "aide.html"), encoding="utf-8").read()
if LANGUE != "fr":                          # comme `habilleAide` de l'extension : toute autre langue lit le corps anglais
    aide = aide[:aide.index("<!-- corps -->")] + open(os.path.join(HERE, "..", "media", "aide.en.html"), encoding="utf-8").read() + aide[aide.index("<!-- /corps -->"):]
aide = aide.replace("{{nonce}}", "banc").replace("{{version}}", "banc")
aide = aide.replace("</body>", "<script nonce=\"banc\">document.title = 'manuel ' + document.querySelectorAll('#sommaire a').length + ' sections, '"
                    " + [...document.querySelectorAll('main a[href^=\"#\"]')].filter((a) => !document.getElementById(a.getAttribute('href').slice(1))).length + ' ancre(s) morte(s)';</script></body>")
f = os.path.join(OUT, "manuel.html")
open(f, "w", encoding="utf-8").write(aide)
url = "file:///" + f.replace("\\", "/").replace(" ", "%20")
common = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--window-size=1500,950", "--virtual-time-budget=4000",
          "--force-dark-mode", "--user-data-dir=" + os.path.join(OUT, "_profil_chrome")]
subprocess.run(common + ["--screenshot=" + os.path.join(OUT, "manuel.png"), url], capture_output=True, timeout=120)
dom = subprocess.run(common + ["--dump-dom", "--enable-logging=stderr", "--v=0", url], capture_output=True, timeout=120)
text = dom.stdout.decode("utf-8", "replace")
errs = [l for l in dom.stderr.decode("utf-8", "replace").splitlines() if "CONSOLE" in l and ("rror" in l or "Refused" in l)]
title = re.search(r"<title>(.*?)</title>", text).group(1)
ok = not errs and re.fullmatch(r"manuel (1[5-9]|2\d) sections, 0 ancre\(s\) morte\(s\)", title) and "{{" not in text and 'class="ici"' in text and ("The idea in one minute" if LANGUE != "fr" else "Le principe en une minute") in text
print(("  ok   " if ok else "  KO   ") + f"manuel : titre « {title} », {len(errs)} erreur(s) de console")
for l in errs[:5]:
    print("       " + l[:300])
if not ok:
    fails.append("manuel")
print(("VERT" if not fails else f"ROUGE : {fails}") + f" (langue {LANGUE})")
sys.exit(1 if fails else 0)
