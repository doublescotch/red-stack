"""Banc de red_stack_wk_mcp.py : parle JSON-RPC au serveur, qui lance la vraie CLI WolvenKit sur un vrai jeu.

  python -I red_stack_wk_mcp_test.py <dossier ou exe de la CLI WolvenKit> <dossier du jeu>
Le jeu n'est que LU. Tout ce que le serveur écrit va dans un atelier jetable, C:\\__DEV\\cyberpunk\\red_stack\\wk_atelier,
vidé au départ. Le banc vérifie le protocole, chaque outil, les gardes (atelier, motifs, plafond) et que les archives des
mods du jeu n'ont pas bougé.
"""
import json, os, shutil, subprocess, sys, zipfile

if len(sys.argv) != 3:
    sys.exit(__doc__)
CLI, JEU = sys.argv[1], sys.argv[2]
BASE = r"C:\__DEV\cyberpunk\red_stack"
ATELIER, DONNEES = os.path.join(BASE, "wk_atelier"), os.path.join(BASE, "wk_donnees")
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extension", "moteur")
MODS = os.path.join(JEU, "archive", "pc", "mod")
fails = []


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  KO   ") + label + (f"  {str(detail)[:600]}" if not cond else ""))
    if not cond:
        fails.append(label)


class Client:
    def __init__(self, *args):
        self.n = 0
        self.p = subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "red_stack_wk_mcp.py"), *args], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, encoding="utf-8")

    def rpc(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}) + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def call(self, name, **args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})["result"]
        t = r["content"][0]["text"]
        return (t if r["isError"] else json.loads(t)), r["isError"]

    def ferme(self):
        self.p.stdin.close()
        return self.p.wait(timeout=20)


def photo(d):
    return sorted((f, os.path.getsize(os.path.join(d, f)), os.stat(os.path.join(d, f)).st_mtime_ns) for f in os.listdir(d))


def fichiers(d):
    return sorted(os.path.relpath(os.path.join(a, f), d) for a, _, fs in os.walk(d) for f in fs)


for d in (ATELIER, DONNEES):
    shutil.rmtree(d, ignore_errors=True)
os.makedirs(DONNEES)
json.dump({"jeu": JEU, "depot": os.path.join(BASE, "depot"), "wolvenkit": CLI, "atelier": ATELIER},
          open(os.path.join(DONNEES, "config.json"), "w", encoding="utf-8"))
avant = photo(MODS)
srv = Client("--donnees", DONNEES)

print("1. protocole")
r = srv.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "banc", "version": "0"}})
check("initialize : nom du serveur et consignes", r["result"]["serverInfo"]["name"] == "red-stack-wolvenkit"
      and "WORKSHOP" in r["result"]["instructions"], r)
tools = srv.rpc("tools/list")["result"]["tools"]
check("tools/list : 11 outils wk_, tous avec un schéma objet",
      len(tools) == 11 and all(t["name"].startswith("wk_") and t["inputSchema"]["type"] == "object" for t in tools), len(tools))
check("méthode inconnue = erreur -32601", srv.rpc("nimporte")["error"]["code"] == -32601)
r = srv.rpc("tools/call", {"name": "red_stack_etat", "arguments": {}})
check("outil d'un autre serveur = erreur JSON-RPC, le serveur survit", r["error"]["code"] == -32601 and srv.rpc("ping")["result"] == {})

print("2. lecture")
i, err = srv.call("wk_info")
check("info : version de la CLI, archives du jeu comptées, atelier pas encore créé",
      not err and i["cli"]["version"][0].isdigit() and i["jeu"]["base"] > 10 and i["atelier"]["existe"] is False and "manque" not in i, i)
h, err = srv.call("wk_hash", chemins=["polarity/icons/Polarity_Icon.xbm"])
check("hash : même valeur que la CLI (casse et barres normalisées)", not err and h["empreintes"][0]["decimal"] == "15983143053837098272", h)
c, err = srv.call("wk_cherche", texte="item_icons inkatlas common", ou="base")
cible = r"base\gameplay\gui\common\icons\item_icons.inkatlas"
ligne = next((x for x in c["ressources"] if x["ressource"].lower() == cible), None) if not err else None
check("cherche : la ressource du jeu de base, et l'archive de content qui la porte",
      bool(ligne) and any(a.startswith("archive/pc/content/") for a in ligne["dans"]), c)
c, err = srv.call("wk_cherche", texte="ab")
check("cherche : un texte trop court est refusé", err and "three" in c, c)
petite = min((f for f in os.listdir(MODS) if f.lower().endswith(".archive") and os.path.getsize(os.path.join(MODS, f)) > 4096),
             key=lambda f: os.path.getsize(os.path.join(MODS, f)))
l, err = srv.call("wk_liste", archive=petite)
check(f"liste : {petite} désignée par son nom seul, des ressources", not err and l["archives"][0]["ressources_total"] > 0, l)
res = l["archives"][0]["ressources"][0] if not err else ""
l2, err = srv.call("wk_liste", archive=os.path.join(MODS, petite), motif="*" + res.split("\\")[-1])
check("liste : chemin complet et motif, la ressource cherchée seule ou presque",
      not err and res in l2["archives"][0]["ressources"] and l2["archives"][0]["ressources_total"] <= l["archives"][0]["ressources_total"], l2)
l3, err = srv.call("wk_liste", archive="zz_aucune_archive_de_ce_nom")
check("liste : archive inconnue = erreur d'outil", err and "not found" in l3, l3)
check("AUCUN atelier créé par les lectures", not os.path.exists(ATELIER))

print("3. gardes")
for nom, args in (("motif « * »", {"motif": "*"}), ("motif « *.* »", {"motif": "*.*"}), ("motif vide", {"motif": "  "}),
                  ("regex « .* »", {"regex": ".*"}), ("regex « a* » (prend le vide)", {"regex": "a*"}),
                  ("motif ET regex", {"motif": "*abc*", "regex": "abc"}), ("aucun choix", {})):
    r, err = srv.call("wk_extrait", archive=petite, **args)
    check(f"extrait refusé : {nom}", err and not os.path.exists(ATELIER), r)
r, err = srv.call("wk_extrait", ou="ep1", motif="*.mesh")
check("extrait : au-dessus du plafond rien n'est écrit, le compte et des exemples sont rendus",
      not err and r["ecrit"] == 0 and "ceiling 200" in r["refuse"] and len(r["exemples"]) == 30 and not os.path.exists(ATELIER), r)
r, err = srv.call("wk_extrait", archive=petite, motif="*" + res.split("\\")[-1], dans="..\\dehors")
check("extrait refusé : `dans` qui remonte", err and "refused" in r and not os.path.exists(os.path.join(BASE, "dehors")), r)
r, err = srv.call("wk_exporte", ou="base", motif="*.xbm")
check("exporte refusé sur un lieu entier (une archive ou un mod seulement)", err and "Source" in r, r)
r, err = srv.call("wk_json", fichier=os.path.join(MODS, petite))
check("json refusé : fichier hors de l'atelier", err and "outside the workshop" in r, r)
for mot, lieu in (("dans le jeu", os.path.join(JEU, "wk_atelier_interdit")), ("qui contient le jeu", os.path.dirname(JEU.rstrip("\\/"))),
                  ("dans les données", os.path.join(DONNEES, "atelier"))):
    s2 = Client("--donnees", DONNEES, "--atelier", lieu)
    r, err = s2.call("wk_extrait", archive=petite, motif="*" + res.split("\\")[-1])
    check(f"atelier {mot} : refusé, rien créé", err and "Workshop refused" in r and (not lieu.startswith(JEU) or not os.path.exists(lieu)), r)
    s2.ferme()
vide = os.path.join(BASE, "wk_donnees_vides")
os.makedirs(vide, exist_ok=True)
s2 = Client("--donnees", vide, "--cli", CLI, "--jeu", JEU)
r, err = s2.call("wk_extrait", archive=petite, motif="*" + res.split("\\")[-1])
check("sans atelier réglé : refusé", err and "No workshop" in r, r)
i2, err = s2.call("wk_info")
check("info dit ce qui manque", not err and i2["atelier"] is None and len(i2["manque"]) == 1, i2)
s2.ferme()

print("4. écritures dans l'atelier")
r, err = srv.call("wk_extrait", archive=petite, motif="*" + res.split("\\")[-1], dans="essai/un")
check("extrait par motif : fichier écrit sous l'atelier, compté",
      not err and r["ecrit"] >= 1 and r["ecrit"] == r["prevus"] and os.path.isfile(os.path.join(ATELIER, "essai", "un", *res.split("\\"))), r)
r, err = srv.call("wk_extrait", ou="base", hash=str(4472749797847136833), dans="essai/hash")
r2, _ = srv.call("wk_hash", chemins=[cible])
r, err = srv.call("wk_extrait", ou="base", hash=r2["empreintes"][0]["hexa"], dans="essai/hash")
check("extrait par empreinte (hexadécimale) dans tout le jeu de base : un fichier",
      not err and r["ecrit"] == 1 and os.path.isfile(os.path.join(ATELIER, "essai", "hash", *cible.split("\\"))), r)
j, err = srv.call("wk_json", ressource=cible.replace("\\", "/"), ou="base", chemin="Data.RootChunk.$type")
check("json : ressource du jeu de base lue, branche demandée rendue", not err and j["texte"] == '"inkTextureAtlas"' and os.path.isfile(j["json"]), j)
j, err = srv.call("wk_json", fichier=os.path.join("essai", "hash", *cible.split("\\")), max_car=600)
check("json : fichier de l'atelier, texte coupé et dit", not err and len(j["texte"]) == 600 and "coupe" in j and '"Header"' in j["texte"], j)
j, err = srv.call("wk_json", fichier=os.path.join("essai", "hash", *cible.split("\\")), chemin="Data.RootChunk.pas_la")
check("json : branche absente = erreur qui liste les clés", err and "missing" in j and "slots" in j, j)
x, err = srv.call("wk_cherche", texte="xbm icon", ou="mods", limite=5)
tex = next((t for t in x["ressources"] if t["dans"]), None) if not err else None
check("cherche dans les mods : une texture et son archive", bool(tex), x)
if tex:
    r, err = srv.call("wk_exporte", archive=tex["dans"][0].split("/")[-1], motif="*" + tex["ressource"].split("\\")[-1], dans="essai/export")
    png = os.path.join(ATELIER, "essai", "export", "raw", *tex["ressource"].split("\\"))[:-4] + ".png"
    check("exporte : la texture en .png sous raw", not err and r["ecrit"] >= 2 and os.path.isfile(png) and open(png, "rb").read(4) == b"\x89PNG", r)
i, err = srv.call("wk_info")
check("info : l'atelier existe et compte ses fichiers", not err and i["atelier"]["existe"] and i["atelier"]["fichiers"] == len(fichiers(ATELIER)), i)

print("5. retouche d'un vrai fichier du jeu")
atlas = os.path.join(ATELIER, "essai", "hash", *cible.split("\\"))
octets0 = open(atlas, "rb").read()
P0 = "Data.RootChunk.slots.Elements.0.parts"
r, err = srv.call("wk_retouche", fichier=atlas, operations=[{"op": "fixe", "chemin": P0 + ".0.partName.$value", "valeur": "banc_red_stack"}], essai=True)
check("retouche à l'essai : avant et après rendus, fichier intact",
      not err and r["ecrit"] == 0 and r["operations"][0]["avant"] == '"icon_womanboots"' and open(atlas, "rb").read() == octets0, r)
for nom, ops in (("chemin absent", [{"op": "fixe", "chemin": P0 + ".0.pas_la", "valeur": 1}]),
                 ("une valeur remplacée par une liste", [{"op": "fixe", "chemin": P0 + ".0.partName.$value", "valeur": [1]}]),
                 ("chemin hors de Data", [{"op": "fixe", "chemin": "Header.GameVersion", "valeur": 1}]),
                 ("la seconde opération fausse annule la première", [{"op": "fixe", "chemin": P0 + ".0.partName.$value", "valeur": "x"},
                                                                      {"op": "retire", "chemin": P0 + ".9999"}]),
                 ("opération inconnue", [{"op": "efface", "chemin": P0}]), ("aucune opération", [])):
    r, err = srv.call("wk_retouche", fichier=atlas, operations=ops)
    check(f"retouche refusée : {nom}", err and open(atlas, "rb").read() == octets0, r)
r, err = srv.call("wk_retouche", fichier=os.path.join(MODS, petite), operations=[{"op": "retire", "chemin": "Data.x"}])
check("retouche refusée : fichier hors de l'atelier", err and "outside the workshop" in r, r)
r, err = srv.call("wk_retouche", fichier=os.path.join("essai", "hash", *cible.split("\\")) + ".json", operations=[
    {"op": "fixe", "chemin": P0 + ".0.partName.$value", "valeur": "banc_red_stack"},
    {"op": "fixe", "chemin": P0 + ".0.clippingRectInUVCoords.Left", "valeur": 0.1},
    {"op": "copie", "chemin": P0 + ".1"},
    {"op": "retire", "chemin": P0 + ".2"},
    {"op": "ajoute", "chemin": P0, "rang": 0, "valeur": {"$type": "inkTextureAtlasMapper", "clippingRectInPixels": {
        "$type": "Rect", "bottom": 0, "left": 0, "right": 0, "top": 0}, "clippingRectInUVCoords": {
        "$type": "RectF", "Bottom": 0.5, "Left": 0.25, "Right": 0.75, "Top": 0.125}, "partName": {
        "$type": "CName", "$storage": "string", "$value": "banc_ajoute"}}}])
avant_f = os.path.join(ATELIER, "_avant", "essai", "hash", *cible.split("\\"))
check("retouche (désignée par son .json) : cinq opérations, fichier refait, relu identique par la CLI",
      not err and r["ecrit"] == 1 and r["relu"].startswith("identical") and open(atlas, "rb").read() != octets0, r)
check("retouche : le premier original est gardé sous _avant, octet pour octet",
      not err and r["original"] == avant_f and open(avant_f, "rb").read() == octets0, r)
j, err = srv.call("wk_json", fichier=atlas, chemin=P0 + ".1.partName.$value")
j2, err2 = srv.call("wk_json", fichier=atlas, chemin=P0 + ".0.partName.$value")
j3, err3 = srv.call("wk_json", fichier=atlas, chemin=P0)
n3 = len(json.load(open(j3["json"], encoding="utf-8"))["Data"]["RootChunk"]["slots"]["Elements"][0]["parts"]) if not err3 else 0
check("retouche relue par wk_json : nom fixé, élément ajouté en tête, 116 + 1 + 1 - 1 parts",
      not err and not err2 and j["texte"] == '"banc_red_stack"' and j2["texte"] == '"banc_ajoute"' and n3 == 117, (j, j2, n3))
r, err = srv.call("wk_retouche", fichier=atlas, operations=[{"op": "fixe", "chemin": P0 + ".1.partName.$value", "valeur": "banc_red_stack"}])
check("retouche qui ne change rien : rien d'écrit, dit", not err and r["ecrit"] == 0 and "note" in r, r)
check("retouche : l'original gardé n'est pas remplacé par une seconde retouche", open(avant_f, "rb").read() == octets0)
app = r"base\weapons\melee\katana\w_katana_appearances.app"
j, err = srv.call("wk_json", ressource=app, ou="base", dans="essai/app", chemin="Data.RootChunk.appearances.0.Data.name.$value")
fapp = j["fichier"] if not err else ""
napp = len(json.load(open(j["json"], encoding="utf-8"))["Data"]["RootChunk"]["appearances"]) if not err else 0
r, err = srv.call("wk_retouche", fichier=fapp, operations=[
    {"op": "copie", "chemin": "Data.RootChunk.appearances.0"},
    {"op": "fixe", "chemin": f"Data.RootChunk.appearances.{napp}.Data.name.$value", "valeur": "banc_copie"}])
check("retouche d'un .app du jeu : apparence doublée, poignées renumérotées, relu identique",
      not err and r["ecrit"] == 1 and r["operations"][0]["renumerotes"]["HandleId"] >= 1 and r["relu"].startswith("identical"), r)
j, err = srv.call("wk_json", fichier=fapp, chemin=f"Data.RootChunk.appearances.{napp}.Data.name.$value")
check("retouche du .app relue : l'apparence de plus porte son nom", not err and j["texte"] == '"banc_copie"', j)

print("6. importer, packer, construire")
if tex:
    r, err = srv.call("wk_importe", source="essai/export/raw", dans="essai/import")
    xbm = os.path.join(ATELIER, "essai", "import", *tex["ressource"].split("\\"))
    check("importe : le .png exporté redevient un .xbm, arborescence gardée", not err and r["ecrit"] == 1 and os.path.isfile(xbm), r)
r, err = srv.call("wk_importe", source=ATELIER, plafond=1)
check("importe : au-dessus du plafond rien n'est écrit", not err and r["ecrit"] == 0 and "ceiling 1" in r["refuse"], r)
r, err = srv.call("wk_importe", source=MODS)
check("importe refusé : source hors de l'atelier", err and "outside the workshop" in r, r)
for nom, args in (("l'atelier entier", {"dossier": ATELIER}), ("dossier hors de l'atelier", {"dossier": MODS}),
                  ("sortie dans le dossier packé", {"dossier": "essai/hash", "dans": "essai/hash/sortie"}),
                  ("nom à barre oblique", {"dossier": "essai/hash", "nom": "a/b"}), ("dossier absent", {"dossier": "essai/pas_la"})):
    r, err = srv.call("wk_pack", **args)
    check(f"pack refusé : {nom}", err and not os.path.exists(os.path.join(ATELIER, "packs")), r)
os.makedirs(os.path.join(ATELIER, "essai", "textes"))
open(os.path.join(ATELIER, "essai", "textes", "lisezmoi.txt"), "w").write("rien à packer")
r, err = srv.call("wk_pack", dossier="essai/textes")
check("pack refusé : aucun fichier que la CLI packe, pas d'archive laissée", err and "Empty archive" in r and not os.listdir(os.path.join(ATELIER, "packs")), r)
r, err = srv.call("wk_pack", dossier="essai/hash", nom="Banc Red Stack", zip=True)
arc = os.path.join(ATELIER, "packs", "Banc Red Stack.archive")
check("pack : archive nommée, relue (une ressource), le .json laissé de côté et dit",
      not err and r["archive"] == arc and r["ressources"] == [cible] and any(x.endswith(".json") for x in r["laisses_de_cote"]), r)
check("pack : zip à la forme d'un mod", not err and zipfile.ZipFile(r["zip"]).namelist() == ["archive/pc/mod/Banc Red Stack.archive"], r)
r, err = srv.call("wk_extrait", archive=arc, motif="*item_icons.inkatlas", dans="essai/retour")
retour = os.path.join(ATELIER, "essai", "retour", *cible.split("\\"))
check("ALLER-RETOUR : la ressource ressortie de l'archive packée est le fichier retouché, octet pour octet",
      not err and r["ecrit"] == 1 and open(retour, "rb").read() == open(atlas, "rb").read() != octets0, r)
r, err = srv.call("wk_build", projet="projets/Essai")
check("build refusé : projet absent", err and "cree" in r, r)
r, err = srv.call("wk_build", projet=os.path.join(BASE, "projet_dehors"), cree=True)
check("build refusé : projet hors de l'atelier, rien créé", err and not os.path.exists(os.path.join(BASE, "projet_dehors")), r)
r, err = srv.call("wk_build", projet="projets/Essai", cree=True, nom="Banc & Essai")
P = os.path.join(ATELIER, "projets", "Essai")
check("build : squelette d'un projet neuf, rien à construire encore",
      not err and r["cree"] and r["ecrit"] == 0 and os.path.isfile(os.path.join(P, "Banc & Essai.cpmodproj"))
      and os.path.isdir(os.path.join(P, "source", "archive")), r)
os.makedirs(os.path.join(P, "source", "archive", os.path.dirname(cible)))
for suffixe in ("", ".json"):
    shutil.copy2(atlas + suffixe, os.path.join(P, "source", "archive", *cible.split("\\")) + suffixe)
os.makedirs(os.path.join(P, "source", "resources", "r6", "scripts", "Banc"))
open(os.path.join(P, "source", "resources", "r6", "scripts", "Banc", "banc.reds"), "w").write("// banc\n")
r, err = srv.call("wk_build", projet=P, zip=True)
noms = sorted(zipfile.ZipFile(r["zip"]).namelist()) if not err and r.get("zip") else []
check("build : packed à la forme du jeu (une archive, le script posé tel quel), zippé",
      not err and r["ecrit"] == 2 and len(noms) == 2 and noms[0].startswith("archive/pc/mod/") and noms[0].endswith(".archive")
      and noms[1] == "r6/scripts/Banc/banc.reds", (r, noms))
l, err2 = srv.call("wk_liste", archive=os.path.join(P, "packed", *noms[0].split("/"))) if noms else ({}, True)
check("build : le JSON de travail n'est pas dans l'archive, et il est remis à sa place dans le projet",
      not err and not err2 and r.get("json_de_travail_ecartes") == 1 and l["archives"][0]["ressources"] == [cible]
      and os.path.isfile(os.path.join(P, "source", "archive", *cible.split("\\")) + ".json"), (r, l))
tmp = os.path.join(ATELIER, "_tmp")
check("aucun dossier de travail laissé dans l'atelier", not os.path.isdir(tmp) or not os.listdir(tmp))

print("7. rien d'autre n'a bougé")
check("LES ARCHIVES DES MODS DU JEU N'ONT PAS BOUGÉ", photo(MODS) == avant)
check("rien d'écrit à côté de l'atelier", sorted(os.listdir(DONNEES)) == ["config.json"] and not os.listdir(vide))
check("le serveur s'arrête à la fermeture de l'entrée", srv.ferme() == 0)
print(f"\n{'VERT' if not fails else 'ROUGE'} : {len(fails)} échec(s)" + "".join(f"\n  - {f}" for f in fails))
sys.exit(1 if fails else 0)
