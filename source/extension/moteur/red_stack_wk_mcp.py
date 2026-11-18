"""Red Stack : serveur MCP (stdio) qui pilote la CLI WolvenKit (créé le 2026-11-17).

Une session Claude Code lit les archives du jeu et des mods comme le fait WolvenKit : chercher une ressource, lister une
archive, extraire, exporter (texture en image, mesh en glb), lire un fichier CR2W en JSON. Depuis la 0.18.0 elle fabrique
aussi : retoucher un CR2W par son JSON, importer des fichiers éditables, packer un dossier en .archive, construire un
projet WolvenKit. Aucune dépendance : JSON-RPC 2.0, un message par ligne ; la CLI (`WolvenKit.CLI.exe`, .NET) est lancée
à chaque appel.

  python -I red_stack_wk_mcp.py --donnees X [--cli C] [--atelier A] [--jeu J]

Les chemins viennent de `config.json` du dossier des données (clés `wolvenkit`, `atelier`, `jeu`), réglés dans la page
« Réglages » de l'extension ; les arguments passent devant.

RÈGLES, tenues par le code :
  - ce serveur n'écrit QUE dans l'atelier, un dossier que l'utilisateur désigne, hors du jeu, du dépôt et du magasin ;
  - un motif vide ou qui prendrait tout est refusé ; avant d'extraire, les fichiers sont COMPTÉS, et rien n'est écrit
    au-dessus du plafond ;
  - `uncook` n'est jamais lancé avec le dossier du jeu (`-gp`) : la CLI appliquerait alors le motif à toutes les archives
    du jeu, pas à la seule archive désignée (vu sur la 10.0.0-beta.1) ;
  - ce que les outils de fabrication LISENT (fichier à retoucher, dossier à importer ou à packer, projet à construire)
    est aussi dans l'atelier : rien n'est packé ni construit depuis le jeu ou le dépôt, et l'archive faite y reste ;
  - une retouche est refaite à part puis relue par la CLI avant de remplacer le fichier ; le premier original est gardé
    sous `_avant` de l'atelier.
"""
import argparse, array, bisect, copy, json, os, re, shutil, struct, subprocess, sys, zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "red_stack.py")
VERSION = "0.18.0"
LIMIT = 24000                                        # caractères rendus par outil, au plus
DELAI = 900                                          # secondes laissées à un appel de la CLI
PLAFOND = {"wk_extrait": 200, "wk_exporte": 40, "wk_importe": 40}   # fichiers écrits ou lus par appel, d'office
PLAFOND_MAX = 2000
OPS_MAX = 200                                        # opérations par retouche
NUMEROS = (("HandleId", "HandleRefId"), ("BufferId", None))   # numéros d'un JSON de WolvenKit : (définition, renvoi)
RX_NOM = re.compile(r'[^\\/:*?"<>|\x00-\x1f]{1,120}')
EXE = "WolvenKit.CLI.exe"
LIEUX = {"base": ["archive/pc/content"], "ep1": ["archive/pc/ep1"], "mods": ["archive/pc/mod"],
         "jeu": ["archive/pc/content", "archive/pc/ep1"], "tout": ["archive/pc/mod", "archive/pc/ep1", "archive/pc/content"]}
FORMATS = ("png", "tga", "dds", "bmp", "jpg", "tiff")
RX_AVANCE = re.compile(r"^(?:\d{1,3}%)+")
RX_LOG = re.compile(r"^\[\s*\d+:\s*(\w+)\s*\]\s*-\s?(.*)$")
RX_LITTERAL = re.compile(r"\\.|[^A-Za-z0-9_]")

P_SOURCE = {"archive": {"type": "string", "description": "An archive: full path of a .archive file, or its name alone if it is in the game (archive/pc/mod, content, ep1, "
                                                         "mods/*/archives)"},
            "mod": {"type": "string", "description": "Text that designates ONE zip of the Red Stack repository: its archives"}}
P_MOTIF = {"motif": {"type": "string", "description": "Wildcard on the WHOLE path of the resource, e.g. *nokota_osprey*.mesh (start with * for a part of the path)"},
           "regex": {"type": "string", "description": "Regular expression (.NET) on the path, instead of `motif`"}}
P_DANS = {"dans": {"type": "string", "description": "Subfolder of the workshop to write into (created if needed)"}}


def tool(name, desc, props=None, required=()):
    return {"name": name, "description": desc,
            "inputSchema": {"type": "object", "properties": props or {}, "required": list(required)}}


TOOLS = [
    tool("wk_info", "State of the WolvenKit side: the CLI (path, version), the game folder, the workshop (the only folder this "
                    "server writes to) and what is missing to use it. Read only."),
    tool("wk_cherche", "Searches resources by a part of their path in the archives of the base game, of Phantom Liberty and of the "
                       "installed mods, and says which archives hold each one. `texte`: words that must ALL be in the path (three "
                       "characters at least for one of them), e.g. “osprey mesh”. Read only; five seconds per place, more the first "
                       "time.",
         {"texte": {"type": "string"},
          "ou": {"type": "string", "enum": list(LIEUX), "description": "base (game), ep1 (Phantom Liberty), mods (archive/pc/mod), jeu (base + ep1), tout (everything, default)"},
          "limite": {"type": "integer", "description": "Maximum number of resources returned (default 60)"}}, ["texte"]),
    tool("wk_liste", "Content of an archive (`archive`) or of a mod's archives (`mod`): resource paths, which `motif` or `regex` "
                     "filter. Read only.",
         {**P_SOURCE, **P_MOTIF, "limite": {"type": "integer", "description": "Maximum number of paths returned per archive (default 200)"}}),
    tool("wk_hash", "FNV1a64 hash of resource paths (what the game and the archives use), in decimal and in hexadecimal. The path is "
                    "lower-cased, with backslashes.",
         {"chemins": {"type": "array", "items": {"type": "string"}}}, ["chemins"]),
    tool("wk_extrait", "Extracts resources as they are (`unbundle`) to the WORKSHOP. Source: `archive`, `mod`, or `ou` (base, ep1 or "
                       "mods: all the archives of that place). Selection: `motif`, `regex` or `hash` (only one). The files are counted "
                       "first; above the `plafond` (ceiling) nothing is written and the list is returned.",
         {**P_SOURCE, "ou": {"type": "string", "enum": ["base", "ep1", "mods"]}, **P_MOTIF,
          "hash": {"type": "string", "description": "Hash of ONE resource (decimal, or 16 hexadecimal digits)"},
          **P_DANS, "plafond": {"type": "integer", "description": f"Maximum number of files (default {PLAFOND['wk_extrait']}, never more than {PLAFOND_MAX})"}}),
    tool("wk_exporte", "Exports resources of ONE archive or of a mod as editable files (`uncook`) to the WORKSHOP: .xbm texture as an "
                       "image, mesh as .glb, and the other types WolvenKit converts. The game files go to `<dans>/archive`, the "
                       "editable files to `<dans>/raw`. Limit: the game folder is not given to the CLI, so the materials of a mesh that "
                       "live in ANOTHER archive are not followed.",
         {**P_SOURCE, **P_MOTIF, **P_DANS,
          "format": {"type": "string", "enum": list(FORMATS), "description": "Texture format (default png)"},
          "plafond": {"type": "integer", "description": f"Maximum number of files (default {PLAFOND['wk_exporte']})"}}),
    tool("wk_json", "Reads a CR2W file (.ent, .app, .mesh, .inkatlas, .mi…) as WolvenKit JSON. Source: `fichier` (already in the "
                    "workshop), or `ressource` (its path in the game) with `archive`, `mod` or `ou`, extracted to the workshop "
                    "first. The full JSON is written next to it; the answer returns `max_car` characters of it, or only the branch "
                    "`chemin` (e.g. Data.RootChunk.appearances.0).",
         {"fichier": {"type": "string", "description": "Path of a file INSIDE the workshop (full, or from the workshop)"},
          "ressource": {"type": "string", "description": "Path of the resource in the game, e.g. base\\gameplay\\gui\\x.inkatlas"},
          **P_SOURCE, "ou": {"type": "string", "enum": ["base", "ep1", "mods"]}, **P_DANS,
          "chemin": {"type": "string", "description": "Branch of the JSON to return: keys and indexes separated by dots"},
          "max_car": {"type": "integer", "description": "Maximum number of characters returned (default 12000)"}}),
    tool("wk_retouche", "Edits a CR2W file of the WORKSHOP through its JSON: the `operations` are played in order, then the CLI rebuilds "
                        "the file and reads it back as a check (`relu`). All or nothing: one operation refused, nothing is written. The "
                        "first original is kept under `_avant` in the workshop. Paths as in wk_json (Data.RootChunk.appearances.0.name). "
                        "Operations: fixe (replaces a value that exists), ajoute (to a list, or a new key to an object), retire "
                        "(removes), copie (duplicates a list element; its HandleId and BufferId are renumbered, its internal references "
                        "followed). `essai`: plays without writing and returns the before / after.",
         {"fichier": {"type": "string", "description": "CR2W file INSIDE the workshop (full, or from the workshop)"},
          "operations": {"type": "array", "items": {"type": "object", "properties": {
              "op": {"type": "string", "enum": ["fixe", "ajoute", "retire", "copie"]},
              "chemin": {"type": "string", "description": "fixe, retire, copie: the targeted element; ajoute: the list or the object that receives"},
              "valeur": {"description": "fixe, ajoute: the value, in WolvenKit's JSON form (read a neighbour with wk_json)"},
              "rang": {"type": "integer", "description": "ajoute, copie: position in the list (default: at the end)"},
              "cle": {"type": "string", "description": "ajoute into an object: the new key"}}, "required": ["op", "chemin"]}},
          "essai": {"type": "boolean", "description": "True: nothing is written"}}, ["fichier", "operations"]),
    tool("wk_importe", "Imports editable files of the WORKSHOP as game files (`import`): image to .xbm, .glb to .mesh, and whatever "
                       "WolvenKit can import. `source`: a file, or a folder whose tree is kept (a single file lands flat in `dans`). "
                       "`garde`: only rebuilds the buffers of game files ALREADY present in `dans` (a mesh exported then edited keeps "
                       "its materials this way).",
         {"source": {"type": "string", "description": "File or folder INSIDE the workshop"}, **P_DANS,
          "garde": {"type": "boolean", "description": "--keep option of the CLI"},
          "plafond": {"type": "integer", "description": f"Maximum number of files read (default {PLAFOND['wk_importe']})"}}, ["source"]),
    tool("wk_pack", "Packs a folder of the WORKSHOP into a .archive (`pack`): the folder is the root of the resource paths (it "
                    "contains base\\…, or the mod's folder). The archive is written in the workshop (`dans`, default packs), read "
                    "back, and its resources are returned with the files left aside (type unknown to the CLI, or working JSON "
                    "`X.json` lying next to `X`). `zip`: also makes a zip ready for a mod manager (archive/pc/mod/<name>.archive). "
                    "Nothing goes into the game: installing the mod is the user's action.",
         {"dossier": {"type": "string", "description": "Folder INSIDE the workshop, not the whole workshop"},
          "nom": {"type": "string", "description": "Name of the archive, without extension (default: the folder's)"},
          **P_DANS, "zip": {"type": "boolean"}}, ["dossier"]),
    tool("wk_build", "Builds a WolvenKit project of the WORKSHOP (`build`): a folder that holds a .cpmodproj and `source` "
                     "(source/archive = resources, source/resources = files installed as they are, e.g. r6/scripts). The result is in "
                     "the project's `packed`, shaped like the game folder; `packed` is erased and rebuilt at each call. `cree`: lays "
                     "down the skeleton of a new project (name = `nom`, otherwise the folder's). `zip`: zips `packed` next to it. "
                     "Nothing goes into the game.",
         {"projet": {"type": "string", "description": "Project folder INSIDE the workshop"},
          "cree": {"type": "boolean"}, "nom": {"type": "string"}, "zip": {"type": "boolean"}}, ["projet"]),
]


class Erreur(Exception):
    pass


def fnv64(texte):
    h = 0xcbf29ce484222325
    for x in texte.strip().strip('"').lstrip("\\/").replace("/", "\\").lower().encode("utf-8"):
        h = ((h ^ x) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def dedans(enfant, parent):
    """`enfant` est-il `parent` ou sous lui (chemins réels, casse ignorée)"""
    e, p = (os.path.normcase(os.path.realpath(x)) for x in (enfant, parent))
    return e == p or e.startswith(p.rstrip("\\/") + os.sep)


def empreintes(path):
    """empreintes des ressources d'une archive RDAR, triées ; tableau vide si ce n'en est pas une"""
    arr = array.array("Q")
    try:
        with open(path, "rb") as f:
            head = f.read(44)
            if len(head) < 44 or head[:4] != b"RDAR":
                return arr
            pos, size = struct.unpack_from("<QI", head, 8)
            f.seek(pos)
            idx = f.read(size) if 28 <= size <= 1 << 30 else b""
        if len(idx) >= 28:
            n = min(struct.unpack_from("<I", idx, 16)[0], (len(idx) - 28) // 56)
            arr.extend(sorted(h for h, in struct.iter_unpack("<Q48x", idx[28:28 + 56 * n])))
    except (OSError, struct.error):
        pass
    return arr


def parcours(x):
    """tous les objets d'un JSON, dans l'ordre du document"""
    pile = [x]
    while pile:
        v = pile.pop()
        if isinstance(v, dict):
            yield v
            pile.extend(reversed(list(v.values())))
        elif isinstance(v, list):
            pile.extend(reversed(v))


def renumerote(doc, neuf):
    """donne à la branche copiée `neuf` des numéros que `doc` n'a pas ; ses renvois vers elle-même suivent"""
    faits = {}
    for defn, renvoi in NUMEROS:
        pris = [int(d[defn]) for d in parcours(doc) if str(d.get(defn, "")).isdigit()]
        suivant, table = max(pris, default=-1) + 1, {}
        for d in parcours(neuf):
            if str(d.get(defn, "")).isdigit():
                table[str(d[defn])] = d[defn] = str(suivant)
                suivant += 1
        for d in parcours(neuf) if renvoi else ():
            if str(d.get(renvoi, "")) in table:
                d[renvoi] = table[str(d[renvoi])]
        if table:
            faits[defn] = len(table)
    return faits


def norme(data):
    """copie où les numéros sont ceux de l'ordre du document : la CLI les redonne ainsi en relisant"""
    d = copy.deepcopy(data)
    for defn, renvoi in NUMEROS:
        table = {}
        for o in parcours(d):
            if defn in o:
                table.setdefault(str(o[defn]), str(len(table)))
        for o in parcours(d):
            if defn in o:
                o[defn] = table[str(o[defn])]
            if renvoi and str(o.get(renvoi, "")) in table:
                o[renvoi] = table[str(o[renvoi])]
    return d


def ecarts(a, b, ou="Data", out=None, n=10):
    """chemins où ce qui a été écrit (`a`) et ce que la CLI relit (`b`) diffèrent"""
    out = [] if out is None else out
    if len(out) >= n:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a or k not in b:
                out.append({"chemin": f"{ou}.{k}", "ecrit": court(a.get(k, "(absent)")), "relu": court(b.get(k, "(absent)"))})
            else:
                ecarts(a[k], b[k], f"{ou}.{k}", out, n)
            if len(out) >= n:
                break
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            ecarts(x, y, f"{ou}.{i}", out, n)
            if len(out) >= n:
                break
    elif a != b:
        nombres = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a, b))
        if not (nombres and abs(a - b) <= 1e-5 * max(1.0, abs(a), abs(b))):      # un flottant 32 bits ne rend pas 0.1
            out.append({"chemin": ou, "ecrit": court(a), "relu": court(b)})
    return out


def court(v, n=160):
    t = json.dumps(v, ensure_ascii=False)
    return t if len(t) <= n else t[:n] + f"… ({len(t)} characters)"


def genre(v):
    return "objet" if isinstance(v, dict) else "liste" if isinstance(v, list) else "valeur"


class Serveur:
    def __init__(self, a):
        self.a = a
        self.data = os.path.abspath(a.donnees or os.path.join(HERE, "red_stack"))
        self.idx = {}                                # chemin d'archive -> (taille, date, empreintes triées)

    # ------------------------------------------------------------ réglages

    def conf(self):
        try:
            return json.load(open(os.path.join(self.data, "config.json"), encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def cli(self):
        p = self.a.cli or self.conf().get("wolvenkit") or ""
        if p and os.path.isdir(p):
            p = os.path.join(p, EXE)
        if not p or not os.path.isfile(p):
            raise Erreur("WolvenKit CLI not found" + (f" : {p}" if p else "") + ". The user sets it in VS Code, Red Stack, “Settings”, “WolvenKit” (the folder that holds " + EXE + ").")
        return p

    def jeu(self):
        j = self.a.jeu or self.conf().get("jeu") or ""
        if not j or not os.path.isdir(os.path.join(j, "archive", "pc")):
            raise Erreur(f"Game folder not found ({j or 'not set'}): it is set in Red Stack, “Settings”.")
        return j

    def interdits(self):
        c = self.conf()
        jeu = self.a.jeu or c.get("jeu") or ""
        lieux = {"the game": jeu, "the zip repository": c.get("depot") or "", "the Red Stack data": self.data,
                 "the store": c.get("magasin") or (jeu.rstrip("\\/") + " - Red Stack" if jeu else ""),
                 "the backups": c.get("sauvegardes") or "", "the game reference": c.get("reference") or ""}
        return {k: v for k, v in lieux.items() if v}

    def atelier(self, cree=True):
        a = self.a.atelier or self.conf().get("atelier") or ""
        if not a or not os.path.isabs(a):
            raise Erreur("No workshop: this server only writes to a folder the user sets in VS Code, Red Stack, “Settings”, “WolvenKit”. "
                         "Nothing was written.")
        for mot, lieu in self.interdits().items():
            if dedans(a, lieu) or dedans(lieu, a):
                raise Erreur(f"Workshop refused: {a} touches {mot} ({lieu}). It must be a folder of its own. Nothing was written.")
        if cree:
            os.makedirs(a, exist_ok=True)
        return a

    def sortie(self, dans, defaut):
        """dossier de l'atelier où écrire ; `dans` ne peut ni remonter ni sortir de l'atelier"""
        racine = self.atelier()
        parts = [x for x in re.split(r"[\\/]+", (dans or defaut).strip()) if x and x != "."]
        if not parts or any(x == ".." or re.search(r'[:*?"<>|]', x) for x in parts):
            raise Erreur(f"`dans` = a subfolder of the workshop, without “..” or a drive: {dans!r} refused.")
        out = os.path.join(racine, *parts)
        os.makedirs(out, exist_ok=True)
        if not dedans(out, racine):
            raise Erreur(f"`dans` leaves the workshop ({out}): refused.")
        return out

    def lieu(self, chemin, quoi):
        """chemin DANS l'atelier (complet, ou depuis l'atelier) ; refusé s'il en sort, liens suivis"""
        racine = self.atelier()
        f = str(chemin or "").strip().strip('"')
        if not f:
            raise Erreur(f"`{quoi}`: a path in the workshop is required.")
        f = os.path.normpath(f if os.path.isabs(f) else os.path.join(racine, f))
        if not dedans(f, racine):
            raise Erreur(f"`{quoi}` outside the workshop ({racine}): refused. This server only reads to build and only writes in the workshop: "
                         "bring the resource there first (wk_extrait, wk_exporte).")
        return f

    def tmp(self):
        """dossier de travail jetable, dans l'atelier ; vidé à chaque prise"""
        t = os.path.join(self.atelier(), "_tmp", str(os.getpid()))
        shutil.rmtree(t, ignore_errors=True)
        os.makedirs(t)
        return t

    @staticmethod
    def de_travail(racine, contenu):
        """fichiers `X.json` posés à côté de `X` : le JSON de WolvenKit d'un fichier du jeu, pas une ressource"""
        noms = {k.lower() for k in contenu}
        return {k for k in contenu if k.lower().endswith(".json") and k[:-5].lower() in noms}

    @staticmethod
    def zippe(dest, paires):
        with zipfile.ZipFile(dest + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
            for nom, f in paires:
                z.write(f, nom.replace("\\", "/"))
        os.replace(dest + ".tmp", dest)
        return dest

    # ------------------------------------------------------------ CLI et moteur

    def wk(self, *args):
        """lance la CLI ; rend (lignes utiles, journal [(niveau, texte)])"""
        try:
            r = subprocess.run([self.cli(), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                               stdin=subprocess.DEVNULL, timeout=DELAI, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            raise Erreur(f"The WolvenKit CLI did not return within {DELAI} s: stopped.")
        except OSError as e:
            raise Erreur(f"The WolvenKit CLI does not start ({e}). It needs the .NET Runtime its version announces.")
        lignes, logs = [], []
        for brut in (r.stdout + "\n" + r.stderr).splitlines():
            l = RX_AVANCE.sub("", brut.strip()).strip()
            m = RX_LOG.match(l)
            if m:
                logs.append((m.group(1), m.group(2).strip()))
            elif l:
                lignes.append(l)
        if r.returncode and not logs and not lignes:
            raise Erreur(f"WolvenKit CLI: code {r.returncode}, no output. Is the .NET Runtime it needs installed?")
        return lignes, logs

    @staticmethod
    def soucis(logs, n=12):
        return [f"{niv} : {t}" for niv, t in logs if niv in ("Error", "Warning")][:n]

    def rs(self, *args):
        base = ["--donnees", self.data] + (["--jeu", self.a.jeu] if self.a.jeu else [])
        r = subprocess.run([sys.executable, "-I", TOOL, *args, *base, "--langue", "en", "--json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        if r.returncode:
            raise Erreur((r.stderr or r.stdout).strip()[-1500:] or f"red_stack.py: code {r.returncode}")
        return json.loads(r.stdout)

    # ------------------------------------------------------------ sources et motifs

    def archives_du_jeu(self, lieux):
        jeu, out = self.jeu(), []
        for rel in lieux:
            d = os.path.join(jeu, *rel.split("/"))
            out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(".archive")] if os.path.isdir(d) else []
        return out

    def sources(self, p, lieu=False):
        """[(libellé, chemin)] des archives désignées par `archive`, `mod` ou `ou` ; un lieu est rendu comme un dossier"""
        donnes = [k for k in ("archive", "mod", "ou") if p.get(k)]
        if len(donnes) != 1 or (donnes == ["ou"] and not lieu):
            raise Erreur("Source : " + ("`archive`, `mod` or `ou`" if lieu else "`archive` or `mod`") + ", only one of them.")
        if p.get("ou"):
            if p["ou"] not in ("base", "ep1", "mods"):
                raise Erreur("`ou` = base, ep1 or mods.")
            d = os.path.join(self.jeu(), *LIEUX[p["ou"]][0].split("/"))
            if not os.path.isdir(d):
                raise Erreur(f"Folder missing from the game: {d}")
            return [(p["ou"], d)]
        if p.get("archive"):
            a = p["archive"].strip().strip('"')
            if os.path.isabs(a):
                if not (os.path.isfile(a) and a.lower().endswith(".archive")):
                    raise Erreur(f"Not a .archive file: {a}")
                return [(os.path.basename(a), a)]
            nom = a if a.lower().endswith(".archive") else a + ".archive"
            jeu = self.jeu()
            cands = self.archives_du_jeu(LIEUX["tout"])
            mods = os.path.join(jeu, "mods")
            for d in sorted(os.listdir(mods)) if os.path.isdir(mods) else []:
                sub = os.path.join(mods, d, "archives")
                cands += [os.path.join(sub, f) for f in sorted(os.listdir(sub))] if os.path.isdir(sub) else []
            vus = [c for c in cands if os.path.basename(c).lower() == nom.lower()]
            if len(vus) != 1:
                raise Erreur(f"Archive “{nom}”: " + ("not found in the game (give its full path, or `mod`)." if not vus
                                                        else "several in the game: " + " | ".join(vus)))
            return [(nom, vus[0])]
        d = self.rs("detail", "--mod", p["mod"])
        out, jeu = [], self.jeu()
        for e in d["entrees"]:
            if not e["dest"].lower().endswith(".archive"):
                continue
            cands = [os.path.join(d["arbre"], *e["entree"].split("/"))] if d.get("arbre") else []
            cands.append(os.path.join(jeu, *e["dest"].split("/")))
            f = next((c for c in cands if os.path.isfile(c)), None)
            if f:
                out.append((e["dest"].split("/")[-1], f))
        if not out:
            raise Erreur(f"{d['cle']}: no readable archive on the disk (neither in its store tree, nor in the game). A mod never installed has no "
                         "tree: install it first, or designate the file with `archive`.")
        return out

    @staticmethod
    def motif(p, hash_ok=False):
        """arguments de choix pour la CLI, après les gardes : jamais vide, jamais « tout »"""
        donnes = [k for k in ("motif", "regex", "hash") if p.get(k) not in (None, "")]
        if len(donnes) != 1 or (donnes == ["hash"] and not hash_ok):
            raise Erreur("Choix : " + ("`motif`, `regex` or `hash`" if hash_ok else "`motif` or `regex`") + ", only one, not empty.")
        k, v = donnes[0], str(p[donnes[0]]).strip()
        if k == "hash":
            try:
                h = int(v, 16) if re.fullmatch(r"(0x)?[0-9a-fA-F]{16}", v) and not v.isdigit() else int(v)
            except ValueError:
                raise Erreur(f"`hash` = a decimal number or 16 hexadecimal digits: {v!r}")
            if not 0 < h <= 0xFFFFFFFFFFFFFFFF:
                raise Erreur(f"`hash` out of range: {v!r}")
            return ["--hash", str(h)]
        if k == "motif":
            if len(re.sub(r"[*?\\/.\s]", "", v)) < 3:
                raise Erreur(f"Pattern refused ({v!r}): it would take everything or nearly. Three characters at least besides wildcards.")
            return ["-w", v.replace("/", "\\")]
        try:
            rx = re.compile(v)
        except re.error as e:
            raise Erreur(f"Unreadable regular expression ({e}): {v!r}")
        if rx.search("") or len(RX_LITTERAL.sub("", v)) < 3:
            raise Erreur(f"Expression refused ({v!r}): it would take everything or nearly. Three literal characters at least.")
        return ["-r", v]

    def compte(self, src, choix):
        """chemins que le choix prendrait dans cette source (fichier ou dossier d'archives), sans rien écrire"""
        if choix[0] == "--hash":
            return None
        lignes, logs = self.wk("archive", src, "-l", *choix)
        return lignes

    def arbre(self, racine):
        out = {}
        for d, _, fs in os.walk(racine):
            for f in fs:
                p = os.path.join(d, f)
                try:
                    st = os.stat(p)
                    out[os.path.relpath(p, racine)] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    pass
        return out

    def ecrit(self, outil, p, defaut, lance):
        """compte, contrôle le plafond, lance, puis dit ce qui est vraiment arrivé sur le disque"""
        srcs = self.sources(p, lieu=outil == "wk_extrait")
        choix = self.motif(p, hash_ok=outil == "wk_extrait")
        plafond = max(1, min(int(p.get("plafond") or PLAFOND[outil]), PLAFOND_MAX))
        prevus, total = [], 0
        for lib, src in srcs:
            noms = self.compte(src, choix)
            total += 1 if noms is None else len(noms)
            prevus.append((lib, src, noms))
        if not total:
            raise Erreur("No resource matches in " + ", ".join(l for l, _, _ in prevus) + ". Nothing was written.")
        if total > plafond:
            return {"ecrit": 0, "refuse": f"{total} files match, ceiling {plafond}: nothing was written. Narrow the pattern, or raise `plafond` (at most {PLAFOND_MAX}) if that "
                                          "is wanted.",
                    "exemples": [n for _, _, noms in prevus for n in (noms or [])][:30]}
        out = self.sortie(p.get("dans"), defaut)
        avant = self.arbre(out)
        soucis = []
        for lib, src, noms in prevus:
            if noms is None or noms:
                soucis += [f"{lib} : {s}" for s in self.soucis(lance(src, out, choix)[1])]
        apres = self.arbre(out)
        neufs = sorted(k for k, v in apres.items() if avant.get(k) != v)
        return {"dossier": out, "prevus": total, "ecrit": len(neufs), "octets": sum(apres[k][0] for k in neufs),
                "fichiers": neufs[:150], **({"fichiers_total": len(neufs)} if len(neufs) > 150 else {}),
                **({"soucis": soucis[:20]} if soucis else {})}

    def index(self, path):
        st = os.stat(path)
        c = self.idx.get(path)
        if not c or c[:2] != (st.st_size, st.st_mtime_ns):
            c = self.idx[path] = (st.st_size, st.st_mtime_ns, empreintes(path))
        return c[2]

    # ------------------------------------------------------------ outils

    def wk_info(self, p):
        out, manque = {"serveur": VERSION}, []
        try:
            cli = self.cli()
            lignes, logs = self.wk("--version")
            out["cli"] = {"chemin": cli, "version": (lignes or ["?"])[0]}
        except Erreur as e:
            out["cli"] = None
            manque.append(str(e))
        try:
            jeu = self.jeu()
            out["jeu"] = {"chemin": jeu, **{k: len(self.archives_du_jeu(LIEUX[k])) for k in ("base", "ep1", "mods")}}
        except Erreur as e:
            out["jeu"] = None
            manque.append(str(e))
        try:
            a = self.atelier(cree=False)
            out["atelier"] = {"chemin": a, "existe": os.path.isdir(a), "fichiers": len(self.arbre(a)) if os.path.isdir(a) else 0}
        except Erreur as e:
            out["atelier"] = None
            manque.append(str(e))
        out["regles"] = ("Writes in the workshop only. Empty or too broad pattern refused. Files counted before any extraction; default "
                         f"ceiling {PLAFOND['wk_extrait']} (extract), {PLAFOND['wk_exporte']} (export), never more than {PLAFOND_MAX}. Editing, importing, packing, building: source AND "
                         "output in the workshop; an edit keeps the first original under _avant. The game, the zip repository and the "
                         "store are never written: putting a file in the game remains the user's action, through a zip in a Red Stack "
                         "stack.")
        if manque:
            out["manque"] = manque
        return out

    def wk_hash(self, p):
        return {"empreintes": [{"chemin": c, "decimal": str(fnv64(c)), "hexa": f"{fnv64(c):016x}"} for c in p["chemins"][:200]]}

    def wk_cherche(self, p):
        mots = [m.lower().replace("/", "\\") for m in str(p["texte"]).split()]
        long_ = max(mots, key=lambda m: len(re.sub(r"[*?\\.]", "", m)), default="")
        if len(re.sub(r"[*?\\.]", "", long_)) < 3:
            raise Erreur("`texte`: a word of at least three characters (besides wildcards) is required.")
        lieux = LIEUX[p.get("ou") or "tout"] if (p.get("ou") or "tout") in LIEUX else None
        if lieux is None:
            raise Erreur("`ou` = " + ", ".join(LIEUX))
        jeu, noms, soucis = self.jeu(), {}, []
        for rel in lieux:
            d = os.path.join(jeu, *rel.split("/"))
            if not os.path.isdir(d):
                continue
            lignes, logs = self.wk("archive", d, "-l", "-w", "*" + long_.strip("*") + "*")
            soucis += [f"{rel} : {s}" for s in self.soucis(logs, 4)]
            for l in lignes:
                ll = l.lower()
                if all(m.strip("*") in ll for m in mots):
                    noms.setdefault(ll, l)
        n = max(1, int(p.get("limite") or 60))
        rendus = sorted(noms.values(), key=str.lower)[:n]
        archives = self.archives_du_jeu(LIEUX["tout"]) if rendus else []
        tables = [(a, self.index(a)) for a in archives]
        rows = []
        for nom in rendus:
            h = fnv64(nom)
            ou = []
            for a, t in tables:
                i = bisect.bisect_left(t, h)
                if i < len(t) and t[i] == h:
                    ou.append(os.path.relpath(a, jeu).replace("\\", "/"))
            rows.append({"ressource": nom, "dans": ou})
        return {"trouvees": len(noms), "rendues": len(rows), "ressources": rows,
                "note": "`dans`: game archives that hold the resource, mods first (by name), then ep1, then base; the exact load order "
                        "and the mod of each archive are read with red_stack_conflits and red_stack_fichier.",
                **({"soucis": soucis[:12]} if soucis else {})}

    def wk_liste(self, p):
        srcs = self.sources(p)
        choix = self.motif(p) if (p.get("motif") or p.get("regex")) else []
        n = max(1, int(p.get("limite") or 200))
        out = []
        for lib, src in srcs:
            lignes, logs = self.wk("archive", src, "-l", *choix)
            out.append({"archive": lib, "fichier": src, "ressources_total": len(lignes), "ressources": sorted(lignes, key=str.lower)[:n],
                        **({"soucis": self.soucis(logs)} if self.soucis(logs) else {})})
        return {"archives": out}

    def wk_extrait(self, p):
        return self.ecrit("wk_extrait", p, "extrait", lambda src, out, choix: self.wk("unbundle", src, "-o", out, *choix))

    def wk_exporte(self, p):
        fmt = p.get("format") or "png"
        if fmt not in FORMATS:
            raise Erreur("`format` = " + ", ".join(FORMATS))

        def lance(src, out, choix):                  # jamais -gp : la CLI étendrait le motif à toutes les archives du jeu
            return self.wk("uncook", src, "-o", os.path.join(out, "archive"), "-or", os.path.join(out, "raw"), *choix, "--uext", fmt)
        return self.ecrit("wk_exporte", p, "export", lance)

    def wk_json(self, p):
        racine = self.atelier()
        if bool(p.get("fichier")) == bool(p.get("ressource")):
            raise Erreur("wk_json: `fichier` (in the workshop) OR `ressource` (with `archive`, `mod` or `ou`).")
        if p.get("fichier"):
            f = p["fichier"].strip().strip('"')
            f = f if os.path.isabs(f) else os.path.join(racine, f)
            if not dedans(f, racine):
                raise Erreur(f"`fichier` outside the workshop ({racine}): refused. Extract the resource first (wk_extrait), or designate it with "
                             "`ressource`.")
            if not os.path.isfile(f):
                raise Erreur(f"File missing: {f}")
        else:
            res = p["ressource"].strip().strip('"').lstrip("\\/").replace("/", "\\")
            r = self.ecrit("wk_extrait", {**{k: p[k] for k in ("archive", "mod", "ou") if p.get(k)}, "hash": str(fnv64(res)),
                                          "dans": p.get("dans"), "plafond": 60}, "json", lambda src, out, choix: self.wk("unbundle", src, "-o", out, *choix))
            f = os.path.join(r["dossier"], *res.split("\\"))
            if not os.path.isfile(f):
                cands = [x for x in r.get("fichiers", []) if x.lower().endswith(os.path.basename(res).lower())]
                if not cands:
                    raise Erreur(f"Resource “{res}” missing from the source. Check its path with wk_cherche or wk_liste.")
                f = os.path.join(r["dossier"], cands[0])
        out = os.path.dirname(f)
        lignes, logs = self.wk("convert", "s", f, "-o", out)
        js = os.path.join(out, os.path.basename(f) + ".json")
        if not os.path.isfile(js) or os.path.getmtime(js) < os.path.getmtime(f) - 1:
            raise Erreur("The CLI returned no JSON for this file (not a CR2W?). " + " ; ".join(self.soucis(logs)))
        rep = {"fichier": f, "json": js, "octets_json": os.path.getsize(js)}
        n = max(500, min(int(p.get("max_car") or 12000), LIMIT - 2000))
        if p.get("chemin"):
            d = json.load(open(js, encoding="utf-8"))
            for cle in [c for c in p["chemin"].split(".") if c != ""]:
                try:
                    d = d[int(cle)] if isinstance(d, list) else d[cle]
                except (KeyError, IndexError, ValueError, TypeError):
                    cles = list(d)[:60] if isinstance(d, dict) else f"list of {len(d)}" if isinstance(d, list) else "a value"
                    raise Erreur(f"`chemin`: “{cle}” missing. Here: {cles}")
            texte = json.dumps(d, ensure_ascii=False, indent=1)
            rep["chemin"] = p["chemin"]
        else:
            texte = open(js, encoding="utf-8", errors="replace").read()
        rep["caracteres"] = len(texte)
        if len(texte) > n:
            rep["coupe"] = f"{n} characters returned out of {len(texte)}: read a branch with `chemin`, or the `json` file."
        rep["texte"] = texte[:n]
        return rep

    # ------------------------------------------------------------ fabrication

    @staticmethod
    def vise(doc, chemin):
        """(parent, clé, valeur) de l'élément au bout de `chemin` ; l'élément doit exister"""
        cles = [c for c in str(chemin or "").split(".") if c != ""]
        if not cles or cles[0] != "Data":
            raise Erreur(f"`chemin` starts from Data (e.g. Data.RootChunk.name): {chemin!r}")
        parent = cle = None
        d, fait = doc, []
        for c in cles:
            parent = d
            if isinstance(d, list):
                if not c.isdigit() or int(c) >= len(d):
                    raise Erreur(f"`chemin`: index “{c}” missing from {'.'.join(fait)} (list of {len(d)}).")
                cle = int(c)
            elif isinstance(d, dict):
                if c not in d:
                    raise Erreur(f"`chemin`: “{c}” missing from {'.'.join(fait) or 'the root'}. Here: {list(d)[:60]}")
                cle = c
            else:
                raise Erreur(f"`chemin`: {'.'.join(fait)} is a value, “{c}” cannot follow it.")
            d = parent[cle]
            fait.append(c)
        return parent, cle, d

    def opere(self, doc, op):
        """joue une opération sur le JSON en mémoire ; rend ce qu'elle a fait"""
        nom, chemin = op.get("op"), op.get("chemin")
        if nom not in ("fixe", "ajoute", "retire", "copie"):
            raise Erreur(f"`op` = fixe, ajoute, retire or copie: {nom!r}")
        if nom in ("fixe", "ajoute") and "valeur" not in op:
            raise Erreur(f"{nom}: `valeur` is missing.")
        parent, cle, v = self.vise(doc, chemin)
        fait = {"op": nom, "chemin": chemin}
        if nom == "fixe":
            if genre(v) != genre(op["valeur"]) and v is not None and op["valeur"] is not None:
                raise Erreur(f"fixe {chemin}: {genre(v)} replaced by {genre(op['valeur'])}, refused. Keep the form WolvenKit writes; here: {court(v)}")
            if type(v) is not type(op["valeur"]) and genre(v) == "valeur" and None not in (v, op["valeur"]) \
                    and not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (v, op["valeur"])):
                fait["note"] = (f"the type changes ({type(v).__name__} → {type(op['valeur']).__name__}): WolvenKit writes some numbers as text (uint64, CRUID); read `relu`.")
            parent[cle] = copy.deepcopy(op["valeur"])
            fait.update(avant=court(v), apres=court(op["valeur"]))
        elif nom == "retire":
            if parent is doc:
                raise Erreur("retire: Data cannot be removed.")
            del parent[cle]
            fait["avant"] = court(v)
        elif nom == "ajoute":
            if isinstance(v, list):
                rang = op.get("rang")
                rang = len(v) if rang is None else int(rang)
                if not 0 <= rang <= len(v):
                    raise Erreur(f"ajoute {chemin}: index {rang} outside the list (0 to {len(v)}).")
                v.insert(rang, copy.deepcopy(op["valeur"]))
                fait.update(rang=rang, longueur=len(v))
            elif isinstance(v, dict):
                k = op.get("cle")
                if not k or k in v:
                    raise Erreur(f"ajoute {chemin}: a new `cle` is required for an object" + (f" (“{k}” exists: fixe)." if k else "."))
                v[k] = copy.deepcopy(op["valeur"])
                fait["cle"] = k
            else:
                raise Erreur(f"ajoute {chemin}: neither a list nor an object.")
        else:
            if not isinstance(parent, list):
                raise Erreur(f"copie {chemin}: the element must be in a list.")
            neuf = copy.deepcopy(v)
            num = renumerote(doc, neuf)
            rang = op.get("rang")
            rang = len(parent) if rang is None else int(rang)
            if not 0 <= rang <= len(parent):
                raise Erreur(f"copie {chemin}: index {rang} outside the list (0 to {len(parent)}).")
            parent.insert(rang, neuf)
            fait.update(copie=".".join(str(chemin).split(".")[:-1] + [str(rang)]), longueur=len(parent),
                        **({"renumerotes": num} if num else {}))
        return fait

    def wk_retouche(self, p):
        racine = self.atelier()
        f = self.lieu(p.get("fichier"), "fichier")
        f = f[:-5] if f.lower().endswith(".json") else f
        if not os.path.isfile(f):
            raise Erreur(f"File missing: {f}")
        ops = p.get("operations")
        if not isinstance(ops, list) or not ops or len(ops) > OPS_MAX or not all(isinstance(o, dict) for o in ops):
            raise Erreur(f"`operations`: a list of 1 to {OPS_MAX} operations.")
        js, t = f + ".json", self.tmp()
        try:
            lu = os.path.join(t, "lu")
            os.makedirs(lu)
            lignes, logs = self.wk("convert", "s", f, "-o", lu)          # toujours relu du fichier : un JSON à côté peut dater
            src = os.path.join(lu, os.path.basename(js))
            if not os.path.isfile(src):
                raise Erreur("The CLI returned no JSON for this file (not a CR2W?). " + " ; ".join(self.soucis(logs)))
            doc = json.load(open(src, encoding="utf-8"))
            origine = json.dumps(doc.get("Data"), sort_keys=True)
            faits = []
            for i, op in enumerate(ops):
                try:
                    faits.append(self.opere(doc, op))
                except Erreur as e:
                    raise Erreur(f"Operation {i + 1} on {len(ops)} refused, NOTHING was written. {e}")
            rep = {"fichier": f, "operations": faits}
            if json.dumps(doc.get("Data"), sort_keys=True) == origine:
                return {**rep, "ecrit": 0, "note": "The operations change nothing: file left as it is."}
            if p.get("essai"):
                return {**rep, "ecrit": 0, "essai": True}
            din, dout, drelu = (os.path.join(t, x) for x in ("in", "out", "relu"))
            for d in (din, dout, drelu):
                os.makedirs(d)
            tj = os.path.join(din, os.path.basename(js))
            json.dump(doc, open(tj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            lignes, logs = self.wk("convert", "d", tj, "-o", dout)
            neuf = os.path.join(dout, os.path.basename(f))
            if not os.path.isfile(neuf) or not os.path.getsize(neuf):
                raise Erreur("The CLI did not rebuild the file from the edited JSON: NOTHING changed in the workshop. "
                             + " ; ".join(self.soucis(logs) or lignes[-3:]))
            lignes, logs2 = self.wk("convert", "s", neuf, "-o", drelu)
            rj = os.path.join(drelu, os.path.basename(js))
            if not os.path.isfile(rj):
                raise Erreur("The CLI cannot read back the file it has just rebuilt: NOTHING changed in the workshop. "
                             + " ; ".join(self.soucis(logs2)))
            diff = ecarts(norme(doc["Data"]), norme(json.load(open(rj, encoding="utf-8")).get("Data")))
            sauv = os.path.join(racine, "_avant", os.path.relpath(f, racine))
            if not os.path.exists(sauv) and not dedans(f, os.path.join(racine, "_avant")):
                os.makedirs(os.path.dirname(sauv), exist_ok=True)
                shutil.copy2(f, sauv)
            rep.update(octets_avant=os.path.getsize(f), octets=os.path.getsize(neuf))
            os.replace(neuf, f)
            os.replace(rj, js)                                           # le JSON à côté = ce que le fichier porte vraiment
            rep.update(ecrit=1, json=js, original=sauv if os.path.isfile(sauv) else None,
                       relu="identical to what was written" if not diff else "DIFFERS from what was written: the CLI changed or lost these values, see `ecarts`", **({"ecarts": diff} if diff else {}),
                       **({"soucis": self.soucis(logs)} if self.soucis(logs) else {}))
            return rep
        finally:
            shutil.rmtree(t, ignore_errors=True)

    def dit(self, logs, n=6):
        return [t for niv, t in logs if niv in ("Success", "Information") and not t.startswith("Elapsed")][-n:]

    def bilan(self, out, avant, logs, **plus):
        apres = self.arbre(out)
        neufs = sorted(k for k, v in apres.items() if avant.get(k) != v)
        return {"dossier": out, "ecrit": len(neufs), "octets": sum(apres[k][0] for k in neufs), "fichiers": neufs[:150],
                **({"fichiers_total": len(neufs)} if len(neufs) > 150 else {}), **plus,
                **({"cli": self.dit(logs)} if self.dit(logs) else {}), **({"soucis": self.soucis(logs)} if self.soucis(logs) else {})}

    def wk_importe(self, p):
        src = self.lieu(p.get("source"), "source")
        if not os.path.exists(src):
            raise Erreur(f"Source missing: {src}")
        n = len(self.arbre(src)) if os.path.isdir(src) else 1
        plafond = max(1, min(int(p.get("plafond") or PLAFOND["wk_importe"]), PLAFOND_MAX))
        if not n:
            raise Erreur(f"Empty folder: {src}. Nothing was written.")
        if n > plafond:
            return {"ecrit": 0, "refuse": f"{n} files in the source, ceiling {plafond}: nothing was written. Designate a subfolder or a file, or raise `plafond` "
                                          f"(at most {PLAFOND_MAX}) if that is wanted."}
        out = self.sortie(p.get("dans"), "import")
        avant = self.arbre(out)
        lignes, logs = self.wk("import", src, "-o", out, *(["-k"] if p.get("garde") else []))
        rep = self.bilan(out, avant, logs, lus=n)
        if not rep["ecrit"]:
            rep["note"] = ("Nothing written: the CLI recognised no file to import" + (", or `garde` found no game file to rebuild in `dans`." if p.get("garde") else "."))
        return rep

    def wk_pack(self, p):
        racine = self.atelier()
        src = self.lieu(p.get("dossier"), "dossier")
        if not os.path.isdir(src):
            raise Erreur(f"Folder missing: {src}")
        if dedans(racine, src):
            raise Erreur("`dossier` = a folder INSIDE the workshop, not the whole workshop: it also holds the exports and the originals.")
        nom = re.sub(r"(?i)\.archive$", "", str(p.get("nom") or os.path.basename(src)).strip())
        if not RX_NOM.fullmatch(nom) or nom.strip(". ") != nom:
            raise Erreur(f"`nom` refused ({nom!r}): a file name, without folder or extension.")
        contenu = self.arbre(src)
        if not contenu:
            raise Erreur(f"Empty folder: {src}. Nothing was written.")
        out = self.sortie(p.get("dans"), "packs")
        if dedans(out, src):
            raise Erreur(f"`dans` ({out}) is inside the folder to pack: the archive must be written next to it.")
        t = self.tmp()
        try:
            travail = self.de_travail(src, contenu)                      # la CLI packerait aussi les JSON de wk_json
            etal = os.path.join(t, "src", nom)
            for k in contenu:
                if k not in travail:
                    os.makedirs(os.path.dirname(os.path.join(etal, k)), exist_ok=True)
                    try:
                        os.link(os.path.join(src, k), os.path.join(etal, k))
                    except OSError:
                        shutil.copy2(os.path.join(src, k), os.path.join(etal, k))
            if not os.path.isdir(etal):
                raise Erreur(f"{src} only holds working JSON files. Nothing was written.")
            lignes, logs = self.wk("pack", etal, "-o", t)
            faits = [x for x in os.listdir(t) if x.lower().endswith(".archive")]
            if len(faits) != 1:
                raise Erreur("The CLI returned no archive. Nothing was written. " + " ; ".join(self.soucis(logs) or lignes[-3:]))
            dedans_, _ = self.wk("archive", os.path.join(t, faits[0]), "-l")
            if not dedans_:
                raise Erreur("Empty archive: no file of the folder is of a type the CLI packs (" +
                             ", ".join(sorted({os.path.splitext(k)[1] or "(sans)" for k in contenu})[:12]) + "). Nothing was written.")
            final = os.path.join(out, nom + ".archive")
            remplace = os.path.isfile(final)
            os.replace(os.path.join(t, faits[0]), final)
        finally:
            shutil.rmtree(t, ignore_errors=True)
        pris = {x.lower().replace("/", "\\") for x in dedans_}
        laisses = sorted(k for k in contenu if k.lower().replace("/", "\\") not in pris)
        rep = {"archive": final, "octets": os.path.getsize(final), "remplace_une_ancienne": remplace, "ressources_total": len(dedans_),
               "ressources": sorted(dedans_, key=str.lower)[:150], **({"laisses_de_cote": laisses[:60]} if laisses else {}),
               **({"soucis": [s for s in self.soucis(logs) if "Unknown file extension" not in s]} if
                  [s for s in self.soucis(logs) if "Unknown file extension" not in s] else {})}
        if p.get("zip"):
            rep["zip"] = self.zippe(os.path.join(out, nom + ".zip"), [(f"archive/pc/mod/{nom}.archive", final)])
        rep["note"] = ("The archive stays in the workshop. To try it in game, the user drops the zip into an arrivals folder of a Red "
                       "Stack stack, then enables it and applies the plan.")
        return rep

    def wk_build(self, p):
        proj = self.lieu(p.get("projet"), "projet")
        cree = False
        if p.get("cree") and not (os.path.isdir(proj) and any(x.lower().endswith(".cpmodproj") for x in os.listdir(proj))):
            nom = str(p.get("nom") or os.path.basename(proj)).strip()
            if not RX_NOM.fullmatch(nom) or nom.strip(". ") != nom:
                raise Erreur(f"`nom` refused ({nom!r}): a file name, without folder.")
            for d in ("source/archive", "source/raw", "source/resources"):
                os.makedirs(os.path.join(proj, *d.split("/")), exist_ok=True)
            with open(os.path.join(proj, nom + ".cpmodproj"), "w", encoding="utf-8") as fh:
                fh.write('<?xml version="1.0" encoding="utf-8"?>\n<CP77Mod xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                         'xmlns:xsd="http://www.w3.org/2001/XMLSchema">\n'
                         f"  <Name>{escape(nom)}</Name>\n  <ModName>{escape(re.sub(r'[^0-9A-Za-z]+', '_', nom).strip('_') or 'Mod')}</ModName>\n"
                         "  <Author />\n  <Email />\n  <Version>1.0.0</Version>\n</CP77Mod>\n")
            cree = True
        if not os.path.isdir(proj):
            raise Erreur(f"Project missing: {proj} (`cree` lays down the skeleton of a new project).")
        cpm = [x for x in os.listdir(proj) if x.lower().endswith(".cpmodproj")]
        if len(cpm) != 1:
            raise Erreur(f"{proj} : " + ("no .cpmodproj (`cree` lays down the skeleton of a new project)." if not cpm
                                         else "several .cpmodproj: " + ", ".join(cpm)))
        source = self.arbre(os.path.join(proj, "source"))
        utiles = [k for k in source if re.split(r"[\\/]", k)[0].lower() in ("archive", "resources")]
        rep = {"projet": proj, "cpmodproj": cpm[0], **({"cree": True} if cree else {})}
        if not utiles:
            if cree:
                return {**rep, "ecrit": 0, "note": "Skeleton laid down, nothing to build yet: resources in source\\archive (game paths), files installed as they are "
                                                   "in source\\resources (e.g. r6\\scripts\\Mod\\x.reds)."}
            raise Erreur(f"{proj}: nothing in source\\archive nor source\\resources. Nothing was built.")
        packed = os.path.join(proj, "packed")
        arch = os.path.join(proj, "source", "archive")
        travail, t = sorted(self.de_travail(arch, self.arbre(arch))), self.tmp()
        try:                                                             # la CLI packerait aussi les JSON de wk_json : écartés
            for k in travail:                                            # le temps de construire, puis remis
                os.makedirs(os.path.dirname(os.path.join(t, k)), exist_ok=True)
                os.replace(os.path.join(arch, k), os.path.join(t, k))
            lignes, logs = self.wk("build", proj)
        finally:
            for k in travail:
                if os.path.isfile(os.path.join(t, k)):
                    os.replace(os.path.join(t, k), os.path.join(arch, k))
            shutil.rmtree(t, ignore_errors=True)
        if travail:
            rep["json_de_travail_ecartes"] = len(travail)
        if any(niv == "Error" for niv, _ in logs) and not self.arbre(packed):
            raise Erreur("The CLI built nothing. " + " ; ".join(self.soucis(logs)))
        rep.update(self.bilan(packed, {}, logs, sources=len(utiles)))
        if p.get("zip") and rep["ecrit"]:
            z = os.path.join(proj, os.path.splitext(cpm[0])[0] + ".zip")
            rep["zip"] = self.zippe(z, [(k, os.path.join(packed, k)) for k in sorted(self.arbre(packed))])
        rep["note"] = ("`packed` is shaped like the game folder and stays in the workshop. To try it in game, the user drops the zip "
                       "into an arrivals folder of a Red Stack stack, then enables it and applies the plan.")
        return rep

    # ------------------------------------------------------------ protocole

    def handle(self, msg):
        m, mid = msg.get("method"), msg.get("id")
        if mid is None:                              # notification : pas de réponse
            return None
        if m == "initialize":
            return {"protocolVersion": (msg.get("params") or {}).get("protocolVersion") or "2025-06-18",
                    "capabilities": {"tools": {}}, "serverInfo": {"name": "red-stack-wolvenkit", "version": VERSION},
                    "instructions": "WolvenKit side of Red Stack: reading the archives of Cyberpunk 2077 through the WolvenKit CLI. Start with "
                                    "wk_info. wk_cherche (search), wk_liste (list) and wk_hash only read; wk_extrait (extract), wk_exporte (export) "
                                    "and wk_json write in the user's WORKSHOP, and nowhere else. Building: wk_retouche (edit a CR2W through its "
                                    "JSON, read back after writing: read `relu`), wk_importe (image, glb to game files), wk_pack (folder to "
                                    ".archive), wk_build (WolvenKit project); they only read and write in the workshop. Typical chain: wk_extrait or "
                                    "wk_json, wk_retouche, wk_pack with zip. Never run the WolvenKit CLI by hand to get around a refusal (pattern "
                                    "too broad, ceiling, path outside the workshop): narrow the pattern. Copy nothing from the workshop to the game "
                                    "or to the repository: installing a mod is the user's action, in Red Stack. Tool names, parameters and JSON keys "
                                    "are French identifiers; the free texts are in English."}
        if m == "ping":
            return {}
        if m == "tools/list":
            return {"tools": TOOLS}
        if m == "tools/call":
            p = msg.get("params") or {}
            fn = getattr(self, p.get("name") or "", None) if str(p.get("name")).startswith("wk_") else None
            if not fn:
                raise KeyError(p.get("name"))
            try:
                text = json.dumps(fn(p.get("arguments") or {}), ensure_ascii=False, indent=1)
                if len(text) > LIMIT:
                    text = text[:LIMIT] + f"\n… cut at {LIMIT} characters: narrow it with a filter."
                return {"content": [{"type": "text", "text": text}], "isError": False}
            except (Erreur, KeyError, OSError, ValueError) as e:
                return {"content": [{"type": "text", "text": f"Erreur : {e}"}], "isError": True}
        raise KeyError(m)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for k in ("donnees", "cli", "atelier", "jeu"):
        ap.add_argument("--" + k)
    srv = Serveur(ap.parse_args())
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            rep = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Unreadable JSON"}}
        else:
            try:
                res = srv.handle(msg)
                if res is None:
                    continue
                rep = {"jsonrpc": "2.0", "id": msg["id"], "result": res}
            except KeyError as e:
                rep = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32601, "message": f"Inconnu : {e}"}}
            except Exception as e:                   # le serveur ne meurt pas sur une erreur d'outil
                rep = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32603, "message": f"{type(e).__name__} : {e}"}}
        sys.stdout.write(json.dumps(rep, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
