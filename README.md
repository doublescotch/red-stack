# Red Stack

A mod manager for Cyberpunk 2077, inside VS Code. Your repository of zips stays the only library:
Red Stack reads the zips where you file them, does not copy them and does not move them.

- **What it does, how to start, settings:** [source/extension/README.md](source/extension/README.md)
  ([Français](source/extension/README.fr.md)). The full manual is inside the extension (“?” button).
- **Requirements:** Windows, VS Code 1.90 or later, Python 3.11 or later.
- **Licence:** MIT ([LICENSE](LICENSE)).

## Layout of this repository

| Path | Content |
| --- | --- |
| `source/extension/` | The VS Code extension: `extension.js`, the page (`media/page.html`), the manual, the themes, the language catalogues (`langues/`) |
| `source/extension/moteur/` | The engine (`red_stack.py`, Python, standard library only) and the two MCP servers |
| `source/extension/test/`, `source/tests/` | The benches: engine, MCP servers, extension under Node, page rendering, languages |
| `source/empaquette.py` | Builds the `.vsix` package, without any third-party tool |

## Building and testing

```
python -I source/empaquette.py                       # builds releases/red-stack-<version>.vsix
python -I source/tests/red_stack_test.py             # engine bench (synthetic repository and game)
python -I source/tests/langues_test.py               # language catalogues against the code (run from source/)
```

The code, its comments and its identifiers are written in French; the interface exists in eleven
languages. Corrections to a translation are welcome as issues.
