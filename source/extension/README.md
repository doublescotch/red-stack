# Red Stack

English · [Français](README.fr.md)

A mod manager for Cyberpunk 2077, inside VS Code. Your repository of zips stays the only library:
Red Stack reads the zips where you file them, does not copy them and does not move them.

## What the page does

- One table per stack (a folder of your repository), one checkbox per mod and one per stack.
- Profiles: each one says which mods are enabled and what is taken from each zip.
- The detail of a mod: its files, where they go in the game, which ones are linked, copied,
  overwritten by another mod or modified in game; the options of a pack to pick from, and one
  checkbox per file to take or leave a single file (the game only changes at “Apply”).
- “Which mod owns this file?”: part of a game path, then Enter.
- The plan preview: what would be installed, replaced, removed, and the conflicts to settle.
  Each disabled mod has its line: what leaves the game, what another mod takes over or already holds.
- “Conflicts”: the analysis of the resources that several archives ship. The game takes each one
  from the first loaded archive (name order, or `modlist.txt`): an archive wins over those loaded
  after it and loses against those before it; identical copies are counted apart. The analysis
  opens in a tab of its own, beside the page: per archive, per mod, per mod pair or per resource,
  with a mention of the resources that replace a base game file. In the list, a badge per mod
  (▼ loses, ▲ wins) opens a box on hover.
- Changing the load order, from that analysis: “Move ahead…” on the archive that wins against
  yours, or “Rename in the game…”. Two ways to choose from: another name for the archive in the
  game (the zip is never touched, the author's name is restored in one click), or `modlist.txt`
  held by the profile. Red Stack proposes a name as close as possible, says who quotes the archive
  by its name in the repository, and only writes the profile: the game follows at the next “Apply”.
- “Scripts and tweaks…”, in the conflicts tab: a separate analysis, that of code conflicts. Two
  mods that replace the same Redscript method, a wrapper that does not call `wrappedMethod`, the
  same TweakXL property set to two values, an addition against a removal, a hard-coded `SetFlat`
  against the tweak of another mod. Three levels (to look at, to review, no action), chips by
  sort, a filter, and each row opens the file at the right line. The “last word” announced is
  predicted from the order of the file names, not observed in the game. Detection taken from
  Conflict Studio (MIT). Read-only.
- “Items”: a separate analysis that reads a game save. For each mod of the profile, the weapons,
  clothing, cyberware, weapon attachments and equipment mods its TweakXL tweaks create, and
  whether the save holds them: on V, in the stash, in the wardrobe or installed on an item. The
  kind of an item built on a game item is read in the game's own database (`tweakdb.bin`). The mods with no item owned come first: a way to spot the item mods
  you do not use. The save is only read, never written (format after WolvenKit, MIT).
- “Arrivals”: the archives of the arrival folders, the names in the format of the Nexus app and
  the `.7z` / `.rar` files. Red Stack proposes the name of the Nexus site
  (`Name-modId-version-timestamp`, read through the public Nexus API), you edit it and then
  rename; it converts to `.zip` and moves a zip into its stack or parks it, row by row or all the
  ticked rows in one confirmation.
  In the list, the “New”, “Parked” and “Retired” filters show these folders; a filed zip can be
  moved into the stack, parked or retired there (moved to the retired folder, never erased), alone
  or as a lot; a retired zip can be deleted (Windows recycle bin, recorded in the history). The page locks while an action
  is writing. In the plan, a file that is present and that Red Stack did not install is replaced
  by the one from the zip when you say so, the old one copied to the backups.
  “Content…” proposes, mod by mod, to rename what the zip ships (archives, script and tweak
  folders) after reading the references of the whole repository: nothing is proposed that breaks
  a hard-coded quote or the load order, and each path can still be edited, its folder included
  (a folder that does not exist is created in the zip; “Add the folder” inserts one under the scripts and tweaks); the folder where the zips of the same family
  already keep their scripts or tweaks is proposed. The same action is in
  the detail of any mod of the list (“Rename the content…”).
- “In-game names…”, in the detail of a mod: install its archives, its `.xl` files, its script and
  tweak files and folders, its CET or REDmod folder under other names, without touching the zip.
  The profile records the name, “Apply” installs the new one and removes the old one, an emptied
  field restores the author's name. Each row says who quotes this name in the repository, the mod
  itself included.
- “History”: what Red Stack has written, action by action. Each “Apply” unfolds mod by mod
  (installed, removed, updated from such a version), and each action on the repository is there too.
- “Store”: the state of the links and the real size. Windows Explorer counts a linked file twice
  (in the tree of the mod and in the game); the panel says what the disk really holds, how many
  game files are linked or copied, which trees no longer serve any enabled mod (“Purge…” deletes
  them, the zips are not touched) and which files of a tree were edited (“Undo…” puts back those
  of the zip).
- FOMOD: a zip that carries `fomod/ModuleConfig.xml` is installed by its installer. “Installer…”
  (detail of the mod) shows its pages, its groups of choices, descriptions and images; a click
  records the choice in the profile, and the pages and files that depend on it follow. The files
  it copies outside the game folders can be left out with a checkbox; the installer can be ignored
  to pick by hand.
- Requirements: the detail of a mod lists what it needs, from the list its author gives on Nexus and from
  the frameworks deduced from where its files go (CET, RED4ext, redscript, TweakXL, ArchiveXL…), with the
  zip that provides each one and its state. An active mod that lacks a framework is flagged in the list
  and in the plan preview.
- The version of a REDmod is read from its `info.json` when the name of the zip has none.
- “Updates”: each zip named in the form of the Nexus site is compared with the published files of
  its mod. The new version is downloaded in place of the old one, which is filed in the retired
  folder of its stack; the profile follows, and what remains is to read the plan preview and
  apply. The name of the new zip can be edited, a mod can be ignored, and doubtful cases (archived
  file, build for another patch of the game) are shown “to check” and never ticked by default.
- Looking for updates needs no key. Downloading needs your personal Nexus API key: it is typed in
  VS Code, stays in its secret storage (`SecretStorage`) and is written in no file. Premium
  account: direct link. Free account: Nexus requires the “Mod manager download” button of its
  site; Red Stack opens the page of the file and waits for the `nxm://` link, pasted by you or
  received on its own if it is registered for these links.
- `nxm://` links (Windows): “Settings”, “This machine”, registers Red Stack as the program for
  these links for your account (one key in the user registry, without administrator rights,
  undone from the same place). “Mod manager download” then sends the file to Red Stack, which
  proposes the zip of the same mod to update, or the stack whose arrival folder receives a new
  mod. Nothing is downloaded without that choice.
- Without an API key: download the file by hand into an arrival folder; “Arrivals” recognises it
  as the update of a mod in place and “File the update…” puts it in its place, the old version in
  the retired folder.
- The list re-reads itself when a zip arrives, leaves or changes in a stack, when
  `archive\pc\mod` changes or when a profile is written elsewhere; the ↻ button re-reads on demand.
- The side bar (Red Stack icon) carries the profile, the figures of the last state read and
  shortcuts to the plan, the conflicts, the arrivals and the settings.

- The full manual, view by view, opens in a tab: the “?” button of the page, the “Manual” line of
  the side bar, or the command “Red Stack: Manual”.

Ticking a box only changes the profile. The game is written only after the plan preview and a
confirmation, and only the plan you saw is applied.

## Getting started

Python 3.11 or later is needed on the machine; the engine is inside the extension, nothing else to install. If Red Stack
finds none (`python`, `py -3`, `python3`), the page says so and offers to download it or to set its command.

Your repository stays as it is: stacks (folders) of zips, or loose zips in a single folder, then read as one more
stack. A folder the convention does not read is named on screen, never left out silently.

Open the page: the “Red Stack” button of the status bar, or the command “Red Stack: Open”.
On first launch, the page asks for two folders: your zip repository and the game folder.
It then offers to read the game to create the profile “actuel” (current); this reading writes nothing.

## Settings

The “Settings” button of the page sets everything the tool remembers:

- the folders: repository, game, store (one extracted tree per mod, linked to the game), backups,
  game reference, game saves (read by “Items”), log;
- the convention of your repository: which folders are stacks, which ones are parked, new,
  retired, which folders of a zip are never installed;
- the settings files of the mods, copied instead of being linked so that they survive updates;
- “outside Red Stack”: the folders of a third-party installer (ReShade), never touched;
  In the detail of a mod, a checkbox per file says “this file belongs to this mod”: it then
  leaves with it.
- the settings backups: “Back up now” copies to the backups folder all the settings of the mods
  present in the game, shipped by a zip or written in game; “Compare with the game” shows what
  has changed since, “Restore…” puts it back (game closed, today's files are copied first);
- a command to run before any writing of the game (your backup, for example);
- the game reference: a copy of the game without its archives, to check or restore the base game.

These settings live in `config.json`, in the data folder. A few settings belong to the machine and
are also in the VS Code settings:

| Setting | Role |
| --- | --- |
| `redStack.python` | Python command (default: `python`) |
| `redStack.donnees` | Data folder: profiles, install registry, `config.json` (default: the storage folder of the extension) |
| `redStack.moteur` | Another `red_stack.py` than the packaged one (development) |
| `redStack.actualisationAuto` | Re-read the repository and the game on its own when the disk changes (ticked by default) |
| `redStack.barreEnCouleur` | Red Stack themes: every activity bar icon in the accent colour |
| `redStack.langue` | Interface language: `auto` (that of VS Code), `fr`, `en`, `de`, `es`, `pt-br`, `it`, `pl`, `ru`, `zh-cn`, `ja` or `ko` |

## Languages

The page, the side bar and the messages of the extension exist in eleven languages (French, English, German, Spanish,
Brazilian Portuguese, Italian, Polish, Russian, Simplified Chinese, Japanese, Korean); the choice is made in
“Settings”, “Language” section (by default: the language of VS Code, English for a language Red Stack does not have).
The messages of the engine follow this choice (`red_stack.py --langue <code>`, same catalogue); its states returned as JSON
(“posé”, “coupé”…) stay codes, which the page words in its language. Both MCP servers speak English. The built-in manual
exists in French and in English (English for any language other than French). A catalogue is a file
`langues/<code>.json` whose keys are the French texts of the code (extension, page and engine); `tests/langues_test.py`
says what is missing. A plural is written `N(n, '{n} fichier', '{n} fichiers')` (extension, page and engine): the
catalogue then carries an object of forms (`one`, `few`, `many`, `other`, those the language needs). All the texts,
in the eleven languages, are written by an AI: French is the source language, the ten others, English included, are
translations of it, checked by the bench and not yet proofread by native speakers. Corrections are welcome as issues.

## Themes

Two complete colour themes come with the extension: “Red Stack Rouge” (red) and “Red Stack Jaune” (yellow). They are
activated in one click in “Settings”, “Theme” section (or with `Ctrl+K Ctrl+T`). Midnight blue background, one accent, a
bright blue as second colour; the Red Stack page follows the current theme, yours included. The screenshots of this page
are made with the [vscode-icons](https://marketplace.visualstudio.com/items?itemName=vscode-icons-team.vscode-icons)
icon pack, which we recommend with these themes.

## Driving by a Claude Code session

The package carries an MCP server (28 tools): a session reads the state, the conflicts, the history,
the arrivals and the proposed updates, changes a profile and prepares a plan. It writes neither
the game nor the zip repository: parking, renaming, downloading stay your actions, in the page.
For the game, it leaves a request, which this extension shows you (plan with its figures, Apply or
Refuse). The command that declares it, with the right paths, can be copied from the page:
“Settings”, “This machine” section.

A second MCP server (11 `wk_` tools), declared separately, drives the WolvenKit CLI: search for a
resource in the archives of the game and of the mods, list an archive, extract, export a texture
or a mesh, read a CR2W file as JSON, edit it (the CLI rebuilds the file then reads it back),
import an image or a `.glb`, pack a folder into an `.archive`, build a WolvenKit project.
To build, it only reads from, and it only writes to, a workshop folder that you name (“Settings”,
“WolvenKit” section); it refuses a pattern that would take everything and counts the files before
extracting. What it makes stays in the workshop: installing it in the game stays your action. The
WolvenKit CLI is downloaded separately.
