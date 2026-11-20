"""Red Stack : moteur du gestionnaire de mods Cyberpunk 2077 (créé le 2026-11-16).

Le dépôt de zips est la seule bibliothèque : l'outil lit la table de chaque zip (CRC-32, taille), compare au jeu,
pose et retire directement depuis les zips. Un PROFIL dit, par zip, s'il est actif et ce qu'on en prend.

  python -I red_stack.py index                         le dépôt : zips, entrées, options à piocher
  python -I red_stack.py adopte  --profil actuel       déduit du jeu le profil et le registre de pose (n'écrit pas le jeu)
  python -I red_stack.py etat    --profil actuel       état de chaque mod face au profil
  python -I red_stack.py bascule --profil P (--mod TEXTE | --section S) on|off
  python -I red_stack.py option  --profil P --mod TEXTE --nom OPTION on|off     (pack à piocher : dossier d'options)
  python -I red_stack.py option  --profil P --mod TEXTE --entree CHEMIN [--mien] on|off   un seul fichier du zip ; --mien :
                                                               « ce fichier est à ce mod » sous un motif hors Red Stack
  python -I red_stack.py priorite --profil P --gagnant TEXTE --perdant TEXTE    (qui écrase qui sur un chemin commun)
  python -I red_stack.py plan    --profil P            ce qui serait posé, remplacé, retiré ; n'écrit rien
  python -I red_stack.py applique --profil P --go      applique le plan (jeu fermé)
  python -I red_stack.py config [--depot D --jeu J --magasin M | --fixe JSON]   montre / écrit config.json : chemins,
                                                               convention, réglages, hors, référence, avant_applique
  python -I red_stack.py profils [--profil P --copie SOURCE | --profil P --supprime]   liste, copie, supprime
  python -I red_stack.py detail  --profil P --mod TEXTE        entrées du zip : option, destination, prise, état dans le jeu
  python -I red_stack.py fichier --nom TEXTE                   à quel mod appartient un fichier du jeu (registre de pose)
  python -I red_stack.py hors [--ajoute MOTIF | --retire MOTIF]   fichiers d'un installateur tiers (« hors Red Stack »)
  python -I red_stack.py conflits --profil P [--mod TEXTE | --nom ARCHIVE | --ressources]   conflits DANS les archives : ordre de
                                                               chargement, qui gagne sur qui, copies identiques à part
  python -I red_stack.py ordre --profil P [--nom ARCHIVE (--avant CIBLE | --apres CIBLE) [--voie nom|modlist] | --nom ARCHIVE
                                 --renomme NOM | --nom ARCHIVE --annule | --modlist --annule]   ordre de chargement des archives :
                                                               le lire ; proposer un nom qui passe avant / après une autre ;
                                                               renommer une archive DANS LE JEU par le profil (le zip ne change
                                                               pas) ; ou tenir `modlist.txt`. Seul le profil est écrit : le jeu
                                                               suit au prochain `applique`.
  python -I red_stack.py noms --profil P --mod TEXTE [--fixe JSON]   noms DANS LE JEU de ce qu'un mod pose (archives, `.xl`,
                                                               fichiers et dossiers de scripts et de tweaks, dossier CET,
                                                               dossier REDmod), et qui les cite ; --fixe [{de, vers}] note
                                                               les nouveaux noms au profil (vers vide = nom de l'auteur)
  python -I red_stack.py deplace --cle CLE --vers parques|pile|retires [--go]   parquer un zip coupé et sorti du jeu, le retirer, ou remonter
                                                               un zip parqué / arrivé à la racine de sa pile (écrit le DÉPÔT)
  python -I red_stack.py reference [--cree | --restaure --go]  copie du jeu vierge sans `archive` : la créer (jeu vierge,
                                                               avant tout mod), contrôler le jeu contre elle, y revenir
  python -I red_stack.py magasin --profil P                    état des liens et poids réel : ce que le magasin et les mods du
                                                               jeu pèsent vraiment sur le disque, arbres sans mod actif
                                                               (`purge --go` les supprime), retouches (lecture seule)
  python -I red_stack.py sauvegarde [--cree | --restaure --nom NOM [--go]]   réglages des mods (fichiers jamais liés, livrés
                                                               ou écrits en jeu) : lister les sauvegardes, en faire une,
                                                               voir ce qu'une restauration changerait, la faire (jeu fermé)
  python -I red_stack.py nexus [--force | --compte | --cle CLE [--fichier ID] [--nom ZIP] [--lien NXM] [--go] | on|off --cle CLE
                               --ignore]                      mises à jour :
                                                               compare chaque zip aux fichiers de son mod sur Nexus ; --cle
                                                               télécharge la nouvelle version à la place de l'ancienne, rangée
                                                               dans les retirés (clé d'API : variable RED_STACK_NEXUS_KEY ;
                                                               compte gratuit : --lien du bouton « Mod manager download »)
  python -I red_stack.py nexus --lien NXM [--section PILE [--go]]   lien reçu du site : dit quels zips il met à jour ; --section
                                                               range un mod nouveau dans le dossier d'arrivée de cette pile
  python -I red_stack.py convention --range --cle ARRIVAGE --de ZIP [--nom NOM] [--go]   un zip téléchargé à la main prend la
                                                               place du zip qu'il met à jour (aucune clé d'API)
  `plan --json` porte une `empreinte` ; `applique --go --si-plan EMPREINTE` refuse si le plan a changé depuis l'aperçu.
  config.json `avant_applique` : commande (liste) lancée avant d'écrire le vrai jeu, ex. la sauvegarde des réglages.
  Options communes : --json, --jeu <racine> (banc), --depot <racine>, --vrai-jeu (exigé pour écrire le vrai jeu),
  --force (remplace aussi les fichiers modifiés en jeu ou inconnus, après copie dans le dossier des sauvegardes, `_red_stack_<date>`).
  --remplace DEST (répétable) : ne remplace que CE fichier présent et pas posé par l'outil, avec la même copie de sauvegarde.
  Données de l'outil (config.json, profils, registre de pose, caches) : --donnees, sinon « red_stack » à côté du script.

Vocabulaire. Entrée « directe » : sous une racine du jeu (archive, bin, r6, red4ext, engine, mods). « Option » : dossier
du zip qui porte son propre arbre du jeu (`Common/archive/pc/mod/…`) ou des `.archive` / `.xl` en vrac (posés dans
`archive/pc/mod`). Le reste (images, textes, zips imbriqués, dossiers `__…`) n'est jamais posé.
Profil : mods[<section>/<zip>] = {actif, sel: {option: "*" | [entrées]}, renomme: {entrée: destination}} ;
priorites = [[gagnant, perdant], …]. Registre de pose : destination -> zip, entrée, CRC, taille de ce que l'outil a posé
(ou reconnu à l'adoption) : c'est lui qui permet une mise à jour sans l'ancien zip et un retrait sans casse.
Règles : un fichier n'est retiré ou remplacé que s'il est encore celui du registre ; modifié en jeu, il est gardé et
signalé. Un fichier livré par un autre mod actif n'est jamais retiré. Les fichiers créés par les mods ne sont pas touchés.
"""
import argparse, bisect, collections, datetime, fnmatch, hashlib, json, os, re, shutil, stat, struct, subprocess, sys, zipfile, zlib

# Avant Python 3.15, la sortie vers un tube suit la page de codes de Windows : refus et JSON sortent en UTF-8, toujours.
for _f in (sys.stdout, sys.stderr):
    if hasattr(_f, "reconfigure"):
        _f.reconfigure(encoding="utf-8")

# Langue des textes. Le texte français du code est la clé ; `langues/<code>.json` (à côté du dossier `moteur` : le même
# catalogue que l'extension) donne celui d'une autre langue, et ce qui lui manque reste en français. `--langue CODE` est lu
# ici, avant tout le reste, parce que des tables du module portent déjà des textes.
# Les états rendus en JSON (« posé », « coupé », « lié »…) sont des CODES que la page et les serveurs MCP comparent : jamais
# traduits dans le JSON. La page les dit dans sa langue ; `C` les dit en mode texte.
LANGUE, TEXTES = "fr", {}


def regle_langue(code, dossier=None):
    """Charge le catalogue de `code` (« en », « pt-br »…) ; langue inconnue ou « fr » : le français du code."""
    global LANGUE, TEXTES
    LANGUE, TEXTES = "fr", {}
    dossier = dossier or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "langues")
    for c in dict.fromkeys((str(code).lower(), str(code).lower().split("-")[0])):
        if c == "fr" or not re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]{2,8})?", c):
            return
        try:
            lu = json.load(open(os.path.join(dossier, c + ".json"), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(lu, dict):
            LANGUE, TEXTES = c, lu
            return


def T(s, *v):
    """Texte dans la langue réglée ; {0}, {1}… reçoivent les valeurs."""
    t = TEXTES.get(s)
    s = t if isinstance(t, str) else s
    return re.sub(r"\{(\d+)\}", lambda m: str(v[int(m.group(1))]) if int(m.group(1)) < len(v) else m.group(0), s) if v else s


def forme_pluriel(langue, n):
    """Forme du pluriel de `n` dans `langue` (règles CLDR des langues livrées) : « one », « few », « many » ou « other »."""
    base = langue.split("-")[0]
    n = abs(n)
    entier = n == int(n)
    if base in ("zh", "ja", "ko"):
        return "other"
    if base == "fr":
        return "one" if n < 2 else "other"
    if base in ("pl", "ru"):
        if not entier:
            return "other"
        d, c = int(n) % 10, int(n) % 100
        if base == "pl":
            return "one" if n == 1 else "few" if 2 <= d <= 4 and not 12 <= c <= 14 else "many"
        return "one" if d == 1 and c != 11 else "few" if 2 <= d <= 4 and not 12 <= c <= 14 else "many"
    return "one" if n == 1 else "other"                # anglais, allemand, espagnol, italien, portugais


def N(n, un, plusieurs, *v):
    """Pluriel : {n} reçoit le nombre, {0}, {1}… les autres valeurs. Le catalogue porte un objet de formes sous la clé du
    singulier (`one`, `few`, `many`, `other`), comme `N` de l'extension ; sans lui, le français : `plusieurs` au-delà de 1."""
    t = TEXTES.get(un)
    s = plusieurs if n > 1 else un
    if isinstance(t, dict):
        s = t.get(forme_pluriel(LANGUE, n)) or t.get("other") or s
    elif isinstance(t, str):
        s = t
    s = s.replace("{n}", str(n))
    return re.sub(r"\{(\d+)\}", lambda m: str(v[int(m.group(1))]) if int(m.group(1)) < len(v) else m.group(0), s) if v else s


def C(code):
    """Code d'état (« posé », « coupé »…) dit dans la langue réglée : pour le mode texte seulement, jamais dans le JSON."""
    t = TEXTES.get(code)
    return t if isinstance(t, str) else code


def suite(*morceaux, sep=None):
    """Propositions entières jointes par le séparateur de la langue (« ; » d'office, `sep=T(", ")` pour une virgule) ;
    les vides sont sautées. Un texte ne commence ni ne finit jamais par son séparateur : chaque langue a le sien."""
    return (T(" ; ") if sep is None else sep).join(m for m in morceaux if m)


for _i, _x in enumerate(sys.argv[1:], 1):
    if _x == "--langue" and _i + 1 < len(sys.argv):
        regle_langue(sys.argv[_i + 1])
    elif _x.startswith("--langue="):
        regle_langue(_x[9:])

# Rien de propre à un poste ici : dépôt, jeu, magasin, dossier des sauvegardes et convention de dossiers sont dans
# config.json (commande `config`). Convention = motifs (jokers `*` `?` `[…]`, casse ignorée) sur des NOMS de dossiers :
# `piles` à la racine du dépôt ; `parques`, `nouveaux`, `retires` = sous-dossiers d'une pile dont les zips ne sont pas
# posés ; `ignores_dans_zip` = dossiers d'un zip jamais posés ; `zips_ignores` = motifs sur des NOMS DE ZIPS d'une pile qui
# ne sont pas des mods (documentation, sources…) : jamais listés. Les valeurs ci-dessous sont les défauts.
CONVENTION = {"piles": ["[0-9]*_*"], "parques": ["__RAM*"], "nouveaux": ["__NEW*"], "retires": ["__DEL*"],
              "ignores_dans_zip": ["__*"], "zips_ignores": []}
CONV = {k: list(v) for k, v in CONVENTION.items()}
GENRES = (("parques", "parqué"), ("nouveaux", "nouveau"), ("retires", "retiré"))
ROOTS = ("archive", "bin", "r6", "red4ext", "engine", "mods")
NEXT = {"archive": ("pc",), "bin": ("x64",), "red4ext": ("plugins",)}  # garde-fou : `archive` d'option suivi de `pc`
LOOSE = {".archive": "archive/pc/mod", ".xl": "archive/pc/mod"}
RACINE = "(racine)"
PILE_RACINE = "(racine)"                             # nom de la pile des zips posés à la racine même du dépôt
# Réglages : fichiers livrés que le mod ou le joueur réécrit. Jamais liés à l'arbre du mod (copiés), donc gardés quand le
# mod est coupé, remis ou mis à jour. Motifs sur la destination dans le jeu, en minuscules ; `*` traverse les dossiers.
# L'utilisateur complète par la commande `reglage` (config.json) ; l'adoption y ajoute ce qu'elle trouve modifié en jeu.
_CET = "bin/x64/plugins/cyber_engine_tweaks/"
REGLAGES = ["*.ini", "*.toml", "*.cfg", "*.sqlite3", "*.db", "r6/storages/*", "r6/cache/*", "r6/config/*",
            _CET + "config.json", _CET + "bindings.json", _CET + "persistent.json", _CET + "layout.ini"] + [
    _CET + "mods/*/" + n for n in (
        "settings.*", "config.*", "*settings*.json", "*config*.json", "*preferences*.json", "*presets*.json",
        "*presets*.lua", "*_state.json", "*state*.lua", "window_cache.json", "tutorials.json", "userparameters.json",
        "excluded*.txt", "user/*", "data/favorite/*")]


# Hors Red Stack : territoire d'un installateur tiers (ReShade pose lui-même `bin/x64/reshade-shaders`). Motifs sur la
# destination, donnés par l'utilisateur (config.json `hors`, commande `hors`). Sous un tel motif, un fichier PRÉSENT que
# l'outil n'a pas posé lui-même est à l'installateur : jamais lié, remplacé, retiré ni compté au mod, même identique à
# celui d'un zip. Un fichier ABSENT que le profil prend est posé en copie et marqué `ajout` au registre : lui seul est au
# mod, et part avec lui.
HORS = []
# « Ce fichier est à ce mod » : exception, fichier par fichier, dite par l'utilisateur (profil : `miens` du mod, destinations
# en minuscules). Un fichier présent sous un motif hors est alors pris au registre pour ce mod, marqué `ajout` et `pris`,
# jamais lié ; il part avec le mod. Case décochée : il est rendu à l'installateur, laissé dans le jeu, sorti du registre.
MIENS = {}                                           # destination minuscule -> clé du mod qui la revendique (profil chargé)


def est_hors(dest):
    d = dest.lower()
    return any(fnmatch.fnmatchcase(d, p) for p in HORS)


def a_tiers(jeu, pose, dest):
    """ce fichier est-il, dans le jeu, celui d'un installateur tiers ? (présent, sous un motif hors, ni ajouté par nous
    ni revendiqué pour un mod ; un fichier pris puis rendu, encore au registre, est de nouveau à l'installateur)"""
    dl = dest.lower()
    r = pose.get(dl) or {}
    return (bool(HORS) and est_hors(dest) and jeu.size(dest) is not None and dl not in MIENS
            and (not r.get("ajout") or bool(r.get("pris"))))


def reg_row(row):
    r = {k: row[k] for k in ("dest", "zip", "entree", "crc", "taille")}
    for k in ("ajout", "pris"):
        if row.get(k):
            r[k] = True
    return r


def charge_miens(prof):
    MIENS.clear()
    for key, mp in prof["mods"].items():
        for d in mp.get("miens", []):
            MIENS[d] = key


# Référence du jeu : copie du jeu VIERGE sans ses archives (exécutables, bibliothèques, scripts du socle), faite une fois,
# avant tout mod. Elle sert de retour arrière si le lanceur force une mise à jour, et de contrôle de corruption. Les
# dossiers exclus (motifs sur les dossiers de la racine du jeu) sont dans config.json `reference_exclus`.
REF_EXCLUS = ["archive"]
REF_MARK = "red_stack_reference.json"


def ref_files(root, exclus):
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root).replace(os.sep, "/")
        if rel == ".":
            rel = ""
            dirs[:] = [d for d in dirs if not match(d, exclus)]
        for f in files:
            if not (rel == "" and f == REF_MARK):
                yield (rel + "/" + f).lstrip("/")


# ---------------------------------------------------------------- dépôt

def match(name, motifs):
    n = name.lower()
    return any(fnmatch.fnmatchcase(n, m.lower()) for m in motifs)


def load_conf(data):
    """config.json du dossier de données ; règle la convention de dossiers pour tout le module."""
    p = os.path.join(data, "config.json")
    conf = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}
    conf.setdefault("reglages", [])
    conf.setdefault("hors", [])
    HORS[:] = [p.lower().replace("\\", "/") for p in conf["hors"]]
    for k, v in CONVENTION.items():
        CONV[k] = list(conf.get("convention", {}).get(k, v))
    return conf


def classify(name):
    """(option, destination) d'une entrée de zip, ou (None, None) si elle ne se pose pas."""
    parts = name.split("/")
    if any(match(p, CONV["ignores_dans_zip"]) for p in parts[:-1]):
        return None, None
    if parts[0].lower() in ROOTS and len(parts) > 1:
        return "", name
    for i in range(1, len(parts) - 1):
        low = parts[i].lower()
        if low in ROOTS and (low not in NEXT or parts[i + 1].lower() in NEXT[low]):
            return "/".join(parts[:i]), "/".join(parts[i:])
    ext = os.path.splitext(parts[-1])[1].lower()
    if ext in LOOSE:
        return "/".join(parts[:-1]) or RACINE, LOOSE[ext] + "/" + parts[-1]
    return None, None


def sections(depot):
    def order(d):                                    # un numéro en tête range la pile, sinon l'alphabet, après
        m = re.match(r"\d+", d)
        return (int(m.group()) if m else 1 << 30, d.lower())
    noms = os.listdir(depot)
    piles = sorted((d for d in noms if d != PILE_RACINE and match(d, CONV["piles"]) and os.path.isdir(os.path.join(depot, d))),
                   key=order)
    # des archives posées à la racine même du dépôt (ou dans un dossier d'arrivée, de parqués, de retirés de la racine) :
    # une pile à part, la dernière, pour qui garde ses zips en vrac dans un seul dossier
    lieux = [depot] + [os.path.join(depot, d) for d in noms if d not in piles and genre_of(d) and os.path.isdir(os.path.join(depot, d))]
    if any(f.lower().endswith((".zip",) + AUTRES_ARCHIVES) and not match(f, CONV["zips_ignores"]) and os.path.isfile(os.path.join(l, f))
           for l in lieux for f in (noms if l is depot else os.listdir(l))):
        piles.append(PILE_RACINE)
    return piles


def dossier_pile(depot, sec):
    """dossier d'une pile ; la pile de la racine est le dépôt lui-même"""
    return depot if sec == PILE_RACINE else os.path.join(depot, sec)


def sous_dossiers(depot, sec):
    """dossiers de convention (parqués, arrivée, retirés) d'une pile ; à la racine, un dossier qui est une pile le reste"""
    base = dossier_pile(depot, sec)
    return [d for d in sorted(os.listdir(base)) if genre_of(d) and os.path.isdir(os.path.join(base, d))
            and not (sec == PILE_RACINE and match(d, CONV["piles"]))]


def ecarts_du_depot(depot):
    """ce que la convention ne lit pas : dossiers de la racine qui portent des archives sans être des piles, et archives
    rangées dans un sous-dossier de pile qui n'est pas un dossier de convention ; {piles, hors_piles, profonds}"""
    def compte(d):
        try:
            return sum(1 for f in os.listdir(d) if f.lower().endswith((".zip",) + AUTRES_ARCHIVES) and os.path.isfile(os.path.join(d, f)))
        except OSError:
            return 0
    piles = sections(depot)
    a_la_racine = sous_dossiers(depot, PILE_RACINE) if PILE_RACINE in piles else []
    hors, profonds = [], []
    for d in sorted(os.listdir(depot)):
        p = os.path.join(depot, d)
        if d not in piles and d not in a_la_racine and os.path.isdir(p) and compte(p):
            hors.append({"dossier": d, "archives": compte(p)})
    for sec in piles:
        base = os.path.join(depot, sec)
        for d in sorted(os.listdir(base)) if sec != PILE_RACINE else []:
            p = os.path.join(base, d)
            if os.path.isdir(p) and not genre_of(d) and compte(p):
                profonds.append({"dossier": sec + "/" + d, "archives": compte(p)})
    return {"piles": len(piles), "hors_piles": hors, "profonds": profonds}


def genre_of(dossier):
    """genre d'un sous-dossier de pile (parqué, nouveau, retiré), ou None s'il n'en est pas un"""
    return next((g for k, g in GENRES if match(dossier, CONV[k])), None)


def ident(name):
    """(radical, modId) : identité d'un mod d'une version à l'autre (même règle que pose_maj.py)."""
    base = name[:-4] if name.lower().endswith(".zip") else name
    m = re.search(r"-(\d{3,6})-", base)
    head = re.split(r"-\d{3,6}-", base, maxsplit=1)[0]
    stamp = re.search(r"\d{9,10}", base[m.end():]) if m else None
    # ce qui suit l'horodatage Nexus distingue deux variantes d'un même mod (« EDITED 1.1 ») ; sa version ne compte pas
    tail = re.sub(r"[\d.]+", "", base[m.end():][stamp.end():]) if stamp else ""
    return re.sub(r"\s+[vV]?[\d.]+$", "", head).strip().lower() + "|" + tail.strip().lower(), m.group(1) if m else ""


def version(name):
    m = re.search(r"-\d{3,6}-([\w\-.]+?)-\d{9,10}", name)
    return m.group(1).replace("-", ".") if m else ""


def load_index(depot, data):
    """{clé: {zip, section, lieu, entrees: [{n, c, s, o, d}]}} ; cache par taille et date du zip."""
    cache_path = os.path.join(data, "index.json")
    cache = {}
    if os.path.isfile(cache_path):
        try:
            cache = json.load(open(cache_path, encoding="utf-8"))
        except ValueError:
            cache = {}
    conv = json.dumps(CONV, sort_keys=True)
    meme_conv = cache.pop("", None) == conv         # clé vide : la convention du cache
    out, dirty = {}, not meme_conv
    for sec in sections(depot):
        base = dossier_pile(depot, sec)
        places = [("", base)] + [(d, os.path.join(base, d)) for d in sous_dossiers(depot, sec)]
        for lieu, folder in places:
            sous = lieu
            for f in sorted(os.listdir(folder)):
                p = os.path.join(folder, f)
                if not f.lower().endswith(".zip") or not os.path.isfile(p) or match(f, CONV["zips_ignores"]):
                    continue
                key = "/".join(x for x in (sec, sous, f) if x)
                st = os.stat(p)
                sig = [st.st_size, st.st_mtime_ns]
                c = cache.get(key)
                if not c or c.get("sig") != sig or c.get("v") != INDEX_V:
                    ents, brut = [], {}
                    with zipfile.ZipFile(p) as z:
                        for i in z.infolist():
                            if i.is_dir():
                                continue
                            n = i.filename.replace("\\", "/").lstrip("/")
                            o, d = classify(n)
                            ents.append({"n": n, "c": i.CRC, "s": i.file_size, "o": o, "d": d})
                            brut[n] = i
                        c = {"sig": sig, "entrees": ents, "v": INDEX_V}
                        cfg = fomod_entree(brut)
                        if cfg:                          # installateur FOMOD : sa description entre dans l'index
                            try:
                                c["fomod"] = lit_fomod(list(brut), z.read(brut[cfg]), cfg[:-len("fomod/ModuleConfig.xml")])
                            except Exception as e:       # XML illisible : le zip reste un pack à piocher, et le dit
                                c["fomod_erreur"] = f"{type(e).__name__} : {e}"[:300]
                        for e in ents:                   # REDmod : nom et version déclarés par son info.json
                            if e["d"] and re.fullmatch(r"mods/[^/]+/info\.json", e["d"].lower()) and e["s"] < 1 << 20:
                                r = lit_redmod(z.read(brut[e["n"]]).decode("utf-8-sig", "replace"), e["d"].split("/")[1])
                                if r:
                                    c.setdefault("redmod", []).append(r)
                    dirty = True
                if "empreinte" not in c:                 # contenu du zip, indépendant de son nom et de sa place
                    c["empreinte"] = hashlib.sha1(json.dumps(sorted((e["n"], e["c"], e["s"]) for e in c["entrees"])).encode()).hexdigest()
                    dirty = True
                if not meme_conv:                    # la convention a changé depuis la mise en cache
                    for e in c["entrees"]:
                        e["o"], e["d"] = classify(e["n"])
                out[key] = {"zip": p, "section": sec, "lieu": lieu, "genre": genre_of(lieu) if lieu else "actif",
                            "nom": f, "taille": st.st_size,
                            "sig": sig, "entrees": c["entrees"], "empreinte": c["empreinte"],
                            **{x: c[x] for x in PLUS_INDEX if x in c}}
    if dirty or set(cache) != set(out):
        os.makedirs(data, exist_ok=True)
        json.dump({"": conv, **{k: {"sig": v["sig"], "entrees": v["entrees"], "empreinte": v["empreinte"], "v": INDEX_V,
                                    **{x: v[x] for x in PLUS_INDEX if x in v}} for k, v in out.items()}},
                  open(cache_path, "w", encoding="utf-8"))
    return out


def options_of(mod):
    c = collections.Counter(e["o"] for e in mod["entrees"] if e["o"] is not None)
    return dict(c)


def version_de(mod):
    """version montrée : celle du nom du zip (forme du site Nexus), sinon celle de l'`info.json` d'un REDmod qu'il livre"""
    return version(mod["nom"]) or next((r["version"] for r in mod.get("redmod") or [] if r.get("version")), "")


def lit_redmod(texte, dossier):
    """nom et version déclarés par `mods/<dossier>/info.json` (REDmod), ou None s'il est illisible"""
    try:
        d = json.loads(texte)
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    return {"dossier": dossier, "nom": str(d.get("name") or ""), "version": str(d.get("version") or "")}


# ---------------------------------------------------------------- FOMOD

# Un zip qui porte `fomod/ModuleConfig.xml` décrit son installation : fichiers toujours posés, pages de choix (groupes à
# choix unique ou multiple), drapeaux posés par un choix, pages et fichiers qui en dépendent. L'index garde cette
# description ; le profil garde les choix (`fomod` du mod : `choix` = {clé du groupe: [noms]}, `hors_jeu`, `libre`).
# `fomod_resolu` rejoue l'installateur : c'est lui qui dit quelles entrées du zip vont où. Ce qui n'est pas rejoué : une
# condition sur un fichier présent dans le jeu (`fileDependency`) est tenue pour « absent », une condition sur la version
# du jeu ou de l'installateur pour vraie.
INDEX_V = 2                                          # ce que l'index garde d'un zip : un cache d'une autre version est relu
PLUS_INDEX = ("fomod", "fomod_erreur", "redmod")     # ce qu'un zip peut porter en plus de ses entrées
FOMOD_GROUPES = ("SelectExactlyOne", "SelectAtMostOne", "SelectAtLeastOne", "SelectAll", "SelectAny")
FOMOD_USAGES = ("Required", "Recommended", "Optional", "CouldBeUsable", "NotUsable")
FOMOD_IMAGES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
                ".bmp": "image/bmp"}
FOMOD_IMAGE_MAX = 6 << 20


def _fo_tag(el):
    return el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""


def _fo_un(el, nom):
    return next((c for c in el if _fo_tag(c) == nom), None) if el is not None else None


def _fo_chemin(s):
    """chemin écrit dans un ModuleConfig.xml : barres à l'endroit, sans barre de tête ; None s'il sort de son dossier"""
    parts = [p for p in (s or "").replace("\\", "/").split("/") if p not in ("", ".")]
    if any(p == ".." or ":" in p for p in parts):
        return None
    return "/".join(parts)


def fomod_entree(noms):
    """l'entrée `fomod/ModuleConfig.xml` d'un zip (à sa racine, ou sous un dossier de tête), ou None"""
    c = [n for n in noms if n.lower() == "fomod/moduleconfig.xml" or n.lower().endswith("/fomod/moduleconfig.xml")]
    return min(c, key=lambda n: (n.count("/"), n)) if c else None


def lit_fomod(noms, brut, racine=""):
    """Description d'un installateur FOMOD. `noms` : entrées du zip ; `racine` : dossier du zip qui porte `fomod/` (fini
    par une barre, ou vide). Les sources sont résolues ici en entrées du zip : [entrée, destination, priorité]."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(brut)
    par = {n.lower(): n for n in noms}
    manquants, limites = [], []

    def note(l):
        if l not in limites:
            limites.append(l)

    def fichiers(el):
        out = []
        for c in (el if el is not None else ()):
            t = _fo_tag(c)
            if t not in ("file", "folder"):
                continue
            src, dst = _fo_chemin(c.get("source")), c.get("destination")
            try:
                prio = int(c.get("priority") or 0)
            except ValueError:
                prio = 0
            if src is None:
                note(T("source hors du zip, laissée : {0}", c.get('source')))
                continue
            plein = racine + src
            if t == "file":
                vrai = par.get(plein.lower())
                if not vrai:
                    manquants.append(src)
                    continue
                base = vrai.split("/")[-1]
                d = src if dst is None else base if not dst.strip() else dst + base if dst.rstrip()[-1] in "/\\" else dst
                d = _fo_chemin(d)
                if not d:
                    note(T("destination refusée : {0}", dst))
                    continue
                out.append([vrai, d, prio])
            else:
                pre = (plein.rstrip("/") + "/").lower() if plein else ""
                d0 = _fo_chemin(src if dst is None else dst)
                if d0 is None:
                    note(T("destination refusée : {0}", dst))
                    continue
                n0 = len(out)
                for low, vrai in par.items():
                    if low.startswith(pre):
                        rel = vrai[len(pre):]
                        if not rel or (not src and rel.lower().startswith("fomod/")):
                            continue
                        out.append([vrai, (d0 + "/" + rel) if d0 else rel, prio])
                if len(out) == n0:
                    manquants.append(src + "/")
        return out

    def cond(el):
        if el is None:
            return None
        termes = []
        for c in el:
            t = _fo_tag(c)
            if t == "flagDependency":
                termes.append({"d": c.get("flag") or "", "v": c.get("value") or ""})
            elif t == "fileDependency":
                termes.append({"f": c.get("file") or "", "e": c.get("state") or "Active"})
                note(T("une condition porte sur un fichier présent dans le jeu : elle n'est pas rejouée (fichier tenu pour absent)"))
            elif t == "dependencies":
                termes.append(cond(c))
            elif t.endswith("Dependency"):
                termes.append({"vrai": 1})
        return {"op": "Or" if (el.get("operator") or "And").lower() == "or" else "And", "t": termes}

    def texte(el):
        return (el.text or "").strip() if el is not None else ""

    def usage(el):
        """[type par défaut, [(condition, type)]] d'un `typeDescriptor`"""
        t = _fo_un(el, "type")
        if t is not None:
            return [t.get("name") or "Optional", []]
        dt = _fo_un(el, "dependencyType")
        if dt is None:
            return ["Optional", []]
        defaut = _fo_un(dt, "defaultType")
        pats = []
        for p in (_fo_un(dt, "patterns") if _fo_un(dt, "patterns") is not None else ()):
            if _fo_tag(p) == "pattern":
                ty = _fo_un(p, "type")
                pats.append([cond(_fo_un(p, "dependencies")), (ty.get("name") if ty is not None else "") or "Optional"])
        return [(defaut.get("name") if defaut is not None else "") or "Optional", pats]

    etapes, cles = [], set()
    steps = _fo_un(root, "installSteps")
    for s in (steps if steps is not None else ()):
        if _fo_tag(s) != "installStep":
            continue
        et = {"nom": s.get("name") or "", "visible": cond(_fo_un(s, "visible")), "groupes": []}
        gs = _fo_un(s, "optionalFileGroups")
        for g in (gs if gs is not None else ()):
            if _fo_tag(g) != "group":
                continue
            cle = base = (et["nom"] + " › " if et["nom"] else "") + (g.get("name") or "")
            i = 2
            while cle in cles:
                cle, i = f"{base} ({i})", i + 1
            cles.add(cle)
            ty = g.get("type") or "SelectAny"
            gr = {"cle": cle, "nom": g.get("name") or "", "type": ty if ty in FOMOD_GROUPES else "SelectAny", "plugins": []}
            ps = _fo_un(g, "plugins")
            for p in (ps if ps is not None else ()):
                if _fo_tag(p) != "plugin":
                    continue
                img = _fo_un(p, "image")
                ip = _fo_chemin(img.get("path")) if img is not None else None
                fl = _fo_un(p, "conditionFlags")
                gr["plugins"].append({
                    "nom": p.get("name") or "", "desc": texte(_fo_un(p, "description")),
                    "image": par.get((racine + ip).lower()) if ip else None,
                    "drapeaux": {f.get("name") or "": texte(f) for f in (fl if fl is not None else ()) if _fo_tag(f) == "flag"},
                    "fichiers": fichiers(_fo_un(p, "files")), "usage": usage(_fo_un(p, "typeDescriptor"))})
            et["groupes"].append(gr)
        etapes.append(et)
    conds = []
    pats = _fo_un(_fo_un(root, "conditionalFileInstalls"), "patterns")
    for p in (pats if pats is not None else ()):
        if _fo_tag(p) == "pattern":
            conds.append({"si": cond(_fo_un(p, "dependencies")), "fichiers": fichiers(_fo_un(p, "files"))})
    if manquants:
        note(N(len(manquants), "{n} source citée par l'installateur n'est pas dans le zip : ", "{n} sources citées par l'installateur ne sont pas dans le zip : ") + ", ".join(sorted(set(manquants))[:6]))
    return {"module": texte(_fo_un(root, "moduleName")), "requis": fichiers(_fo_un(root, "requiredInstallFiles")),
            "etapes": etapes, "conditionnels": conds, "limites": limites}


def fo_vrai(c, drapeaux):
    if not c or not c["t"]:
        return True

    def un(t):
        if "d" in t:
            return drapeaux.get(t["d"], "") == t["v"]
        if "f" in t:
            return t["e"].lower() != "active"        # fichier du jeu : tenu pour absent
        return True if "vrai" in t else fo_vrai(t, drapeaux)
    r = [un(t) for t in c["t"]]
    return any(r) if c["op"] == "Or" else all(r)


def fo_usage(p, drapeaux):
    defaut, pats = p["usage"]
    u = next((t for c, t in pats if fo_vrai(c, drapeaux)), defaut)
    return u if u in FOMOD_USAGES else "Optional"


def fo_choisis(g, usages, voulu):
    """indices des choix retenus d'un groupe : ce que l'utilisateur veut, ramené à ce que le groupe permet"""
    n, t = len(g["plugins"]), g["type"]
    if t == "SelectAll":
        return set(range(n))
    possibles = [i for i in range(n) if usages[i] != "NotUsable"]
    forces = [i for i in possibles if usages[i] == "Required"]
    if voulu is None:
        sel = [i for i in possibles if usages[i] in ("Required", "Recommended")]
    else:
        rang = {nom: k for k, nom in reversed(list(enumerate(voulu)))}
        sel = sorted((i for i in possibles if g["plugins"][i]["nom"] in rang), key=lambda i: rang[g["plugins"][i]["nom"]])
        sel = forces + [i for i in sel if i not in forces]
    if t in ("SelectExactlyOne", "SelectAtMostOne") and len(sel) > 1:
        sel = sel[:1]
    if t in ("SelectExactlyOne", "SelectAtLeastOne") and not sel:
        sel = ([i for i in possibles if usages[i] == "Recommended"] or possibles or list(range(n)))[:1]
    return set(sel)


def du_jeu(dest):
    """cette destination est-elle dans un des dossiers du jeu que les mods remplissent ?"""
    p = dest.split("/")
    return len(p) > 1 and p[0].lower() in ROOTS


def fomod_resolu(fo, etat=None):
    """Rejoue l'installateur pour les choix du profil. Rend les pages telles qu'elles se présentent (visible, choisi,
    usage de chaque choix), les choix retenus, et `fichiers` : [(entrée du zip, destination)], dernier écrit gagnant."""
    etat = etat or {}
    choix = etat.get("choix") or {}
    drapeaux, pris, pages, retenus = {}, [list(f) for f in fo["requis"]], [], {}
    for et in fo["etapes"]:
        vis = fo_vrai(et.get("visible"), drapeaux)
        groupes = []
        for g in et["groupes"]:
            usages = [fo_usage(p, drapeaux) for p in g["plugins"]]
            sel = fo_choisis(g, usages, choix.get(g["cle"])) if vis else set()
            if vis:
                retenus[g["cle"]] = [g["plugins"][i]["nom"] for i in sorted(sel)]
            for i in sorted(sel):
                drapeaux.update(g["plugins"][i]["drapeaux"])
                pris += g["plugins"][i]["fichiers"]
            groupes.append({"cle": g["cle"], "nom": g["nom"], "type": g["type"],
                            "plugins": [{"nom": p["nom"], "desc": p["desc"], "image": p["image"], "usage": usages[i],
                                         "choisi": i in sel, "fichiers": len(p["fichiers"]),
                                         "fige": g["type"] == "SelectAll" or usages[i] in ("Required", "NotUsable")}
                                        for i, p in enumerate(g["plugins"])]})
        pages.append({"nom": et["nom"], "visible": vis, "groupes": groupes})
    for c in fo["conditionnels"]:
        if fo_vrai(c["si"], drapeaux):
            pris += c["fichiers"]
    final = {}
    for n, d, _ in sorted(pris, key=lambda f: f[2]):  # tri stable : à priorité égale, le dernier décrit gagne
        final.pop(d.lower(), None)
        final[d.lower()] = (n, d)
    tous = list(final.values())
    hors = [f for f in tous if not du_jeu(f[1])]
    garde_hors = etat.get("hors_jeu", True)
    return {"pages": pages, "choix": retenus, "drapeaux": drapeaux, "hors": hors,
            "fichiers": tous if garde_hors else [f for f in tous if du_jeu(f[1])]}


def fomod_actif(mod, mp):
    """ce zip est-il posé par son installateur ? Non s'il n'en a pas, si l'utilisateur l'a rendu « pack à piocher »
    (`libre`), ou si le profil porte déjà une sélection faite à la main avant que l'installateur soit lu."""
    if not mod.get("fomod"):
        return False
    etat = (mp or {}).get("fomod")
    return not etat.get("libre") if etat is not None else "sel" not in (mp or {})


def fomod_bref(mod, mp):
    """ce que la liste et le détail d'un mod disent de son installateur, ou None s'il n'en a pas"""
    if mod.get("fomod_erreur"):
        return {"actif": False, "erreur": mod["fomod_erreur"]}
    if not mod.get("fomod"):
        return None
    r = fomod_resolu(mod["fomod"], (mp or {}).get("fomod"))
    return {"actif": fomod_actif(mod, mp), "module": mod["fomod"]["module"], "fichiers": len(r["fichiers"]),
            "choix": sum(1 for p in r["pages"] if p["visible"] for g in p["groupes"] if g["type"] != "SelectAll"),
            "regle": bool((mp or {}).get("fomod"))}


def fomod_vue(key, mod, mp):
    """l'installateur tel qu'il se présente pour les choix du profil, et ce qu'il poserait"""
    etat = (mp or {}).get("fomod") or {}
    r = fomod_resolu(mod["fomod"], etat)
    return {"cle": key, "nom": mod["nom"], "module": mod["fomod"]["module"], "actif": bool(mp and mp.get("actif")),
            "lieu": mod["lieu"], "genre": mod["genre"], "par_fomod": fomod_actif(mod, mp), "libre": bool(etat.get("libre")),
            "regle": bool(etat), "hors_jeu": etat.get("hors_jeu", True), "pages": r["pages"], "choix": r["choix"],
            "fichiers": [{"entree": n, "dest": d, "hors_jeu": not du_jeu(d)} for n, d in r["fichiers"]],
            "compte": {"poses": len(r["fichiers"]), "hors_jeu": len(r["hors"]),
                       "zip": len(mod["entrees"])},
            "limites": mod["fomod"]["limites"]}


# ---------------------------------------------------------------- jeu

class Jeu:
    def __init__(self, root, data):
        self.root = root
        self.ident = hashlib.sha1(os.path.normcase(os.path.abspath(root)).encode()).hexdigest()[:8]
        self.cache_path = os.path.join(data, f"cache_{self.ident}.json")
        self.pose_path = os.path.join(data, f"pose_{self.ident}.json")
        self.cache = {}
        if os.path.isfile(self.cache_path):
            try:
                self.cache = json.load(open(self.cache_path, encoding="utf-8"))
            except ValueError:
                self.cache = {}
        self.dirty = False
        self.vus = None                              # mémo des `stat` le temps d'un plan (build_plan l'ouvre, apply_plan le ferme)

    def path(self, dest):
        return os.path.join(self.root, dest.replace("/", os.sep))

    def st(self, dest):
        """`stat` du fichier du jeu, ou None. Un plan demande chaque fichier plusieurs fois (taille, CRC, lien) : tant que
        `vus` est ouvert, le disque n'est lu qu'une fois par fichier. Fermé (None) dès qu'on écrit le jeu."""
        if self.vus is None:
            try:
                return os.stat(self.path(dest))
            except OSError:
                return None
        k = dest.lower()
        if k not in self.vus:
            try:
                self.vus[k] = os.stat(self.path(dest))
            except OSError:
                self.vus[k] = None
        return self.vus[k]

    def size(self, dest):
        st = self.st(dest)
        return st.st_size if st else None

    def crc(self, dest):
        p = self.path(dest)
        st = self.st(dest)
        if st is None:
            return None
        k = dest.lower()
        c = self.cache.get(k)
        if c and c[0] == st.st_size and c[1] == st.st_mtime_ns:
            return c[2]
        crc = 0
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                crc = zipfile.crc32(b, crc)
        crc &= 0xFFFFFFFF
        self.cache[k] = [st.st_size, st.st_mtime_ns, crc]
        self.dirty = True
        return crc

    def same(self, dest, crc, size):
        return self.size(dest) == size and self.crc(dest) == crc

    def save(self):
        if self.dirty:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            json.dump(self.cache, open(self.cache_path, "w", encoding="utf-8"))

    def load_pose(self):
        if os.path.isfile(self.pose_path):
            return json.load(open(self.pose_path, encoding="utf-8"))
        return {}

    def save_pose(self, pose):
        os.makedirs(os.path.dirname(self.pose_path), exist_ok=True)
        json.dump(pose, open(self.pose_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


class Magasin:
    """Un arbre extrait par mod, sur le disque du jeu : <magasin>\\<section>\\<nom du zip>\\<contenu du zip tel quel>.
    Dérivé des zips (se refait à partir d'eux), jamais une source. Le jeu reçoit des liens physiques vers ces fichiers,
    SAUF les réglages (motifs REGLAGES + ceux de l'utilisateur), copiés : un mod qui réécrit son réglage ne touche pas
    l'arbre, et le réglage survit aux mises à jour.
    Retouche : un fichier de l'arbre qui n'est plus celui du zip (édité à la main pour un essai, ou réécrit par le jeu à
    travers un lien). Elle est gardée, posée telle quelle, signalée, copiée dans les sauvegardes avant qu'un arbre soit refait,
    et annulable (le zip fait foi). Le marqueur de l'arbre note taille et date de chaque fichier pour les repérer vite."""
    MARK = ".red_stack.json"

    def __init__(self, root, reglages=(), sauvegarde=None):
        self.root = os.path.abspath(root)
        self.reglages = [p.lower().replace("\\", "/") for p in list(REGLAGES) + list(reglages)]
        self.sauvegarde = sauvegarde
        self.extraits = self.sauves = 0
        self.marks, self.dirty = {}, set()
        self.rx_reglages = re.compile("|".join(fnmatch.translate(p) for p in self.reglages))   # tous les motifs en un
        self.vus = None                              # mémo des `stat` le temps d'un plan, comme Jeu.vus

    def est_reglage(self, dest):
        return self.rx_reglages.match(dest.lower()) is not None

    def vu(self, path):
        """`stat` d'un chemin, ou None ; mémorisé tant que `vus` est ouvert (lecture d'un plan)"""
        if self.vus is None:
            try:
                return os.stat(path)
            except OSError:
                return None
        if path not in self.vus:
            try:
                self.vus[path] = os.stat(path)
            except OSError:
                self.vus[path] = None
        return self.vus[path]

    def meme(self, src, target, st=None):
        """`src` (arbre) et `target` (jeu) sont-ils le même fichier du disque ? `st` = le `stat` de `target` s'il est déjà lu"""
        a = self.vu(src)
        b = st if st is not None else self.vu(target)
        return bool(a and b) and (a.st_ino, a.st_dev) == (b.st_ino, b.st_dev)

    def liable(self, taille, dest):
        return taille > 0 and not self.est_reglage(dest)

    @staticmethod
    def lp(path):                                    # chemins de plus de 260 caractères
        return path if path.startswith("\\\\?\\") else "\\\\?\\" + os.path.abspath(path)

    def dir_of(self, mod):
        return os.path.join(self.root, mod["section"], mod["nom"][:-4].rstrip(" ."))

    def dir_of_key(self, key):                       # arbre d'un zip connu par sa seule clé (ancienne version, zip renommé)
        return os.path.join(self.root, key.split("/")[0], key.split("/")[-1][:-4].rstrip(" ."))

    def lie_key(self, key, name, target, st=None):
        """le fichier du jeu est-il un lien vers l'arbre de ce zip ? (alors il est à nous, quel que soit son contenu)"""
        return self.meme(self.lp(os.path.join(self.dir_of_key(key), *(p.rstrip(" .") or "_" for p in name.split("/")))), target, st)

    def renomme(self, old_key, mod):
        """zip renommé ou déplacé sans changer de contenu : l'arbre suit, les liens du jeu restent valables"""
        old, new = self.dir_of_key(old_key), self.dir_of(mod)
        if os.path.isdir(self.lp(old)) and not os.path.exists(self.lp(new)):
            os.makedirs(self.lp(os.path.dirname(new)), exist_ok=True)
            os.rename(self.lp(old), self.lp(new))
            return True
        return False

    def src(self, mod, name):
        # sous \\?\ Windows ne nettoie plus rien : un dossier fini par un point ou une espace serait créé tel quel
        return self.lp(os.path.join(self.dir_of(mod), *(p.rstrip(" .") or "_" for p in name.split("/"))))

    @staticmethod
    def stat(path):
        try:
            st = os.stat(path)
            return [st.st_size, st.st_mtime_ns]
        except OSError:
            return None

    def mark(self, mod):
        d = self.dir_of(mod)
        if d not in self.marks:
            try:
                m = json.load(open(self.lp(os.path.join(d, self.MARK)), encoding="utf-8"))
            except (OSError, ValueError):
                m = None
            if isinstance(m, list):                  # marqueur du premier jour (signature seule) : arbre tenu pour intact
                m = {"sig": m, "retouches": {},
                     "fichiers": {e["n"]: self.stat(self.src(mod, e["n"])) for e in mod["entrees"]}}
                self.dirty.add(d)
            self.marks[d] = m
        return self.marks[d]

    def flush(self):
        for d in self.dirty:
            if self.marks.get(d):
                json.dump(self.marks[d], open(self.lp(os.path.join(d, self.MARK)), "w", encoding="utf-8"))
        self.dirty.clear()

    def a_jour(self, mod):
        m = self.mark(mod)
        return bool(m) and m["sig"] == mod["sig"]

    def effectif(self, mod, e):
        """(crc, taille, retouché) de ce que l'arbre porte pour cette entrée ; le zip si l'arbre est intact ou absent."""
        m = self.mark(mod)
        p = self.src(mod, e["n"])
        v = self.vu(p)
        st = [v.st_size, v.st_mtime_ns] if v else None
        if st is None or st == m["fichiers"].get(e["n"]):
            return e["c"], e["s"], False
        r = m["retouches"].get(e["n"])
        if not r or r[:2] != st:
            crc = 0
            with open(p, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    crc = zipfile.crc32(b, crc)
            crc &= 0xFFFFFFFF
            self.dirty.add(self.dir_of(mod))
            if crc == e["c"] and st[0] == e["s"]:    # réécrit à l'identique : pas une retouche
                m["fichiers"][e["n"]] = st
                m["retouches"].pop(e["n"], None)
                return e["c"], e["s"], False
            r = m["retouches"][e["n"]] = st + [crc]
        return r[2], r[0], True

    def sauve_retouches(self, d):
        """avant de défaire un arbre : copie dans les sauvegardes ce qui n'y est plus le fichier du zip"""
        try:
            m = json.load(open(self.lp(os.path.join(d, self.MARK)), encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        n = 0
        for name, st in (m.get("fichiers") or {}).items() if isinstance(m, dict) else ():
            p = self.lp(os.path.join(d, *(x.rstrip(" .") or "_" for x in name.split("/"))))
            now = self.stat(p)
            if now and now != st and self.sauvegarde:
                t = self.lp(os.path.join(self.sauvegarde, "magasin", os.path.relpath(d, self.root), name.replace("/", os.sep)))
                os.makedirs(os.path.dirname(t), exist_ok=True)
                shutil.copy2(p, t)
                n += 1
        self.sauves += n
        return n

    def restaure(self, mod, zf, name):
        """remet dans l'arbre le fichier du zip ; l'ancien nom est défait d'abord, un lien du jeu garde donc son contenu"""
        t = self.src(mod, name)
        os.makedirs(os.path.dirname(t), exist_ok=True)
        drop(t)
        with zf.open(name) as s, open(t, "wb") as o:
            shutil.copyfileobj(s, o, 1 << 20)
        m = self.mark(mod)
        m["fichiers"][name] = self.stat(t)
        m["retouches"].pop(name, None)
        self.dirty.add(self.dir_of(mod))

    def ensure(self, mod):
        if self.a_jour(mod):
            return
        d = self.dir_of(mod)
        self.sauve_retouches(d)
        shutil.rmtree(self.lp(d), ignore_errors=True)
        os.makedirs(self.lp(d), exist_ok=True)
        stats = {}
        with zipfile.ZipFile(mod["zip"]) as zf:      # l'extraction lit chaque entrée jusqu'au bout : CRC vérifié
            for i in zf.infolist():
                if i.is_dir():
                    continue
                n = i.filename.replace("\\", "/").lstrip("/")
                t = self.src(mod, n)
                os.makedirs(os.path.dirname(t), exist_ok=True)
                with zf.open(i) as s, open(t, "wb") as o:
                    shutil.copyfileobj(s, o, 1 << 20)
                stats[n] = self.stat(t)
        self.marks[d] = {"sig": mod["sig"], "fichiers": stats, "retouches": {}}
        self.dirty.add(d)
        self.extraits += 1

    def lie(self, mod, name, target, st=None):
        return self.meme(self.src(mod, name), target, st)


def pese(d):
    """(fichiers, octets) d'un dossier, marqueur de l'arbre exclu ; la liste du dossier donne les tailles sans `stat`"""
    n = o = 0
    pile = [d]
    while pile:
        try:
            it = os.scandir(pile.pop())
        except OSError:
            continue
        with it:
            for e in it:
                if e.is_dir(follow_symlinks=False):
                    pile.append(e.path)
                elif e.name != Magasin.MARK:
                    n += 1
                    o += e.stat().st_size
    return n, o


def arbres_du_magasin(store):
    """[(pile, dossier, chemin)] de chaque arbre présent dans le magasin"""
    out = []
    for s in sorted(os.listdir(store.root)) if os.path.isdir(store.root) else []:
        ps = os.path.join(store.root, s)
        if os.path.isdir(ps):
            out += [(s, d, os.path.join(ps, d)) for d in sorted(os.listdir(ps))]
    return out


def arbres_sans_mod(store, index, prof):
    """arbres du magasin qu'aucun mod actif du profil ne tient : mod coupé, parqué, ancienne version, zip disparu"""
    keep = {os.path.normcase(store.dir_of(index[k])) for k, mp in prof["mods"].items()
            if k in index and not index[k]["lieu"] and selected(index[k], mp)}
    return [p for _, _, p in arbres_du_magasin(store) if os.path.normcase(p) not in keep]


# Sauvegarde des réglages : copie datée des fichiers de réglages du jeu (motifs REGLAGES + ceux de l'utilisateur), qu'un
# mod les ait livrés ou que le jeu les ait écrits. Jamais pris : les caches (recalculés au lancement), le socle du jeu,
# les journaux, les fichiers vides, le territoire d'un installateur tiers. Un dossier par sauvegarde dans le dossier des
# sauvegardes, avec son manifeste (taille et CRC de chaque copie).
SAUVE_MARK = "red_stack_reglages.json"
SAUVE_PREFIXE = "_reglages_"
SAUVE_EXCLUS = ["r6/cache/*", "engine/config/base/*", "engine/config/platform/*", "archive/pc/content/*", "archive/pc/ep1/*",
                "*.log", "*.bak", "*.tmp"]


def reglages_du_jeu(jeu, store):
    exclu = lambda d: any(fnmatch.fnmatchcase(d, p) for p in SAUVE_EXCLUS)
    out = []
    for top in ROOTS:
        for base, dirs, files in os.walk(os.path.join(jeu.root, top)):
            rel = os.path.relpath(base, jeu.root).replace(os.sep, "/")
            dirs[:] = [x for x in dirs if not exclu(f"{rel}/{x}/_".lower())]
            for f in files:
                dest = rel + "/" + f
                if store.est_reglage(dest) and not exclu(dest.lower()) and not (HORS and est_hors(dest)) and jeu.size(dest):
                    out.append(dest)
    return sorted(out, key=str.lower)


def crc_fichier(path):
    crc = 0
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            crc = zipfile.crc32(b, crc)
    return crc & 0xFFFFFFFF


def sauvegardes_reglages(racine):
    """sauvegardes de réglages présentes, la plus récente d'abord"""
    rows = []
    for d in sorted(os.listdir(racine), reverse=True) if os.path.isdir(racine) else []:
        mark = os.path.join(racine, d, SAUVE_MARK)
        if d.startswith(SAUVE_PREFIXE) and os.path.isfile(mark):
            try:
                m = json.load(open(mark, encoding="utf-8"))
            except ValueError:
                continue
            rows.append({"nom": d, "cree": m.get("cree", ""), "fichiers": len(m.get("fichiers", {})),
                         "octets": sum(v[0] for v in m.get("fichiers", {}).values()), "chemin": os.path.join(racine, d),
                         "jeu_lance": bool(m.get("jeu_lance"))})
    return rows


def game_running():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Cyberpunk2077.exe", "/NH"], capture_output=True)
    return b"cyberpunk2077.exe" in r.stdout.lower()      # octets : la console répond dans sa page de codes, pas en UTF-8


# ---------------------------------------------------------------- profil

def profil_path(data, nom):
    return os.path.join(data, "profils", nom + ".json")


def load_profil(data, nom, index, pose=None, auto=False):
    """`auto` (config.json `nouveaux_actifs`) : un zip arrivé à la racine d'une pile est coché d'office"""
    p = profil_path(data, nom)
    if not os.path.isfile(p):
        sys.exit(T("Profil introuvable : {0} (le créer par `adopte --profil {1}`)", p, nom))
    prof = json.load(open(p, encoding="utf-8"))
    notes, changed = [], False
    prof.setdefault("priorites", [])
    for key, mp in prof["mods"].items():             # empreinte du contenu : retrouve un zip renommé ou déplacé
        if key in index and mp.get("empreinte") != index[key]["empreinte"]:
            mp["empreinte"] = index[key]["empreinte"]
            changed = True
    for key, mp in prof["mods"].items():             # parqué depuis l'outil puis remonté : il revient comme un nouveau
        if mp.get("parque") and key in index and not index[key]["lieu"]:
            del mp["parque"]
            if auto:
                mp["actif"] = True
                mp.pop("coupe", None)
            changed = True
    for key in [k for k in prof["mods"] if k not in index]:
        if prof["mods"][key].get("parque"):          # parqué depuis l'outil : gardé au profil avec ses choix, sans bruit
            continue
        sec, name = key.split("/")[0], key.split("/")[-1]
        free = {k: m for k, m in index.items() if not m["lieu"] and k not in prof["mods"]}
        # 1. même contenu sous un autre nom ou dans une autre pile : renommage, rien à refaire dans le jeu
        cands, kind = [k for k, m in free.items() if m["empreinte"] == prof["mods"][key].get("empreinte")], "renommé"
        if len(cands) != 1:
            # 2. même mod (radical et modId) dans la même pile, autre contenu : nouvelle version
            cands, kind = [k for k, m in free.items() if m["section"] == sec and ident(m["nom"]) == ident(name)], "mise à jour"
        if len(cands) != 1 and pose:
            # 3. autre nom ET autre contenu (version EDITED, zip refait) : le zip libre qui livre au moins la moitié des
            #    fichiers que l'ancien avait posés, s'il est seul dans ce cas
            mine = {dl for dl, r in pose.items() if r["zip"] == key}
            score = {k: len(mine & {e["d"].lower() for e in m["entrees"] if e["d"]}) for k, m in free.items()} if mine else {}
            best = sorted(score, key=score.get, reverse=True)[:2]
            if best and score[best[0]] * 2 >= len(mine) and (len(best) == 1 or score[best[1]] < score[best[0]]):
                cands, kind = [best[0]], "remplacé"
        if len(cands) == 1:
            mp = prof["mods"][cands[0]] = prof["mods"].pop(key)
            mp["empreinte"] = index[cands[0]]["empreinte"]
            prof["priorites"] = [[cands[0] if x == key else x for x in pair] for pair in prof["priorites"]]
            prof["priorites_fichiers"] = {d: cands[0] if z == key else z for d, z in prof.get("priorites_fichiers", {}).items()}
            notes.append((kind, key, cands[0]))
            changed = True
        else:
            notes.append(("zip disparu", key, ", ".join(cands) or T("aucun remplaçant")))
    if auto:
        for key, m in index.items():
            if not m["lieu"] and key not in prof["mods"]:
                prof["mods"][key] = {"actif": True, "empreinte": m["empreinte"], "auto": True}
                notes.append(("nouveau, coché d'office", key, key))
                changed = True
    if changed:
        save_profil(data, nom, prof)
    return prof, notes


def save_profil(data, nom, prof):
    p = profil_path(data, nom)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(prof, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def selected(mod, mp):
    """entrées prises d'un zip selon le profil : [(entrée, destination)]"""
    if not mp or not mp.get("actif"):
        return []
    ren = mp.get("renomme", {})
    if fomod_actif(mod, mp):                         # posé par son installateur : lui seul dit quoi va où
        par = {e["n"]: e for e in mod["entrees"]}
        return [(par[n], ren.get(n, d)) for n, d in fomod_resolu(mod["fomod"], mp.get("fomod"))["fichiers"] if n in par]
    sel = mp.get("sel")
    if sel is None:
        sel = {"": "*"}
    out = []
    for e in mod["entrees"]:
        if e["o"] is None:
            continue
        s = sel.get(e["o"])
        if s == "*" or (isinstance(s, list) and e["n"] in s):
            out.append((e, ren.get(e["n"], e["d"])))
    return out


def find_mod(index, prof, text, partout=False):
    """clé du zip actif que `text` désigne ; `partout` : une clé entière désigne aussi un zip parqué ou un arrivage (à lire seulement)"""
    t = text.lower()
    if partout and text in index:
        return text
    hits = [k for k in index if not index[k]["lieu"] and t in k.lower()]
    exact = [k for k in hits if k.lower() == t or index[k]["nom"].lower() in (t, t + ".zip")]
    hits = exact or hits
    if len(hits) != 1:
        sys.exit(N(len(hits), "« {0} » désigne {n} zip actif : {1}", "« {0} » désigne {n} zips actifs : {1}", text, hits[:8]))
    return hits[0]


# ---------------------------------------------------------------- plan

def build_plan(index, prof, jeu, force=False, store=None, filtre=None):
    """`filtre(destination)` borne le plan à une partie du jeu (lecture seule : ne jamais appliquer un plan filtré)"""
    pose = jeu.load_pose()
    jeu.vus = {}                                     # un `stat` par fichier pour tout le plan, au lieu de cinq ou six
    if store is not None:
        store.vus = {}
    beats = {(w, l) for w, l in prof.get("priorites", [])}
    wanted = collections.defaultdict(list)  # destination minuscule -> [(clé, entrée, destination)]
    tiers = set()
    for key, mp in prof["mods"].items():
        if key in index and not index[key]["lieu"]:
            tree = store is not None and store.a_jour(index[key])
            for e, dest in selected(index[key], mp):
                if filtre and not filtre(dest):
                    continue
                if HORS and est_hors(dest):
                    if MIENS.get(dest.lower(), key) != key:
                        continue                     # revendiqué pour un autre mod : pas à celui-ci
                    if a_tiers(jeu, pose, dest):     # fichier de l'installateur tiers : ni voulu, ni touché
                        tiers.add(dest.lower())
                        continue
                    e = dict(e, h=True, p=dest.lower() in MIENS)   # absent, ajouté par nous ou revendiqué : au mod, en copie
                if tree:                             # ce que l'arbre porte fait foi pour la pose : une retouche se pose
                    c, s, r = store.effectif(index[key], e)
                    if r:
                        e = dict(e, c=c, s=s, r=True)
                wanted[dest.lower()].append((key, e, dest))
    plan = {"pose": [], "remplace": [], "retire": [], "garde_modifie": [], "inconnu": [], "conflit": [], "ok": 0,
            "oublie": [], "lie": [], "delie": [], "retouche": [], "tranche": [], "tiers": len(tiers), "pris": [], "rendu": []}
    final = {}
    for dl, cands in wanted.items():
        crcs = {(e["c"], e["s"]) for _, e, _ in cands}
        if len(crcs) > 1:
            seul = prof.get("priorites_fichiers", {}).get(dl)
            seul = seul if any(c[0] == seul for c in cands) else None
            win = [c for c in cands if c[0] == seul] if seul else \
                [c for c in cands if not any((o[0], c[0]) in beats for o in cands if o[1]["c"] != c[1]["c"])]
            if len({(e["c"], e["s"]) for _, e, _ in win}) != 1:
                held = [c for c in cands if jeu.same(c[2], c[1]["c"], c[1]["s"])]
                plan["conflit"].append({"dest": cands[0][2], "zips": sorted({c[0] for c in cands}),
                                        "dans_le_jeu": held[0][0] if held else None})
                if held:
                    final[dl] = held[0]
                continue
            # conflit déjà tranché par une priorité : gardé visible, pour pouvoir revenir dessus
            plan["tranche"].append({"dest": cands[0][2], "zip": win[0][0], "par_fichier": bool(seul),
                                    "perdants": sorted({c[0] for c in cands if c[1]["c"] != win[0][1]["c"]})})
            cands = win
        final[dl] = cands[0]
    for dl, (key, e, dest) in final.items():
        row = {"dest": dest, "zip": key, "entree": e["n"], "crc": e["c"], "taille": e["s"]}
        if e.get("h"):
            row["ajout"] = True
        if e.get("p"):
            row["pris"] = True
        size = jeu.size(dest)
        reg = pose.get(dl)
        a_prendre = bool(row.get("pris")) and not (reg and reg.get("pris") and reg["zip"] == key)
        if e.get("r"):
            plan["retouche"].append(row)
        liable = store is not None and store.liable(e["s"], dest) and not e.get("h")
        if size is None:
            plan["pose"].append(row)
        elif store and not liable and store.lie(index[key], e["n"], jeu.path(dest), jeu.st(dest)):
            # réglage (motif ajouté après coup) encore lié à l'arbre : le jeu garde son contenu en copie, l'arbre
            # reprend le fichier du zip
            orig = next(x for x in index[key]["entrees"] if x["n"] == e["n"])
            plan["delie"].append(dict(row, crc=orig["c"], taille=orig["s"]))
        elif jeu.same(dest, e["c"], e["s"]):
            plan["ok"] += 1
            if (not reg or reg["crc"] != e["c"] or reg["zip"] != key or bool(reg.get("ajout")) != bool(row.get("ajout"))
                    or bool(reg.get("pris")) != bool(row.get("pris"))):
                plan["oublie"].append(("inscrit", dl, row))
                if a_prendre:
                    plan["pris"].append(row)        # revendiqué : pris au registre, le fichier du jeu ne change pas
            if liable and not store.lie(index[key], e["n"], jeu.path(dest), jeu.st(dest)):
                # bon contenu, mais copie, ou lien vers l'arbre d'un mod qui ne le tient plus : à lier à l'arbre de celui-ci
                plan["lie"].append(dict(row, ancien=reg["zip"]) if reg and reg["zip"] != key else row)
        elif a_prendre and not reg:
            # revendiqué, mais le jeu porte un autre contenu que le zip : pris au registre comme « modifié en jeu », gardé
            plan["oublie"].append(("inscrit", dl, row))
            plan["pris"].append(dict(row, raison=T("autre contenu que le zip : gardé tel quel")))
        elif reg and jeu.same(dest, reg["crc"], reg["taille"]):
            plan["remplace"].append(dict(row, ancien=reg["zip"]))
        elif reg and reg["crc"] == e["c"] and reg["taille"] == e["s"]:
            plan["garde_modifie"].append(dict(row, raison=T("modifié en jeu")))
        elif reg:
            (plan["remplace"] if force is True else plan["garde_modifie"]).append(
                dict(row, ancien=reg["zip"], sauve=True, raison=T("modifié en jeu, nouvelle version en attente")))
        else:
            # `force` : tout (--force), ou les seules destinations désignées une à une (--remplace)
            voulu = force is True or (bool(force) and dl in force)
            (plan["remplace"] if voulu else plan["inconnu"]).append(
                dict(row, sauve=True, raison=T("fichier présent, pas posé par l'outil"), **({"force": True} if voulu and force is not True else {})))
    for dl, reg in pose.items():
        if dl in final or (filtre and not filtre(reg["dest"])):
            continue
        if jeu.size(reg["dest"]) is None:
            plan["oublie"].append(("efface", dl, None))
        elif HORS and est_hors(reg["dest"]) and (not reg.get("ajout") or (reg.get("pris") and dl not in MIENS)):
            # reconnu à l'adoption avant que le motif existe, ou revendiqué puis rendu (case décochée) : à l'installateur.
            # Lié à un arbre, il est d'abord délié (le jeu garde une copie à lui) ; dans tous les cas il sort du registre
            # et reste dans le jeu.
            if store and reg["zip"] in index and store.lie_key(reg["zip"], reg["entree"], jeu.path(reg["dest"]), jeu.st(reg["dest"])):
                plan["delie"].append(dict(reg, tiers=True))
            else:
                plan["oublie"].append(("efface", dl, None))
                if reg.get("pris"):
                    plan["rendu"].append(dict(reg))
        elif jeu.same(reg["dest"], reg["crc"], reg["taille"]) or (
                store and store.lie_key(reg["zip"], reg["entree"], jeu.path(reg["dest"]), jeu.st(reg["dest"]))):
            plan["retire"].append(dict(reg))        # celui du registre, ou un lien vers l'arbre (retouche : elle y reste)
        else:
            plan["garde_modifie"].append(dict(reg, raison=T("plus voulu mais modifié en jeu : gardé"), orphelin=True))
    plan["final"] = final                            # destination -> (zip, entrée, destination) : qui tient chaque fichier
    plan["coupes"] = [] if filtre else resume_coupes(index, prof, plan, pose)
    if store:
        store.flush()
    return plan, pose


def resume_coupes(index, prof, plan, pose):
    """Une ligne par mod coupé dont le jeu porte encore la trace, ou coupé depuis le dernier « Appliquer » (`a_dire`) :
    ce qui sort du jeu, ce qu'un autre mod actif reprend à l'identique, ce qu'un autre mod tient avec un autre contenu."""
    tenus = collections.Counter(r["zip"] for r in pose.values())
    retires = collections.Counter(r["zip"] for r in plan["retire"])
    gardes = collections.Counter(r["zip"] for r in plan["garde_modifie"] if r.get("orphelin"))
    rendus = collections.Counter(r["zip"] for r in plan["delie"] if r.get("tiers"))
    rows = []
    for key, mp in prof["mods"].items():
        if mp.get("actif") or key not in index or index[key]["lieu"] or not (mp.get("a_dire") or tenus.get(key)):
            continue
        repris, tenu_par = collections.Counter(), collections.Counter()
        for e, dest in selected(index[key], dict(mp, actif=True)):
            f = plan["final"].get(dest.lower())
            if f and f[0] != key:
                (repris if (f[1]["c"], f[1]["s"]) == (e["c"], e["s"]) else tenu_par)[f[0]] += 1
        rows.append({"zip": key, "au_registre": tenus.get(key, 0), "retire": retires.get(key, 0), "garde": gardes.get(key, 0),
                     "rendu": rendus.get(key, 0),
                     "repris": [{"zip": z, "n": n} for z, n in repris.most_common()],
                     "tenu_par": [{"zip": z, "n": n} for z, n in tenu_par.most_common()]})
    return rows


def drop(target):
    """retire un fichier du jeu, lecture seule comprise ; un lien physique ne perd que ce nom-là, pas l'arbre du magasin"""
    if os.path.lexists(target):
        try:
            os.remove(target)
        except PermissionError:
            os.chmod(target, stat.S_IWRITE)
            os.remove(target)


def write_file(zf, name, target):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    drop(target)                                     # jamais écrire À TRAVERS un lien : ce serait écrire dans le magasin
    with zf.open(name) as s, open(target, "wb") as d:
        shutil.copyfileobj(s, d, 1 << 20)


def prune(path, root):
    d = os.path.dirname(path)
    while os.path.normcase(d) != os.path.normcase(root) and os.path.isdir(d) and not os.listdir(d):
        try:
            os.rmdir(d)
        except OSError:
            return
        d = os.path.dirname(d)


def apply_plan(plan, pose, index, jeu, stamp, log, store=None):
    jeu.vus = None                                   # on écrit : plus aucun `stat` mémorisé
    if store:
        store.vus = None
    for row in plan["retire"]:
        p = jeu.path(row["dest"])
        drop(p)
        prune(p, jeu.root)
        pose.pop(row["dest"].lower(), None)
        log(f"  x RETIRE    {row['dest']}  ({row['zip']})")
    by_zip = collections.defaultdict(list)
    for kind in ("delie", "pose", "remplace", "lie"):
        for row in plan[kind]:
            by_zip[row["zip"]].append((kind, row))
    bad, word = [], {"pose": "+ POSE     ", "remplace": "~ REMPLACE ", "lie": "= LIE      ", "delie": "/ DELIE    "}
    for key, rows in by_zip.items():
        mod = index[key]
        if store:
            store.ensure(mod)
        with zipfile.ZipFile(mod["zip"]) as zf:
            for kind, row in rows:
                target = jeu.path(row["dest"])
                if kind == "delie":                  # copie indépendante d'abord, puis l'arbre reprend le fichier du zip
                    tmp = target + ".red_stack_tmp"
                    shutil.copyfile(target, tmp)
                    drop(target)
                    os.replace(tmp, target)
                    store.restaure(mod, zf, row["entree"])
                    if row.get("tiers"):             # rendu à l'installateur tiers : plus au registre
                        pose.pop(row["dest"].lower(), None)
                    else:
                        pose[row["dest"].lower()] = reg_row(row)
                    log(f"  {word[kind]}{row['dest']}  ({key})" + (T("  [hors Red Stack]") if row.get("tiers") else ""))
                    continue
                if store and not os.path.isfile(store.src(mod, row["entree"])):
                    store.restaure(mod, zf, row["entree"])   # fichier effacé de l'arbre à la main : repris du zip
                if row.get("sauve") and os.path.isfile(target):
                    b = os.path.join(stamp, row["dest"].replace("/", os.sep))
                    os.makedirs(os.path.dirname(b), exist_ok=True)
                    shutil.copy2(target, b)
                if store:
                    src = store.src(mod, row["entree"])
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    drop(target)
                    linked = False
                    if store.liable(row["taille"], row["dest"]) and not row.get("ajout"):
                        try:
                            os.link(src, target)
                            linked = True
                        except OSError:              # magasin sur un autre disque que le jeu : copie
                            plan.setdefault("copies_faute_de_lien", []).append(row["dest"])
                    if not linked:
                        shutil.copyfile(src, target)
                    st = os.stat(target)             # contenu = arbre du magasin, vérifié à l'extraction
                    if st.st_size != row["taille"]:
                        bad.append(row["dest"])
                    jeu.cache[row["dest"].lower()] = [st.st_size, st.st_mtime_ns, row["crc"]]
                    jeu.dirty = True
                else:
                    write_file(zf, row["entree"], target)
                    if not jeu.same(row["dest"], row["crc"], row["taille"]):
                        bad.append(row["dest"])
                pose[row["dest"].lower()] = reg_row(row)
                log(f"  {word[kind]}{row['dest']}  ({key})")
    for what, dl, row in plan["oublie"]:
        if what == "efface":
            pose.pop(dl, None)
        else:
            pose[dl] = reg_row(row)
    for row in plan["garde_modifie"]:
        if row.get("orphelin"):
            pose.pop(row["dest"].lower(), None)
    if store:
        store.flush()
    jeu.save_pose(pose)
    jeu.save()
    return bad, stamp if os.path.isdir(stamp) else None


# ---------------------------------------------------------------- adoption

def adopt(index, jeu):
    """Déduit du jeu : profil (ce qui est pris de chaque zip actif), priorités observées, registre de pose."""
    active = {k: m for k, m in index.items() if not m["lieu"]}
    ident_at = collections.defaultdict(list)  # destination -> [(clé, entrée)] identiques au jeu
    state = {}
    for key, mod in active.items():
        for e in mod["entrees"]:
            if e["o"] is None:
                continue
            size = jeu.size(e["d"])
            if size is not None and HORS and est_hors(e["d"]):
                continue                             # fichier d'un installateur tiers : pas au mod, même identique
            st = "absent" if size is None else ("identique" if jeu.same(e["d"], e["c"], e["s"]) else "different")
            state[(key, e["n"])] = st
            if st == "identique":
                ident_at[e["d"].lower()].append((key, e))
    prof = {"mods": {}, "priorites": []}
    pose, pairs, rapport = {}, set(), {}
    for key, mod in active.items():
        sel, counts = {}, collections.Counter()
        for opt in options_of(mod):
            ents = [e for e in mod["entrees"] if e["o"] == opt and (key, e["n"]) in state]
            if not ents:
                continue
            same = [e for e in ents if state[(key, e["n"])] == "identique"]
            took = list(same)
            if same:
                for e in ents:
                    if state[(key, e["n"])] != "different":
                        continue
                    others = [k for k, _ in ident_at.get(e["d"].lower(), []) if k != key]
                    if others and opt == "" and len(same) * 2 >= len(ents):
                        took.append(e)                      # posé puis écrasé par un autre mod
                        pairs.update((o, key) for o in others)
                        counts["écrasé"] += 1
                    elif not others:
                        took.append(e)                      # livré puis modifié en jeu (réglage)
                        counts["modifié"] += 1
                        pose[e["d"].lower()] = {"dest": e["d"], "zip": key, "entree": e["n"], "crc": e["c"], "taille": e["s"]}
            for e in same:
                pose.setdefault(e["d"].lower(), {"dest": e["d"], "zip": key, "entree": e["n"], "crc": e["c"], "taille": e["s"]})
            counts["identique"] += len(same)
            counts["absent"] += sum(1 for e in ents if state[(key, e["n"])] == "absent")
            if took:
                sel[opt] = "*" if len(took) == len(ents) else sorted(e["n"] for e in took)
        n = sum(1 for e in mod["entrees"] if (key, e["n"]) in state)
        full = bool(sel) and all(v == "*" for v in sel.values()) and set(sel) == {e["o"] for e in mod["entrees"] if (key, e["n"]) in state}
        rapport[key] = {"etat": "non posable" if not n else "entier" if full else "partiel" if sel else "absent",
                        "posables": n, **counts}
        mp = {"actif": bool(sel)}
        if sel and (sel != {"": "*"} or mod.get("fomod")):   # FOMOD déjà dans le jeu : ce qui y est fait foi, pas ses défauts
            mp["sel"] = sel
        prof["mods"][key] = mp
    prof["priorites"] = sorted([w, l] for w, l in pairs if (l, w) not in pairs)
    return prof, pose, rapport


# ---------------------------------------------------------------- conflits d'archives

# Le jeu charge les `.archive` de `archive/pc/mod` dans l'ordre de leurs noms comparés octet par octet (`!` `#`, chiffres,
# MAJUSCULES, `_`, minuscules), ou dans celui de `archive/pc/mod/modlist.txt` s'il existe (le reste ensuite, par nom) ; puis
# les archives REDmod (`mods/<dossier>/archives`), par dossier. Une ressource (chemin du jeu haché en FNV-1a 64) livrée par
# plusieurs archives est prise dans la PREMIÈRE chargée : une archive ne gagne que sur celles chargées APRÈS elle et perd
# contre celles d'avant. Deux copies de même SHA-1 (index RDAR) ne sont pas un conflit : comptées à part, « identiques ».
# Les noms des ressources viennent du bloc de chemins que WolvenKit écrit dans l'archive, sinon de la liste de CET
# (`usedhashes.kark`) ; les deux se lisent avec le décodeur Oodle du jeu. Sans nom, la ressource est montrée par son empreinte.
ARCH_DIR = "archive/pc/mod/"
OODLE_DLL = "bin/x64/oo2ext_7_win64.dll"
KARK = "bin/x64/plugins/cyber_engine_tweaks/tweakdb/usedhashes.kark"
SHA_VIDES = ("0" * 40, "da39a3ee5e6b4b0d3255bfef95601890afd80709")
FNV_M = 0xFFFFFFFFFFFFFFFF


def fnv64(b):
    """empreinte d'un chemin de ressource déjà normalisé (octets, minuscules, barres obliques inverses)"""
    h = 0xcbf29ce484222325
    for x in b:
        h = ((h ^ x) * 0x100000001b3) & FNV_M
    return h


class Oodle:
    """décodeur du jeu, pour les blocs de chemins compressés ; absent (banc, autre système), ils sont passés"""

    def __init__(self, jeu_root):
        self.fn = None
        p = os.path.join(jeu_root, OODLE_DLL.replace("/", os.sep))
        if os.path.isfile(p):
            try:
                import ctypes
                f = ctypes.WinDLL(p).OodleLZ_Decompress
                f.restype = ctypes.c_int64
                f.argtypes = [ctypes.c_char_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_int64, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                              ctypes.c_int64, ctypes.c_int]
                self.fn, self.ct = f, ctypes
            except (OSError, AttributeError):
                self.fn = None

    def decode(self, data, taille):
        if not self.fn or not 0 < taille <= 1 << 28:
            return b""
        out = self.ct.create_string_buffer(taille)
        n = self.fn(data, len(data), out, taille, 1, 0, 0, None, 0, None, None, None, 0, 3)
        return out.raw[:n] if n > 0 else b""


def rdar_index(read_at):
    """[(empreinte, sha1 hex)] de l'index d'une archive RDAR, ou None si ce n'en est pas une"""
    head = read_at(0, 44)
    if len(head) < 44 or head[:4] != b"RDAR":
        return None
    pos, size = struct.unpack_from("<QI", head, 8)
    idx = read_at(pos, size) if 28 <= size <= 1 << 28 else b""
    if len(idx) < 28:
        return None
    count = struct.unpack_from("<I", idx, 16)[0]
    if 28 + 56 * count > len(idx):
        return None
    return [(struct.unpack_from("<Q", idx, o)[0], idx[o + 36:o + 56].hex()) for o in range(28, 28 + 56 * count, 56)]


def rdar_noms(read_at, oodle):
    """chemins de ressources écrits dans l'archive (bloc LXRS de WolvenKit), en octets ; [] s'il n'y en a pas"""
    head = read_at(0, 44)
    custom = struct.unpack_from("<I", head, 40)[0] if len(head) >= 44 and head[:4] == b"RDAR" else 0
    if custom < 20:
        return []
    magic, ver, raw, comp, _ = struct.unpack("<IIIII", read_at(0xAC, 20))
    if magic != 0x4C585253 or ver != 1 or comp + 20 > custom or raw > 1 << 26:
        return []
    data = read_at(0xAC + 20, comp)
    if raw != comp:
        data = oodle.decode(data, raw)
    return [p for p in data.split(b"\0") if p]


def lit_archive(prov, fn):
    """fn(read_at) sur le fichier de l'archive : celui du disque (jeu ou arbre), sinon l'entrée du zip"""
    if prov["fichier"]:
        with open(prov["fichier"], "rb") as f:
            def r(p, n):
                f.seek(p)
                return f.read(n)
            return fn(r)
    with zipfile.ZipFile(prov["zip_path"]) as zf, zf.open(prov["entree"]) as f:
        def r(p, n):                                 # entrée compressée : la lecture avance en décompressant
            f.seek(p)
            return f.read(n)
        return fn(r)


ML = ARCH_DIR + "modlist.txt"
octets = lambda t: t.encode("utf-8", "surrogateescape")


def modlist_du_jeu(jeu):
    """lignes de `modlist.txt` dans le jeu, ou None s'il n'y est pas"""
    try:
        with open(jeu.path(ML), encoding="utf-8", errors="replace") as f:
            return [l.strip() for l in f if l.strip()]
    except OSError:
        return None


def modlist_plan(prof, jeu, noms):
    """ce qu'« Appliquer » ferait de `modlist.txt`. Profil sans clé `modlist` : le fichier n'est pas tenu par l'outil, il
    est lu et laissé tel quel. Liste : la tête de l'ordre voulu ; liste vide : pas de fichier (ordre par les noms).
    Le fichier écrit cite TOUTES les archives (`noms`), la tête voulue puis le reste par nom : ce que le jeu fait d'une
    archive absente de la liste n'est écrit nulle part, on ne s'appuie pas dessus."""
    voulu = prof.get("modlist")
    if voulu is None:
        return []
    voulu = ordonne(noms, voulu)[0] if voulu else []
    if voulu == (modlist_du_jeu(jeu) or []):
        return []
    return [{"dest": ML, "zip": "", "crc": zlib.crc32("\n".join(voulu).encode("utf-8")),
             "action": "ecrire" if voulu else "retirer", "lignes": voulu}]


def ordonne(noms, lignes):
    """ordre de chargement de ces noms d'archives : ceux que `lignes` (modlist.txt) cite, dans son ordre, puis le reste par
    octets ; rend (ordre, la liste a-t-elle servi)"""
    par_nom = {n.lower(): n for n in noms}
    tete = list(dict.fromkeys(l.strip().lower() for l in lignes if l.strip().lower() in par_nom))
    vus = set(tete)
    return [par_nom[l] for l in tete] + sorted((n for n in noms if n.lower() not in vus), key=octets), bool(tete)


def nom_pour_ordre(nom, cible, avant, pris):
    """nom d'archive qui se charge avant (ou après) `cible` par l'ordre des octets, au plus près d'elle :
    son préfixe de signes repris, puis des `!` pour passer avant ou un `z…_` pour passer après ; `pris` = noms déjà dans le jeu (minuscules)"""
    if (octets(nom) < octets(cible)) if avant else (octets(nom) > octets(cible)):
        return nom
    # au plus près de la cible : son préfixe de signes repris (`##_`), pour ne pas passer aussi devant tout le reste du jeu
    tete, nu = cible[:len(cible) - len(cible.lstrip("!#_"))], nom.lstrip("!#_") or nom
    cands = [tete + nu] + ([tete + "!" * n + nu for n in range(1, 40)] + ["!" * n + nu for n in range(1, 40)] if avant
                           else [tete + "z" * n + "_" + nu for n in range(1, 40)])
    for cand in cands:
        if ((octets(cand) < octets(cible)) if avant else (octets(cand) > octets(cible))) and cand.lower() not in pris:
            return cand
    return None


def archives_du_profil(index, plan, pose, jeu, store, modlist=None):
    """les archives que le jeu chargerait pour ce profil, dans l'ordre de chargement, et la source de l'ordre ;
    `modlist` : les lignes que le profil veut dans `modlist.txt` (None : le fichier du jeu fait foi)"""
    provs, vus = [], set()

    def genre(dest):
        dl = dest.lower()
        if dl.startswith(ARCH_DIR) and "/" not in dl[len(ARCH_DIR):] and dl.endswith(".archive"):
            return "mod", ""
        m = re.fullmatch(r"mods/([^/]+)/archives/[^/]+\.archive", dest, re.I)
        return ("redmod", m.group(1)) if m else (None, "")

    for dl, (key, e, dest) in plan["final"].items():
        g, dossier = genre(dest)
        if not g:
            continue
        mod, fichier = index[key], None
        if jeu.same(dest, e["c"], e["s"]):
            fichier = jeu.path(dest)
        elif store and store.a_jour(mod) and os.path.isfile(store.src(mod, e["n"])):
            fichier = store.src(mod, e["n"])
        provs.append({"archive": dest.split("/")[-1], "dest": dest, "zip": key, "genre": g, "dossier": dossier,
                      "fichier": fichier, "zip_path": mod["zip"], "entree": e["n"], "origine": (e["d"] or dest).split("/")[-1]})
        vus.add(dl)
    # archives présentes dans le jeu que le profil ne tient pas et que l'outil n'a pas posées : mods posés à la main
    lieux = [(ARCH_DIR.rstrip("/"), "")]
    mods_dir = jeu.path("mods")
    if os.path.isdir(mods_dir):
        lieux += [(f"mods/{d}/archives", d) for d in sorted(os.listdir(mods_dir)) if os.path.isdir(os.path.join(mods_dir, d, "archives"))]
    for rel, dossier in lieux:
        folder = jeu.path(rel)
        for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            dest = rel + "/" + f
            if f.lower().endswith(".archive") and dest.lower() not in vus and dest.lower() not in pose and os.path.isfile(os.path.join(folder, f)):
                provs.append({"archive": f, "dest": dest, "zip": None, "genre": "hors", "dossier": dossier,
                              "fichier": os.path.join(folder, f), "zip_path": None, "entree": None, "origine": f})
    par_nom = {p["archive"]: p for p in provs if not p["dossier"]}
    noms, sert = ordonne(list(par_nom), modlist if modlist is not None else modlist_du_jeu(jeu) or [])
    libres, source = [par_nom[n] for n in noms], "modlist.txt" if sert else "noms"
    red = sorted((p for p in provs if p["dossier"]), key=lambda p: (octets(p["dossier"]), octets(p["archive"])))
    return libres + red, source


def noms_ressources(besoin, provs, jeu, data, oodle):
    """{empreinte: chemin} pour les empreintes demandées ; ce qui est trouvé est gardé dans `noms.json` (données)"""
    path = os.path.join(data, "noms.json")
    try:
        cache = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    connus = cache.setdefault("noms", {})
    kark = jeu.path(KARK)
    # ce qui a déjà été cherché en vain n'est recherché que si les archives chargées ou la liste de CET ont changé
    sig = hashlib.sha1(json.dumps([[p["dest"], len(p["ents"])] for p in provs]
                                  + [Magasin.stat(kark) if oodle.fn else None]).encode()).hexdigest()
    sans = set(cache.get("sans", [])) if cache.get("sig") == sig else set()
    manque = {h for h in besoin if f"{h:016x}" not in connus and f"{h:016x}" not in sans}
    if not manque:
        return {h: connus[f"{h:016x}"] for h in besoin if f"{h:016x}" in connus}

    def range_(lignes):
        for raw in lignes:
            b = raw.strip().strip(b'"').lstrip(b"\\/").replace(b"/", b"\\").lower()
            h = fnv64(b)
            if h in manque:
                connus[f"{h:016x}"] = b.decode("latin-1")
                manque.discard(h)

    for p in provs:                                  # d'abord les chemins écrits dans les archives concernées
        if manque and manque & p["set"]:
            try:
                range_(lit_archive(p, lambda r: rdar_noms(r, oodle)))
            except (OSError, ValueError, struct.error, zipfile.BadZipFile):
                pass
    if manque and os.path.isfile(kark) and oodle.fn:   # puis la liste de CET (chemins du jeu de base)
        raw = open(kark, "rb").read()
        if len(raw) > 8 and raw[:4] == b"KARK":
            range_(oodle.decode(raw[8:], struct.unpack_from("<I", raw, 4)[0]).splitlines())
    cache["sig"], cache["sans"] = sig, sorted(sans | {f"{h:016x}" for h in manque})
    cache.pop("kark", None)
    os.makedirs(data, exist_ok=True)
    json.dump(cache, open(path, "w", encoding="utf-8"))
    return {h: connus[f"{h:016x}"] for h in besoin if f"{h:016x}" in connus}


BASE_DIRS = ("archive/pc/content", "archive/pc/ep1")


def base_du_jeu(jeu, data):
    """empreintes des ressources du jeu de base (archives de `content` et `ep1`), gardées dans `base.bin` tant que ces
    archives n'ont pas changé ; tableau vide si le jeu n'en a pas (banc)"""
    import array
    fichiers = []
    for rel in BASE_DIRS:
        d = jeu.path(rel)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.lower().endswith(".archive"):
                st = os.stat(os.path.join(d, f))
                fichiers.append([rel + "/" + f, st.st_size, st.st_mtime_ns])
    sig = hashlib.sha1(json.dumps(fichiers).encode()).hexdigest()
    bin_path, sig_path = os.path.join(data, "base.bin"), os.path.join(data, "base.json")
    arr = array.array("Q")
    try:
        if json.load(open(sig_path, encoding="utf-8")).get("sig") == sig:
            with open(bin_path, "rb") as f:
                arr.frombytes(f.read())
            return arr
    except (OSError, ValueError):
        pass
    for rel, _, _ in fichiers:
        try:
            with open(jeu.path(rel), "rb") as f:
                head = f.read(44)
                if len(head) < 44 or head[:4] != b"RDAR":
                    continue
                pos, size = struct.unpack_from("<QI", head, 8)
                f.seek(pos)
                idx = f.read(size) if 28 <= size <= 1 << 30 else b""
            if len(idx) < 28:
                continue
            count = min(struct.unpack_from("<I", idx, 16)[0], (len(idx) - 28) // 56)
            arr.extend(h for h, in struct.iter_unpack("<Q48x", idx[28:28 + 56 * count]))
        except (OSError, struct.error):
            continue
    os.makedirs(data, exist_ok=True)
    with open(bin_path, "wb") as f:
        f.write(arr.tobytes())
    json.dump({"sig": sig, "archives": len(fichiers), "ressources": len(arr)}, open(sig_path, "w", encoding="utf-8"))
    return arr


def conflits_archives(provs):
    """paires {(i, j): {conflits: [empreintes], identiques: n}} avec i chargée avant j (i gagne) ; rangs = place dans provs"""
    par = collections.defaultdict(list)
    for i, p in enumerate(provs):
        for h, sha in dict(p["ents"]).items():
            par[h].append((i, sha))
    paires = {}
    for h, l in par.items():
        for a in range(len(l) - 1):
            for b in range(a + 1, len(l)):
                d = paires.setdefault((l[a][0], l[b][0]), {"conflits": [], "identiques": 0})
                if l[a][1] == l[b][1] and l[a][1] not in SHA_VIDES:
                    d["identiques"] += 1
                else:
                    d["conflits"].append(h)
    return paires, par


# ---------------------------------------------------------------- conflits de code : Redscript, TweakXL, SetFlat
# Port de la détection de Conflict Studio 1.0.2 (qcargile, MIT) : ScriptInteractions, TweakInteractions, SourcePrecedence,
# RedScriptConditionalSourceFilter, SharedStateWriteAnalyzer (TweakDB seul). Lecture seule. Deux mods qui posent le MÊME
# chemin ne sont pas un conflit de code : c'est un écrasement de fichier, tranché par le plan ; ici un seul le tient.

CODE_V = 3                                           # version de l'extraction : un cache d'une autre version est relu
CODE_EXT_LUES = (".reds", ".yaml", ".yml", ".lua", ".tweak")
GREFFONS_REDS = ("archivexl", "codeware", "tweakxl")  # greffons RED4ext dont le dossier `Scripts` est compilé
RX_MASQUE = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
RX_MASQUE_LUA = re.compile(r"--\[(=*)\[.*?\]\1\]|--[^\n]*", re.S)
RX_CHAINE = re.compile(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')', re.S)
RX_ANNOT = re.compile(r"^[ \t]*@(wrapMethod|replaceMethod|addMethod|addField)\(([^)]+)\)", re.M)
RX_FUNC = re.compile(r"\bfunc\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)")
RX_LET = re.compile(r"\blet\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^;=]+)")
RX_MODULE = re.compile(r"^\s*module\s+([A-Za-z_][A-Za-z0-9_.]*)", re.M)
RX_SI = re.compile(r"@if(Not)?\s*\(")
RX_SI_TERME = re.compile(r"""^\s*(!)?\s*ModuleExists\s*\(\s*["']([^"']+)["']\s*\)\s*$""")
RX_IMPORT = re.compile(r"import\b[^;\r\n]*;?")
RX_DECL = re.compile(r"\b(?:func|class|struct|enum|let)\b")
RX_DECL_DEBUT = re.compile(r"^[ \t]*(?:@|(?:[A-Za-z_][A-Za-z0-9_]*[ \t]+)*(?:func|class|struct|enum|let|import)\b)", re.M)
RX_ACCOLADE = re.compile(r"[{}]")
RX_SUITE = re.compile(r"\bwrappedMethod\s*\(")
RX_SETFLAT = re.compile(r"""\b(TweakDBInterface|TweakDBManager|TweakDB)[.:](SetFlat|SetFlatNoUpdate)\s*\(\s*([tn])?(["'])([^"'\\\r\n]+)\4\s*,""")
RX_LITTERAL = re.compile(r"""^(?:(-?[0-9]+(?:\.[0-9]+)?)[fF]?|(true|false)|[tn]?(["'])((?:\\.|(?!\3).)*)\3)$""", re.I)
MUTATIONS = {"!append": "append", "!append-once": "append-once", "!append-from": "append-from", "!prepend": "prepend",
             "!prepend-once": "prepend-once", "!prepend-from": "prepend-from", "!remove": "remove"}
AJOUTS = ("append", "append-once", "append-from", "prepend", "prepend-once", "prepend-from")
COPIES = ("append-from", "prepend-from")
NIVEAUX = {"remplacement": "attention", "double": "revoir", "coupe": "revoir", "valeur": "revoir", "oppose": "revoir", "liste": "revoir",
           "doublon": "revoir", "definition": "revoir", "copie": "revoir", "code": "revoir"}   # le reste : « rien » ou « info »
INFOS = ("interne",)


def _blanc(s):
    return "\n".join(" " * len(x) for x in s.split("\n"))


def masque_reds(t, chaines):
    """commentaires effacés (longueur gardée : les positions restent celles du fichier) ; `chaines` efface aussi les chaînes"""
    return RX_MASQUE.sub(lambda m: _blanc(m.group(0)) if chaines or m.group(0)[0] == "/" else m.group(0), t)


def normalise_code(s):
    """blancs réduits hors des chaînes : deux corps qui ne diffèrent que par la mise en page sont le même"""
    return "".join(p if i % 2 else re.sub(r"\s+", " ", p) for i, p in enumerate(RX_CHAINE.split(s))).strip()


def fin_bloc(syn, i):
    """position après l'accolade qui ferme le bloc ouvert en `i` ; None s'il ne se ferme pas"""
    prof = 0
    for m in RX_ACCOLADE.finditer(syn, i):
        prof += 1 if m.group() == "{" else -1
        if prof == 0:
            return m.end()
    return None


def fin_parenthese(s, i):
    """position de la parenthèse qui ferme celle ouverte en `i` ; -1 sinon"""
    prof = 0
    for k in range(i, len(s)):
        if s[k] == "(":
            prof += 1
        elif s[k] == ")":
            prof -= 1
            if prof == 0:
                return k
    return -1


def fin_declaration(syn, i):
    """fin de la déclaration gardée par un `@if` (annotations suivantes comprises)"""
    n = len(syn)
    while i < n:
        if syn[i].isspace():
            i += 1
            continue
        if syn[i] != "@":
            break
        while i < n and syn[i] != "(":
            i += 1
        k = fin_parenthese(syn, i)
        i = n if k < 0 else k + 1
    m = RX_IMPORT.match(syn, i)
    if m:
        return m.end()
    d = RX_DECL.search(syn, i)
    nl = syn.find("\n", d.end() if d else i)
    nd = RX_DECL_DEBUT.search(syn, nl + 1) if nl >= 0 else None
    lim = nd.start() if nd else n
    while i < lim and syn[i] not in "{;":
        i += 1
    if i == lim:
        return i
    return i + 1 if syn[i] == ";" else (fin_bloc(syn, i) or n)


def type_reds(t):
    t = re.sub(r"\s+", "", t)
    while True:
        u = re.sub(r"\[([^\[\]]+)\]", r"array<\1>", t)
        if u == t:
            return t
        t = u


def cible_reds(classe, methode, params):
    parts, debut, prof = [], 0, 0
    for i, c in enumerate(params):
        if c in "<[(":
            prof += 1
        elif c in ">])":
            prof -= 1
        elif c == "," and prof == 0:
            parts.append(params[debut:i])
            debut = i + 1
    parts.append(params[debut:])
    types = [type_reds(p.split(":", 1)[-1].split("=")[0]) for p in parts]
    return f"{classe.strip()}.{methode}({', '.join(t for t in types if t)})"


def litteral(arg):
    """valeur littérale d'un argument de SetFlat (nombre, booléen, chaîne) ; None si c'est une expression"""
    m = RX_LITTERAL.match(arg.strip())
    if not m:
        return None
    return m.group(1) or (m.group(2) or "").lower() or m.group(4)


def lignes_de(t):
    """rend ligne(position) pour ce texte, à partir de 1"""
    fins = [m.start() for m in re.finditer("\n", t)]
    return lambda pos: bisect.bisect_left(fins, pos) + 1


def ecrits_tweakdb(code, syn, lua=False):
    out, ligne = [], lignes_de(code)
    for m in RX_SETFLAT.finditer(code):
        if syn is not None and syn[m.start()] != code[m.start()]:
            continue                                 # dans une chaîne
        if m.group(3) and (lua or (m.group(3) == "n" and (m.group(1), m.group(2)) != ("TweakDBManager", "SetFlat"))):
            continue
        k = m.start() - 1
        while k >= 0 and code[k].isspace():
            k -= 1
        if k >= 0 and code[k] in ".:":
            continue                                 # `x.TweakDB.SetFlat` : un autre objet
        fin = fin_parenthese(syn if syn is not None else code, code.index("(", m.start()))
        arg = code[m.end():fin] if fin > 0 else ""
        out.append({"cible": m.group(5), "ligne": ligne(m.start()), "geste": m.group(2),
                    "valeur": litteral(arg), "texte": normalise_code(arg)[:200], "pos": m.start()})
    return out


def lit_reds(texte):
    """ce qu'un `.reds` déclare : modules, annotations (cible, corps), écritures TweakDB, conditions `@if` qui les gardent"""
    code, syn = masque_reds(texte, False), masque_reds(texte, True)
    conds = []                                       # [début, fin de la déclaration gardée, expression, @ifNot]
    for m in RX_SI.finditer(code):
        if syn[m.start()] != "@":
            continue
        f = fin_parenthese(syn, m.end() - 1)
        if f < 0:
            continue
        conds.append([m.start(), fin_declaration(syn, f + 1), code[m.end():f], bool(m.group(1))])
    garde = lambda pos: [i for i, c in enumerate(conds) if c[0] <= pos < c[1]]
    annots, hooks, ligne = list(RX_ANNOT.finditer(code)), [], lignes_de(code)
    for n, a in enumerate(annots):
        sorte = a.group(1)
        d = (RX_LET if sorte == "addField" else RX_FUNC).search(code, a.end())
        if not d or (n + 1 < len(annots) and annots[n + 1].start() < d.start()):
            continue
        h = {"sorte": sorte, "ligne": ligne(a.start()), "si": garde(a.start())}
        if sorte == "addField":
            h["cible"], h["type"] = f"{a.group(2).strip()}.{d.group(1)}", d.group(2).strip()
        else:
            h["cible"] = cible_reds(a.group(2), d.group(1), d.group(2))
            ouvre, point = syn.find("{", d.end()), syn.find(";", d.end())
            fin = fin_bloc(syn, ouvre) if ouvre >= 0 and not 0 <= point < ouvre else None
            if fin:
                h["corps"] = hashlib.sha1(normalise_code(h["cible"] + "|" + code[d.start():fin]).encode("utf-8", "replace")).hexdigest()[:16]
                if sorte == "wrapMethod":
                    h["suite"] = bool(RX_SUITE.search(syn, ouvre, fin))
        hooks.append(h)
    ecrits = ecrits_tweakdb(code, syn)
    for e in ecrits:
        e["si"] = garde(e.pop("pos"))
    return {"modules": [m.group(1) for m in RX_MODULE.finditer(code)], "hooks": hooks, "ecrits": ecrits,
            "conds": [[c[2], c[3]] for c in conds]}


def lit_lua(texte):
    code = RX_MASQUE_LUA.sub(lambda m: _blanc(m.group(0)), texte)
    ecrits = ecrits_tweakdb(code, None, True)
    for e in ecrits:
        e.pop("pos")
    return {"ecrits": ecrits}


def condition_vraie(expr, non, modules):
    """`@if(ModuleExists("X") && …)` évalué sur les modules déclarés par les scripts lus ; None si l'expression est autre"""
    sep = "||" if "||" in expr else "&&"
    vals = []
    for t in (x for x in expr.split(sep) if x.strip()):
        m = RX_SI_TERME.match(t)
        if not m:
            return None
        vals.append((m.group(2).lower() in modules) != bool(m.group(1)))
    if not vals:
        return None
    v = any(vals) if sep == "||" else all(vals)
    return not v if non else v


# -- YAML de TweakXL : mappings et listes en blocs ou en ligne, étiquettes (`!append`…), ancres ; rien d'autre n'y sert

class YamlErreur(ValueError):
    pass


class Noeud:
    """nœud YAML : t = s (scalaire), l (liste), m (mapping : liste de couples) ; ligne à partir de 1"""
    __slots__ = ("t", "v", "tag", "ligne", "alias")

    def __init__(self, t, v, ligne, tag="", alias=False):
        self.t, self.v, self.ligne, self.tag, self.alias = t, v, ligne, tag, alias


def _yaml_lignes(texte):
    """[n° de ligne, indentation, texte sans commentaire, bloc littéral ou None] pour chaque ligne utile"""
    brutes = texte.lstrip("\ufeff").splitlines()
    out, i = [], 0
    while i < len(brutes):
        l = brutes[i]
        i += 1
        q, k, n = "", 0, len(l)
        while k < n:                                 # coupe le commentaire, hors guillemets
            c = l[k]
            if q == '"':
                if c == "\\":
                    k += 1
                elif c == '"':
                    q = ""
            elif q == "'":
                if c == "'":
                    if k + 1 < n and l[k + 1] == "'":
                        k += 1
                    else:
                        q = ""
            elif c in "\"'" and (k == 0 or l[k - 1] in " \t[{,:"):
                q = c
            elif c == "#" and (k == 0 or l[k - 1] in " \t"):
                l = l[:k]
                break
            k += 1
        t = l.strip()
        if not t:
            continue
        tete = l[:len(l) - len(l.lstrip())]
        if "\t" in tete:
            raise YamlErreur(T("ligne {0} : tabulation dans l'indentation", i))
        bloc, no = None, i
        if re.search(r"(?:^|\s)[|>][+-]?[0-9]?[+-]?$", t):   # bloc littéral : les lignes plus indentées sont son texte
            corps = []
            while i < len(brutes) and (not brutes[i].strip() or len(brutes[i]) - len(brutes[i].lstrip()) > len(tete)):
                corps.append(brutes[i].strip())
                i += 1
            bloc = "\n".join(corps).strip()
        out.append([no, len(tete), t, bloc])
    return out


class _Yaml:
    def __init__(self, lignes):
        self.L, self.i, self.ancres = lignes, 0, {}

    def racine(self):
        n = self.bloc()
        if self.i < len(self.L):
            raise YamlErreur(T("ligne {0} : contenu inattendu", self.L[self.i][0]))
        return n

    @staticmethod
    def cle(t):
        """(clé, reste, décalage du reste) si la ligne est `clé: valeur` ; None sinon"""
        if t[0] in "[{-?" and (t[0] in "[{" or t[1:2] in ("", " ")):
            return None
        if t[0] in "\"'":
            q, k = t[0], 1
            while k < len(t) and t[k] != q:
                k += 2 if (q == '"' and t[k] == "\\") else 1
            k += 1
            if t[k:k + 1] != ":" or t[k + 1:k + 2] not in ("", " "):
                return None
            cle = t[1:k - 1]
        else:
            k = 0
            while True:
                k = t.find(":", k)
                if k < 0:
                    return None
                if t[k + 1:k + 2] in ("", " "):
                    break
                k += 1
            cle = t[:k].rstrip()
        reste = t[k + 1:]
        return cle, reste.strip(), k + 1 + len(reste) - len(reste.lstrip())

    @staticmethod
    def props(t):
        tag = ancre = ""
        while t[:1] in ("!", "&"):
            mot, _, suite = t.partition(" ")
            if mot[0] == "!":
                tag = mot
            else:
                ancre = mot[1:]
            t = suite.lstrip()
        return tag, ancre, t

    def bloc(self):
        no, ind, t, _ = self.L[self.i]
        if t == "-" or t.startswith("- "):
            return self.liste(ind)
        if self.cle(t) is not None:
            return self.mapping(ind)
        return self.noeud(t, no, ind, False)

    def liste(self, ind):
        items, no0 = [], self.L[self.i][0]
        while self.i < len(self.L) and self.L[self.i][1] == ind and (self.L[self.i][2] == "-" or self.L[self.i][2].startswith("- ")):
            no, _, t, b = self.L[self.i]
            reste = t[1:].lstrip()
            self.L[self.i] = [no, ind + len(t) - len(reste), reste, b]
            items.append(self.noeud(reste, no, ind, False))
        if self.i < len(self.L) and self.L[self.i][1] > ind:
            raise YamlErreur(T("ligne {0} : indentation", self.L[self.i][0]))
        return Noeud("l", items, no0)

    def mapping(self, ind):
        couples, no0 = [], self.L[self.i][0]
        while self.i < len(self.L) and self.L[self.i][1] == ind:
            no, _, t, b = self.L[self.i]
            c = self.cle(t)
            if c is None:
                raise YamlErreur(T("ligne {0} : « clé: valeur » attendu", no))
            self.L[self.i] = [no, ind + c[2], c[1], b]
            couples.append((Noeud("s", c[0], no), self.noeud(c[1], no, ind, True)))
        if self.i < len(self.L) and self.L[self.i][1] > ind:
            raise YamlErreur(T("ligne {0} : indentation", self.L[self.i][0]))
        return Noeud("m", couples, no0)

    def noeud(self, t, no, parent, de_mapping):
        """nœud dont le texte en ligne est `t` (ligne courante), dans une collection indentée à `parent`"""
        tag, ancre, t = self.props(t)
        col, bloc = self.L[self.i][1], self.L[self.i][3]
        if not t:
            self.i += 1
            suit = self.L[self.i] if self.i < len(self.L) else None
            if suit and (suit[1] > parent or (de_mapping and suit[1] == parent and (suit[2] == "-" or suit[2].startswith("- ")))):
                n = self.bloc()
            else:
                n = Noeud("s", "", no)
        elif t[0] == "*":
            self.i += 1
            src = self.ancres.get(t[1:].strip())
            if src is None:
                raise YamlErreur(T("ligne {0} : ancre inconnue {1}", no, t))
            n = Noeud(src.t, src.v, no, src.tag, True)
        elif bloc is not None and t[0] in "|>":
            self.i += 1
            n = Noeud("s", bloc, no)
        elif not de_mapping and not tag and t[0] not in "[{\"'" and self.cle(t) is not None:
            self.L[self.i] = [no, col + (len(self.L[self.i][2]) - len(t)), t, bloc]
            n = self.mapping(self.L[self.i][1])
        elif not de_mapping and tag and t[0] not in "[{\"'" and self.cle(t) is not None:
            self.L[self.i] = [no, col + (len(self.L[self.i][2]) - len(t)), t, bloc]   # `- !append-once $type: X` et la suite
            n = self.mapping(self.L[self.i][1])
        else:
            self.i += 1
            if t[0] in "[{":
                while t.count("[") + t.count("{") > t.count("]") + t.count("}") and self.i < len(self.L):
                    t += " " + self.L[self.i][2]
                    self.i += 1
                n, p = self.flux(t, 0, no, "")
                if t[p:].strip():
                    raise YamlErreur(T("ligne {0} : suite inattendue après la valeur", no))
            else:
                if t[0] in "\"'":
                    while not self.ferme(t) and self.i < len(self.L):
                        t += " " + self.L[self.i][2]
                        self.i += 1
                else:
                    while self.i < len(self.L) and self.L[self.i][1] > parent:   # scalaire simple sur plusieurs lignes
                        t += " " + self.L[self.i][2]
                        self.i += 1
                n = Noeud("s", self.scalaire(t, no), no)
        if tag:
            n.tag = tag
        if ancre:
            self.ancres[ancre] = n
        return n

    @staticmethod
    def ferme(t):
        q, k = t[0], 1
        while k < len(t):
            if q == '"' and t[k] == "\\":
                k += 2
                continue
            if t[k] == q:
                if q == "'" and t[k + 1:k + 2] == "'":
                    k += 2
                    continue
                return True
            k += 1
        return False

    @staticmethod
    def scalaire(t, no):
        t = t.strip()
        if t[:1] == '"':
            if len(t) < 2 or t[-1] != '"':
                raise YamlErreur(T("ligne {0} : guillemet non fermé", no))
            return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t", "0": "\0"}.get(m.group(1), m.group(1)), t[1:-1])
        if t[:1] == "'":
            if len(t) < 2 or t[-1] != "'":
                raise YamlErreur(T("ligne {0} : apostrophe non fermée", no))
            return t[1:-1].replace("''", "'")
        return t

    def flux(self, s, p, no, fins):
        """valeur en ligne (`[a, b]`, `{k: v}`, scalaire) à partir de `p` ; rend (nœud, position suivante)"""
        n_s = len(s)
        while p < n_s and s[p] == " ":
            p += 1
        tag = ancre = ""
        while p < n_s and s[p] in "!&":
            q = p
            while q < n_s and s[q] not in " ,]}":
                q += 1
            if s[p] == "!":
                tag = s[p:q]
            else:
                ancre = s[p + 1:q]
            p = q
            while p < n_s and s[p] == " ":
                p += 1
        if p >= n_s or s[p] in ",]}":
            n = Noeud("s", "", no)
        elif s[p] == "*":
            q = p
            while q < n_s and s[q] not in " ,]}":
                q += 1
            src = self.ancres.get(s[p + 1:q])
            if src is None:
                raise YamlErreur(T("ligne {0} : ancre inconnue {1}", no, s[p:q]))
            n, p = Noeud(src.t, src.v, no, src.tag, True), q
        elif s[p] == "[":
            items, p = [], p + 1
            while True:
                while p < n_s and s[p] == " ":
                    p += 1
                if p >= n_s:
                    raise YamlErreur(T("ligne {0} : « ] » manquant", no))
                if s[p] == "]":
                    p += 1
                    break
                it, p = self.flux(s, p, no, ",]")
                items.append(it)
                while p < n_s and s[p] == " ":
                    p += 1
                if p < n_s and s[p] == ",":
                    p += 1
                elif p >= n_s or s[p] != "]":
                    raise YamlErreur(T("ligne {0} : « , » ou « ] » attendu", no))
            n = Noeud("l", items, no)
        elif s[p] == "{":
            couples, p = [], p + 1
            while True:
                while p < n_s and s[p] == " ":
                    p += 1
                if p >= n_s:
                    raise YamlErreur(T("ligne {0} : « } » manquant", no))
                if s[p] == "}":
                    p += 1
                    break
                k, p = self.flux(s, p, no, ":,}")
                while p < n_s and s[p] == " ":
                    p += 1
                if p < n_s and s[p] == ":":
                    v, p = self.flux(s, p + 1, no, ",}")
                else:
                    v = Noeud("s", "", no)
                couples.append((k, v))
                while p < n_s and s[p] == " ":
                    p += 1
                if p < n_s and s[p] == ",":
                    p += 1
                elif p >= n_s or s[p] != "}":
                    raise YamlErreur(T("ligne {0} : « , » ou « } » attendu", no))
            n = Noeud("m", couples, no)
        elif s[p] in "\"'":
            q, k = s[p], p + 1
            while k < n_s:
                if q == '"' and s[k] == "\\":
                    k += 2
                    continue
                if s[k] == q:
                    if q == "'" and s[k + 1:k + 2] == "'":
                        k += 2
                        continue
                    break
                k += 1
            if k >= n_s:
                raise YamlErreur(T("ligne {0} : guillemet non fermé", no))
            n, p = Noeud("s", self.scalaire(s[p:k + 1], no), no), k + 1
        else:
            q = p
            while q < n_s and not (s[q] in fins and (s[q] != ":" or s[q + 1:q + 2] in ("", " "))):
                q += 1
            n, p = Noeud("s", s[p:q].strip(), no), q
        if tag:
            n.tag = tag
        if ancre:
            self.ancres[ancre] = n
        return n, p


def yaml_docs(texte):
    """les documents d'un fichier YAML ; YamlErreur si le fichier sort de ce que ce lecteur comprend"""
    docs, cur = [], []
    for l in _yaml_lignes(texte):
        if l[1] == 0 and (l[2] == "---" or l[2].startswith("--- ")):
            if cur:
                docs.append(cur)
            cur = [[l[0], 0, l[2][3:].strip(), l[3]]] if l[2][3:].strip() else []
        elif l[1] == 0 and (l[2] == "..." or (l[2][0] == "%" and not cur)):
            continue
        else:
            cur.append(l)
    if cur:
        docs.append(cur)
    try:
        return [_Yaml(d).racine() for d in docs]
    except (IndexError, RecursionError) as e:
        raise YamlErreur(T("structure non comprise ({0})", type(e).__name__))


def _yn(n, racine=True):
    """valeur normalisée d'un nœud : étiquette gardée (sauf celle d'une mutation), clés d'un mapping triées"""
    tag = "" if not n.tag or n.tag.lower() in MUTATIONS else n.tag + " "
    if n.t == "s":
        return tag + n.v
    if n.t == "l":
        return tag + "[" + ",".join(_yn(x) for x in n.v) + "]"
    return tag + "{" + ",".join(f"{k}:{v}" for k, v in sorted((_yn(k), _yn(v)) for k, v in n.v)) + "}"


def _yget(m, nom):
    return next((v for k, v in m.v if k.t == "s" and k.v == nom), None)


def _mut(n):
    return MUTATIONS.get(n.tag.lower()) if n.tag else None


def _est_affectation(v):
    if v.t == "l":
        return not any(_mut(x) for x in v.v)
    if v.t == "m":
        return _yget(v, "$type") is None and _yget(v, "$base") is None
    return True


def _proprietes(m):
    """couples d'un enregistrement : un seul `$base` (sinon `$type`), et la DERNIÈRE affectation d'une propriété répétée"""
    construit = next((k for k, _ in m.v if k.t == "s" and k.v == "$base"), None) or \
        next((k for k, _ in m.v if k.t == "s" and k.v == "$type"), None)
    dernier = {}
    for k, v in m.v:
        if k.t == "s" and _est_affectation(v):
            dernier[k.v] = k
    for k, v in m.v:
        if k.t == "s" and k.v in ("$type", "$base"):
            if k is construit:
                yield k, v
        elif k.t != "s" or not _est_affectation(v) or dernier[k.v] is k:
            yield k, v


def lit_tweak(texte):
    """opérations TweakXL d'un fichier : [cible, valeur, genre, ligne, drapeaux] ; limites = ce qui n'a pas pu être lu"""
    ops, limites = [], []

    def op(cible, n, genre, ligne, alias, mutation=False):
        ops.append({"cible": cible, "valeur": _yn(n), "genre": genre, "ligne": ligne, "alias": alias or n.alias})

    def ajoute(cible, prop, v, ligne, alias=False):
        if prop.startswith("$") and prop not in ("$type", "$base"):
            return
        alias = alias or v.alias
        if v.t == "l":
            muts = [x for x in v.v if _mut(x)]
            if muts:
                for x in muts:
                    op(cible, x, _mut(x), x.ligne, alias)
                if any(not x.tag for x in v.v):
                    limites.append(T("{0} : liste qui mêle remplacement et mutations ; seules les mutations comptent (ligne {1})", cible, ligne))
            else:
                op(cible, v, "liste", ligne, alias)
            return
        if v.t == "m" and (_yget(v, "$type") is not None or _yget(v, "$base") is not None):
            for k, w in _proprietes(v):
                if k.t == "s" and k.v.strip():
                    ajoute(cible + "." + k.v, k.v, w, k.ligne, alias)
            return
        genre = "type" if prop == "$type" else "base" if prop == "$base" else "inline" if v.t == "m" else "valeur"
        if genre in ("type", "base"):
            cible = (cible[:cible.rfind(".")] if "." in cible else cible) + ".$definition"
        op(cible, v, genre, ligne, alias)

    def remplace(s, variables):
        for nom, val in variables.items():
            s = s.replace("$(" + nom + ")", val).replace("${" + nom + "}", val)
        return s

    for doc in yaml_docs(texte):
        if doc.t != "m":
            raise YamlErreur(T("la racine d'un document TweakXL doit être un mapping"))
        for cle, v in doc.v:
            if cle.t != "s" or not cle.v.strip():
                continue
            cible = cle.v
            if v.t != "m":
                ajoute(cible, cible.split(".")[-1], v, cle.ligne)
                continue
            inst = _yget(v, "$instances")
            if inst is not None and inst.t == "l":
                for i in inst.v:
                    if i.t != "m":
                        continue
                    variables = {k.v: _yn(w) for k, w in i.v if k.t == "s"}
                    for k, w in _proprietes(v):
                        if k.t != "s" or not k.v.strip() or k.v == "$instances":
                            continue
                        n0 = len(ops)
                        ajoute(remplace(cible + "." + k.v, variables), k.v, w, k.ligne, v.alias)
                        for o in ops[n0:]:
                            o.update(cible=remplace(o["cible"], variables), valeur=remplace(o["valeur"], variables), genere=True)
                continue
            for k, w in _proprietes(v):
                if k.t == "s" and k.v.strip():
                    ajoute(cible + "." + k.v, k.v, w, k.ligne, v.alias)
    for o in ops:                                    # valeur longue : sa tête et son empreinte (l'égalité reste exacte)
        if len(o["valeur"]) > 160:
            o["valeur"] = o["valeur"][:120] + " … #" + hashlib.sha1(o["valeur"].encode("utf-8", "replace")).hexdigest()[:12]
    return {"ops": [[o["cible"], o["valeur"], o["genre"], o["ligne"], (1 if o["alias"] else 0) + (2 if o.get("genere") else 0)] for o in ops],
            "limites": limites}


def _parts(dest):
    return [p.lower() for p in dest.split("/")]


def _ordre_sources(lignes, tweak):
    """(gagnant, raison) prévus par l'ordre de lecture des fichiers : le dernier lu a le dernier mot. Jamais observé en jeu."""
    lus = []
    for l in lignes:
        p = _parts(l["fichier"])
        greffon = p[0] == "red4ext"
        prio = 1 if not tweak else 0 if p[-1][0] in "_#$!" else 2 if p[-1][0] == "^" else 1
        if any(ord(c) < 32 or ord(c) > 126 for c in l["fichier"]):
            return None, T("nom de fichier hors ASCII : ordre de lecture non prévisible")
        lus.append((greffon, prio, p, l["ligne"], l))
    if len(lus) < 2 or sum(1 for x in lus if x[0]) > 1:
        return None, T("ordre entre greffons RED4ext inconnu")
    for i, a in enumerate(lus):
        for b in lus[i + 1:]:
            if len(a[2]) != len(b[2]) and all(x == y for x, y in zip(a[2], b[2])):
                return None, T("un chemin est le début de l'autre : ordre non prévisible")
            if a[2] == b[2] and (a[4]["prov"] != b[4]["prov"] or a[3] == b[3]):
                return None, T("même fichier : ordre non prévisible")
    lus.sort(key=lambda x: x[:4])
    return lus[-1][4], (T("ordre des noms de fichiers de r6/tweaks (« _ # $ ! » en tête d'abord, « ^ » en dernier)") if tweak
                        else suite(T("ordre des noms de fichiers de r6/scripts"), T("les scripts d'un greffon RED4ext viennent après") if lus[-1][0] else ""))


def conflits_redscript(fichiers):
    """fichiers : [{prov, fichier, lu: résultat de lit_reds}] ; rend (trouvailles, limites)"""
    modules = {m.lower() for f in fichiers for m in f["lu"]["modules"]}
    par, limites = collections.defaultdict(list), []
    for f in fichiers:
        etat = [condition_vraie(e, non, modules) for e, non in f["lu"]["conds"]]
        if any(x is None for x in etat):
            limites.append({"prov": f["prov"], "fichier": f["fichier"],
                            "quoi": T("condition @if non évaluée : les déclarations qu'elle garde sont laissées hors de l'analyse")})
        for h in f["lu"]["hooks"]:
            if all(etat[i] is True for i in h["si"]):
                par[h["cible"]].append(dict(h, prov=f["prov"], fichier=f["fichier"]))
    out = []
    for cible, hs in par.items():
        provs = {h["prov"] for h in hs}
        ajouts = [h for h in hs if h["sorte"] in ("addMethod", "addField")]
        reps = [h for h in hs if h["sorte"] == "replaceMethod"]
        vus = hs
        if len(provs) == 1:
            if len(ajouts) > 1:
                sorte = "double"
            elif len(reps) > 1:
                vus = reps
                sorte = None
            else:
                sorte = "compose"
        else:
            sorte = None
        if sorte is None:
            aj = [h for h in vus if h["sorte"] in ("addMethod", "addField")]
            rp = [h for h in vus if h["sorte"] == "replaceMethod"]
            if len(aj) == len(vus):
                sorte = "double"
            elif aj:
                sorte = "ajout"
            elif len(rp) <= 1:
                sorte = "compose"
            elif not (all(h.get("corps") for h in rp) and len({h["corps"] for h in rp}) == 1):
                sorte = "remplacement"
            else:
                sorte = "identique" if len(rp) == len(vus) else "compose"
        if len(provs) < 2 and sorte not in ("remplacement", "identique", "double"):
            continue
        # une enveloppe qui n'appelle jamais `wrappedMethod` coupe la chaîne : pour les autres mods, c'est un remplacement
        if sorte in ("compose", "ajout") and len(provs) > 1 and any(h["sorte"] == "wrapMethod" and h.get("suite") is False for h in hs):
            sorte = "coupe"
        t = {"voie": "redscript", "sorte": sorte, "cible": cible, "lignes": [
            {"prov": h["prov"], "fichier": h["fichier"], "ligne": h["ligne"], "geste": "@" + h["sorte"],
             "valeur": h.get("type") or (T("n'appelle pas wrappedMethod") if h.get("suite") is False else "")} for h in hs]}
        if sorte == "remplacement":
            g, raison = _ordre_sources([l for l in t["lignes"] if l["geste"] == "@replaceMethod"], False)
            t["gagnant"], t["raison"] = (t["lignes"].index(g) if g else None), raison
        out.append(t)
    return out, limites


def conflits_tweaks(fichiers):
    """fichiers : [{prov, fichier, lu: résultat de lit_tweak}] ; rend (trouvailles, toutes les opérations)"""
    ops = [{"cible": o[0], "valeur": o[1], "genre": o[2], "ligne": o[3], "alias": bool(o[4] & 1), "genere": bool(o[4] & 2),
            "prov": f["prov"], "fichier": f["fichier"]} for f in fichiers for o in f["lu"]["ops"]]
    ident = lambda o: o["genre"] + ":" + o["valeur"]
    mutation = lambda o: o["genre"] in MUTATIONS.values()
    meme = lambda a, b: a["prov"] == b["prov"] and a["fichier"].lower() == b["fichier"].lower()
    nprov = lambda l: len({o["prov"] for o in l})

    def par_valeur(l):
        d = collections.defaultdict(list)
        for o in l:
            d[o["valeur"]].append(o)
        return d

    def opposees(vs):                                # un retrait d'un fichier contre l'ajout de la même valeur par un autre
        ajouts = [o for o in vs if o["genre"] in AJOUTS and o["genre"] not in COPIES]
        return any(r["genre"] == "remove" and not any(meme(r, a) for a in ajouts) and any(not meme(r, a) for a in ajouts) for r in vs)

    sensible = lambda vs: nprov(vs) > 1 and any(o["genre"] in ("append", "prepend") for o in vs) and \
        any(o["genre"] in ("append-once", "prepend-once") for o in vs)
    doubles = lambda vs: nprov(vs) > 1 and sum(o["genre"] in ("append", "prepend") for o in vs) > 1 and all(o["genre"] in AJOUTS for o in vs)

    def classe(l):
        aff = [o for o in l if not mutation(o)]
        if any(opposees(vs) for vs in par_valeur(l).values()):
            if any(o["genre"] in ("type", "base") for o in aff):
                return "definition"
            if len({ident(o) for o in aff}) > 1:
                return "liste" if any(o["genre"] == "liste" for o in aff) else "valeur"
            return "oppose"
        ids = {ident(o) for o in l}
        if len(ids) == 1:
            return "doublon" if l[0]["genre"] in ("append", "prepend") else "identique"
        d = collections.defaultdict(list)
        for o in l:
            d[o["prov"]].append(ident(o))
        if len({"\n".join(sorted(v)) for v in d.values()}) == 1:
            return "doublon" if any(o["genre"] in ("append", "prepend") for o in l) else "identique"
        if any(o["genre"] in ("type", "base") for o in l):
            return "definition"
        if all(o["genre"] == "liste" for o in l):
            return "liste"
        if any(not mutation(o) and any(mutation(p) and p["prov"] != o["prov"] for p in l) for o in l):
            return "liste" if len({ident(o) for o in aff}) > 1 else "puis"
        pv = par_valeur(l).values()
        if any(sensible(vs) for vs in pv):
            return "liste"
        if any(doubles(vs) for vs in pv):
            return "doublon"
        return "compose" if all(mutation(o) for o in l) else "liste" if any(mutation(o) for o in l) else "valeur"

    def utiles(l, sorte):
        pv = par_valeur(l)
        if any(opposees(vs) for vs in pv.values()):
            if any(not mutation(o) for o in l):
                return l
            garde = {v for v, vs in pv.items() if opposees(vs) or sensible(vs) or doubles(vs)}
            return [o for o in l if o["valeur"] in garde]
        if sorte not in ("liste", "doublon") or all(o["genre"] == "liste" for o in l):
            return l
        if any(not mutation(o) and any(mutation(p) and p["prov"] != o["prov"] for p in l) for o in l):
            return l
        garde = {v for v, vs in pv.items() if (sensible if sorte == "liste" else doubles)(vs)}
        return [o for o in l if o["valeur"] in garde]

    par = collections.defaultdict(list)
    for o in ops:
        par[o["cible"]].append(o)
    out = []
    ligne = lambda o: {"prov": o["prov"], "fichier": o["fichier"], "ligne": o["ligne"], "valeur": o["valeur"][:300],
                       "geste": {"valeur": "=", "liste": "= liste", "inline": "= enregistrement", "type": "$type", "base": "$base"}.get(o["genre"], "!" + o["genre"])}
    for cible, l in par.items():
        if nprov(l) == 1 and not any(opposees(vs) for vs in par_valeur(l).values()):
            aff = [o for o in l if not mutation(o)]
            if len({ident(o) for o in aff}) <= 1:
                continue                             # mutations d'un seul mod : rien à dire
            if len({o["fichier"].lower() for o in aff}) == 1 or (all(o["genre"] == "valeur" for o in aff) and len({o["valeur"].lower() for o in aff}) == 1):
                sorte = "interne"
            else:
                sorte = "definition" if any(o["genre"] in ("type", "base") for o in aff) else \
                    "liste" if any(o["genre"] == "liste" for o in aff) else "valeur"
            vus = aff
        else:
            sorte = classe(l)
            vus = utiles(l, sorte)
        if nprov(vus) < 2 and sorte not in ("valeur", "liste", "doublon", "definition", "interne", "oppose"):
            continue
        t = {"voie": "tweak", "sorte": sorte, "cible": cible, "lignes": [ligne(o) for o in vus]}
        if sorte == "valeur":
            if any(o["genre"] != "valeur" or o.get("genere") or o.get("alias") for o in vus):
                t["gagnant"], t["raison"] = None, T("valeur générée (`$instances`) ou reprise d'une ancre : ordre non prévisible")
            else:
                g, t["raison"] = _ordre_sources(t["lignes"], True)
                t["gagnant"] = next((i for i, x in enumerate(t["lignes"]) if x is g), None)
        out.append(t)
    # une liste copiée (`!append-from`) qu'un autre mod change
    copies = collections.defaultdict(list)
    for o in ops:
        if o["genre"] in COPIES:
            copies[(o["cible"], o["valeur"])].append(o)
    for (cible, source), cs in copies.items():
        ecrits = [o for o in par.get(source, []) if any(o["prov"] != c["prov"] for c in cs)]
        if ecrits:
            out.append({"voie": "tweak", "sorte": "copie", "cible": f"{cible} <- {source}", "lignes": [ligne(o) for o in cs + ecrits]})
    return out, ops


def conflits_setflat(ecrits, ops):
    """écritures TweakDB littérales du code (Redscript, Lua de CET) face aux tweaks et au code d'un AUTRE mod, valeur différente"""
    def differe(a, b):
        try:
            return float(a) != float(b)
        except ValueError:
            return a.lower() != b.lower() if {a.lower(), b.lower()} <= {"true", "false"} else a != b

    par, tw = collections.defaultdict(list), collections.defaultdict(list)
    for e in ecrits:
        if e["valeur"] is not None:
            par[e["cible"]].append(e)
    for o in ops:
        if o["genre"] == "valeur" and o["cible"] in par:
            tw[o["cible"]].append(o)
    out = []
    for cible, es in par.items():
        face = [dict(o, geste="=") for o in tw.get(cible, [])] + [dict(e, geste=e["geste"] + "()") for e in es]
        vus = [x for x in face if any(y["prov"] != x["prov"] and differe(x["valeur"], y["valeur"]) and "(" in (x["geste"] + y["geste"]) for y in face)]
        if vus:
            out.append({"voie": "code", "sorte": "code", "cible": cible, "lignes": [
                {"prov": x["prov"], "fichier": x["fichier"], "ligne": x["ligne"], "geste": x["geste"], "valeur": x["valeur"][:300]} for x in vus]})
    return out


def voie_code(dest):
    """`reds`, `tweak`, `lua`, `red` (.tweak, non lu) ou None : ce que le jeu lit comme code à ce chemin"""
    d = dest.lower()
    if d.endswith(".reds"):
        if d.startswith("r6/scripts/"):
            return "reds"
        p = d.split("/")
        if p[:2] == ["red4ext", "plugins"] and ((len(p) >= 5 and p[2] in GREFFONS_REDS and p[3] == "scripts")
                                                or (len(p) == 4 and p[2] == "mod_settings" and p[3] in ("packed.reds", "module.reds"))):
            return "reds"
        return None
    if d.startswith("r6/tweaks/"):
        return "tweak" if d.endswith((".yaml", ".yml")) else "red" if d.endswith(".tweak") else None
    if d.startswith(_CET + "mods/") and d.endswith(".lua") and d.count("/") >= 6:
        return "lua"
    return None


def sources_code(index, plan, pose, jeu, store, data):
    """ce que le jeu lirait pour ce profil : [{prov, zip, fichier (destination), chemin (sur le disque ou None), voie, lu}].
    Les fichiers du jeu que ni le profil ni le registre ne tiennent comptent aussi, dits « hors Red Stack »."""
    path = os.path.join(data, "code.json")
    try:
        cache = json.load(open(path, encoding="utf-8"))
        cache = cache if cache.get("v") == CODE_V else {}
    except (OSError, ValueError):
        cache = {}
    neuf, out, zips = {"v": CODE_V}, [], {}

    def lit(voie, cle, octets_de):
        c = cache.get(cle)
        if c is None:
            try:
                t = octets_de().decode("utf-8-sig", "replace")
                c = lit_reds(t) if voie == "reds" else lit_lua(t) if voie == "lua" else lit_tweak(t)
            except YamlErreur as e:
                c = {"erreur": str(e)}
            except (OSError, KeyError, zipfile.BadZipFile) as e:
                return {"erreur": T("illisible : {0}", e)}
        neuf[cle] = c
        return c

    vus = set()
    for dl, (key, e, dest) in plan["final"].items():
        voie = voie_code(dest)
        if not voie:
            continue
        vus.add(dl)
        mod, chemin = index[key], None
        if jeu.same(dest, e["c"], e["s"]):
            chemin = jeu.path(dest)
        elif store and store.a_jour(mod) and os.path.isfile(store.src(mod, e["n"])):
            chemin = store.src(mod, e["n"])
        row = {"prov": key, "zip": key, "fichier": dest, "chemin": chemin, "voie": voie}
        if voie != "red":
            def octets_de(mod=mod, e=e, chemin=chemin):
                if chemin:
                    return open(chemin, "rb").read()
                z = zips.get(mod["zip"]) or zips.setdefault(mod["zip"], zipfile.ZipFile(mod["zip"]))
                return z.read(e["n"])
            row["lu"] = lit(voie, f"{voie}:{e['c']:08x}:{e['s']}", octets_de)
        out.append(row)
    for z in zips.values():
        z.close()
    for base in ("r6/scripts", "r6/tweaks", "red4ext/plugins", _CET + "mods"):
        racine = jeu.path(base)
        for r, _, fs in os.walk(racine):
            for f in fs:
                if not f.lower().endswith(CODE_EXT_LUES):
                    continue
                p = os.path.join(r, f)
                dest = base + "/" + os.path.relpath(p, racine).replace(os.sep, "/")
                voie = voie_code(dest)
                if not voie or dest.lower() in vus or dest.lower() in pose:
                    continue
                reste = dest[len(base) + 1:].split("/")
                row = {"prov": "hors:" + (reste[0] if len(reste) > 1 else "(racine)"), "zip": None, "fichier": dest, "chemin": p, "voie": voie}
                if voie != "red":
                    st = os.stat(p)
                    row["lu"] = lit(voie, f"{voie}:{dest.lower()}:{st.st_size}:{st.st_mtime_ns}", lambda p=p: open(p, "rb").read())
                out.append(row)
    if neuf != cache:
        os.makedirs(data, exist_ok=True)
        json.dump(neuf, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    # un dossier de mod CET sans `init.lua` n'est pas chargé : son Lua ne compte pas
    actifs = {"/".join(s["fichier"].lower().split("/")[:6]) for s in out if s["voie"] == "lua" and s["fichier"].lower().endswith("/init.lua")
              and s["fichier"].count("/") == 6}
    return [s for s in out if s["voie"] != "lua" or "/".join(s["fichier"].lower().split("/")[:6]) in actifs]


def analyse_code(sources):
    """trouvailles et limites des sources de `sources_code`, classées : à regarder, à revoir, sans action, pour information"""
    limites = [{"prov": s["prov"], "fichier": s["fichier"],
                "quoi": T("fichier .tweak (format RED) : posé, pas analysé") if s["voie"] == "red" else s["lu"]["erreur"]}
               for s in sources if s["voie"] == "red" or "erreur" in s["lu"]]
    bons = [s for s in sources if s["voie"] != "red" and "erreur" not in s["lu"]]
    for s in bons:
        limites += [{"prov": s["prov"], "fichier": s["fichier"], "quoi": q} for q in s["lu"].get("limites", [])]
    reds = [s for s in bons if s["voie"] == "reds"]
    trouv, lim = conflits_redscript(reds)
    tw, ops = conflits_tweaks([s for s in bons if s["voie"] == "tweak"])
    modules = {m.lower() for s in reds for m in s["lu"]["modules"]}
    ecrits = []
    for s in bons:
        etat = [condition_vraie(e, non, modules) for e, non in s["lu"].get("conds", [])]
        ecrits += [dict(e, prov=s["prov"], fichier=s["fichier"]) for e in s["lu"].get("ecrits", [])
                   if all(etat[i] is True for i in e.get("si", []))]
    trouv += tw + conflits_setflat(ecrits, ops)
    rang = {"attention": 0, "revoir": 1, "info": 2, "rien": 3}
    for t in trouv:
        t["niveau"] = NIVEAUX.get(t["sorte"], "info" if t["sorte"] in INFOS else "rien")
        t["provs"] = sorted({l["prov"] for l in t["lignes"]})
    trouv.sort(key=lambda t: (rang[t["niveau"]], t["voie"], t["sorte"], t["cible"]))
    chemins = {s["fichier"].lower(): s["chemin"] for s in sources if s["chemin"]}
    for t in trouv:
        if t["niveau"] == "rien" and len(t["lignes"]) > 40:   # sans action : quarante lignes montrées, le reste compté
            t["plus"], t["lignes"] = len(t["lignes"]) - 40, t["lignes"][:40]
        for l in t["lignes"]:
            l["chemin"] = chemins.get(l["fichier"].lower())
    compte = collections.Counter(s["voie"] for s in sources)
    return trouv, limites + lim, {"reds": compte["reds"], "tweaks": compte["tweak"], "lua": compte["lua"], "red": compte["red"]}


# ---------------------------------------------------------------- objets des mods face à une sauvegarde de partie
# Lecture seule d'un `sav.dat` (format du jeu 2.0 et après, lu d'après WolvenKit.RED4/Save, licence MIT) : en-tête `CSAV`,
# blocs LZ4 (`4ZLX`) sous une table `FZLC`, table des nœuds `NODE` en fin de fichier. Le nœud `inventory` porte des
# sous-inventaires (identifiant, objets) ; chaque objet commence par son identifiant TweakDB sur 64 bits : CRC32 du nom
# de l'enregistrement, puis sa longueur sur 8 bits. La garde-robe (`WardrobeSystem`) garde les vêtements déjà portés,
# même vendus : leurs identifiants y sont cherchés tels quels. Rien n'est jamais écrit dans une sauvegarde.

INV_V, INV_PLANQUE = 0x1, 0xF4240                    # V, et la planque (le coffre des appartements, un seul pour tous)
LIEUX_OBJET = ("v", "planque", "garde_robe")
SORTES_OBJET = ("arme", "vetement", "implant", "accessoire", "module")   # accessoire = lunette, bouche ; module = mod d'équipement
M40 = 0xFFFFFFFFFF                                   # un identifiant TweakDB se compare sur ses 40 bits (CRC32 et longueur)
DOSSIER_PARTIES = os.path.join(os.path.expanduser("~"), "Saved Games", "CD Projekt Red", "Cyberpunk 2077")


class PartieErreur(ValueError):
    pass


def _lz4_bloc(src, taille):
    """un bloc LZ4 (format « block », sans cadre) ; `taille` = taille décompressée annoncée"""
    dst, i, n = bytearray(), 0, len(src)
    while i < n:
        jeton = src[i]
        i += 1
        lit = jeton >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        dst += src[i:i + lit]
        i += lit
        if i >= n:
            break
        dec = src[i] | (src[i + 1] << 8)
        i += 2
        lg = jeton & 15
        if lg == 15:
            while True:
                b = src[i]
                i += 1
                lg += b
                if b != 255:
                    break
        lg += 4
        if not 0 < dec <= len(dst):
            raise PartieErreur(T("bloc LZ4 illisible"))
        debut = len(dst) - dec
        if dec >= lg:
            dst += dst[debut:debut + lg]
        else:                                        # recouvrement : la copie relit ce qu'elle vient d'écrire
            while lg > 0:
                k = min(dec, lg)
                dst += dst[debut:debut + k]
                lg -= k
                debut += k
    if len(dst) != taille:
        raise PartieErreur(T("bloc LZ4 illisible"))
    return dst


def _vlq(b, p):
    x = b[p]
    p += 1
    neg, v = x & 0x80, x & 0x3F
    if x & 0x40:
        dec = 6
        while True:
            x = b[p]
            p += 1
            v |= (x & 0x7F) << dec
            dec += 7
            if not x & 0x80:
                break
    return (-v if neg else v), p


def _chaine(b, p):
    n, p = _vlq(b, p)
    if n > 0:
        return b[p:p + 2 * n].decode("utf-16-le", "replace"), p + 2 * n
    return b[p:p - n].decode("utf-8", "replace"), p - n


def tdbid(nom):
    """identifiant TweakDB d'un nom d'enregistrement (les 40 bits qu'une sauvegarde compare)"""
    o = nom.encode("utf-8")
    return zlib.crc32(o) | (len(o) << 32)


def _piece(b, p, out):
    """une pièce d'objet (ItemSlotPart d'après WolvenKit) et celles qu'elle porte : leurs identifiants dans `out`"""
    out.append(struct.unpack_from("<Q", b, p)[0] & M40)
    p += 16                                          # ItemID : identifiant, graine, structure, compteur, drapeaux
    _, p = _chaine(b, p)                             # apparence
    p += 8                                           # emplacement où elle se monte
    n, p = _vlq(b, p)
    for _ in range(n):
        p = _piece(b, p, out)
    return p + 4 + 16                                # inconnu, puis infos de butin (pool, inconnu, niveau requis)


def pieces_montees(b, p):
    """identifiants des pièces montées sur l'objet dont le nœud itemData commence en `p` (après l'index du nœud) :
    lunettes, bouches, mods d'armes, de vêtements, d'implants. L'objet lui-même n'y est pas."""
    ident, graine, forme = struct.unpack_from("<QIB", b, p)
    p += 16 + 1 + 4                                  # ItemID, drapeaux, date de création
    if forme & 2 or (forme == 0 and graine == 2):
        p += 4                                       # quantité
    out = []
    if forme & 1 or (forme == 0 and graine != 2):
        _piece(b, p + 16, out)                       # après les infos de butin : l'arbre des pièces, l'objet à sa racine
    return [i for i in out if i != ident & M40]


def lit_partie(chemin):
    """objets d'une sauvegarde : ({identifiant TweakDB : {"v", "planque", "monte"}}, octets de la garde-robe, version du
    jeu, objets dont les pièces n'ont pas pu se lire). « monte » : une pièce montée sur un objet de ce lieu (lunette sur
    une arme, mod sur un vêtement…).
    PartieErreur si le fichier n'est pas une sauvegarde que ce lecteur comprend."""
    try:
        f = open(chemin, "rb").read()
    except OSError as e:
        raise PartieErreur(T("illisible : {0}", e))
    try:
        if f[:4] != b"VASC" or f[-4:] != b"ENOD":
            raise PartieErreur(T("pas une sauvegarde de Cyberpunk 2077"))
        version = struct.unpack_from("<I", f, 8)[0]
        if version < 2000:
            raise PartieErreur(T("sauvegarde d'une version du jeu d'avant la 2.0 : format non lu"))
        info = struct.unpack_from("<i", f, len(f) - 8)[0]
        if f[info:info + 4] != b"EDON":
            raise PartieErreur(T("table des nœuds introuvable"))
        p = info + 4
        nb, p = _vlq(f, p)
        noeuds = []
        for _ in range(nb):
            nom, p = _chaine(f, p)
            noeuds.append((nom,) + struct.unpack_from("<iiii", f, p))
            p += 16
        t = f.find(b"FZLC")
        if t < 0:
            raise PartieErreur(T("table de compression introuvable"))
        blocs = [struct.unpack_from("<iii", f, t + 8 + 12 * k) for k in range(struct.unpack_from("<i", f, t + 4)[0])]
        data = bytearray(f[:blocs[0][0]])           # même espace d'adresses que les positions des nœuds
        for off, taille, dec in blocs:
            data += _lz4_bloc(f[off + 8:off + taille], dec) if f[off:off + 4] == b"4ZLX" else f[off:off + taille]
        inv = next((n for n in noeuds if n[0] == "inventory"), None)
        if inv is None:
            raise PartieErreur(T("inventaire introuvable"))
        _, _, _, off, taille = inv
        items = [n for n in noeuds if n[0] == "itemData" and off <= n[3] < off + taille]
        objets, k, p, illisibles = collections.defaultdict(set), 0, off + 8, 0   # identifiant du nœud, puis nombre de sous-inventaires
        for _ in range(struct.unpack_from("<i", data, off + 4)[0]):
            ident, nb = struct.unpack_from("<QI", data, p)
            p += 12
            lieu = "v" if ident == INV_V else "planque" if ident == INV_PLANQUE else None
            for _ in range(nb):                      # tête de l'objet (identifiant TweakDB d'abord), puis son nœud itemData
                if lieu:
                    objets[struct.unpack_from("<Q", data, p)[0] & M40].add(lieu)
                    try:
                        for i in pieces_montees(data, items[k][3] + 4):
                            objets[i] |= {lieu, "monte"}
                    except (struct.error, IndexError):
                        illisibles += 1              # ses pièces seules restent hors compte, l'objet lui-même est lu
                p = items[k][3] + items[k][4]
                k += 1
        gr = next((n for n in noeuds if n[0] == "WardrobeSystem"), None)
        return objets, bytes(data[gr[3]:gr[3] + gr[4]]) if gr else b"", version, illisibles
    except (struct.error, IndexError, StopIteration):
        raise PartieErreur(T("structure non comprise"))


def parties(dossier):
    """les sauvegardes du dossier, la plus récente d'abord : nom, chemin, date, et ce que leur `metadata` en dit"""
    out = []
    try:
        noms = os.listdir(dossier)
    except OSError:
        return out
    for nom in noms:
        d = os.path.join(dossier, nom)
        sav = os.path.join(d, "sav.dat")
        if not os.path.isfile(sav):
            continue
        st = os.stat(sav)
        r = {"nom": nom, "chemin": sav, "date": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
             "octets": st.st_size}
        for m in sorted(x for x in os.listdir(d) if x.startswith("metadata.") and x.endswith(".json")):
            try:
                md = json.load(open(os.path.join(d, m), encoding="utf-8"))["Data"]["metadata"]
                r.update(niveau=int(md.get("level") or 0), vie=md.get("lifePath") or "", duree=int(md.get("playTime") or 0),
                         partie=md.get("playthroughID") or "", jeu=md.get("gameVersion") or 0)
            except (OSError, ValueError, KeyError, TypeError):
                pass
        out.append(r)
    return sorted(out, key=lambda r: r["date"], reverse=True)


# Sorte d'un objet : d'abord ce que l'enregistrement dit de lui (itemType, equipArea, placementSlots, itemCategory), le sien
# ou celui d'une base écrite par un mod ; puis son `$type` ; puis, pour une base du jeu, ce que la TweakDB du jeu en dit
# (`r6/cache/tweakdb.bin`) ; sans elle, le nom de la base, par familles de noms. Ce qui ne se classe pas (pièces internes
# d'une arme, programmes, recettes, apparences, PNJ…) n'est pas un objet pour cette vue. Les pièces passent avant les
# implants : un mod d'implant (`Prt_Fragment`) porte aussi la catégorie des implants.
PROPS_OBJET = ("itemType", "equipArea", "placementSlots", "itemCategory")
RX_SORTE_PROPS = (("accessoire", re.compile(r"ItemType\.Prt_\w*(Scope|Muzzle)\b|AttachmentSlots\.(Scope|PowerModule)\b")),
                  ("module", re.compile(r"ItemType\.Prt_(\w*Mod|\w*FabricEnhancer|Fragment)\b|ItemCategory\.WeaponMod\b"
                                        r"|AttachmentSlots\.\w*(WeaponMod|FabricEnhancer)")),
                  ("implant", re.compile(r"ItemType\.(Cyb_|Cyberware\b)|EquipmentArea\.\w*CW\b|ItemCategory\.Cyberware\b")),
                  ("arme", re.compile(r"ItemType\.(Wea_|Gad_Grenade)|EquipmentArea\.Weapon|ItemCategory\.Weapon\b")),
                  ("vetement", re.compile(r"ItemType\.Clo_|OutfitSlots\.|EquipmentArea\.(Head|Face|OuterChest|InnerChest|Legs|Feet|Outfit)\b|ItemCategory\.Clothing\b")))
TYPES_OBJET = {"WeaponItem": "arme", "Grenade": "arme", "Clothing": "vetement"}
RX_SORTE_BASE = (("accessoire", re.compile(r"^Items\.w_(att_scope|silencer|att_muzzle)")),
                 ("module", re.compile(r"^Items\.\w*(WeaponMod|FabricEnhancer)\d*$")),
                 ("arme", re.compile(r"^Items\.(Preset_|Base_|Grenade)")),
                 ("vetement", re.compile(r"^Items\.(Generic\w*Clothing$|Outfit$|[A-Za-z]+_\d\d_[A-Za-z]+_\d\d)")),
                 ("implant", re.compile(r"^Items\.(Advanced|Berserk|Sandevistan|Kiroshi|\w*Cyberdeck|\w*Netdriver)")))
RX_SOUS_ENREG = re.compile(r"_inline\d+$")

# TweakDB du jeu, d'après `WolvenKit.RED4/TweakDB/TweakDBReader.cs` (MIT) : en-tête, puis des flats rangés par type de
# valeur (hachage FNV-1a 64 du nom du type ; valeurs, puis clés « identifiant du flat → rang de la valeur »), puis les
# enregistrements (identifiant, hachage Murmur3 du nom de leur type, graine 0x5EEDBA5E). Les noms n'y sont pas : on
# compare des identifiants, ceux des quelques noms dont le tri a besoin (catégories, sortes de pièces, zones d'équipement).
TWEAKDB = "r6/cache/tweakdb.bin"
NOMS_TDB = (["ItemCategory." + x for x in ("Weapon", "Clothing", "Cyberware", "WeaponMod")]
            + ["ItemType." + x for x in ("Gad_Grenade", "Cyberware", "Cyb_Ability", "Cyb_Launcher", "Cyb_MantisBlades", "Cyb_NanoWires",
                                         "Cyb_StrongArms", "Cyb_HealingAbility", "Prt_Mod", "Prt_Fragment", "Prt_FabricEnhancer",
                                         "Prt_Muzzle", "Prt_HandgunMuzzle", "Prt_RifleMuzzle", "Prt_ShortScope", "Prt_LongScope",
                                         "Prt_TechSniperScope", "Prt_PowerSniperScope", "Prt_HandgunMod", "Prt_AR_SMG_LMGMod",
                                         "Prt_Precision_Sniper_RifleMod", "Prt_MeleeMod", "Prt_BladeMod", "Prt_BluntMod",
                                         "Prt_ThrowableMod", "Prt_ShotgunMod", "Prt_RangedMod", "Prt_HeadFabricEnhancer",
                                         "Prt_FaceFabricEnhancer", "Prt_OuterTorsoFabricEnhancer", "Prt_TorsoFabricEnhancer",
                                         "Prt_PantsFabricEnhancer", "Prt_BootsFabricEnhancer")]
            + ["EquipmentArea." + x for x in ("Weapon", "InnerChest", "Feet", "Outfit", "HandsCW", "ArmsCW", "EyesCW",
                                              "FrontalCortexCW", "SystemReplacementCW", "NervousSystemCW", "CardiovascularSystemCW",
                                              "IntegumentarySystemCW", "LegsCW", "MusculoskeletalSystemCW")])


def _murmur3(data, graine):
    c1, c2, h, n = 0xCC9E2D51, 0x1B873593, graine, len(data)
    rot = lambda x, r: ((x << r) | (x >> (32 - r))) & 0xFFFFFFFF
    for i in range(0, n - n % 4, 4):
        h ^= (rot((struct.unpack_from("<I", data, i)[0] * c1) & 0xFFFFFFFF, 15) * c2) & 0xFFFFFFFF
        h = (rot(h, 13) * 5 + 0xE6546B64) & 0xFFFFFFFF
    reste = int.from_bytes(data[n - n % 4:], "little")
    if n % 4:
        h ^= (rot((reste * c1) & 0xFFFFFFFF, 15) * c2) & 0xFFFFFFFF
    h ^= n
    h = ((h ^ (h >> 16)) * 0x85EBCA6B) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
    return h ^ (h >> 16)


def _fnv1a64(texte):
    h = 0xCBF29CE484222325
    for b in texte.encode():
        h = ((h ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def lit_tweakdb(racine_jeu):
    """sorte des enregistrements du jeu, à la demande : une fonction nom → sorte (ou None), ou None si la TweakDB du jeu
    manque ou ne se lit pas (le tri retombe alors sur les familles de noms)"""
    try:
        f = open(os.path.join(racine_jeu, *TWEAKDB.split("/")), "rb").read()
        magie, _, _, _, flats, recs, _, _ = struct.unpack_from("<IIIIiiii", f, 0)
        if magie != 0x0BB1DB47:
            return None
        n = struct.unpack_from("<i", f, recs)[0]
        types = {i & M40: t for i, t in struct.iter_unpack("<QI", f[recs + 4:recs + 4 + 12 * n])}
        valeurs = {}
        for th, nv, nk, off in (struct.unpack_from("<QIII", f, flats + 4 + 20 * i) for i in range(struct.unpack_from("<i", f, flats)[0])):
            if th == _fnv1a64("TweakDBID"):
                v = struct.unpack_from(f"<{nv}Q", f, off + 4)
                p = off + 8 + 8 * nv
                valeurs = {k & M40: v[r] & M40 for k, r in struct.iter_unpack("<Qi", f[p:p + 12 * nk])}
    except (OSError, struct.error, IndexError):
        return None
    noms = {tdbid(x): x for x in NOMS_TDB}
    sortes_type = {_murmur3(t.encode(), 0x5EEDBA5E): s for t, s in TYPES_OBJET.items()}

    def sorte(nom):
        i = tdbid(nom)
        if i not in types:
            return "inconnu"                         # pas un enregistrement du jeu : la famille de noms décide
        dit = " ".join(noms.get(valeurs.get(tdbid(f"{nom}.{p}")), "") for p in PROPS_OBJET)
        return next((k for k, rx in RX_SORTE_PROPS if rx.search(dit)), None) or sortes_type.get(types[i])
    return sorte


def objets_des_tweaks(sources, sorte_jeu=None):
    """objets (armes, vêtements, implants, accessoires d'armes, mods d'équipement) que les tweaks lus créent :
    ({prov : [{rec, sorte, fichier, chemin, ligne}]}, non classés). `sorte_jeu` : la TweakDB du jeu (lit_tweakdb)."""
    defs, props, ou = {}, collections.defaultdict(dict), collections.defaultdict(list)
    for s in sources:
        if s["voie"] != "tweak" or "erreur" in s.get("lu", {"erreur": 1}):
            continue
        for cible, valeur, genre, ligne, _ in s["lu"]["ops"]:
            if cible.endswith(".$definition") and genre in ("type", "base"):
                rec = cible[:-len(".$definition")]
                defs.setdefault(rec, (genre, valeur))
                ou[rec].append((s["prov"], s["fichier"], s["chemin"], ligne))
            else:
                rec, _, p = cible.rpartition(".")
                if p in PROPS_OBJET:
                    props[rec][p] = valeur

    memo = {}

    def sorte(rec, vus=()):
        if rec in memo:
            return memo[rec]
        s = next((k for k, rx in RX_SORTE_PROPS if rx.search(" ".join(props.get(rec, {}).values()))), None)
        if s is None and rec not in vus:
            genre, v = defs.get(rec, (None, ""))
            if genre == "type":
                s = TYPES_OBJET.get(v.replace("gamedata", "").replace("_Record", ""))
            elif genre == "base" and v in defs:
                s = sorte(v, vus + (rec,))
            elif genre == "base" and not RX_SOUS_ENREG.search(v):
                s = sorte_jeu(v) if sorte_jeu else "inconnu"
                if s == "inconnu":
                    s = next((k for k, rx in RX_SORTE_BASE if rx.search(v)), None)
        memo[rec] = s
        return s

    par, hors = collections.defaultdict(list), 0
    for rec in defs:
        s = None if RX_SOUS_ENREG.search(rec) else sorte(rec)
        if s is None:
            hors += 1
            continue
        for prov in dict.fromkeys(o[0] for o in ou[rec]):
            _, fichier, chemin, ligne = next(o for o in ou[rec] if o[0] == prov)
            par[prov].append({"rec": rec, "sorte": s, "fichier": fichier, "chemin": chemin, "ligne": ligne})
    return par, hors


def objets_face_partie(par, objets, garde_robe):
    """chaque mod, ses objets et où la sauvegarde les tient ; les mods sans objet possédé d'abord"""
    mods = []
    for prov, recs in par.items():
        for r in recs:
            i = tdbid(r["rec"])
            r["lieux"] = [l for l in LIEUX_OBJET if l in objets.get(i, ())
                          or (l == "garde_robe" and garde_robe and struct.pack("<Q", i) in garde_robe)]
            r["monte"] = "monte" in objets.get(i, ())    # monté sur un objet (lunette sur une arme…), peut-être aussi rangé seul
        recs.sort(key=lambda r: (SORTES_OBJET.index(r["sorte"]), not r["lieux"], r["rec"].lower()))
        compte = {s: [sum(1 for r in recs if r["sorte"] == s and r["lieux"]), sum(1 for r in recs if r["sorte"] == s)] for s in SORTES_OBJET}
        mods.append({"prov": prov, "objets": recs, "possedes": sum(1 for r in recs if r["lieux"]), "total": len(recs),
                     "sortes": {s: c for s, c in compte.items() if c[1]}})
    mods.sort(key=lambda m: (m["possedes"] > 0, m["possedes"] / m["total"], m["prov"].lower()))
    return mods


# ---------------------------------------------------------------- configuration

CHEMINS =("depot", "jeu", "magasin", "sauvegardes", "reference", "journal",
          "wolvenkit", "atelier", "parties")        # parties : dossier des sauvegardes du jeu ; volet WolvenKit (red_stack_wk_mcp.py) : la CLI, et le seul dossier où il écrit


def conf_fixe(conf, neuf):
    """écrit dans `conf` les clés de `neuf` après contrôle ; une chaîne vide ou une liste vide rend le défaut"""
    if not isinstance(neuf, dict):
        sys.exit(T("config --fixe : un objet JSON est attendu"))

    def liste(k, v):
        if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
            sys.exit(T("config --fixe : {0} = liste de textes", k))

    propre = lambda v: list(dict.fromkeys(x.strip() for x in v if x.strip()))
    for k, v in neuf.items():
        if k in CHEMINS:
            if not isinstance(v, str):
                sys.exit(T("config --fixe : {0} = un chemin (texte)", k))
            if v.strip():
                conf[k] = os.path.abspath(v.strip())
            else:
                conf.pop(k, None)
        elif k == "convention":
            if not isinstance(v, dict) or set(v) - set(CONVENTION):
                sys.exit(T("config --fixe : convention = objet aux clés {0}", ', '.join(CONVENTION)))
            cur = conf.setdefault("convention", {})
            for ck, cv in v.items():
                liste("convention." + ck, cv)
                cur[ck] = propre(cv)
            if not cur.get("piles", CONVENTION["piles"]):
                sys.exit(T("config --fixe : convention.piles ne peut pas être vide (aucun dossier ne serait une pile)"))
        elif k in ("reglages", "hors"):
            liste(k, v)
            conf[k] = propre(x.replace("\\", "/").strip("/").lower() for x in v)
        elif k == "reference_exclus":
            liste(k, v)
            conf[k] = propre(v) or list(REF_EXCLUS)
        elif k == "contenu":                         # habitudes de renommage du contenu des zips (voir CONTENU)
            if not isinstance(v, dict) or set(v) - set(CONTENU):
                sys.exit(T("config --fixe : contenu = objet aux clés {0}", ', '.join(CONTENU)))
            cur = conf.setdefault("contenu", {})
            for ck, cv in v.items():
                if ck == "prefixes":
                    if not (isinstance(cv, dict) and all(isinstance(x, str) and x.strip() for kv in cv.items() for x in kv)):
                        sys.exit(T("config --fixe : contenu.prefixes = objet « début du nom du zip » -> « préfixe des fichiers »"))
                    if any(INTERDITS.search(x) or " " in x for x in cv.values()):
                        sys.exit(T("config --fixe : contenu.prefixes : un préfixe de fichier ne porte ni espace ni caractère interdit"))
                    cur[ck] = dict(cv)
                else:
                    liste("contenu." + ck, cv)
                    cur[ck] = propre(cv)
        elif k == "nouveaux_actifs":
            if not isinstance(v, bool):
                sys.exit(T("config --fixe : nouveaux_actifs = true ou false"))
            conf[k] = v
        elif k == "avant_applique":
            liste(k, v)
            conf[k] = [x for x in v if x.strip()]
        elif k == "maj_ignores":                     # mods dont les mises à jour Nexus ne sont plus proposées (`modId|radical`)
            liste(k, v)
            conf[k] = sorted(propre(v))
        else:
            sys.exit(T("config --fixe : clé inconnue « {0} »", k))


def conf_view(conf, data, conf_path):
    """la configuration telle que la page de réglages la montre : valeurs écrites, défauts, chemins effectifs"""
    jeu = conf.get("jeu", "")
    eff = {"magasin": conf.get("magasin") or (jeu.rstrip("\\/") + " - Red Stack" if jeu else ""),
           "sauvegardes": conf.get("sauvegardes") or os.path.join(data, "sauvegardes"),
           "reference": conf.get("reference") or (jeu.rstrip("\\/") + " - Référence" if jeu else ""),
           "journal": conf.get("journal") or os.path.join(data, "red_stack.log"),
           "parties": conf.get("parties") or DOSSIER_PARTIES}
    return {"fichier": conf_path, "donnees": data, **{k: conf.get(k, "") for k in CHEMINS}, "effectif": eff,
            "existe": {"depot": os.path.isdir(conf.get("depot", "") or "?"), "jeu": os.path.isdir(jeu or "?"),
                       "magasin": os.path.isdir(eff["magasin"] or "?"),
                       "reference": os.path.isfile(os.path.join(eff["reference"] or "?", REF_MARK)),
                       "wolvenkit": any(os.path.isfile(p) for p in (conf.get("wolvenkit") or "?", os.path.join(conf.get("wolvenkit") or "?", "WolvenKit.CLI.exe"))),
                       "atelier": os.path.isdir(conf.get("atelier") or "?"),
                       "parties": os.path.isdir(conf.get("parties") or DOSSIER_PARTIES)},
            "adopte": bool(jeu) and os.path.isfile(Jeu(jeu, data).pose_path),
            "convention": {k: list(v) for k, v in CONV.items()}, "convention_defaut": CONVENTION,
            "reglages": conf["reglages"], "reglages_defaut": REGLAGES, "hors": conf["hors"],
            "reference_exclus": conf.get("reference_exclus", REF_EXCLUS), "avant_applique": conf.get("avant_applique", []),
            "nouveaux_actifs": bool(conf.get("nouveaux_actifs")), "maj_ignores": conf.get("maj_ignores", []), "contenu": {**CONTENU, **conf.get("contenu", {})},
            "veille": veille(conf, data),
            "ecarts": ecarts_du_depot(conf["depot"]) if os.path.isdir(conf.get("depot") or "?") else None}


def veille(conf, data):
    """ce que l'extension surveille pour relire seule : des dossiers (la liste de leurs fichiers) et des fichiers isolés.
    Les caches du moteur n'y sont pas : il les écrit à chaque lecture."""
    depot, jeu = conf.get("depot", ""), conf.get("jeu", "")
    dossiers, fichiers = [], [os.path.join(data, "config.json")]
    if depot and os.path.isdir(depot):
        dossiers += [depot] + [p for _, _, p in lieux_du_depot(depot)]
    if jeu:
        dossiers.append(os.path.join(jeu, "archive", "pc", "mod"))
        fichiers.append(Jeu(jeu, data).pose_path)
    dossiers.append(os.path.join(data, "profils"))
    return {"dossiers": dossiers, "fichiers": fichiers}


# ---------------------------------------------------------------- historique
# Une ligne JSON par geste qui écrit (le jeu par « applique », le dépôt par parquer, remonter, renommer, convertir,
# récrire un contenu), dans `historique.jsonl` du dossier des données : lisible par un agent, filtrable par `journal`.
# Le journal texte (une ligne par fichier) reste écrit à côté.

def historise(data, geste, **faits):
    os.makedirs(data, exist_ok=True)
    with open(os.path.join(data, "historique.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"date": datetime.datetime.now().isoformat(timespec="seconds"), "geste": geste, **faits},
                           ensure_ascii=False) + "\n")


def lit_historique(data):
    p, out = os.path.join(data, "historique.jsonl"), []
    if os.path.isfile(p):
        for ligne in open(p, encoding="utf-8"):
            try:
                out.append(json.loads(ligne))
            except ValueError:                       # ligne coupée par un arrêt en cours d'écriture : sautée
                continue
    return out


def mods_du_plan(plan, avant, apres):
    """par mod, ce qu'un « applique » a fait : posé (rien de lui avant), retiré (plus rien après), mis à jour (un zip du
    même mod, dans la même pile, a quitté le registre au même moment), sinon modifié"""
    par = collections.defaultdict(collections.Counter)
    for k in ("pose", "remplace", "retire", "lie", "delie"):
        for row in plan[k]:
            par[row["zip"]][k] += 1
    nom = lambda cle: cle.split("/")[-1]
    partis = [k for k in avant if not apres.get(k)]
    mods = []
    for key in sorted(par):
        av, ap = avant.get(key, 0), apres.get(key, 0)
        m = {"cle": key, "version": version(nom(key)), "fait": "posé" if not av and ap else "retiré" if av and not ap else "modifié",
             **par[key]}
        if m["fait"] == "posé":
            vieux = [k for k in partis if k != key and k.split("/")[0] == key.split("/")[0] and ident(nom(k)) == ident(nom(key))]
            if len(vieux) == 1:
                m.update(fait="mis à jour", depuis=version(nom(vieux[0])) or nom(vieux[0]))
        mods.append(m)
    return mods


# ---------------------------------------------------------------- commandes

# ---------------------------------------------------------------- convention des noms de zips
# Un zip téléchargé par le bouton du site Nexus s'appelle `Nom-<modId>-<version, points en tirets>-<horodatage Unix>.zip` :
# c'est la forme que l'outil lit partout (identité d'un mod, version, lien Nexus). L'application Nexus livre
# `Nom <modId> <version> <AAAA-MM-JJTHH-MMZ> <id>.zip` : l'horodatage exact se lit par l'API publique de Nexus (fichier du
# mod publié dans la minute du nom ; départage par version, par taille, puis par mots). `convention` PROPOSE, rien de plus :
# l'utilisateur retouche ou valide chaque nom, et `--fixe … --go` renomme. Ce qui suit deux espaces en fin de nom est une
# annotation de l'utilisateur (`  EDITED`), gardée.
RX_WEB = re.compile(r"^(?P<name>.+?)-(?P<mod>\d{1,6})-(?:(?P<ver>.*?)-)?(?P<ts>\d{10})(?P<tail>[^.]*)\.(?P<ext>[A-Za-z0-9]+)$")
RX_APP = re.compile(r"^(?P<name>.+?)[ -]?(?P<mod>\d{3,6}) (?P<ver>\S+) (?P<d>\d{4}-\d{2}-\d{2})T(?P<h>\d{2})-(?P<mi>\d{2})Z "
                    r"(?P<id>[^\s.]+)(?P<tail> {2,}.*?)?\.(?P<ext>[A-Za-z0-9]+)$")
NEXUS_JEU = 3333                                     # cyberpunk2077
NEXUS_FRAIS = 6 * 3600                               # durée de vie du cache des fichiers d'un mod
AUTRES_ARCHIVES = (".7z", ".rar")
INTERDITS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def nexus_fichiers(mods, data, frais=False, complet=False, requis=False):
    """({modId: [fichier Nexus]}, erreur ou None) ; cache `nexus.json` du dossier des données.
    `complet` (mises à jour) : un mod mis en cache avant la 0.12.0, sans catégorie de fichier, est relu.
    `requis` (mises à jour, prérequis) : un mod mis en cache avant la 1.1.0, sans ses prérequis, est relu aussi. La même requête rend les prérequis déclarés par l'auteur
    (`requis` de chaque mod du cache, `None` si Nexus ne connaît plus ce mod) : aucun appel de plus."""
    import urllib.request
    path = os.path.join(data, "nexus.json")
    try:
        cache = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    now = datetime.datetime.now().timestamp()
    api, tetes = f"{NEXUS_BASE}/v2/graphql", ["Application-Name: Red Stack", "Application-Version: " + str(version_outil())]
    perime = lambda c: (now - c.get("lu", 0) > NEXUS_FRAIS or (complet and any("category" not in f for f in c.get("fichiers") or []))
                        or (requis and "requis" not in c and now - c.get("requis_lu", 0) > NEXUS_FRAIS))
    todo = sorted(m for m in mods if frais or perime(cache.get(str(m), {})))
    err = None
    for i in range(0, len(todo), 20):
        lot = todo[i:i + 20]
        q = " ".join(f"m{m}: modFiles(modId: {m}, gameId: {NEXUS_JEU}) {{ fileId name version category date uri sizeInBytes }}" for m in lot)
        # prérequis : par la liste `legacyMods`, qui passe sous silence un mod retiré du site (`mod(…)` ferait échouer le lot)
        q += (f" req: legacyMods(count: {len(lot)}, ids: [" + ", ".join(f"{{gameId: {NEXUS_JEU}, modId: {m}}}" for m in lot) + "]) { nodes { modId name"
              " modRequirements { nexusRequirements { nodes { modId modName notes externalRequirement url gameId } }"
              " dlcRequirements { gameExpansion { name } notes } } } }")
        corps = json.dumps({"query": "{ " + q + " }"}).encode()
        try:
            curl = shutil.which("curl")              # curl d'abord : il lit le magasin de certificats du système
            if curl:
                p = subprocess.run([curl, "-sS", "--fail", "-m", "40", api, "-H", "Content-Type: application/json",
                                    *(x for t in tetes for x in ("-H", t)),
                                    "-A", "red-stack", "--data-binary", "@-"], input=corps, capture_output=True)
                if p.returncode:
                    raise OSError(p.stderr.decode("utf-8", "replace").strip() or T("curl, code {0}", p.returncode))
                d = json.loads(p.stdout.decode("utf-8"))
            else:
                req = urllib.request.Request(api, corps, {"Content-Type": "application/json", "User-Agent": "red-stack",
                                                          **dict(t.split(": ", 1) for t in tetes)})
                with urllib.request.urlopen(req, timeout=40) as r:
                    d = json.loads(r.read().decode("utf-8"))
        except Exception as e:                       # hors ligne, API en panne : les noms restent à trancher à la main
            err = T("Nexus injoignable ({0})", e)
            break
        if d.get("errors"):
            err = "Nexus : " + "; ".join(str(x.get("message", x)) for x in d["errors"][:3])
        req = (d.get("data") or {}).get("req")
        lus = {int(n["modId"]): n for n in (req or {}).get("nodes") or []}
        for m in lot:
            fl = (d.get("data") or {}).get(f"m{m}")
            if fl is not None:
                cache[str(m)] = {"lu": now, "fichiers": fl}
                if req is None:                      # prérequis pas rendus (panne, serveur d'essai) : redemandés plus tard
                    cache[str(m)]["requis_lu"] = now
                else:
                    cache[str(m)].update(requis_de_nexus(lus.get(m)))
    if todo:
        os.makedirs(data, exist_ok=True)
        json.dump(cache, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return {m: cache.get(str(m), {}).get("fichiers") for m in mods}, err


# ---------------------------------------------------------------- prérequis

# Ce qu'un mod exige pour marcher, lu à deux sources. (1) Nexus : la liste que l'auteur déclare sur la page du mod (cache
# `nexus.json`, remplie par la lecture des mises à jour ou par `prerequis --nexus`) ; elle peut être incomplète ou périmée,
# et ne porte aucune version minimale, seulement une note libre. (2) Les fichiers du zip : un cadre (« framework ») se
# déduit de la place de ce que le mod pose, sans Nexus, donc aussi pour un mod sans modId. Un cadre est tenu pour présent
# si un zip actif du profil le livre, ou si son fichier témoin est dans le jeu sans que Red Stack l'ait posé.
# (code, nom, modId Nexus, fichier témoin dans le jeu, (début, fins) des destinations qui en ont besoin)
_CETM = _CET + "mods/"
CADRES = (
    ("cet", "Cyber Engine Tweaks", 107, "bin/x64/plugins/cyber_engine_tweaks.asi", ((_CETM, (".lua",)),)),
    ("red4ext", "RED4ext", 2380, "red4ext/red4ext.dll", (("red4ext/plugins/", (".dll",)),)),
    ("redscript", "redscript", 1511, "engine/tools/scc_lib.dll", (("r6/scripts/", (".reds",)),)),
    ("tweakxl", "TweakXL", 4197, "red4ext/plugins/tweakxl/tweakxl.dll", (("r6/tweaks/", (".yaml", ".yml", ".tweak")),)),
    ("archivexl", "ArchiveXL", 4198, "red4ext/plugins/archivexl/archivexl.dll", (("archive/pc/mod/", (".xl",)), ("red4ext/plugins/", (".xl",)))),
    ("codeware", "Codeware", 7780, "red4ext/plugins/codeware/codeware.dll", ()),
    ("input_loader", "Input Loader", 4575, "red4ext/plugins/input_loader/input_loader.dll", (("r6/input/", (".xml",)),)),
    ("audioware", "Audioware", 12001, "red4ext/plugins/audioware/audioware.dll", (("r6/audioware/", ("",)),)),
    ("mod_settings", "Mod Settings", 4885, "red4ext/plugins/mod_settings/mod_settings.dll", ()),
    ("native_settings", "Native Settings UI", 3518, _CETM + "nativesettings/init.lua", ()),
    ("redmod", "REDmod", 0, "tools/redmod/bin/redmod.exe", (("mods/", ("/info.json",)),)),
)
CADRE_DU_MOD = {c[2]: c[0] for c in CADRES if c[2]}
EXTENSION_JEU = "archive/pc/ep1"                     # dossier de Phantom Liberty : le seul contenu payant qu'un mod peut exiger
MANQUES = ("coupé", "rangé", "absent")               # états d'un prérequis qui laissent un mod actif sans ce qu'il exige
# Sur Nexus un auteur range sous « requirements » aussi ce qu'il conseille : la note libre est seule à le dire. Trois
# niveaux pour un prérequis qui n'est pas là : un cadre (ferme, le mod ne se charge pas), un mod déclaré sans réserve
# (« à voir »), un mod dont la note dit le caractère facultatif (« optionnel », jamais compté comme un défaut).
RX_OPTIONNEL = re.compile(r"option|recommend|suggest|soft|not\s+(strictly\s+|really\s+)?(required|necessary|needed|mandatory)|n[o']t\s+need"
                          r"|\bif\s+(you|using|used|installed|needed|desired)|\bonly\s+(if|for|required|needed|when)|\bwhen\s+using|compatib"
                          r"|add-?on|this\s+or\b|\bor\s+(this|the|any|another)\b|use\s+one|either|nice\s+to|for\s+the\s+\S+(\s+\S+)?\s+(option|version|variant|refit)"
                          r"|facultati|optionnel|conseill|empfohlen|opcional|recomend", re.I)


def dit_etat(code):
    """état d'un prérequis dit en mode texte : trois codes ont une phrase à eux, les autres sont ceux de la liste des mods"""
    return {"dans le jeu": T("dans le jeu, hors Red Stack"), "rangé": T("rangé, pas dans une pile"),
            "externe": T("hors Nexus, non contrôlé")}.get(code) or C(code)


def requis_de_nexus(n):
    """ce que le cache garde des prérequis d'un mod lu sur Nexus (`n` : son nœud `legacyMods`, None si Nexus ne le rend pas)"""
    if not n:
        return {"requis": None}
    r = n.get("modRequirements") or {}
    ici = lambda x: str(x.get("gameId")) == str(NEXUS_JEU) and not x.get("externalRequirement")
    return {"titre": n.get("name") or "",
            "requis": [{"mod": int(x.get("modId") or 0) if ici(x) else 0, "nom": x.get("modName") or "",
                        "notes": (x.get("notes") or "").strip()[:300], "url": x.get("url") or ""}
                       for x in (r.get("nexusRequirements") or {}).get("nodes") or []],
            "dlc": [{"nom": (x.get("gameExpansion") or {}).get("name") or "", "notes": (x.get("notes") or "").strip()[:300]}
                    for x in r.get("dlcRequirements") or []]}


def qui_requiert(nom):
    """identité d'un mod pour ses prérequis ignorés : son modId, sinon le radical de son nom ; elle tient d'une version à l'autre"""
    radical, mid = ident(nom)
    return mid or radical


def prerequis(index, prof, jeu, data, ignores=None):
    """({clé: {nexus, requis: [...], requis_par: [clés], manque}}, [cadres]) pour tout zip qui n'est pas retiré. Lecture
    seule, sans réseau : Nexus est lu dans son cache. Un prérequis : {cadre, mod, nom, notes, url, sources, par, etat} ;
    `par` = les zips du dépôt qui le fournissent ; `etat` = actif, dans le jeu (posé hors Red Stack), coupé, rangé (parqué
    ou arrivage seulement), absent, externe (hors Nexus, ou d'un autre jeu : pas contrôlable). `ignores` (config.json
    `requis_ignores`) : {identité du mod: [identifiants de prérequis]} que l'utilisateur a dit ne pas compter pour ce mod
    (inutile chez lui, ou tenu sous un autre zip) ; ils restent listés, marqués `ignore`, et ne lèvent plus d'alerte."""
    try:
        cache = json.load(open(os.path.join(data, "nexus.json"), encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    pose = jeu.load_pose()
    actif = lambda k: not index[k]["lieu"] and bool((prof["mods"].get(k) or {}).get("actif"))
    vivants = {k: m for k, m in index.items() if m["genre"] != "retiré"}
    du_mod, du_cadre, dests, ids = collections.defaultdict(list), collections.defaultdict(list), {}, {}
    temoins = {c[3]: c[0] for c in CADRES}
    for k, m in vivants.items():
        w = RX_ZIP_NEXUS.match(m["nom"])
        ids[k] = int(w["mod"]) if w else 0
        if ids[k]:
            du_mod[ids[k]].append(k)
        dests[k] = [e["d"].lower() for e in m["entrees"] if e["d"]]
        for d in dests[k]:
            if d in temoins:
                du_cadre[temoins[d]].append(k)

    def etat_de(cles, temoin=None):
        if any(actif(k) for k in cles):
            return "actif"
        if temoin and jeu.size(temoin) is not None and (pose.get(temoin) or {}).get("zip") not in vivants:
            return "dans le jeu"                     # posé à la main ou par un autre gestionnaire : rien ne le retirera
        return "coupé" if any(not index[k]["lieu"] for k in cles) else "rangé" if cles else "absent"

    cadres = {}
    for code, nom, mid, temoin, _ in CADRES:
        par = sorted(set(du_cadre[code]) | set(du_mod.get(mid, []) if mid else []))
        cadres[code] = {"cadre": code, "mod": mid, "nom": nom, "par": par, "etat": etat_de(par, temoin), "exige_par": 0}
    ep1 = os.path.isdir(jeu.path(EXTENSION_JEU))
    lignes, requis_par = {}, collections.defaultdict(set)
    for k, m in vivants.items():
        mid, req = ids[k], {}
        c = cache.get(str(mid)) if mid else None
        for code, nom, cmid, temoin, usages in CADRES:   # par les fichiers : ce que le zip pose dit le cadre qu'il lui faut
            if usages and k not in cadres[code]["par"] and any(d.startswith(deb) and d.endswith(fins) for d in dests[k] for deb, fins in usages):
                req["c:" + code] = {"cadre": code, "mod": cmid, "nom": nom, "notes": "", "url": "", "sources": ["fichiers"]}
        for x in (c or {}).get("requis") or []:      # par Nexus : ce que l'auteur déclare
            if x["mod"] and x["mod"] == mid:
                continue
            code = CADRE_DU_MOD.get(x["mod"])
            if code and k in cadres[code]["par"]:
                continue
            ident = "c:" + code if code else f"m:{x['mod']}" if x["mod"] else "x:" + x["nom"].lower()
            e = req.setdefault(ident, {"cadre": code, "mod": x["mod"], "nom": next(n[1] for n in CADRES if n[0] == code) if code else x["nom"],
                                       "notes": "", "url": "", "sources": []})
            e["sources"].append("nexus")
            e["notes"], e["url"] = x.get("notes") or e["notes"], x.get("url") or e["url"]
        for x in (c or {}).get("dlc") or []:
            pl = "phantom" in x["nom"].lower()
            req["d:" + x["nom"].lower()] = {"cadre": None, "mod": 0, "nom": x["nom"], "notes": x.get("notes") or "", "url": "", "sources": ["nexus"],
                                            "par": [], "etat": ("dans le jeu" if ep1 else "absent") if pl else "externe", "extension": True}
        for ident, e in req.items():
            if "etat" in e:
                continue
            if e["cadre"]:
                e["par"], e["etat"] = cadres[e["cadre"]]["par"], cadres[e["cadre"]]["etat"]
                cadres[e["cadre"]]["exige_par"] += actif(k)
            elif e["mod"]:
                e["par"] = sorted(x for x in du_mod.get(e["mod"], []) if x != k)
                e["etat"] = etat_de(e["par"])
            else:
                e["par"], e["etat"] = [], "externe"
            for p in e["par"]:
                requis_par[p].add(k)
        tus = set((ignores or {}).get(qui_requiert(m["nom"]), ()))
        for i, e in req.items():                     # Nexus ne dit pas « optionnel » : seule la note de l'auteur le dit
            e["optionnel"] = not e["cadre"] and bool(RX_OPTIONNEL.search(e["notes"]))
            e["ident"], e["ignore"] = i, i in tus
        rq = sorted(req.values(), key=lambda e: (e["etat"] not in MANQUES, e["ignore"], e["optionnel"], not e["cadre"], e["nom"].lower()))
        absents = [e for e in rq if e["etat"] in MANQUES and not e["ignore"]] if actif(k) else []
        lignes[k] = {"nexus": "sans modId" if not mid else "jamais lu" if not c or ("requis" not in c) else "inconnu" if c["requis"] is None else "lu",
                     "requis": rq, "manque": sum(1 for e in absents if e["cadre"]),
                     "a_voir": sum(1 for e in absents if not e["cadre"] and not e["optionnel"]),
                     "optionnels": sum(1 for e in absents if e["optionnel"])}
    for k, r in lignes.items():
        qui = sorted(requis_par.get(k, ()), key=str.lower)
        r["requis_par"], r["requis_par_actifs"] = qui, sum(1 for x in qui if actif(x))
    return lignes, list(cadres.values())


def mots(s):
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return {w for w in re.split(r"[^a-z0-9]+", s.lower()) if w and not re.fullmatch(r"v?\d+", w)}


def nom_convention(nom, taille, fichiers):
    """lit un nom d'archive : {statut, mod, propose, nexus, candidats} (voir l'en-tête de cette section)"""
    if RX_APP.match(nom):
        m = RX_APP.match(nom)
        base = m["name"].rstrip(" -")
        fait = lambda x: f"{base}-{m['mod']}-{m['ver'].replace('.', '-')}-{x['date']}{m['tail'] or ''}.{m['ext']}"
        if fichiers is None:
            return {"statut": "doute", "mod": int(m["mod"]), "raison": T("fichiers du mod pas lus sur Nexus")}
        minute = int(datetime.datetime.strptime(f"{m['d']} {m['h']}:{m['mi']}", "%Y-%m-%d %H:%M")
                     .replace(tzinfo=datetime.timezone.utc).timestamp())
        cand = [x for x in fichiers if minute <= int(x["date"]) < minute + 60]
        if len(cand) > 1:
            pour = [x for x in cand if x.get("version") == m["ver"]]
            cand = pour or cand
        if len(cand) > 1:
            pour = [x for x in cand if int(x.get("sizeInBytes") or -1) == taille]
            cand = pour if len(pour) == 1 else cand
        if len(cand) > 1:                            # nom choisi contre nom du fichier Nexus : gagnant net seulement
            mine = mots(m["name"])
            sc = sorted(((len(mine & mots(x["name"])) / max(1, len(mots(x["name"]))), x) for x in cand), key=lambda s: -s[0])
            if sc[0][0] >= 0.6 and sc[0][0] - sc[1][0] >= 0.2:
                cand = [sc[0][1]]
        out = {"mod": int(m["mod"]), "candidats": [{"nexus": x["name"], "version": x.get("version") or "", "date": int(x["date"]),
                                                    "propose": fait(x)} for x in cand]}
        if len(cand) == 1:
            return dict(out, statut="a_renommer", propose=fait(cand[0]), nexus=cand[0]["name"])
        return dict(out, statut="doute", raison=T("aucun fichier de ce mod publié à cette minute") if not cand
                    else T("plusieurs fichiers publiés à la même minute"))
    m = RX_WEB.match(nom)
    if m:
        return {"statut": "conforme", "mod": int(m["mod"])}
    return {"statut": "hors_nexus", "mod": None}


# ---------------------------------------------------------------- Nexus : mises à jour et téléchargement
# `nexus` compare chaque zip du dépôt aux fichiers publiés de son mod (API publique, sans clé) et PROPOSE la version qui le
# remplace ; `nexus --cle CLE --go` la télécharge à la place de l'ancienne, qui part dans le dossier des retirés de sa
# pile. Le profil suit seul (même radical, même modId) : il reste à lire le plan et à appliquer.
# La clé d'API personnelle ne sert qu'au téléchargement. Elle arrive par la variable d'environnement RED_STACK_NEXUS_KEY
# (l'extension la garde au coffre de VS Code) : jamais dans config.json, jamais sur une ligne de commande, jamais au journal.
# Compte Premium : lien direct par l'API. Compte gratuit : Nexus exige le bouton « Mod manager download » du site, qui
# donne un lien `nxm://…?key=…&expires=…` à passer par --lien.
# Règles reprises de `maj_plan.py` (chacune a coûté une erreur) : un fichier encore publié n'est remplacé que par un fichier
# de MÊME catégorie et de même nom (hors version) ; une variante pour un autre patch du jeu (« - 2.31 ») n'est pas une
# mise à jour ; un fichier archivé n'est remplacé que si le mod n'a qu'un fichier principal.
NEXUS_CLE = "RED_STACK_NEXUS_KEY"
NEXUS_BASE = os.environ.get("RED_STACK_NEXUS_URL", "https://api.nexusmods.com").rstrip("/")   # autre adresse : banc d'essai
NEXUS_DOMAINE = "cyberpunk2077"
NEXUS_VIVANTS = ("MAIN", "OPTIONAL", "MISCELLANEOUS", "UPDATE")
NEXUS_MORTS = ("OLD_VERSION", "ARCHIVED", "DELETED", "REMOVED")
RX_ZIP_NEXUS = re.compile(r"^(?P<name>.+?)-(?P<mod>\d{1,6})-(?:(?P<ver>.*?)-)?(?P<ts>\d{10})(?P<tail>.*)\.zip$", re.I)
RX_PATCH = re.compile(r"(?<![\d.vV])2\.\d{1,2}(?![\d.])")      # patch du jeu dans un nom de fichier Nexus (2.31, 2.5)
RX_NXM = re.compile(r"^nxm://(?P<jeu>[^/]+)/mods/(?P<mod>\d+)/files/(?P<fichier>\d+)/?(?:\?(?P<q>.*))?$", re.I)


def version_outil():
    try:
        return json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "package.json"), encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "dev"


def nexus_v1(chemin, cle, params=None):
    """(code HTTP, en-têtes en minuscules, JSON ou texte) d'un appel à l'API v1 de Nexus"""
    import urllib.error, urllib.parse, urllib.request
    url = f"{NEXUS_BASE}/v1/{chemin}" + ("?" + urllib.parse.urlencode(params) if params else "")
    tetes = {"apikey": cle, "Accept": "application/json", "Application-Name": "Red Stack", "Application-Version": version_outil(),
             "User-Agent": f"RedStack/{version_outil()}"}
    curl = shutil.which("curl")
    if curl:                                         # la clé passe par l'entrée standard, pas par la ligne de commande
        esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
        conf = "".join(f'header = "{esc(k)}: {esc(v)}"\n' for k, v in tetes.items()) + f'url = "{esc(url)}"\n'
        p = subprocess.run([curl, "-sS", "-m", "40", "-D", "-", "-K", "-"], input=conf.encode("utf-8"), capture_output=True)
        if p.returncode:
            raise OSError(p.stderr.decode("utf-8", "replace").strip() or T("curl, code {0}", p.returncode))
        brut = p.stdout
        while True:                                  # un « 100 Continue » ou une réponse de mandataire peut précéder la vraie
            tete, _, corps = brut.partition(b"\r\n\r\n")
            lignes = tete.decode("latin-1").split("\r\n")
            code = int(lignes[0].split()[1]) if len(lignes[0].split()) > 1 and lignes[0].split()[1].isdigit() else 0
            if code // 100 == 1 and corps.startswith(b"HTTP/"):
                brut = corps
                continue
            break
        h = {k.strip().lower(): v.strip() for k, _, v in (x.partition(":") for x in lignes[1:])}
    else:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=tetes), timeout=40) as r:
                code, h, corps = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            code, h, corps = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    try:
        return code, h, json.loads(corps.decode("utf-8"))
    except ValueError:
        return code, h, corps.decode("utf-8", "replace")[:300]


def nexus_compte():
    """le compte de la clé d'API : {cle, nom, premium, reste_jour, reste_heure} ; `cle` False = aucune clé donnée"""
    cle = os.environ.get(NEXUS_CLE, "").strip()
    if not cle:
        return {"cle": False}
    try:
        code, h, d = nexus_v1("users/validate.json", cle)
    except OSError as e:
        return {"cle": True, "erreur": T("Nexus injoignable ({0})", e)}
    if code != 200 or not isinstance(d, dict):
        return {"cle": True, "erreur": T("clé refusée par Nexus") if code in (401, 403)
                else T("Nexus répond {0} : {1}", code, d.get('message', d) if isinstance(d, dict) else d)}
    entier = lambda k: int(h[k]) if h.get(k, "").isdigit() else None
    return {"cle": True, "nom": d.get("name", ""), "premium": bool(d.get("is_premium")),
            "reste_jour": entier("x-rl-daily-remaining"), "reste_heure": entier("x-rl-hourly-remaining")}


def norme_nexus(s):
    """nom d'un fichier Nexus sans sa version ni son patch : deux versions d'un même fichier se retrouvent"""
    s = re.sub(r"\bv?\d+(\.\d+)+[a-z]?\b", " ", s.lower())
    s = re.sub(r"\bfor (patch )?\d\.\d+\b", " ", s)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def version_dans_nom(nom, vieille, neuve):
    """version écrite dans le nom choisi : remplacée par la nouvelle, au même format (`V1.2` -> `V1.2.1`)"""
    for v in sorted({vieille.replace("-", "."), vieille} - {""}, key=len, reverse=True):
        m = re.search(r"(?<![\w.])([vV]?)" + re.escape(v) + r"(?![\w.])", nom)
        if m:
            return nom[:m.start()] + m.group(1) + neuve.lstrip("vV") + nom[m.end():]
    return nom


def nom_de_maj(w, f):
    """nom du zip de la nouvelle version `f` (fichier Nexus) d'après celui de l'ancienne (`w` : lecture de RX_ZIP_NEXUS)"""
    ver = INTERDITS.sub("", (f.get("version") or "").strip()).replace(" ", "_")
    return f"{version_dans_nom(w['name'], w['ver'] or '', ver)}-{int(w['mod'])}-" + (ver.replace(".", "-") + "-" if ver else "") + str(int(f["date"]))


def ext_nexus(f):
    e = os.path.splitext(f.get("uri") or "")[1].lower()
    return e if e in (".zip",) + AUTRES_ARCHIVES else ""


def fiche_nexus(f):
    return {"fichier": int(f["fileId"]), "nom": f["name"], "version": f.get("version") or "", "date": int(f["date"]),
            "taille": int(f.get("sizeInBytes") or 0), "categorie": f.get("category") or "", "ext": ext_nexus(f)}


def nexus_maj(index, fichiers, ignores):
    """une ligne par zip du dépôt lu à la forme du site : à jour, mise à jour proposée, à voir ; plus les zips non comparés"""
    lignes, hors = [], []
    present = collections.defaultdict(dict)          # modId -> {horodatage: clé} de tout le dépôt, retirés compris
    for key, m in index.items():
        w = RX_ZIP_NEXUS.match(m["nom"])
        if w:
            present[int(w["mod"])][int(w["ts"])] = key
    for key, m in index.items():
        if m["genre"] == "retiré":
            continue
        w = RX_ZIP_NEXUS.match(m["nom"])
        if not w:
            hors.append({"cle": key, "raison": T("nom de l'application Nexus : à renommer dans « Arrivages »") if RX_APP.match(m["nom"])
                         else T("pas de modId dans le nom : hors Nexus, ou compilation")})
            continue
        mod, ts, ver = int(w["mod"]), int(w["ts"]), (w["ver"] or "").replace("-", ".")
        qui = f"{mod}|{ident(m['nom'])[0]}"
        r = {"cle": key, "section": m["section"], "lieu": m["lieu"], "genre": m["genre"], "nom": m["nom"], "mod": mod, "version": ver,
             "date": ts, "annotation": w["tail"].strip(), "ignore": qui in ignores, "qui": qui,
             "page": f"https://www.nexusmods.com/{NEXUS_DOMAINE}/mods/{mod}?tab=files"}
        lignes.append(r)
        lst = fichiers.get(mod)
        if not lst:
            r.update(statut="illisible" if lst is None else "introuvable",
                     raison=T("fichiers de ce mod pas lus sur Nexus") if lst is None else T("mod absent de Nexus (retiré ou caché)"))
            continue
        vieux = next((f for f in lst if int(f["date"]) == ts), None)
        vivants = [f for f in lst if f.get("category") in NEXUS_VIVANTS]
        base = norme_nexus(vieux["name"] if vieux else w["name"])
        cand = [f for f in vivants if norme_nexus(f["name"]) == base]
        if vieux and vieux.get("category") in NEXUS_VIVANTS:
            cand = [f for f in cand if f.get("category") == vieux["category"]]
        if not cand and vieux and vieux.get("category") in NEXUS_MORTS:
            mains = [f for f in vivants if f.get("category") == "MAIN"]
            cand = mains if len(mains) == 1 else []
        plus_recents = [f for f in vivants if int(f["date"]) > ts]
        if not cand:
            if plus_recents and not (vieux and vieux in vivants):
                r.update(statut="a_voir", raison=suite(T("ce fichier est archivé sur Nexus") if vieux else T("ce fichier n'est plus listé sur Nexus"),
                                                     N(len(plus_recents), "{n} fichier plus récent porte un autre nom : à choisir", "{n} fichiers plus récents portent un autre nom : à choisir")),
                         candidats=[dict(fiche_nexus(f), propose=nom_de_maj(w, f) + ".zip")
                                    for f in sorted(plus_recents, key=lambda f: -int(f["date"]))])
            else:
                r["statut"] = "a_jour"
            continue
        patchs = set(RX_PATCH.findall(vieux["name"] if vieux else w["name"]))
        cand = [f for f in cand if not set(RX_PATCH.findall(f["name"])) - patchs] or cand
        neuf = max(cand, key=lambda f: int(f["date"]))
        if int(neuf["date"]) <= ts or (vieux and neuf["fileId"] == vieux["fileId"]):
            r["statut"] = "a_jour"
            continue
        r["neuf"] = fiche_nexus(neuf)
        r["propose"] = nom_de_maj(w, neuf) + ".zip"
        r["page"] = f"https://www.nexusmods.com/{NEXUS_DOMAINE}/mods/{mod}?tab=files&file_id={int(neuf['fileId'])}&nmm=1"
        autre = set(RX_PATCH.findall(neuf["name"])) - patchs
        deja = present[mod].get(int(neuf["date"]))
        if deja:
            r.update(statut="deja", raison=T("cette version est déjà dans le dépôt : {0}", deja))
        elif autre:
            r.update(statut="a_voir", raison=T("« {0} » vise le patch {1} du jeu : pas une version plus récente ?", neuf['name'], ', '.join(sorted(autre))))
        else:
            r["statut"] = "maj"
            if r["annotation"]:
                r["raison"] = (T("zip annoté « {0} » : s'il a été retouché ou complété à la main, la nouvelle version ne portera pas ces changements", r['annotation']))
    vus = {}                                         # deux anciennes du même mod au même endroit visent le même zip
    for r in sorted((r for r in lignes if r["statut"] == "maj"), key=lambda r: -r["date"]):
        k = (r["section"], r["lieu"], r["propose"].lower())
        if k in vus:
            r.update(statut="doublon", raison=T("autre version du même mod au même endroit, plus récente : {0} (c'est elle qui porte la mise à jour)", vus[k]))
        else:
            vus[k] = r["cle"]
    return lignes, hors


def nature_archive(path):
    with open(path, "rb") as f:
        tete = f.read(8)
    return ".zip" if tete.startswith(b"PK") else ".7z" if tete.startswith(b"7z\xbc\xaf") else ".rar" if tete.startswith(b"Rar!") else ""


def nexus_recoit(urls, part, taille):
    """télécharge vers `part` en essayant chaque miroir à tour de rôle (reprise comprise) ; rend l'erreur, ou None"""
    import urllib.parse, urllib.request
    urls = [urllib.parse.quote(u, safe=":/?&=%#~+,;@!$*()'") for u in urls]
    curl, err = shutil.which("curl"), T("aucun miroir proposé")
    for essai in range(2 * len(urls)):
        url = urls[essai % len(urls)]
        try:
            if curl:
                # premier tour : un miroir sous 500 Ko/s pendant 15 s est lâché pour le suivant (la reprise garde l'acquis) ;
                # second tour sans plancher, pour une ligne lente partout
                lent = ["--speed-limit", "500000", "--speed-time", "15"] if essai < len(urls) and len(urls) > 1 else []
                p = subprocess.run([curl, "-sS", "--fail", "-L", "-A", f"RedStack/{version_outil()}", "-C", "-", "--retry", "1",
                                    "--connect-timeout", "15", *lent, "-o", part, url], capture_output=True)
                if p.returncode:
                    raise OSError(p.stderr.decode("utf-8", "replace").strip()[-200:] or T("curl, code {0}", p.returncode))
            else:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": f"RedStack/{version_outil()}"}),
                                            timeout=60) as r, open(part, "wb") as f:
                    shutil.copyfileobj(r, f, 1 << 20)
        except Exception as e:
            err = str(e)
            continue
        recu = os.path.getsize(part)
        if taille and recu != taille:
            err = T("{0} octets reçus, {1} annoncés par Nexus", recu, taille)
            os.remove(part)
            continue
        return None
    return err


def lit_nxm(lien):
    """(modId, fileId, paramètres `key` / `expires` ou None) d'un lien `nxm://` de ce jeu ; arrêt s'il n'en est pas un"""
    import urllib.parse
    x = RX_NXM.match((lien or "").strip())
    if not x:
        sys.exit(T("Lien refusé : un lien `nxm://…/mods/<mod>/files/<fichier>?key=…&expires=…` est attendu (bouton « Mod manager download »)."))
    if x["jeu"].lower() != NEXUS_DOMAINE:
        sys.exit(T("Ce lien est celui d'un autre jeu ({0}) : Red Stack ne range que les mods de {1}.", x['jeu'], NEXUS_DOMAINE))
    q = urllib.parse.parse_qs(x["q"] or "")
    ok = q.get("key") and q.get("expires")
    return int(x["mod"]), int(x["fichier"]), ({"key": q["key"][0], "expires": q["expires"][0]} if ok else None)


def dossier_convention(base, genre):
    """nom du dossier `genre` (retires, nouveaux, parques) d'une pile : celui qui existe, sinon tiré du premier motif de la
    convention ; '' si elle n'en donne pas"""
    existants = [d for d in sorted(os.listdir(base)) if match(d, CONV[genre]) and os.path.isdir(os.path.join(base, d))]
    nom = existants[0] if existants else re.sub(r"[*?\[\]]", "", (CONV[genre] or [""])[0])
    return nom if nom and match(nom, CONV[genre]) and not INTERDITS.search(nom) else ""


def fichier_partiel(cible):
    """fichier où un téléchargement s'écrit avant de devenir `cible` ; dit dans la réponse (`part`) : l'extension y lit l'avancée"""
    return os.path.splitext(cible)[0] + ".part"


def nexus_obtient(mod, neuf, cible, conf, params):
    """reçoit le fichier Nexus `neuf` du mod vers le zip `cible` (converti s'il arrive en .7z / .rar) ; rend (nombre de
    fichiers du zip, outil de conversion ou None). Tout échec arrête sans rien changer d'autre dans le dépôt."""
    dossier = os.path.dirname(cible)
    libre = shutil.disk_usage(dossier if os.path.isdir(dossier) else os.path.dirname(dossier)).free
    if neuf["taille"] and libre < neuf["taille"] * 2 + (64 << 20):
        sys.exit(T("Place insuffisante sur le disque du dépôt : {0} Mo libres, {1} Mo à recevoir.", libre >> 20, neuf['taille'] >> 20))
    code, _, d = nexus_v1(f"games/{NEXUS_DOMAINE}/mods/{mod}/files/{neuf['fichier']}/download_link.json", os.environ[NEXUS_CLE].strip(), params)
    if code != 200 or not isinstance(d, list) or not d:
        msg = d.get("message", d) if isinstance(d, dict) else d
        sys.exit(T("Nexus refuse le lien de téléchargement ({0}) : {1}", code, msg)
                 + (T(" Le lien `nxm://` a peut-être expiré : recliquer « Mod manager download ».") if params else ""))
    os.makedirs(dossier, exist_ok=True)
    part = fichier_partiel(cible)
    # « Nexus CDN » d'abord : mesuré le 18/11 à 9 Mo/s quand les miroirs de ville, dont le préféré du compte, donnaient
    # 0,05 à 0,3 Mo/s ; les autres suivent dans l'ordre de Nexus
    d = sorted(d, key=lambda x: x.get("short_name") != "Nexus CDN")
    err = nexus_recoit([x["URI"] for x in d if x.get("URI")], part, neuf["taille"])
    if err:
        if os.path.exists(part):
            os.remove(part)
        sys.exit(T("Téléchargement échoué, rien changé dans le dépôt : {0}", err))
    ext = nature_archive(part) or neuf["ext"]
    if ext not in (".zip",) + AUTRES_ARCHIVES:
        os.remove(part)
        sys.exit(T("Le fichier reçu n'est ni un .zip, ni un .7z, ni un .rar : rien changé dans le dépôt."))
    recu = os.path.splitext(cible)[0] + ext
    if os.path.exists(recu):
        os.remove(part)
        sys.exit(T("Un fichier du même nom est déjà là : {0}", recu))
    os.replace(part, recu)
    converti = None
    if ext != ".zip":                                # un échec de conversion laisse l'archive reçue, rien d'autre ne bouge
        converti = convertit(recu, conf, True)["outil"]
    try:
        with zipfile.ZipFile(cible) as z:
            return len(z.infolist()), converti
    except (OSError, zipfile.BadZipFile) as e:
        sys.exit(T("Zip reçu illisible ({0}) : laissé là, rien d'autre n'a bougé : {1}", e, cible))


def nexus_arrive(mod, f, depot, section, conf, params, go):
    """télécharge le fichier Nexus `f` d'un mod que le dépôt n'a pas encore, dans le dossier d'arrivée de la pile `section`,
    sous son nom du site ; sans `go`, dit seulement où il irait"""
    if section not in sections(depot):
        sys.exit(T("Pile inconnue du dépôt : {0}", section))
    neuf, base = fiche_nexus(f), dossier_pile(depot, section)
    lieu = dossier_convention(base, "nouveaux")
    if not lieu:
        sys.exit(T("Aucun dossier d'arrivée : la convention {0} ne donne pas de nom (Réglages).", CONV['nouveaux']))
    stem = os.path.splitext(INTERDITS.sub("", os.path.basename(f.get("uri") or "")).strip())[0]
    w = RX_WEB.match(stem + ".zip")
    if not w or int(w["mod"]) != mod:                # nom du site illisible : refait d'après le nom et la version du fichier
        ver = INTERDITS.sub("", (f.get("version") or "").strip()).replace(" ", "_").replace(".", "-")
        stem = f"{INTERDITS.sub('', f['name']).strip(' .') or 'Mod'}-{mod}-" + (ver + "-" if ver else "") + str(int(f["date"]))
    cible = os.path.join(base, lieu, stem + ".zip")
    if os.path.exists(cible):
        sys.exit(T("Un zip du même nom est déjà là : {0}", cible))
    compte = nexus_compte()
    vue = {"cle": "/".join((section, lieu, stem + ".zip")), "vers": cible, "part": fichier_partiel(cible), "neuf": neuf, "compte": compte, "besoin_lien": False,
           "ecrit": False, "page": f"https://www.nexusmods.com/{NEXUS_DOMAINE}/mods/{mod}?tab=files&file_id={neuf['fichier']}&nmm=1"}
    if not compte["cle"] or compte.get("erreur"):
        return dict(vue, erreur=compte.get("erreur") or T("aucune clé d'API Nexus : la donner dans la vue « Mises à jour »"))
    if not compte["premium"] and not params:
        return dict(vue, besoin_lien=True)
    if not go:
        return vue
    n, converti = nexus_obtient(mod, neuf, cible, conf, params)
    return dict(vue, ecrit=True, fichiers=n, converti=converti, octets=os.path.getsize(cible))


def nexus_cibles(mod, date, nom, index, fichiers, fid=None):
    """zips en place (actifs ou parqués) qu'un fichier du mod `mod`, publié à `date` sous le nom `nom`, peut mettre à jour,
    le plus sûr d'abord : [{cle, nom, section, lieu, version, annotation, sur}]. `sur` : c'est le fichier que Red Stack
    proposait pour ce zip, ou il porte le même nom sur Nexus (hors version)."""
    lignes, _ = nexus_maj(index, fichiers, set())
    base, vus = norme_nexus(nom), []
    for r in lignes:
        if r["mod"] != mod or r["genre"] == "nouveau" or r["date"] >= date:
            continue
        w = RX_ZIP_NEXUS.match(r["nom"])
        vieux = next((x for x in fichiers.get(mod) or [] if int(x["date"]) == r["date"]), None)
        prevu = r.get("neuf") and (r["neuf"]["fichier"] == fid or r["neuf"]["date"] == date)
        rang = 0 if prevu else 1 if base in (norme_nexus(vieux["name"]) if vieux else "", norme_nexus(w["name"])) else 2
        vus.append((rang, -r["date"], {"cle": r["cle"], "nom": r["nom"], "section": r["section"], "lieu": r["lieu"],
                                       "version": r["version"], "annotation": r["annotation"], "sur": rang < 2}))
    return [x for _, _, x in sorted(vus, key=lambda t: t[:2])]


RX_LOCAL = re.compile(r"^(?P<name>.+?)[ _-]+[vV]?(?P<ver>\d+(?:\.\d+)+)(?P<tail>.*)$")


def ident_local(nom):
    """zip sans modId (mod maison, GitHub) : (radical sans espace ni casse, version en nombres, reste, version écrite), ou None.
    « Red Windows Snap 1.0.0.zip » et « RedWindows Snap 1.0.1.zip » sont le même mod."""
    if RX_ZIP_NEXUS.match(nom) or RX_APP.match(nom) or not nom.lower().endswith(".zip"):
        return None
    m = RX_LOCAL.match(nom[:-4])
    plat = lambda x: re.sub(r"[^a-z0-9]+", "", x.lower())
    return (plat(m["name"]), tuple(int(x) for x in m["ver"].split(".")), plat(m["tail"]), m["ver"]) if m and plat(m["name"]) else None


def cibles_locales(nom, index):
    """zips en place (actifs ou parqués) qu'un arrivage sans modId met à jour : même radical, version plus basse ; le plus
    récent d'abord, à la forme de `nexus_cibles`. Le nom de l'arrivage est gardé tel quel."""
    neuf, vus = ident_local(nom), []
    for k, m in index.items() if neuf else ():
        vieux = ident_local(m["nom"]) if m["genre"] not in ("retiré", "nouveau") else None
        if vieux and vieux[0] == neuf[0] and vieux[2] == neuf[2] and vieux[1] < neuf[1]:
            vus.append((vieux[1], {"cle": k, "nom": m["nom"], "section": m["section"], "lieu": m["lieu"], "version": vieux[3],
                                   "annotation": "", "sur": True, "propose": nom}))
    vus.sort(key=lambda t: t[0], reverse=True)
    for _, x in vus[1:]:
        x["sur"] = False
    return [x for _, x in vus]


def nexus_telecharge(r, m, depot, conf, lien, go, fichiers, choisi=None, nom=None):
    """télécharge la nouvelle version de la ligne `r` à la place du zip `m` ; sans `go`, dit seulement ce qui serait fait.
    `choisi` : identifiant d'un autre fichier du même mod (ligne « à voir ») ; `nom` : nom du zip retouché par l'utilisateur."""
    w = RX_ZIP_NEXUS.match(m["nom"])
    neuf, propose, params = r.get("neuf"), r.get("propose"), None

    def prend(fid):                                  # un autre fichier du même mod que celui proposé : l'utilisateur décide
        f = next((f for f in fichiers or [] if int(f["fileId"]) == int(fid)), None)
        if not f:
            sys.exit(T("Le fichier {0} n'est pas dans la liste des fichiers du mod {1} (relire Nexus).", fid, r['mod']))
        return fiche_nexus(f), nom_de_maj(w, f) + ".zip"

    if choisi and not (neuf and int(choisi) == neuf["fichier"]):
        neuf, propose = prend(choisi)
    if lien:
        mod, fid, params = lit_nxm(lien)
        if mod != r["mod"]:
            sys.exit(T("Ce lien n'est pas celui du mod {0} de {1} : il porte le mod {2}.", r['mod'], NEXUS_DOMAINE, mod))
        if not neuf or fid != neuf["fichier"]:
            neuf, propose = prend(fid)
    if not neuf:
        sys.exit(T("Rien à télécharger pour {0} : choisir un fichier (--fichier ID), ou passer un lien `nxm://` (--lien).", r['cle']))
    if nom:
        nom = nom.strip()
        if INTERDITS.search(nom) or nom.endswith((" ", ".")) or len(nom) > 200 or not nom.lower().endswith(".zip") or len(nom) < 5:
            sys.exit(T("Nom refusé : « {0} » (un nom de zip, sans \\ / : * ? \" < > |)", nom))
        propose = nom
    page = f"https://www.nexusmods.com/{NEXUS_DOMAINE}/mods/{r['mod']}?tab=files&file_id={neuf['fichier']}&nmm=1"
    base = dossier_pile(depot, m["section"])
    dossier = os.path.dirname(m["zip"])
    cible = os.path.join(dossier, propose)
    retires = dossier_convention(base, "retires")
    if not retires:
        sys.exit(T("Aucun dossier des retirés pour ranger l'ancienne version : la convention {0} ne donne pas de nom (Réglages).", CONV['retires']))
    range_ = os.path.join(base, retires, m["nom"])
    if os.path.exists(cible):
        sys.exit(T("Un zip du même nom est déjà là : {0}", cible))
    if os.path.exists(range_):
        sys.exit(T("L'ancienne version ne peut pas être rangée, un zip du même nom est déjà là : {0}", range_))
    compte = nexus_compte()
    vue = {"cle": r["cle"], "de": m["zip"], "vers": cible, "part": fichier_partiel(cible), "ancienne_vers": range_, "neuf": neuf, "compte": compte, "page": page,
           "besoin_lien": False, "ecrit": False}
    if not compte["cle"] or compte.get("erreur"):
        return dict(vue, erreur=compte.get("erreur") or T("aucune clé d'API Nexus : la donner dans « Réglages »"))
    if not compte["premium"] and not params:
        return dict(vue, besoin_lien=True)
    if not go:
        return vue
    n, converti = nexus_obtient(r["mod"], neuf, cible, conf, params)   # un échec laisse l'ancienne version en place
    restee = False
    try:                                             # parquée, renommée ou supprimée pendant le téléchargement : la nouvelle
        os.makedirs(os.path.dirname(range_), exist_ok=True)   # version reste en place, l'ancienne est laissée où elle est
        os.rename(m["zip"], range_)
    except OSError:
        restee = True
    return dict(vue, neuf=neuf, ecrit=True, fichiers=n, converti=converti, octets=os.path.getsize(cible), ancienne_restee=restee)


def lieux_du_depot(depot):
    """(pile, dossier de convention ou '', chemin) de chaque endroit où une archive peut se trouver"""
    for sec in sections(depot):
        base = dossier_pile(depot, sec)
        yield sec, "", base
        for d in sous_dossiers(depot, sec):
            yield sec, d, os.path.join(base, d)


def chemin_de_cle(depot, cle):
    """chemin d'une archive du dépôt d'après sa clé `pile/[dossier/]nom`, ou None si la clé sort des piles"""
    parts = (cle or "").split("/")
    if not 2 <= len(parts) <= 3 or any(p in ("", ".", "..") or INTERDITS.search(p) for p in parts):
        return None
    if parts[0] not in sections(depot) or (len(parts) == 3 and parts[1] not in sous_dossiers(depot, parts[0])):
        return None
    p = os.path.join(dossier_pile(depot, parts[0]), *parts[1:])
    return p if os.path.isfile(p) else None


def extracteur(src, conf):
    """commande d'extraction d'un .7z ou .rar vers un dossier : (nom de l'outil, fonction dossier -> arguments), ou None"""
    sept = conf.get("extracteur") or shutil.which("7z") or next(
        (p for p in (os.path.join(os.environ.get(v, ""), "7-Zip", "7z.exe") for v in ("ProgramFiles", "ProgramFiles(x86)"))
         if os.path.isfile(p)), None)
    if sept:
        return "7-Zip", lambda dst: [sept, "x", "-y", "-bso0", "-bsp0", "-o" + dst, src]
    unrar = next((p for p in (os.path.join(os.environ.get(v, ""), "WinRAR", "UnRAR.exe") for v in ("ProgramFiles", "ProgramFiles(x86)"))
                  if os.path.isfile(p)), None)
    if src.lower().endswith(".rar") and unrar:
        return "UnRAR", lambda dst: [unrar, "x", "-o+", "-idq", src, dst + os.sep]
    tar = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "tar.exe")   # bsdtar de Windows : lit 7z et rar
    tar = tar if os.path.isfile(tar) else shutil.which("bsdtar")
    if tar:
        return "tar", lambda dst: [tar, "-xf", src, "-C", dst]
    return None


def convertit(src, conf, go):
    """.7z / .rar -> .zip à côté, vérifié ; l'original n'est supprimé qu'après le contrôle du zip"""
    import tempfile
    dst = os.path.splitext(src)[0] + ".zip"
    if os.path.exists(dst):
        sys.exit(T("Un zip du même nom est déjà là : {0}", dst))
    ex = extracteur(src, conf)
    if not ex:
        sys.exit(T("Aucun outil pour lire cette archive : installer 7-Zip, ou donner son chemin dans config.json (`extracteur`)."))
    if not go:
        return {"de": src, "vers": dst, "outil": ex[0], "ecrit": False}
    work = tempfile.mkdtemp(prefix="rs_conv_")       # court : certains mods dépassent sinon les 260 caractères
    try:
        r = subprocess.run(ex[1](work), capture_output=True, text=True, errors="replace")
        files = sorted(os.path.join(b, f) for b, _, fs in os.walk(work) for f in fs)
        if r.returncode or not files:
            sys.exit(T("Extraction refusée par {0} (code {1}) : original gardé, rien écrit.\n{2}", ex[0], r.returncode, (r.stderr or r.stdout)[-600:]))
        with zipfile.ZipFile(dst + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, os.path.relpath(p, work).replace(os.sep, "/"))
        with zipfile.ZipFile(dst + ".tmp") as z:
            if z.testzip() is not None or len(z.namelist()) != len(files):
                os.remove(dst + ".tmp")
                sys.exit(T("Zip écrit puis relu différent : original gardé, rien écrit."))
        os.replace(dst + ".tmp", dst)
        os.remove(src)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if os.path.exists(dst + ".tmp"):
            os.remove(dst + ".tmp")
    return {"de": src, "vers": dst, "outil": ex[0], "fichiers": len(files), "ecrit": True}


# ---------------------------------------------------------------- convention du contenu d'un zip
# Sur demande, mod par mod : `contenu --cle` PROPOSE de renommer ce qu'un zip livre, `--fixe … --go` réécrit le zip.
# Candidats : `.archive`, `.xl`, `.yaml`, `.reds`, et les dossiers directs `r6/scripts/X`, `r6/tweaks/X`, `r6/audioware/X`.
# Cible : `Mots_Capitalisés`, au nom du mod quand le fichier est seul de son type, sinon le nom du créateur découpé ;
# `.archive.xl` -> `.xl` ; préfixes d'ordre du créateur gardés (`!!_`, `#_`, `0_`, `zz_`) ; un dossier de tête qui emballe
# le mod est retiré. Jamais touchés : dossiers CET, `red4ext/plugins`, `r6/storages` (retrouvés par leur nom).
# Rien n'est proposé qui casse une référence : l'index des références lit le code de TOUS les zips du dépôt (hors
# commentaires) et garde au nom du créateur une `.archive` citée en dur (`Nom.archive`), un `.yaml` / `.reds` ou un dossier
# cité littéralement, un dossier livré aussi par un autre mod, et les `.archive` / `.xl` d'un mod dont le renommage
# changerait l'ordre de chargement. Les habitudes de l'utilisateur sont dans config.json `contenu`.
CUT = r"(?<=[a-z0-9])(?=[A-Z][a-z])|(?<=[a-z])(?=[A-Z0-9])|(?<=[A-Z])(?=[A-Z][a-z])"
PREFIXE = re.compile(r"^(!+ ?\d*_?|#+_?|\d{1,3}_|[Zz]{1,4}_|[Zz]{1,4}(?=[A-Z][a-z]))")
CODE_EXT = (".lua", ".reds", ".json", ".yaml", ".yml", ".ini", ".toml", ".tweak")
DOSSIERS_MOD = ("r6/scripts", "r6/tweaks", "r6/audioware")
JAMAIS = ("bin/x64/plugins/cyber_engine_tweaks/mods/", "r6/storages/", "red4ext/plugins/")
CONTENU = {"mots_gardes": [],                        # pseudos d'auteur jamais découpés (`ThighHighValerie`)
           "prefixes": {},                           # début du nom du zip -> préfixe des fichiers (`Location - ` -> `Location_`)
           "piles_nom_complet": [],                  # piles où `.archive` / `.xl` prennent le nom complet du zip (véhicules)
           "listes_de_conflits": ["knownConflictingOtherModsWarnings.lua", "cyanidex.json"]}   # citer n'y est pas dépendre
RX_REF_A = re.compile(r"([A-Za-z0-9_!#'\- ]+)\.archive(?![A-Za-z0-9_])")
RX_REF_F = re.compile(r"([A-Za-z0-9_!#'\-]+\.(?:yaml|yml|reds))(?![A-Za-z0-9_])", re.I)
RX_REF_D = re.compile(r"(scripts|tweaks|audioware)[/\\]+([A-Za-z0-9_!#'\- ]+)", re.I)
RX_REF_M = re.compile(r"""GetMod\(\s*["']([^"']+)["']|cyber_engine_tweaks[/\\]+mods[/\\]+([A-Za-z0-9_!#'\- .]+?)(?=[/\\"'])""", re.I)
REFS_V = 3                                           # version des motifs : un cache d'une autre version est relu
RX_REF_I = re.compile(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)      # module Redscript importé (sa racine)
RX_REF_MOD = re.compile(r"^\s*module\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)    # module Redscript déclaré (sa racine)


def sans_commentaires(name, t):
    """une citation en commentaire n'est pas une référence"""
    n = name.lower()
    if n.endswith(".lua"):
        return re.sub(r"--[^\n]*", "", re.sub(r"--\[(=*)\[.*?\]\1\]", "", t, flags=re.S))
    if n.endswith(".reds"):
        return re.sub(r"(?<!:)//[^\n]*", "", re.sub(r"/\*.*?\*/", "", t, flags=re.S))
    if n.endswith((".yaml", ".yml", ".toml", ".tweak")):
        return re.sub(r"(?m)(^|\s)#[^\n]*", r"\1", t)
    if n.endswith(".ini"):
        return re.sub(r"(?m)^\s*[;#][^\n]*", "", t)
    return t


def references(index, data):
    """{clé du zip: [[fichier citant, genre, texte cité en minuscules]]} ; cache `references.json` par signature.
    Genres : a = `.archive` par son nom, f = `.yaml` / `.reds` par son nom, d = dossier de scripts, de tweaks ou d'audioware,
    m = dossier d'un mod CET (`GetMod("nom")`, ou un chemin `cyber_engine_tweaks/mods/nom/`), i = module Redscript importé
    (racine du nom), M = module Redscript que ce zip déclare."""
    path = os.path.join(data, "references.json")
    try:
        cache = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    out, dirty = {}, False
    for key, m in index.items():
        if m["genre"] == "retiré":
            continue
        c = cache.get(key)
        if not c or c.get("sig") != m["sig"] or c.get("v") != REFS_V:
            refs = set()
            try:
                with zipfile.ZipFile(m["zip"]) as z:
                    for e in m["entrees"]:
                        if not e["n"].lower().endswith(CODE_EXT) or e["s"] > 8 << 20:
                            continue
                        t = sans_commentaires(e["n"], z.read(e["n"]).decode("utf-8", "replace"))
                        refs.update((e["n"], "a", x.strip().lower()) for x in RX_REF_A.findall(t))
                        refs.update((e["n"], "f", x.lower()) for x in RX_REF_F.findall(t))
                        refs.update((e["n"], "d", (p + "/" + d).strip().lower()) for p, d in RX_REF_D.findall(t))
                        refs.update((e["n"], "m", (g or c2).strip().lower()) for g, c2 in RX_REF_M.findall(t) if (g or c2).strip())
                        if e["n"].lower().endswith(".reds"):
                            refs.update((e["n"], "i", x.lower()) for x in RX_REF_I.findall(t))
                            refs.update((e["n"], "M", x.lower()) for x in RX_REF_MOD.findall(t))
            except (OSError, zipfile.BadZipFile, KeyError):
                pass
            c = {"sig": m["sig"], "v": REFS_V, "refs": sorted(refs)}
            dirty = True
        out[key] = c
    if dirty or set(cache) != set(out):
        os.makedirs(data, exist_ok=True)
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return {k: c["refs"] for k, c in out.items()}


# ---------------------------------------------------------------- nature d'un mod, lue dans ce que son zip pose
# Chaque nature est un FAIT du zip (où vont ses fichiers), jamais un nom ni une liste de mods connus. « socle » : le zip
# livre un chargeur que d'autres mods exigent (fichier précis), ou d'autres mods du dépôt le citent (dossier CET appelé par
# `GetMod`, module Redscript importé) : cela se lit dans le cache des références, s'il existe déjà.
NATURES = (("archive", lambda d: d.startswith("archive/pc/mod/") and d.endswith(".archive")),
           ("xl", lambda d: d.startswith("archive/pc/mod/") and d.endswith(".xl")),
           ("redmod", lambda d: d.startswith("mods/")),
           ("reds", lambda d: d.startswith("r6/scripts/") and d.endswith(".reds")),
           ("tweak", lambda d: d.startswith("r6/tweaks/") and d.endswith((".yaml", ".yml", ".tweak"))),
           ("cet", lambda d: d.startswith("bin/x64/plugins/cyber_engine_tweaks/mods/")),
           ("red4ext", lambda d: d.startswith("red4ext/plugins/") and d.endswith(".dll")),
           ("asi", lambda d: d.startswith("bin/x64/plugins/") and d.endswith(".asi")),
           ("audio", lambda d: d.startswith("r6/audioware/")),
           ("reshade", lambda d: d.startswith("bin/x64/reshade-shaders/")),
           ("config", lambda d: d.startswith(("r6/config/", "r6/input/", "engine/config/"))))
CHARGEURS = ("bin/x64/plugins/cyber_engine_tweaks.asi", "red4ext/red4ext.dll", "engine/tools/scc.exe",
             "red4ext/plugins/archivexl/archivexl.dll", "red4ext/plugins/tweakxl/tweakxl.dll", "red4ext/plugins/codeware/codeware.dll")
SOCLE_CITE = 2                                       # cité par au moins tant d'AUTRES mods du dépôt


def cites_du_depot(index, cache):
    """({dossier CET: {radicaux qui l'appellent}}, {module Redscript: {radicaux qui l'importent}}) d'après le cache des
    références ; vides s'il n'a jamais été fait (jamais calculé ici : une minute sur un gros dépôt)"""
    cet, mods = collections.defaultdict(set), collections.defaultdict(set)
    for key, c in cache.items():
        if key in index and index[key]["genre"] != "retiré":
            for _, genre, texte in c.get("refs", []):
                if genre in ("m", "i"):
                    (cet if genre == "m" else mods)[texte].add(ident(index[key]["nom"])[0])
    return cet, mods


def natures(mod, key, cites, cache):
    """natures d'un zip, socle d'abord, puis dans l'ordre de NATURES ; « autre » s'il pose des fichiers d'aucune"""
    dests = [e["d"].lower() for e in mod["entrees"] if e.get("d")]
    out = [n for n, f in NATURES if any(f(d) for d in dests)]
    if any(d for d in dests if not any(f(d) for _, f in NATURES)):
        out.append("autre")
    moi = ident(mod["nom"])[0]
    # un dossier CET est À ce zip s'il en livre l'`init.lua` (un pack de props pose ses fichiers dans le dossier d'un autre)
    dossiers = {d.split("/")[5] for d in dests if d.startswith("bin/x64/plugins/cyber_engine_tweaks/mods/") and d.count("/") == 6 and d.endswith("/init.lua")}
    declares = {t for _, g, t in cache.get(key, {}).get("refs", []) if g == "M"}
    socle = (any(d in CHARGEURS for d in dests)
             or any(len(cites[0].get(x, set()) - {moi}) >= SOCLE_CITE for x in dossiers)
             or any(len(cites[1].get(x, set()) - {moi}) >= SOCLE_CITE for x in declares))
    return (["socle"] if socle else []) + out


def mots_capitalises(s, gardes=()):
    ws = [w for w in re.split(r"[^A-Za-z0-9']+", re.sub(CUT, " ", s)) if w]
    out = "_".join(w[0].upper() + w[1:] for w in ws)
    for k in gardes:                                 # pseudo recollé quand le nom est fabriqué (Ne0wing -> Ne_0wing)
        cut = re.sub(CUT, "_", k)
        out = out.replace(cut[0].upper() + cut[1:], k)
    return out


def nom_du_mod(zip_name, gardes=()):
    """nom choisi du zip, sans version ni mentions d'empaquetage, en Mots_Capitalisés"""
    app = RX_APP.match(zip_name)                     # nom de l'application Nexus : ce qui précède le modId
    n = app["name"] if app else re.sub(r"-\d{1,6}-.*$", "", os.path.splitext(zip_name)[0])
    n = re.sub(r"\(.*?\)", " ", n)
    n = re.sub(r"(?i)\b(v?\d+(\.\d+)+[a-z]?|v\d+|fomod|main file|aio)\b", " ", n)
    n = re.sub(r"(?i)\b(by \w+)$", " ", n.strip(" -_"))
    n = re.sub(r"(?i)\s+for(\s+game\s+version)?\s*$", " ", n.strip(" -_"))
    return mots_capitalises(n, gardes)


def coupe_prefixe(stem):
    m = PREFIXE.match(stem)
    if not m:
        return "", stem
    g = m.group(0)
    return (g + "_" if re.fullmatch(r"[Zz]{1,4}", g) else g), stem[m.end():]


def en_convention(name, gardes=()):
    """déjà en Mots_Capitalisés (préfixe d'ordre admis), sans espace ni camelCase dans un mot"""
    if any(k.lower() in name.lower() for k in gardes):
        return True
    bare = coupe_prefixe(name)[1]
    ws = bare.split("_")
    return bool(bare) and " " not in name and all(w and (w[0].isupper() or w[0].isdigit()) and not re.search(r"[a-z][A-Z]", w) for w in ws)


def plan_contenu(key, index, refs, cfg, nom=None):
    """plan de renommage du contenu d'un zip : {etat, base, ops: [{de, vers}], gardes: [{chemin, raison}], notes}"""
    mod = index[key]
    gardes_mots = cfg["mots_gardes"]
    names = [e["n"] for e in mod["entrees"]]
    out = {"cle": key, "nom": mod["nom"], "ops": [], "gardes": [], "notes": [], "fichiers": []}
    if any(n.lower().startswith("fomod/") or "/fomod/" in n.lower() for n in names):
        return dict(out, etat="fomod", notes=[T("Installeur à choix (FOMOD) : contenu laissé tel quel.")])
    opts = {e["o"] for e in mod["entrees"] if e["o"] not in (None, RACINE)}
    if len(opts) > 1:
        return dict(out, etat="pack", notes=[T("Pack à options ({0} dossiers) : contenu laissé tel quel, les options se choisissent dans le détail du mod.", len(opts))])
    top = next(iter(opts), "")
    # chemin de travail de chaque entrée posable : sans le dossier de tête ; un fichier seul à la racine prend sa destination
    work = {e["n"]: (e["d"] if e["o"] == RACINE else e["n"][len(top) + 1:] if top else e["n"]) for e in mod["entrees"] if e["o"] is not None}
    if not work:
        return dict(out, etat="rien", notes=[T("Rien de posable dans ce zip.")])
    files = sorted(work.values())
    base = (nom or "").strip() or nom_du_mod(mod["nom"], gardes_mots)   # `nom` : le nom du mod voulu par l'utilisateur
    out["base"] = base
    cat = next((v for k, v in cfg["prefixes"].items() if mod["nom"].startswith(k)), "")
    avec_cat = lambda core: core if not cat or core.lower().startswith(cat.lower()) else cat + core
    mid = ident(mod["nom"])[1]
    famille = [k for k, m in index.items() if k != key and mid and m["genre"] != "retiré" and ident(m["nom"])[1] == mid
               and ident(m["nom"])[0] != ident(mod["nom"])[0]]
    cites = lambda genre, autres: [(k, f, c) for k, rl in refs.items() if (k != key) == autres for f, g, c in rl if g == genre]
    cible, garde = {}, {}                            # chemin de travail -> nouveau chemin ; chemin -> raison de le garder

    # 1. dossiers de mod directs
    dirs = {}
    for f in files:
        for parent in DOSSIERS_MOD:
            if f.lower().startswith(parent + "/") and f.count("/") > parent.count("/") + 1:
                dirs.setdefault(f[:len(parent)] + "/" + f[len(parent) + 1:].split("/")[0], parent)
    ailleurs = {(parent + "/" + e["d"][len(parent) + 1:].split("/")[0]).lower()
                for k, m in index.items() if k != key and m["genre"] != "retiré" and ident(m["nom"]) != ident(mod["nom"])
                for e in m["entrees"] if e["d"] for parent in DOSSIERS_MOD
                if e["d"].lower().startswith(parent + "/") and e["d"].count("/") > parent.count("/") + 1}
    libres = collections.Counter(p for d, p in dirs.items() if d.lower() not in ailleurs)
    dir_map, leves, communs = {}, set(), set()
    leve_de, voulu = {}, {}                          # dossier -> son fichier remonté ; dossier -> nom proposé
    for old, parent in sorted(dirs.items()):
        d = old.split("/")[-1]
        pre_d, bare_d = coupe_prefixe(d)             # préfixe d'ordre du créateur (`zz_`, `0_`, `!`) : gardé devant le nom proposé
        if old.lower() in ailleurs:
            garde[old] = T("dossier livré aussi par un autre mod du dépôt")
            communs.add(old)
            continue
        cite = (parent.split("/")[-1] + "/" + d).lower()
        hit = next(((k, f) for k, rl in refs.items() for f, g, c in rl
                    if g == "d" and (c == cite or (c.startswith(cite) and not re.match(r"[a-z0-9_]", c[len(cite):])))), None)
        new_d = pre_d + (base if libres[parent] == 1 else mots_capitalises(bare_d, gardes_mots))
        inside = [f for f in files if f.startswith(old + "/")]
        seul = parent != "r6/audioware" and len(inside) == 1 and inside[0].lower().endswith((".reds", ".yaml", ".yml"))
        if hit and (seul or new_d != d):
            garde[old] = T("dossier cité en dur par {0} ({1})", os.path.basename(hit[1]), hit[0].split('/')[-1])
            communs.add(old)
            continue
        if seul:                                     # un seul fichier dans le dossier : il remonte d'un cran, au nom du mod
            leves.add(inside[0])
            leve_de[old], voulu[old] = inside[0], new_d
            cible[inside[0]] = f"{old.rsplit('/', 1)[0]}/{new_d}{os.path.splitext(inside[0])[1]}"
        elif not en_convention(d, gardes_mots) and new_d and new_d != d:
            dir_map[old] = f"{old.rsplit('/', 1)[0]}/{new_d}"
            voulu[old] = new_d
        if pre_d and old in voulu:
            out["notes"].append(T("`{0}` : le préfixe `{1}` fixe l'ordre voulu par l'auteur, la proposition le garde. Le chemin reste retouchable si vous savez ce que vous changez.", d, pre_d))
    # plusieurs dossiers livrés au même endroit : leur ordre entre eux est celui que l'auteur a voulu (sa demande du 16/11).
    # Si les noms proposés le changent, par octets ou sans la casse, tous gardent leur nom.
    for parent in sorted(set(dirs.values())):
        freres = [o for o, p in dirs.items() if p == parent]
        if len(freres) < 2 or not any(o in voulu for o in freres):
            continue
        avant = {o: o.split("/")[-1] for o in freres}
        apres = {o: voulu.get(o, avant[o]) for o in freres}
        if any(sorted(freres, key=lambda o: k(avant[o])) != sorted(freres, key=lambda o: k(apres[o])) for k in (str.lower, lambda t: t)):
            for o in freres:
                if o in voulu:
                    dir_map.pop(o, None)
                    if o in leve_de:
                        leves.discard(leve_de[o])
                        cible.pop(leve_de[o], None)
                    garde[o] = T("renommer changerait l'ordre des dossiers voulu par l'auteur")
                communs.add(o)
            out["notes"].append(T("`{0}` : ce mod y livre {1} dossiers ; les noms proposés changeraient leur ordre, ils gardent ceux de l'auteur.", parent, len(freres)))

    # 2. fichiers .archive / .xl / .yaml / .reds
    def ext(f):
        lf = f.lower()
        return ".xl" if lf.endswith(".xl") else ".yaml" if lf.endswith(".yml") else os.path.splitext(lf)[1]
    def tige(f):
        return re.sub(r"(?i)(\.archive)?\.xl$|\.(archive|yaml|yml|reds)$", "", os.path.basename(f))
    cands = [f for f in files if ext(f) in (".archive", ".xl", ".yaml", ".reds") and not f.lower().startswith(JAMAIS) and f not in leves]
    count = collections.Counter(ext(f) for f in cands)
    archives = [f for f in cands if ext(f) == ".archive"]
    def citee(stem, autres):
        s = stem.lower()
        return next(((k, f) for k, f, c in cites("a", autres) if (c == s or re.search(r"(?<![a-z0-9])" + re.escape(s) + r"$", c))
                     and os.path.basename(f) not in cfg["listes_de_conflits"]), None)
    longues = [f for f in archives if len(coupe_prefixe(tige(f))[1]) > 3]
    tenue = next(((f, citee(tige(f), False), "le code du mod") for f in longues if citee(tige(f), False)), None) \
        or next(((f, citee(tige(f), True), "un autre mod") for f in longues if citee(tige(f), True)), None)
    if tenue:
        f0, (k0, par), qui = tenue
        out["notes"].append(T("`{0}` est citée en dur par un autre mod ({1}, {2}) : `.archive` et `.xl` gardés au nom du créateur.",
                              os.path.basename(f0), os.path.basename(par), k0.split('/')[-1]) if qui == "un autre mod" else
                            T("`{0}` est citée en dur par le code du mod ({1}) : `.archive` et `.xl` gardés au nom du créateur.",
                              os.path.basename(f0), os.path.basename(par)))
        dir_map.clear()
    force = {}
    if match(mod["section"], cfg["piles_nom_complet"]) and archives and not tenue:
        st = [tige(a) for a in archives]
        s0 = min(st, key=len)
        if all(s.lower().startswith(s0.lower()) for s in st):   # variantes : le suffixe reste (`…_Black`)
            force = {s.lower(): base + s[len(s0):] for s in st}
            xl = [tige(x) for x in cands if ext(x) == ".xl"]
            if len(xl) == 1:
                force[xl[0].lower()] = base
    # dossier de famille : un zip « Tête - Nom » dont les frères de même tête (au moins deux, et la plupart de ceux qui
    # livrent là) rangent scripts ou tweaks sous un même sous-dossier. Lu dans le dépôt, jamais deviné d'un nom.
    tete = mod["nom"].split(" - ")[0].strip() if " - " in mod["nom"] else ""
    freres_tete = [m for k, m in index.items() if tete and k != key and m["genre"] != "retiré" and m["nom"].startswith(tete + " - ")
                   and ident(m["nom"]) != ident(mod["nom"])]
    dits = set()
    def dossier_famille(parent):
        if parent.lower() not in ("r6/scripts", "r6/tweaks") or not freres_tete:
            return None
        sous, livrent = collections.Counter(), 0
        for m in freres_tete:
            la = [e["d"][len(parent) + 1:] for e in m["entrees"] if e.get("d") and e["d"].lower().startswith(parent.lower() + "/")]
            livrent += bool(la)
            sous.update({x.split("/")[0] for x in la if "/" in x})
        if not sous:
            return None
        nom_d, n = sous.most_common(1)[0]
        return (nom_d, n) if n >= 2 and n * 2 > livrent else None
    arch_cible = {}
    for f in archives:
        d, stem = os.path.dirname(f), tige(f)
        pre, bare = coupe_prefixe(stem)
        if tenue:
            arch_cible[stem.lower()] = stem
            continue
        if stem.lower() in force:
            new = force[stem.lower()]
        elif en_convention(stem, gardes_mots) and avec_cat(bare) == bare:
            new = stem
        else:
            core = bare if en_convention(stem, gardes_mots) else (base if len(archives) == 1 and not famille else mots_capitalises(bare, gardes_mots))
            new = pre + avec_cat(core)
        arch_cible[stem.lower()] = new
        cible[f] = f"{d}/{new}.archive"
    for f in cands:
        e = ext(f)
        if e == ".archive":
            continue
        d, stem = os.path.dirname(f), tige(f)
        pre, bare = coupe_prefixe(stem)
        suffixe = ".xl" if e == ".xl" else os.path.splitext(f)[1]
        if e == ".xl":
            if tenue:
                new = stem
            elif stem.lower() in force:
                new = force[stem.lower()]
            elif stem.lower() in arch_cible:
                new = arch_cible[stem.lower()]
            elif count[".xl"] == 1 and len(archives) == 1:
                new = next(iter(arch_cible.values()))
            else:                                    # .xl dérivé d'une archive : nom de l'archive + suffixe
                k = max((k for k in arch_cible if bare.lower().startswith(k + "_")), key=len, default=None)
                new = pre + arch_cible[k] + "_" + mots_capitalises(bare[len(k) + 1:], gardes_mots) if k \
                    else pre + avec_cat(bare if en_convention(stem, gardes_mots) else mots_capitalises(bare, gardes_mots))
        else:                                        # .reds / .yaml : seul de son type, il prend le nom du mod
            nom = os.path.basename(f).lower()
            hit = next(((k, cf) for k, rl in refs.items() for cf, g, c in rl if g == "f" and c == nom
                        and not (k == key and work.get(cf, cf) == f)), None)
            if any(d == c or d.startswith(c + "/") for c in communs) or en_convention(stem, gardes_mots) or count[e] > 1:
                new = stem
            elif hit:
                garde[f] = T("cité en dur par {0} ({1})", os.path.basename(hit[1]), hit[0].split('/')[-1])
                new = stem
            else:
                new = pre + base
            fam = dossier_famille(d) if f not in garde else None
            if fam:                                  # le dossier où la famille du zip range déjà ses scripts ou ses tweaks
                d = f"{d}/{fam[0]}"
                if fam[0] not in dits:
                    dits.add(fam[0])
                    out["notes"].append(T("`{0}` : dossier où {1} autres mods « {2} - … » du dépôt rangent déjà les leurs ; la proposition y range ceux de ce mod.", fam[0], fam[1], tete))
        cible[f] = f"{d}/{new}{suffixe}" if d else f"{new}{suffixe}"

    # 3. ordre de chargement des .archive et des .xl du mod et de sa famille : s'il change, ils gardent leur nom
    def ordre_change(e):
        new_of = {os.path.basename(f): os.path.basename(cible.get(f, f)) for f in cands if ext(f) == e and f.lower().startswith(ARCH_DIR)}
        for k in famille:
            new_of.update({os.path.basename(x["d"]): os.path.basename(x["d"]) for x in index[k]["entrees"]
                           if x["d"] and x["d"].lower().startswith(ARCH_DIR) and ext(x["d"]) == e})
        return any([new_of[a] for a in sorted(new_of, key=k)] != sorted(new_of.values(), key=k) for k in (str.lower, None))
    if not tenue and (ordre_change(".archive") or ordre_change(".xl")):
        for f in [f for f in cands if ext(f) in (".archive", ".xl")]:
            cible[f] = f[:-11] + ".xl" if f.lower().endswith(".archive.xl") else f
        out["notes"].append(T("Le renommage changerait l'ordre de chargement entre les `.archive` / `.xl` de ce mod : gardés au nom du créateur."))

    # 4. chemins finaux : un fichier suit son dossier renommé ; deux fichiers ne visent jamais la même cible
    pris = collections.Counter()
    final = {}
    for n, w in work.items():
        new = cible.get(w, w)
        for o, nd in dir_map.items():
            if w not in leves and (new == o or new.startswith(o + "/")):
                new = nd + new[len(o):]
        final[n] = new
        pris[new.lower()] += 1
    autres = {n.lower() for n in names if n not in work}
    for n, new in sorted(final.items()):
        if new != n and (pris[new.lower()] > 1 or new.lower() in autres):
            garde[work[n]] = T("cible `{0}` déjà prise", new)
            new = work[n]
            if new != n and new.lower() in autres:
                new = n
        if new != n:
            out["ops"].append({"de": n, "vers": new})
    out["gardes"] = [{"chemin": c, "raison": r} for c, r in sorted(garde.items())]
    vus = {o["de"] for o in out["ops"]}                  # le reste de ce que le zip pose : rien de proposé, mais retouchable
    out["fichiers"] = sorted(n for n in work if n not in vus)
    if top:
        out["notes"].append(T("Tout le mod est sous le dossier `{0}/` : il est remonté à la racine du zip.", top))
    return dict(out, etat="a_renommer" if out["ops"] else "conforme")


def reecrit_zip(path, renommes):
    """récrit un zip avec des entrées renommées ({ancien: nouveau}) : contenu, dates et compression gardés ; contrôlé avant de remplacer"""
    tmp = path + ".red_stack_tmp"
    try:
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w") as dst:
            n = 0
            for i in src.infolist():
                if i.is_dir():
                    continue
                name = i.filename.replace("\\", "/").lstrip("/")
                j = zipfile.ZipInfo(renommes.get(name, i.filename), i.date_time)
                j.compress_type, j.external_attr = i.compress_type, i.external_attr
                with src.open(i) as s, dst.open(j, "w", force_zip64=True) as d:
                    shutil.copyfileobj(s, d, 1 << 20)
                n += 1
        with zipfile.ZipFile(tmp) as z:
            if z.testzip() is not None or len(z.namelist()) != n:
                sys.exit(T("Zip récrit puis relu différent : original gardé."))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return n


# ---------------------------------------------------------------- noms dans le jeu (profil)
# Ce qu'un mod pose sous un nom qui lui est propre, et que le PROFIL peut poser sous un autre nom sans toucher au zip :
# une `.archive` ou un `.xl` de archive/pc/mod, un fichier ou un dossier direct de r6/scripts, r6/tweaks, r6/audioware,
# le dossier d'un mod CET, le dossier d'un mod REDmod. Le profil note `renomme` entrée par entrée ; le plan pose le nouveau
# nom et retire l'ancien. Avant de renommer, l'index des références dit qui cite ce nom (le mod lui-même compris).
UNITES = (("archive/pc/mod", "fichier"), ("r6/scripts", "tout"), ("r6/tweaks", "tout"), ("r6/audioware", "tout"),
          (_CET + "mods", "dossier"), ("mods", "dossier"))
NOTES_UNITE = {"tweaks": T("TweakXL lit r6/tweaks dans l'ordre des noms : un autre nom peut changer qui a le dernier mot."),
               "cet": T("Ce que ce mod a écrit dans son dossier en jeu (réglages, favoris) reste sous l'ancien nom, gardé."),
               "redmod": T("REDmod range ses mods par nom de dossier (ordre compris) ; `info.json` garde le nom de l'auteur.")}


def unites_du_mod(mod, mp):
    """[{genre, chemin (auteur), nom, actuel, dossier, mixte, entrees}] : ce qui se renomme dans le jeu, d'un seul geste"""
    ren = (mp or {}).get("renomme", {})
    out = {}
    for e in mod["entrees"]:
        if e["o"] is None or not e["d"]:
            continue
        dl = e["d"].lower()
        for parent, mode in UNITES:
            if not dl.startswith(parent + "/"):
                continue
            reste = e["d"][len(parent) + 1:]
            seg, dossier = reste.split("/")[0], "/" in reste
            if (mode == "fichier" and dossier) or (mode == "dossier" and not dossier):
                break
            genre = {"archive/pc/mod": "archive" if seg.lower().endswith(".archive") else "xl" if seg.lower().endswith(".xl") else "",
                     _CET + "mods": "cet", "mods": "redmod"}.get(parent, parent.split("/")[-1])
            if not genre:
                break
            chemin = e["d"][:len(parent) + 1 + len(seg)]
            u = out.setdefault(chemin.lower(), {"genre": genre, "chemin": chemin, "nom": seg, "dossier": dossier, "entrees": [], "vus": set()})
            u["entrees"].append(e)
            u["vus"].add("/".join(ren.get(e["n"], e["d"]).split("/")[:chemin.count("/") + 1]))
            break
    res = []
    for k in sorted(out):
        u = out[k]
        vus = u.pop("vus")
        u["mixte"] = len(vus) > 1                    # renommé fichier par fichier, à la main : pas un seul nom à montrer
        u["actuel"] = u["nom"] if u["mixte"] else next(iter(vus)).split("/")[-1]
        res.append(u)
    return res


def cites_unite(u, key, refs, hors_listes):
    """qui cite cette unité par son nom d'auteur dans le code du dépôt : [{zip, fichier, soi}]"""
    nom = u["nom"].lower()
    if u["genre"] == "archive":
        ok = lambda g, t: g == "a" and t == nom[:-len(".archive")]
    elif u["genre"] == "cet":
        ok = lambda g, t: g == "m" and t == nom
    elif u["genre"] in ("scripts", "tweaks", "audioware") and u["dossier"]:
        cite = u["genre"] + "/" + nom
        ok = lambda g, t: g == "d" and (t == cite or (t.startswith(cite) and not re.match(r"[a-z0-9_]", t[len(cite):])))
    elif u["genre"] in ("scripts", "tweaks"):
        ok = lambda g, t: g == "f" and t == nom
    else:
        return []
    return [{"zip": k, "fichier": f, "soi": k == key} for k, f in sorted({(k, f) for k, rows in refs.items() for f, g, t in rows
                                                                          if ok(g, t) and f.split("/")[-1].lower() not in hors_listes})]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=["index", "adopte", "etat", "bascule", "option", "priorite", "plan", "applique",
                                       "reglage", "retouche", "purge", "config", "profils", "detail", "fichier", "hors", "reference",
                                       "conflits", "deplace", "convention", "contenu", "ordre", "noms", "scripts", "journal",
                                       "magasin", "sauvegarde", "nexus", "fomod", "prerequis", "objets"])
    ap.add_argument("--requis", help="prerequis on|off --cle CLE --ignore --requis IDENT : ne plus compter (on) ou compter de nouveau (off) "
                    "ce prérequis pour ce mod ; IDENT est l'`ident` rendu par `prerequis --mod`")
    ap.add_argument("--nexus", action="store_true", help="prerequis : lit d'abord sur Nexus les prérequis des mods qui ne sont pas "
                    "au cache (--mod : de ce mod seul ; --force : de tous, même lus il y a peu)")
    ap.add_argument("--convertit", action="store_true", help="convention : change le .7z / .rar de --cle en .zip")
    ap.add_argument("valeur", nargs="?", choices=["on", "off"])
    ap.add_argument("--profil", default="actuel")
    ap.add_argument("--mod")
    ap.add_argument("--section")
    ap.add_argument("--nom")
    ap.add_argument("--entree", help="option : un seul fichier du zip (son chemin dans le zip), à prendre ou à laisser")
    ap.add_argument("--mien", action="store_true",
                    help="option --entree : « ce fichier est à ce mod », pour un fichier présent sous un motif hors Red Stack")
    ap.add_argument("--ressources", action="store_true", help="conflits : la liste de toutes les ressources en conflit")
    ap.add_argument("--tout", action="store_true",
                    help="conflits --mod / --nom : aussi les ressources que ces archives sont seules à livrer (sans conflit)")
    ap.add_argument("--gagnant")
    ap.add_argument("--perdant")
    ap.add_argument("--fichier", help="priorite : chemin d'UN fichier du jeu ; --gagnant le tient, quelle que soit la règle entre mods")
    ap.add_argument("--jeu", help="racine du jeu (défaut : config.json)")
    ap.add_argument("--depot", help="racine du dépôt de zips (défaut : config.json)")
    ap.add_argument("--donnees", help="dossier des données de l'outil (défaut : « red_stack » à côté du script)")
    ap.add_argument("--fixe", help="config : objet JSON des clés à écrire dans config.json (« - » : lu sur l'entrée standard)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--langue", help="langue des textes (fr, en…) : un catalogue `langues/<code>.json` ; les états du JSON restent des codes")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--remplace", action="append", default=[], metavar="DEST",
                    help="plan, applique : remplace par le zip CE fichier présent que l'outil n'a pas posé (répétable ; l'ancien est copié dans les sauvegardes)")
    ap.add_argument("--vrai-jeu", action="store_true")
    ap.add_argument("--magasin", help="racine des arbres par mod (défaut : « <jeu> - Red Stack », à côté du jeu)")
    ap.add_argument("--sans-magasin", action="store_true", help="pose directe depuis les zips, sans arbre ni lien")
    ap.add_argument("--ajoute", help="reglage : motif à ne jamais lier (ex. bin/x64/plugins/cyber_engine_tweaks/mods/MonMod/etat.lua)")
    ap.add_argument("--retire", help="reglage : motif à enlever de la liste de l'utilisateur")
    ap.add_argument("--annule", action="store_true", help="retouche : remet dans l'arbre les fichiers du zip")
    ap.add_argument("--copie", help="profils : crée --profil à partir de ce profil")
    ap.add_argument("--supprime", action="store_true", help="profils : supprime --profil ; journal --de CHEMIN : inscrit la suppression "
                    "d'un zip retiré, faite hors du moteur (corbeille du système), refusé si le zip est toujours là")
    ap.add_argument("--cree", action="store_true", help="reference : copie le jeu (vierge) sans ses archives ; sauvegarde : en fait une")
    ap.add_argument("--restaure", action="store_true", help="reference : remet dans le jeu les fichiers du socle changés ou disparus ; "
                    "sauvegarde --nom NOM : remet les réglages de cette sauvegarde")
    ap.add_argument("--reference", help="dossier de la référence (défaut : config.json, sinon « <jeu> - Référence »)")
    ap.add_argument("--cle", help="deplace : clé exacte du zip dans l'index (pile/[dossier/]nom.zip)")
    ap.add_argument("--vers", choices=["parques", "pile", "retires"], help="deplace : vers le dossier des parqués de sa pile, vers celui des retirés, ou vers la racine de sa pile")
    ap.add_argument("--dossier", help="deplace --vers parques : nom du dossier (défaut : celui qui existe, sinon tiré de la convention)")
    ap.add_argument("--avant", help="ordre : l'archive --nom doit se charger avant celle-ci (elle gagne sur elle)")
    ap.add_argument("--apres", help="ordre : l'archive --nom doit se charger après celle-ci (elle perd contre elle)")
    ap.add_argument("--voie", choices=["nom", "modlist"], default="nom",
                    help="ordre --avant / --apres : proposer un nom (défaut, rien écrit), ou écrire l'ordre voulu de modlist.txt au profil")
    ap.add_argument("--renomme", help="ordre --nom : nom de cette archive dans le jeu, noté au profil (le zip ne change pas)")
    ap.add_argument("--modlist", action="store_true", help="ordre --annule : ne plus tenir modlist.txt (retiré du jeu au prochain applique)")
    ap.add_argument("--geste", help="journal : un seul geste (applique, parque, remonte, retire, supprime, renomme, convertit, contenu)")
    ap.add_argument("--depuis", help="journal : entrées à partir de cette date (AAAA-MM-JJ, heure possible)")
    ap.add_argument("--limite", type=int, help="journal : nombre d'entrées rendues au plus (défaut 50), les plus récentes d'abord")
    ap.add_argument("--compte", action="store_true", help="nexus : le compte de la clé d'API (variable RED_STACK_NEXUS_KEY), rien d'autre")
    ap.add_argument("--lien", help="nexus : lien `nxm://…` du bouton « Mod manager download ». Avec --cle : télécharge à la place de ce zip. "
                    "Seul : dit quels zips il met à jour. Avec --section PILE : range ce mod nouveau dans le dossier d'arrivée de la pile")
    ap.add_argument("--range", action="store_true", help="convention --cle ARRIVAGE --de ZIP [--nom NOM] : l'arrivage prend la place du zip "
                    "qu'il met à jour, l'ancienne version part dans les retirés de sa pile")
    ap.add_argument("--de", help="convention --range : clé du zip en place que l'arrivage met à jour ; journal --supprime : chemin du zip supprimé")
    ap.add_argument("--designe", action="store_true", help="convention --range : l'utilisateur désigne lui-même le zip remplacé ; ni le modId, "
                    "ni le nom, ni la version ne sont comparés, l'arrivage garde son nom (ou --nom)")
    ap.add_argument("--ignore", action="store_true", help="nexus on|off --cle CLE --ignore : ne plus proposer / reproposer les mises à jour de ce mod")
    ap.add_argument("--partie", help="objets : la sauvegarde de partie à lire (nom de son dossier, ou chemin du dossier ou de son sav.dat) ; "
                    "défaut : la plus récente du dossier des parties")
    ap.add_argument("--si-plan", help="applique : empreinte du plan vu à l'aperçu ; refuse si le plan a changé")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    data = os.path.abspath(a.donnees or os.path.join(os.path.dirname(os.path.abspath(__file__)), "red_stack"))
    conf_path = os.path.join(data, "config.json")
    conf = load_conf(data)
    out = lambda obj, text: print(json.dumps(obj, ensure_ascii=False, indent=1) if a.json else text)

    def save_conf():
        os.makedirs(data, exist_ok=True)
        json.dump(conf, open(conf_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if a.action == "config":                         # montre la configuration ; --depot / --jeu / --magasin / --fixe l'écrivent
        change = False
        for k in ("depot", "jeu", "magasin"):
            if getattr(a, k):
                conf[k] = os.path.abspath(getattr(a, k))
                change = True
        if a.fixe:
            try:
                neuf = json.loads(sys.stdin.buffer.read().decode("utf-8") if a.fixe == "-" else a.fixe)
            except ValueError as e:
                sys.exit(T("config --fixe : JSON illisible ({0})", e))
            conf_fixe(conf, neuf)
            change = True
        if change:
            save_conf()
            conf = load_conf(data)
        v = conf_view(conf, data, conf_path)
        return out(v, f"{conf_path}\n" + "\n".join("  " + k + " : " + (v[k] or T("(défaut) ") + v['effectif'].get(k, '')) for k in CHEMINS)
                   + T("\n  convention (motifs sur les noms de dossiers) :\n")
                   + "\n".join(f"    {k} : {', '.join(x)}" for k, x in v["convention"].items())
                   + T("\n  hors Red Stack : {0}", ', '.join(v['hors']) or T("(rien)"))
                   + T("\n  avant d'appliquer : {0}", ' '.join(v['avant_applique']) or T("(rien)")))
    if a.action == "journal":                        # historique des gestes qui ont écrit, du plus récent au plus ancien
        if a.supprime:                               # suppression faite par l'extension (corbeille du système) : le moteur l'inscrit
            if not a.de or not os.path.isabs(a.de) or not a.de.lower().endswith(".zip"):
                sys.exit(T("journal --supprime : --de <chemin complet du zip supprimé>"))
            if os.path.exists(a.de):
                sys.exit(T("Ce zip est toujours là, rien n'est inscrit : {0}", a.de))
            historise(data, "supprime", de=a.de)
            return out({"geste": "supprime", "de": a.de, "ecrit": True}, T("Suppression inscrite à l'historique : {0}", a.de))
        ents = lit_historique(data)
        total = len(ents)
        if a.geste:
            ents = [e for e in ents if e.get("geste") == a.geste]
        if a.depuis:
            ents = [e for e in ents if e.get("date", "") >= a.depuis]
        if a.mod:                                    # texte du nom d'un zip : ses lignes seulement
            t, garde = a.mod.lower(), []
            for e in ents:
                if "mods" in e:
                    ms = [m for m in e["mods"] if t in m["cle"].lower()]
                    if ms:
                        garde.append(dict(e, mods=ms))
                elif t in (str(e.get("de", "")) + " " + str(e.get("vers", ""))).lower():
                    garde.append(e)
            ents = garde
        trouve = len(ents)
        ents = ents[::-1][:a.limite or 50]
        txt = []
        for e in ents:
            if "mods" in e:
                txt.append(f"{e['date']}  applique  profil {e.get('profil', '')}  "
                           + ", ".join(f"{v} {k}" for k, v in e.get("compte", {}).items()))
                txt += [f"    {m['fait']} : {m['cle']}" + (f" (depuis {m['depuis']})" if m.get("depuis") else "") for m in e["mods"]]
            else:
                txt.append(f"{e['date']}  {e['geste']}  {e.get('de', '')}" + (f"  ->  {e['vers']}" if e.get("vers") else ""))
        return out({"fichier": os.path.join(data, "historique.jsonl"), "total": total, "trouve": trouve, "entrees": ents},
                   "\n".join(txt) or T("Historique vide : aucun geste n'a écrit depuis que Red Stack le tient."))
    real_game = conf.get("jeu", "")
    a.depot, a.jeu = a.depot or conf.get("depot"), a.jeu or real_game
    if not a.depot or not a.jeu:
        sys.exit(T("Dépôt ou jeu inconnu : `config --depot <racine des zips> --jeu <racine du jeu>` (écrit {0})", conf_path))
    stamp = os.path.join(conf.get("sauvegardes") or os.path.join(data, "sauvegardes"),
                         "_red_stack_" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    store = None if a.sans_magasin else Magasin(a.magasin or conf.get("magasin") or a.jeu.rstrip("\\/") + " - Red Stack",
                                                conf["reglages"], stamp)
    index = load_index(a.depot, data)
    jeu = Jeu(a.jeu, data)
    real = bool(real_game) and os.path.normcase(os.path.abspath(a.jeu)) == os.path.normcase(os.path.abspath(real_game))

    if a.action == "index":
        rows = [{"cle": k, "section": m["section"], "lieu": m["lieu"] or "actif", "genre": m["genre"], "version": version_de(m),
                 "taille": m["taille"], "entrees": len(m["entrees"]), "options": options_of(m)} for k, m in index.items()]
        picks = [r for r in rows if r["lieu"] == "actif" and set(r["options"]) - {""}]
        txt = [T("{0} zips ({1} actifs), {2} entrées ; {3} zips actifs à options :", len(rows), sum(1 for r in rows if r['lieu'] == 'actif'), sum(r['entrees'] for r in rows), len(picks))]
        txt += [f"  {r['cle']} : " + ", ".join(f"{o or 'direct'} ({n})" for o, n in r["options"].items()) for r in picks]
        return out(rows, "\n".join(txt))

    if a.action == "reglage":
        norm = lambda s: s.replace("\\", "/").lower()
        if a.ajoute and norm(a.ajoute) not in conf["reglages"]:
            conf["reglages"].append(norm(a.ajoute))
        if a.retire:
            conf["reglages"] = [p for p in conf["reglages"] if p != norm(a.retire)]
        if a.ajoute or a.retire:
            save_conf()
        return out({"defaut": REGLAGES, "utilisateur": conf["reglages"]},
                   T("Réglages (jamais liés, gardés tels qu'ils sont dans le jeu)\n  par défaut :\n")
                   + "\n".join("    " + p for p in REGLAGES) + T("\n  ajoutés :\n") + "\n".join("    " + p for p in conf["reglages"])
                   + (T("\nUn fichier déjà lié qui devient un réglage est délié au prochain `applique`.") if a.ajoute else ""))

    if a.action == "hors":
        norm = lambda s: s.replace("\\", "/").strip("/").lower()
        if a.ajoute and norm(a.ajoute) not in conf["hors"]:
            conf["hors"].append(norm(a.ajoute))
        if a.retire:
            conf["hors"] = [p for p in conf["hors"] if p != norm(a.retire)]
        if a.ajoute or a.retire:
            save_conf()
        return out({"hors": conf["hors"]},
                   T("Hors Red Stack (fichiers d'un installateur tiers : présents, ils ne sont jamais liés, remplacés, retirés ni comptés à un mod ;\nabsents, ils sont posés en copie pour le mod qui les prend)\n")
                   + "\n".join("    " + p for p in conf["hors"])
                   + (T("\nLes fichiers déjà attribués à un mod sous ce motif lui sont repris au prochain `applique` (déliés, laissés en place).")
                      if a.ajoute else ""))

    if a.action == "adopte":
        prof, pose, rapport = adopt(index, jeu)
        prof["nom"] = a.profil
        save_profil(data, a.profil, prof)
        jeu.save_pose(pose)
        jeu.save()
        seen = [r["dest"].lower() for r in pose.values() if not jeu.same(r["dest"], r["crc"], r["taille"])]
        new = [d for d in seen if d not in conf["reglages"] and not (store or Magasin(".")).est_reglage(d)]
        if new:                                      # livré puis modifié en jeu = réglage, par constat
            conf["reglages"] += new
            save_conf()
        c = collections.Counter(r["etat"] for r in rapport.values())
        txt = [T("Profil « {0} » écrit : {1}", a.profil, profil_path(data, a.profil)),
               T("réglages constatés (modifiés en jeu), ajoutés à la liste : {0}", len(new)),
               T("zips actifs : {0} ; fichiers reconnus dans le jeu : {1} ; priorités observées : {2}", dict(c), len(pose), len(prof['priorites']))]
        for etat in ("partiel", "absent", "non posable"):
            txt.append(f"\n{etat} :")
            txt += [f"  {k}  " + ", ".join(f"{n} {v}" for n, v in r.items() if n not in ("etat",) and v)
                    for k, r in rapport.items() if r["etat"] == etat]
        txt.append(T("\npriorités (gagnant > perdant) :"))
        txt += [f"  {w}  >  {l}" for w, l in prof["priorites"]]
        return out({"rapport": rapport, "priorites": prof["priorites"]}, "\n".join(txt))

    if a.action == "profils":
        pdir = os.path.join(data, "profils")
        if a.copie:
            if not re.fullmatch(r"[\w .\-]{1,60}", a.profil) or os.path.isfile(profil_path(data, a.profil)):
                sys.exit(T("Nom de profil refusé ou déjà pris : {0}", a.profil))
            src, _ = load_profil(data, a.copie, index, jeu.load_pose())
            src["nom"] = a.profil
            save_profil(data, a.profil, src)
        elif a.supprime:
            if a.profil == "actuel" or not os.path.isfile(profil_path(data, a.profil)):
                sys.exit(T("Profil introuvable, ou « actuel » (jamais supprimé) : {0}", a.profil))
            os.remove(profil_path(data, a.profil))
        rows = []
        for f in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
            if f.lower().endswith(".json"):
                pr = json.load(open(os.path.join(pdir, f), encoding="utf-8"))
                rows.append({"nom": f[:-5], "actifs": sum(1 for m in pr["mods"].values() if m.get("actif")),
                             "mods": len(pr["mods"]), "priorites": len(pr.get("priorites", []))})
        return out({"profils": rows}, "\n".join(T("  {0} : {1} actifs sur {2}", r['nom'], r['actifs'], r['mods']) for r in rows))

    if a.action == "fichier":
        t = (a.nom or "").replace("\\", "/").lower()
        if len(t) < 3:
            sys.exit(T("fichier : --nom TEXTE (trois caractères au moins)"))
        rows = [dict(r, lie=bool(store and store.lie_key(r["zip"], r["entree"], jeu.path(r["dest"]))),
                     reglage=bool(store and store.est_reglage(r["dest"])))
                for dl, r in sorted(jeu.load_pose().items()) if t in dl]
        return out({"fichiers": rows[:500], "total": len(rows)},
                   f"{len(rows)} fichier(s)\n" + "\n".join(f"  {r['dest']}  <-  {r['zip']}" for r in rows[:200]))

    if a.action == "reference":
        ref = a.reference or conf.get("reference") or a.jeu.rstrip("\\/") + " - Référence"
        mark = os.path.join(ref, REF_MARK)
        exclus = conf.get("reference_exclus", REF_EXCLUS)
        reg = jeu.load_pose()
        if a.cree:
            if os.path.isfile(mark):
                sys.exit(T("Une référence existe déjà : {0} (la supprimer à la main pour la refaire)", ref))
            if reg and not a.force:
                sys.exit(N(len(reg), "Le jeu n'est pas vierge : {n} fichier posé par des mods. La référence se crée sur un jeu vierge, avant l'adoption ; --force la crée quand même, marquée « non vierge ».", "Le jeu n'est pas vierge : {n} fichiers posés par des mods. La référence se crée sur un jeu vierge, avant l'adoption ; --force la crée quand même, marquée « non vierge »."))
            if real and game_running():
                sys.exit(T("Le jeu tourne : le fermer d'abord."))
            files, total = {}, 0
            for rel in ref_files(a.jeu, exclus):
                if rel.lower() in reg:               # posé par un mod : pas du socle, laissé hors de la référence
                    continue
                t = Magasin.lp(os.path.join(ref, rel.replace("/", os.sep)))
                os.makedirs(os.path.dirname(t), exist_ok=True)
                shutil.copy2(jeu.path(rel), t)
                crc = 0
                with open(t, "rb") as f:             # CRC relu sur la COPIE : elle est ce qu'on restaurera
                    for b in iter(lambda: f.read(1 << 20), b""):
                        crc = zipfile.crc32(b, crc)
                files[rel] = [os.path.getsize(t), crc & 0xFFFFFFFF]
                total += files[rel][0]
            json.dump({"cree": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "jeu": a.jeu, "vierge": not reg,
                       "exclus": exclus, "fichiers": files}, open(mark, "w", encoding="utf-8"), ensure_ascii=False)
            if not a.reference:
                conf["reference"] = ref
                save_conf()
            return out({"reference": ref, "fichiers": len(files), "taille": total, "vierge": not reg},
                       suite(suite(T("Référence créée : {0}\n  {1} fichiers, {2} Go", ref, len(files), f"{total / 1e9:.1f}"),
                                   T("jeu vierge") if not reg else T("JEU NON VIERGE (mods présents)"), sep=T(", ")), T("dossiers exclus : {0}", ', '.join(exclus))))
        if not os.path.isfile(mark):
            sys.exit(T("Aucune référence : {0}\nLa créer sur un jeu vierge par `reference --cree`.", ref))
        m = json.load(open(mark, encoding="utf-8"))
        modifies, manquants, par_mod = [], [], []
        for rel, (size, crc) in m["fichiers"].items():
            if jeu.size(rel) is None:
                manquants.append(rel)
            elif not jeu.same(rel, crc, size):
                (par_mod if rel.lower() in reg else modifies).append(rel)
        jeu.save()
        connus = {r.lower() for r in m["fichiers"]}
        ajoutes = sum(1 for rel in ref_files(a.jeu, m["exclus"]) if rel.lower() not in connus and rel.lower() not in reg)
        todo = modifies + manquants
        if a.restaure and a.go and todo:
            if real and not a.vrai_jeu:
                sys.exit(T("Cible = le vrai jeu : ajouter --vrai-jeu (jeu fermé)."))
            if real and game_running():
                sys.exit(T("Le jeu tourne : le fermer d'abord."))
            for rel in todo:
                src, target = Magasin.lp(os.path.join(ref, rel.replace("/", os.sep))), jeu.path(rel)
                size, crc = m["fichiers"][rel]
                if not os.path.isfile(src) or os.path.getsize(src) != size:
                    sys.exit(T("Référence abîmée, restauration arrêtée : {0}", rel))
                if os.path.isfile(target):           # ce que la mise à jour avait mis : copié avant d'être remplacé
                    b = os.path.join(stamp, "reference", rel.replace("/", os.sep))
                    os.makedirs(os.path.dirname(b), exist_ok=True)
                    shutil.copy2(target, b)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                drop(target)
                shutil.copy2(src, target)
            jeu.save()
        fait = bool(a.restaure and a.go and todo)
        txt = [T("Référence {0} du {1}", ref, m['cree']) + ("" if m.get("vierge") else T(" (NON VIERGE)")) + f" : {len(m['fichiers'])} fichiers",
               T("socle changé {0}, disparu {1}, remplacé par un mod {2} ; fichiers du jeu hors référence et hors mods (créés en jeu, installateurs tiers) {3}", len(modifies), len(manquants), len(par_mod), ajoutes)]
        txt += [T("  ~ changé  : {0}", r) for r in modifies[:60]] + [f"  - disparu : {r}" for r in manquants[:60]]
        txt += [T("  = par un mod : {0}  ({1})", r, reg[r.lower()]['zip']) for r in par_mod[:60]]
        txt.append(N(len(todo), "RESTAURÉ : {n} fichier ; celui d'avant copié dans {0}", "RESTAURÉ : {n} fichiers ; ceux d'avant copiés dans {0}", stamp) if fait else
                   T("Le socle est celui de la référence.") if not todo else
                   T("Rien écrit : `reference --restaure --go` remet ces fichiers (jeu fermé).") )
        return out({"reference": ref, "cree": m["cree"], "vierge": bool(m.get("vierge")), "fichiers": len(m["fichiers"]),
                    "modifies": modifies, "manquants": manquants, "par_mod": par_mod, "ajoutes": ajoutes, "restaure": fait},
                   "\n".join(txt))

    if a.action == "sauvegarde":                     # réglages des mods : lister, sauver, restaurer
        racine = conf.get("sauvegardes") or os.path.join(data, "sauvegardes")
        regle = store or Magasin(".", conf["reglages"])
        if a.cree:
            lance = real and game_running()
            dossier = os.path.join(racine, SAUVE_PREFIXE + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"))
            files = {}
            for rel in reglages_du_jeu(jeu, regle):
                cible = Magasin.lp(os.path.join(dossier, rel.replace("/", os.sep)))
                os.makedirs(os.path.dirname(cible), exist_ok=True)
                shutil.copy2(jeu.path(rel), cible)
                files[rel] = [os.path.getsize(cible), crc_fichier(cible)]   # relu sur la COPIE : c'est elle qu'on restaurera
            if not files:
                sys.exit(T("Aucun fichier de réglages dans le jeu : rien à sauvegarder."))
            json.dump({"cree": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "jeu": a.jeu, "jeu_lance": lance, "fichiers": files},
                      open(os.path.join(dossier, SAUVE_MARK), "w", encoding="utf-8"), ensure_ascii=False)
            historise(data, "reglages", sens="sauve", de=dossier, fichiers=len(files))
        rows = sauvegardes_reglages(racine)
        if a.cree:
            r = rows[0]
            return out({"cree": r, "sauvegardes": rows, "dossier": racine},
                       T("Réglages sauvegardés : {0}\n  {1} fichiers, {2} Mo", r['chemin'], r['fichiers'], f"{r['octets'] / 1e6:.1f}")
                       + (T("\n  ! le jeu tournait : un fichier en cours d'écriture peut être incomplet") if r["jeu_lance"] else ""))
        if not a.restaure:
            return out({"sauvegardes": rows, "dossier": racine},
                       N(len(rows), "{n} sauvegarde de réglages dans {0}\n", "{n} sauvegardes de réglages dans {0}\n", racine)
                       + "\n".join(T("  {0}  {1}  {2} fichiers, {3} Mo", r['nom'], r['cree'], r['fichiers'], f"{r['octets'] / 1e6:.1f}") for r in rows))
        r = next((x for x in rows if x["nom"] == a.nom), None) if a.nom else (rows[0] if rows else None)
        if not r:
            sys.exit(T("sauvegarde --restaure : sauvegarde inconnue ({0}) ; `sauvegarde` les liste", a.nom or 'aucune'))
        m = json.load(open(os.path.join(r["chemin"], SAUVE_MARK), encoding="utf-8"))
        absents, changes = [], []
        for rel, (size, crc) in m["fichiers"].items():
            if jeu.size(rel) is None:
                absents.append(rel)
            elif not jeu.same(rel, crc, size):
                changes.append(rel)
        jeu.save()
        todo = absents + changes
        fait = bool(a.go and todo)
        if fait:
            if real and not a.vrai_jeu:
                sys.exit(T("Cible = le vrai jeu : ajouter --vrai-jeu (jeu fermé)."))
            if real and game_running():
                sys.exit(T("Le jeu tourne : le fermer d'abord."))
            for rel in todo:
                src, target = Magasin.lp(os.path.join(r["chemin"], rel.replace("/", os.sep))), jeu.path(rel)
                if not os.path.isfile(src) or os.path.getsize(src) != m["fichiers"][rel][0]:
                    sys.exit(T("Sauvegarde abîmée, restauration arrêtée : {0}", rel))
                if os.path.isfile(target):           # le réglage d'aujourd'hui : copié avant d'être remplacé
                    b = os.path.join(stamp, "reglages", rel.replace("/", os.sep))
                    os.makedirs(os.path.dirname(b), exist_ok=True)
                    shutil.copy2(target, b)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                drop(target)                         # jamais écrire à travers un lien vers le magasin
                shutil.copy2(src, target)
            historise(data, "reglages", sens="restaure", de=r["chemin"], fichiers=len(todo), sauvegarde=stamp if changes else None)
        return out({"sauvegarde": r, "absents": absents, "changes": changes, "identiques": len(m["fichiers"]) - len(todo),
                    "restaure": fait, "copies": stamp if fait and changes else None},
                   T("Sauvegarde {0} du {1} : {2} fichiers ; dans le jeu aujourd'hui : {3}, {4}\n", r['nom'], r['cree'], len(m['fichiers']), N(len(changes), "{n} différent", "{n} différents"), N(len(absents), "{n} absent", "{n} absents"))
                   + "\n".join([T("  ~ différent : {0}", x) for x in changes[:80]] + [f"  + absent : {x}" for x in absents[:80]])
                   + (suite(N(len(todo), "\nRESTAURÉ : {n} fichier", "\nRESTAURÉ : {n} fichiers"), T("ceux d'avant copiés dans {0}", stamp) if changes else "") if fait
                      else T("\nLes réglages du jeu sont ceux de la sauvegarde.") if not todo
                      else T("\nRien écrit : `sauvegarde --restaure --nom NOM --go` les remet (jeu fermé).")))

    def journal(ligne):
        logp = conf.get("journal") or os.path.join(data, "red_stack.log")
        os.makedirs(os.path.dirname(logp), exist_ok=True)
        with open(logp, "a", encoding="utf-8") as logf:
            print(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M} dépôt : {ligne}", file=logf)

    if a.action == "convention":                     # noms des archives : propose ; --fixe renomme, --convertit change en .zip
        if a.convertit:
            src = chemin_de_cle(a.depot, a.cle)
            if not src or not src.lower().endswith(AUTRES_ARCHIVES):
                sys.exit(T("convention --convertit : --cle doit désigner un .7z ou un .rar d'une pile ; reçu : {0}", a.cle))
            r = convertit(src, conf, a.go)
            if r["ecrit"]:
                journal(T("converti {0} -> {1} ({2} fichiers, {3})", r['de'], r['vers'], r['fichiers'], r['outil']))
                historise(data, "convertit", de=r["de"], vers=r["vers"], fichiers=r["fichiers"])
            return out(r, f"{r['de']}  ->  {r['vers']} ({r['outil']}) : " + (T("fait.") if r["ecrit"] else T("rien écrit, relancer avec --go.")))
        if a.range:                                  # un arrivage est la mise à jour du zip --de : il prend sa place
            src, m = chemin_de_cle(a.depot, a.cle), index.get(a.de or "")
            if not src or not src.lower().endswith(".zip"):
                sys.exit(T("convention --range : --cle doit désigner un .zip d'une pile (un .7z ou un .rar se convertit d'abord) ; reçu : {0}", a.cle))
            if not m or m["genre"] in ("retiré", "nouveau") or os.path.normcase(m["zip"]) == os.path.normcase(src):
                sys.exit(T("convention --range : --de doit désigner le zip en place que cet arrivage met à jour ; reçu : {0}", a.de))
            w, v = RX_ZIP_NEXUS.match(m["nom"]), RX_ZIP_NEXUS.match(os.path.basename(src))
            local = None if w else next((c for c in cibles_locales(os.path.basename(src), index) if c["cle"] == a.de), None)
            if local or a.designe:                   # mod sans modId (même radical, version plus haute), ou zip désigné par l'utilisateur
                nom = (a.nom or "").strip() or os.path.basename(src)
                if INTERDITS.search(nom) or nom.endswith((" ", ".")) or len(nom) > 200 or not nom.lower().endswith(".zip"):
                    sys.exit(T("Nom refusé : « {0} » (caractères interdits \\ / : * ? \" < > |, ou fin par un espace ou un point)", nom))
                versions = (version(nom) or (ident_local(nom) or ("", (), "", ""))[3], version_de(m) or (ident_local(m["nom"]) or ("", (), "", ""))[3])
            else:
                if not w:
                    sys.exit(T("Le zip en place ne porte pas de modId dans son nom : {0}", m['nom']))
                nom = (a.nom or "").strip() or (nom_de_maj(w, {"version": (v["ver"] or "").replace("-", "."), "date": int(v["ts"])}) + v["tail"] + ".zip" if v else "")
                n = RX_ZIP_NEXUS.match(nom)
                if not n or INTERDITS.search(nom) or nom.endswith((" ", ".")) or len(nom) > 200:
                    sys.exit(T("Nom refusé : « {0} » (la forme du site est attendue, `Nom-modId-version-horodatage.zip` : renommer l'arrivage d'abord)", nom))
                if int((v or n)["mod"]) != int(w["mod"]) or int(n["mod"]) != int(w["mod"]):
                    sys.exit(T("Cet arrivage est du mod {0},le zip en place du mod {1} : ce n'est pas sa mise à jour.", int((v or n)['mod']), int(w['mod'])))
                if int(n["ts"]) <= int(w["ts"]):
                    sys.exit(T("Cet arrivage n'est pas plus récent que le zip en place : rien rangé."))
                versions = ((n["ver"] or "").replace("-", "."), (w["ver"] or "").replace("-", "."))
            base = dossier_pile(a.depot, m["section"])
            retires = dossier_convention(base, "retires")
            if not retires:
                sys.exit(T("Aucun dossier des retirés pour ranger l'ancienne version : la convention {0} ne donne pas de nom (Réglages).", CONV['retires']))
            cible, range_ = os.path.join(os.path.dirname(m["zip"]), nom), os.path.join(base, retires, m["nom"])
            for p in (cible, range_):
                if os.path.exists(p):
                    sys.exit(T("Un zip du même nom est déjà là : {0}", p))
            if a.go:
                os.makedirs(os.path.dirname(range_), exist_ok=True)
                shutil.move(src, cible)
                os.rename(m["zip"], range_)
                journal(T("mis à jour {0} -> {1} (arrivage {2}) ; ancienne version rangée : {3}", m['zip'], cible, src, range_))
                historise(data, "maj", de=m["zip"], vers=cible, version=versions[0], depuis=versions[1], range=range_, arrivage=src)
            return out({"arrivage": src, "de": m["zip"], "vers": cible, "ancienne_vers": range_, "ecrit": bool(a.go)},
                       T("{0}\n  -> {1}\n  ancienne version -> {2}\n", src, cible, range_) + (T("Fait.") if a.go else T("Rien écrit, relancer avec --go.")))
        if a.fixe:
            try:
                demandes = json.loads(sys.stdin.buffer.read().decode("utf-8") if a.fixe == "-" else a.fixe)
            except ValueError as e:
                sys.exit(T("convention --fixe : JSON illisible ({0})", e))
            todo, cibles = [], set()
            for d in demandes:
                src, nom = chemin_de_cle(a.depot, d.get("cle")), (d.get("nom") or "").strip()
                if not src:
                    sys.exit(T("Archive inconnue dans les piles du dépôt : {0}", d.get('cle')))
                if not nom or INTERDITS.search(nom) or nom.endswith((" ", ".")) or len(nom) > 200:
                    sys.exit(T("Nom refusé : « {0} » (caractères interdits \\ / : * ? \" < > |, ou fin par un espace ou un point)", nom))
                if os.path.splitext(nom)[1].lower() != os.path.splitext(src)[1].lower():
                    sys.exit(T("Le nom doit garder son extension {0} : « {1} »", os.path.splitext(src)[1], nom))
                cible = os.path.join(os.path.dirname(src), nom)
                if os.path.basename(src) == nom:
                    continue
                if cible.lower() in cibles or (os.path.exists(cible) and not os.path.samefile(cible, src)):
                    sys.exit(T("Un fichier porte déjà ce nom dans ce dossier : {0}", cible))
                cibles.add(cible.lower())
                todo.append((src, cible))
            if a.go:
                for src, cible in todo:
                    os.rename(src, cible)
                    journal(T("renommé {0} -> {1}", src, os.path.basename(cible)))
                    historise(data, "renomme", de=src, vers=cible)
            return out({"renommes": [{"de": s, "vers": c} for s, c in todo], "ecrit": bool(a.go)},
                       "\n".join(f"{os.path.basename(s)}  ->  {os.path.basename(c)}" for s, c in todo)
                       + (T("\nFait.") if a.go else T("\nRien écrit, relancer avec --go.")))
        vus = []
        for sec, lieu, folder in lieux_du_depot(a.depot):
            g = genre_of(lieu) if lieu else "actif"
            for f in sorted(os.listdir(folder)):
                p = os.path.join(folder, f)
                autre = f.lower().endswith(AUTRES_ARCHIVES)
                if not os.path.isfile(p) or not (autre or f.lower().endswith(".zip")) or g == "retiré":
                    continue
                if g == "nouveau" or autre or RX_APP.match(f):   # arrivages, archives à convertir, noms de l'application
                    vus.append({"cle": "/".join(x for x in (sec, lieu, f) if x), "section": sec, "lieu": lieu, "genre": g,
                                "nom": f, "taille": os.path.getsize(p), "convertir": autre})
        lu = lambda nom: RX_APP.match(nom) or RX_WEB.match(nom)
        mods = {int(lu(r["nom"])["mod"]) for r in vus if lu(r["nom"]) and (RX_APP.match(r["nom"]) or r["genre"] == "nouveau")}
        fichiers, err = nexus_fichiers(mods, data, a.force, True) if mods else ({}, None)
        for r in vus:
            m = RX_APP.match(r["nom"])
            r.update(nom_convention(r["nom"], r["taille"], fichiers.get(int(m["mod"])) if m else None))
            # arrivage d'un mod déjà en place, plus récent que lui : c'est sa mise à jour (téléchargée à la main, sans clé)
            w = RX_ZIP_NEXUS.match(os.path.splitext(r.get("propose") or r["nom"])[0] + ".zip") if r["genre"] == "nouveau" and r["statut"] != "doute" else None
            if w:
                f = {"version": (w["ver"] or "").replace("-", "."), "date": int(w["ts"])}
                publie = next((x for x in fichiers.get(int(w["mod"])) or [] if int(x["date"]) == f["date"]), None)
                r["maj_de"] = [dict(c, propose=nom_de_maj(RX_ZIP_NEXUS.match(c["nom"]), f) + w["tail"] + ".zip")
                               for c in nexus_cibles(int(w["mod"]), f["date"], publie["name"] if publie else w["name"], index, fichiers)]
            elif r["genre"] == "nouveau" and r["statut"] == "hors_nexus" and not r["convertir"]:   # mod sans modId : par le nom et la version
                locales = cibles_locales(r["nom"], index)
                if locales:
                    r["maj_de"] = locales
        ex = extracteur("x.7z", conf)
        c = collections.Counter(r["statut"] for r in vus)
        txt = [N(len(vus), "{n} archive à regarder : ", "{n} archives à regarder : ") + ", ".join(f"{n} {s}" for s, n in c.most_common())] + ([f"  ! {err}"] if err else [])
        for r in vus:
            txt.append(f"  [{r['statut']}] {r['cle']}" + (T("  (à convertir en .zip)") if r["convertir"] else ""))
            if r.get("propose"):
                txt.append(f"        -> {r['propose']}")
            txt += [f"        ? {x['propose']}  ({x['nexus']})" for x in r.get("candidats", []) if r["statut"] == "doute"]
        return out({"lignes": vus, "erreur": err, "extracteur": ex[0] if ex else None, "compte": dict(c)}, "\n".join(txt))

    if a.action == "nexus":                          # mises à jour : lire Nexus, proposer ; --cle … --go télécharge et remplace
        if a.compte:
            c = nexus_compte()
            return out(c, T("Aucune clé d'API Nexus (variable RED_STACK_NEXUS_KEY).") if not c["cle"] else c.get("erreur")
                       or T("Compte {0}, {1} ; appels restants : {2} ce jour, {3} cette heure", c['nom'], 'Premium' if c['premium'] else T("gratuit"), c['reste_jour'], c['reste_heure']))
        if a.lien and not a.cle:                     # lien reçu du site sans zip désigné : qui met-il à jour ? sinon, arrivage
            mod, fid, params = lit_nxm(a.lien)
            fichiers, err = nexus_fichiers([mod], data, a.force, True)
            f = next((x for x in fichiers.get(mod) or [] if int(x["fileId"]) == fid), None)
            if not f and not a.force:                # fichier publié depuis la dernière lecture de ce mod
                fichiers, err = nexus_fichiers([mod], data, True, True)
                f = next((x for x in fichiers.get(mod) or [] if int(x["fileId"]) == fid), None)
            if not f:
                sys.exit(T("Le fichier {0} du mod {1} n'est pas lisible sur Nexus", fid, mod) + (f" ({err})." if err else T(" (retiré, ou caché).")))
            deja = next((k for k, m in index.items() if (w := RX_ZIP_NEXUS.match(m["nom"])) and int(w["mod"]) == mod
                         and int(w["ts"]) == int(f["date"]) and m["genre"] != "retiré"), None)
            if a.section:
                res = nexus_arrive(mod, f, a.depot, a.section, conf, params, a.go)
                if res["ecrit"]:
                    journal(T("téléchargé {0} (Nexus, mod {1}, fichier {2})", res['vers'], mod, fid))
                    historise(data, "arrive", vers=res["vers"], version=res["neuf"]["version"])
                return out(res, f"-> {res['vers']}\n" + (res.get("erreur") or (T("Compte gratuit : ce lien ne porte ni `key` ni `expires`.")
                                                         if res["besoin_lien"] else T("Fait.") if res["ecrit"] else T("Rien écrit, relancer avec --go."))))
            cibles = nexus_cibles(mod, int(f["date"]), f["name"], index, fichiers, fid)
            for c in cibles:
                c["propose"] = nom_de_maj(RX_ZIP_NEXUS.match(c["nom"]), f) + ".zip"
            return out({"mod": mod, "fichier": fiche_nexus(f), "cibles": cibles, "deja": deja, "piles": sections(a.depot), "erreur": err},
                       T("mod {0}, fichier {1} : {2} {3}\n", mod, fid, f['name'], f.get('version') or '')
                       + (T("  déjà dans le dépôt : {0}\n", deja) if deja else "")
                       + ("\n".join(T("  met à jour {0}\n        -> {1}", c['cle'], c['propose']) if c['sur'] else T("  peut-être {0}\n        -> {1}", c['cle'], c['propose']) for c in cibles)
                          or T("  aucun zip de ce mod dans le dépôt : --section PILE le range dans son dossier d'arrivée")))
        ignores = set(conf.get("maj_ignores", []))
        lus = {k: RX_ZIP_NEXUS.match(m["nom"]) for k, m in index.items() if m["genre"] != "retiré"}
        if a.cle and not lus.get(a.cle):
            sys.exit(T("nexus --cle : zip inconnu des piles, ou sans modId dans son nom : {0}", a.cle))
        mods = sorted({int(w["mod"]) for k, w in lus.items() if w and (not a.cle or k == a.cle)})
        fichiers, err = nexus_fichiers(mods, data, a.force, True, True) if mods else ({}, None)
        lignes, hors = nexus_maj(index, fichiers, ignores)
        if a.cle:
            r = next(r for r in lignes if r["cle"] == a.cle)
            if a.ignore:
                if a.valeur not in ("on", "off"):
                    sys.exit(T("nexus --ignore : on (ne plus proposer) ou off (reproposer)"))
                conf["maj_ignores"] = sorted(ignores | {r["qui"]} if a.valeur == "on" else ignores - {r["qui"]})
                save_conf()
                return out({"cle": a.cle, "ignore": a.valeur == "on"}, T("{0} : mises à jour ignorées.", a.cle) if a.valeur == "on" else T("{0} : mises à jour proposées de nouveau.", a.cle))
            if r["statut"] == "deja" or ("neuf" not in r and not a.lien and not a.fichier):
                sys.exit(T("Rien à télécharger pour {0} : ", a.cle) + (r.get("raison") or err or T("ce zip est à jour.")))
            if a.fichier and not a.fichier.isdigit():
                sys.exit(T("nexus --fichier : l'identifiant d'un fichier Nexus de ce mod (un nombre)"))
            res = nexus_telecharge(r, index[a.cle], a.depot, conf, a.lien, a.go, fichiers.get(r["mod"]), a.fichier, a.nom)
            if res["ecrit"]:
                journal(T("mis à jour {0} -> {1} (Nexus, fichier {2}) ; ancienne version rangée : {3}", res['de'], res['vers'], res['neuf']['fichier'], res['ancienne_vers']))
                historise(data, "maj", de=res["de"], vers=res["vers"], version=res["neuf"]["version"], depuis=r["version"], range=res["ancienne_vers"])
            return out(res, T("{0}\n  -> {1}\n  ancienne version -> {2}\n", res['de'], res['vers'], res['ancienne_vers'])
                       + (res.get("erreur") or (T("Compte gratuit : ouvrir {0}, cliquer « Mod manager download », passer le lien par --lien.", res["page"])
                                                if res["besoin_lien"] else T("Fait.") if res["ecrit"] else T("Rien écrit, relancer avec --go."))))
        ordre = ("maj", "a_voir", "doublon", "deja", "introuvable", "illisible")
        c = collections.Counter(r["statut"] for r in lignes)
        vues = sorted((r for r in lignes if r["statut"] != "a_jour"), key=lambda r: (ordre.index(r["statut"]), r["cle"].lower()))
        txt = [suite(N(len(lignes), "{n} zip comparé à Nexus : ", "{n} zips comparés à Nexus : ") + ", ".join(f"{n} {s}" for s, n in c.most_common()),
                     T("{0} non comparés", len(hors)))] + ([f"  ! {err}"] if err else [])
        for r in vues:
            txt.append(f"  [{r['statut']}" + (T(", ") + T("ignoré") if r['ignore'] else '') + f"] {r['cle']}"
                       + (f"\n        -> {r['propose']}  ({r['neuf']['nom']}, {r['neuf']['categorie']})" if r.get("propose") else "")
                       + (f"\n        {r['raison']}" if r.get("raison") else ""))
        return out({"lignes": vues, "a_jour": c["a_jour"], "total": len(lignes), "hors": hors, "compte": dict(c), "erreur": err,
                    "cle_api": bool(os.environ.get(NEXUS_CLE, "").strip())}, "\n".join(txt))

    if a.action == "contenu":                        # contenu d'UN zip : propose ; --fixe récrit le zip aux noms validés
        m = index.get(a.cle or "")
        if not m or m["genre"] == "retiré":
            sys.exit(T("contenu : --cle <clé exacte d'un zip de l'index> ; clé inconnue : {0}", a.cle))
        if not a.fixe:
            if a.nom and (INTERDITS.search(a.nom) or " " in a.nom.strip()):
                sys.exit(T("Nom du mod refusé : « {0} » (ni espace, ni barre oblique, ni : * ? < > |)", a.nom))
            r = plan_contenu(a.cle, index, references(index, data), {**CONTENU, **conf.get("contenu", {})}, a.nom)
            return out(r, f"{a.cle} : {r['etat']}\n" + "\n".join(f"  {o['de']}\n      -> {o['vers']}" for o in r["ops"])
                       + "".join(T("\n  = gardé : {0}  ({1})", g['chemin'], g['raison']) for g in r["gardes"])
                       + "".join(f"\n  ! {n}" for n in r["notes"]))
        try:
            demandes = json.loads(sys.stdin.buffer.read().decode("utf-8") if a.fixe == "-" else a.fixe)
        except ValueError as e:
            sys.exit(T("contenu --fixe : JSON illisible ({0})", e))
        names = {e["n"] for e in m["entrees"]}
        ren = {}
        for d in demandes:
            de, vers = d.get("de"), (d.get("vers") or "").replace("\\", "/").strip()
            if de not in names:
                sys.exit(T("Entrée inconnue dans ce zip : {0}", de))
            parts = vers.split("/")
            if not vers or any(x in ("", ".", "..") or INTERDITS.search(x) or x.endswith((" ", ".")) for x in parts):
                sys.exit(T("Chemin refusé : « {0} » (segment vide, « .. », caractère interdit, ou fin par un espace ou un point)", vers))
            if vers != de:
                ren[de] = vers
        apres = collections.Counter(ren.get(n, n).lower() for n in names)
        double = next((v for v in ren.values() if apres[v.lower()] > 1), None)
        if double:
            sys.exit(T("Deux fichiers du zip porteraient le même chemin : {0}", double))
        poses = sum(1 for r in jeu.load_pose().values() if r["zip"] == a.cle)
        if a.go and ren:
            n = reecrit_zip(m["zip"], ren)
            pdir = os.path.join(data, "profils")     # les choix fichier par fichier des profils suivent les nouveaux noms
            for f in os.listdir(pdir) if os.path.isdir(pdir) else []:
                if f.lower().endswith(".json"):
                    pr = json.load(open(os.path.join(pdir, f), encoding="utf-8"))
                    mp = pr.get("mods", {}).get(a.cle)
                    if mp and (isinstance(mp.get("sel"), dict) or mp.get("renomme")):
                        mp["sel"] = {o: ([ren.get(x, x) for x in v] if isinstance(v, list) else v) for o, v in (mp.get("sel") or {}).items()} or mp.get("sel")
                        if mp.get("renomme"):
                            mp["renomme"] = {ren.get(k, k): v for k, v in mp["renomme"].items()}
                        save_profil(data, f[:-5], pr)
            journal(T("contenu renommé dans {0} ({1} sur {2} fichiers)\n", m['zip'], len(ren), n)
                    + "\n".join(f"  ~ {k}  ->  {v}" for k, v in sorted(ren.items())))
            historise(data, "contenu", de=m["zip"], renommes=len(ren), fichiers=n)
        return out({"cle": a.cle, "renommes": len(ren), "poses": poses, "ecrit": bool(a.go and ren)},
                   N(len(ren), "{n} fichier à renommer dans {0} : ", "{n} fichiers à renommer dans {0} : ", m['zip']) + (T("fait.") if a.go and ren else T("rien écrit, relancer avec --go."))
                   + (N(poses, "\n{n} fichier de ce mod est dans le jeu : le plan le remplacera au prochain `applique`.", "\n{n} fichiers de ce mod sont dans le jeu : le plan les remplacera au prochain `applique`.") if poses else ""))

    if a.action == "deplace":                        # parquer / remonter / retirer : un renommage de zip dans sa pile, rien d'effacé
        m = index.get(a.cle or "")
        if not m or not a.vers:
            sys.exit(T("deplace : --cle <clé exacte de l'index> --vers parques|pile ; clé inconnue : {0}", a.cle))
        base = dossier_pile(a.depot, m["section"])
        if a.vers == "pile":
            if not m["lieu"]:
                sys.exit(T("Ce zip est déjà à la racine de sa pile."))
            lieu = ""
        elif a.vers == "retires":                    # retirer : le zip passe dans le dossier des retirés, d'où il se remonte
            if m["genre"] == "retiré":
                sys.exit(T("Ce zip est déjà dans les retirés."))
            n = sum(1 for r in jeu.load_pose().values() if r["zip"] == a.cle)
            if n:
                sys.exit(T("Des fichiers de ce mod sont encore dans le jeu ({0}) : le couper et appliquer le plan avant de le retirer.", n))
            lieu = dossier_convention(base, "retires")
            if not lieu:
                sys.exit(T("Aucun dossier des retirés dans cette pile : la convention {0} ne donne pas de nom (Réglages).", CONV['retires']))
        else:
            if m["genre"] == "parqué":
                sys.exit(T("Ce zip est déjà parqué."))
            n = sum(1 for r in jeu.load_pose().values() if r["zip"] == a.cle)
            if n:
                sys.exit(N(n, "{n} fichier de ce mod est encore dans le jeu : le couper, appliquer le plan, puis le parquer.", "{n} fichiers de ce mod sont encore dans le jeu : le couper, appliquer le plan, puis le parquer."))
            existants = [d for d in sorted(os.listdir(base)) if match(d, CONV["parques"]) and os.path.isdir(os.path.join(base, d))]
            lieu = a.dossier or (existants[0] if existants else re.sub(r"[*?\[\]]", "", (CONV["parques"] or [""])[0]))
            if not lieu or not match(lieu, CONV["parques"]) or os.sep in lieu or re.search(r'[/:*?"<>|]', lieu):
                sys.exit(T("Dossier des parqués refusé : « {0} » ne suit pas la convention {1} (Réglages, ou --dossier).", lieu, CONV['parques']))
        cible = os.path.join(base, lieu, m["nom"])
        if os.path.exists(cible):
            sys.exit(T("Un zip du même nom est déjà là : {0}", cible))
        cle = "/".join(x for x in (m["section"], lieu, m["nom"]) if x)
        mot = T("remonté dans la pile") if a.vers == "pile" else C("retiré") if a.vers == "retires" else C("parqué")
        if a.go:
            os.makedirs(os.path.dirname(cible), exist_ok=True)
            os.rename(m["zip"], cible)
            pdir = os.path.join(data, "profils")
            if a.vers != "pile":                     # les profils gardent ses choix (options, fichiers), marqués « parqué »
                for f in os.listdir(pdir) if os.path.isdir(pdir) else []:
                    if f.lower().endswith(".json"):
                        pr = json.load(open(os.path.join(pdir, f), encoding="utf-8"))
                        if a.cle in pr.get("mods", {}):
                            pr["mods"][a.cle].update(actif=False, parque=True)
                            save_profil(data, f[:-5], pr)
            logp = conf.get("journal") or os.path.join(data, "red_stack.log")
            os.makedirs(os.path.dirname(logp), exist_ok=True)
            with open(logp, "a", encoding="utf-8") as logf:
                print(file=logf)
                print(f"=== {datetime.datetime.now():%Y-%m-%d %H:%M} dépôt : {mot} {m['zip']} -> {cible}", file=logf)
            historise(data, {"pile": "remonte", "retires": "retire"}.get(a.vers, "parque"), de=m["zip"], vers=cible)
        return out({"de": m["zip"], "vers": cible, "cle": cle, "geste": mot, "ecrit": bool(a.go)},
                   f"{m['zip']}  ->  {cible} : " + (T("fait, {0}.", mot) if a.go else T("rien écrit, relancer avec --go.")))

    prof, notes = load_profil(data, a.profil, index, jeu.load_pose(), bool(conf.get("nouveaux_actifs")))
    charge_miens(prof)

    if a.action == "prerequis":                      # ce que chaque mod exige, qui le fournit, dans quel état : lecture seule
        if a.ignore:                                 # « ce prérequis ne compte pas pour ce mod » : noté dans config.json, réversible
            if a.valeur not in ("on", "off") or a.cle not in index or not a.requis:
                sys.exit(T("prerequis --ignore : on (ne plus compter) ou off (compter de nouveau), --cle <clé du zip>, --requis <identifiant du prérequis>"))
            qui, tous = qui_requiert(index[a.cle]["nom"]), dict(conf.get("requis_ignores") or {})
            connus = {e["ident"] for e in prerequis(index, prof, jeu, data)[0].get(a.cle, {}).get("requis", [])}
            if a.valeur == "on" and a.requis not in connus:
                sys.exit(T("prerequis --ignore : ce mod n'a pas de prérequis « {0} »", a.requis))
            tus = sorted(set(tous.get(qui, [])) | {a.requis} if a.valeur == "on" else set(tous.get(qui, [])) - {a.requis})
            tous.pop(qui, None)
            if tus:
                tous[qui] = tus
            conf["requis_ignores"] = tous
            save_conf()
            return out({"cle": a.cle, "requis": a.requis, "ignore": a.valeur == "on"},
                       T("{0} : prérequis « {1} » ignoré.", a.cle, a.requis) if a.valeur == "on" else T("{0} : prérequis « {1} » compté de nouveau.", a.cle, a.requis))
        key = find_mod(index, prof, a.mod, partout=True) if a.mod else None
        err = None
        if a.nexus:
            mods = sorted({int(w["mod"]) for k, m in index.items() if m["genre"] != "retiré" and (not key or k == key)
                           and (w := RX_ZIP_NEXUS.match(m["nom"]))})
            err = nexus_fichiers(mods, data, a.force, True, True)[1] if mods else None
        lignes, cadres = prerequis(index, prof, jeu, data, conf.get("requis_ignores"))
        jeu.save()
        rows = [dict(r, cle=k, actif=bool((prof["mods"].get(k) or {}).get("actif")) and not index[k]["lieu"], lieu=index[k]["lieu"])
                for k, r in lignes.items() if not key or k == key]
        c = collections.Counter(r["nexus"] for r in rows)
        manques = [r for r in rows if r["manque"] or r["a_voir"]]
        dit = lambda e: f"{e['nom']} [{dit_etat(e['etat'])}]" + (f" ({e['notes']})" if e["notes"] else "")
        txt = [suite(N(len(rows), "{n} zip", "{n} zips"), T("prérequis lus sur Nexus pour {0}", c["lu"]), T("jamais lus : {0}", c["jamais lu"]),
                     T("sans modId : {0}", c["sans modId"]), T("inconnus de Nexus : {0}", c["inconnu"]))] + ([f"  ! {err}"] if err else [])
        txt += [suite(T("  cadre {0} : {1}", x["nom"], dit_etat(x["etat"])), N(x["exige_par"], "exigé par {n} mod actif", "exigé par {n} mods actifs") if x["exige_par"] else "", sep=T(", "))
                for x in cadres if x["exige_par"] or x["etat"] in ("actif", "dans le jeu")]
        if key:
            r = rows[0]
            txt += [f"{key}"] + ["  " + dit(e) for e in r["requis"]] + [N(len(r["requis_par"]), "  exigé par {n} zip, dont {0} actifs", "  exigé par {n} zips, dont {0} actifs", r["requis_par_actifs"])]
        else:
            txt += [N(len(manques), "{n} mod actif à qui il manque un prérequis :", "{n} mods actifs à qui il manque un prérequis :")] if manques else [T("Aucun mod actif ne manque d'un prérequis connu.")]
            txt += [f"  {r['cle']} : " + T(", ").join(dit(e) for e in r["requis"] if e["etat"] in MANQUES and not e["optionnel"] and not e["ignore"]) for r in manques]
            txt += [T("Prérequis optionnels (d'après la note de l'auteur) absents, non comptés : {0}", sum(r["optionnels"] for r in rows))]
        return out({"mods": rows, "cadres": cadres, "compte": dict(c), "manques": sum(1 for r in rows if r["manque"]),
                    "a_voir": sum(1 for r in rows if r["a_voir"]), "optionnels": sum(r["optionnels"] for r in rows), "erreur": err}, "\n".join(txt))

    if a.action == "detail":
        key = find_mod(index, prof, a.mod or "", partout=True)
        mod, mp, reg = index[key], prof["mods"].get(key), jeu.load_pose()
        taken = {e["n"]: d for e, d in selected(mod, mp)}
        par_fomod = fomod_actif(mod, mp)             # alors seul l'installateur donne une destination
        # mod coupé : ce que ses choix poseraient
        prevus = {e["n"]: d for e, d in selected(mod, dict(mp or {}, actif=True))} if par_fomod and not taken else taken
        autres = {}                                  # ce que les AUTRES mods actifs livrent : destination -> {(crc, taille): clé}
        for k2, mp2 in prof["mods"].items():
            if k2 != key and k2 in index and not index[k2]["lieu"]:
                for e2, d2 in selected(index[k2], mp2):
                    autres.setdefault(d2.lower(), {}).setdefault((e2["c"], e2["s"]), k2)
        rows = []
        for e in mod["entrees"]:
            d = taken.get(e["n"], prevus.get(e["n"]) if par_fomod else e["d"])
            r = reg.get(d.lower()) if d else None
            hors = bool(d) and a_tiers(jeu, reg, d)
            if hors:
                st = "hors Red Stack"
            elif d is None:
                st = "jamais posé"
            elif jeu.size(d) is None:
                st = "absent"
            elif r and r["zip"] != key:
                st = ("partagé avec " if jeu.same(d, e["c"], e["s"]) else "écrasé par ") + r["zip"]
            elif jeu.same(d, e["c"], e["s"]):
                st = "lié" if store and store.lie(mod, e["n"], jeu.path(d)) else "copié"
            else:
                st = "modifié en jeu" if r else "autre contenu"
            if st in ("lié", "copié") and e["n"] not in taken and (e["c"], e["s"]) in autres.get(d.lower(), {}):
                # plus pris ici, mais un autre mod actif livre le même fichier : il reste dans le jeu, repris par lui
                st = "partagé avec " + autres[d.lower()][(e["c"], e["s"])]
            rows.append({"entree": e["n"], "option": ("" if d else None) if par_fomod else e["o"], "dest": d,
                         "taille": e["s"], "pris": e["n"] in taken and not hors,
                         "etat": st, "hors": hors, "mien": bool(d) and MIENS.get(d.lower()) == key,
                         "reglage": bool(d and store and store.est_reglage(d))})
        jeu.save()
        return out({"cle": key, "nom": mod["nom"], "section": mod["section"], "version": version_de(mod),
                    "redmod": mod.get("redmod") or [], "fomod": fomod_bref(mod, mp), "prerequis": prerequis(index, prof, jeu, data, conf.get("requis_ignores"))[0].get(key),
                    "actif": bool(mp and mp.get("actif")), "options": options_of(mod), "sel": (mp or {}).get("sel"),
                    "arbre": store.dir_of(mod) if store and os.path.isdir(store.dir_of(mod)) else None, "zip": mod["zip"], "entrees": rows,
                    "priorites": [p for p in prof["priorites"] if key in p]},
                   f"{key}\n" + "\n".join(f"  [{r['etat']}] {r['entree']}" + (f"  ->  {r['dest']}" if r["dest"] else "") for r in rows))

    if a.action == "fomod":                          # installateur d'un zip : le lire, noter ses choix au profil
        key = a.cle if a.cle else find_mod(index, prof, a.mod or "")
        if key not in index:
            sys.exit(T("Zip inconnu de l'index : {0}", key))
        mod, mp = index[key], prof["mods"].get(key)
        if not mod.get("fomod"):
            return out({"cle": key, "nom": mod["nom"], "fomod": False, "erreur": mod.get("fomod_erreur")},
                       f"{key} : " + (T("installateur illisible ({0})", mod['fomod_erreur']) if mod.get("fomod_erreur") else T("pas d'installateur FOMOD dans ce zip.")))
        if a.entree:                                 # une image de l'installateur, pour la page
            ent = next((e for e in mod["entrees"] if e["n"] == a.entree), None)
            mime = FOMOD_IMAGES.get(os.path.splitext(a.entree)[1].lower())
            if ent is None or not mime:
                sys.exit(T("Image inconnue dans ce zip : {0}", a.entree))
            if ent["s"] > FOMOD_IMAGE_MAX:
                return out({"entree": a.entree, "image": None, "trop_grosse": ent["s"]}, T("image trop grosse"))
            import base64
            with zipfile.ZipFile(mod["zip"]) as z:
                b = z.read(next(i for i in z.infolist() if i.filename.replace("\\", "/").lstrip("/") == a.entree))
            return out({"entree": a.entree, "image": f"data:{mime};base64," + base64.b64encode(b).decode()}, f"{a.entree} : {len(b)} octets")
        fait = False
        if a.fixe:
            try:
                neuf = json.loads(sys.stdin.buffer.read().decode("utf-8") if a.fixe == "-" else a.fixe)
            except ValueError as e:
                sys.exit(T("fomod --fixe : JSON illisible ({0})", e))
            if not isinstance(neuf, dict) or not isinstance(neuf.get("choix", {}), dict):
                sys.exit(T("fomod --fixe : attendu {\"choix\": {groupe: [noms]}, \"hors_jeu\": vrai|faux, \"libre\": vrai|faux}"))
            if mod["lieu"]:
                sys.exit(T("Ce zip est rangé dans {0} ({1}) : le remonter dans sa pile avant de noter ses choix.", mod['lieu'], mod['genre']))
            if mp is None:
                mp = prof["mods"].setdefault(key, {"actif": False, "empreinte": mod["empreinte"]})
            etat = dict(mp.get("fomod") or {})
            groupes = {g["cle"]: {p["nom"] for p in g["plugins"]} for et in mod["fomod"]["etapes"] for g in et["groupes"]}
            choix = dict(etat.get("choix") or {})
            for cle, noms in neuf.get("choix", {}).items():
                if cle not in groupes:
                    sys.exit(T("fomod : groupe inconnu de cet installateur : {0}", cle))
                noms = [noms] if isinstance(noms, str) else list(noms or [])
                inconnus = [n for n in noms if n not in groupes[cle]]
                if inconnus:
                    sys.exit(N(len(inconnus), "fomod : choix inconnu dans « {0} » : {1}", "fomod : choix inconnus dans « {0} » : {1}", cle, inconnus))
                choix[cle] = noms
            etat["choix"] = {c: v for c, v in choix.items() if c in groupes}   # un groupe disparu à une mise à jour s'oublie
            for k, defaut in (("hors_jeu", True), ("libre", False)):
                if k in neuf:
                    etat[k] = bool(neuf[k])
                if etat.get(k, defaut) == defaut:
                    etat.pop(k, None)
            # les choix d'une page visible sont ramenés à ce que son groupe permet ; ceux d'une page cachée sont gardés
            etat["choix"].update(fomod_resolu(mod["fomod"], etat)["choix"])
            mp["fomod"] = etat
            if not etat.get("libre"):
                mp.pop("sel", None)                  # la pioche à la main d'avant cède à l'installateur
            save_profil(data, a.profil, prof)
            fait = True
        v = fomod_vue(key, mod, mp)
        txt = [suite(T("{0} : installateur « {1} »", key, v['module']), T("pioché à la main (installateur ignoré)") if v["libre"] else
                     T("posé par son installateur") if v["par_fomod"] else T("sélection faite à la main avant sa lecture (valider ses choix pour le suivre)"), sep=T(", "))]
        for pg in v["pages"]:
            txt.append("  " + (pg['nom'] or T("(page)")) + ("" if pg["visible"] else T("   (page cachée par un choix d'avant)")))
            for g in pg["groupes"]:
                txt.append(T("    {0}  [{1}]   clé : {2}", g['nom'], g['type'], g['cle']))
                txt += [f"      [{'x' if p['choisi'] else ' '}] {p['nom']}" + (f"  ({p['usage']})" if p["usage"] != "Optional" else "") for p in g["plugins"]]
        txt.append(suite(suite(N(v['compte']['poses'], "  {n} fichier à poser sur {0} du zip", "  {n} fichiers à poser sur {0} du zip", v['compte']['zip']),
                               T("dont {0} hors des dossiers du jeu", v['compte']['hors_jeu']) if v["compte"]["hors_jeu"] and v["hors_jeu"] else "", sep=T(", ")),
                         T("{0} hors des dossiers du jeu laissés", v['compte']['hors_jeu']) if v["compte"]["hors_jeu"] and not v["hors_jeu"] else ""))
        txt += [f"  ! {l}" for l in v["limites"]]
        if fait:
            txt.append(T("Choix notés au profil ; le jeu suit au prochain `applique`."))
        return out(dict(v, fait=fait, profil=a.profil), "\n".join(txt))

    if a.action == "noms":
        key = find_mod(index, prof, a.mod or "")
        mod, mp = index[key], prof["mods"].get(key)
        hors_listes = {x.lower() for x in {**CONTENU, **conf.get("contenu", {})}["listes_de_conflits"]}
        refs = references(index, data)
        fait = []
        if a.fixe:
            try:
                demandes = json.loads(sys.stdin.buffer.read().decode("utf-8") if a.fixe == "-" else a.fixe)
            except ValueError as e:
                sys.exit(T("noms --fixe : JSON illisible ({0})", e))
            if mp is None:
                mp = prof["mods"].setdefault(key, {"actif": False})
            unites = {u["chemin"].lower(): u for u in unites_du_mod(mod, mp)}
            ren = dict(mp.get("renomme", {}))
            moves = []                               # (entrée, destination d'avant, destination voulue)
            for d in demandes:
                u = unites.get((d.get("de") or "").replace("\\", "/").lower())
                if not u:
                    sys.exit(T("noms : rien de renommable sous ce chemin dans ce mod : {0}", d.get('de')))
                vers = (d.get("vers") or "").strip() or u["nom"]
                ext = "" if u["dossier"] else os.path.splitext(u["nom"])[1]
                if ext and not vers.lower().endswith(ext.lower()):
                    vers += ext
                if INTERDITS.search(vers) or vers != vers.strip(" .") or len(vers) <= len(ext):
                    sys.exit(T("Nom refusé : « {0} » (un seul nom, sans barre oblique ni : * ? < > |, sans espace ni point en fin)", vers))
                if vers != u["actuel"] and vers.lower() == u["actuel"].lower():
                    sys.exit(T("« {0} » -> « {1} » : changer seulement la casse n'est pas suivi par le plan (Windows y voit le même fichier) : ajouter ou retirer un signe.", u['actuel'], vers))
                neuf = u["chemin"].rsplit("/", 1)[0] + "/" + vers
                for e in u["entrees"]:
                    cible = neuf + e["d"][len(u["chemin"]):]
                    moves.append((e, ren.get(e["n"], e["d"]), cible))
                    if cible == e["d"]:
                        ren.pop(e["n"], None)
                    else:
                        ren[e["n"]] = cible
                if u["mixte"] or vers != u["actuel"]:
                    fait.append({"de": u["chemin"], "avant": u["actuel"], "vers": vers, "genre": u["genre"],
                                 "cites": cites_unite(u, key, refs, hors_listes) if u["nom"] != vers else []})
            # deux fichiers ne visent jamais la même place : ni dans ce mod, ni face à un autre mod actif du profil
            voulus = {c.lower() for _, v, c in moves if c != v}
            miens = collections.Counter(d.lower() for _, d in selected(mod, dict(mp, renomme=ren, actif=True)))
            double = next((d for d in sorted(voulus) if miens[d] > 1), None)
            if double:
                sys.exit(T("Deux fichiers de ce mod porteraient le même chemin dans le jeu : {0}", double))
            for k2, mp2 in prof["mods"].items():
                if k2 != key and k2 in index and not index[k2]["lieu"] and voulus:
                    pris = next((d2 for _, d2 in selected(index[k2], mp2) if d2.lower() in voulus), None)
                    if pris:
                        sys.exit(T("Ce nom mettrait un fichier à la place de celui d'un autre mod actif : {0} ({1})", pris, k2.split('/')[-1]))
            if ren:
                mp["renomme"] = ren
            else:
                mp.pop("renomme", None)
            seuls = prof.get("priorites_fichiers", {})
            for e, v, c in moves:                    # ce que le profil note par destination suit le nouveau nom
                if c == v:
                    continue
                if v.lower() in seuls:
                    seuls[c.lower()] = seuls.pop(v.lower())
                if prof.get("modlist") and v.lower().startswith(ARCH_DIR) and v.count("/") == 3:
                    prof["modlist"] = [c.split("/")[-1] if l.lower() == v.split("/")[-1].lower() else l for l in prof["modlist"]]
                if v.lower() in mp.get("miens", []):
                    mp["miens"] = sorted({c.lower() if x == v.lower() else x for x in mp["miens"]})
            save_profil(data, a.profil, prof)
        rows = []
        for u in unites_du_mod(mod, mp):
            rows.append({"genre": u["genre"], "chemin": u["chemin"], "nom": u["nom"], "actuel": u["actuel"], "dossier": u["dossier"],
                         "mixte": u["mixte"], "renommee": u["mixte"] or u["actuel"] != u["nom"], "fichiers": len(u["entrees"]),
                         "cites": cites_unite(u, key, refs, hors_listes), "note": NOTES_UNITE.get(u["genre"], "")})
        txt = [T("{0} : {1}, {2}", key, N(len(rows), "{n} nom dans le jeu", "{n} noms dans le jeu"), N(sum(1 for r in rows if r['renommee']), "{n} changé par le profil « {0} »", "{n} changés par le profil « {0} »", a.profil))]
        for r in rows:
            txt.append(f"  [{r['genre']}] {r['chemin']}" + (T("  (renommé fichier par fichier)") if r["mixte"] else f"  ->  {r['actuel']}" if r["renommee"] else ""))
            txt += [T("      ! cité par son nom : {0}  {1}", c['zip'], c['fichier']) + (T("  (le mod lui-même)") if c["soi"] else "") for c in r["cites"]]
        if fait:
            txt.append(N(len(fait), "{n} nom noté au profil ; le jeu suit au prochain `applique`.", "{n} noms notés au profil ; le jeu suit au prochain `applique`."))
        return out({"profil": a.profil, "cle": key, "nom": mod["nom"], "actif": bool(mp and mp.get("actif")), "unites": rows, "fait": fait},
                   "\n".join(txt))

    if a.action in ("bascule", "option", "priorite"):
        if a.action == "priorite":
            w = find_mod(index, prof, a.gagnant)
            if a.fichier:                               # un seul fichier du jeu : passe avant la règle par paire
                dest = a.fichier.replace("\\", "/").strip("/").lower()
                seuls = prof.setdefault("priorites_fichiers", {})
                seuls.pop(dest, None)
                if not a.annule:
                    seuls[dest] = w
                msg = T("priorité du fichier {0} oubliée", dest) if a.annule else f"{dest} : {w}"
            else:
                l = find_mod(index, prof, a.perdant)
                prof["priorites"] = [p for p in prof["priorites"] if set(p) != {w, l}] + ([] if a.annule else [[w, l]])
                msg = T("priorité oubliée entre {0} et {1}", w, l) if a.annule else f"{w}  >  {l}"
        elif a.action == "option":
            key = find_mod(index, prof, a.mod)
            if fomod_actif(index[key], prof["mods"].get(key)) and not a.mien:
                sys.exit(T("Ce zip est posé par son installateur FOMOD : ses choix se font par la commande `fomod` (« Installateur… » dans la page). Pour le piocher à la main : `fomod --mod … --fixe {\"libre\": true}`."))
            opts = options_of(index[key])
            ent = None
            if a.entree:                                    # un seul fichier du zip, dans son option
                ent = next((e for e in index[key]["entrees"] if e["n"] == a.entree and e["o"] is not None), None)
                if ent is None:
                    sys.exit(T("Entrée inconnue ou jamais posable dans ce zip : {0}", a.entree))
                name = ent["o"]
            else:
                name = "" if a.nom in (None, "direct") else a.nom
            if a.valeur not in ("on", "off"):
                sys.exit(T("option : on | off"))
            if name not in opts:
                sys.exit(T("Option inconnue ; celles du zip : {0}", [o or 'direct' for o in opts]))
            mp = prof["mods"].setdefault(key, {"actif": True})
            sel = mp.setdefault("sel", {"": "*"} if "" in opts else {})
            if a.mien:                                      # « ce fichier est à ce mod » : pris à l'installateur tiers, ou rendu
                if ent is None:
                    sys.exit(T("option --mien : préciser --entree"))
                dl = mp.get("renomme", {}).get(ent["n"], ent["d"]).lower()
                if not est_hors(dl):
                    sys.exit(T("{0} n'est sous aucun motif « hors Red Stack » : rien à revendiquer, ce fichier suit déjà son mod.", dl))
                for autre in prof["mods"].values():         # un seul mod par fichier
                    if dl in autre.get("miens", []):
                        autre["miens"] = [x for x in autre["miens"] if x != dl]
                        if not autre["miens"]:
                            del autre["miens"]
                if a.valeur == "on":
                    mp["miens"] = sorted(set(mp.get("miens", [])) | {dl})
            if a.mien and a.valeur == "off":
                pass                                        # rendu : la sélection du fichier ne change pas
            elif ent is not None:
                tous = sorted(e["n"] for e in index[key]["entrees"] if e["o"] == name)
                cur = set(tous) if sel.get(name) == "*" else set(sel.get(name) or ())
                (cur.add if a.valeur == "on" else cur.discard)(ent["n"])
                if not cur:
                    sel.pop(name, None)
                else:
                    sel[name] = "*" if len(cur) == len(tous) else sorted(cur)
                    if a.valeur == "on":
                        mp["actif"] = True
            elif a.valeur == "on":
                sel[name] = "*"
                mp["actif"] = True
            else:
                sel.pop(name, None)
            msg = f"{key} : {'fichier ' + a.entree if ent is not None else 'option ' + str(a.nom)} {a.valeur}"
            if a.mien:
                msg += T(" (à ce mod : pris au registre au prochain `applique`)") if a.valeur == "on" else T(" (rendu à l'installateur tiers)")
        else:
            if not a.valeur or not (a.mod or a.section):
                sys.exit(T("bascule : --mod TEXTE ou --section S, puis on | off"))
            keys = [find_mod(index, prof, a.mod)] if a.mod else [k for k, m in index.items()
                                                                 if m["section"] == a.section and not m["lieu"]]
            if not keys:
                sys.exit(T("Section inconnue ou vide : {0}", a.section))
            warn = []
            marked = bool(a.section) and any(prof["mods"].get(k, {}).get("avant_pile") for k in keys)
            for k in keys:
                mp = prof["mods"].setdefault(k, {})
                if a.section and a.valeur == "off":
                    if mp.get("actif"):
                        mp["avant_pile"] = True
                        mp["coupe"] = True
                        mp["a_dire"] = True          # coupé depuis le dernier « Appliquer » : l'aperçu du plan le nomme
                    mp["actif"] = False
                    continue
                if a.section and marked and not mp.pop("avant_pile", None):
                    continue                         # coupé avant la pile : il le reste
                mp.pop("avant_pile", None)
                mp["actif"] = a.valeur == "on"
                if a.valeur == "on":
                    mp.pop("coupe", None)
                    mp.pop("a_dire", None)
                else:
                    mp["coupe"] = True
                    mp["a_dire"] = True
                if a.valeur == "on" and "sel" not in mp and "" not in options_of(index[k]) and not fomod_actif(index[k], mp):
                    warn.append(k)
            msg = f"{len(keys)} mod(s) {a.valeur}" + "".join(T("\n  ! pack à piocher, rien de choisi : {0} (commande `option`)", k) for k in warn)
        save_profil(data, a.profil, prof)
        return out({"ok": True, "message": msg}, msg)

    renames = [(o, n) for kind, o, n in notes if kind == "renommé"]
    if renames:                                      # l'arbre et le registre suivent le nouveau nom, le jeu ne bouge pas
        reg = jeu.load_pose()
        for o, n in renames:
            if store:
                store.renomme(o, index[n])
            for r in reg.values():
                if r["zip"] == o:
                    r["zip"] = n
        jeu.save_pose(reg)

    if a.action == "purge":
        if not store:
            sys.exit(T("purge : sans objet sans magasin"))
        gone = arbres_sans_mod(store, index, prof)
        poids = sum(pese(store.lp(d))[1] for d in gone)
        if a.go:
            for d in gone:
                store.sauve_retouches(d)
                shutil.rmtree(store.lp(d), ignore_errors=True)
        msg = ((suite(N(len(gone), "{n} arbre sans mod actif (coupé, parqué, ancienne version) supprimé, {0} Go", "{n} arbres sans mod actif (coupé, parqué, ancienne version) supprimés, {0} Go", f"{poids / 1e9:.2f}"),
                      N(store.sauves, "{n} retouche copiée dans {0}", "{n} retouches copiées dans {0}", stamp)) if a.go else
                N(len(gone), "{n} arbre sans mod actif (coupé, parqué, ancienne version), {0} Go, à supprimer (--go)", "{n} arbres sans mod actif (coupé, parqué, ancienne version), {0} Go, à supprimer (--go)", f"{poids / 1e9:.2f}")) + "\n"
               + "\n".join("  " + os.path.relpath(d, store.root) for d in gone))
        return out({"arbres": gone, "octets": poids, "supprimes": bool(a.go), "retouches_sauvees": store.sauves}, msg)

    plan, pose = build_plan(index, prof, jeu, a.force or {d.replace("\\", "/").lower() for d in a.remplace}, store, (lambda d: d.lower().endswith(".archive")) if a.action in ("conflits", "ordre")
                            else (lambda d: d.lower().endswith(CODE_EXT_LUES)) if a.action in ("scripts", "objets") else None)
    libres_de = lambda provs: [p["archive"] for p in provs if not p["dossier"]]
    plan["modlist"] = [] if prof.get("modlist") is None or a.action in ("scripts", "objets") else modlist_plan(
        prof, jeu, libres_de(archives_du_profil(index, plan, pose, jeu, store, prof["modlist"])[0]))
    jeu.save()

    if a.action == "magasin":                        # état des liens et poids réel : lecture seule
        if not store:
            sys.exit(T("magasin : sans objet sans magasin (pose directe depuis les zips)"))
        sans_mod = {os.path.normcase(d) for d in arbres_sans_mod(store, index, prof)}
        tous = arbres_du_magasin(store)
        fichiers = poids = 0
        orphelins = []
        for s, d, chemin in tous:
            n, o = pese(store.lp(chemin))
            fichiers, poids = fichiers + n, poids + o
            if os.path.normcase(chemin) in sans_mod:
                orphelins.append({"arbre": s + "/" + d, "chemin": chemin, "fichiers": n, "octets": o})
        lies = copies = reglages = o_lies = o_copies = 0
        for r in pose.values():
            st = jeu.st(r["dest"])
            if st is None or a_tiers(jeu, pose, r["dest"]):
                continue
            if st.st_nlink > 1:                      # un autre nom sur le disque : l'arbre du magasin
                lies, o_lies = lies + 1, o_lies + st.st_size
            else:
                copies, o_copies = copies + 1, o_copies + st.st_size
                reglages += store.est_reglage(r["dest"])
        try:
            meme_disque = os.stat(store.root).st_dev == os.stat(jeu.root).st_dev
            libre = shutil.disk_usage(jeu.root).free
        except OSError:
            meme_disque, libre = None, None
        d = {"magasin": store.root, "existe": os.path.isdir(store.root), "meme_disque": meme_disque, "libre": libre,
             "arbres": len(tous), "fichiers": fichiers, "octets": poids,
             "jeu": {"lies": lies, "octets_lies": o_lies, "copies": copies, "octets_copies": o_copies, "reglages": reglages,
                     "a_lier": len(plan["lie"]), "octets_a_lier": sum(r["taille"] for r in plan["lie"])},
             # l'Explorateur additionne le magasin et les mods du jeu ; un fichier lié n'est qu'une fois sur le disque
             "explorateur": poids + o_lies + o_copies, "reel": poids + o_copies,
             "sans_mod": orphelins, "octets_sans_mod": sum(x["octets"] for x in orphelins),
             "retouches": [{"zip": r["zip"], "entree": r["entree"], "dest": r["dest"]} for r in plan["retouche"]]}
        go = lambda n: T("{0} Go", f"{n / 1e9:.1f}")
        return out(d, T("Magasin {0} : {1} arbres, {2} fichiers, {3}\nDans le jeu, fichiers des mods : {4} liés au magasin ({5}, aucune place en plus), {6} copiés ({7}, dont {8} réglages)\nL'Explorateur additionne {9} ; le disque n'en porte que {10}", store.root, len(tous), fichiers, go(poids), lies, go(o_lies), copies, go(o_copies), reglages, go(d['explorateur']), go(d['reel']))
                   + (T(" ; ") + T("libre sur le disque du jeu : {0}", go(libre)) if libre is not None else "") + "\n"
                   + (T("! magasin et jeu sur deux disques : aucun lien possible, tout est copié\n") if meme_disque is False else "")
                   + (N(len(plan['lie']), "{n} copie à changer en lien au prochain `applique` ({0})\n", "{n} copies à changer en liens au prochain `applique` ({0})\n", go(d['jeu']['octets_a_lier'])) if plan["lie"] else "")
                   + N(len(orphelins), "{n} arbre sans mod actif, {0} à rendre par `purge --go`\n", "{n} arbres sans mod actif, {0} à rendre par `purge --go`\n", go(d['octets_sans_mod']))
                   + N(len(plan['retouche']), "{n} retouche d'arbre posée telle quelle", "{n} retouches d'arbre posées telles quelles"))

    if a.action == "retouche":
        rows = [r for r in plan["retouche"] if not a.mod or r["zip"] == find_mod(index, prof, a.mod)]
        if a.annule:
            if not a.mod:
                sys.exit(T("retouche --annule : préciser --mod"))
            if rows:
                with zipfile.ZipFile(index[rows[0]["zip"]]["zip"]) as zf:
                    for r in rows:
                        store.restaure(index[r["zip"]], zf, r["entree"])
                store.flush()
        msg = ((N(len(rows), "{n} retouche annulée dans l'arbre ; `applique` remet le fichier du zip dans le jeu", "{n} retouches annulées dans l'arbre ; `applique` remet les fichiers du zip dans le jeu") if a.annule else
                N(len(rows), "{n} retouche : fichier de l'arbre qui n'est plus celui du zip, posé tel quel", "{n} retouches : fichiers de l'arbre qui ne sont plus ceux du zip, posés tels quels")) + "\n"
               + "\n".join(f"  {r['zip']}  {r['entree']}" for r in rows))
        return out({"retouches": rows, "annule": a.annule}, msg)

    if a.action == "scripts":                        # conflits de code du profil : lecture seule, rien n'est écrit dans le jeu
        srcs = sources_code(index, plan, pose, jeu, store, data)
        jeu.save()
        trouv, limites, lus = analyse_code(srcs)
        if a.mod:
            cle = find_mod(index, prof, a.mod)
            trouv = [t for t in trouv if cle in t["provs"]]
            limites = [l for l in limites if l["prov"] == cle]
        compte = collections.Counter(t["niveau"] for t in trouv)
        sortes = collections.Counter(t["voie"] + ":" + t["sorte"] for t in trouv)
        nom = lambda pr: pr[5:] + T("  [hors Red Stack]") if pr.startswith("hors:") else pr.split("/")[-1][:-4]
        txt = [T("Lus : {0}, {1}, {2} ; {3} à regarder, {4} à revoir, {5} sans action, {6}", N(lus['reds'], "{n} script Redscript", "{n} scripts Redscript"), N(lus['tweaks'], "{n} tweak", "{n} tweaks"), N(lus['lua'], "{n} fichier Lua de CET", "{n} fichiers Lua de CET"), compte['attention'], compte['revoir'], compte['rien'] + compte['info'], N(len(limites), "{n} limite de lecture", "{n} limites de lecture"))]
        for t in trouv:
            if t["niveau"] in ("rien", "info") and not a.ressources:
                continue
            txt.append(f"[{t['niveau']}] {t['voie']} {t['sorte']} : {t['cible']}")
            for i, l in enumerate(t["lignes"]):
                txt.append(f"    {'>' if t.get('gagnant') == i else ' '} {nom(l['prov'])} : {l['fichier']}:{l['ligne']}  {l['geste']} {l['valeur'][:80]}")
            if t.get("raison"):
                txt.append("      " + (T("dernier mot prévu") if t.get('gagnant') is not None else T("dernier mot non prévu")) + f" : {t['raison']}")
        return out({"profil": a.profil, "lus": lus, "compte": dict(compte), "sortes": dict(sortes), "trouvailles": trouv, "limites": limites,
                    "a_appliquer": sum(len(plan[k]) for k in ("pose", "remplace", "retire"))}, "\n".join(txt))

    if a.action == "objets":                         # armes, vêtements, implants des mods, face à une sauvegarde : lecture seule
        dossier = conf.get("parties") or DOSSIER_PARTIES
        liste = parties(dossier)
        choisie = None
        if a.partie:
            p = os.path.abspath(a.partie)
            p = os.path.join(p, "sav.dat") if os.path.isdir(p) else p
            choisie = next((x for x in liste if x["nom"].lower() == a.partie.lower() or os.path.normcase(x["chemin"]) == os.path.normcase(p)), None)
            if choisie is None and os.path.isfile(p):
                choisie = {"nom": os.path.basename(os.path.dirname(p)), "chemin": p,
                           "date": datetime.datetime.fromtimestamp(os.stat(p).st_mtime).isoformat(timespec="seconds")}
            if choisie is None:
                sys.exit(T("Sauvegarde introuvable : {0} (dossier des parties : {1})", a.partie, dossier))
        elif liste:
            choisie = liste[0]
        srcs = sources_code(index, plan, pose, jeu, store, data)
        jeu.save()
        sorte_jeu = lit_tweakdb(a.jeu)
        par, hors = objets_des_tweaks(srcs, sorte_jeu)
        if a.mod:
            cle = find_mod(index, prof, a.mod)
            par = {k: v for k, v in par.items() if k == cle}
        limites = [{"prov": s["prov"], "fichier": s["fichier"],
                    "quoi": T("fichier .tweak (format RED) : posé, pas analysé") if s["voie"] == "red" else s["lu"]["erreur"]}
                   for s in srcs if s["voie"] in ("tweak", "red") and (s["voie"] == "red" or "erreur" in s["lu"])]
        objets, garde_robe, erreur, illisibles = {}, b"", None, 0
        if choisie:
            try:
                objets, garde_robe, choisie["jeu"], illisibles = lit_partie(choisie["chemin"])
            except PartieErreur as e:
                erreur = str(e)
        mods = objets_face_partie(par, objets, garde_robe)
        d = {"profil": a.profil, "dossier": dossier, "parties": liste, "partie": choisie, "erreur": erreur,
             "mods": mods, "objets": sum(m["total"] for m in mods), "possedes": sum(m["possedes"] for m in mods),
             "non_classes": hors, "limites": limites, "tweakdb": sorte_jeu is not None, "pieces_illisibles": illisibles,
             "a_appliquer": sum(len(plan[k]) for k in ("pose", "remplace", "retire"))}
        if not choisie:
            tete = T("Aucune sauvegarde dans {0} : réglage « Dossier des parties ».", dossier)
        elif erreur:
            tete = T("Sauvegarde {0} illisible : {1}", choisie["nom"], erreur)
        else:
            tete = T("Sauvegarde {0} ({1}), objets des mods du profil possédés (V, planque, garde-robe) : {2} sur {3}", choisie["nom"], choisie["date"], d["possedes"], d["objets"])
        nom = lambda pr: pr[5:] + T("  [hors Red Stack]") if pr.startswith("hors:") else pr.split("/")[-1][:-4]
        txt = [tete] + [f"  {m['possedes']:>4}/{m['total']:<4} {nom(m['prov'])}" for m in mods]
        return out(d, "\n".join(txt))

    if a.action == "ordre":
        provs, source = archives_du_profil(index, plan, pose, jeu, store, prof.get("modlist"))
        libres = [p for p in provs if not p["dossier"]]
        pris = {p["archive"].lower() for p in libres}

        def trouve(texte, quoi):
            t = texte.lower()
            hits = [p for p in libres if p["archive"].lower() in (t, t + ".archive")]
            if len(hits) != 1:
                sys.exit(N(len(hits), "ordre {0} : « {1} » désigne {n} archive de archive/pc/mod dans ce profil (les archives REDmod se rangent par dossier, pas ici)", "ordre {0} : « {1} » désigne {n} archives de archive/pc/mod dans ce profil (les archives REDmod se rangent par dossier, pas ici)", quoi, texte))
            return hits[0]

        def cites(p):
            """qui cite cette archive par son nom dans le code du dépôt : à relire avant de la renommer"""
            stem = p["archive"].lower()[:-len(".archive")]
            hors_listes = {x.lower() for x in {**CONTENU, **conf.get("contenu", {})}["listes_de_conflits"]}
            return [{"zip": k, "fichier": f} for k, f in sorted({(k, f) for k, rows in references(index, data).items() for f, g, t in rows
                                                                 if g == "a" and t == stem and f.split("/")[-1].lower() not in hors_listes})]

        def simule(p, nom):
            """ordre des archives si celle-ci prenait ce nom, les lignes de modlist.txt restant ce qu'elles sont"""
            lignes = prof["modlist"] if prof.get("modlist") is not None else modlist_du_jeu(jeu) or []
            if prof.get("modlist") is not None:      # liste tenue par le profil : elle suivra le nouveau nom
                lignes = [nom if l.lower() == p["archive"].lower() else l for l in lignes]
            return ordonne([nom if q is p else q["archive"] for q in libres], lignes)[0]

        def nom_valide(p, texte):
            nom = texte.strip()
            if not nom.lower().endswith(".archive"):
                nom += ".archive"
            if not p["zip"]:
                sys.exit(T("{0} n'est pas posée par Red Stack (hors Red Stack) : son nom ne se change pas par le profil ; l'ordre se règle alors par modlist.txt (--voie modlist).", p['archive']))
            if INTERDITS.search(nom) or nom != nom.strip(" .") or len(nom) < len("x.archive"):
                sys.exit(T("Nom d'archive refusé : « {0} »", nom))
            if nom != p["archive"] and nom.lower() == p["archive"].lower():
                sys.exit(T("Changer seulement la casse n'est pas suivi par le plan (Windows y voit le même fichier) : ajouter ou retirer un signe."))
            if nom.lower() != p["archive"].lower() and nom.lower() in pris:
                sys.exit(T("Une autre archive du jeu porte déjà ce nom : {0}", nom))
            return nom

        fait, propose = None, None
        if a.nom and (a.renomme is not None or a.annule):
            p = trouve(a.nom, "--nom")
            nom = nom_valide(p, p["origine"] if a.annule else a.renomme)
            ent = next(e for e in index[p["zip"]]["entrees"] if e["n"] == p["entree"])
            mp = prof["mods"][p["zip"]]
            ren = mp.setdefault("renomme", {})
            neuf = p["dest"].rsplit("/", 1)[0] + "/" + nom
            if neuf == ent["d"]:
                ren.pop(ent["n"], None)              # le nom de l'auteur : plus rien à noter
            else:
                ren[ent["n"]] = neuf
            if not ren:
                mp.pop("renomme", None)
            if prof.get("modlist"):
                prof["modlist"] = [nom if l.lower() == p["archive"].lower() else l for l in prof["modlist"]]
            seuls = prof.get("priorites_fichiers", {})
            if p["dest"].lower() in seuls:
                seuls[neuf.lower()] = seuls.pop(p["dest"].lower())
            c = cites(p) if nom != p["archive"] else []
            save_profil(data, a.profil, prof)
            fait = {"geste": "renomme", "archive": p["archive"], "vers": nom, "origine": p["origine"], "cites": c}
        elif a.nom and (a.avant or a.apres):
            p, cible = trouve(a.nom, "--nom"), trouve(a.avant or a.apres, "--avant / --apres")
            if p is cible:
                sys.exit(T("ordre : une archive ne passe pas avant ou après elle-même"))
            avant = bool(a.avant)
            if a.voie == "modlist":
                L = [q["archive"] for q in libres if q is not p]
                L.insert(L.index(cible["archive"]) + (0 if avant else 1), p["archive"])
                n = len(L)                           # la fin déjà dans l'ordre des noms n'a pas à être écrite
                while n > 0 and (n == len(L) or octets(L[n - 1]) < octets(L[n])):
                    n -= 1
                prof["modlist"] = L[:n]
                save_profil(data, a.profil, prof)
                fait = {"geste": "modlist", "archive": p["archive"], "cible": cible["archive"], "avant": avant, "lignes": n}
            else:
                nom = nom_pour_ordre(p["archive"], cible["archive"], avant, pris - {p["archive"].lower()}) if p["zip"] else None
                apres = simule(p, nom) if nom else None
                atteint = bool(nom) and ((apres.index(nom) < apres.index(cible["archive"])) == avant)
                propose = {"archive": p["archive"], "cible": cible["archive"], "avant": avant, "nom": nom, "atteint": atteint,
                           "origine": p["origine"], "hors": not p["zip"], "rang": libres.index(p) + 1,
                           "rang_apres": apres.index(nom) + 1 if nom else None, "par_modlist": source == "modlist.txt",
                           "cites": cites(p) if nom and nom != p["archive"] else []}
        elif a.modlist and a.annule:
            if modlist_du_jeu(jeu) is None:
                prof.pop("modlist", None)
            else:
                prof["modlist"] = []                 # le fichier part au prochain « Appliquer », l'ordre revient aux noms
            save_profil(data, a.profil, prof)
            fait = {"geste": "modlist", "lignes": 0}
        elif a.nom or a.avant or a.apres or a.renomme or a.modlist:
            sys.exit(T("ordre : --nom ARCHIVE avec --avant / --apres CIBLE [--voie modlist], --renomme NOM ou --annule ; ou --modlist --annule"))
        if fait:                                     # relu après l'écriture du profil
            plan, pose = build_plan(index, prof, jeu, a.force or {d.replace("\\", "/").lower() for d in a.remplace}, store, lambda d: d.lower().endswith(".archive"))
            provs, source = archives_du_profil(index, plan, pose, jeu, store, prof.get("modlist"))
        jeu.save()
        ml = {"tenu": prof.get("modlist") is not None, "lignes": prof.get("modlist") or [], "dans_le_jeu": modlist_du_jeu(jeu) is not None,
              "a_appliquer": bool(modlist_plan(prof, jeu, libres_de(provs)))}
        ordre = [{"rang": i + 1, "archive": p["archive"], "origine": p["origine"], "renommee": p["archive"] != p["origine"],
                  "zip": p["zip"], "genre": p["genre"]} for i, p in enumerate(provs)]
        txt = [suite(T("Profil « {0} » : {1} archives, ordre par les noms des archives", a.profil, len(provs)) if source == "noms"
                     else T("Profil « {0} » : {1} archives, ordre par modlist.txt", a.profil, len(provs)),
                     N(len(ml['lignes']), "modlist.txt tenu par le profil ({n} ligne)", "modlist.txt tenu par le profil ({n} lignes)") if ml["tenu"] else "")]
        if propose:
            txt.append(suite((T("Proposé pour que {0} se charge avant {1} : ", propose['archive'], propose['cible']) if propose['avant']
                              else T("Proposé pour que {0} se charge après {1} : ", propose['archive'], propose['cible']))
                             + (T("{0} (rang {1} -> {2})", propose['nom'], propose['rang'], propose['rang_apres']) if propose["nom"] else T("aucun nom (archive hors Red Stack)")),
                             "" if propose["atteint"] or not propose["nom"] else T("SANS EFFET : modlist.txt décide de l'ordre de ces archives")))
            txt += [T("  ! citée par son nom : {0}  {1}", c['zip'], c['fichier']) for c in propose["cites"]]
            txt.append(T("Rien écrit : `ordre --nom … --renomme NOM` le note au profil."))
        elif fait:
            txt.append(suite(T("{0} -> {1} noté au profil", fait['archive'], fait['vers']) if fait["geste"] == "renomme"
                             else N(fait['lignes'], "modlist.txt : {n} ligne au profil", "modlist.txt : {n} lignes au profil"), T("le jeu suit au prochain `applique`.")))
            txt += [T("  ! citée par son nom : {0}  {1}", c['zip'], c['fichier']) for c in fait.get("cites", [])]
        else:
            txt += [f"  {o['rang']:4d}  {o['archive']}" + (T("  (nom de l'auteur : {0})", o['origine']) if o["renommee"] else "")
                    + (T("  [hors Red Stack]") if o["genre"] == "hors" else "  [REDmod]" if o["genre"] == "redmod" else "") for o in ordre]
        return out({"profil": a.profil, "ordre_par": source, "modlist": ml, "ordre": ordre, "propose": propose, "fait": fait}, "\n".join(txt))

    if a.action == "conflits":
        oodle = Oodle(a.jeu)
        provs, source = archives_du_profil(index, plan, pose, jeu, store, prof.get("modlist"))
        jeu.save()
        illisibles = []
        for p in provs:
            try:
                ents = lit_archive(p, rdar_index)
            except (OSError, ValueError, KeyError, struct.error, zipfile.BadZipFile):
                ents = None
            if ents is None:
                illisibles.append(p["dest"])
            p["ents"] = ents or []
            p["set"] = {h for h, _ in p["ents"]}
        paires, par = conflits_archives(provs)
        stats = [collections.Counter() for _ in provs]
        en_conflit = partages = 0
        relations = {}                               # empreinte -> [(rang, gagne sur, perd contre, identique à)]
        for h, l in par.items():
            if len(l) < 2:
                continue
            rows, diff = [], False
            for k, (i, sha) in enumerate(l):
                meme = lambda x: x[1] == sha and sha not in SHA_VIDES
                g = [x[0] for x in l[k + 1:] if not meme(x)]
                pd = [x[0] for x in l[:k] if not meme(x)]
                idt = [x[0] for x in l[:k] + l[k + 1:] if meme(x)]
                stats[i]["gagne"] += bool(g)
                stats[i]["perd"] += bool(pd)
                stats[i]["identiques"] += bool(idt)
                diff = diff or bool(g)
                rows.append((i, g, pd, idt))
            relations[h] = rows
            en_conflit += diff
            partages += not diff
        # ressources qui remplacent un fichier du jeu de base (même empreinte de chemin dans `content` ou `ep1`)
        toutes = set().union(*(p["set"] for p in provs)) if provs else set()
        base = {h for h in base_du_jeu(jeu, data) if h in toutes} if toutes else set()
        ordre = [{"rang": i, "archive": p["archive"], "dest": p["dest"], "zip": p["zip"], "genre": p["genre"], "origine": p["origine"],
                  "ressources": len(p["set"]), "base": len(p["set"] & base), **{k: stats[i][k] for k in ("gagne", "perd", "identiques")}}
                 for i, p in enumerate(provs)]
        tete = {"profil": a.profil, "ordre_par": source, "illisibles": illisibles,
                "modlist": {"tenu": prof.get("modlist") is not None, "lignes": len(prof.get("modlist") or []),
                            "a_appliquer": bool(plan["modlist"])},
                "a_appliquer": sum(len(plan[k]) for k in ("pose", "remplace", "retire")) + len(plan["modlist"]),
                "compte": {"archives": len(provs), "ressources": sum(len(p["set"]) for p in provs),
                           "en_conflit": en_conflit, "identiques": partages, "base": len(base),
                           "paires": sum(1 for d in paires.values() if d["conflits"])}}
        lib = lambda i: provs[i]["archive"] + (f"  [{provs[i]['zip'].split('/')[-1][:-4]}]" if provs[i]["zip"] else T("  [hors Red Stack]"))
        if a.ressources:                             # toutes les ressources en conflit : où le jeu la prend, qui la perd
            noms = noms_ressources(set(relations), provs, jeu, data, oodle)
            rows = sorted(({"ressource": noms.get(h, f"#{h:016x}"), "prise_dans": l[0][0], "perd": l[0][1], "identiques": l[0][3],
                            "base": h in base} for h, l in relations.items() if l[0][1]),
                          key=lambda r: (r["ressource"].startswith("#"), r["ressource"]))   # les nommées d'abord
            txt = [N(len(rows), "{n} ressource en conflit ; ordre de chargement par {0}", "{n} ressources en conflit ; ordre de chargement par {0}", source)]
            for r in rows[:400]:
                txt.append(f"  {r['ressource']}" + (T("  [remplace le jeu de base]") if r["base"] else ""))
                txt.append(T("      prise dans {0}", lib(r['prise_dans'])))
                txt += [T("      perdue par {0}", lib(j)) for j in r["perd"]]
            # copies identiques sans aucun conflit : la même ressource, au même contenu, dans plusieurs archives
            egales = sorted(({"ressource": noms.get(h, f"#{h:016x}"), "prise_dans": l[0][0], "perd": [], "identiques": l[0][3],
                              "base": h in base} for h, l in relations.items() if not l[0][1] and l[0][3]),
                            key=lambda r: (r["ressource"].startswith("#"), r["ressource"]))
            return out({**tete, "ordre": ordre, "total": len(rows), "ressources": rows, "identiques": egales}, "\n".join(txt))
        if a.mod or a.nom:                           # détail : les ressources d'un mod (ses archives) ou d'une archive
            if a.mod:
                key = find_mod(index, prof, a.mod)
                cible = {i for i, p in enumerate(provs) if p["zip"] == key}
            else:
                t = a.nom.lower()
                cible = {i for i, p in enumerate(provs) if p["archive"].lower() in (t, t + ".archive")} \
                    or {i for i, p in enumerate(provs) if t in p["archive"].lower()}
            if not cible:
                sys.exit(T("Aucune archive chargée pour « {0} » dans ce profil.", a.mod or a.nom))
            mine = [(h, r) for h, rows in relations.items() for r in rows if r[0] in cible]
            noms = noms_ressources(set(relations), provs, jeu, data, oodle)
            rows = sorted(({"ressource": noms.get(h, f"#{h:016x}"), "archive": i, "prise_dans": relations[h][0][0],
                            "gagne_sur": g, "perd_contre": pd, "identique_a": idt} for h, (i, g, pd, idt) in mine),
                          key=lambda r: (not r["perd_contre"], not r["gagne_sur"], r["ressource"]))
            txt = [N(len(rows), "{n} ressource partagée ; ordre de chargement par {0}", "{n} ressources partagées ; ordre de chargement par {0}", source)]
            for r in rows[:300]:
                txt.append(f"  {r['ressource']}  ({provs[r['archive']]['archive']})")
                txt += [f"      {mot} {lib(j)}" for mot, k in ((T("perd contre"), "perd_contre"), (T("gagne sur  "), "gagne_sur"),
                                                               (T("identique à"), "identique_a")) for j in r[k]]
            seules = []                              # ce que ces archives sont seules à livrer : servi au jeu, aucun conflit
            if a.tout:
                libres = [(h, i) for i in sorted(cible) for h in provs[i]["set"] if h not in relations]
                noms2 = noms_ressources({h for h, _ in libres}, provs, jeu, data, oodle)
                seules = sorted(({"ressource": noms2.get(h, f"#{h:016x}"), "archive": i, "base": h in base} for h, i in libres),
                                key=lambda r: (r["ressource"].startswith("#"), r["ressource"]))
            return out({**tete, "cible": sorted(cible), "ordre": ordre, "total": len(rows), "nommees": sum(1 for h, _ in mine if h in noms),
                        "ressources": rows[:3000], **({"seules_total": len(seules), "seules": seules[:5000]} if a.tout else {})},
                       "\n".join(txt))
        vues = sorted(((i, j, d) for (i, j), d in paires.items()), key=lambda x: (-len(x[2]["conflits"]), -x[2]["identiques"], x[0], x[1]))
        noms = noms_ressources(set(relations), provs, jeu, data, oodle)   # tout d'un coup : le détail suit sans attente
        rows = [{"gagnant": i, "perdant": j, "conflits": len(d["conflits"]), "identiques": d["identiques"],
                 "meme_mod": bool(provs[i]["zip"]) and provs[i]["zip"] == provs[j]["zip"],
                 "exemples": [noms.get(h, f"#{h:016x}") for h in sorted(d["conflits"])[:3]]} for i, j, d in vues]
        c = tete["compte"]
        txt = [T("Profil « {0} » : {1} archives chargées (ordre par {2}), {3} ressources ; {4}, {5}", a.profil, c['archives'], source, c['ressources'], N(c['en_conflit'], "{n} ressource en conflit dans {0}", "{n} ressources en conflit dans {0}", N(c['paires'], "{n} paire d'archives", "{n} paires d'archives")), N(c['identiques'], "{n} partagée à l'identique", "{n} partagées à l'identique"))]
        txt += [f"  ! illisible : {d}" for d in illisibles[:40]]
        for r in rows[:200]:
            if r["conflits"]:
                txt.append(T("  {0}  {1}   GAGNE SUR   {2}", f"{r['conflits']:5d}", lib(r['gagnant']), lib(r['perdant']))
                           + (T("   (+ {0} identiques)", r['identiques']) if r["identiques"] else "") + (T("   (même mod)") if r["meme_mod"] else ""))
                txt += [f"           {e}" for e in r["exemples"]]
        return out({**tete, "ordre": ordre, "paires": rows}, "\n".join(txt))

    if a.action == "etat":
        per = collections.defaultdict(collections.Counter)
        for kind in ("pose", "remplace", "retire", "garde_modifie", "inconnu"):
            for row in plan[kind]:
                per[row["zip"]][kind] += 1
        posed = collections.Counter(r["zip"] for r in pose.values() if not a_tiers(jeu, pose, r["dest"]))
        rows = []
        try:                                         # cache des références : lu s'il existe, jamais refait ici
            cache_refs = json.load(open(os.path.join(data, "references.json"), encoding="utf-8"))
        except (OSError, ValueError):
            cache_refs = {}
        cites = cites_du_depot(index, cache_refs)
        requis = prerequis(index, prof, jeu, data, conf.get("requis_ignores"))[0]    # Nexus lu dans son cache : jamais d'appel ici
        for k, m in index.items():
            mp = prof["mods"].get(k)
            c = per.get(k, {})
            if m["lieu"]:
                etat = f"{m['genre']} ({m['lieu']})"
            elif mp is None:
                etat = "nouveau dans le dépôt"
            elif not mp.get("actif"):
                # « coupé » = coupé par l'utilisateur ; sans cette marque, le zip n'a jamais été dans le jeu
                etat = "coupé, à retirer" if c.get("retire") else "coupé" if mp.get("coupe") or posed.get(k) else "jamais posé"
            elif c.get("pose") or c.get("remplace"):
                etat = "à poser" if not posed.get(k) else "à compléter"
            else:
                etat = "posé" + (" (modifié en jeu)" if c.get("garde_modifie") else "")
            ht = sum(1 for e in m["entrees"] if e["d"] and a_tiers(jeu, pose, e["d"])) if HORS and not m["lieu"] else 0
            fo = fomod_bref(m, mp)
            rows.append({"cle": k, "section": m["section"], "nom": m["nom"], "version": version_de(m),
                         "lieu": m["lieu"], "genre": m["genre"], "actif": bool(mp and mp.get("actif")) and not m["lieu"],
                         "fomod": fo, "natures": natures(m, k, cites, cache_refs),
                         "prerequis": {x: requis[k][x] for x in ("manque", "a_voir", "optionnels", "requis_par_actifs")} if k in requis else None,
                         "posables": (fo["fichiers"] if fo and fo["actif"] else sum(1 for e in m["entrees"] if e["o"] is not None)) - ht,
                         "hors": ht,
                         "taille": m["taille"], "etat": etat, "fichiers_poses": posed.get(k, 0),
                         "zip": m["zip"], "arbre": store.dir_of(m) if store and not m["lieu"] and os.path.isdir(store.dir_of(m)) else None,
                         "options": options_of(m), "sel": (mp or {}).get("sel"), **{x: c.get(x, 0) for x in ("pose", "remplace", "retire")}})
        old = collections.Counter(r["zip"] for r in pose.values() if r["zip"] not in index)
        c = collections.Counter(r["etat"] for r in rows)
        txt = [T("Profil « {0} », jeu {1}", a.profil, a.jeu), ", ".join(f"{n} {C(e)}" for e, n in c.most_common())]
        txt += [f"  {C(kind)} : {old_k} -> {new_k}" for kind, old_k, new_k in notes]
        txt += [T("  ancienne version encore dans le jeu : {0} ({1} fichiers)", k, n) for k, n in old.items()]
        for sec in sections(a.depot):
            mine = [r for r in rows if r["section"] == sec and not r["etat"].startswith(("posé", "parqué", "retiré"))]
            if mine:
                txt.append(f"\n{sec}")
                txt += [f"  [{r['etat']}] {r['nom']}" for r in mine]
        return out({"profil": a.profil, "jeu": a.jeu, "depot": a.depot, "magasin": store.root if store else None, "reel": real,
                    "sections": sections(a.depot), "mods": rows, "notes": notes, "anciennes": old,
                    "conflits": plan["conflit"], "gardes": len(plan["garde_modifie"]), "retouches": len(plan["retouche"]),
                    "hors": conf["hors"], "tiers": plan["tiers"], "natures_citees": bool(cache_refs)},
                   "\n".join(txt))

    counts = {k: len(plan[k]) for k in ("pose", "remplace", "retire", "lie", "delie", "retouche", "garde_modifie",
                                        "inconnu", "conflit", "pris", "rendu", "modlist")}
    # empreinte de ce qui serait écrit : ce que l'utilisateur a vu à l'aperçu est ce qui sera appliqué, ou rien
    mark = hashlib.sha1(json.dumps([a.profil, bool(a.force), sorted(r["dest"].lower() for r in plan["remplace"] if r.get("force"))] + [sorted((r["dest"].lower(), r["zip"], r["crc"]) for r in plan[k])
                                   for k in ("pose", "remplace", "retire", "lie", "delie", "pris", "rendu", "modlist")]).encode()).hexdigest()[:16]
    txt = [suite(T("Profil « {0} », jeu {1}", a.profil, a.jeu), T("magasin {0}", store.root) if store else T("pose directe"), sep=T(", ")),
           suite(T("à poser {0}, à remplacer {1}, à retirer {2}, copies à changer en liens {3} ({4} Go) ; déjà en place {5} ; gardés (modifiés en jeu) {6}, présents non posés par l'outil {7}, conflits à trancher {8}", counts['pose'], counts['remplace'], counts['retire'], counts['lie'], f"{sum(r['taille'] for r in plan['lie']) / 1e9:.1f}", plan['ok'], counts['garde_modifie'], counts['inconnu'], counts['conflit']),
                 T("hors Red Stack (installateur tiers, laissés) {0}, dont à rendre (délier) {1}", plan['tiers'], sum(1 for r in plan['delie'] if r.get('tiers'))) if HORS else "")]
    txt += [T("  {0} : {1} -> {2}", C(kind), o, n) for kind, o, n in notes]
    if counts["delie"] or counts["retouche"]:
        txt.append(T("  réglages à délier de l'arbre {0} ; retouches de l'arbre posées telles quelles {1}", counts['delie'], counts['retouche']))
        txt += [f"  * retouche : {r['zip']}  {r['entree']}" for r in plan["retouche"][:40]]
    for kind, sign in (("pose", "+"), ("remplace", "~"), ("retire", "x")):
        per = collections.Counter(r["zip"] for r in plan[kind])
        txt += [f"  {sign} {kind:9s} {n:5d}  {z}" for z, n in per.most_common()]
    txt += [T("  ! gardé : {0}  ({1} ; {2})", r['dest'], r['zip'], r['raison']) for r in plan["garde_modifie"][:40]]
    txt += [T("  ? présent : {0}  ({1})", r['dest'], r['zip']) for r in plan["inconnu"][:40]]
    txt += [T("  # conflit : {0}  <- {1} ; dans le jeu : {2}", c['dest'], ' | '.join(c['zips']), c['dans_le_jeu']) for c in plan["conflit"]]
    txt += [T("  = lié à l'arbre de {0}, repris de {1} : {2}", r['zip'], r['ancien'], r['dest']) for r in plan["lie"] if r.get("ancien")][:40]
    txt += [T("  @ pris au registre pour {0} : {1}", r['zip'], r['dest']) + (f"  ({r['raison']})" if r.get("raison") else "") for r in plan["pris"]]
    txt += [T("  @ rendu à l'installateur tiers (laissé dans le jeu) : {0}  ({1})", r['dest'], r['zip']) for r in plan["rendu"]]
    txt += [T("  # modlist.txt : ") + (N(len(r['lignes']), "à écrire, {n} ligne (ordre de chargement voulu par le profil)", "à écrire, {n} lignes (ordre de chargement voulu par le profil)")
                                    if r["action"] == "ecrire" else T("à retirer du jeu (l'ordre revient aux noms des archives)"))
            for r in plan["modlist"]]
    nom_de = lambda rows: ", ".join(f"{x['n']} par {x['zip']}" for x in rows)
    for c in plan["coupes"]:
        faits = [T("{0} à retirer du jeu", c['retire'])] + ([N(c['garde'], "{n} modifié en jeu, gardé", "{n} modifiés en jeu, gardés")] if c["garde"] else []) \
            + ([N(c['rendu'], "{n} rendu à l'installateur tiers", "{n} rendus à l'installateur tiers")] if c["rendu"] else []) \
            + ([T("repris à l'identique : {0}", nom_de(c['repris']))] if c["repris"] else []) \
            + ([T("tenus avec un autre contenu : {0}", nom_de(c['tenu_par']))] if c["tenu_par"] else [])
        txt.append(T("  - coupé : {0} : ", c['zip']) + " ; ".join(faits))

    if a.action == "plan":
        # prérequis : ce que l'aperçu doit dire avant d'écrire. Un cadre qui manque à un mod actif, ou un mod déclaré
        # requis sans réserve que ce profil coupe. Un prérequis absent du dépôt se lit dans la liste, pas ici.
        alertes = []
        for k, r in prerequis(index, prof, jeu, data, conf.get("requis_ignores"))[0].items():
            es = [e for e in r["requis"] if e["etat"] in MANQUES and not e["ignore"] and (e["cadre"] or (e["etat"] == "coupé" and not e["optionnel"]))]
            if es and (r["manque"] or r["a_voir"]):
                alertes.append({"zip": k, "requis": [{x: e[x] for x in ("cadre", "mod", "nom", "etat", "notes", "par")} for e in es]})
                txt.append(T("  ! prérequis : {0} exige {1}", k, T(", ").join(f"{e['nom']} [{dit_etat(e['etat'])}]" for e in es)))
        return out({"compte": counts, "empreinte": mark, "reel": real, "jeu_lance": game_running() if real else False, "prerequis": alertes,
                    "ok": plan["ok"], **{k: plan[k] for k in counts}, "tranche": plan["tranche"], "notes": notes,
                    "tiers": plan["tiers"], "coupes": plan["coupes"]},
                   "\n".join(txt + [T("Rien écrit.")]))

    # applique
    if not a.go:
        sys.exit("\n".join(txt + [T("Rien écrit : relancer avec --go.")]))
    if real and not a.vrai_jeu:
        sys.exit(T("Cible = le vrai jeu : ajouter --vrai-jeu (jeu fermé)."))
    if real and game_running():
        sys.exit(T("Le jeu tourne : le fermer d'abord."))
    if a.si_plan and a.si_plan != mark:
        sys.exit(T("Le plan a changé depuis l'aperçu ({0} attendu, {1} à présent) : rien écrit, revoir l'aperçu.", a.si_plan, mark))
    if real and conf.get("avant_applique") and any(counts[k] for k in ("pose", "remplace", "retire", "lie", "delie")):
        r = subprocess.run(conf["avant_applique"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            sys.exit(T("Commande `avant_applique` en échec ({0}) : rien écrit.\n{1}\n{2}", r.returncode, r.stdout[-800:], r.stderr[-800:]))
    dits = [mp.pop("a_dire") for mp in prof["mods"].values() if "a_dire" in mp]   # coupures montrées à cet aperçu : dites
    if dits or any(k == "mise à jour" for k, _, _ in notes):
        save_profil(data, a.profil, prof)
    logp = conf.get("journal") or os.path.join(data, "red_stack.log")
    os.makedirs(os.path.dirname(logp), exist_ok=True)
    logf = open(logp, "a", encoding="utf-8")
    logf.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M} applique profil={a.profil} jeu={a.jeu}\n")
    if store:                                        # un arbre par mod ACTIF, même s'il n'a rien à lier
        for key, mp in prof["mods"].items():
            if key in index and not index[key]["lieu"] and selected(index[key], mp):
                store.ensure(index[key])
    for r in plan["modlist"]:                        # ordre de chargement voulu par le profil : le fichier d'avant est copié
        target = jeu.path(ML)
        if os.path.isfile(target):
            b = os.path.join(stamp, ML.replace("/", os.sep))
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(target, b)
        drop(target)
        if r["action"] == "ecrire":
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(r["lignes"]) + "\n")
        logf.write(f"  # MODLIST   {r['action']}  {len(r['lignes'])} ligne(s)\n")
        if r["action"] == "retirer":                 # fichier parti : l'outil ne le tient plus, un fichier écrit à la main sera lu
            prof.pop("modlist", None)
            save_profil(data, a.profil, prof)
    avant = collections.Counter(r["zip"] for r in pose.values())
    bad, stamp = apply_plan(plan, pose, index, jeu, stamp, lambda s: logf.write(s + "\n"), store)
    ecrit = {k: counts[k] for k in ("pose", "remplace", "retire", "lie", "delie", "pris", "rendu", "modlist") if counts.get(k)}
    if ecrit:
        historise(data, "applique", profil=a.profil, reel=real, compte=ecrit,
                  mods=mods_du_plan(plan, avant, collections.Counter(r["zip"] for r in pose.values())),
                  echecs=bad, sauvegarde=stamp)
    if store and (counts["delie"] or store.sauves):
        txt.append(T("  {0} ; {1}", N(counts['delie'], "{n} réglage délié de l'arbre", "{n} réglages déliés de l'arbre"), N(store.sauves, "{n} retouche d'un arbre refait copiée dans les sauvegardes", "{n} retouches d'un arbre refait copiées dans les sauvegardes")))
    logf.close()
    txt.append(suite(suite(T("APPLIQUÉ : {0} posés, {1} remplacés, {2} retirés, {3} liés", counts['pose'], counts['remplace'], counts['retire'], counts['lie']), T("modlist.txt à jour") if counts["modlist"] else "",
                           N(store.extraits, "{n} arbre extrait", "{n} arbres extraits") if store else "", sep=T(", ")),
                     T("copies des fichiers écrasés : {0}", stamp) if stamp else ""))
    if plan.get("copies_faute_de_lien"):
        txt.append(N(len(plan['copies_faute_de_lien']), "  ! {n} copie faute de lien possible (magasin sur un autre disque ?)", "  ! {n} copies faute de lien possible (magasin sur un autre disque ?)"))
    if bad:
        txt.append(N(len(bad), "ÉCHEC de vérification sur {n} fichier : {0}", "ÉCHEC de vérification sur {n} fichiers : {0}", bad[:10]))
    out({"compte": counts, "echecs": bad, "sauvegarde": stamp, "message": txt[-1]}, "\n".join(txt))
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
