"""Fabrique les thèmes de couleurs VS Code de Red Stack (un fichier par variante d'accent).

  python -I themes.py            -> extension\\themes\\red-stack-<variante>.json
Une seule palette : fond sombre bleuté (ni noir ni gris), un accent principal (rouge ou jaune), un bleu vif en second,
et une coloration du code à teintes franches. La page Red Stack reprend les couleurs de VS Code : elle suit le thème.
Retoucher une couleur ICI, puis relancer ; les fichiers JSON ne se retouchent pas à la main.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "extension", "themes")

# fonds, du plus profond au plus clair, et textes
F0, F1, F2, F3, F4 = "#090b10", "#0d1017", "#121620", "#1a2030", "#252d40"
TRAIT = "#1f2636"
TEXTE, DOUX, PALE, MUET = "#dfe5f2", "#b4bdd0", "#7d889f", "#515b72"
BLEU, BLEU_FONCE = "#2fc4ff", "#0b6f9c"
VERT, AMBRE, ROUGE, VIOLET, ROSE, ORANGE, TURQUOISE, CITRON = "#4be38a", "#ffb629", "#ff4d5e", "#b58cff", "#ff5fa8", "#ff9440", "#22e0c8", "#c8f04a"
FERRARI, JAUNE = "#ff2800", "#fcee0a"                # Markdown : barré, sections ; aussi les accents des deux variantes

# Les accents sont repris dans extension.js (`ACCENTS`, réglage « redStack.barreEnCouleur ») : les changer aux deux endroits.
VARIANTES = {
    "rouge": {"nom": "Red Stack Rouge", "accent": "#ff2800", "accent_fort": "#ff5436", "bouton": "#e02208", "sur_bouton": "#ffffff"},
    "jaune": {"nom": "Red Stack Jaune", "accent": "#fcee0a", "accent_fort": "#fff66b", "bouton": "#fcee0a", "sur_bouton": "#0d1017"},
}


def couleurs(v):
    A, AF = v["accent"], v["accent_fort"]
    return {
        "focusBorder": BLEU + "aa", "foreground": TEXTE, "disabledForeground": MUET, "descriptionForeground": PALE,
        "errorForeground": ROUGE, "icon.foreground": DOUX, "selection.background": BLEU + "55", "widget.shadow": "#00000080",
        "sash.hoverBorder": BLEU, "textLink.foreground": BLEU, "textLink.activeForeground": "#7bdcff",
        "textPreformat.foreground": TURQUOISE, "textPreformat.background": F3, "textBlockQuote.background": F2, "textBlockQuote.border": A,
        "textCodeBlock.background": F3, "textSeparator.foreground": TRAIT,
        # fenêtre
        "titleBar.activeBackground": F0, "titleBar.activeForeground": DOUX, "titleBar.inactiveBackground": F0, "titleBar.inactiveForeground": MUET,
        "titleBar.border": TRAIT, "menubar.selectionBackground": F3, "menu.background": F2, "menu.foreground": TEXTE,
        "menu.selectionBackground": F4, "menu.selectionForeground": "#ffffff", "menu.separatorBackground": TRAIT, "menu.border": TRAIT,
        "commandCenter.background": F2, "commandCenter.border": TRAIT, "commandCenter.foreground": DOUX, "commandCenter.activeBackground": F3,
        # barre d'activité, barre latérale
        "activityBar.background": F0, "activityBar.foreground": A, "activityBar.inactiveForeground": MUET, "activityBar.border": TRAIT,
        "activityBar.activeBorder": A, "activityBarBadge.background": BLEU, "activityBarBadge.foreground": F0,
        "sideBar.background": F1, "sideBar.foreground": DOUX, "sideBar.border": TRAIT, "sideBarTitle.foreground": BLEU,
        "sideBarSectionHeader.background": F1, "sideBarSectionHeader.foreground": BLEU, "sideBarSectionHeader.border": TRAIT,
        # listes et arbres
        "list.activeSelectionBackground": F4, "list.activeSelectionForeground": "#ffffff", "list.inactiveSelectionBackground": F3,
        "list.inactiveSelectionForeground": TEXTE, "list.hoverBackground": F3, "list.hoverForeground": TEXTE, "list.focusOutline": BLEU + "88",
        "list.highlightForeground": BLEU, "list.focusHighlightForeground": AF, "list.errorForeground": ROUGE, "list.warningForeground": AMBRE,
        "list.dropBackground": BLEU + "33", "tree.indentGuidesStroke": BLEU_FONCE, "tree.inactiveIndentGuidesStroke": F3,
        "listFilterWidget.background": F3, "listFilterWidget.outline": BLEU,
        # éditeur
        "editor.background": F2, "editor.foreground": TEXTE, "editorCursor.foreground": A, "editorLineNumber.foreground": MUET,
        "editorLineNumber.activeForeground": A, "editor.lineHighlightBackground": "#161b28", "editor.lineHighlightBorder": "#00000000",
        "editor.selectionBackground": BLEU + "40", "editor.inactiveSelectionBackground": BLEU + "22", "editor.selectionHighlightBackground": BLEU + "26",
        "editor.wordHighlightBackground": VIOLET + "30", "editor.wordHighlightStrongBackground": ROSE + "30",
        "editor.findMatchBackground": A + "66", "editor.findMatchBorder": A, "editor.findMatchHighlightBackground": AMBRE + "40",
        "editor.findRangeHighlightBackground": BLEU + "18", "editor.hoverHighlightBackground": BLEU + "22",
        "editor.rangeHighlightBackground": BLEU + "14", "editorWhitespace.foreground": F4, "editorIndentGuide.background1": "#1c2333",
        "editorIndentGuide.activeBackground1": "#3a4662", "editorRuler.foreground": TRAIT, "editorBracketMatch.background": BLEU + "22",
        "editorBracketMatch.border": BLEU, "editorBracketHighlight.foreground1": AMBRE, "editorBracketHighlight.foreground2": ROSE,
        "editorBracketHighlight.foreground3": BLEU, "editorBracketHighlight.foreground4": VERT, "editorBracketHighlight.foreground5": VIOLET,
        "editorBracketHighlight.foreground6": ORANGE, "editorBracketHighlight.unexpectedBracket.foreground": ROUGE,
        "editorError.foreground": ROUGE, "editorWarning.foreground": AMBRE, "editorInfo.foreground": BLEU, "editorHint.foreground": TURQUOISE,
        "editorGutter.addedBackground": VERT, "editorGutter.modifiedBackground": BLEU, "editorGutter.deletedBackground": ROUGE,
        "editorOverviewRuler.border": "#00000000", "editorOverviewRuler.findMatchForeground": A + "aa",
        "editorOverviewRuler.errorForeground": ROUGE, "editorOverviewRuler.warningForeground": AMBRE, "editorOverviewRuler.infoForeground": BLEU,
        "editorCodeLens.foreground": MUET, "editorLink.activeForeground": BLEU, "editorInlayHint.foreground": PALE, "editorInlayHint.background": F3,
        "editorGroup.border": TRAIT, "editorGroupHeader.tabsBackground": F0, "editorGroupHeader.tabsBorder": TRAIT, "editorGroup.dropBackground": BLEU + "22",
        "editorWidget.background": F1, "editorWidget.border": TRAIT, "editorWidget.foreground": TEXTE,
        "editorSuggestWidget.background": F1, "editorSuggestWidget.border": TRAIT, "editorSuggestWidget.selectedBackground": F4,
        "editorSuggestWidget.highlightForeground": A, "editorSuggestWidget.focusHighlightForeground": AF,
        "editorHoverWidget.background": F1, "editorHoverWidget.border": F4, "editorStickyScroll.background": F2, "editorStickyScrollHover.background": F3,
        "diffEditor.insertedTextBackground": VERT + "22", "diffEditor.removedTextBackground": ROUGE + "22",
        "diffEditor.insertedLineBackground": VERT + "14", "diffEditor.removedLineBackground": ROUGE + "14",
        "minimap.findMatchHighlight": A, "minimap.selectionHighlight": BLEU, "minimap.errorHighlight": ROUGE, "minimap.warningHighlight": AMBRE,
        "minimapSlider.background": "#ffffff14", "minimapSlider.hoverBackground": "#ffffff22",
        # onglets
        "tab.activeBackground": F2, "tab.activeForeground": "#ffffff", "tab.activeBorderTop": A, "tab.inactiveBackground": F0,
        "tab.inactiveForeground": PALE, "tab.border": TRAIT, "tab.hoverBackground": F3, "tab.unfocusedActiveBorderTop": MUET,
        "tab.unfocusedActiveForeground": DOUX, "tab.activeModifiedBorder": BLEU, "tab.inactiveModifiedBorder": BLEU_FONCE,
        "breadcrumb.background": F2, "breadcrumb.foreground": PALE, "breadcrumb.focusForeground": BLEU, "breadcrumb.activeSelectionForeground": A,
        # panneau, terminal
        "panel.background": F1, "panel.border": TRAIT, "panelTitle.activeForeground": BLEU, "panelTitle.activeBorder": A,
        "panelTitle.inactiveForeground": PALE, "panelSectionHeader.background": F2,
        "terminal.background": F1, "terminal.foreground": TEXTE, "terminalCursor.foreground": A, "terminal.selectionBackground": BLEU + "44",
        "terminal.ansiBlack": "#1a2030", "terminal.ansiRed": ROUGE, "terminal.ansiGreen": VERT, "terminal.ansiYellow": AMBRE,
        "terminal.ansiBlue": "#4d9bff", "terminal.ansiMagenta": VIOLET, "terminal.ansiCyan": TURQUOISE, "terminal.ansiWhite": DOUX,
        "terminal.ansiBrightBlack": MUET, "terminal.ansiBrightRed": "#ff7a86", "terminal.ansiBrightGreen": "#7df0aa",
        "terminal.ansiBrightYellow": "#ffd76b", "terminal.ansiBrightBlue": BLEU, "terminal.ansiBrightMagenta": ROSE,
        "terminal.ansiBrightCyan": "#6ff0e0", "terminal.ansiBrightWhite": "#ffffff",
        # barre d'état
        "statusBar.background": F0, "statusBar.foreground": PALE, "statusBar.border": TRAIT, "statusBar.noFolderBackground": F0,
        "statusBar.debuggingBackground": ORANGE, "statusBar.debuggingForeground": F0, "statusBarItem.hoverBackground": F3,
        "statusBarItem.remoteBackground": v["bouton"], "statusBarItem.remoteForeground": v["sur_bouton"],
        "statusBarItem.prominentBackground": F3, "statusBarItem.errorBackground": "#b3202f", "statusBarItem.warningBackground": "#8a5a00",
        # champs, boutons, pastilles
        "input.background": F3, "input.foreground": TEXTE, "input.border": F4, "input.placeholderForeground": MUET,
        "inputOption.activeBorder": BLEU, "inputOption.activeBackground": BLEU + "33", "inputOption.activeForeground": "#ffffff",
        "inputValidation.errorBackground": "#3a1218", "inputValidation.errorBorder": ROUGE, "inputValidation.warningBackground": "#33260a",
        "inputValidation.warningBorder": AMBRE, "inputValidation.infoBackground": "#0a2533", "inputValidation.infoBorder": BLEU,
        "dropdown.background": F3, "dropdown.foreground": TEXTE, "dropdown.border": F4, "dropdown.listBackground": F2,
        "button.background": v["bouton"], "button.foreground": v["sur_bouton"], "button.hoverBackground": AF, "button.border": "#00000000",
        "button.secondaryBackground": F4, "button.secondaryForeground": TEXTE, "button.secondaryHoverBackground": "#313b54",
        "checkbox.background": F3, "checkbox.border": F4, "checkbox.foreground": A,
        "badge.background": BLEU, "badge.foreground": F0, "progressBar.background": A,
        "scrollbar.shadow": "#00000066", "scrollbarSlider.background": "#ffffff14", "scrollbarSlider.hoverBackground": "#ffffff26",
        "scrollbarSlider.activeBackground": BLEU + "66",
        # palette de commandes, notifications, divers
        "quickInput.background": F1, "quickInput.foreground": TEXTE, "quickInputTitle.background": F0, "quickInputList.focusBackground": F4,
        "quickInputList.focusForeground": "#ffffff", "pickerGroup.foreground": BLEU, "pickerGroup.border": TRAIT,
        "notifications.background": F1, "notifications.foreground": TEXTE, "notifications.border": TRAIT, "notificationCenterHeader.background": F0,
        "notificationsErrorIcon.foreground": ROUGE, "notificationsWarningIcon.foreground": AMBRE, "notificationsInfoIcon.foreground": BLEU,
        "notificationLink.foreground": BLEU, "peekView.border": BLEU, "peekViewEditor.background": F1, "peekViewResult.background": F0,
        "peekViewTitle.background": F0, "peekViewTitleLabel.foreground": TEXTE, "peekViewEditor.matchHighlightBackground": A + "44",
        "peekViewResult.matchHighlightBackground": A + "44", "peekViewResult.selectionBackground": F4,
        "settings.headerForeground": BLEU, "settings.modifiedItemIndicator": BLEU, "keybindingLabel.background": F3,
        "keybindingLabel.foreground": TEXTE, "keybindingLabel.border": F4, "keybindingLabel.bottomBorder": F4,
        "gitDecoration.addedResourceForeground": VERT, "gitDecoration.modifiedResourceForeground": AMBRE,
        "gitDecoration.deletedResourceForeground": ROUGE, "gitDecoration.untrackedResourceForeground": TURQUOISE,
        "gitDecoration.ignoredResourceForeground": MUET, "gitDecoration.conflictingResourceForeground": VIOLET,
        "gitDecoration.renamedResourceForeground": BLEU, "testing.iconPassed": VERT, "testing.iconFailed": ROUGE, "testing.iconQueued": AMBRE,
        "charts.red": ROUGE, "charts.blue": BLEU, "charts.yellow": AMBRE, "charts.orange": ORANGE, "charts.green": VERT, "charts.purple": VIOLET,
        "debugToolBar.background": F1, "debugIcon.breakpointForeground": ROUGE, "editor.stackFrameHighlightBackground": AMBRE + "33",
        "welcomePage.tileBackground": F1, "walkThrough.embeddedEditorBackground": F0,
    }


def jetons():
    r = lambda nom, portee, couleur, style=None: {"name": nom, "scope": portee,
                                                    "settings": {"foreground": couleur, **({"fontStyle": style} if style is not None else {})}}
    return [
        r("Commentaires", ["comment", "punctuation.definition.comment", "string.comment"], "#5f6c88", "italic"),
        r("Mots-clés", ["keyword", "storage", "storage.type", "storage.modifier", "keyword.control", "keyword.other"], ROSE),
        r("Opérateurs", ["keyword.operator", "punctuation.accessor", "punctuation.separator.key-value"], "#8fd8ff"),
        r("Ponctuation", ["punctuation", "meta.brace", "punctuation.definition.block", "punctuation.terminator"], "#95a0b8"),
        r("Chaînes", ["string", "punctuation.definition.string", "string.quoted"], CITRON),
        r("Échappements et expressions régulières", ["constant.character.escape", "string.regexp", "constant.other.placeholder",
                                                     "punctuation.definition.template-expression", "punctuation.section.embedded"], TURQUOISE),
        r("Nombres", ["constant.numeric", "keyword.other.unit"], ORANGE),
        r("Constantes du langage", ["constant.language", "variable.language", "support.constant"], VIOLET),
        r("Constantes", ["constant", "variable.other.constant", "variable.other.enummember"], "#d0a8ff"),
        r("Fonctions", ["entity.name.function", "support.function", "meta.function-call", "variable.function", "meta.function-call.generic"], BLEU),
        r("Classes et types", ["entity.name.type", "entity.name.class", "support.type", "support.class", "entity.other.inherited-class",
                               "entity.name.namespace", "storage.type.primitive"], TURQUOISE),
        r("Variables", ["variable", "meta.definition.variable", "variable.other.readwrite"], TEXTE),
        r("Paramètres", ["variable.parameter", "meta.parameter"], "#ffb38a", "italic"),
        r("Propriétés", ["variable.other.property", "variable.other.object.property", "meta.object-literal.key", "support.variable.property",
                         "support.type.property-name", "entity.name.tag.yaml"], "#8ab8ff"),
        r("Décorateurs et annotations", ["meta.decorator", "entity.name.function.decorator", "punctuation.definition.decorator",
                                         "meta.annotation", "storage.type.annotation"], AMBRE),
        r("Balises", ["entity.name.tag", "punctuation.definition.tag"], ROSE),
        r("Attributs", ["entity.other.attribute-name"], AMBRE, "italic"),
        r("Sélecteurs CSS", ["entity.other.attribute-name.class.css", "entity.other.attribute-name.id.css", "entity.name.tag.css"], TURQUOISE, ""),
        r("Propriétés CSS", ["support.type.property-name.css", "meta.property-name.css"], "#8ab8ff"),
        r("Valeurs CSS", ["support.constant.property-value.css", "constant.other.color"], ORANGE),
        r("Clés JSON", ["support.type.property-name.json", "meta.structure.dictionary.key.python string"], "#8ab8ff"),
        # Markdown, ses choix du 17/11 : sections en jaune, gras (titre d'une puce) en vert citron, code en ligne (le
        # « gras secondaire ») en bleu, tout ce qui est barré en rouge
        r("Titres Markdown", ["markup.heading", "entity.name.section", "punctuation.definition.heading"], JAUNE, "bold"),
        r("Gras", ["markup.bold"], CITRON, "bold"),    # corrigé le 17/11 (19e séance) : j'avais inversé avec le code en ligne
        r("Code en ligne", ["markup.inline.raw", "markup.inline.raw punctuation.definition.raw", "markup.bold markup.inline.raw"], BLEU),
        r("Italique", ["markup.italic"], VIOLET, "italic"),
        r("Barré", ["markup.strikethrough", "markup.strikethrough markup.inline.raw", "markup.strikethrough string",
                    "markup.strikethrough punctuation.definition.raw", "markup.strikethrough markup.italic"], FERRARI, "strikethrough"),
        r("Barré en gras", ["markup.strikethrough markup.bold", "markup.bold markup.strikethrough",
                            "markup.bold markup.strikethrough markup.inline.raw", "markup.strikethrough markup.bold markup.inline.raw"],
          FERRARI, "bold strikethrough"),
        r("Liens", ["markup.underline.link", "string.other.link", "meta.link"], BLEU),
        r("Listes et citations", ["punctuation.definition.list.begin", "markup.quote", "punctuation.definition.quote.begin"], ROSE),
        r("Ajouté", ["markup.inserted", "punctuation.definition.inserted"], VERT),
        r("Retiré", ["markup.deleted", "punctuation.definition.deleted"], ROUGE),
        r("Modifié", ["markup.changed", "meta.diff.range", "meta.diff.header"], BLEU),
        r("Invalide", ["invalid", "invalid.illegal"], ROUGE, "underline"),
    ]


SEMANTIQUE = {
    "function": BLEU, "method": BLEU, "class": TURQUOISE, "type": TURQUOISE, "interface": TURQUOISE, "struct": TURQUOISE,
    "enum": TURQUOISE, "enumMember": "#d0a8ff", "namespace": "#7fe3d6", "parameter": {"foreground": "#ffb38a", "italic": True},
    "property": "#8ab8ff", "variable": TEXTE, "variable.readonly": "#d0a8ff", "variable.defaultLibrary": VIOLET,
    "decorator": AMBRE, "macro": AMBRE, "keyword": ROSE, "number": ORANGE, "string": CITRON, "selfParameter": {"foreground": VIOLET, "italic": True},
}

os.makedirs(OUT, exist_ok=True)
for cle, v in VARIANTES.items():
    chemin = os.path.join(OUT, f"red-stack-{cle}.json")
    json.dump({"$schema": "vscode://schemas/color-theme", "name": v["nom"], "type": "dark", "semanticHighlighting": True,
               "colors": couleurs(v), "tokenColors": jetons(), "semanticTokenColors": SEMANTIQUE},
              open(chemin, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(chemin, len(couleurs(v)), "couleurs")
