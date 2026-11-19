"""Red Stack : serveur MCP (stdio) au-dessus de red_stack.py (créé le 2026-11-16).

Une session Claude Code pilote Red Stack comme l'utilisateur : état, détail d'un mod, propriétaire d'un fichier, profils,
bascule, options, priorités, réglages, retouches, plan. Aucune dépendance : JSON-RPC 2.0, un message par ligne.

  python -I red_stack_mcp.py --donnees X [--depot D --jeu J --magasin M | --sans-magasin]

RÈGLE : ce serveur n'écrit JAMAIS le jeu. Les outils changent le PROFIL (un fichier JSON) ; l'application au jeu passe par
`red_stack_demande_application`, qui dépose `demande.json` dans le dossier des données. L'extension VS Code la montre à
l'utilisateur (plan chiffré, Appliquer / Refuser) et lance elle-même `applique --go --si-plan <empreinte>` : ce qui est
appliqué est le plan que l'utilisateur a vu, ou rien. Sans l'extension, l'utilisateur lance la commande à la main.
"""
import argparse, datetime, json, os, subprocess, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "red_stack.py")
LIMIT = 24000                                        # caractères rendus par outil, au plus

P_PROFIL = {"profil": {"type": "string", "description": "Profile name (default: actuel)"}}
P_ONOFF = {"valeur": {"type": "string", "enum": ["on", "off"]}}


def tool(name, desc, props=None, required=()):
    return {"name": name, "description": desc,
            "inputSchema": {"type": "object", "properties": props or {}, "required": list(required)}}


TOOLS = [
    tool("red_stack_etat",
         "State of the mods against a profile. Without a filter: counts per state and per stack, plus the mods that are "
         "not simply “posé” (installed). With a filter (stack, state, text of the name): the matching rows. States are "
         "stable codes in French: posé (installed), à poser (to install), à compléter (to complete), coupé (disabled), "
         "jamais posé (never installed), nouveau dans le dépôt (new in the repository), parqué (parked), nouveau (new "
         "arrival), retiré (removed).",
         {**P_PROFIL, "section": {"type": "string", "description": "Stack, e.g. 12_Weapons"},
          "etat": {"type": "string", "description": "Start of the state code: posé, coupé, à poser, parqué, nouveau, retiré…"},
          "texte": {"type": "string", "description": "Text contained in the zip name"},
          "nature": {"type": "string", "description": "What the zip installs: archive, xl, REDmod, scripts, tweaks, CET, RED4ext, asi, audio, ReShade, réglages "
                                                      "(settings), socle (core: a loader, or a mod that others cite)…"},
          "limite": {"type": "integer", "description": "Maximum number of rows (default 80)"}}),
    tool("red_stack_detail", "Entries of a zip: option, destination in the game, taken by the profile or not, state in the game (codes: lié = "
                             "linked, copié = copied, absent = missing, écrasé par… = overwritten by…, modifié en jeu = modified in game), "
                             "options of the pack, priorities.",
         {**P_PROFIL, "mod": {"type": "string", "description": "Text that designates ONE active zip"}}, ["mod"]),
    tool("red_stack_fichier", "Which mod a game file belongs to (install registry): text contained in the path.",
         {"nom": {"type": "string"}}, ["nom"]),
    tool("red_stack_profils", "Lists the profiles; with `nom` and `source`, creates the profile `nom` by copying `source`.",
         {"nom": {"type": "string"}, "source": {"type": "string"}}),
    tool("red_stack_bascule", "Enables or disables a mod (text) or a whole stack IN THE PROFILE. Does not write the game.",
         {**P_PROFIL, "mod": {"type": "string"}, "section": {"type": "string"}, **P_ONOFF}, ["valeur"]),
    tool("red_stack_option", "Pick-and-choose pack: takes or leaves an options folder of a zip (`nom`) or a single one of its files "
                             "(`entree`), in the profile. Does not write the game. `mien` with `entree`: “this file belongs to this mod”, for "
                             "a game file present under an outside Red Stack pattern (on: the registry takes it when the plan is applied; "
                             "off: handed back).",
         {**P_PROFIL, "mod": {"type": "string"}, "nom": {"type": "string", "description": "Option; “direct” = the root"},
          "entree": {"type": "string", "description": "Path of a file INSIDE the zip, as red_stack_detail gives it"},
          "mien": {"type": "boolean"}, **P_ONOFF}, ["mod", "valeur"]),
    tool("red_stack_priorite", "Two mods deliver the same path with different contents: says which one wins, IN THE PROFILE. `gagnant` + "
                               "`perdant`: rule between the two mods. `gagnant` + `fichier`: this mod holds this single game file, whatever the "
                               "rule between mods. `annule`: forgets the rule.",
         {**P_PROFIL, "gagnant": {"type": "string"}, "perdant": {"type": "string"},
          "fichier": {"type": "string", "description": "Path of ONE file in the game, e.g. r6/scripts/x/y.reds"},
          "annule": {"type": "boolean"}}, ["gagnant"]),
    tool("red_stack_reglage", "Settings: patterns of files never linked to the store (kept as they are in the game). Without an argument: the "
                              "list. `ajoute` / `retire`: a pattern on the destination in the game.",
         {"ajoute": {"type": "string"}, "retire": {"type": "string"}}),
    tool("red_stack_retouches", "Files of a store tree that are no longer those of the zip (local edits). `annule` (with `mod`) puts the zip's "
                                "files back in the tree; the game only changes when the plan is applied.",
         {**P_PROFIL, "mod": {"type": "string"}, "annule": {"type": "boolean"}}),
    tool("red_stack_plan", "What would be installed, replaced, removed in the game for this profile. Writes nothing. Returns the counts, "
                           "the detail per zip, the conflicts, the files kept, and the fingerprint of the plan.", P_PROFIL),
    tool("red_stack_conflits", "Conflicts INSIDE the archives of the profile (read only). The game takes each resource from the first archive "
                               "loaded (byte order of the names, or modlist.txt): an archive wins over those loaded after it, loses to those "
                               "before; identical copies are counted apart. Without an argument: counts and pairs of archives. With `mod` or "
                               "`archive`: its resources, with wins over / loses to. With `ressources`: the reading per resource (taken from, "
                               "lost by, replaces the base game), which `texte` filters (path, archive or mod).",
         {**P_PROFIL, "mod": {"type": "string", "description": "Text that designates ONE active zip"},
          "archive": {"type": "string", "description": "Name of a loaded archive"},
          "ressources": {"type": "boolean"}, "texte": {"type": "string"},
          "limite": {"type": "integer", "description": "Maximum number of pairs or resources returned (default 60)"}}),
    tool("red_stack_scripts", "CODE conflicts of the profile (read only): Redscript (competing @replaceMethod, duplicate @addMethod, "
                              "@wrapMethod that does not call wrappedMethod), TweakXL (same property with different values, removal against "
                              "addition, different lists, competing definitions) and literal SetFlat in code against another mod's tweak. "
                              "Levels: attention (to look at), revoir (to review), rien (compatible), info. The announced “last word” is "
                              "PREDICTED from the order of the file names, never observed in game. The first reading of a large profile takes "
                              "tens of seconds.",
         {**P_PROFIL, "mod": {"type": "string", "description": "Text that designates ONE active zip: its findings only"},
          "niveau": {"type": "string", "enum": ["attention", "revoir", "rien", "info"], "description": "Default: attention and revoir"},
          "limite": {"type": "integer", "description": "Maximum number of findings returned (default 40)"}}),
    tool("red_stack_ordre", "Load order of the archives of archive/pc/mod, IN THE PROFILE (the game follows when the plan is applied). "
                            "Without an argument: the order, and whether modlist.txt is kept by the profile. `archive` + `avant` or `apres` "
                            "(another archive): proposes a name that goes before (it wins) or after, says who cites the archive by name, "
                            "writes nothing; with `voie` = modlist: notes in the profile the wanted order of modlist.txt. `archive` + "
                            "`renomme`: notes in the profile the name of the archive in the game (the zip does not change). `archive` + "
                            "`annule`: gives back the author's name. `annule` alone: stop keeping modlist.txt.",
         {**P_PROFIL, "archive": {"type": "string", "description": "Name of a loaded archive"},
          "avant": {"type": "string"}, "apres": {"type": "string"}, "voie": {"type": "string", "enum": ["nom", "modlist"]},
          "renomme": {"type": "string"}, "annule": {"type": "boolean"},
          "limite": {"type": "integer", "description": "Maximum number of order lines returned (default 80)"}}),
    tool("red_stack_noms", "Names IN THE GAME of what a mod installs (archives, .xl, files and folders of scripts and tweaks, CET folder, "
                           "REDmod folder), and who cites each one by name in the code of the repository (the mod itself included). With "
                           "`noms` = [{de: author's path, vers: new name}]: notes these names in the PROFILE (empty vers = author's name); "
                           "the zip does not change, the game follows when the plan is applied.",
         {**P_PROFIL, "mod": {"type": "string", "description": "Text that designates ONE active zip"},
          "noms": {"type": "array", "items": {"type": "object", "properties": {"de": {"type": "string"}, "vers": {"type": "string"}},
                                              "required": ["de"]}}}, ["mod"]),
    tool("red_stack_fomod", "FOMOD installer of a zip (fomod/ModuleConfig.xml): its pages, its groups (key, type: single choice, several…), "
                            "its choices (taken or not, required, recommended), the pages ruled out by an earlier choice, and what it would "
                            "install. With `choix` = {group key: [names]}, `hors_jeu` (also install what goes outside the game folders) or "
                            "`libre` (ignore the installer, pick by hand): notes it in the PROFILE; the game follows when the plan is "
                            "applied.",
         {**P_PROFIL, "mod": {"type": "string", "description": "Text that designates ONE active zip, or its exact key (stack/[folder/]name.zip)"},
          "choix": {"type": "object", "description": "{group key: [names of the choices]}", "additionalProperties": {"type": "array", "items": {"type": "string"}}},
          "hors_jeu": {"type": "boolean"}, "libre": {"type": "boolean"}}, ["mod"]),
    tool("red_stack_journal", "History of what Red Stack has WRITTEN, most recent first (read only): each application to the game (date, "
                              "profile, counts, and per mod: posé = installed, retiré = removed, mis à jour = updated from which version, "
                              "modifié = modified) and each action on the repository (parque = park, remonte = bring back, retire = move to the retired folder, supprime = retired zip deleted to the system recycle bin, renomme = rename, "
                              "convertit = convert, contenu = content, maj = update downloaded or filed, arrive = new mod received through a "
                              "link, reglages = settings backup or restore). Kept since version 0.10; the present state is read with "
                              "red_stack_etat.",
         {"mod": {"type": "string", "description": "Text contained in the name of a zip: its lines only"},
          "geste": {"type": "string", "enum": ["applique", "parque", "remonte", "retire", "supprime", "renomme", "convertit", "contenu", "maj", "arrive", "reglages"]},
          "depuis": {"type": "string", "description": "Date YYYY-MM-DD (time allowed: YYYY-MM-DDTHH:MM)"},
          "limite": {"type": "integer", "description": "Maximum number of entries returned (default 20)"}}),
    tool("red_stack_demande_application", "Asks the USER to apply the plan to the game. Does not apply it: files the request, which the user confirms or "
                                          "refuses in VS Code (Red Stack). Follow it with red_stack_suivi_demande.",
         {**P_PROFIL, "motif": {"type": "string", "description": "One sentence: why this change"}}),
    tool("red_stack_suivi_demande", "Where the last application request stands (codes): attente (waiting), appliquée (applied), refusée (refused), "
                                    "échec (failed)."),
    tool("red_stack_config", "Paths (repository, game, store, backups, reference), folder convention, outside Red Stack patterns, command run "
                             "before applying. Read only: the settings are changed in VS Code."),
    tool("red_stack_hors", "Outside Red Stack: patterns of game files left to a third-party installer (never linked, replaced or removed). "
                           "Without an argument: the list. `ajoute` / `retire`: a pattern; the effect comes when the plan is applied.",
         {"ajoute": {"type": "string"}, "retire": {"type": "string"}}),
    tool("red_stack_reference", "Checks the base game against the reference (copy of the clean game without its archives): files changed, gone, "
                                "replaced by a mod. Writes nothing; creating or restoring is done in VS Code."),
    tool("red_stack_magasin", "State of the store (one tree per mod, linked to the game) for this profile, read only: number of game files "
                              "linked or copied, size that Explorer adds up against real size on the disk, free room, trees without an active "
                              "mod (what a purge would free), local edits. The purge is done in VS Code.", P_PROFIL),
    tool("red_stack_prerequis", "Requirements of the mods (read only): what each mod needs, from two sources. `nexus` = the list the author "
                                "declares on the mod's Nexus page (no minimum version, and authors also list what they merely recommend: only "
                                "the free-text note tells, `optionnel` is a guess from that note). `fichiers` = a framework deduced from where "
                                "the zip puts its files (CET, RED4ext, redscript, TweakXL, ArchiveXL, Input Loader, Audioware, REDmod), known "
                                "without Nexus. `par` = the zips of the repository that provide it; `etat` (codes): actif = an active zip "
                                "provides it, dans le jeu = present in the game but not installed by Red Stack, coupé = its zip is disabled, "
                                "rangé = its zip is only parked or in an arrivals folder, absent = nowhere, externe = outside Nexus, not "
                                "checkable. Without `mod`: the frameworks, and the ACTIVE mods missing something (`manque` = frameworks, the mod "
                                "will not load; `a_voir` = declared mods not active). With `mod`: its full list and who requires it. `nexus` "
                                "true reads Nexus first for what is not cached yet (public API, no key).",
         {**P_PROFIL, "mod": {"type": "string", "description": "Text that designates ONE active zip, or its exact key (stack/[folder/]name.zip)"},
          "nexus": {"type": "boolean", "description": "Read the declared requirements on Nexus first (only what is not cached)"}}),
    tool("red_stack_sauvegardes", "Backups of the mods' settings (files never linked, delivered or written in game). Without an argument: the "
                                  "list. `cree`: makes one now (dated copy, the game is not touched). `compare` (name of a backup, or “derniere” "
                                  "for the latest): what a restore would change in the game; restoring is done in VS Code.",
         {"cree": {"type": "boolean"}, "compare": {"type": "string"}}),
    tool("red_stack_mises_a_jour", "Updates available on Nexus for the zips of the repository (read only, public API, no key): per zip, the version "
                                   "in place, the Nexus file that replaces it, the proposed name; the “à voir” (to check) cases (archived file, "
                                   "build for another game patch) with their reason; the mods ignored by the user. The files of each mod are kept "
                                   "for six hours (`frais` asks again). Downloading is done in VS Code: the user's API key is never given to the "
                                   "server.",
         {"frais": {"type": "boolean", "description": "Ask Nexus again for the files of all the mods"},
          "mod": {"type": "string", "description": "Text contained in the name of a zip: its lines only"},
          "ignore": {"type": "string", "enum": ["on", "off"], "description": "With `cle`: stop offering (on) or offer again (off) the updates of this mod; noted in the configuration, "
                                                                             "reversible"},
          "cle": {"type": "string", "description": "Exact key of the zip (stack/[folder/]name.zip), for `ignore`"}}),
    tool("red_stack_arrivages", "Arrivals of the repository (read only): zips of the arrivals folders, names in the Nexus app format, .7z / .rar "
                                "to convert. Per row: the status, the proposed name in the site's form, the candidates of a “doute” (to settle) "
                                "case, and `maj_de` when the arrival is the update of a zip in place. Reads the public Nexus API (six-hour "
                                "cache). Renaming, converting, filing, bringing back or parking WRITE the repository: in VS Code.",
         {"texte": {"type": "string", "description": "Text contained in the key of the arrival"}}),
    tool("red_stack_contenu", "Content of ONE zip against the naming convention of the repository (read only): proposed renames (de -> vers), "
                              "paths kept with their reason (hard-coded in another mod, load order…), notes. Rewriting the zip is done in VS "
                              "Code (“Content…”). The first reading of a large repository indexes the references (one minute).",
         {"cle": {"type": "string", "description": "Exact key of the zip (stack/[folder/]name.zip), as red_stack_etat or red_stack_arrivages gives it"},
          "nom": {"type": "string", "description": "Mod name to put in the files (default: taken from the zip name)"}}, ["cle"]),
]


class Erreur(Exception):
    pass


class Serveur:
    def __init__(self, a):
        self.base = []
        for k in ("depot", "jeu", "donnees", "magasin"):
            if getattr(a, k):
                self.base += ["--" + k, getattr(a, k)]
        if a.sans_magasin:
            self.base.append("--sans-magasin")
        self.data = os.path.abspath(a.donnees or os.path.join(HERE, "red_stack"))
        self.demande = os.path.join(self.data, "demande.json")

    def rs(self, *args):
        r = subprocess.run([sys.executable, "-I", TOOL, *args, *self.base, "--langue", "en", "--json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        if r.returncode:
            raise Erreur((r.stderr or r.stdout).strip()[-2000:] or f"red_stack.py: code {r.returncode}")
        try:
            return json.loads(r.stdout)
        except ValueError:
            raise Erreur("Unreadable output from red_stack.py: " + r.stdout[:500])

    # ------------------------------------------------------------ outils

    def red_stack_etat(self, p):
        d = self.rs("etat", "--profil", p.get("profil") or "actuel")
        rows = d["mods"]
        filtre = any(p.get(k) for k in ("section", "etat", "texte", "nature"))
        if p.get("section"):
            rows = [r for r in rows if r["section"].lower() == p["section"].lower()]
        if p.get("etat"):
            rows = [r for r in rows if r["etat"].lower().startswith(p["etat"].lower())]
        if p.get("texte"):
            rows = [r for r in rows if p["texte"].lower() in r["cle"].lower()]
        if p.get("nature"):
            rows = [r for r in rows if p["nature"].lower() in [x.lower() for x in r.get("natures") or []]]
        compte, piles = {}, {}
        for r in d["mods"]:
            compte[r["etat"]] = compte.get(r["etat"], 0) + 1
            s = piles.setdefault(r["section"], {"zips": 0, "actifs": 0})
            s["zips"] += 1
            s["actifs"] += r["etat"].startswith(("posé", "à poser", "à compléter"))
        if not filtre:
            rows = [r for r in rows if r["etat"] != "posé" and not r["etat"].startswith(("parqué", "retiré", "nouveau ("))]
        n = int(p.get("limite") or 80)
        return {"compte": compte, "piles": piles, "lignes": len(rows), "notes": d["notes"], "conflits": d["conflits"],
                "anciennes_versions": d["anciennes"],
                "mods": [{k: r[k] for k in ("cle", "version", "etat", "taille", "fichiers_poses", "sel", "natures") if r.get(k) not in (None, "", [])}
                         for r in rows[:n]]}

    def red_stack_detail(self, p):
        return self.rs("detail", "--profil", p.get("profil") or "actuel", "--mod", p["mod"])

    def red_stack_fichier(self, p):
        return self.rs("fichier", "--nom", p["nom"])

    def red_stack_profils(self, p):
        if p.get("nom") or p.get("source"):
            if not (p.get("nom") and p.get("source")):
                raise Erreur("Creating a profile: `nom` AND `source`.")
            return self.rs("profils", "--profil", p["nom"], "--copie", p["source"])
        return self.rs("profils")

    def red_stack_bascule(self, p):
        if bool(p.get("mod")) == bool(p.get("section")):
            raise Erreur("bascule: `mod` OR `section`, not both.")
        cible = ["--mod", p["mod"]] if p.get("mod") else ["--section", p["section"]]
        d = self.rs("bascule", p["valeur"], "--profil", p.get("profil") or "actuel", *cible)
        return dict(d, suite="Profile changed, game unchanged: red_stack_plan to see, red_stack_demande_application to ask.")

    def red_stack_option(self, p):
        if not p.get("nom") and not p.get("entree"):
            raise Erreur("option: `nom` (an options folder) OR `entree` (a file of the zip).")
        cible = ["--entree", p["entree"]] if p.get("entree") else ["--nom", p["nom"]]
        if p.get("mien") and not p.get("entree"):
            raise Erreur("option: `mien` needs `entree` (the file of the zip that the mod claims).")
        return self.rs("option", p["valeur"], "--profil", p.get("profil") or "actuel", "--mod", p["mod"], *cible,
                       *(["--mien"] if p.get("mien") else []))

    def red_stack_priorite(self, p):
        if bool(p.get("perdant")) == bool(p.get("fichier")):
            raise Erreur("priorite: `perdant` (rule between two mods) OR `fichier` (a single game file), not both.")
        cible = ["--fichier", p["fichier"]] if p.get("fichier") else ["--perdant", p["perdant"]]
        return self.rs("priorite", "--profil", p.get("profil") or "actuel", "--gagnant", p["gagnant"], *cible,
                       *(["--annule"] if p.get("annule") else []))

    def red_stack_reglage(self, p):
        args = [x for k in ("ajoute", "retire") if p.get(k) for x in ("--" + k, p[k])]
        d = self.rs("reglage", *args)
        return d if args else {"utilisateur": d["utilisateur"], "defaut": d["defaut"]}

    def red_stack_retouches(self, p):
        args = ["--mod", p["mod"]] if p.get("mod") else []
        return self.rs("retouche", "--profil", p.get("profil") or "actuel", *args, *(["--annule"] if p.get("annule") else []))

    def red_stack_conflits(self, p):
        cible = ["--mod", p["mod"]] if p.get("mod") else ["--nom=" + p["archive"]] if p.get("archive") else []
        if p.get("ressources") and cible:
            raise Erreur("conflits: `ressources` is read over the whole profile; narrow it with `texte`, not with `mod` or `archive`.")
        d = self.rs("conflits", "--profil", p.get("profil") or "actuel", *(["--ressources"] if p.get("ressources") else cible))
        n = int(p.get("limite") or 60)
        o = d["ordre"]
        nom = lambda i: {"rang": i + 1, "archive": o[i]["archive"], "mod": o[i]["zip"] or "(outside Red Stack)"}
        tete = {k: d[k] for k in ("profil", "ordre_par", "compte", "illisibles")}
        if p.get("ressources"):                      # lecture par ressource : où le jeu la prend, qui la perd
            lib = lambda i: f"{o[i]['archive']} ({o[i]['zip'] or "outside Red Stack"})"
            rows = [{"ressource": r["ressource"], "prise_dans": lib(r["prise_dans"]), "perdue_par": [lib(i) for i in r["perd"]],
                     **({"identique_dans": [lib(i) for i in r["identiques"]]} if r["identiques"] else {}),
                     **({"remplace_le_jeu_de_base": True} if r["base"] else {})} for r in d["ressources"]]
            if p.get("texte"):
                t = p["texte"].lower()
                rows = [r for r in rows if t in json.dumps(r, ensure_ascii=False).lower()]
            return {**tete, "en_conflit": d["total"], "copies_identiques_sans_conflit": len(d["identiques"]),
                    "trouvees": len(rows), "ressources": rows[:n]}
        if cible:
            return {**tete, "archives": [dict(nom(i), **{k: o[i][k] for k in ("ressources", "gagne", "perd", "identiques")}) for i in d["cible"]],
                    "total": d["total"],
                    "ressources": [{"ressource": r["ressource"], "archive": o[r["archive"]]["archive"],
                                    **{k: [o[i]["archive"] for i in r[k]] for k in ("gagne_sur", "perd_contre", "identique_a") if r[k]}}
                                   for r in d["ressources"][:n]]}
        paires = [r for r in d["paires"] if r["conflits"]]
        return {**tete, "paires_montrees": min(n, len(paires)),
                "paires": [{"gagnant": nom(r["gagnant"]), "perdant": nom(r["perdant"]), "ressources": r["conflits"],
                            "identiques": r["identiques"], "meme_mod": r["meme_mod"], "exemples": r["exemples"]} for r in paires[:n]]}

    def red_stack_scripts(self, p):
        d = self.rs("scripts", "--profil", p.get("profil") or "actuel", *(["--mod", p["mod"]] if p.get("mod") else []))
        veut = [p["niveau"]] if p.get("niveau") else ["attention", "revoir"]
        vues = [t for t in d["trouvailles"] if t["niveau"] in veut]
        n = int(p.get("limite") or 40)
        court = lambda t: {"niveau": t["niveau"], "voie": t["voie"], "sorte": t["sorte"], "cible": t["cible"],
                           **({"dernier_mot_prevu": t["lignes"][t["gagnant"]]["fichier"]} if t.get("gagnant") is not None else {}),
                           **({"raison": t["raison"]} if t.get("raison") else {}),
                           "lignes": [{"mod": l["prov"], "fichier": l["fichier"], "ligne": l["ligne"], "geste": l["geste"],
                                       **({"valeur": l["valeur"][:120]} if l["valeur"] else {})} for l in t["lignes"][:12]]}
        return {"profil": d["profil"], "lus": d["lus"], "compte": d["compte"], "sortes": d["sortes"], "limites": d["limites"][:20],
                "limites_total": len(d["limites"]), "trouvailles": [court(t) for t in vues[:n]], "total": len(vues)}

    def red_stack_ordre(self, p):
        args = ["--nom=" + p["archive"]] if p.get("archive") else []
        for k in ("avant", "apres", "renomme"):
            if p.get(k):
                args.append(f"--{k}={p[k]}")
        if p.get("voie"):
            args += ["--voie", p["voie"]]
        if p.get("annule"):
            args += ["--annule"] + ([] if p.get("archive") else ["--modlist"])
        d = self.rs("ordre", "--profil", p.get("profil") or "actuel", *args)
        tete = {"profil": d["profil"], "ordre_par": d["ordre_par"], "archives": len(d["ordre"]),
                "modlist": dict(d["modlist"], lignes=len(d["modlist"]["lignes"]))}
        if d["propose"] or d["fait"]:
            return {**tete, "propose": d["propose"], "fait": d["fait"],
                    "suite": "nothing written" if d["propose"] else "noted in the profile; the game follows when the plan is applied (red_stack_plan)"}
        n = int(p.get("limite") or 80)
        return {**tete, "ordre": [f"{o['rang']} {o['archive']}" + (f" (auteur : {o['origine']})" if o["renommee"] else "")
                                  + ("" if o["zip"] else " [outside Red Stack]") for o in d["ordre"][:n]]}

    def red_stack_noms(self, p):
        args = ["--fixe", json.dumps(p["noms"], ensure_ascii=False)] if p.get("noms") else []
        d = self.rs("noms", "--profil", p.get("profil") or "actuel", "--mod", p["mod"], *args)
        court = lambda cites: sorted({c["zip"] + ("  (the mod itself)" if c["soi"] else "") for c in cites})
        out = {"profil": d["profil"], "mod": d["cle"], "actif": d["actif"],
               "noms": [{"genre": u["genre"], "auteur": u["chemin"], "dans_le_jeu": u["actuel"], "renomme": u["renommee"],
                         **({"cite_par": court(u["cites"])} if u["cites"] else {}), **({"note": u["note"]} if u["note"] else {})}
                        for u in d["unites"]]}
        if d["fait"]:
            out["fait"] = [{"de": f["de"], "vers": f["vers"], **({"a_relire": court(f["cites"])} if f["cites"] else {})} for f in d["fait"]]
            out["suite"] = "noted in the profile; the game follows when the plan is applied (red_stack_plan)"
        return out

    def red_stack_fomod(self, p):
        neuf = {k: p[k] for k in ("choix", "hors_jeu", "libre") if k in p}
        cible = ["--cle", p["mod"]] if p["mod"].lower().endswith(".zip") and "/" in p["mod"] else ["--mod", p["mod"]]
        d = self.rs("fomod", "--profil", p.get("profil") or "actuel", *cible, *(["--fixe", json.dumps(neuf, ensure_ascii=False)] if neuf else []))
        if d.get("fomod") is False:
            return d
        for pg in d["pages"]:
            for g in pg["groupes"]:
                g["plugins"] = [{"nom": x["nom"], "choisi": x["choisi"], **({"usage": x["usage"]} if x["usage"] != "Optional" else {}),
                                 **({"description": x["desc"][:300]} if x["desc"] else {})} for x in g["plugins"]]
        d["fichiers_total"], d["fichiers"] = len(d["fichiers"]), [f"{f['dest']}  <-  {f['entree']}" for f in d["fichiers"][:60]]
        if d.get("fait"):
            d["suite"] = "noted in the profile; the game follows when the plan is applied (red_stack_plan)"
        return d

    def red_stack_journal(self, p):
        args = [x for k in ("mod", "geste", "depuis") if p.get(k) for x in ("--" + k, str(p[k]))]
        d = self.rs("journal", "--limite", str(int(p.get("limite") or 20)), *args)
        for e in d["entrees"]:                       # une grosse application : quarante mods, le reste compté
            if len(e.get("mods", [])) > 40:
                e["mods_total"], e["mods"] = len(e["mods"]), e["mods"][:40]
        return d

    def plan(self, profil):
        d = self.rs("plan", "--profil", profil)
        par_zip = {}
        for k in ("pose", "remplace", "retire", "lie", "delie"):
            for r in d[k]:
                par_zip.setdefault(r["zip"], {}).setdefault(k, 0)
                par_zip[r["zip"]][k] += 1
        return d, {"profil": profil, "compte": d["compte"], "empreinte": d["empreinte"], "vrai_jeu": d["reel"],
                   "jeu_lance": d["jeu_lance"], "deja_en_place": d["ok"], "par_zip": par_zip, "conflits": d["conflit"],
                   "gardes_modifies_en_jeu": [f"{r['dest']} ({r.get('raison', '')})" for r in d["garde_modifie"][:60]],
                   "presents_non_poses_par_l_outil": [r["dest"] for r in d["inconnu"][:60]], "notes": d["notes"],
                   "mods_coupes": d.get("coupes", []), "actifs_sans_un_prerequis": d.get("prerequis", []),
                   "lies_repris_d_un_autre_mod": [f"{r['dest']} ({r['ancien']} -> {r['zip']})" for r in d["lie"] if r.get("ancien")][:60]}

    def red_stack_plan(self, p):
        return self.plan(p.get("profil") or "actuel")[1]

    def red_stack_demande_application(self, p):
        d, resume = self.plan(p.get("profil") or "actuel")
        ecrit = sum(d["compte"][k] for k in ("pose", "remplace", "retire", "lie", "delie", "pris", "rendu", "modlist"))
        if not ecrit:
            return {"demande": None, "message": "Nothing to write in the game for this profile: no request filed.", **resume}
        if d["compte"]["conflit"]:
            raise Erreur(f"{d['compte']['conflit']} conflict(s) to settle first (red_stack_priorite): "
                         + " ; ".join(c["dest"] + " <- " + " | ".join(c["zips"]) for c in d["conflit"][:10]))
        dem = {"id": uuid.uuid4().hex[:12], "date": datetime.datetime.now().isoformat(timespec="seconds"), "etat": "attente",
               "profil": resume["profil"], "empreinte": d["empreinte"], "compte": d["compte"], "par_zip": resume["par_zip"],
               "motif": (p.get("motif") or "")[:400], "vrai_jeu": d["reel"]}
        os.makedirs(self.data, exist_ok=True)
        tmp = self.demande + ".tmp"
        json.dump(dem, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(tmp, self.demande)
        return {"demande": dem["id"], "etat": "attente", "jeu_lance": d["jeu_lance"],
                "message": "Request filed. The user confirms or refuses it in VS Code (Red Stack). Nothing is written until then: do not "
                           "try to apply it any other way. Follow-up: red_stack_suivi_demande."
                           + (" The game is running: they will have to close it first." if d["jeu_lance"] else ""),
                "a_la_main": f"python -I red_stack.py applique --profil {resume['profil']} --go --vrai-jeu --si-plan {d['empreinte']}",
                "compte": d["compte"], "par_zip": resume["par_zip"]}

    def red_stack_suivi_demande(self, p):
        if not os.path.isfile(self.demande):
            return {"demande": None, "message": "No request."}
        return json.load(open(self.demande, encoding="utf-8"))

    def red_stack_config(self, p):
        c = self.rs("config")
        for k in ("reglages", "reglages_defaut", "convention_defaut"):
            c.pop(k, None)
        return {**c, "arguments_du_serveur": self.base}

    def red_stack_hors(self, p):
        return self.rs("hors", *[x for k in ("ajoute", "retire") if p.get(k) for x in ("--" + k, p[k])])

    def red_stack_reference(self, p):
        d = self.rs("reference")                     # contrôle seul : créer ou restaurer reste un geste de l'utilisateur
        for k in ("modifies", "manquants", "par_mod"):
            d[k + "_total"], d[k] = len(d[k]), d[k][:60]
        return d

    def red_stack_magasin(self, p):
        d = self.rs("magasin", "--profil", p.get("profil") or "actuel")
        d["sans_mod_total"], d["sans_mod"] = len(d["sans_mod"]), d["sans_mod"][:60]
        d["retouches_total"], d["retouches"] = len(d["retouches"]), d["retouches"][:60]
        return d

    def red_stack_prerequis(self, p):
        d = self.rs("prerequis", "--profil", p.get("profil") or "actuel", *(["--mod", p["mod"]] if p.get("mod") else []),
                    *(["--nexus"] if p.get("nexus") else []))
        if p.get("mod"):                             # un mod : sa liste entière, et qui l'exige (soixante noms, le reste compté)
            r = d["mods"][0]
            r["requis_par_total"], r["requis_par"] = len(r["requis_par"]), r["requis_par"][:60]
            return {"mod": r, "erreur": d["erreur"]}
        absents = lambda r: [{k: e[k] for k in ("nom", "cadre", "mod", "etat", "notes", "par")}
                             for e in r["requis"] if e["etat"] in ("coupé", "rangé", "absent") and not e["optionnel"]]
        vus = [{"cle": r["cle"], "manque": r["manque"], "a_voir": r["a_voir"], "absents": absents(r)} for r in d["mods"] if r["manque"] or r["a_voir"]]
        for c in d["cadres"]:
            c["par"] = c["par"][:5]
        return {"cadres": d["cadres"], "lus_sur_nexus": d["compte"], "mods_sans_un_cadre": d["manques"], "mods_a_voir": d["a_voir"],
                "optionnels_absents": d["optionnels"], "mods": vus[:80], "mods_total": len(vus), "erreur": d["erreur"]}

    def red_stack_sauvegardes(self, p):
        if p.get("cree"):
            return self.rs("sauvegarde", "--cree")["cree"]
        if p.get("compare"):                         # aperçu seul : jamais --go ici
            nom = [] if p["compare"].lower() in ("derniere", "dernière") else ["--nom", p["compare"]]
            d = self.rs("sauvegarde", "--restaure", *nom)
            for k in ("changes", "absents"):
                d[k + "_total"], d[k] = len(d[k]), d[k][:80]
            return d
        d = self.rs("sauvegarde")
        return {"dossier": d["dossier"], "total": len(d["sauvegardes"]), "sauvegardes": d["sauvegardes"][:30]}

    def red_stack_arrivages(self, p):
        d = self.rs("convention")                    # sans --fixe, --convertit ni --range : rien n'est écrit
        rows = [r for r in d["lignes"] if (p.get("texte") or "").lower() in r["cle"].lower()]
        garde = ("cle", "taille", "statut", "propose", "nexus", "convertir", "candidats", "maj_de")
        court = lambda r: {k: r[k] for k in garde if r.get(k) not in (None, "", [], False)}
        return {"compte": d["compte"], "erreur": d["erreur"], "extracteur": d["extracteur"], "total": len(rows),
                "arrivages": [court(r) for r in rows[:80]],
                "suite": "Read only: renaming, converting, filing an update, bringing back or parking are done in VS Code."}

    def red_stack_contenu(self, p):
        d = self.rs("contenu", "--cle", p["cle"], *(["--nom", p["nom"]] if p.get("nom") else []))   # sans --fixe : aperçu seul
        d.pop("fichiers", None)
        d["ops_total"], d["ops"] = len(d["ops"]), d["ops"][:150]
        d["gardes_total"], d["gardes"] = len(d["gardes"]), d["gardes"][:80]
        return d

    def red_stack_mises_a_jour(self, p):
        if p.get("ignore"):
            if not p.get("cle"):
                raise Erreur("mises à jour: `ignore` needs `cle` (the exact key of the zip).")
            return self.rs("nexus", p["ignore"], "--cle", p["cle"], "--ignore")
        d = self.rs("nexus", *(["--force"] if p.get("frais") else []))
        if p.get("mod"):
            d["lignes"] = [r for r in d["lignes"] if p["mod"].lower() in r["cle"].lower()]
        for r in d["lignes"]:
            r.pop("qui", None)
        d["hors_total"], d["hors"] = len(d["hors"]), d["hors"][:40]
        d.pop("cle_api", None)
        return d

    # ------------------------------------------------------------ protocole

    def handle(self, msg):
        m, mid = msg.get("method"), msg.get("id")
        if mid is None:                              # notification : pas de réponse
            return None
        if m == "initialize":
            return {"protocolVersion": (msg.get("params") or {}).get("protocolVersion") or "2025-06-18",
                    "capabilities": {"tools": {}}, "serverInfo": {"name": "red-stack", "version": "0.18.0"},
                    "instructions": "Red Stack, mod manager for Cyberpunk 2077. The tools change a PROFILE, never the game. To write the game: "
                                    "red_stack_plan, then red_stack_demande_application, and the user confirms in VS Code. Never run `applique --go` "
                                    "in their place. The zip REPOSITORY (parking, bringing back, renaming, converting, rewriting a content, "
                                    "downloading an update) is not written from here either: those actions belong to the user, in VS Code; the tools "
                                    "prepare them read-only (red_stack_arrivages, red_stack_contenu, red_stack_mises_a_jour). Tool names, "
                                    "parameters, JSON keys and state codes are French identifiers (posé = installed, coupé = disabled, parqué = "
                                    "parked, retiré = removed, lié = linked, copié = copied); the free texts are in English."}
        if m == "ping":
            return {}
        if m == "tools/list":
            return {"tools": TOOLS}
        if m == "tools/call":
            p = msg.get("params") or {}
            fn = getattr(self, p.get("name") or "", None) if str(p.get("name")).startswith("red_stack_") else None
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
    for k in ("depot", "jeu", "donnees", "magasin"):
        ap.add_argument("--" + k)
    ap.add_argument("--sans-magasin", action="store_true")
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
