"""Banc des langues : relit le code de l'extension, en tire les textes passés à T et à N, et les compare aux catalogues.

  python -I tests/langues_test.py [--cles]      (depuis `source`)
Rouge si une clé du code manque à un catalogue, si un catalogue porte une clé que le code n'a plus, si une traduction
perd une valeur ({0}, {n}), change les balises ou les guillemets de sa clé, ou si un appel de T ne se lit pas (texte
calculé). `--cles` écrit les clés du code, une par ligne en JSON, pour préparer un catalogue.
"""
import ast, html.parser, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(HERE, "..", "extension")
CODE = ("extension.js", "nxm.js", "moteur.js", "media/page.html")
MOTEUR = ("moteur/red_stack.py",)                 # textes du moteur : T("texte {0}", valeur), C("code d'état")
FIXES = {"Red Stack", "?", "↻"}                    # textes de la page qui ne se traduisent pas
MOTS_CLES = ("return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do")


# ---------------------------------------------------------------- lecture du JavaScript : chaînes, gabarits, commentaires
def fin_chaine(s, i):
    q, j = s[i], i + 1
    while s[j] != q:
        j += 2 if s[j] == "\\" else 1
    return j + 1


def fin_regex(s, i):
    j, classe = i + 1, False
    while True:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            raise ValueError(f"expression régulière non fermée vers {i}")
        if c == "[":
            classe = True
        elif c == "]":
            classe = False
        elif c == "/" and not classe:
            break
        j += 1
    j += 1
    while s[j].isalpha():
        j += 1
    return j


def regex_ici(s, i, debut):
    j = i - 1
    while j >= debut and s[j] in " \t\r\n":
        j -= 1
    if j < debut:
        return True
    if s[j] in "(,=:[!&|?{};+-*%<>~^":
        return True
    m = re.search(r"([A-Za-z_$][\w$]*)$", s[max(debut, j - 12):j + 1])
    return bool(m and m.group(1) in MOTS_CLES)


def lit_gabarit(s, i):
    """Gabarit ouvert en s[i] : rend (fin, parts), parts = [('s', a, b) | ('h', a, b)] en alternance, texte puis trou."""
    j, d, parts = i + 1, i + 1, []
    while True:
        c = s[j]
        if c == "\\":
            j += 2
        elif c == "`":
            parts.append(("s", d, j))
            return j + 1, parts
        elif c == "$" and s[j + 1] == "{":
            parts.append(("s", d, j))
            k = fin_code(s, j + 2, j + 2)
            parts.append(("h", j + 2, k))
            j = d = k + 1
        else:
            j += 1


def jetons(s, a, b):
    """Jetons littéraux du code s[a:b] : ('str', i, j) et ('tpl', i, j, parts). Commentaires et expressions régulières sautés."""
    i = a
    while i < b:
        c = s[i]
        if c in "\"'":
            j = fin_chaine(s, i)
            yield ("str", i, j)
            i = j
        elif c == "`":
            j, parts = lit_gabarit(s, i)
            yield ("tpl", i, j, parts)
            i = j
        elif c == "/" and s[i + 1] == "/":
            i = s.find("\n", i)
            i = b if i < 0 else i
        elif c == "/" and s[i + 1] == "*":
            i = s.index("*/", i) + 2
        elif c == "/" and regex_ici(s, i, a):
            i = fin_regex(s, i)
        else:
            i += 1


def fin_code(s, i, debut):
    """Avance dans du code jusqu'à l'accolade fermante qui n'a pas d'ouvrante ; rend sa place."""
    n = 0
    while True:
        c = s[i]
        if c in "\"'":
            i = fin_chaine(s, i)
        elif c == "`":
            i, _ = lit_gabarit(s, i)
        elif c == "/" and s[i + 1] == "/":
            i = s.index("\n", i)
        elif c == "/" and s[i + 1] == "*":
            i = s.index("*/", i) + 2
        elif c == "/" and regex_ici(s, i, debut):
            i = fin_regex(s, i)
        elif c == "{":
            n, i = n + 1, i + 1
        elif c == "}":
            if n == 0:
                return i
            n, i = n - 1, i + 1
        else:
            i += 1


SIMPLES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0", "\n": ""}


def cuit(brut):
    """Valeur d'un littéral JavaScript d'après son texte entre délimiteurs."""
    def un(m):
        x = m.group(1)
        if x[0] == "u":
            return chr(int(x[2:-1] if x[1] == "{" else x[1:], 16))
        if x[0] == "x":
            return chr(int(x[1:], 16))
        return SIMPLES.get(x, x)
    return re.sub(r"\\(u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|\r\n|[\s\S])", un, brut)


def cles_du_code(s, a, b, ou, out, soucis):
    """Clés de T`…`, T('…') et N(n, '…', '…') dans le code s[a:b] ; descend dans les trous des gabarits."""
    js = list(jetons(s, a, b))
    for n, j in enumerate(js):
        avant = s[max(a, j[1] - 3):j[1]]
        if j[0] == "tpl":
            if re.search(r"(?<![\w$.])T$", avant):
                cle = "".join(cuit(s[p[1]:p[2]]) if p[0] == "s" else "{%d}" % (k // 2) for k, p in enumerate(j[3]))
                out.setdefault(cle, {"genre": "T", "ou": ou(j[1])})
            for p in j[3]:
                if p[0] == "h":
                    cles_du_code(s, p[1], p[2], ou, out, soucis)
        elif re.search(r"(?<![\w$.])T\($", avant):
            out.setdefault(cuit(s[j[1] + 1:j[2] - 1]), {"genre": "T", "ou": ou(j[1])})
    for m in re.finditer(r"(?<![\w$.])([TN])\(", s[a:b]):
        i = a + m.end()
        if any(j[1] < m.start() + a < j[2] for j in js if j[0] == "str") or any(
                p[0] == "s" and p[1] <= a + m.start() < p[2] for j in js if j[0] == "tpl" for p in j[3]):
            continue                                # « T( » écrit dans un texte, pas un appel
        if any(p[0] == "h" and p[1] <= a + m.start() < p[2] for j in js if j[0] == "tpl" for p in j[3]):
            continue                                # dans un trou : lu par la descente
        if m.group(1) == "T":
            if s[i] not in "\"'":
                soucis.append(f"{ou(i)} : T( … ) sur un texte calculé, illisible pour ce banc : {s[i:i + 60]!r}")
            continue
        # N(n, 'un', 'plusieurs') : sauter le premier argument jusqu'à sa virgule
        k, prof = i, 0
        while not (s[k] == "," and prof == 0):
            if s[k] in "\"'":
                k = fin_chaine(s, k) - 1
            elif s[k] == "`":
                k = lit_gabarit(s, k)[0] - 1
            elif s[k] in "([{":
                prof += 1
            elif s[k] in ")]}":
                prof -= 1
            k += 1
        mm = re.match(r",\s*(['\"])", s[k:])
        if not mm:
            soucis.append(f"{ou(i)} : N( … ) sans texte en clair : {s[i:i + 60]!r}")
            continue
        d = k + mm.end() - 1
        f = fin_chaine(s, d)
        m2 = re.match(r"\s*,\s*(['\"])", s[f:])
        if not m2:
            soucis.append(f"{ou(i)} : N( … ) sans pluriel en clair : {s[i:i + 60]!r}")
            continue
        d2 = f + m2.end() - 1
        out[cuit(s[d + 1:f - 1])] = {"genre": "N", "ou": ou(d), "pluriel": cuit(s[d2 + 1:fin_chaine(s, d2) - 1])}


class Statique(html.parser.HTMLParser):
    """Textes du corps de la page écrits en HTML : la page les passe à T quand elle s'ouvre (`traduitPage`)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cles, self.dans = [], 0

    def handle_starttag(self, tag, attrs):
        self.dans += tag in ("script", "style")
        for k, v in attrs:
            if k in ("title", "placeholder", "aria-label") and v and v.strip():
                self.cles.append(v.strip())

    def handle_endtag(self, tag):
        self.dans -= tag in ("script", "style")

    def handle_data(self, data):
        if not self.dans and data.strip():
            self.cles.append(data.strip())


def cles():
    out, soucis = {}, []
    for rel in CODE:
        s = open(os.path.join(EXT, rel), encoding="utf-8").read()
        ligne = lambda i, s=s, rel=rel: f"{rel}:{s.count(chr(10), 0, i) + 1}"
        a, b = 0, len(s)
        if rel.endswith(".html"):
            corps = s.index("<body>")
            a = s.index(">", s.rindex("<script")) + 1       # le dernier script : celui de la page
            b = s.rindex("</script>")
            p = Statique()
            p.feed(s[corps:s.index("<script", corps)])
            for c in p.cles:
                if c not in FIXES:
                    out.setdefault(c, {"genre": "T", "ou": rel + " (HTML)"})
        cles_du_code(s, a, b, ligne, out, soucis)
    for rel in MOTEUR:                              # Python : lu par son arbre ; N(n, "un", "plusieurs") comme dans l'extension
        for n in ast.walk(ast.parse(open(os.path.join(EXT, rel), encoding="utf-8").read())):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("T", "C", "N") and n.args):
                continue
            if n.func.id == "N":
                un, plusieurs = (n.args + [None, None])[1:3]
                if all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in (un, plusieurs)):
                    out[un.value] = {"genre": "N", "ou": f"{rel}:{n.lineno}", "pluriel": plusieurs.value, "moteur": True}
                else:
                    soucis.append(f"{rel}:{n.lineno} : N( … ) sans singulier et pluriel en clair")
                continue
            x = n.args[0]
            if isinstance(x, ast.Constant) and isinstance(x.value, str):
                out.setdefault(x.value, {"genre": "T", "ou": f"{rel}:{n.lineno}", "moteur": True})
            elif n.func.id == "T":                  # C(variable) est permis : le code vient d'une table, dite par la page
                soucis.append(f"{rel}:{n.lineno} : T( … ) sur un texte calculé, illisible pour ce banc")
    return out, soucis


# formes du pluriel que chaque langue exige (CLDR, nombres entiers) ; une langue absente d'ici : « one » et « other »
FORMES = {"pl": ("one", "few", "many", "other"), "ru": ("one", "few", "many", "other"), "zh-cn": ("other",), "ja": ("other",), "ko": ("other",)}


SEPARATEURS = (" ; ", ", ")                        # les deux séparateurs de `suite` du moteur, traduits une fois par langue
VALEURS = re.compile(r"\{(?:\d+|n)\}")
BALISES = re.compile(r"</?[a-zA-Z][^>]*>")


def forme(cle, t):
    """Ce qu'une traduction doit garder de sa clé : valeurs, balises, guillemets droits, entités."""
    return (sorted(set(VALEURS.findall(t)) - {"{n}"}), sorted(BALISES.findall(t)), t.count('"'), sorted(re.findall(r"&(?:lt|gt|amp|quot);", t)))


def pluriels_du_moteur():
    """`forme_pluriel` du moteur contre les formes attendues (CLDR) : le moteur n'a pas l'`Intl.PluralRules` de la page."""
    import importlib.util
    argv, sys.argv = sys.argv, ["red_stack.py"]
    try:
        spec = importlib.util.spec_from_file_location("red_stack", os.path.join(EXT, MOTEUR[0]))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    finally:
        sys.argv = argv
    attendu = {"en": {0: "other", 1: "one", 2: "other"}, "de": {1: "one", 5: "other"}, "pt-br": {1: "one", 2: "other"}, "fr": {0: "one", 1: "one", 2: "other"},
               "zh-cn": {1: "other"}, "ja": {1: "other"}, "ko": {7: "other"},
               "ru": {1: "one", 2: "few", 4: "few", 5: "many", 11: "many", 12: "many", 21: "one", 22: "few", 25: "many", 111: "many", 1.5: "other", 0: "many"},
               "pl": {1: "one", 2: "few", 4: "few", 5: "many", 12: "many", 21: "many", 22: "few", 25: "many", 112: "many", 1.5: "other", 0: "many"}}
    return [f"moteur : forme_pluriel({l!r}, {n}) rend {m.forme_pluriel(l, n)!r}, attendu {v!r}" for l, d in attendu.items() for n, v in d.items() if m.forme_pluriel(l, n) != v]


# Codes que le manuel anglais dit autrement que le français (exemples de noms, natures dites par la page, titre de commande).
CODES_MANUEL = {"réglages": "settings", "autre": "other", "Red Stack : ouvrir": "Red Stack: Open", "fichier:ligne": "file:line",
                "Nom-numéroDuMod-version-horodatage.zip": "Name-modId-version-timestamp.zip",
                "Mon Mod 1.0.1.zip": "My Mod 1.0.1.zip", "Mon Mod 1.0.0.zip": "My Mod 1.0.0.zip",
                "r6/tweaks/Famille/Mon_Mod.yaml": "r6/tweaks/Family/My_Mod.yaml", "Famille - …": "Family - …"}


def manuels():
    """Le manuel français (`media/aide.html`) et le corps anglais (`media/aide.en.html`) : même structure, mêmes ancres, mêmes
    codes, et chaque bouton cité (`<b class="b">`) qui est un texte du code porte en anglais le texte du catalogue anglais."""
    soucis = []
    try:
        fr = open(os.path.join(EXT, "media", "aide.html"), encoding="utf-8").read()
        en = open(os.path.join(EXT, "media", "aide.en.html"), encoding="utf-8").read()
        cat = json.load(open(os.path.join(EXT, "langues", "en.json"), encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"manuel : illisible ({e})"]
    a, b = fr.find("<!-- corps -->"), fr.find("<!-- /corps -->")
    if not 0 < a < b:
        return ["manuel : repères « corps » absents de aide.html"]
    fr = fr[a:b]
    if re.search(r"<(script|style|html|head|body)[ >]", en):
        soucis.append("manuel anglais : il ne porte que le corps (ni style ni script)")
    nu = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s))
    for nom, motif in (("sections", r'<section id="([^"]+)"'), ("ancres", r'(?<![A-Za-z-])id="([^"]+)"'), ("liens", r'href="([^"]+)"'), ("touches", r"<kbd>(.*?)</kbd>"),
                       ("balises", r"<(/?(?:section|h2|h3|table|tr|th|td|ul|ol|li|p|div|b|a|code|kbd|nav|main|input|button)(?=[ >]))")):
        x, y = re.findall(motif, fr), re.findall(motif, en)
        if nom == "touches":
            x = ["Shift" if k == "Maj" else "Enter" if k == "Entrée" else k for k in x]
        if x != y:
            i = next((i for i, (u, v) in enumerate(zip(x, y)) if u != v), min(len(x), len(y)))
            soucis.append(f"manuel : {nom} différentes entre le français et l'anglais (rang {i} : {x[i:i + 1]} contre {y[i:i + 1]} ; {len(x)} contre {len(y)})")
    x = sorted(CODES_MANUEL.get(nu(c), nu(c)) for c in re.findall(r"<code>(.*?)</code>", fr))
    y = sorted(nu(c) for c in re.findall(r"<code>(.*?)</code>", en))
    if x != y:
        soucis.append(f"manuel : codes différents entre le français et l'anglais : {sorted(set(x) ^ set(y))[:8]}")
    cles = {re.sub(r"^\$\([a-z-]+\) ", "", k): v for k, v in cat.items() if isinstance(v, str)}
    dit = lambda v: re.sub(r"^\$\([a-z-]+\) ", "", v)
    x, y = [nu(c) for c in re.findall(r'<b class="b">(.*?)</b>', fr)], [nu(c) for c in re.findall(r'<b class="b">(.*?)</b>', en)]
    for u, v in zip(x, y):
        if u in cles and dit(cles[u]) != v:
            soucis.append(f"manuel anglais : le bouton « {u} » s'y appelle « {v} », le catalogue dit « {dit(cles[u])} »")
    if re.search(r"[«»]|[àâçéèêîôùû]", re.sub(r"Red Stack (Rouge|Jaune)|Référence|_avant", "", en)):
        soucis.append("manuel anglais : il reste du français (guillemets « » ou lettre accentuée) : " + ", ".join(re.findall(r"\S*[«»àâçéèêîôùû]\S*", en)[:6]))
    try:                                        # les deux README : mêmes titres de section, même table, mêmes réglages cités
        lf = open(os.path.join(EXT, "README.fr.md"), encoding="utf-8").read()
        le = open(os.path.join(EXT, "README.md"), encoding="utf-8").read()
        for nom, motif in (("titres", r"(?m)^#+ "), ("puces", r"(?m)^- "), ("lignes de table", r"(?m)^\| "), ("réglages cités", r"`redStack\.[A-Za-z]+`")):
            if len(re.findall(motif, lf)) != len(re.findall(motif, le)):
                soucis.append(f"README : {nom} en nombre différent entre le français ({len(re.findall(motif, lf))}) et l'anglais ({len(re.findall(motif, le))})")
        if re.search(r"[«»]", le):
            soucis.append("README anglais : il reste des guillemets français")
    except OSError as e:
        soucis.append(f"README : illisible ({e})")
    print(f"  manuels : {len(re.findall('<section ', fr))} sections, {len(x)} boutons cités, {len(soucis)} souci(s)")
    return soucis


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    code, soucis = cles()
    if "--cles" in sys.argv:
        for c, v in code.items():
            print(json.dumps([c, v.get("pluriel")] if v["genre"] == "N" else c, ensure_ascii=False))
        return 0
    dossier = os.path.join(EXT, "langues")
    catalogues = sorted(f for f in os.listdir(dossier) if f.endswith(".json")) if os.path.isdir(dossier) else []
    print(f"{len(code)} textes dans le code ({sum(1 for v in code.values() if v['genre'] == 'N')} pluriels), {len(catalogues)} catalogue(s)")
    for f in catalogues:
        try:
            t = json.load(open(os.path.join(dossier, f), encoding="utf-8"))
        except ValueError as e:
            soucis.append(f"{f} : illisible ({e})")
            continue
        manque = [c for c in code if c not in t]
        trop = [c for c in t if c not in code and not c.startswith("_")]
        for c in manque[:40]:
            soucis.append(f"{f} : manque {c!r} ({code[c]['ou']})")
        if len(manque) > 40:
            soucis.append(f"{f} : … et {len(manque) - 40} autres clés manquantes")
        for c in trop[:40]:
            soucis.append(f"{f} : n'est plus dans le code : {c!r}")
        for c, v in code.items():
            if c not in t:
                continue
            formes = [t[c]] if isinstance(t[c], str) else list(t[c].values()) if isinstance(t[c], dict) else None
            if formes is None or (v["genre"] == "N") != isinstance(t[c], dict) or (isinstance(t[c], dict) and "other" not in t[c]):
                soucis.append(f"{f} : {c!r} doit être {'un objet de formes avec « other »' if v['genre'] == 'N' else 'un texte'}")
                continue
            voulues = FORMES.get(f[:-5], ("one", "other"))
            if isinstance(t[c], dict) and set(t[c]) != set(voulues):
                soucis.append(f"{f} : {c!r} porte les formes {sorted(t[c])}, cette langue demande {list(voulues)}")
            for x in formes:
                if not x.strip():
                    soucis.append(f"{f} : traduction vide pour {c!r}")
                elif v.get("moteur") and forme(c, x)[0::2] == forme(c, c)[0::2]:
                    pass                            # texte du moteur : « <mod> » y est un mot à remplacer, pas une balise
                elif forme(c, x) != forme(c, c) and not (v["genre"] == "N" and forme(c, x)[1:] == forme(c, c)[1:]):
                    soucis.append(f"{f} : {c!r} -> {x!r} : valeurs, balises ou guillemets différents")
        print(f"  {f} : {len(t) - sum(1 for c in t if c.startswith('_'))} entrées, {len(manque)} manquante(s), {len(trop)} en trop")
    for c, v in code.items():                      # moteur, page, extension : un texte ne porte jamais le séparateur qui le joint à son voisin
        if c in SEPARATEURS:
            continue
        if c.lstrip(" ")[:1] in (";", ",", ".", ":") or c.rstrip(" ")[-1:] in (";", ","):
            soucis.append(f"{v['ou']} : {c!r} commence ou finit par un séparateur : proposition entière, jointe par `suite` ou par T(', ')")
        elif not v.get("moteur") and c != c.strip():   # page et extension : pas de morceau collé par une espace de bord
            soucis.append(f"{v['ou']} : {c!r} commence ou finit par une espace : morceau collé, à écrire en phrase entière")
    soucis += pluriels_du_moteur()
    soucis += manuels()
    for x in soucis:
        print("  KO   " + x)
    print("VERT" if not soucis else f"ROUGE : {len(soucis)} souci(s)")
    return 1 if soucis else 0


if __name__ == "__main__":
    sys.exit(main())
