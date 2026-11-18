"""Fabrique le paquet .vsix de l'extension Red Stack, sans outil tiers (un .vsix est un zip avec deux fichiers de manifeste).

  python -I empaquette.py            -> ..\\releases\\red-stack-<version>.vsix
Le moteur Python et le serveur MCP (dossier `moteur`) sont dans le paquet ; `test` et `.vscodeignore` restent dehors. Installation : code --install-extension <fichier.vsix>
"""
import json, os, re, sys, zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "extension")
pkg = json.load(open(os.path.join(SRC, "package.json"), encoding="utf-8"))
nls = json.load(open(os.path.join(SRC, "package.nls.json"), encoding="utf-8"))   # textes de package.json : l'anglais par défaut, package.nls.fr.json pour le français
dit = lambda t: nls.get(t[1:-1], t) if isinstance(t, str) and t.startswith("%") and t.endswith("%") else t
out = os.path.join(HERE, "..", "releases", f"{pkg['name']}-{pkg['version']}.vsix")
os.makedirs(os.path.dirname(out), exist_ok=True)

files = []
for d, dirs, fs in os.walk(SRC):
    dirs[:] = [x for x in dirs if x not in ("test", "node_modules", "__pycache__", "red_stack")]
    files += [os.path.relpath(os.path.join(d, f), SRC).replace("\\", "/") for f in fs if f != ".vscodeignore"]
# fiche de la place de marché : icône (PNG exigé), licence, liens du dépôt, mots-clés ; les thèmes livrés ajoutent leurs deux étiquettes, comme le fait vsce
depot = re.sub(r"\.git$", "", (pkg.get("repository") or {}).get("url", ""))
tags = list(pkg.get("keywords", [])) + (["theme", "color-theme"] if pkg.get("contributes", {}).get("themes") else [])
icone = pkg.get("icon", "")
if icone and (not icone.lower().endswith(".png") or icone not in files):
    sys.exit(f"Icône du paquet absente ou pas en PNG : {icone}")
liens = "".join(f'\n      <Property Id="Microsoft.VisualStudio.Services.Links.{k}" Value="{escape(v)}"/>' for k, v in (
    ("Source", depot + ".git"), ("Getstarted", depot + ".git"), ("GitHub", depot + ".git"), ("Support", (pkg.get("bugs") or {}).get("url", "")), ("Learn", pkg.get("homepage", ""))) if depot and v)
balise_icone = f"\n    <Icon>extension/{escape(icone)}</Icon>" if icone else ""
asset_icone = f'\n    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/{escape(icone)}" Addressable="true"/>' if icone else ""
banniere = pkg.get("galleryBanner") or {}
liens += "".join(f'\n      <Property Id="Microsoft.VisualStudio.Services.Branding.{k}" Value="{escape(banniere[c])}"/>' for k, c in (("Color", "color"), ("Theme", "theme")) if banniere.get(c))


def lisezmoi(nom):
    """Un README du paquet : ses liens relatifs (l'autre langue) deviennent ceux du dépôt, la place de marché ne sert pas les fichiers voisins."""
    t = open(os.path.join(SRC, nom), encoding="utf-8").read()
    return re.sub(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)", lambda m: f"]({depot}/blob/master/source/extension/{m.group(1)})", t) if depot else t


exts = sorted({os.path.splitext(f)[1].lower() or ".txt" for f in files} | {".vsixmanifest"})
TYPES = {".txt": "text/plain", ".json": "application/json", ".js": "application/javascript", ".html": "text/html", ".svg": "image/svg+xml", ".md": "text/markdown", ".py": "text/x-python", ".png": "image/png",
         ".vsixmanifest": "text/xml"}
content_types = ('<?xml version="1.0" encoding="utf-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 + "".join(f'<Default Extension="{e}" ContentType="{TYPES.get(e, "application/octet-stream")}"/>' for e in exts if e)
                 + "</Types>\n")
manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="{escape(pkg['name'])}" Version="{escape(pkg['version'])}" Publisher="{escape(pkg['publisher'])}"/>
    <DisplayName>{escape(pkg['displayName'])}</DisplayName>
    <Description xml:space="preserve">{escape(dit(pkg['description']))}</Description>
    <Tags>{escape(",".join(tags))}</Tags>
    <Categories>{escape(",".join(pkg.get('categories', [])))}</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <License>extension/LICENSE.txt</License>{balise_icone}
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{escape(pkg['engines']['vscode'])}"/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value=""/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value=""/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace"/>{liens}
      <Property Id="Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown" Value="true"/>
      <Property Id="Microsoft.VisualStudio.Services.Content.Pricing" Value="Free"/>
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.License" Path="extension/LICENSE.txt" Addressable="true"/>{asset_icone}
  </Assets>
</PackageManifest>
"""
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("extension.vsixmanifest", manifest)
    for f in sorted(files):
        if f in ("README.md", "README.fr.md"):
            z.writestr("extension/" + f, lisezmoi(f))
        else:
            z.write(os.path.join(SRC, f.replace("/", os.sep)), "extension/" + (f if os.path.splitext(f)[1] else f + ".txt"))   # LICENSE -> LICENSE.txt
with zipfile.ZipFile(out) as z:
    bad = z.testzip()
    names = z.namelist()
if (bad or any(n not in names for n in ("extension/extension.js", "extension/moteur/red_stack.py", "extension/moteur/red_stack_mcp.py", "extension/moteur/red_stack_wk_mcp.py", "extension/langue.js", "extension/langues/en.json", "extension/package.nls.json", "extension/package.nls.fr.json", "extension/media/aide.html", "extension/media/aide.en.html", "extension/README.md", "extension/README.fr.md", "extension/LICENSE.txt") + (("extension/" + icone,) if icone else ()))
        or any("/test/" in n or "__pycache__" in n or "/moteur/red_stack/" in n for n in names)):
    sys.exit(f"Paquet douteux : {bad} {names}")
print(f"{os.path.abspath(out)} : {len(names)} fichiers, {os.path.getsize(out)} octets\n  " + "\n  ".join(names))
