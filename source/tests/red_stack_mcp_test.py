"""Banc de red_stack_mcp.py : parle JSON-RPC au serveur sur le dépôt et le jeu synthétiques de red_stack_test.py.

  python -I red_stack_test.py && python -I red_stack_mcp_test.py
Le premier banc laisse sous C:\\__DEV\\cyberpunk\\red_stack\\ un dépôt, un jeu, un magasin et le profil « t ». Celui-ci
vérifie le protocole, chaque outil, et que le serveur n'écrit jamais le jeu : il dépose une demande, que ce banc
applique à la place de l'extension par `applique --go --si-plan`.
"""
import json, os, subprocess, sys

BASE = r"C:\__DEV\cyberpunk\red_stack"
DEPOT, JEU, STORE, DONNEES = (os.path.join(BASE, x) for x in ("depot", "jeu", "magasin", "donnees"))
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extension", "moteur")
ARGS = ["--depot", DEPOT, "--jeu", JEU, "--magasin", STORE, "--donnees", DONNEES]
fails, n = [], 0


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  KO   ") + label + (f"  {detail}" if not cond else ""))
    if not cond:
        fails.append(label)


os.environ["RED_STACK_NEXUS_URL"] = "http://127.0.0.1:9"      # Nexus injoignable : le banc ne sort jamais sur le réseau
srv = subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "red_stack_mcp.py"), *ARGS], stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE, text=True, encoding="utf-8")


def rpc(method, params=None, notif=False):
    global n
    msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not notif:
        n += 1
        msg["id"] = n
    srv.stdin.write(json.dumps(msg) + "\n")
    srv.stdin.flush()
    return None if notif else json.loads(srv.stdout.readline())


def call(name, **args):
    r = rpc("tools/call", {"name": name, "arguments": args})["result"]
    t = r["content"][0]["text"]
    return (t if r["isError"] else json.loads(t)), r["isError"]


def snapshot():
    out = {}
    for d, _, fs in os.walk(JEU):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, JEU)] = (os.path.getsize(p), os.stat(p).st_mtime_ns)
    return out


if not os.path.isfile(os.path.join(DONNEES, "profils", "t.json")):
    sys.exit("Lancer red_stack_test.py d'abord (profil « t » absent).")
print("1. protocole")
r = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "banc", "version": "0"}})
check("initialize rend la version demandée et le nom du serveur",
      r["result"]["protocolVersion"] == "2025-06-18" and r["result"]["serverInfo"]["name"] == "red-stack", r)
rpc("notifications/initialized", notif=True)
tools = rpc("tools/list")["result"]["tools"]
check("tools/list : 27 outils, tous avec un schéma objet",
      len(tools) == 27 and all(t["inputSchema"]["type"] == "object" for t in tools), len(tools))
check("ping répond", rpc("ping")["result"] == {})
check("méthode inconnue = erreur -32601", rpc("nimporte")["error"]["code"] == -32601)
r = rpc("tools/call", {"name": "red_stack_inexistant", "arguments": {}})
check("outil inconnu = erreur JSON-RPC, le serveur survit", r["error"]["code"] == -32601 and rpc("ping")["result"] == {})

print("2. lecture")
before = snapshot()
e, err = call("red_stack_etat", profil="t")
check("etat : comptes et piles", not err and e["piles"] and sum(e["compte"].values()) > 5, e)
e, err = call("red_stack_etat", profil="t", section="6_Autre")
check("etat filtré par pile", not err and e["mods"] and all(m["cle"].startswith("6_Autre/") for m in e["mods"]), e)
world = next(m["cle"] for m in e["mods"] if "Monde-3001" in m["cle"])
d, err = call("red_stack_detail", profil="t", mod="Monde-3001")
N = sum(1 for x in d["entrees"] if x["pris"]) if not err else 0
check("detail : entrées avec destination et état, des fichiers pris", not err and N >= 2 and all(x["dest"] for x in d["entrees"]), d)
f, err = call("red_stack_fichier", nom="w1.archive")
check("fichier : le propriétaire de w1.archive", not err and f["total"] == 1 and f["fichiers"][0]["zip"] == world, f)
p, err = call("red_stack_profils")
check("profils : « t » listé", not err and any(x["nom"] == "t" for x in p["profils"]), p)
c, err = call("red_stack_config")
check("config : dossier des données du banc", not err and c["donnees"] == DONNEES, c)
pl, err = call("red_stack_plan", profil="t")
check("plan de départ vide, empreinte rendue", not err and len(pl["empreinte"]) == 16
      and not any(pl["compte"][k] for k in ("pose", "remplace", "retire")), pl)
r, err = call("red_stack_demande_application", profil="t")
check("demande sur un plan vide : aucune demande déposée", not err and r["demande"] is None, r)

print("3. le profil change, le jeu non")
call("red_stack_profils", nom="mcp", source="t")
p, err = call("red_stack_profils")
check("profil « mcp » créé par copie", any(x["nom"] == "mcp" for x in p["profils"]), p)
r, err = call("red_stack_bascule", profil="mcp", mod="Monde-3001", valeur="off")
check("bascule off acceptée", not err and r["ok"], r)
r, err = call("red_stack_bascule", profil="mcp", valeur="off")
check("bascule sans cible = erreur d'outil, pas de plantage", err and "mod" in r, r)
pl, err = call("red_stack_plan", profil="mcp")
check("plan : les fichiers du mod à retirer", not err and pl["compte"]["retire"] == N and pl["par_zip"][world]["retire"] == N, pl)
r, err = call("red_stack_demande_application", profil="mcp", motif="essai du banc")
check("demande déposée, en attente", not err and r["etat"] == "attente" and r["demande"], r)
s, err = call("red_stack_suivi_demande")
check("suivi : même demande, même empreinte", not err and s["id"] == r["demande"] and s["empreinte"] == pl["empreinte"], s)
check("LE JEU N'A PAS BOUGÉ (aucun fichier créé, retiré ni réécrit par le serveur)", snapshot() == before)

print("4. l'application reste hors du serveur (ce que fait l'extension)")
tool = [sys.executable, "-I", os.path.join(HERE, "red_stack.py"), "applique", "--profil", "mcp", "--go", "--vrai-jeu", "--json", *ARGS]
bad = subprocess.run(tool + ["--si-plan", "0" * 16], capture_output=True, text=True, encoding="utf-8")
check("empreinte fausse : refus, rien d'écrit", bad.returncode != 0 and "plan a changé" in bad.stderr and snapshot() == before, bad.stderr)
good = subprocess.run(tool + ["--si-plan", s["empreinte"]], capture_output=True, text=True, encoding="utf-8")
check("bonne empreinte : appliqué", good.returncode == 0 and json.loads(good.stdout)["compte"]["retire"] == N, good.stdout + good.stderr)
check("w1.archive sorti du jeu", not os.path.isfile(os.path.join(JEU, "archive", "pc", "mod", "w1.archive")))
pl, err = call("red_stack_plan", profil="mcp")
check("plan relu : plus rien à faire", not any(pl["compte"][k] for k in ("pose", "remplace", "retire")), pl)

print("5. retour à l'état de départ")
call("red_stack_bascule", profil="mcp", mod="Monde-3001", valeur="on")
pl, err = call("red_stack_plan", profil="mcp")
back = subprocess.run(tool + ["--si-plan", pl["empreinte"]], capture_output=True, text=True, encoding="utf-8")
check("mod remis : ses fichiers reposés", back.returncode == 0 and pl["compte"]["pose"] == N, back.stdout + back.stderr)
j, err = call("red_stack_journal", geste="applique", limite=5)
check("journal : les applications de ce banc, la plus récente d'abord, avec le mod reposé",
      not err and j["entrees"] and j["entrees"][0]["geste"] == "applique" and any(m["cle"] == world and m["fait"] == "posé" for m in j["entrees"][0]["mods"])
      and any(m["cle"] == world and m["fait"] == "retiré" for e in j["entrees"] for m in e["mods"]), j)
g, err = call("red_stack_magasin", profil="mcp")
check("magasin : poids réel, liens et arbres sans mod rendus, rien d'écrit",
      not err and "reel" in g and "explorateur" in g and isinstance(g["sans_mod"], list) and "lies" in g["jeu"], g if err else str(g)[:300])
sv, err = call("red_stack_sauvegardes")
check("sauvegardes des réglages : la liste (lecture seule)", not err and isinstance(sv["sauvegardes"], list) and sv["dossier"], sv)
pq, err = call("red_stack_prerequis", profil="mcp")
check("prérequis : les cadres et les mods actifs sans un prérequis, lus sans appeler Nexus",
      not err and any(c["cadre"] == "cet" for c in pq["cadres"]) and isinstance(pq["mods"], list) and pq["erreur"] is None and pq["mods_total"] >= len(pq["mods"]), pq)
pq, err = call("red_stack_prerequis", profil="mcp", mod=world)
check("prérequis d'un mod : sa liste et qui l'exige", not err and isinstance(pq["mod"]["requis"], list) and "requis_par_total" in pq["mod"], pq)
mj, err = call("red_stack_mises_a_jour")
check("mises à jour : Nexus injoignable (adresse du banc), dit sans planter ; aucune clé ni marque interne rendue",
      not err and "unreachable" in (mj["erreur"] or "") and mj["total"] > 3 and "cle_api" not in mj and all("qui" not in r for r in mj["lignes"]), mj)
print("6. gestes de la page ajoutés au serveur (0.16.0)")
before = snapshot()
depot_avant = sorted((os.path.relpath(os.path.join(d, f), DEPOT), os.path.getsize(os.path.join(d, f))) for d, _, fs in os.walk(DEPOT) for f in fs)
e, err = call("red_stack_etat", profil="mcp", nature="archive")
check("etat filtré par nature : des zips qui posent une archive, la nature rendue",
      not err and e["mods"] and all("archive" in m["natures"] for m in e["mods"]), e)
e2, err = call("red_stack_etat", profil="mcp", nature="nature_qui_n_existe_pas")
check("etat, nature inconnue : aucune ligne, pas d'erreur", not err and e2["lignes"] == 0, e2)
r, err = call("red_stack_priorite", profil="mcp", gagnant="Monde-3001", fichier="archive/pc/mod/w1.archive")
check("priorite par fichier : notée au profil", not err, r)
prof = json.load(open(os.path.join(DONNEES, "profils", "mcp.json"), encoding="utf-8"))
check("priorite par fichier : dans le profil, sous le chemin en minuscules",
      prof.get("priorites_fichiers", {}).get("archive/pc/mod/w1.archive") == world, prof.get("priorites_fichiers"))
r, err = call("red_stack_priorite", profil="mcp", gagnant="Monde-3001", fichier="archive/pc/mod/w1.archive", annule=True)
prof = json.load(open(os.path.join(DONNEES, "profils", "mcp.json"), encoding="utf-8"))
check("priorite par fichier annulée : sortie du profil", not err and not prof.get("priorites_fichiers"), prof.get("priorites_fichiers"))
r, err = call("red_stack_priorite", profil="mcp", gagnant="Monde-3001")
check("priorite sans perdant ni fichier = erreur d'outil", err and "perdant" in r, r)
r, err = call("red_stack_option", profil="mcp", mod="Monde-3001", valeur="on", mien=True)
check("option mien sans entree = erreur d'outil", err and "entree" in r, r)
c, err = call("red_stack_conflits", profil="mcp", ressources=True)
check("conflits par ressource : comptes et liste, chaque ligne dit où le jeu la prend",
      not err and isinstance(c["ressources"], list) and c["trouvees"] <= c["en_conflit"] and all(x["prise_dans"] for x in c["ressources"]), c)
c2, err = call("red_stack_conflits", profil="mcp", ressources=True, texte="texte_introuvable_xyz")
check("conflits par ressource, filtre sans résultat : liste vide", not err and c2["trouvees"] == 0, c2)
c3, err = call("red_stack_conflits", profil="mcp", ressources=True, mod="Monde-3001")
check("conflits : ressources + mod = erreur d'outil", err and "texte" in c3, c3)
ar, err = call("red_stack_arrivages")
check("arrivages : la liste et les comptes, lecture seule", not err and isinstance(ar["arrivages"], list) and ar["total"] == len(ar["arrivages"]) and "compte" in ar, ar)
ct, err = call("red_stack_contenu", cle=world)
check("contenu : l'aperçu d'un zip (état, renommages, gardés), sans la liste brute des fichiers",
      not err and ct["cle"] == world and "etat" in ct and isinstance(ct["ops"], list) and "fichiers" not in ct, ct)
ct, err = call("red_stack_contenu", cle="6_Autre/inconnu.zip")
check("contenu, clé inconnue = erreur d'outil", err and "unknown key" in ct, ct)
conf_p = os.path.join(DONNEES, "config.json")
ign = lambda: json.load(open(conf_p, encoding="utf-8")).get("maj_ignores", [])
ign0 = ign()
r, err = call("red_stack_mises_a_jour", ignore="on", cle=world)
check("mises à jour : ignorer un mod, noté dans la configuration", not err and r["ignore"] is True and len(ign()) == len(ign0) + 1, r)
r, err = call("red_stack_mises_a_jour", ignore="off", cle=world)
check("mises à jour : ne plus l'ignorer, configuration rendue telle quelle", not err and r["ignore"] is False and ign() == ign0, r)
r, err = call("red_stack_mises_a_jour", ignore="on")
check("mises à jour : ignore sans cle = erreur d'outil", err and "cle" in r, r)
j, err = call("red_stack_journal", geste="maj", limite=3)
check("journal : le geste « maj » est accepté", not err and isinstance(j["entrees"], list), j)
check("LE JEU N'A PAS BOUGÉ pendant ces lectures", snapshot() == before)
check("LE DÉPÔT N'A PAS BOUGÉ (aucun zip créé, renommé ni récrit par le serveur)",
      depot_avant == sorted((os.path.relpath(os.path.join(d, f), DEPOT), os.path.getsize(os.path.join(d, f))) for d, _, fs in os.walk(DEPOT) for f in fs))
srv.stdin.close()
check("le serveur s'arrête à la fermeture de l'entrée", srv.wait(timeout=10) == 0)
os.remove(os.path.join(DONNEES, "profils", "mcp.json"))
print(f"\n{'VERT' if not fails else 'ROUGE'} : {len(fails)} échec(s)" + "".join(f"\n  - {f}" for f in fails))
sys.exit(1 if fails else 0)
