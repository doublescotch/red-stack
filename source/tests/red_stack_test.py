"""Banc de red_stack.py : dépôt et jeu synthétiques sous C:\\__DEV\\cyberpunk\\red_stack\\ (recréés à chaque passe).

  python -I red_stack_test.py
Couvre : adoption d'un jeu déjà posé (plan vide), pose partielle, pack à piocher, écrasement entre deux mods, coupure et
remise d'un mod puis d'une section, fichier partagé, fichier modifié en jeu, fichier créé par un mod, mise à jour d'un zip.
"""
import json, os, shutil, subprocess, sys, zipfile

BASE = r"C:\__DEV\cyberpunk\red_stack"
DEPOT, JEU, DONNEES = os.path.join(BASE, "depot"), os.path.join(BASE, "jeu"), os.path.join(BASE, "donnees")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extension", "moteur", "red_stack.py")
fails = []
if len(sys.argv) < 2:                       # sans argument : les deux modes l'un après l'autre
    codes = [subprocess.run([sys.executable, "-I", __file__, m]).returncode for m in ("direct", "magasin")]
    sys.exit(max(codes))
MAGASIN = sys.argv[1] == "magasin"
STORE = os.path.join(BASE, "magasin")
MODE = ["--magasin", STORE] if MAGASIN else ["--sans-magasin"]
print(f"\n===== mode {sys.argv[1]} =====")


def mkzip(rel, files):                      # contenu : texte, ou octets (archives RDAR de la section 12)
    p = os.path.join(DEPOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)


def put(rel, data):
    p = os.path.join(JEU, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", newline="").write(data)


def get(rel):
    p = os.path.join(JEU, rel.replace("/", os.sep))
    return open(p, newline="").read() if os.path.isfile(p) else None


def rs(*args, ok=True):
    r = subprocess.run([sys.executable, "-I", TOOL, *args, "--depot", DEPOT, "--jeu", JEU, "--donnees", DONNEES, "--json", *MODE],
                       capture_output=True, text=True, encoding="utf-8")
    if ok and r.returncode:
        sys.exit(f"red_stack {args} : {r.stdout}\n{r.stderr}")
    try:
        return json.loads(r.stdout)
    except ValueError:
        return r.stdout + r.stderr


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  KO   ") + label + (f"  {detail}" if not cond else ""))
    if not cond:
        fails.append(label)


def plan_counts():
    return rs("plan", "--profil", "t")["compte"]


shutil.rmtree(BASE, ignore_errors=True)
os.makedirs(DEPOT)
A = "archive/pc/mod/"
mkzip("1_Core/Alpha-1001-1-0-1700000001.zip", {A + "alpha.archive": "alpha1", "r6/scripts/alpha/a.reds": "a1",
                                             "bin/x64/plugins/cyber_engine_tweaks/mods/alpha/config.json": "defaut",
                                             "readme.txt": "doc"})
mkzip("1_Core/Romance-2001-3-0-1700000002.zip", {A + "romance.archive": "r1", A + "cleanup.archive": "vieux"})
mkzip("1_Core/Romance Next Chapter-2002-1-0-1700000003.zip", {A + "next.archive": "n1", A + "cleanup.archive": "neuf"})
mkzip("3_Bodies/Body Pack.zip", {"Common/" + A + "common.archive": "c", "UV_Solo/" + A + "body.archive": "solo",
                                 "VTK_Angel/" + A + "body.archive": "angel", "Tattoos/t1.archive": "t1",
                                 "Tattoos/t2.archive": "t2", "Common/" + A + "__RAM/old.archive": "x", "notes.png": "p"})
mkzip("5_World/World-3001-1-0-1700000004.zip", {A + "w1.archive": "w1", A + "w2.archive": "w2", A + "w3.archive": "w3"})
mkzip("5_World/Shared A-3002-1-0-1700000005.zip", {A + "sa.archive": "sa", "r6/tweaks/shared.yaml": "meme"})
mkzip("5_World/Shared B-3003-1-0-1700000006.zip", {A + "sb.archive": "sb", "r6/tweaks/shared.yaml": "meme"})
mkzip("5_World/__RAM/Parked-3004-1-0-1700000007.zip", {A + "parked.archive": "pk"})
mkzip("5_World/Jamais-3005-1-0-1700000008.zip", {A + "jamais.archive": "j"})

# le jeu tel qu'il aurait été posé à la main
put(A + "alpha.archive", "alpha1"); put("r6/scripts/alpha/a.reds", "a1")
put("bin/x64/plugins/cyber_engine_tweaks/mods/alpha/config.json", "REGLE PAR LUI")       # livré puis modifié en jeu
put("bin/x64/plugins/cyber_engine_tweaks/mods/alpha/cree_par_le_mod.json", "etat")       # créé par le mod
put(A + "romance.archive", "r1"); put(A + "next.archive", "n1"); put(A + "cleanup.archive", "neuf")  # Next écrase
put(A + "common.archive", "c"); put(A + "body.archive", "angel"); put(A + "t2.archive", "t2")     # pack pioché
put(A + "w1.archive", "w1"); put(A + "w3.archive", "w3")                                           # pose partielle
put(A + "sa.archive", "sa"); put(A + "sb.archive", "sb"); put("r6/tweaks/shared.yaml", "meme")
put("bin/x64/socle.dll", "socle")

print("1. adoption")
ad = rs("adopte", "--profil", "t")
rep = ad["rapport"]
check("pose partielle reconnue (World 2/3)", rep["5_World/World-3001-1-0-1700000004.zip"]["etat"] == "partiel")
check("zip jamais posé = absent", rep["5_World/Jamais-3005-1-0-1700000008.zip"]["etat"] == "absent")
check("priorité observée Next > Romance", ad["priorites"] == [["1_Core/Romance Next Chapter-2002-1-0-1700000003.zip",
                                                               "1_Core/Romance-2001-3-0-1700000002.zip"]], str(ad["priorites"]))
prof = json.load(open(os.path.join(DONNEES, "profils", "t.json"), encoding="utf-8"))
sel = prof["mods"]["3_Bodies/Body Pack.zip"].get("sel")
check("pack à piocher : Common + VTK_Angel + un tatouage", sel == {"Common": "*", "VTK_Angel": "*", "Tattoos": ["Tattoos/t2.archive"]}, str(sel))
c = plan_counts()
check("plan vide après adoption", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == c["inconnu"] == 0, str(c))
check("réglage modifié en jeu signalé, gardé", c["garde_modifie"] == 1, str(c))

if MAGASIN:
    print("1 bis. passage au magasin")
    check("copies du jeu à changer en liens", c["lie"] > 0, str(c))
    rs("applique", "--profil", "t", "--go")
    g = os.path.join(JEU, "archive", "pc", "mod")
    s = os.path.join(STORE, "5_World", "World-3001-1-0-1700000004")
    check("un arbre par mod, contenu du zip entier", os.path.isfile(os.path.join(s, "archive", "pc", "mod", "w2.archive")))
    check("archive du jeu = lien vers l'arbre du mod", os.path.samefile(os.path.join(g, "w1.archive"), os.path.join(s, "archive", "pc", "mod", "w1.archive")))
    check("le perdant d'un écrasement reste dans son arbre",
          open(os.path.join(STORE, "1_Core", "Romance-2001-3-0-1700000002", "archive", "pc", "mod", "cleanup.archive")).read() == "vieux"
          and get(A + "cleanup.archive") == "neuf")
    check("réglage modifié ni lié ni écrasé", get("bin/x64/plugins/cyber_engine_tweaks/mods/alpha/config.json") == "REGLE PAR LUI")
    check("plus rien à lier", plan_counts()["lie"] == 0)
    st = lambda *p: os.path.join(STORE, *p)
    check("petit fichier (script) lié aussi", os.path.samefile(st("1_Core", "Alpha-1001-1-0-1700000001", "r6", "scripts", "alpha", "a.reds"),
                                                               os.path.join(JEU, "r6", "scripts", "alpha", "a.reds")))
    check("réglage par défaut (config.json) copié, pas lié",
          open(st("1_Core", "Alpha-1001-1-0-1700000001", "bin", "x64", "plugins", "cyber_engine_tweaks", "mods", "alpha", "config.json")).read() == "defaut")

    print("1 ter. retouche dans l'arbre d'un mod")
    w1 = st("5_World", "World-3001-1-0-1700000004", "archive", "pc", "mod", "w1.archive")
    open(w1, "w", newline="").write("w1-essai")                      # édition sur place : le jeu la voit tout de suite
    check("édition sur place visible dans le jeu", get(A + "w1.archive") == "w1-essai")
    c = plan_counts()
    check("retouche signalée, rien à refaire", c["retouche"] == 1 and c["pose"] == c["remplace"] == c["retire"] == 0, str(c))
    rs("bascule", "off", "--profil", "t", "--mod", "World-3001"); rs("applique", "--profil", "t", "--go")
    check("mod coupé : retiré du jeu, retouche gardée dans l'arbre", get(A + "w1.archive") is None and open(w1).read() == "w1-essai")
    rs("bascule", "on", "--profil", "t", "--mod", "World-3001"); rs("applique", "--profil", "t", "--go")
    check("mod remis avec sa retouche", get(A + "w1.archive") == "w1-essai" and get(A + "w2.archive") is None)
    w3 = st("5_World", "World-3001-1-0-1700000004", "archive", "pc", "mod", "w3.archive")
    open(w3 + ".tmp", "w", newline="").write("w3-essai"); os.replace(w3 + ".tmp", w3)   # éditeur qui enregistre par renommage
    check("enregistrement par renommage : le jeu a encore l'ancien", get(A + "w3.archive") == "w3")
    rs("applique", "--profil", "t", "--go")
    check("applique repose la retouche", get(A + "w3.archive") == "w3-essai")
    r = rs("retouche", "--profil", "t", "--mod", "World-3001", "--annule")
    check("deux retouches annulées", len(r["retouches"]) == 2, str(r)[:200])
    rs("applique", "--profil", "t", "--go")
    check("le jeu retrouve les fichiers du zip", get(A + "w1.archive") == "w1" and get(A + "w3.archive") == "w3" and plan_counts()["retouche"] == 0)

    print("1 quater. réglage non détecté, ajouté à la main")
    put(A + "romance.archive", "r1-regle")                           # un mod réécrit SUR PLACE un fichier lié
    ro = st("1_Core", "Romance-2001-3-0-1700000002", "archive", "pc", "mod", "romance.archive")
    check("écrit à travers le lien : l'arbre est touché, vu comme retouche", open(ro).read() == "r1-regle" and plan_counts()["retouche"] == 1)
    rs("reglage", "--ajoute", "archive/pc/mod/romance.archive")
    check("devenu réglage : à délier", plan_counts()["delie"] == 1)
    rs("applique", "--profil", "t", "--go")
    check("délié : le jeu garde sa valeur, l'arbre reprend le zip", get(A + "romance.archive") == "r1-regle" and open(ro).read() == "r1"
          and not os.path.samefile(ro, os.path.join(JEU, "archive", "pc", "mod", "romance.archive")))
    c = plan_counts()
    check("ensuite : gardé comme modifié en jeu, plus rien à faire", c["delie"] == c["retouche"] == c["remplace"] == 0 and c["garde_modifie"] == 2, str(c))
    rs("bascule", "off", "--profil", "t", "--mod", "Romance-2001"); rs("applique", "--profil", "t", "--go")
    check("mod coupé : son réglage modifié reste dans le jeu", get(A + "romance.archive") == "r1-regle")
    rs("bascule", "on", "--profil", "t", "--mod", "Romance-2001"); rs("applique", "--profil", "t", "--go")
    check("mod remis : réglage intact", get(A + "romance.archive") == "r1-regle")

print("2. couper puis remettre un mod")
rs("bascule", "off", "--profil", "t", "--mod", "Alpha")
r = rs("applique", "--profil", "t", "--go")
check("archive et script retirés", get(A + "alpha.archive") is None and get("r6/scripts/alpha/a.reds") is None)
check("réglage modifié gardé", get("bin/x64/plugins/cyber_engine_tweaks/mods/alpha/config.json") == "REGLE PAR LUI")
check("fichier créé par le mod gardé", get("bin/x64/plugins/cyber_engine_tweaks/mods/alpha/cree_par_le_mod.json") == "etat")
rs("bascule", "on", "--profil", "t", "--mod", "Alpha")
rs("applique", "--profil", "t", "--go")
check("mod remis", get(A + "alpha.archive") == "alpha1" and get("r6/scripts/alpha/a.reds") == "a1")
check("réglage toujours le sien", get("bin/x64/plugins/cyber_engine_tweaks/mods/alpha/config.json") == "REGLE PAR LUI")
check("texte de racine jamais posé", get("readme.txt") is None)

print("3. écrasement")
rs("bascule", "off", "--profil", "t", "--mod", "Next Chapter")
rs("applique", "--profil", "t", "--go")
check("Next coupé : le fichier de Romance revient", get(A + "cleanup.archive") == "vieux" and get(A + "next.archive") is None)
rs("bascule", "on", "--profil", "t", "--mod", "Next Chapter")
rs("applique", "--profil", "t", "--go")
check("Next remis : il écrase à nouveau", get(A + "cleanup.archive") == "neuf")

c = rs("plan", "--profil", "t")
check("conflit tranché visible au plan", [(r["zip"][:25], [p[:14] for p in r["perdants"]]) for r in c["tranche"]]
      == [("1_Core/Romance Next Chapt", ["1_Core/Romance"])], str(c["tranche"]))
rs("priorite", "--profil", "t", "--gagnant", "Next Chapter", "--perdant", "Romance-2001", "--annule")
c = rs("plan", "--profil", "t")
check("priorité oubliée : le conflit revient, rien à écrire", c["compte"]["conflit"] == 1 and not c["tranche"]
      and c["compte"]["remplace"] == 0, str(c["compte"]))
rs("priorite", "--profil", "t", "--gagnant", "Next Chapter", "--perdant", "Romance-2001")
check("priorité remise : plus de conflit", plan_counts()["conflit"] == 0)

rs("priorite", "--profil", "t", "--gagnant", "Romance-2001", "--fichier", A + "cleanup.archive")
c = rs("plan", "--profil", "t")
check("priorité d'un seul fichier : passe avant la règle entre mods", c["compte"]["remplace"] == 1 and c["tranche"][0]["par_fichier"]
      and c["tranche"][0]["zip"].startswith("1_Core/Romance-2001"), str(c["tranche"]))
rs("priorite", "--profil", "t", "--gagnant", "Romance-2001", "--fichier", A + "cleanup.archive", "--annule")
c = rs("plan", "--profil", "t")
check("priorité du fichier oubliée : la règle entre mods reprend", c["compte"]["remplace"] == 0 and not c["tranche"][0]["par_fichier"], str(c["tranche"]))

print("4. fichier partagé")
rs("bascule", "off", "--profil", "t", "--mod", "Shared A")
rs("applique", "--profil", "t", "--go")
check("partagé gardé tant que B est actif", get("r6/tweaks/shared.yaml") == "meme" and get(A + "sa.archive") is None)
rs("bascule", "off", "--profil", "t", "--mod", "Shared B")
rs("applique", "--profil", "t", "--go")
check("partagé retiré avec le dernier", get("r6/tweaks/shared.yaml") is None)

print("5. section entière")
rs("bascule", "off", "--profil", "t", "--section", "5_World")
rs("applique", "--profil", "t", "--go")
check("section coupée", get(A + "w1.archive") is None and get(A + "w3.archive") is None)
prof = json.load(open(os.path.join(DONNEES, "profils", "t.json"), encoding="utf-8"))
check("pile coupée : seul le mod alors actif est retenu", prof["mods"]["5_World/World-3001-1-0-1700000004.zip"].get("avant_pile")
      and not prof["mods"]["5_World/Shared A-3002-1-0-1700000005.zip"].get("avant_pile"))
rs("bascule", "on", "--profil", "t", "--section", "5_World")
c = plan_counts()
check("pile remise : seul ce mod revient, pas ceux coupés avant elle", c["pose"] == 2, str(c))
rs("bascule", "off", "--profil", "t", "--section", "5_World")
rs("bascule", "on", "--profil", "t", "--mod", "World-3001")
rs("applique", "--profil", "t", "--go")
check("pose partielle rendue telle quelle (w2 jamais posé)", get(A + "w1.archive") == "w1" and get(A + "w2.archive") is None)

print("6. pack à piocher")
rs("option", "off", "--profil", "t", "--mod", "Body Pack", "--nom", "VTK_Angel")
rs("option", "on", "--profil", "t", "--mod", "Body Pack", "--nom", "UV_Solo")
rs("applique", "--profil", "t", "--go")
check("option changée : corps Solo", get(A + "body.archive") == "solo" and get(A + "common.archive") == "c")
check("dossier __RAM du zip jamais posé", get(A + "old.archive") is None and get(A + "__RAM/old.archive") is None)
rs("option", "on", "--profil", "t", "--mod", "Body Pack", "--nom", "VTK_Angel")
c = plan_counts()
check("deux options sur le même fichier = conflit signalé, rien écrit", c["conflit"] == 1 and c["remplace"] == 0, str(c))
rs("option", "off", "--profil", "t", "--mod", "Body Pack", "--nom", "VTK_Angel")

print("6 bis. un fichier seul d'un pack")
psel = lambda: json.load(open(os.path.join(DONNEES, "profils", "t.json"), encoding="utf-8"))["mods"]["3_Bodies/Body Pack.zip"]["sel"]
rs("option", "on", "--profil", "t", "--mod", "Body Pack", "--entree", "Tattoos/t1.archive")
check("fichier ajouté : l'option redevient entière", psel().get("Tattoos") == "*", str(psel()))
rs("option", "off", "--profil", "t", "--mod", "Body Pack", "--entree", "Tattoos/t2.archive")
check("fichier laissé : l'option garde la liste du reste", psel().get("Tattoos") == ["Tattoos/t1.archive"], str(psel()))
rs("applique", "--profil", "t", "--go")
check("jeu : t1 posé, t2 retiré", get(A + "t1.archive") == "t1" and get(A + "t2.archive") is None)
rs("option", "off", "--profil", "t", "--mod", "Body Pack", "--entree", "Tattoos/t1.archive")
check("dernier fichier laissé : l'option sort de la sélection", "Tattoos" not in psel(), str(psel()))
rs("option", "off", "--profil", "t", "--mod", "Body Pack", "--entree", "Common/" + A + "common.archive")
rs("applique", "--profil", "t", "--go")
check("jeu : fichier d'une option entière laissé seul", get(A + "common.archive") is None and get(A + "body.archive") == "solo"
      and get(A + "t1.archive") is None)
r = rs("option", "on", "--profil", "t", "--mod", "Body Pack", "--entree", "notes.png", ok=False)
check("entrée jamais posable refusée", "Entrée inconnue" in str(r), str(r)[:200])
rs("option", "on", "--profil", "t", "--mod", "Body Pack", "--entree", "Common/" + A + "common.archive")
rs("option", "on", "--profil", "t", "--mod", "Body Pack", "--entree", "Tattoos/t2.archive")
rs("applique", "--profil", "t", "--go")
check("remis : common et t2 dans le jeu", get(A + "common.archive") == "c" and get(A + "t2.archive") == "t2")

print("7. mise à jour d'un zip")
if MAGASIN:                                 # une retouche en cours sur l'ancienne version
    open(os.path.join(STORE, "1_Core", "Alpha-1001-1-0-1700000001", "r6", "scripts", "alpha", "a.reds"), "w", newline="").write("a1-essai")
os.remove(os.path.join(DEPOT, "1_Core", "Alpha-1001-1-0-1700000001.zip"))
mkzip("1_Core/Alpha-1001-1-1-1700009999.zip", {A + "alpha.archive": "alpha2", "r6/scripts/alpha/b.reds": "b2",
                                             "bin/x64/plugins/cyber_engine_tweaks/mods/alpha/config.json": "defaut2"})
p = rs("plan", "--profil", "t")
check("le profil suit le nouveau zip", any(n[0] == "mise à jour" for n in p["notes"]), str(p["notes"]))
rs("applique", "--profil", "t", "--go")
check("nouvelle archive posée", get(A + "alpha.archive") == "alpha2")
check("fichier disparu de la nouvelle version retiré", get("r6/scripts/alpha/a.reds") is None and get("r6/scripts/alpha/b.reds") == "b2")
check("réglage modifié gardé à la mise à jour", get("bin/x64/plugins/cyber_engine_tweaks/mods/alpha/config.json") == "REGLE PAR LUI")
c = plan_counts()
check("plan stable après mise à jour", c["pose"] == c["remplace"] == c["retire"] == 0, str(c))

if MAGASIN:
    new = os.path.join(STORE, "1_Core", "Alpha-1001-1-1-1700009999", "archive", "pc", "mod", "alpha.archive")
    check("mise à jour : nouvel arbre, jeu lié dessus", os.path.samefile(new, os.path.join(JEU, "archive", "pc", "mod", "alpha.archive")))
    p = rs("purge", "--profil", "t", "--go")
    import glob
    saved = glob.glob(os.path.join(DONNEES, "sauvegardes", "_red_stack_*", "magasin", "1_Core", "Alpha-1001-1-0-1700000001", "r6", "scripts", "alpha", "a.reds"))
    check("purge : arbre de l'ancienne version supprimé, sa retouche copiée dans les sauvegardes",
          not os.path.isdir(os.path.join(STORE, "1_Core", "Alpha-1001-1-0-1700000001")) and saved and open(saved[0]).read() == "a1-essai", str(p)[:300])
    check("purge : les arbres des mods actifs restent", os.path.isdir(os.path.join(STORE, "5_World", "World-3001-1-0-1700000004")))
    check("aucun arbre du magasin abîmé (réglage par défaut intact)",
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(new)))), "bin", "x64", "plugins",
                            "cyber_engine_tweaks", "mods", "alpha", "config.json")).read() == "defaut2")

print("7 bis. zip renommé et changé de pile, contenu identique")
os.makedirs(os.path.join(DEPOT, "6_Autre"), exist_ok=True)
os.rename(os.path.join(DEPOT, "5_World", "World-3001-1-0-1700000004.zip"), os.path.join(DEPOT, "6_Autre", "Auteur - Monde-3001-1-0-1700000004.zip"))
p = rs("plan", "--profil", "t")
c = p["compte"]
check("renommage reconnu par le contenu", any(n[0] == "renommé" for n in p["notes"]), str(p["notes"]))
check("rien à refaire dans le jeu", c["pose"] == c["remplace"] == c["retire"] == c["lie"] == 0 and get(A + "w1.archive") == "w1", str(c))
if MAGASIN:
    check("l'arbre a suivi, le lien du jeu tient", os.path.samefile(os.path.join(STORE, "6_Autre", "Auteur - Monde-3001-1-0-1700000004", "archive", "pc", "mod", "w1.archive"),
                                                                 os.path.join(JEU, "archive", "pc", "mod", "w1.archive")))
rs("bascule", "off", "--profil", "t", "--mod", "Auteur - Monde"); rs("applique", "--profil", "t", "--go")
check("le mod renommé se coupe normalement", get(A + "w1.archive") is None)
rs("bascule", "on", "--profil", "t", "--mod", "Auteur - Monde"); rs("applique", "--profil", "t", "--go")

print("7 ter. zip remplacé par une version EDITED (autre nom, autre contenu)")
os.remove(os.path.join(DEPOT, "1_Core", "Romance Next Chapter-2002-1-0-1700000003.zip"))
mkzip("1_Core/Romance Next Chapter-2002-1-0-1700000003    EDITED 2.5.zip", {A + "next.archive": "n1-edite", A + "cleanup.archive": "neuf"})
p = rs("plan", "--profil", "t")
check("reconnu comme le même mod", any(n[0] in ("remplacé", "mise à jour") for n in p["notes"]), str(p["notes"]))
rs("applique", "--profil", "t", "--go")
check("contenu de la version EDITED posé, mod resté actif", get(A + "next.archive") == "n1-edite")
check("sa priorité sur Romance a suivi", get(A + "cleanup.archive") == "neuf" and plan_counts()["conflit"] == 0)

print("8. intouchés")
check("socle intact", get("bin/x64/socle.dll") == "socle")
check("zip parqué jamais posé", get(A + "parked.archive") is None)
e = rs("etat", "--profil", "t")
check("état lisible en JSON", isinstance(e, dict) and len(e["mods"]) == 9, str(e)[:200])

print("9. convention de dossiers réglée par l'utilisateur")
cp = os.path.join(DONNEES, "config.json")
conf = json.load(open(cp, encoding="utf-8")) if os.path.isfile(cp) else {}
conf["convention"] = {"piles": ["[0-9]*_*", "Extras"], "parques": ["__RAM*", "Garage"], "nouveaux": ["Arrivages"],
                      "retires": ["Corbeille"], "ignores_dans_zip": ["__*", "Bonus"]}
json.dump(conf, open(cp, "w", encoding="utf-8"))
mkzip("Extras/Hors Serie.zip", {A + "hs.archive": "hs", "Bonus/" + A + "bonus.archive": "b"})
mkzip("5_World/Garage/Au Garage.zip", {A + "garage.archive": "g"})
mkzip("5_World/Arrivages/Arrive.zip", {A + "arrive.archive": "a"})
mkzip("5_World/Corbeille/Jete.zip", {A + "jete.archive": "j"})
ix = {r["cle"]: r for r in rs("index")}
check("pile sans numéro reconnue", ix.get("Extras/Hors Serie.zip", {}).get("genre") == "actif", str(list(ix)))
check("dossier du zip ignoré par motif", ix.get("Extras/Hors Serie.zip", {}).get("options") == {"": 1})
check("parqué, nouveau, retiré à ses noms", [ix.get(k, {}).get("genre") for k in (
    "5_World/Garage/Au Garage.zip", "5_World/Arrivages/Arrive.zip", "5_World/Corbeille/Jete.zip")] == ["parqué", "nouveau", "retiré"])
check("l'ancien nom n'est plus un parking", "5_World/__NEW" not in str(list(ix)) and ix["5_World/__RAM/Parked-3004-1-0-1700000007.zip"]["genre"] == "parqué")
rs("bascule", "on", "--profil", "t", "--mod", "Hors Serie"); rs("applique", "--profil", "t", "--go")
check("pile ajoutée : posée, parkings jamais posés", get(A + "hs.archive") == "hs" and get(A + "bonus.archive") is None
      and get(A + "garage.archive") is None and get(A + "arrive.archive") is None and get(A + "jete.archive") is None)
st9 = {m["cle"]: m["etat"] for m in rs("etat", "--profil", "t")["mods"]}
check("états lisibles, avec leur dossier", st9["5_World/Garage/Au Garage.zip"] == "parqué (Garage)"
      and st9["5_World/Corbeille/Jete.zip"] == "retiré (Corbeille)" and st9["5_World/Arrivages/Arrive.zip"] == "nouveau (Arrivages)", str(st9))
r = rs("config")
check("config lisible en JSON", isinstance(r, dict) and r["convention"]["piles"] == ["[0-9]*_*", "Extras"], str(r)[:200])

print("10. hors Red Stack : dossier d'un installateur tiers")
T = "bin/x64/shaders-tiers/"
PZ = "5_World/Preset-4001-1-0-1700000010.zip"
conf = json.load(open(cp, encoding="utf-8"))            # `config` vient d'inscrire le jeu du banc comme « vrai jeu »
jeu_du_banc = conf.pop("jeu", None)
json.dump(conf, open(cp, "w", encoding="utf-8"))
mkzip(PZ, {"bin/x64/preset.ini": "p", T + "a.fx": "a", T + "b.fx": "b", T + "c.fx": "c"})
put("bin/x64/preset.ini", "p"); put(T + "a.fx", "a"); put(T + "b.fx", "b-installateur")   # l'installateur a posé a et b
rs("adopte", "--profil", "h")
rs("applique", "--profil", "h", "--go")
f10 = lambda: rs("fichier", "--nom", "shaders-tiers")["total"]
check("avant le motif : les fichiers de l'installateur sont pris pour ceux du mod", f10() == 2, str(f10()))
tree_a = os.path.join(STORE, "5_World", "Preset-4001-1-0-1700000010", "bin", "x64", "shaders-tiers", "a.fx")
game_a = os.path.join(JEU, "bin", "x64", "shaders-tiers", "a.fx")
if MAGASIN:
    check("avant le motif : lié à l'arbre du mod", os.path.samefile(tree_a, game_a))
r = rs("hors", "--ajoute", "bin/x64/shaders-tiers/*")
check("motif enregistré", r["hors"] == ["bin/x64/shaders-tiers/*"], str(r))
p = rs("plan", "--profil", "h")
c = p["compte"]
check("plan : rien à poser ni à retirer, les liens à rendre", c["pose"] == c["remplace"] == c["retire"] == 0
      and c["delie"] == (1 if MAGASIN else 0) and p["tiers"] == 2, str(c) + str(p["tiers"]))
row = next(m for m in rs("etat", "--profil", "h")["mods"] if m["cle"] == PZ)
check("sortis du compte du mod", row["posables"] == 2 and row["hors"] == 2 and row["fichiers_poses"] == 1, str(row))
d10 = {e["dest"]: e for e in rs("detail", "--profil", "h", "--mod", "Preset-4001")["entrees"]}
check("détail : dits hors Red Stack, pas pris", d10[T + "a.fx"]["etat"] == "hors Red Stack" and not d10[T + "a.fx"]["pris"]
      and d10[T + "b.fx"]["hors"] and d10[T + "c.fx"]["etat"] == "absent", str(d10)[:300])
if MAGASIN:
    rs("applique", "--profil", "h", "--go")
    check("rendu à l'installateur : délié, contenu gardé", get(T + "a.fx") == "a" and not os.path.samefile(tree_a, game_a))
    check("hors du registre", f10() == 0, str(f10()))
rs("option", "on", "--profil", "h", "--mod", "Preset-4001", "--entree", T + "c.fx")
check("fichier manquant pris : à poser", plan_h := rs("plan", "--profil", "h")["compte"]["pose"] == 1)
rs("applique", "--profil", "h", "--go")
check("manquant posé, celui de l'installateur intact", get(T + "c.fx") == "c" and get(T + "b.fx") == "b-installateur")
check("lui seul est au registre", f10() == 1, str(f10()))
if MAGASIN:
    check("posé en copie, jamais lié", not os.path.samefile(os.path.join(os.path.dirname(tree_a), "c.fx"), os.path.join(os.path.dirname(game_a), "c.fx")))
c = rs("plan", "--profil", "h")["compte"]
check("plan stable", c["pose"] == c["remplace"] == c["retire"] == c["delie"] == c["lie"] == 0, str(c))
rs("bascule", "off", "--profil", "h", "--mod", "Preset-4001"); rs("applique", "--profil", "h", "--go")
check("mod coupé : seul le fichier ajouté part, ceux de l'installateur restent",
      get(T + "c.fx") is None and get(T + "a.fx") == "a" and get(T + "b.fx") == "b-installateur" and get("bin/x64/preset.ini") is None)
rs("bascule", "on", "--profil", "h", "--mod", "Preset-4001"); rs("applique", "--profil", "h", "--go")
check("mod remis : le manquant revient", get(T + "c.fx") == "c" and get("bin/x64/preset.ini") == "p")
rs("bascule", "off", "--profil", "h", "--mod", "Preset-4001"); rs("applique", "--profil", "h", "--go")
put(T + "d.fx", "d-installateur")
mkzip("5_World/Preset Deux-4002-1-0-1700000011.zip", {T + "a.fx": "a", T + "d.fx": "d"})
ad = rs("adopte", "--profil", "h2")
check("adoption : rien pris sous le motif", ad["rapport"]["5_World/Preset Deux-4002-1-0-1700000011.zip"]["posables"] == 0
      and ad["rapport"][PZ]["posables"] == 2, str({k: v for k, v in ad["rapport"].items() if "Preset" in k}))

# le banc rend le dépôt comme les bancs suivants l'attendent (profil « t », aucun motif, aucun zip d'essai)
for z in (PZ, "5_World/Preset Deux-4002-1-0-1700000011.zip"):
    os.remove(os.path.join(DEPOT, z))
for n in ("h", "h2"):
    os.remove(os.path.join(DONNEES, "profils", n + ".json"))
rs("hors", "--retire", "bin/x64/shaders-tiers/*")
c = plan_counts()
check("profil « t » intact après l'essai", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

print("11. référence du jeu vierge")
REF = os.path.join(BASE, "reference")
r = rs("reference", "--cree", "--reference", REF, ok=False)
check("jeu déjà moddé : création refusée", "pas vierge" in str(r), str(r)[:200])
r = rs("reference", "--cree", "--force", "--reference", REF)
check("créée de force, marquée non vierge", r["vierge"] is False and r["fichiers"] > 0, str(r))
check("copie sans le dossier archive", os.path.isfile(os.path.join(REF, "bin", "x64", "socle.dll")) and not os.path.isdir(os.path.join(REF, "archive")))
r = rs("reference", "--reference", REF)
check("jeu conforme à sa référence", r["modifies"] == [] and r["manquants"] == [], str(r)[:300])
put("bin/x64/socle.dll", "socle MIS A JOUR"); os.remove(os.path.join(JEU, "r6", "tweaks", "shared.yaml")) if get("r6/tweaks/shared.yaml") else None
put("bin/x64/cree_en_jeu.log", "x")
r = rs("reference", "--reference", REF)
check("socle changé vu, fichier créé en jeu compté à part", r["modifies"] == ["bin/x64/socle.dll"] and r["ajoutes"] >= 1, str(r)[:300])
r = rs("reference", "--restaure", "--reference", REF)
check("sans --go : rien écrit", get("bin/x64/socle.dll") == "socle MIS A JOUR" and not r["restaure"])
r = rs("reference", "--restaure", "--go", "--reference", REF)
check("restauré : le socle revient, le reste ne bouge pas", get("bin/x64/socle.dll") == "socle" and get("bin/x64/cree_en_jeu.log") == "x"
      and get(T + "a.fx") == "a", str(r)[:200])
r = rs("reference", "--cree", "--force", "--reference", REF, ok=False)
check("une référence ne s'écrase pas", "existe déjà" in str(r), str(r)[:200])
conf = json.load(open(cp, encoding="utf-8"))
conf["jeu"] = jeu_du_banc
json.dump(conf, open(cp, "w", encoding="utf-8"))

print("12. conflits dans les archives")
import hashlib, struct


def fnv(path):
    v = 0xcbf29ce484222325
    for b in path.lower().encode():
        v = ((v ^ b) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return v


def rdar(res):
    """archive RDAR minimale : index (empreinte, SHA-1 du contenu) et bloc de chemins non compressé"""
    paths = b"".join(p.encode() + b"\0" for p in res)
    custom = struct.pack("<IIIII", 0x4C585253, 1, len(paths), len(paths), len(res)) + paths
    ents = b"".join(struct.pack("<QqIIIII", fnv(p), 0, 0, 0, 0, 0, 0) + hashlib.sha1(c.encode()).digest() for p, c in res.items())
    idx = struct.pack("<IIQIII", 8, len(ents), 0, len(res), 0, 0) + ents
    head = (b"RDAR" + struct.pack("<IQIQIQI", 12, 0xAC + len(custom), len(idx), 0, 0, 0, len(custom))).ljust(0xAC, b"\0")
    return head + custom + idx


conf = json.load(open(cp, encoding="utf-8"))            # le jeu du banc ne doit pas passer pour le vrai jeu
conf.pop("jeu", None)
json.dump(conf, open(cp, "w", encoding="utf-8"))
RA, RB, RC = "base\\x\\a.mesh", "base\\x\\b.mesh", "base\\x\\c.mesh"
mkzip("7_Conf/Zeta.zip", {A + "zeta.archive": rdar({RA: "Z", RB: "pareil", RC: "z"})})
mkzip("7_Conf/Alpha Tex.zip", {A + "Kappa.archive": rdar({RA: "A", RB: "pareil"})})
mkzip("7_Conf/Mid.zip", {A + "_mid.archive": rdar({RA: "M"})})
os.makedirs(os.path.join(JEU, "archive", "pc", "mod"), exist_ok=True)
open(os.path.join(JEU, "archive", "pc", "mod", "!main.archive"), "wb").write(rdar({RC: "posé à la main"}))
rs("profils", "--profil", "c", "--copie", "t")
for m in ("Zeta", "Alpha Tex", "Mid"):
    rs("bascule", "on", "--profil", "c", "--mod", "7_Conf/" + m)


def lecture():
    d = rs("conflits", "--profil", "c")
    return d, {a["archive"]: a for a in d["ordre"]}


d, o = lecture()
check("avant la pose : archives lues dans les zips", d["compte"]["en_conflit"] == 2 and d["compte"]["identiques"] == 1, str(d["compte"]))
rs("applique", "--profil", "c", "--go")
d, o = lecture()
rangs = [o[n]["rang"] for n in ("!main.archive", "Kappa.archive", "_mid.archive", "zeta.archive")]
check("ordre des noms en octets : ! puis MAJUSCULES puis _ puis minuscules", rangs == sorted(rangs) and d["ordre_par"] == "noms", str(rangs))
check("deux ressources en conflit, une copie identique à part", d["compte"]["en_conflit"] == 2 and d["compte"]["identiques"] == 1, str(d["compte"]))
check("l'archive du milieu gagne sur celle d'après et perd contre celle d'avant",
      (o["_mid.archive"]["gagne"], o["_mid.archive"]["perd"]) == (1, 1) and (o["Kappa.archive"]["gagne"], o["Kappa.archive"]["perd"]) == (1, 0)
      and (o["zeta.archive"]["gagne"], o["zeta.archive"]["perd"]) == (0, 2), str([o[n] for n in ("Kappa.archive", "_mid.archive", "zeta.archive")]))
pa = {(d["ordre"][p["gagnant"]]["archive"], d["ordre"][p["perdant"]]["archive"]): p for p in d["paires"]}
check("paire Kappa / zeta : un conflit, une identique, nommé par le bloc de chemins de l'archive",
      pa[("Kappa.archive", "zeta.archive")]["conflits"] == 1 and pa[("Kappa.archive", "zeta.archive")]["identiques"] == 1
      and pa[("Kappa.archive", "zeta.archive")]["exemples"] == [RA], str(pa.get(("Kappa.archive", "zeta.archive"))))
check("archive posée à la main : vue, dite hors Red Stack, gagne sur zeta",
      o["!main.archive"]["genre"] == "hors" and o["!main.archive"]["zip"] is None and pa[("!main.archive", "zeta.archive")]["conflits"] == 1)
check("archives qui ne sont pas des RDAR : signalées, sans casse", len(d["illisibles"]) > 0 and A + "w1.archive" in d["illisibles"], str(d["illisibles"])[:200])
dm = rs("conflits", "--profil", "c", "--mod", "7_Conf/Mid")
r = dm["ressources"]
check("détail d'un mod : gagne sur / perd contre par ressource",
      len(r) == 1 and r[0]["ressource"] == RA and r[0]["gagne_sur"] == [o["zeta.archive"]["rang"]]
      and r[0]["perd_contre"] == [o["Kappa.archive"]["rang"]] and r[0]["prise_dans"] == o["Kappa.archive"]["rang"], str(r))
dn = rs("conflits", "--profil", "c", "--nom=zeta.archive")
check("détail d'une archive : copie identique rangée à part",
      any(x["ressource"] == RB and x["identique_a"] == [o["Kappa.archive"]["rang"]] and not x["perd_contre"] for x in dn["ressources"]), str(dn["ressources"]))
os.makedirs(os.path.join(JEU, "archive", "pc", "content"), exist_ok=True)   # jeu de base : il porte RA et une ressource à lui
open(os.path.join(JEU, "archive", "pc", "content", "basegame_1.archive"), "wb").write(rdar({RA: "origine", "base\\x\\seule.mesh": "o"}))
dr = rs("conflits", "--profil", "c", "--ressources")
lr = {x["ressource"]: x for x in dr["ressources"]}
check("par ressource : où le jeu la prend, qui la perd, copie identique hors liste",
      dr["total"] == 2 and RB not in lr and [x["ressource"] for x in dr["identiques"]] == [RB] and dr["identiques"][0]["identiques"] and lr[RA]["prise_dans"] == o["Kappa.archive"]["rang"]
      and sorted(lr[RA]["perd"]) == sorted([o["_mid.archive"]["rang"], o["zeta.archive"]["rang"]]), str(dr["ressources"]))
check("jeu de base : la ressource qui le remplace est dite, l'autre non", lr[RA]["base"] is True and lr[RC]["base"] is False
      and dr["compte"]["base"] == 1 and {a["archive"]: a["base"] for a in dr["ordre"]}["_mid.archive"] == 1, str(dr["compte"]))
check("jeu de base : empreintes gardées en cache", json.load(open(os.path.join(DONNEES, "base.json"), encoding="utf-8"))["ressources"] == 2)
shutil.rmtree(os.path.join(JEU, "archive", "pc", "content"))
open(os.path.join(JEU, "archive", "pc", "mod", "modlist.txt"), "w").write("zeta.archive\nabsente.archive\n")
d, o = lecture()
check("modlist.txt : son ordre passe devant, le reste suit par nom",
      d["ordre_par"] == "modlist.txt" and o["zeta.archive"]["rang"] == 0 and o["zeta.archive"]["perd"] == 0 and o["zeta.archive"]["gagne"] == 2, str(o["zeta.archive"]))
os.remove(os.path.join(JEU, "archive", "pc", "mod", "modlist.txt"))
rs("applique", "--profil", "t", "--go")               # le banc rend le jeu et le dépôt comme les bancs suivants l'attendent
os.remove(os.path.join(JEU, "archive", "pc", "mod", "!main.archive"))
shutil.rmtree(os.path.join(DEPOT, "7_Conf"))
rs("profils", "--profil", "c", "--supprime")
conf = json.load(open(cp, encoding="utf-8"))
conf["jeu"] = jeu_du_banc
json.dump(conf, open(cp, "w", encoding="utf-8"))
c = plan_counts()
check("profil « t » intact après l'essai", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0 and get(A + "zeta.archive") is None, str(c))

# ---------------------------------------------------------------- 13. dépôt : nouveaux cochés d'office, parquer, remonter
NEUF = "5_World/Neuf-4001-1-0-1700000009.zip"
PARQUE = "5_World/Garage/Neuf-4001-1-0-1700000009.zip"     # « Garage » : dossier des parqués de la convention du banc (section 9)
mkzip(NEUF, {A + "neuf.archive": "n"})
def fixe(v, jeu=None):                      # écrit config.json à la main : le jeu du banc ne doit pas passer pour le vrai
    conf = json.load(open(cp, encoding="utf-8"))
    conf["nouveaux_actifs"] = v
    conf.pop("jeu", None)
    if jeu:
        conf["jeu"] = jeu
    json.dump(conf, open(cp, "w", encoding="utf-8"))


fixe(False)
check("réglage lu par la page", rs("config")["nouveaux_actifs"] is False)
fixe(False)
ligne = lambda cle: next((m for m in rs("etat", "--profil", "t")["mods"] if m["cle"] == cle), None)
check("zip arrivé dans une pile : nouveau, pas coché", ligne(NEUF)["etat"] == "nouveau dans le dépôt" and not ligne(NEUF)["actif"], str(ligne(NEUF)))
fixe(True)
check("option « nouveaux cochés d'office » : coché, à poser", ligne(NEUF)["actif"] and ligne(NEUF)["etat"] == "à poser", str(ligne(NEUF)))
rs("applique", "--profil", "t", "--go")
check("le nouveau est posé par le plan", get(A + "neuf.archive") == "n")
r = rs("deplace", "--cle", NEUF, "--vers", "parques", "--go", ok=False)
check("parquer un mod encore dans le jeu : refusé", isinstance(r, str) and "encore dans le jeu" in r and os.path.isfile(os.path.join(DEPOT, NEUF)), str(r)[:200])
rs("bascule", "off", "--profil", "t", "--mod", NEUF)
rs("applique", "--profil", "t", "--go")
r = rs("deplace", "--cle", NEUF, "--vers", "parques")
check("parquer sans --go : rien écrit, la cible est dite", r["ecrit"] is False and r["cle"] == PARQUE and os.path.isfile(os.path.join(DEPOT, NEUF)), str(r))
rs("deplace", "--cle", NEUF, "--vers", "parques", "--go")
check("parqué : le zip est dans le dossier des parqués, la ligne le dit",
      os.path.isfile(os.path.join(DEPOT, PARQUE)) and not os.path.isfile(os.path.join(DEPOT, NEUF)) and ligne(PARQUE)["genre"] == "parqué", str(ligne(PARQUE)))
check("parqué : aucun « zip disparu » au profil", not any(k == "zip disparu" and NEUF in o for k, o, n in rs("etat", "--profil", "t")["notes"]))
fixe(False)
rs("deplace", "--cle", PARQUE, "--vers", "pile", "--go")
check("remonté, option éteinte : à la racine, pas coché", os.path.isfile(os.path.join(DEPOT, NEUF)) and not ligne(NEUF)["actif"], str(ligne(NEUF)))
rs("deplace", "--cle", NEUF, "--vers", "parques", "--go")
RETIRE = "5_World/Corbeille/Neuf-4001-1-0-1700000009.zip"   # « Corbeille » : dossier des retirés de la convention du banc
r = rs("deplace", "--cle", PARQUE, "--vers", "retires")
check("retirer sans --go : rien écrit, la cible est dite", r["ecrit"] is False and r["cle"] == RETIRE and os.path.isfile(os.path.join(DEPOT, PARQUE)), str(r))
rs("deplace", "--cle", PARQUE, "--vers", "retires", "--go")
check("retiré : le zip est dans le dossier des retirés, rien d'effacé, la ligne le dit",
      os.path.isfile(os.path.join(DEPOT, RETIRE)) and not os.path.isfile(os.path.join(DEPOT, PARQUE)) and ligne(RETIRE)["genre"] == "retiré", str(ligne(RETIRE)))
check("retiré : aucun « zip disparu » au profil", not any(k == "zip disparu" and NEUF in o for k, o, n in rs("etat", "--profil", "t")["notes"]))
check("retiré : le geste est à l'historique", any(x.get("geste") == "retire" for x in rs("journal", "--geste", "retire")["entrees"]))
r = rs("journal", "--supprime", "--de", os.path.join(DEPOT, RETIRE.replace("/", os.sep)), ok=False)
check("suppression d'un zip toujours là : refusée, rien à l'historique",
      isinstance(r, str) and "toujours" in r and rs("journal", "--geste", "supprime")["trouve"] == 0, str(r)[:200])
r = rs("journal", "--supprime", "--de", "Parti.zip", ok=False)
check("suppression sans chemin complet : refusée", isinstance(r, str) and "--de" in r and rs("journal", "--geste", "supprime")["trouve"] == 0, str(r)[:200])
PARTI = os.path.join(DEPOT, "5_World", "Corbeille", "Parti-4002-1-0-1700000010.zip")
r = rs("journal", "--supprime", "--de", PARTI)
j = rs("journal", "--geste", "supprime")
check("suppression faite hors du moteur (corbeille du système) : inscrite à l'historique, trouvée par le nom du zip",
      r["ecrit"] and j["trouve"] == 1 and j["entrees"][0]["de"] == PARTI and rs("journal", "--mod", "Parti-4002")["trouve"] == 1, str(j)[:300])
r = rs("deplace", "--cle", RETIRE, "--vers", "retires", ok=False)
check("retirer un zip déjà retiré : refusé", isinstance(r, str) and "déjà" in r, str(r)[:200])
rs("deplace", "--cle", RETIRE, "--vers", "pile", "--go")
check("retiré puis remonté : à la racine, pas coché", os.path.isfile(os.path.join(DEPOT, NEUF)) and not ligne(NEUF)["actif"], str(ligne(NEUF)))
rs("deplace", "--cle", NEUF, "--vers", "parques", "--go")
fixe(True)
rs("deplace", "--cle", PARQUE, "--vers", "pile", "--go")
check("remonté, option allumée : coché d'office, à poser", ligne(NEUF)["actif"] and ligne(NEUF)["etat"] == "à poser", str(ligne(NEUF)))
r = rs("deplace", "--cle", NEUF, "--vers", "pile", ok=False)
check("remonter un zip déjà à la racine : refusé", isinstance(r, str) and "déjà" in r)
fixe(False)
rs("bascule", "off", "--profil", "t", "--mod", NEUF)
os.remove(os.path.join(DEPOT, NEUF))
if not os.listdir(os.path.join(DEPOT, "5_World", "Garage")):
    os.rmdir(os.path.join(DEPOT, "5_World", "Garage"))
fixe(False, jeu_du_banc)
c = plan_counts()
check("après l'essai : plan vide", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

# ---------------------------------------------------------------- 14. arrivages : noms à la convention, conversion en .zip
print("14. arrivages : noms proposés, renommage, conversion")
import calendar, time
ARR = "5_World/Arrivages/"
T0 = calendar.timegm((2026, 1, 2, 3, 4, 30))
APP = ARR + "Truc Machin 4242 1.2 2026-01-02T03-04Z AbCdEf  EDITED.zip"
DOUTE = ARR + "Bidule 4243 2.0 2026-01-02T03-04Z GhIjKl.zip"
mkzip(APP, {A + "truc.archive": "t"})
mkzip(DOUTE, {A + "bidule.archive": "b"})
mkzip(ARR + "Deja-4244-1-0-1700000010.zip", {A + "deja.archive": "d"})
fc = lambda fid, nom, ver, date, taille: {"fileId": fid, "name": nom, "version": ver, "date": date, "sizeInBytes": taille, "category": "MAIN"}
json.dump({"4242": {"lu": time.time(), "fichiers": [fc(1, "Truc Machin", "1.2", T0, 1), fc(2, "Truc Machin vieux", "1.1", T0 - 86400, 1)]},
           "4243": {"lu": time.time(), "fichiers": [fc(3, "Bidule rouge", "2.0", T0, 1), fc(4, "Bidule bleu", "2.0", T0 + 5, 2)]},
           "4244": {"lu": time.time(), "fichiers": [fc(5, "Deja", "1.0", 1700000010, 1)]}},   # tout arrivage au nom du site est lu aussi
          open(os.path.join(DONNEES, "nexus.json"), "w", encoding="utf-8"))
cv = lambda: {r["cle"]: r for r in rs("convention")["lignes"]}
v = cv()
VOULU = f"Truc Machin-4242-1-2-{T0}  EDITED.zip"
check("nom de l'application : proposé à la forme du site, annotation gardée", v[APP]["statut"] == "a_renommer" and v[APP]["propose"] == VOULU, str(v[APP]))
check("deux fichiers Nexus à la même minute : à trancher, deux candidats", v[DOUTE]["statut"] == "doute" and len(v[DOUTE]["candidats"]) == 2, str(v[DOUTE]))
check("nom du site : conforme ; nom libre : hors Nexus",
      v[ARR + "Deja-4244-1-0-1700000010.zip"]["statut"] == "conforme" and v[ARR + "Arrive.zip"]["statut"] == "hors_nexus")
r = rs("convention", "--fixe", json.dumps([{"cle": APP, "nom": VOULU}]))
check("renommer sans --go : rien écrit, la cible est dite", r["ecrit"] is False and len(r["renommes"]) == 1 and os.path.isfile(os.path.join(DEPOT, APP)), str(r))
for nom, mot in (("a:b.zip", "refusé"), ("Truc.7z", "extension"), ("Deja-4244-1-0-1700000010.zip", "déjà")):
    r = rs("convention", "--fixe", json.dumps([{"cle": APP, "nom": nom}]), "--go", ok=False)
    check(f"nom « {nom} » : refusé, rien écrit", isinstance(r, str) and mot in r and os.path.isfile(os.path.join(DEPOT, APP)), str(r)[:200])
r = rs("convention", "--fixe", json.dumps([{"cle": "../" + APP, "nom": "x.zip"}]), "--go", ok=False)
check("clé hors des piles : refusée", isinstance(r, str) and "inconnue" in r, str(r)[:200])
rs("convention", "--fixe", json.dumps([{"cle": APP, "nom": VOULU}, {"cle": DOUTE, "nom": v[DOUTE]["candidats"][1]["propose"]}]), "--go")
v = cv()
check("renommés : les deux zips portent leur nom, lus conformes",
      v.get(ARR + VOULU, {}).get("statut") == "conforme" and v.get(ARR + f"Bidule-4243-2-0-{T0 + 5}.zip", {}).get("statut") == "conforme"
      and APP not in v and DOUTE not in v, str(sorted(v)))
tar = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "tar.exe")
if os.path.isfile(tar):
    src = os.path.join(BASE, "_7z")
    shutil.rmtree(src, ignore_errors=True)
    os.makedirs(os.path.join(src, "archive", "pc", "mod"))
    open(os.path.join(src, "archive", "pc", "mod", "sept.archive"), "w").write("7")
    SEPT = "5_World/Sept-4245-1-0-1700000011.7z"
    subprocess.run([tar, "-a", "-cf", os.path.join(DEPOT, SEPT), "-C", src, "archive"], check=True)
    v = cv()
    check("un .7z d'une pile : listé, à convertir", v[SEPT]["convertir"] and v[SEPT]["statut"] == "conforme", str(v[SEPT]))
    r = rs("convention", "--convertit", "--cle", SEPT)
    check("convertir sans --go : rien écrit", r["ecrit"] is False and os.path.isfile(os.path.join(DEPOT, SEPT)), str(r))
    r = rs("convention", "--convertit", "--cle", SEPT, "--go")
    z = os.path.join(DEPOT, SEPT[:-3] + ".zip")
    check("converti : zip relu, original supprimé, le mod entre dans l'index",
          os.path.isfile(z) and not os.path.isfile(os.path.join(DEPOT, SEPT)) and zipfile.ZipFile(z).namelist() == [A + "sept.archive"]
          and ligne(SEPT[:-3] + ".zip") is not None, str(r))
    os.remove(z)
    shutil.rmtree(src, ignore_errors=True)
else:
    print("  --   conversion non éprouvée : tar.exe de Windows absent")
for f in (VOULU, f"Bidule-4243-2-0-{T0 + 5}.zip", "Deja-4244-1-0-1700000010.zip"):
    os.remove(os.path.join(DEPOT, ARR + f))
os.remove(os.path.join(DONNEES, "nexus.json"))

# ---------------------------------------------------------------- 15. contenu d'un zip : plan de renommage, références, réécriture
print("15. contenu : noms proposés, références croisées, zip récrit")
S, T = "r6/scripts/", "r6/tweaks/"
TRUC = ARR + "Mon Truc-5001-1-0-1700000020.zip"
TENU = ARR + "Tenu-5003-1-0-1700000022.zip"
VU = ARR + "Vu-5005-1-0-1700000024.zip"
EMB = ARR + "Emballe-5004-1-0-1700000023.zip"
ORD = ARR + "Ordre-5006-1-0-1700000025.zip"
CITE = "5_World/Cite-5002-1-0-1700000021.zip"
mkzip(TRUC, {A + "monTruc.archive": "m", A + "monTruc.archive.xl": "x", S + "monTruc/a.reds": "// a", S + "monTruc/b.reds": "// b",
             T + "monTruc/seul.yaml": "a: 1", T + "gardeMoi.yaml": "b: 2", T + "autreFichier.yaml": "c: 3", "LISEZ.txt": "notes"})
mkzip(CITE, {S + "Cite/x.reds": 'if ModArchiveExists("tenuParAutre.archive") { }\n// vuEnCommentaire.archive\nlet f = "gardeMoi.yaml";'})
mkzip(TENU, {A + "tenuParAutre.archive": "t", A + "tenuParAutre.archive.xl": "x"})
mkzip(VU, {A + "vuEnCommentaire.archive": "v"})
mkzip(EMB, {"Emballe v1/" + A + "Emballe.archive": "e", "Emballe v1/" + T + "emballe.yaml": "e: 1"})
mkzip(ORD, {A + "alpha.archive": "a", A + "Beta.archive": "b"})
ops = lambda cle, *a: {o["de"]: o["vers"] for o in rs("contenu", "--cle", cle, *a)["ops"]}
DOS, DOS2 = ARR + "Dossiers-5007-1-0-1700000026.zip", ARR + "Dossiers Deux-5008-1-0-1700000027.zip"
mkzip(DOS, {S + "Zulu/a.reds": "// a", S + "Zulu/b.reds": "// b", S + "beta/c.reds": "// c", S + "beta/d.reds": "// d"})
mkzip(DOS2, {S + "alphaOne/a.reds": "// a", S + "alphaOne/b.reds": "// b", S + "betaTwo/c.reds": "// c", S + "betaTwo/d.reds": "// d"})
r = rs("contenu", "--cle", DOS)
check("plusieurs dossiers de scripts dont l'ordre changerait : tous gardés au nom de l'auteur, dit",
      not r["ops"] and {g["chemin"] for g in r["gardes"]} == {S + "beta"} and "ordre" in " ".join(r["notes"]), str(r))
check("plusieurs dossiers dont l'ordre tient : renommés",
      ops(DOS2) == {S + "alphaOne/a.reds": S + "Alpha_One/a.reds", S + "alphaOne/b.reds": S + "Alpha_One/b.reds",
                    S + "betaTwo/c.reds": S + "Beta_Two/c.reds", S + "betaTwo/d.reds": S + "Beta_Two/d.reds"}, str(ops(DOS2)))
PREF = ARR + "Prefixe-5009-1-0-1700000028.zip"
mkzip(PREF, {S + "zz_monLot/a.reds": "// a", S + "zz_monLot/b.reds": "// b", S + "0_autreLot/c.reds": "// c", S + "0_autreLot/d.reds": "// d"})
r = rs("contenu", "--cle", PREF)
check("dossiers à préfixe d'ordre : renommés à la convention, préfixe gardé, recommandation dite",
      {x["de"]: x["vers"] for x in r["ops"]} == {S + "zz_monLot/a.reds": S + "zz_Mon_Lot/a.reds", S + "zz_monLot/b.reds": S + "zz_Mon_Lot/b.reds",
                                                 S + "0_autreLot/c.reds": S + "0_Autre_Lot/c.reds", S + "0_autreLot/d.reds": S + "0_Autre_Lot/d.reds"}
      and sum("préfixe" in n for n in r["notes"]) == 2 and not r["gardes"], str(r))
libre = [{"de": S + "zz_monLot/a.reds", "vers": S + "Mon_Lot/a.reds"}]
check("retirer le préfixe à la main : accepté (sans --go, rien écrit)", rs("contenu", "--cle", PREF, "--fixe", json.dumps(libre))["renommes"] == 1)
o = ops(TRUC)
check("archive seule et son .xl : au nom du mod, `.archive.xl` -> `.xl`",
      o.get(A + "monTruc.archive") == A + "Mon_Truc.archive" and o.get(A + "monTruc.archive.xl") == A + "Mon_Truc.xl", str(o))
check("dossier de scripts au nom du mod ; .yaml seul dans son dossier remonté d'un cran",
      o.get(S + "monTruc/a.reds") == S + "Mon_Truc/a.reds" and o.get(T + "monTruc/seul.yaml") == T + "Mon_Truc.yaml", str(o))
check("plusieurs .yaml : gardés ; fichier hors pose jamais proposé", T + "gardeMoi.yaml" not in o and T + "autreFichier.yaml" not in o and "LISEZ.txt" not in o, str(o))
check("nom du mod donné par l'utilisateur : repris partout", ops(TRUC, "--nom", "Machin")[A + "monTruc.archive"] == A + "Machin.archive")
r = rs("contenu", "--cle", TENU)
check(".archive citée en dur par un autre mod : gardée, dite ; seul `.archive.xl` -> `.xl`",
      [(x["de"], x["vers"]) for x in r["ops"]] == [(A + "tenuParAutre.archive.xl", A + "tenuParAutre.xl")] and "un autre mod" in " ".join(r["notes"]), str(r))
check("citation en commentaire : pas une référence, renommée", ops(VU) == {A + "vuEnCommentaire.archive": A + "Vu.archive"}, str(ops(VU)))
r = rs("contenu", "--cle", EMB)
check("dossier de tête qui emballe le mod : remonté à la racine du zip",
      {x["de"]: x["vers"] for x in r["ops"]} == {"Emballe v1/" + A + "Emballe.archive": A + "Emballe.archive", "Emballe v1/" + T + "emballe.yaml": T + "Emballe.yaml"}, str(r))
r = rs("contenu", "--cle", ORD)
check("ordre de chargement changé par le renommage : .archive gardées, dit", r["ops"] == [] and "ordre de chargement" in " ".join(r["notes"]), str(r))
voulu = [{"de": k, "vers": v} for k, v in o.items()]
r = rs("contenu", "--cle", TRUC, "--fixe", json.dumps(voulu))
check("récrire sans --go : rien écrit", r["ecrit"] is False and r["renommes"] == len(voulu) and A + "monTruc.archive" in zipfile.ZipFile(os.path.join(DEPOT, TRUC)).namelist())
for bad, mot in (([{"de": A + "monTruc.archive", "vers": "../dehors.archive"}], "refusé"), ([{"de": "absent.txt", "vers": "x.txt"}], "inconnue"),
                 ([{"de": S + "monTruc/a.reds", "vers": S + "monTruc/b.reds"}], "même chemin")):
    r = rs("contenu", "--cle", TRUC, "--fixe", json.dumps(bad), "--go", ok=False)
    check(f"demande « {bad[0]['vers']} » : refusée, zip intact", isinstance(r, str) and mot in r and A + "monTruc.archive" in zipfile.ZipFile(os.path.join(DEPOT, TRUC)).namelist(), str(r)[:200])
avant = {i.filename: (i.CRC, i.date_time) for i in zipfile.ZipFile(os.path.join(DEPOT, TRUC)).infolist()}
rs("contenu", "--cle", TRUC, "--fixe", json.dumps(voulu), "--go")
apres = {i.filename: (i.CRC, i.date_time) for i in zipfile.ZipFile(os.path.join(DEPOT, TRUC)).infolist()}
check("zip récrit : nouveaux noms, contenu et dates gardés, rien perdu",
      apres == {o.get(k, k): v for k, v in avant.items()} and len(apres) == len(avant) and zipfile.ZipFile(os.path.join(DEPOT, TRUC)).testzip() is None, str(sorted(apres)))
relu = rs("contenu", "--cle", TRUC)
check("relu après coup : conforme, et tous ses fichiers restent listés pour une retouche",
      relu["etat"] == "conforme" and not relu["ops"] and len(relu["fichiers"]) >= len(o), str(relu))
# dossier de famille : les frères « Clan - … » rangent leurs tweaks sous `Clan/` ; le nouveau venu y est proposé, ses scripts non (aucun frère n'en range)
FA, FB, FC = "5_World/Clan - Un-5011-1-0-1700000030.zip", "5_World/Clan - Deux-5012-1-0-1700000031.zip", ARR + "Clan - Trois-5013-1-0-1700000032.zip"
mkzip(FA, {A + "Clan_Un.archive": "1", T + "Clan/Clan_Un.yaml": "a: 1"})
mkzip(FC, {A + "clanTrois.archive": "3", T + "clanTrois.yaml": "c: 3", S + "clanTrois.reds": "// c"})
check("un seul frère range ses tweaks dans un dossier : rien de proposé", ops(FC).get(T + "clanTrois.yaml") == T + "Clan_Trois.yaml", str(ops(FC)))
mkzip(FB, {A + "Clan_Deux.archive": "2", T + "Clan/Clan_Deux.yaml": "b: 2"})
r = rs("contenu", "--cle", FC)
o = {x["de"]: x["vers"] for x in r["ops"]}
check("dossier de famille lu chez deux frères : le tweak y est proposé, dit ; le script reste où il est",
      o.get(T + "clanTrois.yaml") == T + "Clan/Clan_Trois.yaml" and o.get(S + "clanTrois.reds") == S + "Clan_Trois.reds" and sum("« Clan - … »" in n for n in r["notes"]) == 1, str(r))
libre = [{"de": S + "clanTrois.reds", "vers": S + "Neuf/Sous/clanTrois.reds"}]
rs("contenu", "--cle", FC, "--fixe", json.dumps(libre), "--go")
check("restructurer à la main : un dossier qui n'existait pas est créé dans le zip", S + "Neuf/Sous/clanTrois.reds" in zipfile.ZipFile(os.path.join(DEPOT, FC)).namelist())
for f in (TRUC, TENU, VU, EMB, ORD, CITE, DOS, DOS2, PREF, FA, FB, FC):
    os.remove(os.path.join(DEPOT, f))
os.remove(os.path.join(DONNEES, "references.json"))
c = plan_counts()
check("après l'essai : plan vide", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

print("16. « ce fichier est à ce mod », et les mods coupés nommés dans le plan")
T16 = "bin/x64/tiers-seize/"
CZ = "5_World/Claim-4101-1-0-1700000016.zip"
mkzip(CZ, {"bin/x64/claim.dat": "p", T16 + "a.fx": "a", T16 + "b.fx": "b"})
put("bin/x64/claim.dat", "p"); put(T16 + "a.fx", "a"); put(T16 + "b.fx", "b-autre")
rs("hors", "--ajoute", T16 + "*")
conf = json.load(open(cp, encoding="utf-8"))            # le jeu du banc n'est pas un « vrai jeu » (inscrit par les sections d'avant)
conf.pop("jeu", None)
json.dump(conf, open(cp, "w", encoding="utf-8"))
rs("adopte", "--profil", "m"); rs("applique", "--profil", "m", "--go", "--vrai-jeu")
f16 = lambda: rs("fichier", "--nom", "tiers-seize")["total"]
det = lambda: {e["dest"]: e for e in rs("detail", "--profil", "m", "--mod", "Claim-4101")["entrees"]}
check("au départ : les deux sont à l'installateur", det()[T16 + "a.fx"]["hors"] and det()[T16 + "b.fx"]["hors"] and f16() == 0)
r = rs("option", "on", "--profil", "m", "--mod", "Claim-4101", "--entree", "bin/x64/claim.dat", "--mien", ok=False)
check("fichier hors de tout motif : revendication refusée", isinstance(r, str) and "aucun motif" in r, str(r)[:200])
rs("option", "on", "--profil", "m", "--mod", "Claim-4101", "--entree", T16 + "a.fx", "--mien")
d = det()[T16 + "a.fx"]
check("détail : à ce mod, plus hors, pris", d["mien"] and not d["hors"] and d["pris"], str(d))
p = rs("plan", "--profil", "m")
c = p["compte"]
check("plan : un fichier à prendre au registre, rien d'écrit dans le jeu", c["pris"] == 1 and c["pose"] == c["remplace"] == c["retire"] == c["lie"] == 0
      and p["pris"][0]["dest"] == T16 + "a.fx", str(c))
rs("applique", "--profil", "m", "--go", "--si-plan", p["empreinte"])
check("pris au registre, contenu intact", f16() == 1 and get(T16 + "a.fx") == "a", str(f16()))
c = rs("plan", "--profil", "m")["compte"]
check("plan stable après la prise", c["pris"] == c["rendu"] == c["pose"] == c["lie"] == c["delie"] == 0, str(c))
if MAGASIN:
    arbre = os.path.join(STORE, "5_World", "Claim-4101-1-0-1700000016", "bin", "x64", "tiers-seize", "a.fx")
    check("jamais lié à l'arbre", not (os.path.isfile(arbre) and os.path.samefile(arbre, os.path.join(JEU, "bin", "x64", "tiers-seize", "a.fx"))))
rs("option", "on", "--profil", "m", "--mod", "Claim-4101", "--entree", T16 + "b.fx", "--mien")
p = rs("plan", "--profil", "m")
check("autre contenu que le zip : pris quand même, dit, rien à remplacer", p["compte"]["pris"] == 1 and "autre contenu" in p["pris"][0].get("raison", "")
      and p["compte"]["remplace"] == p["compte"]["pose"] == 0, str(p["compte"]))
rs("applique", "--profil", "m", "--go", "--vrai-jeu")
p = rs("plan", "--profil", "m")
check("gardé tel quel, vu « modifié en jeu »", get(T16 + "b.fx") == "b-autre" and f16() == 2 and p["compte"]["pris"] == 0
      and any(r["dest"] == T16 + "b.fx" for r in p["garde_modifie"]), str(p["compte"]))
rs("option", "off", "--profil", "m", "--mod", "Claim-4101", "--entree", T16 + "b.fx", "--mien")
p = rs("plan", "--profil", "m")
check("case décochée : à rendre à l'installateur", p["compte"]["rendu"] == 1 and p["compte"]["retire"] == 0 and det()[T16 + "b.fx"]["hors"], str(p["compte"]))
rs("applique", "--profil", "m", "--go", "--vrai-jeu")
check("rendu : laissé dans le jeu, sorti du registre", get(T16 + "b.fx") == "b-autre" and f16() == 1, str(f16()))
rs("bascule", "off", "--profil", "m", "--mod", "Claim-4101")
p = rs("plan", "--profil", "m")
k = [x for x in p["coupes"] if x["zip"] == CZ]
check("mod coupé : nommé dans le plan, son fichier pris part avec lui", len(k) == 1 and k[0]["retire"] == 2
      and any(r["dest"] == T16 + "a.fx" for r in p["retire"]), str(p["coupes"]))
rs("applique", "--profil", "m", "--go", "--vrai-jeu")
check("parti avec le mod, celui de l'installateur resté", get(T16 + "a.fx") is None and get(T16 + "b.fx") == "b-autre" and get("bin/x64/claim.dat") is None)
check("après « Appliquer » : plus rien à dire du mod coupé", not [x for x in rs("plan", "--profil", "m")["coupes"] if x["zip"] == CZ])
os.remove(os.path.join(DEPOT, CZ))
os.remove(os.path.join(DONNEES, "profils", "m.json"))
rs("hors", "--retire", T16 + "*")
SA, SB = "5_World/Shared A-3002-1-0-1700000005.zip", "5_World/Shared B-3003-1-0-1700000006.zip"
actifs = {m["cle"]: m["actif"] for m in rs("etat", "--profil", "t")["mods"]}
for z in (SA, SB):
    if not actifs[z]:
        rs("bascule", "on", "--profil", "t", "--mod", z.split("/")[1][:-4])
rs("applique", "--profil", "t", "--go")
tient = rs("fichier", "--nom", "shared.yaml")["fichiers"][0]["zip"]
autre = SB if tient == SA else SA
rs("bascule", "off", "--profil", "t", "--mod", tient.split("/")[1][:-4])
p = rs("plan", "--profil", "t")
k = [x for x in p["coupes"] if x["zip"] == tient]
check("fichier partagé : le plan dit qui le reprend", len(k) == 1 and k[0]["retire"] == 1 and k[0]["repris"] == [{"zip": autre, "n": 1}], str(p["coupes"]))
dk = {e["dest"]: e for e in rs("detail", "--profil", "t", "--mod", tient.split("/")[1][:-4])["entrees"]}
check("détail du mod coupé : le fichier partagé n'est pas « à retirer », l'autre le tient",
      dk["r6/tweaks/shared.yaml"]["etat"] == "partagé avec " + autre and not dk["r6/tweaks/shared.yaml"]["pris"], str(dk["r6/tweaks/shared.yaml"]))
if MAGASIN:
    check("« à lier » : dit de quel mod il est repris", [r.get("ancien") for r in p["lie"]] == [tient], str(p["lie"]))
rs("bascule", "on", "--profil", "t", "--mod", tient.split("/")[1][:-4])
p = rs("plan", "--profil", "t")
check("remis avant d'appliquer : plus de ligne, plan vide", not p["coupes"] and p["compte"]["retire"] == p["compte"]["lie"] == 0, str(p["coupes"]))

# ---------------------------------------------------------------- 17. ordre de chargement : nom par le profil, modlist.txt
print("17. ordre de chargement")
conf = json.load(open(cp, encoding="utf-8"))
conf.pop("jeu", None)
json.dump(conf, open(cp, "w", encoding="utf-8"))
MODDIR = os.path.join(JEU, "archive", "pc", "mod")
la = lambda n: os.path.isfile(os.path.join(MODDIR, n)) and n in os.listdir(MODDIR)
mkzip("7_Ord/Zeta.zip", {A + "zeta.archive": rdar({RA: "Z"}), "r6/scripts/zeta/cite.reds": 'let a = "Kappa.archive";\n'})
mkzip("7_Ord/Alpha.zip", {A + "Kappa.archive": rdar({RA: "A"})})
rs("profils", "--profil", "o", "--copie", "t")
for m in ("Zeta", "Alpha"):
    rs("bascule", "on", "--profil", "o", "--mod", "7_Ord/" + m)
rs("applique", "--profil", "o", "--go")
gagne = lambda: {x["archive"]: x for x in rs("conflits", "--profil", "o")["ordre"]}
d = rs("ordre", "--profil", "o")
noms = [x["archive"] for x in d["ordre"]]
check("lecture de l'ordre : Kappa avant zeta, rien de tenu", noms.index("Kappa.archive") < noms.index("zeta.archive")
      and d["ordre_par"] == "noms" and not d["modlist"]["tenu"], str(noms))
pr = rs("ordre", "--profil", "o", "--nom", "zeta.archive", "--avant", "Kappa.archive")["propose"]
check("proposition : un nom qui passe avant, le moins de signes, rien écrit",
      pr["nom"] == "!zeta.archive" and pr["atteint"] and pr["rang_apres"] < pr["rang"] and not pr["cites"]
      and rs("plan", "--profil", "o")["compte"]["pose"] == 0, str(pr))
pr = rs("ordre", "--profil", "o", "--nom", "Kappa.archive", "--apres", "zeta.archive")["propose"]
check("proposition « après » : préfixe z, et qui cite l'archive par son nom est dit",
      pr["nom"] == "zz_Kappa.archive" and pr["atteint"] and [c["zip"] for c in pr["cites"]] == ["7_Ord/Zeta.zip"], str(pr))
f = rs("ordre", "--profil", "o", "--nom", "zeta.archive", "--renomme", "!zeta")["fait"]
p = rs("plan", "--profil", "o")
check("renommer par le profil : le plan pose le nouveau nom et retire l'ancien, le zip n'a pas bougé",
      f["vers"] == "!zeta.archive" and p["compte"]["pose"] + p["compte"]["lie"] >= 1 and p["compte"]["retire"] == 1
      and zipfile.ZipFile(os.path.join(DEPOT, "7_Ord", "Zeta.zip")).namelist()[0] == A + "zeta.archive", str(p["compte"]))
rs("applique", "--profil", "o", "--go")
o = gagne()
check("appliqué : l'archive porte son nouveau nom dans le jeu et gagne",
      la("!zeta.archive") and not la("zeta.archive") and o["!zeta.archive"]["gagne"] == 1 and o["Kappa.archive"]["perd"] == 1
      and o["!zeta.archive"]["origine"] == "zeta.archive", str(o.get("!zeta.archive")))
check("plan vide après la pose", sum(rs("plan", "--profil", "o")["compte"][k] for k in ("pose", "remplace", "retire", "lie")) == 0)
r = rs("ordre", "--profil", "o", "--nom", "!zeta.archive", "--renomme", "!Zeta", ok=False)
check("changer la seule casse : refusé, dit", "casse" in str(r), str(r)[:200])
r = rs("ordre", "--profil", "o", "--nom", "!zeta.archive", "--renomme", "Kappa", ok=False)
check("nom déjà pris par une autre archive : refusé", "déjà" in str(r), str(r)[:200])
rs("ordre", "--profil", "o", "--nom", "!zeta.archive", "--annule")
rs("applique", "--profil", "o", "--go")
check("nom de l'auteur rendu", la("zeta.archive") and not la("!zeta.archive") and gagne()["zeta.archive"]["perd"] == 1
      and "renomme" not in json.load(open(os.path.join(DONNEES, "profils", "o.json"), encoding="utf-8"))["mods"]["7_Ord/Zeta.zip"])
f = rs("ordre", "--profil", "o", "--nom", "zeta.archive", "--avant", "Kappa.archive", "--voie", "modlist")
p = rs("plan", "--profil", "o")
check("modlist.txt : noté au profil, le plan l'annonce, rien d'autre à écrire",
      f["fait"]["lignes"] >= 1 and f["modlist"]["lignes"][-1] == "zeta.archive" and "Kappa.archive" not in f["modlist"]["lignes"]
      and f["modlist"]["a_appliquer"] and p["compte"]["modlist"] == 1 and p["compte"]["pose"] == p["compte"]["retire"] == 0, str(f["modlist"]))
check("l'analyse lit l'ordre voulu avant même la pose", gagne()["zeta.archive"]["gagne"] == 1)
e1 = p["empreinte"]
rs("applique", "--profil", "o", "--go", "--si-plan", e1)
ml = os.path.join(MODDIR, "modlist.txt")
d = rs("conflits", "--profil", "o")
check("appliqué : le fichier cite toutes les archives, la tête voulue d'abord ; l'ordre vient de lui, plan vide",
      open(ml, encoding="utf-8").read().splitlines() == [x["archive"] for x in d["ordre"] if x["genre"] != "redmod"]
      and open(ml, encoding="utf-8").read().splitlines()[:len(f["modlist"]["lignes"])] == f["modlist"]["lignes"] and d["ordre_par"] == "modlist.txt"
      and rs("plan", "--profil", "o")["compte"]["modlist"] == 0 and rs("plan", "--profil", "o")["empreinte"] != e1)
pr = rs("ordre", "--profil", "o", "--nom", "Kappa.archive", "--avant", "zeta.archive")["propose"]
check("sous modlist.txt, un nom qui ne changerait rien est dit sans effet", pr["par_modlist"] and (pr["atteint"] or pr["nom"]), str(pr))
rs("ordre", "--profil", "o", "--modlist", "--annule")
p = rs("plan", "--profil", "o")
check("ne plus tenir modlist.txt : le plan annonce son retrait", p["compte"]["modlist"] == 1 and p["modlist"][0]["action"] == "retirer", str(p["modlist"]))
rs("applique", "--profil", "o", "--go")
check("retiré, et le profil ne le tient plus", not os.path.isfile(ml) and gagne()["zeta.archive"]["perd"] == 1
      and "modlist" not in json.load(open(os.path.join(DONNEES, "profils", "o.json"), encoding="utf-8")))
open(ml, "w").write("zeta.archive\n")
check("fichier écrit à la main : lu, laissé par le plan", rs("conflits", "--profil", "o")["ordre_par"] == "modlist.txt"
      and rs("plan", "--profil", "o")["compte"]["modlist"] == 0)
os.remove(ml)
rs("applique", "--profil", "t", "--go")
shutil.rmtree(os.path.join(DEPOT, "7_Ord"))
rs("profils", "--profil", "o", "--supprime")
conf = json.load(open(cp, encoding="utf-8"))
conf["jeu"] = jeu_du_banc
json.dump(conf, open(cp, "w", encoding="utf-8"))
c = plan_counts()
check("profil « t » intact après l'essai", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0 and not la("zeta.archive"), str(c))

# ---------------------------------------------------------------- 18. noms dans le jeu : scripts, tweaks, .xl, dossiers CET et REDmod
print("18. noms dans le jeu, par le profil")
conf = json.load(open(cp, encoding="utf-8"))
conf.pop("jeu", None)
json.dump(conf, open(cp, "w", encoding="utf-8"))
CM = "bin/x64/plugins/cyber_engine_tweaks/mods/"
BETA = {A + "beta.archive": "b", A + "beta.xl": "x", "r6/scripts/beta/main.reds": "m", "r6/scripts/beta/sub/util.reds": "u",
        "r6/tweaks/beta.yaml": "t", CM + "beta/init.lua": 'local a = 1\n', "mods/beta/info.json": "{}", "mods/beta/archives/b.archive": "r"}
mkzip("8_Noms/Beta.zip", BETA)
mkzip("8_Noms/Gamma.zip", {CM + "gamma/init.lua": 'local b = GetMod("beta")\nlocal p = "r6/scripts/beta/main.reds"\n-- GetMod("gamma")\n',
                           "r6/tweaks/gamma.yaml": "g"})
rs("profils", "--profil", "n", "--copie", "t")
for m in ("Beta", "Gamma"):
    rs("bascule", "on", "--profil", "n", "--mod", "8_Noms/" + m)
rs("applique", "--profil", "n", "--go")
d = rs("noms", "--profil", "n", "--mod", "8_Noms/Beta")
U = {u["chemin"]: u for u in d["unites"]}
check("lecture : six noms, un par genre, aucun changé",
      sorted(u["genre"] for u in d["unites"]) == ["archive", "cet", "redmod", "scripts", "tweaks", "xl"] and not any(u["renommee"] for u in d["unites"])
      and U["r6/scripts/beta"]["dossier"] and U["r6/scripts/beta"]["fichiers"] == 2 and not U["r6/tweaks/beta.yaml"]["dossier"], str(sorted(U)))
check("qui cite : le dossier CET (GetMod) et le dossier de scripts (chemin), par l'autre mod ; un commentaire ne compte pas",
      [(c["zip"], c["soi"]) for c in U[CM + "beta"]["cites"]] == [("8_Noms/Gamma.zip", False)]
      and [c["zip"] for c in U["r6/scripts/beta"]["cites"]] == ["8_Noms/Gamma.zip"] and not U["r6/tweaks/beta.yaml"]["cites"]
      and not {u["chemin"]: u for u in rs("noms", "--profil", "n", "--mod", "8_Noms/Gamma")["unites"]}[CM + "gamma"]["cites"],
      str(U[CM + "beta"]["cites"]) + str(U["r6/scripts/beta"]["cites"]))
check("cache des références : à la version des motifs",
      all(c.get("v") == 3 for c in json.load(open(os.path.join(DONNEES, "references.json"), encoding="utf-8")).values()))
d = rs("noms", "--profil", "n", "--mod", "8_Noms/Beta", "--fixe", json.dumps(
    [{"de": "r6/scripts/beta", "vers": "Beta_Scripts"}, {"de": CM + "beta", "vers": "beta2"}, {"de": "r6/tweaks/beta.yaml", "vers": "zz_beta"},
     {"de": "mods/beta", "vers": "beta_redmod"}, {"de": A + "beta.xl", "vers": "beta.xl"}]))
U = {u["chemin"]: u for u in d["unites"]}
p = rs("plan", "--profil", "n")
check("noté au profil : quatre noms changés (extension remise, nom inchangé ignoré), l'avertissement suit le geste",
      [f["vers"] for f in d["fait"]] == ["Beta_Scripts", "beta2", "zz_beta.yaml", "beta_redmod"] and U["r6/scripts/beta"]["actuel"] == "Beta_Scripts"
      and [c["zip"] for c in d["fait"][1]["cites"]] == ["8_Noms/Gamma.zip"] and not U[A + "beta.xl"]["renommee"], str(d["fait"]))
check("le plan pose les nouveaux noms et retire les anciens, le zip n'a pas bougé",
      p["compte"]["retire"] == 6 and p["compte"]["pose"] + p["compte"]["lie"] >= 6
      and sorted(zipfile.ZipFile(os.path.join(DEPOT, "8_Noms", "Beta.zip")).namelist()) == sorted(BETA), str(p["compte"]))
rs("applique", "--profil", "n", "--go")
check("appliqué : chaque fichier est sous son nouveau nom, plus rien sous l'ancien, plan vide",
      get("r6/scripts/Beta_Scripts/sub/util.reds") == "u" and get(CM + "beta2/init.lua") is not None and get("r6/tweaks/zz_beta.yaml") == "t"
      and get("mods/beta_redmod/archives/b.archive") == "r" and get("r6/scripts/beta/main.reds") is None and get(CM + "beta/init.lua") is None
      and get("r6/tweaks/beta.yaml") is None and get(A + "beta.archive") == "b"
      and sum(rs("plan", "--profil", "n")["compte"][k] for k in ("pose", "remplace", "retire", "lie")) == 0)
dk = {e["entree"]: e for e in rs("detail", "--profil", "n", "--mod", "8_Noms/Beta")["entrees"]}
check("le détail du mod montre la destination renommée", dk["r6/scripts/beta/main.reds"]["dest"] == "r6/scripts/Beta_Scripts/main.reds"
      and dk["r6/scripts/beta/main.reds"]["etat"] in ("lié", "copié"), str(dk["r6/scripts/beta/main.reds"]))
r = rs("noms", "--profil", "n", "--mod", "8_Noms/Beta", "--fixe", json.dumps([{"de": "r6/scripts/beta", "vers": "beta_scripts"}]), ok=False)
check("changer la seule casse : refusé, dit", "casse" in str(r), str(r)[:200])
r = rs("noms", "--profil", "n", "--mod", "8_Noms/Beta", "--fixe", json.dumps([{"de": "r6/tweaks/beta.yaml", "vers": "gamma"}]), ok=False)
check("nom qui prendrait la place du fichier d'un autre mod : refusé, dit", "autre mod" in str(r), str(r)[:200])
r = rs("noms", "--profil", "n", "--mod", "8_Noms/Beta", "--fixe", json.dumps([{"de": "r6/scripts/beta", "vers": "a/b"}]), ok=False)
check("nom à barre oblique : refusé", "refusé" in str(r), str(r)[:200])
d = rs("noms", "--profil", "n", "--mod", "8_Noms/Beta", "--fixe", json.dumps(
    [{"de": u, "vers": ""} for u in ("r6/scripts/beta", CM + "beta", "r6/tweaks/beta.yaml", "mods/beta")]))
rs("applique", "--profil", "n", "--go")
check("nom de l'auteur rendu (champ vide) : le profil ne note plus rien, le jeu revient",
      "renomme" not in json.load(open(os.path.join(DONNEES, "profils", "n.json"), encoding="utf-8"))["mods"]["8_Noms/Beta.zip"]
      and get("r6/scripts/beta/sub/util.reds") == "u" and get("r6/scripts/Beta_Scripts/main.reds") is None and get(CM + "beta/init.lua") is not None
      and len(d["fait"]) == 4 and not any(u["renommee"] for u in d["unites"]))
rs("applique", "--profil", "t", "--go")
shutil.rmtree(os.path.join(DEPOT, "8_Noms"))
rs("profils", "--profil", "n", "--supprime")

# ---------------------------------------------------------------- 19. conflits de code : Redscript, TweakXL, SetFlat
print("19. conflits de code (scripts)")
mkzip("9_Code/Un.zip", {
    "r6/scripts/un/a.reds": 'module Un\n@replaceMethod(Foo)\nfunc Bar(a: Int32, b: array<ref<X>>) -> Void { let x = 1; }\n'
                            '// @replaceMethod(Foo) func Commentaire() {}\n@wrapMethod(Foo)\nfunc W() -> Void { wrappedMethod(); }\n'
                            '@addMethod(Foo)\nfunc Neuf() -> Void {}\n@if(ModuleExists("Absent"))\n@replaceMethod(Foo)\nfunc Garde() -> Void { }\n',
    "r6/tweaks/un.yaml": 'Items.A:\n  price: 10\n  tags:\n    - !append X\n  list: [a, b]\nItems.B:\n  $type: gamedataItem_Record\n  v: 1\n',
    CM + "un/init.lua": '-- TweakDB:SetFlat("Items.C.v", 1)\nTweakDB:SetFlat("Items.C.v", 5)\n'})
mkzip("9_Code/Deux.zip", {
    "r6/scripts/deux/b.reds": '@replaceMethod(Foo)\nfunc Bar(a: Int32, b: [ref<X>]) -> Void { let x = 2; }\n@wrapMethod(Foo)\nfunc W() -> Void { return; }\n'
                              '@addMethod(Foo)\nfunc Neuf() -> Void {}\n@if(ModuleExists("Un"))\n@replaceMethod(Foo)\nfunc Garde() -> Void { }\n',
    "r6/tweaks/deux.yaml": 'Items.A:\n  price: 12   # autre valeur\n  tags:\n    - !remove X\n  list: [a, c]\nItems.C:\n  v: 7\n',
    "r6/tweaks/casse.yaml": 'Items.D:\n\t- b\n'})
rs("profils", "--profil", "s", "--copie", "t")
for m in ("Un", "Deux"):
    rs("bascule", "on", "--profil", "s", "--mod", "9_Code/" + m)
d = rs("scripts", "--profil", "s")
T = {(t["voie"], t["sorte"], t["cible"]): t for t in d["trouvailles"]}
qui = lambda t, i: t["lignes"][i]["prov"].split("/")[-1]
r = T.get(("redscript", "remplacement", "Foo.Bar(Int32, array<ref<X>>)"))
check("Redscript : deux @replaceMethod de corps différents sur la même cible (types normalisés), à regarder, dernier mot prévu au dernier fichier lu",
      bool(r) and r["niveau"] == "attention" and len(r["lignes"]) == 2 and qui(r, r["gagnant"]) == "Un.zip", str(sorted(T)))
check("Redscript : enveloppe qui n'appelle pas wrappedMethod = « coupe » ; @addMethod en double = « double » ; un commentaire ne compte pas",
      ("redscript", "coupe", "Foo.W()") in T and ("redscript", "double", "Foo.Neuf()") in T and not any("Commentaire" in k[2] for k in T), str(sorted(T)))
check("Redscript : @if(ModuleExists) évalué (module absent : déclaration écartée ; module présent : gardée, seule, donc rien à dire)",
      not any("Garde" in k[2] for k in T) and not any("@if" in l["quoi"] for l in d["limites"]), str(d["limites"]))
v = T.get(("tweak", "valeur", "Items.A.price"))
check("TweakXL : même propriété, deux valeurs = « valeur », dernier mot prévu au dernier fichier dans l'ordre des noms",
      bool(v) and v["niveau"] == "revoir" and qui(v, v["gagnant"]) == "Un.zip" and sorted(l["valeur"] for l in v["lignes"]) == ["10", "12"], str(v))
check("TweakXL : retrait contre ajout = « oppose », deux listes différentes = « liste », rien pour l'enregistrement d'un seul mod",
      ("tweak", "oppose", "Items.A.tags") in T and ("tweak", "liste", "Items.A.list") in T and not any("Items.B" in k[2] for k in T), str(sorted(T)))
c = T.get(("code", "code", "Items.C.v"))
check("SetFlat littéral du Lua de CET contre le tweak d'un autre mod, valeur différente ; la ligne en commentaire ne compte pas",
      bool(c) and sorted((l["geste"], l["valeur"]) for l in c["lignes"]) == [("=", "7"), ("SetFlat()", "5")], str(c))
check("limite dite : un YAML illisible est nommé, pas avalé ; les comptes suivent",
      any(l["fichier"] == "r6/tweaks/casse.yaml" and "tabulation" in l["quoi"] for l in d["limites"]) and d["lus"]["reds"] >= 2 and d["compte"]["attention"] == 1, str(d["limites"]))
check("rien n'est écrit dans le jeu par cette lecture, et le filtre par mod garde les trouvailles du mod",
      get("r6/scripts/un/a.reds") is None and len(rs("scripts", "--profil", "s", "--mod", "9_Code/Un")["trouvailles"]) == len(d["trouvailles"]))
shutil.rmtree(os.path.join(DEPOT, "9_Code"))
rs("profils", "--profil", "s", "--supprime")

# ---------------------------------------------------------------- 20. historique structuré et veille
print("20. historique (journal) et dossiers à veiller")
mkzip("9_Hist/Histo-4242-1-0-1700000000.zip", {A + "histo.archive": "h1"})
rs("profils", "--profil", "h", "--copie", "t")
avant_h = rs("journal")["total"]
rs("bascule", "on", "--profil", "h", "--mod", "9_Hist/Histo")
rs("applique", "--profil", "h", "--go")
j = rs("journal", "--mod", "histo")
e = j["entrees"][0] if j["entrees"] else {}
check("un « applique » qui écrit ajoute UNE entrée : date, profil, comptes, le mod « posé » avec sa version",
      j["total"] == avant_h + 1 and e.get("geste") == "applique" and e.get("profil") == "h" and e["compte"].get("pose") == 1
      and [(m["cle"], m["fait"], m["version"]) for m in e["mods"]] == [("9_Hist/Histo-4242-1-0-1700000000.zip", "posé", "1.0")], str(j)[:600])
rs("applique", "--profil", "h", "--go")
check("un « applique » qui n'écrit rien n'ajoute rien", rs("journal")["total"] == avant_h + 1)
os.remove(os.path.join(DEPOT, "9_Hist", "Histo-4242-1-0-1700000000.zip"))
mkzip("9_Hist/Histo-4242-1-1-1700000900.zip", {A + "histo.archive": "h2", A + "histo2.archive": "h3"})
rs("applique", "--profil", "h", "--go")
e = rs("journal", "--mod", "histo", "--limite", "1")["entrees"][0]
m = next((m for m in e["mods"] if "1-1-" in m["cle"]), {})
check("nouvelle version du zip : dite « mis à jour », depuis 1.0", m.get("fait") == "mis à jour" and m.get("depuis") == "1.0" and m.get("version") == "1.1", str(e))
rs("bascule", "off", "--profil", "h", "--mod", "9_Hist/Histo")
rs("applique", "--profil", "h", "--go")
e = rs("journal", "--limite", "1")["entrees"][0]
check("mod coupé puis appliqué : dit « retiré », et le jeu ne l'a plus",
      [m["fait"] for m in e["mods"]] == ["retiré"] and e["compte"].get("retire") == 2 and get(A + "histo.archive") is None, str(e))
rs("deplace", "--profil", "h", "--cle", "9_Hist/Histo-4242-1-1-1700000900.zip", "--vers", "parques", "--go")
g = rs("journal", "--geste", "parque")
check("geste sur le dépôt : parquer est à l'historique, filtrable par geste, par date et par mod",
      g["entrees"] and g["entrees"][0]["de"].endswith("Histo-4242-1-1-1700000900.zip") and g["trouve"] == len(g["entrees"])
      and rs("journal", "--depuis", "2999-01-01")["entrees"] == [] and rs("journal", "--mod", "aucun mod de ce nom")["entrees"] == []
      and len(rs("journal", "--mod", "histo")["entrees"]) == 4, str(g)[:400])
v = rs("config")["veille"]
check("veille : la racine du dépôt, chaque pile et ses dossiers de convention, archive/pc/mod du jeu, les profils ; aucun cache",
      any(os.path.normcase(d) == os.path.normcase(DEPOT) for d in v["dossiers"])
      and any(d.replace(os.sep, "/").endswith("9_Hist") for d in v["dossiers"]) and any(d.replace(os.sep, "/").endswith("archive/pc/mod") for d in v["dossiers"])
      and any(os.path.basename(d) == "profils" for d in v["dossiers"]) and len([d for d in v["dossiers"] if "9_Hist" in d]) == 2
      and [os.path.basename(f) for f in v["fichiers"]][0] == "config.json" and not any("index" in f or "cache_" in f for f in v["fichiers"]), str(v))
shutil.rmtree(os.path.join(DEPOT, "9_Hist"))
rs("profils", "--profil", "h", "--supprime")
conf = json.load(open(cp, encoding="utf-8"))
conf["jeu"] = jeu_du_banc
json.dump(conf, open(cp, "w", encoding="utf-8"))
c = plan_counts()
check("profil « t » intact après l'essai", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0 and get(A + "beta.archive") is None, str(c))

# ---------------------------------------------------------------- 21. magasin (liens, poids réel) et sauvegarde des réglages
print("21. sauvegarde et restauration des réglages, état du magasin")
CR = "bin/x64/plugins/cyber_engine_tweaks/mods/regle/"
mkzip("9_Sauve/Regle-5151-1-0-1700000000.zip", {A + "gros.archive": "g" * 5000, CR + "settings.json": "defaut", CR + "init.lua": "code"})
rs("profils", "--profil", "m", "--copie", "t")
rs("bascule", "on", "--profil", "m", "--mod", "9_Sauve/Regle")
rs("applique", "--profil", "m", "--go", "--vrai-jeu")
put(CR + "settings.json", "choisi")                 # le joueur règle le mod
put("r6/storages/regle/etat.json", "ecrit en jeu")  # fichier que le mod crée, livré par aucun zip
put("r6/cache/modded/final.redscripts", "cache")
put("r6/storages/regle/vide.json", "")
s = rs("sauvegarde", "--cree")
dans = lambda rel: os.path.isfile(os.path.join(s["cree"]["chemin"], rel.replace("/", os.sep)))
check("sauvegarde : le réglage livré puis changé et le fichier écrit en jeu sont copiés ; ni code, ni archive, ni cache, ni fichier vide",
      dans(CR + "settings.json") and dans("r6/storages/regle/etat.json") and not dans(CR + "init.lua") and not dans(A + "gros.archive")
      and not dans("r6/cache/modded/final.redscripts") and not dans("r6/storages/regle/vide.json") and s["cree"]["fichiers"] >= 2, str(s)[:400])
l = rs("sauvegarde")
check("la sauvegarde est listée, avec sa date, son nombre de fichiers et son poids",
      l["sauvegardes"][0]["nom"] == s["cree"]["nom"] and l["sauvegardes"][0]["octets"] > 0 and l["sauvegardes"][0]["cree"], str(l)[:300])
put(CR + "settings.json", "autre")
os.remove(os.path.join(JEU, "r6", "storages", "regle", "etat.json"))
d = rs("sauvegarde", "--restaure", "--nom", s["cree"]["nom"])
check("aperçu d'une restauration : un différent, un absent, rien d'écrit",
      [x.lower() for x in d["changes"]] == [CR + "settings.json"] and d["absents"] == ["r6/storages/regle/etat.json"]
      and d["restaure"] is False and get(CR + "settings.json") == "autre", str(d)[:400])
d = rs("sauvegarde", "--restaure", "--nom", s["cree"]["nom"], "--go", "--vrai-jeu")
check("restauration : les deux réglages reviennent, celui d'avant est copié dans les sauvegardes",
      d["restaure"] and get(CR + "settings.json") == "choisi" and get("r6/storages/regle/etat.json") == "ecrit en jeu"
      and open(os.path.join(d["copies"], "reglages", *CR.split("/")[:-1], "settings.json")).read() == "autre", str(d)[:400])
d = rs("sauvegarde", "--restaure", "--go", "--vrai-jeu")
check("relancée sans nom (la plus récente) : plus rien à remettre", d["restaure"] is False and not d["changes"] and not d["absents"], str(d)[:300])
check("sauvegarde inconnue : refusée", "inconnue" in str(rs("sauvegarde", "--restaure", "--nom", "_reglages_1999", ok=False)))
g = rs("journal", "--geste", "reglages")
check("historique : la sauvegarde et la restauration y sont", [e["sens"] for e in g["entrees"]] == ["restaure", "sauve"], str(g)[:300])
c = rs("plan", "--profil", "m")["compte"]
check("le plan ne veut rien défaire : le réglage restauré reste « modifié en jeu », gardé",
      c["pose"] == c["remplace"] == c["retire"] == 0 and c["garde_modifie"] >= 1, str(c))
if MAGASIN:
    g = rs("magasin", "--profil", "m")
    check("magasin : l'archive est liée (aucune place en plus), le réglage est copié ; poids réel = magasin + copies",
          g["jeu"]["lies"] >= 1 and g["jeu"]["octets_lies"] >= 5000 and g["jeu"]["reglages"] >= 1 and g["meme_disque"] is True
          and g["reel"] == g["octets"] + g["jeu"]["octets_copies"] and g["explorateur"] - g["reel"] == g["jeu"]["octets_lies"]
          and g["arbres"] >= 1 and g["fichiers"] >= 3 and g["libre"] > 0, str({k: v for k, v in g.items() if k != "sans_mod"}))
rs("bascule", "off", "--profil", "m", "--mod", "9_Sauve/Regle")
rs("applique", "--profil", "m", "--go", "--vrai-jeu")
if MAGASIN:
    g2 = rs("magasin", "--profil", "m")
    orphelin = next((x for x in g2["sans_mod"] if x["arbre"] == "9_Sauve/Regle-5151-1-0-1700000000"), None)
    check("mod coupé : son arbre est dit sans mod actif, avec son poids ; deux liens de moins dans le jeu (archive et code)",
          bool(orphelin) and orphelin["octets"] >= 5000 and orphelin["fichiers"] == 3 and g2["jeu"]["lies"] == g["jeu"]["lies"] - 2
          and g2["octets_sans_mod"] >= 5000, str((orphelin, g["jeu"], g2["jeu"])))
    pv = rs("purge", "--profil", "m")
    check("purge sans --go : dit le poids, ne supprime rien", pv["supprimes"] is False and pv["octets"] >= 5000 and os.path.isdir(orphelin["chemin"]), str(pv)[:200])
    rs("purge", "--profil", "m", "--go")
    check("purge : l'arbre part, le magasin ne le compte plus",
          not os.path.isdir(orphelin["chemin"]) and not rs("magasin", "--profil", "m")["sans_mod"])
else:
    check("sans magasin : la commande le dit", "sans objet" in str(rs("magasin", "--profil", "m", ok=False)))
shutil.rmtree(os.path.join(DEPOT, "9_Sauve"))
shutil.rmtree(os.path.join(JEU, "r6", "storages", "regle"))
os.remove(os.path.join(JEU, "r6", "cache", "modded", "final.redscripts"))
rs("profils", "--profil", "m", "--supprime")
c = plan_counts()
check("profil « t » intact après l'essai (21)", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

# ---------------------------------------------------------------- 22. Nexus : mises à jour proposées, téléchargées, rangées
print("22. Nexus : mises à jour (faux serveur local), clé, compte gratuit et Premium")
import http.server, io, re, threading, urllib.parse


def zip_octets(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
    return b.getvalue()


NEUFS = {11: zip_octets({A + "vieux.archive": "v2", A + "plus.archive": "p"}), 41: zip_octets({A + "retouche.archive": "r2"})}
fich = lambda fid, nom, ver, cat, date, taille=0: {"fileId": fid, "name": nom, "version": ver, "category": cat, "date": date,
                                                   "uri": f"{nom}-{fid}.zip", "sizeInBytes": taille}
NEXUS = {6001: [fich(10, "Vieux Mod", "1.0", "OLD_VERSION", 1700000100), fich(11, "Vieux Mod", "1.1", "MAIN", 1700009999, len(NEUFS[11])),
                fich(12, "Vieux Mod - Extra", "1.1", "OPTIONAL", 1700009998)],
         6002: [fich(20, "Stable", "2.0", "MAIN", 1700000200), fich(21, "Stable - 2.31", "2.0", "MAIN", 1700000299)],
         6003: [fich(30, "Rustine", "1.0", "OLD_VERSION", 1700000300), fich(31, "Rustine - 2.31", "1.1", "MAIN", 1700000399)],
         6004: [fich(40, "Retouche", "1.0", "MAIN", 1700000400), fich(41, "Retouche", "1.2", "MAIN", 1700008888, len(NEUFS[41]))],
         6005: [fich(50, "Archive", "1.0", "ARCHIVED", 1700000500), fich(51, "Autre Nom", "3.0", "MAIN", 1700007777),
                fich(52, "Encore Un", "3.0", "MAIN", 1700007778)]}
PREMIUM = [False]


class FauxNexus(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def rend(self, code, corps, genre="application/json"):
        corps = corps if isinstance(corps, bytes) else json.dumps(corps).encode()
        self.send_response(code)
        self.send_header("Content-Type", genre)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("x-rl-daily-remaining", "19990")
        self.send_header("x-rl-hourly-remaining", "500")
        self.end_headers()
        self.wfile.write(corps)

    def do_POST(self):
        q = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["query"]
        self.rend(200, {"data": {f"m{m}": NEXUS.get(int(m), []) for m in re.findall(r"m(\d+): modFiles", q)}})

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path.startswith("/cdn/"):
            return self.rend(200, NEUFS[int(u.path.split("/")[-1])], "application/zip")
        if self.headers.get("apikey") != "bonne" or self.headers.get("Application-Name") != "Red Stack":
            return self.rend(401, {"message": "Please provide a valid API Key"})
        if u.path == "/v1/users/validate.json":
            return self.rend(200, {"name": "Banc", "is_premium": PREMIUM[0]})
        m = re.match(r"/v1/games/cyberpunk2077/mods/(\d+)/files/(\d+)/download_link.json", u.path)
        q = urllib.parse.parse_qs(u.query)
        if not PREMIUM[0] and q.get("key") != ["cle-courte"]:
            return self.rend(403, {"message": "You don't have permission to get download links from the API without visiting nexusmods.com - this is for premium users only."})
        self.rend(200, [{"name": "Banc", "short_name": "banc", "URI": f"http://127.0.0.1:{PORT}/cdn/{m[2]}"}])


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FauxNexus)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["RED_STACK_NEXUS_URL"] = f"http://127.0.0.1:{PORT}"
os.environ.pop("RED_STACK_NEXUS_KEY", None)
M = "6_Maj/"
VIEUX, RETOUCHE = M + "Vieux Mod 1.0-6001-1-0-1700000100.zip", M + "Retouche-6004-1-0-1700000400  EDITED.zip"
mkzip(VIEUX, {A + "vieux.archive": "v1"})
mkzip(M + "Stable-6002-2-0-1700000200.zip", {A + "stable.archive": "s"})
mkzip(M + "Rustine-6003-1-0-1700000300.zip", {A + "rustine.archive": "r"})
mkzip(RETOUCHE, {A + "retouche.archive": "r1"})
mkzip(M + "Archive-6005-1-0-1700000500.zip", {A + "archive5.archive": "a"})
mkzip(M + "Libre.zip", {A + "libre.archive": "l"})
rs("profils", "--profil", "n", "--copie", "t")
rs("bascule", "on", "--profil", "n", "--mod", "6_Maj/Vieux Mod")
rs("applique", "--profil", "n", "--go", "--vrai-jeu")
nx = rs("nexus")
L = {r["cle"]: r for r in nx["lignes"]}
check("mise à jour proposée : même nom, version du nom choisi suivie, le fichier optionnel n'est pas pris pour elle",
      L[VIEUX]["statut"] == "maj" and L[VIEUX]["neuf"]["fichier"] == 11 and L[VIEUX]["propose"] == "Vieux Mod 1.1-6001-1-1-1700009999.zip", str(L.get(VIEUX)))
check("zip à jour malgré une variante plus récente pour un autre patch : compté, pas listé ; zip sans modId : non comparé",
      M + "Stable-6002-2-0-1700000200.zip" not in L and nx["a_jour"] >= 1 and any(x["cle"] == M + "Libre.zip" for x in nx["hors"]), str(nx["compte"]))
check("seul fichier vivant = build pour un autre patch du jeu : à voir, pas une mise à jour",
      L[M + "Rustine-6003-1-0-1700000300.zip"]["statut"] == "a_voir" and "2.31" in L[M + "Rustine-6003-1-0-1700000300.zip"]["raison"])
check("zip annoté : mise à jour proposée, avec l'avertissement", L[RETOUCHE]["statut"] == "maj" and "EDITED" in L[RETOUCHE]["raison"], str(L.get(RETOUCHE)))
ar = L[M + "Archive-6005-1-0-1700000500.zip"]
check("fichier archivé, deux fichiers principaux d'un autre nom : à voir, deux candidats",
      ar["statut"] == "a_voir" and [c["fichier"] for c in ar["candidats"]] == [52, 51], str(ar))
rs("nexus", "on", "--cle", RETOUCHE, "--ignore")
ig = {r["cle"]: r["ignore"] for r in rs("nexus")["lignes"]}
rs("nexus", "off", "--cle", RETOUCHE, "--ignore")
check("ignorer un mod puis le reprendre", ig[RETOUCHE] is True and ig[VIEUX] is False
      and not {r["cle"]: r["ignore"] for r in rs("nexus")["lignes"]}[RETOUCHE])
check("sans clé d'API : le compte le dit, le téléchargement refuse, rien écrit",
      rs("nexus", "--compte") == {"cle": False} and "aucune clé" in rs("nexus", "--cle", VIEUX, "--go")["erreur"]
      and os.path.isfile(os.path.join(DEPOT, VIEUX)))
os.environ["RED_STACK_NEXUS_KEY"] = "fausse"
check("clé refusée par Nexus : dite, rien écrit", "refusée" in rs("nexus", "--compte")["erreur"] and "refusée" in rs("nexus", "--cle", VIEUX, "--go")["erreur"])
os.environ["RED_STACK_NEXUS_KEY"] = "bonne"
c = rs("nexus", "--compte")
check("compte lu : nom, gratuit, appels restants", c["nom"] == "Banc" and c["premium"] is False and c["reste_jour"] == 19990, str(c))
r = rs("nexus", "--cle", VIEUX, "--go")
check("compte gratuit sans lien : la page du fichier est rendue, rien écrit",
      r["besoin_lien"] and not r["ecrit"] and "file_id=11" in r["page"] and os.path.isfile(os.path.join(DEPOT, VIEUX)), str(r))
r = rs("nexus", "--cle", VIEUX, "--lien", "nxm://cyberpunk2077/mods/9999/files/11?key=cle-courte&expires=1", "--go", ok=False)
check("lien d'un autre mod : refusé", "n'est pas celui du mod" in str(r), str(r)[:200])
r = rs("nexus", "--cle", VIEUX, "--lien", "nxm://cyberpunk2077/mods/6001/files/11?key=cle-courte&expires=1&user_id=5", "--go")
NEUF = M + "Vieux Mod 1.1-6001-1-1-1700009999.zip"
check("compte gratuit avec le lien nxm : nouvelle version à la place, l'ancienne dans les retirés de la convention",
      r["ecrit"] and r["fichiers"] == 2 and os.path.isfile(os.path.join(DEPOT, NEUF)) and not os.path.exists(os.path.join(DEPOT, VIEUX))
      and os.path.isfile(os.path.join(DEPOT, "6_Maj", "Corbeille", os.path.basename(VIEUX)))
      and not [f for f in os.listdir(os.path.join(DEPOT, "6_Maj")) if f.endswith(".part")], str(r))
c = rs("plan", "--profil", "n")["compte"]
check("le profil suit la nouvelle version : un fichier à remplacer, un à poser", c["remplace"] == 1 and c["pose"] == 1 and c["retire"] == 0, str(c))
rs("applique", "--profil", "n", "--go", "--vrai-jeu")
check("appliqué : le jeu porte la nouvelle version", get(A + "vieux.archive") == "v2" and get(A + "plus.archive") == "p")
check("relu : ce zip est à jour, l'ancienne version rangée n'est pas reproposée", not [r for r in rs("nexus")["lignes"] if r["mod"] == 6001])
PREMIUM[0] = True
r = rs("nexus", "--cle", RETOUCHE, "--nom", "Retouche neuve-6004-1-2-1700008888.zip", "--go")
check("compte Premium : lien direct, nom retouché par l'utilisateur", r["ecrit"] and r["compte"]["premium"]
      and os.path.isfile(os.path.join(DEPOT, "6_Maj", "Retouche neuve-6004-1-2-1700008888.zip")), str(r))
r = rs("nexus", "--cle", M + "Archive-6005-1-0-1700000500.zip", "--fichier", "51")
check("ligne « à voir » : le fichier choisi est pris, son nom proposé (sans --go, rien écrit)",
      not r["ecrit"] and r["neuf"]["fichier"] == 51 and r["vers"].endswith("Archive-6005-3-0-1700007777.zip"), str(r))
j = rs("journal", "--geste", "maj")
check("historique : les deux mises à jour, version d'avant et d'après", j["trouve"] == 2 and j["entrees"][-1]["depuis"] == "1.0" and j["entrees"][-1]["version"] == "1.1", str(j)[:300])

# lien nxm reçu du site sans zip désigné, mod nouveau, arrivage téléchargé à la main
print("24. lien nxm reçu : zip visé, mod nouveau dans les arrivages ; arrivage = mise à jour d'un zip en place")
PREMIUM[0] = False
NEUFS.update({62: zip_octets({A + "suivi.archive": "s2"}), 71: zip_octets({A + "inconnu.archive": "i"})})
NEXUS[6006] = [fich(60, "Suivi", "1.0", "MAIN", 1700000600), fich(61, "Suivi - Addon", "1.0", "OPTIONAL", 1700000601),
               fich(62, "Suivi", "2.0", "MAIN", 1700006000, len(NEUFS[62]))]
NEXUS[6007] = [dict(fich(71, "Inconnu", "0.9", "MAIN", 1700007000, len(NEUFS[71])), uri="Inconnu au bataillon-6007-0-9-1700007000.zip")]
SUIVI, ADDON = M + "Mon Suivi-6006-1-0-1700000600.zip", M + "Suivi Addon-6006-1-0-1700000601.zip"
mkzip(SUIVI, {A + "suivi.archive": "s1"})
mkzip(ADDON, {A + "addon.archive": "a"})
r = rs("nexus", "--lien", "nxm://skyrim/mods/6006/files/62?key=cle-courte&expires=1", ok=False)
check("lien d'un autre jeu : refusé", "autre jeu" in str(r), str(r)[:200])
r = rs("nexus", "--lien", "nxm://cyberpunk2077/mods/6006/files/62?key=cle-courte&expires=1")
check("lien reçu : le zip qu'il met à jour d'abord (sûr, nom choisi gardé), l'addon du même mod ensuite (pas sûr)",
      [c["cle"] for c in r["cibles"]] == [SUIVI, ADDON] and r["cibles"][0]["sur"] and not r["cibles"][1]["sur"]
      and r["cibles"][0]["propose"] == "Mon Suivi-6006-2-0-1700006000.zip" and r["fichier"]["fichier"] == 62 and not r["deja"], str(r))
r = rs("nexus", "--cle", SUIVI, "--lien", "nxm://cyberpunk2077/mods/6006/files/62?key=cle-courte&expires=1", "--go")
check("lien reçu puis rangé à la place du zip visé", r["ecrit"] and os.path.isfile(os.path.join(DEPOT, M + "Mon Suivi-6006-2-0-1700006000.zip"))
      and os.path.isfile(os.path.join(DEPOT, "6_Maj", "Corbeille", os.path.basename(SUIVI))), str(r))
r = rs("nexus", "--lien", "nxm://cyberpunk2077/mods/6006/files/62?key=cle-courte&expires=1")
check("le même lien une seconde fois : déjà dans le dépôt, plus aucun zip à mettre à jour par lui",
      r["deja"] == M + "Mon Suivi-6006-2-0-1700006000.zip" and not [c for c in r["cibles"] if c["sur"]], str(r))
r = rs("nexus", "--lien", "nxm://cyberpunk2077/mods/6007/files/71?key=cle-courte&expires=1")
check("mod que le dépôt n'a pas : aucune cible, les piles sont proposées", r["cibles"] == [] and "6_Maj" in r["piles"], str(r))
r = rs("nexus", "--lien", "nxm://cyberpunk2077/mods/6007/files/71?key=cle-courte&expires=1", "--section", "6_Maj")
ARRIVE = os.path.join(DEPOT, "6_Maj", "Arrivages", "Inconnu au bataillon-6007-0-9-1700007000.zip")
check("mod nouveau, sans --go : le dossier d'arrivée de la pile et le nom du site, rien écrit",
      not r["ecrit"] and os.path.normcase(r["vers"]) == os.path.normcase(ARRIVE) and not os.path.exists(ARRIVE), str(r))
r = rs("nexus", "--lien", "nxm://cyberpunk2077/mods/6007/files/71", "--section", "6_Maj", "--go")
check("compte gratuit, lien sans `key` : refusé proprement, rien écrit", r["besoin_lien"] and not r["ecrit"] and not os.path.exists(ARRIVE), str(r))
r = rs("nexus", "--lien", "nxm://cyberpunk2077/mods/6007/files/71?key=cle-courte&expires=1", "--section", "6_Maj", "--go")
check("mod nouveau téléchargé dans les arrivages, vu « nouveau » par l'index, noté à l'historique",
      r["ecrit"] and r["fichiers"] == 1 and os.path.isfile(ARRIVE) and rs("journal", "--geste", "arrive")["trouve"] == 1
      and any(x["cle"] == "6_Maj/Arrivages/" + os.path.basename(ARRIVE) for x in rs("convention")["lignes"]), str(r))
os.environ.pop("RED_STACK_NEXUS_KEY")               # sans clé du tout : le zip est téléchargé à la main dans un dossier d'arrivée
NEXUS[6001].append(fich(13, "Vieux Mod", "1.2", "MAIN", 1700019999))
NEXUS[6006].append(fich(63, "Suivi - Addon", "1.1", "OPTIONAL", 1700016001))
MAIN_A, MAIN_B = "6_Maj/Arrivages/Vieux Mod-6001-1-2-1700019999.zip", "6_Maj/Arrivages/Suivi - Addon-6006-1-1-1700016001  EDITED.zip"
mkzip(MAIN_A, {A + "vieux.archive": "v3"})
mkzip(MAIN_B, {A + "addon.archive": "a2"})
cv = {x["cle"]: x for x in rs("convention", "--force")["lignes"]}
check("arrivage d'un mod en place : reconnu comme sa mise à jour, nom choisi et version du nom suivis",
      [(c["cle"], c["sur"], c["propose"]) for c in cv[MAIN_A]["maj_de"]] == [(NEUF, True, "Vieux Mod 1.2-6001-1-2-1700019999.zip")], str(cv[MAIN_A]))
check("deux zips du même mod en place : l'addon d'abord (même fichier sur Nexus), l'annotation de l'arrivage gardée ; mod nouveau : aucune",
      cv[MAIN_B]["maj_de"][0]["cle"] == ADDON and cv[MAIN_B]["maj_de"][0]["sur"] and cv[MAIN_B]["maj_de"][0]["propose"] == "Suivi Addon-6006-1-1-1700016001  EDITED.zip"
      and not cv[MAIN_B]["maj_de"][1]["sur"] and cv["6_Maj/Arrivages/" + os.path.basename(ARRIVE)]["maj_de"] == [], str(cv[MAIN_B]))
r = rs("convention", "--range", "--cle", MAIN_A, "--de", ADDON, ok=False)
check("ranger à la place d'un zip d'un autre mod : refusé", "pas sa mise à jour" in str(r), str(r)[:200])
r = rs("convention", "--range", "--cle", MAIN_A, "--de", NEUF)
check("ranger, sans --go : la cible et le dossier des retirés, rien écrit", not r["ecrit"] and r["vers"].endswith("Vieux Mod 1.2-6001-1-2-1700019999.zip")
      and os.path.isfile(os.path.join(DEPOT, MAIN_A)) and os.path.isfile(os.path.join(DEPOT, NEUF)), str(r))
r = rs("convention", "--range", "--cle", MAIN_A, "--de", NEUF, "--go")
check("rangé sans clé d'API : l'arrivage à la place, l'ancienne dans les retirés, le profil suit (un fichier à remplacer)",
      r["ecrit"] and os.path.isfile(os.path.join(DEPOT, M + "Vieux Mod 1.2-6001-1-2-1700019999.zip")) and not os.path.exists(os.path.join(DEPOT, MAIN_A))
      and os.path.isfile(os.path.join(DEPOT, "6_Maj", "Corbeille", os.path.basename(NEUF))) and rs("plan", "--profil", "n")["compte"]["remplace"] == 1, str(r))
r = rs("convention", "--range", "--cle", MAIN_B, "--de", ADDON, "--nom", cv[MAIN_B]["maj_de"][0]["propose"], "--go")
j = rs("journal", "--geste", "maj")
check("rangé au nom proposé par la liste ; historique : arrivage, version d'avant et d'après",
      r["ecrit"] and os.path.isfile(os.path.join(DEPOT, M + "Suivi Addon-6006-1-1-1700016001  EDITED.zip"))
      and j["entrees"][0]["depuis"] == "1.0" and j["entrees"][0]["version"] == "1.1" and j["entrees"][0]["arrivage"].endswith("EDITED.zip"), str(j)[:300])
# mod sans modId (maison, GitHub) : reconnu par son nom et sa version, espaces et casse à part
mkzip(M + "Mon Outil 1.0.0.zip", {"r6/scripts/MonOutil/a.reds": "v1"})
LOC, VIEUX = "6_Maj/Arrivages/MonOutil 1.0.1.zip", "6_Maj/Arrivages/Mon Outil 0.9.zip"
mkzip(LOC, {"r6/scripts/MonOutil/a.reds": "v2"})
mkzip(VIEUX, {"r6/scripts/MonOutil/a.reds": "v0"})
cv = {x["cle"]: x for x in rs("convention")["lignes"]}
check("arrivage sans modId : mise à jour du zip de même nom et de version plus basse, son nom gardé ; une version plus vieille n'en est pas une",
      [(c["cle"], c["version"], c["sur"], c["propose"]) for c in cv[LOC].get("maj_de", [])] == [(M + "Mon Outil 1.0.0.zip", "1.0.0", True, "MonOutil 1.0.1.zip")]
      and not cv[VIEUX].get("maj_de"), str(cv[LOC]))
r = rs("convention", "--range", "--cle", VIEUX, "--de", M + "Mon Outil 1.0.0.zip", ok=False)
check("ranger une version plus vieille à sa place : refusé", "modId" in r, r)
r = rs("convention", "--range", "--cle", LOC, "--de", M + "Mon Outil 1.0.0.zip", "--go")
j = rs("journal", "--geste", "maj")
check("rangé : le nouveau zip à la racine de la pile, l'ancien dans les retirés, versions à l'historique",
      r["ecrit"] and os.path.isfile(os.path.join(DEPOT, M + "MonOutil 1.0.1.zip")) and not os.path.exists(os.path.join(DEPOT, M + "Mon Outil 1.0.0.zip"))
      and os.path.isfile(r["ancienne_vers"]) and j["entrees"][0]["depuis"] == "1.0.0" and j["entrees"][0]["version"] == "1.0.1", str(r))
# zip désigné par l'utilisateur : ni nom ni version comparés (ici la version « plus vieille », refusée plus haut)
r = rs("convention", "--range", "--designe", "--cle", VIEUX, "--de", M + "MonOutil 1.0.1.zip")
check("zip désigné à la main, sans --go : accepté, l'arrivage garde son nom, rien écrit",
      not r["ecrit"] and r["vers"].endswith("Mon Outil 0.9.zip") and os.path.isfile(os.path.join(DEPOT, VIEUX)), str(r))
r2 = rs("convention", "--range", "--designe", "--cle", VIEUX, "--de", M + "MonOutil 1.0.1.zip", "--nom", "Mon Outil 0.9 RETOUR.zip", "--go")
check("zip désigné à la main, nom retouché : rangé à la racine de la pile, le remplacé dans les retirés",
      r2["ecrit"] and os.path.isfile(os.path.join(DEPOT, M + "Mon Outil 0.9 RETOUR.zip")) and os.path.isfile(r2["ancienne_vers"])
      and not os.path.exists(os.path.join(DEPOT, M + "MonOutil 1.0.1.zip")), str(r2))
for f in (os.path.join(DEPOT, M + "Mon Outil 0.9 RETOUR.zip"), r["ancienne_vers"] if False else r2["ancienne_vers"]):
    os.remove(f)
ANC = [os.path.join(os.path.dirname(r2["ancienne_vers"]), "Mon Outil 1.0.0.zip")]
for f in ANC:
    if os.path.isfile(f):
        os.remove(f)
mkzip(M + "Chargeur.zip", {"bin/x64/plugins/cyber_engine_tweaks.asi": "x", "r6/scripts/Lib/lib.reds": "module Lib", "LISEZMOI.txt": "x"})
nat = {x["cle"]: x["natures"] for x in rs("etat", "--profil", "n")["mods"]}
check("nature d'un mod lue dans ce que son zip pose : archive ; chargeur = socle, scripts, greffon .asi ; un fichier non posable ne compte pas",
      nat[ADDON.replace("1-0-1700000601", "1-1-1700016001  EDITED")] == ["archive"] and nat[M + "Chargeur.zip"] == ["socle", "reds", "asi"], str(nat.get(M + "Chargeur.zip")))
os.environ["RED_STACK_NEXUS_KEY"] = "bonne"
srv.shutdown()
os.environ.pop("RED_STACK_NEXUS_URL")
os.environ.pop("RED_STACK_NEXUS_KEY")
rs("bascule", "off", "--profil", "n", "--mod", "6_Maj/Vieux Mod")
rs("applique", "--profil", "n", "--go", "--vrai-jeu")
shutil.rmtree(os.path.join(DEPOT, "6_Maj"))
os.remove(os.path.join(DONNEES, "nexus.json"))
rs("profils", "--profil", "n", "--supprime")
c = plan_counts()
check("profil « t » intact après l'essai (22)", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

# ---------------------------------------------------------------- 23. FOMOD : installateur lu, choix au profil ; version d'un REDmod
print("23. FOMOD (pages, drapeaux, fichiers conditionnels) et version lue dans info.json")
FO = """<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <moduleName>Voiture</moduleName>
 <requiredInstallFiles><folder source="base" destination="" priority="0"/></requiredInstallFiles>
 <installSteps order="Explicit">
  <installStep name="Mode"><optionalFileGroups><group name="Mode" type="SelectExactlyOne"><plugins>
   <plugin name="Simple"><description>Sans pieces.</description><image path="fomod\\img.png"/>
    <conditionFlags><flag name="TUNING">Off</flag></conditionFlags><typeDescriptor><type name="Recommended"/></typeDescriptor></plugin>
   <plugin name="Complet"><description>Avec pieces.</description>
    <conditionFlags><flag name="TUNING">On</flag></conditionFlags><typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
  </plugins></group></optionalFileGroups></installStep>
  <installStep name="Pieces"><visible><dependencies operator="And"><flagDependency flag="TUNING" value="On"/></dependencies></visible>
   <optionalFileGroups>
    <group name="Couleur" type="SelectExactlyOne"><plugins>
     <plugin name="Rouge"><files><file source="couleurs\\rouge.xl" destination="archive\\pc\\mod\\voiture_couleur.xl"/></files>
      <typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
     <plugin name="Bleu"><files><file source="couleurs\\bleu.xl" destination="archive\\pc\\mod\\voiture_couleur.xl"/></files>
      <typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
    </plugins></group>
    <group name="Extras" type="SelectAny"><plugins>
     <plugin name="Aileron"><files><file source="extras\\aileron.archive" destination="archive\\pc\\mod\\"/></files>
      <typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
     <plugin name="Notice"><conditionFlags><flag name="DOCS">On</flag></conditionFlags>
      <typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
     <plugin name="Interdit"><files><file source="extras\\interdit.archive" destination="archive\\pc\\mod\\interdit.archive"/></files>
      <typeDescriptor><type name="NotUsable"/></typeDescriptor></plugin>
    </plugins></group>
   </optionalFileGroups></installStep>
 </installSteps>
 <conditionalFileInstalls><patterns>
  <pattern><dependencies><flagDependency flag="DOCS" value="On"/></dependencies>
   <files><folder source="docs" destination="Voiture Docs"/></files></pattern>
  <pattern><dependencies operator="Or"><flagDependency flag="TUNING" value="On"/><flagDependency flag="TUNING" value="Jamais"/></dependencies>
   <files><file source="preset\\sport.yaml" destination="r6\\tweaks\\voiture\\preset.yaml"/><file source="absent.txt" destination="absent.txt"/></files></pattern>
 </patterns></conditionalFileInstalls>
</config>"""
V = "7_Fomod/Voiture FOMOD-7001-1-0-1700000100.zip"
mkzip(V, {"fomod/ModuleConfig.xml": FO.encode("utf-16"), "fomod/img.png": b"\x89PNG", "base/" + A + "voiture.archive": "v",
          "couleurs/rouge.xl": "rouge", "couleurs/bleu.xl": "bleu", "extras/aileron.archive": "ail",
          "extras/interdit.archive": "non", "docs/notice.txt": "lire", "docs/plans/p.txt": "plan", "preset/sport.yaml": "sport"})
mkzip("7_Fomod/Casse.zip", {"fomod/ModuleConfig.xml": "<config><pas fermé", A + "casse.archive": "c"})
mkzip("7_Fomod/Son Mod.zip", {"mods/Son/info.json": '{"name": "Son Nom", "version": "2.3"}', "mods/Son/customSounds/a.wav": "w"})
CM, CC, CE = "Mode › Mode", "Pieces › Couleur", "Pieces › Extras"
f = rs("fomod", "--profil", "t", "--cle", V)
pg = f["pages"]
check("installateur lu (UTF-16) : deux pages, la seconde cachée, le choix recommandé pris, une source absente dite",
      f["module"] == "Voiture" and f["par_fomod"] and len(pg) == 2 and pg[0]["visible"] and not pg[1]["visible"]
      and f["choix"] == {CM: ["Simple"]} and f["compte"]["poses"] == 1 and any("absent.txt" in l for l in f["limites"]), str(f)[:400])
e = {r["nom"]: r for r in rs("etat", "--profil", "t")["mods"]}
check("état : le zip dit son installateur ; XML illisible = pack à piocher, erreur dite ; version du REDmod lue dans info.json",
      e["Voiture FOMOD-7001-1-0-1700000100.zip"]["fomod"]["actif"] and e["Casse.zip"]["fomod"]["erreur"]
      and e["Son Mod.zip"]["version"] == "2.3" and e["Son Mod.zip"]["fomod"] is None, str(e["Casse.zip"]))
img = rs("fomod", "--profil", "t", "--cle", V, "--entree", "fomod/img.png")
check("image d'un choix rendue pour la page", img["image"].startswith("data:image/png;base64,"), str(img)[:80])
rs("bascule", "on", "--profil", "t", "--mod", "7_Fomod/Voiture")
c = plan_counts()
check("coché sans rien régler : les choix par défaut, un fichier à poser", c["pose"] == 1 and c["conflit"] == 0, str(c))
r = rs("fomod", "--profil", "t", "--mod", "7_Fomod/Voiture", "--fixe", json.dumps({"choix": {CM: ["Tout"]}}), ok=False)
check("choix inconnu : refusé", "inconnu" in str(r), str(r)[:200])
f = rs("fomod", "--profil", "t", "--mod", "7_Fomod/Voiture", "--fixe",
       json.dumps({"choix": {CM: ["Complet"], CC: ["Rouge", "Bleu"], CE: ["Aileron", "Notice", "Interdit"]}}))
dests = sorted(x["dest"] for x in f["fichiers"])
check("choix notés : page révélée, choix unique ramené au premier demandé, choix interdit écarté, fichiers conditionnels pris",
      f["fait"] and f["pages"][1]["visible"] and f["choix"] == {CM: ["Complet"], CC: ["Rouge"], CE: ["Aileron", "Notice"]}
      and dests == ["Voiture Docs/notice.txt", "Voiture Docs/plans/p.txt", A + "aileron.archive", A + "voiture.archive",
                    A + "voiture_couleur.xl", "r6/tweaks/voiture/preset.yaml"] and f["compte"]["hors_jeu"] == 2, str(dests) + str(f["choix"]))
rs("fomod", "--profil", "t", "--mod", "7_Fomod/Voiture", "--fixe", json.dumps({"choix": {CC: ["Bleu"]}}))
c = plan_counts()
check("plan : six fichiers à poser", c["pose"] == 6 and c["retire"] == 0, str(c))
rs("applique", "--profil", "t", "--go", "--vrai-jeu")
check("appliqué : destinations de l'installateur, dossier hors du jeu compris",
      get(A + "voiture_couleur.xl") == "bleu" and get(A + "aileron.archive") == "ail" and get("r6/tweaks/voiture/preset.yaml") == "sport"
      and get("Voiture Docs/plans/p.txt") == "plan" and get(A + "interdit.archive") is None and get(A + "voiture.archive") == "v")
d = rs("detail", "--profil", "t", "--mod", "7_Fomod/Voiture")
pris = {r["entree"]: r["dest"] for r in d["entrees"] if r["pris"]}
check("détail : les entrées prises et leur destination viennent de l'installateur",
      d["fomod"]["actif"] and pris.get("couleurs/bleu.xl") == A + "voiture_couleur.xl" and "couleurs/rouge.xl" not in pris
      and "fomod/img.png" not in pris, str(pris))
r = rs("option", "off", "--profil", "t", "--mod", "7_Fomod/Voiture", "--nom", "couleurs", ok=False)
check("option à la main refusée tant que l'installateur pose", "installateur" in str(r), str(r)[:200])
rs("fomod", "--profil", "t", "--mod", "7_Fomod/Voiture", "--fixe", json.dumps({"choix": {CC: ["Rouge"]}, "hors_jeu": False}))
c = plan_counts()
check("autre couleur, sans les fichiers hors du jeu : un remplacé, deux retirés", c["remplace"] == 1 and c["retire"] == 2 and c["pose"] == 0, str(c))
rs("applique", "--profil", "t", "--go", "--vrai-jeu")
check("appliqué : couleur changée, dossier hors du jeu retiré", get(A + "voiture_couleur.xl") == "rouge" and get("Voiture Docs/notice.txt") is None)
f = rs("fomod", "--profil", "t", "--mod", "7_Fomod/Voiture", "--fixe", json.dumps({"choix": {CM: ["Simple"]}}))
c = plan_counts()
check("retour au mode simple : la page se cache, ses fichiers sortent, ses choix restent au profil",
      not f["pages"][1]["visible"] and c["retire"] == 3 and c["pose"] == 0
      and json.load(open(os.path.join(DONNEES, "profils", "t.json"), encoding="utf-8"))["mods"][V]["fomod"]["choix"][CC] == ["Rouge"], str(c))
f = rs("fomod", "--profil", "t", "--mod", "7_Fomod/Voiture", "--fixe", json.dumps({"libre": True}))
rs("option", "on", "--profil", "t", "--mod", "7_Fomod/Voiture", "--nom", "extras")
d = rs("detail", "--profil", "t", "--mod", "7_Fomod/Voiture")
check("rendu « pack à piocher » : l'installateur est ignoré, les dossiers se cochent comme avant",
      f["libre"] and not f["par_fomod"] and not d["fomod"]["actif"]
      and sorted(r["entree"] for r in d["entrees"] if r["pris"]) == ["extras/aileron.archive", "extras/interdit.archive"], str(d["sel"]))
f = rs("fomod", "--profil", "t", "--mod", "7_Fomod/Voiture", "--fixe", json.dumps({"libre": False, "choix": {CM: ["Complet"]}}))
check("installateur repris : les choix d'avant reviennent", f["par_fomod"] and f["choix"][CC] == ["Rouge"] and f["choix"][CE] == ["Aileron", "Notice"], str(f["choix"]))
r = rs("fomod", "--profil", "t", "--cle", "5_World/__RAM/Parked-3004-1-0-1700000007.zip")
check("zip sans installateur : dit", r["fomod"] is False, str(r))
d = rs("detail", "--profil", "t", "--mod", "5_World/__RAM/Parked-3004-1-0-1700000007.zip")
check("détail d'un zip parqué, désigné par sa clé entière : lu, pas actif", d["cle"].endswith("Parked-3004-1-0-1700000007.zip") and not d["actif"], str(d)[:200])
rs("bascule", "off", "--profil", "t", "--mod", "7_Fomod/Voiture")
rs("applique", "--profil", "t", "--go", "--vrai-jeu")
check("coupé et appliqué : plus rien de lui dans le jeu", get(A + "voiture.archive") is None and get(A + "voiture_couleur.xl") is None)
shutil.rmtree(os.path.join(DEPOT, "7_Fomod"))
c = plan_counts()
check("profil « t » intact après l'essai (23)", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

print("25. fichier présent, pas posé par l'outil : remplacé par le zip sur désignation (--remplace)")
MAIN = "8_Main/A La Main 1.0.0.zip"
base25 = plan_counts()["inconnu"]
put(A + "main_a.archive", "vieux")
put(A + "main_b.archive", "b")
mkzip(MAIN, {A + "main_a.archive": "neuf", A + "main_b.archive": "b"})
rs("bascule", "on", "--profil", "t", "--mod", MAIN)
p = rs("plan", "--profil", "t")
check("mod posé à la main : le fichier identique est repris, l'autre est « présent, pas posé », laissé",
      p["compte"]["inconnu"] == base25 + 1 and any(r["dest"] == A + "main_a.archive" for r in p["inconnu"]) and p["compte"]["remplace"] == 0, str(p["compte"]))
p2 = rs("plan", "--profil", "t", "--remplace", A + "main_a.archive")
check("--remplace : ce fichier passe dans « à remplacer », marqué, avec copie de sauvegarde ; les modifiés en jeu restent gardés",
      p2["compte"]["inconnu"] == base25 and p2["compte"]["remplace"] == 1 and p2["remplace"][0].get("force") and p2["remplace"][0].get("sauve")
      and p2["compte"]["garde_modifie"] == p["compte"]["garde_modifie"] and p2["empreinte"] != p["empreinte"], str(p2["compte"]))
r = rs("applique", "--profil", "t", "--go", "--si-plan", p["empreinte"], "--remplace", A + "main_a.archive", "--vrai-jeu", ok=False)
check("appliquer avec l'empreinte du plan d'avant la désignation : refusé", isinstance(r, str) and "changé" in r and get(A + "main_a.archive") == "vieux", str(r)[:200])
rs("applique", "--profil", "t", "--go", "--si-plan", p2["empreinte"], "--remplace", A + "main_a.archive", "--vrai-jeu")
c = plan_counts()
check("appliqué : le jeu porte le fichier du zip, plus rien à écrire ni d'inconnu",
      get(A + "main_a.archive") == "neuf" and c["inconnu"] == base25 and c["remplace"] == c["pose"] == 0, str(c))
rs("bascule", "off", "--profil", "t", "--mod", MAIN)
rs("applique", "--profil", "t", "--go", "--vrai-jeu")
shutil.rmtree(os.path.join(DEPOT, "8_Main"))
c = plan_counts()
check("profil « t » intact après l'essai (25)", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

print("26. dépôt hors convention : zips à la racine du dépôt (pile de la racine), dossiers que la convention ne lit pas")
RAC = "(racine)"
e = rs("config")["ecarts"]
check("dépôt à la convention : pas de pile de la racine, aucun écart dit",
      RAC not in rs("etat", "--profil", "t")["sections"] and e["hors_piles"] == [] and e["profonds"] == [] and e["piles"] > 0, str(e))
mkzip("En Vrac-9001-1-0-1700000026.zip", {A + "vrac.archive": "v1"})
mkzip("Arrivages/Arrive-9002-1-0-1700000027.zip", {A + "arrive.archive": "ar"})
mkzip("Libre/Hors Pile.zip", {A + "hors.archive": "h"})
mkzip("5_World/Sous Dossier/Profond.zip", {A + "profond.archive": "p"})
et = rs("etat", "--profil", "t")
vus = {m["cle"]: m for m in et["mods"]}
check("zip à la racine du dépôt : lu dans la pile de la racine, la dernière ; dossier d'arrivée de la racine lu aussi",
      et["sections"][-1] == RAC and RAC + "/En Vrac-9001-1-0-1700000026.zip" in vus
      and vus.get(RAC + "/Arrivages/Arrive-9002-1-0-1700000027.zip", {}).get("genre") == "nouveau", str(et["sections"]))
check("une pile ne devient pas un dossier de la racine, et rien d'autre n'a changé de clé",
      not any(k.startswith(RAC + "/5_World") for k in vus) and any(k.startswith("5_World/") for k in vus), str(sorted(vus))[:300])
e = rs("config")["ecarts"]
check("écarts dits : dossier de la racine hors motif des piles, sous-dossier de pile hors convention",
      e["hors_piles"] == [{"dossier": "Libre", "archives": 1}] and e["profonds"] == [{"dossier": "5_World/Sous Dossier", "archives": 1}], str(e))
VRAC = RAC + "/En Vrac-9001-1-0-1700000026.zip"
rs("bascule", "on", "--profil", "t", "--mod", VRAC)
rs("applique", "--profil", "t", "--go", "--vrai-jeu")
d = rs("detail", "--profil", "t", "--mod", VRAC)
check("posé depuis la racine : dans le jeu" + (", arbre du magasin sous « (racine) »" if MAGASIN else ""),
      get(A + "vrac.archive") == "v1" and (not MAGASIN or (d["arbre"] or "").startswith(os.path.join(STORE, RAC) + os.sep)), str(d.get("arbre")))
if MAGASIN:
    m = rs("magasin", "--profil", "t")
    check("magasin : l'arbre de la racine est tenu par son mod (la purge ne le prendrait pas)",
          not any(RAC in str(x) for x in m.get("sans_mod", [])), str(m.get("sans_mod"))[:200])
r = rs("deplace", "--cle", RAC + "/Arrivages/Arrive-9002-1-0-1700000027.zip", "--vers", "pile", "--go")
check("arrivage de la racine remonté : le zip est à la racine du dépôt", os.path.isfile(os.path.join(DEPOT, "Arrive-9002-1-0-1700000027.zip")), str(r)[:200])
rs("bascule", "off", "--profil", "t", "--mod", VRAC)
rs("applique", "--profil", "t", "--go", "--vrai-jeu")
r = rs("deplace", "--cle", VRAC, "--vers", "parques", "--go")
check("zip de la racine coupé, sorti du jeu, parqué : dossier des parqués créé à la racine du dépôt",
      get(A + "vrac.archive") is None and os.path.isfile(os.path.join(DEPOT, "__RAM", "En Vrac-9001-1-0-1700000026.zip")), str(r)[:200])
r = rs("deplace", "--cle", "5_World/Sous Dossier/Profond.zip", "--vers", "pile", "--go", ok=False)
check("clé d'un sous-dossier hors convention : refusée", isinstance(r, str), str(r)[:120])
for x in ("__RAM", "Arrivages", "Libre", os.path.join("5_World", "Sous Dossier")):
    shutil.rmtree(os.path.join(DEPOT, x), ignore_errors=True)
os.remove(os.path.join(DEPOT, "Arrive-9002-1-0-1700000027.zip"))
et = rs("etat", "--profil", "t")
c = plan_counts()
check("racine vidée : la pile de la racine disparaît, profil « t » intact (26)",
      RAC not in et["sections"] and c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

# ---------------------------------------------------------------- 27. mode texte (sans --json) : propositions entières, séparateur de la langue
def texte(langue, *args):
    r = subprocess.run([sys.executable, "-I", TOOL, *args, "--depot", DEPOT, "--jeu", JEU, "--donnees", DONNEES, "--langue", langue, *MODE],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


import re
COLLE = re.compile(r"(?m)[;,·–、；，]\s*[;,·–、；，]|[;,·–、；，]\s*$|^\s*[;,·–、；，]")
vues = [("plan", "--profil", "t"), ("ordre", "--profil", "t"), ("config",)] + ([("magasin", "--profil", "t"), ("purge", "--profil", "t")] if MAGASIN else [])
sorties = {l: {v[0]: texte(l, *v) for v in vues} for l in ("fr", "en", "de", "ja", "ru", "zh-cn")}
check("mode texte : chaque commande répond dans six langues, sans erreur",
      all(c == 0 and t.strip() for d in sorties.values() for c, t in d.values()), str([(l, k, c) for l, d in sorties.items() for k, (c, t) in d.items() if c or not t.strip()]))
mal = [(l, k, m.group(0), t[max(0, m.start() - 40):m.end() + 10]) for l, d in sorties.items() for k, (c, t) in d.items() for m in [COLLE.search(t)] if m]
check("mode texte : aucun séparateur doublé, en tête ou en fin de ligne", not mal, str(mal)[:400])
fr, en = sorties["fr"], sorties["en"]
check("mode texte, plan : le lieu de pose est une proposition jointe par la virgule de la langue",
      (", magasin " if MAGASIN else ", pose directe") in fr["plan"][1].splitlines()[0] and (", store " if MAGASIN else ", direct install") in en["plan"][1].splitlines()[0],
      fr["plan"][1][:160] + en["plan"][1][:160])
check("mode texte, ordre : la source de l'ordre est dite en phrase entière dans la langue",
      "ordre par les noms des archives" in fr["ordre"][1].splitlines()[0] and "ordered by archive names" in en["ordre"][1].splitlines()[0], fr["ordre"][1][:120] + en["ordre"][1][:120])
check("mode texte anglais : plus de « ; » à la française ni d'unité « Go »", not any(" ; " in t or re.search(r"\d Go\b", t) for c, t in en.values()),
      str([k for k, (c, t) in en.items() if " ; " in t or re.search(r"\d Go\b", t)]))
if MAGASIN:
    check("mode texte, magasin : la place libre suit le séparateur de la langue",
          " ; libre sur le disque du jeu : " in fr["magasin"][1] and "; free on the game disk: " in en["magasin"][1] and " / " in sorties["ja"]["magasin"][1], en["magasin"][1][:300])

# ---------------------------------------------------------------- 28. prérequis : déclarés sur Nexus, déduits des fichiers, qui les fournit
print("28. prérequis (faux serveur local) : cadres déduits des fichiers, liste de Nexus, optionnels, alertes du plan")
REQUIS = {7002: ("Besoin", [(107, "Cyber Engine Tweaks", "", False), (7003, "Fourni", "", False), (7004, "Extras", "Optional, for the extra colours", False),
                            (0, "ReShade", "Download and install it", True)]),
          7003: ("Fourni", []), 107: ("Cyber Engine Tweaks", [])}


class FauxRequis(FauxNexus):
    def do_POST(self):
        q = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["query"]
        ids = [int(m) for m in re.findall(r"modId: (\d+)\}", q)]
        noeud = lambda m: {"modId": str(m), "name": REQUIS[m][0], "modRequirements": {"dlcRequirements": [], "nexusRequirements": {"nodes": [
            {"modId": str(i), "modName": n, "notes": note, "externalRequirement": ext, "url": "https://reshade.me/" if ext else "", "gameId": "3333"}
            for i, n, note, ext in REQUIS[m][1]]}}}
        self.rend(200, {"data": {**{f"m{m}": [] for m in re.findall(r"m(\d+): modFiles", q)},
                                 "req": {"nodes": [noeud(m) for m in ids if m in REQUIS]}}})


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FauxRequis)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["RED_STACK_NEXUS_URL"] = f"http://127.0.0.1:{srv.server_address[1]}"
Q = "7_Req/"
CADRE, LUA, BESOIN, FOURNI, SANS = (Q + "Cadre CET-107-1-0-1700000701.zip", Q + "Lua Mod-7001-1-0-1700000702.zip", Q + "Besoin-7002-1-0-1700000703.zip",
                                    Q + "Fourni-7003-1-0-1700000704.zip", Q + "Sans Id.zip")
mkzip(CADRE, {"bin/x64/plugins/cyber_engine_tweaks.asi": "cet"})
mkzip(LUA, {"bin/x64/plugins/cyber_engine_tweaks/mods/lua_mod/init.lua": "-- lua"})
mkzip(BESOIN, {A + "besoin.archive": "b"})
mkzip(FOURNI, {A + "fourni.archive": "f"})
mkzip(SANS, {"r6/tweaks/sans_id.yaml": "a: 1"})
rs("profils", "--profil", "q", "--copie", "t")
for z in (LUA, BESOIN, SANS):
    rs("bascule", "on", "--profil", "q", "--mod", z[:-4])
lit = lambda *a: {r["cle"]: r for r in rs("prerequis", "--profil", "q", *a)["mods"]}
R = lit()
un = lambda r, nom: next((e for e in r["requis"] if e["nom"] == nom), {})
check("cadre déduit des fichiers sans Nexus : un mod Lua exige CET, fourni par un zip du dépôt qui n'est pas actif",
      un(R[LUA], "Cyber Engine Tweaks").get("etat") == "coupé" and un(R[LUA], "Cyber Engine Tweaks")["sources"] == ["fichiers"]
      and un(R[LUA], "Cyber Engine Tweaks")["par"] == [CADRE] and R[LUA]["manque"] == 1 and R[LUA]["nexus"] == "jamais lu", str(R[LUA]))
check("zip sans modId : son cadre se déduit quand même, absent du dépôt et du jeu ; le zip du cadre ne s'exige pas lui-même",
      un(R[SANS], "TweakXL").get("etat") == "absent" and R[SANS]["manque"] == 1 and R[SANS]["nexus"] == "sans modId" and not R[CADRE]["requis"], str(R[SANS]))
put("red4ext/plugins/TweakXL/TweakXL.dll", "posé à la main")
R = lit()
check("cadre posé à la main dans le jeu, hors Red Stack : tenu pour présent", un(R[SANS], "TweakXL").get("etat") == "dans le jeu" and R[SANS]["manque"] == 0, str(R[SANS]))
os.remove(os.path.join(JEU, "red4ext", "plugins", "TweakXL", "TweakXL.dll"))
R = lit("--nexus")
b = R[BESOIN]
check("Nexus lu : mod déclaré requis et coupé = à voir ; note « Optional » = optionnel, non compté ; prérequis hors Nexus = externe",
      un(b, "Fourni").get("etat") == "coupé" and b["a_voir"] == 1 and un(b, "Extras").get("optionnel") is True and un(b, "Extras")["etat"] == "absent"
      and b["optionnels"] == 1 and un(b, "ReShade").get("etat") == "externe" and b["nexus"] == "lu", str(b))
check("cadre déclaré sur Nexus : compté comme cadre, par son zip ; mod que Nexus ne rend pas : dit inconnu, ses cadres restent",
      un(b, "Cyber Engine Tweaks").get("cadre") == "cet" and b["manque"] == 1 and R[LUA]["nexus"] == "inconnu" and R[LUA]["manque"] == 1, str(R[LUA]))
check("exigé par : le zip fourni nomme qui l'exige, aucun actif ne l'a tant qu'il est coupé de son côté",
      R[FOURNI]["requis_par"] == [BESOIN] and R[FOURNI]["requis_par_actifs"] == 1 and sorted(R[CADRE]["requis_par"]) == sorted([LUA, BESOIN]), str(R[FOURNI]))
pl = {x["zip"]: [e["nom"] for e in x["requis"]] for x in rs("plan", "--profil", "q")["prerequis"]}
check("aperçu du plan : cadre manquant et mod requis coupé sont dits, l'optionnel et l'externe non",
      pl.get(BESOIN) == ["Cyber Engine Tweaks", "Fourni"] and pl.get(LUA) == ["Cyber Engine Tweaks"] and pl.get(SANS) == ["TweakXL"], str(pl))
tu = un(b, "Fourni")["ident"]
refus = rs("prerequis", "on", "--profil", "q", "--cle", BESOIN, "--ignore", "--requis", "m:424242", ok=False)
rs("prerequis", "on", "--profil", "q", "--cle", BESOIN, "--ignore", "--requis", tu)
R2 = lit()
pl2 = {x["zip"]: [e["nom"] for e in x["requis"]] for x in rs("plan", "--profil", "q")["prerequis"]}
rs("prerequis", "off", "--profil", "q", "--cle", BESOIN, "--ignore", "--requis", tu)
check("prérequis ignoré pour ce mod : toujours listé, marqué, plus compté ni dit au plan ; inconnu = refus ; repris, il compte de nouveau",
      un(R2[BESOIN], "Fourni")["ignore"] is True and R2[BESOIN]["a_voir"] == 0 and pl2.get(BESOIN) == ["Cyber Engine Tweaks"] and "m:424242" in str(refus)
      and lit()[BESOIN]["a_voir"] == 1 and "requis_ignores" in json.load(open(os.path.join(DONNEES, "config.json"), encoding="utf-8")), str(R2[BESOIN]) + str(refus))
for z in (CADRE, FOURNI):
    rs("bascule", "on", "--profil", "q", "--mod", z[:-4])
R = lit()
et = {r["cle"]: r["prerequis"] for r in rs("etat", "--profil", "q")["mods"]}
check("cadre et mod requis activés : plus rien ne manque, l'état de la liste le porte, le plan ne dit plus que le cadre absent",
      R[BESOIN]["manque"] == R[BESOIN]["a_voir"] == 0 and R[LUA]["manque"] == 0 and et[BESOIN] == {"manque": 0, "a_voir": 0, "optionnels": 1, "requis_par_actifs": 0}
      and et[SANS]["manque"] == 1 and [x["zip"] for x in rs("plan", "--profil", "q")["prerequis"] if x["zip"].startswith(Q)] == [SANS], str(et.get(BESOIN)))
d = rs("detail", "--profil", "q", "--mod", FOURNI)
check("fiche d'un mod : ses prérequis et qui l'exige", d["prerequis"]["requis_par"] == [BESOIN] and d["prerequis"]["requis"] == [], str(d.get("prerequis")))
srv.shutdown()
os.environ.pop("RED_STACK_NEXUS_URL")
shutil.rmtree(os.path.join(DEPOT, "7_Req"))
os.remove(os.path.join(DONNEES, "nexus.json"))
rs("profils", "--profil", "q", "--supprime")
c = plan_counts()
check("profil « t » intact après l'essai (28)", c["pose"] == c["remplace"] == c["retire"] == c["conflit"] == 0, str(c))

print(f"\n{'TOUT VERT' if not fails else str(len(fails)) + ' KO : ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
