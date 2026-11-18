# Red Stack

[English](README.md) · Français

Gestionnaire de mods pour Cyberpunk 2077, dans VS Code. Votre dépôt de zips reste la seule
bibliothèque : Red Stack lit les zips là où vous les rangez, ne les copie pas et ne les déplace pas.

## Ce que fait la page

- Une table par pile (dossier de votre dépôt), une case par mod et une case par pile.
- Des profils : chacun dit quels mods sont actifs et ce qu'on prend de chaque zip.
- Le détail d'un mod : ses fichiers, où ils vont dans le jeu, lesquels sont liés, copiés, écrasés
  par un autre mod ou modifiés en jeu ; les options d'un pack à piocher, et une
  case par fichier pour prendre ou laisser un fichier seul (le jeu ne change qu'à « Appliquer »).
- « À quel mod est ce fichier ? » : le texte d'un chemin du jeu, puis Entrée.
- L'aperçu du plan : ce qui serait posé, remplacé, retiré, et les conflits à trancher.
  Chaque mod coupé y a sa ligne : ce qui sort du jeu, ce qu'un autre mod reprend ou tient déjà.
- « Conflits » : l'analyse des ressources que plusieurs archives livrent. Le jeu prend chacune dans
  la première archive chargée (ordre des noms, ou `modlist.txt`) : une archive gagne sur celles
  chargées après elle, perd contre celles d'avant ; les copies identiques sont à part. L'analyse
  s'ouvre dans un onglet à elle, à côté de la page : par archive, par mod, par paire de mods ou
  par ressource, avec la mention des ressources qui remplacent un fichier du jeu de base. Dans la
  liste, une pastille par mod (▼ perd, ▲ gagne) ouvre une boîte au survol.
- Changer l'ordre de chargement, depuis cette analyse : « Passer devant… » sur l'archive qui gagne
  contre la vôtre, ou « Renommer dans le jeu… ». Deux voies au choix : un autre nom pour l'archive
  dans le jeu (le zip n'est jamais touché, le nom de l'auteur se rend d'un clic), ou `modlist.txt`
  tenu par le profil. Red Stack propose un nom au plus près, dit qui cite l'archive par son nom
  dans le dépôt, et n'écrit que le profil : le jeu suit au prochain « Appliquer ».
- « Scripts et tweaks… », dans l'onglet des conflits : une analyse à part, celle des conflits de
  code. Deux mods qui remplacent la même méthode Redscript, une enveloppe qui n'appelle pas
  `wrappedMethod`, la même propriété TweakXL posée à deux valeurs, un ajout contre un retrait,
  un `SetFlat` écrit en dur contre le tweak d'un autre mod. Trois niveaux (à regarder, à revoir,
  sans action), des puces par sorte, un filtre, et chaque ligne ouvre le fichier à la bonne
  ligne. Le « dernier mot » annoncé est prévu d'après l'ordre des noms de fichiers, pas observé
  dans le jeu. Détection reprise de Conflict Studio (MIT). Lecture seule.
- « Arrivages » : les archives des dossiers d'arrivée, les noms au format de l'application Nexus
  et les `.7z` / `.rar`. Red Stack propose le nom du site Nexus (`Nom-modId-version-horodatage`,
  lu par l'API publique de Nexus), vous le retouchez puis vous renommez ; il convertit en `.zip`
  et remonte ou parque un zip, ligne par ligne ou toutes les lignes cochées en une confirmation.
  Dans la liste, les filtres « Nouveaux », « Parqués » et « Retirés » montrent ces dossiers ; un zip
  rangé s'y remonte, s'y parque ou s'y retire (déplacé dans les retirés, jamais effacé), seul ou en lot ;
  un zip des retirés peut être supprimé (corbeille de Windows, geste inscrit à l'historique). La page se verrouille pendant qu'un
  geste écrit. Dans le plan, un fichier présent que Red Stack n'a pas posé se remplace par celui du
  zip sur votre désignation, l'ancien copié dans les sauvegardes.
  « Contenu… » propose, mod par mod, de renommer ce que le zip livre (archives, dossiers de
  scripts et de tweaks) après lecture des références de tout le dépôt : rien n'est proposé qui
  casse une citation en dur ou l'ordre de chargement, et chaque chemin reste retouchable, dossier compris (un
  dossier qui n'existe pas est créé dans le zip ; « Ajouter le dossier » en insère un sous les scripts et les tweaks) ; le dossier où les zips de la même famille rangent
  déjà leurs scripts ou leurs tweaks est proposé. Le même
  geste est dans le détail de tout mod de la liste (« Renommer le contenu… »).
- « Noms dans le jeu… », dans le détail d'un mod : poser ses archives, ses `.xl`, ses fichiers et
  dossiers de scripts et de tweaks, son dossier CET ou REDmod sous d'autres noms, sans toucher
  au zip. Le profil note le nom, « Appliquer » pose le nouveau et retire l'ancien, un champ vidé
  rend le nom de l'auteur. Chaque ligne dit qui cite ce nom dans le dépôt, le mod lui-même compris.
- « Historique » : ce que Red Stack a écrit, geste par geste. Chaque « Appliquer » se déplie mod
  par mod (posé, retiré, mis à jour depuis telle version), chaque geste sur le dépôt y est aussi.
- « Magasin » : l'état des liens et le poids réel. L'Explorateur de Windows compte deux fois un
  fichier lié (dans l'arbre du mod et dans le jeu) ; le volet dit ce que le disque porte vraiment,
  combien de fichiers du jeu sont liés ou copiés, quels arbres ne servent plus à aucun mod actif
  (« Purger… » les supprime, les zips ne sont pas touchés) et quels fichiers d'un arbre ont été
  retouchés (« Annuler… » remet ceux du zip).
- FOMOD : un zip qui porte `fomod/ModuleConfig.xml` est posé par son installateur. « Installateur… »
  (détail du mod) montre ses pages, ses groupes de choix, descriptions et images ; un clic note le
  choix au profil, les pages et les fichiers qui en dépendent suivent. Les fichiers qu'il copie hors
  des dossiers du jeu se laissent d'une case ; l'installateur s'ignore pour piocher à la main.
- La version d'un REDmod est lue dans son `info.json` quand le nom du zip n'en porte pas.
- « Mises à jour » : chaque zip nommé à la forme du site Nexus est comparé aux fichiers publiés
  de son mod. La nouvelle version se télécharge à la place de l'ancienne, rangée dans le dossier
  des retirés de sa pile ; le profil suit, il reste à lire l'aperçu du plan et à appliquer. Le nom
  du nouveau zip se retouche, un mod s'ignore, les cas douteux (fichier archivé, build pour un
  autre patch du jeu) sont montrés « à voir » et jamais cochés d'office.
- La recherche de mises à jour ne demande aucune clé. Le téléchargement demande votre clé d'API
  personnelle Nexus : elle se saisit dans VS Code, reste dans son coffre (`SecretStorage`) et
  n'est écrite dans aucun fichier. Compte Premium : lien direct. Compte gratuit : Nexus exige le
  bouton « Mod manager download » de son site ; Red Stack ouvre la page du fichier et attend le
  lien `nxm://`, collé par vous ou reçu seul s'il est inscrit pour ces liens.
- Liens `nxm://` (Windows) : « Réglages », « Ce poste », inscrit Red Stack comme programme de ces
  liens pour votre compte (une clé du registre de l'utilisateur, sans droits d'administrateur,
  défaite du même endroit). « Mod manager download » envoie alors le fichier à Red Stack, qui
  propose le zip du même mod à mettre à jour, ou la pile dont le dossier d'arrivée reçoit un mod
  nouveau. Rien n'est téléchargé sans ce choix.
- Sans clé d'API : téléchargez le fichier à la main dans un dossier d'arrivée ; « Arrivages » le
  reconnaît comme la mise à jour d'un mod en place et « Ranger la mise à jour… » le met à sa
  place, l'ancienne version dans les retirés.
- La liste se relit seule quand un zip arrive, part ou change dans une pile, quand
  `archive\pc\mod` change ou qu'un profil est écrit ailleurs ; le bouton ↻ relit sur demande.
- La barre latérale (icône Red Stack) porte le profil, les chiffres du dernier état lu et des
  raccourcis vers le plan, les conflits, les arrivages et les réglages.

- Le manuel complet, vue par vue, s'ouvre dans un onglet : bouton « ? » de la page, ligne « Manuel »
  de la barre latérale, ou commande « Red Stack : manuel ».

Cocher une case ne change que le profil. Le jeu n'est écrit qu'après l'aperçu du plan et une
confirmation, et seul le plan que vous avez vu est appliqué.

## Mise en route

Il faut Python 3.11 ou plus récent sur le poste ; le moteur est dans l'extension, rien d'autre à installer. Si Red Stack
n'en trouve pas (`python`, `py -3`, `python3`), la page le dit et offre de le télécharger ou d'indiquer sa commande.

Votre dépôt reste comme il est : des piles (dossiers) de zips, ou des zips en vrac dans un seul dossier, lus alors
comme une pile de plus. Un dossier que la convention ne lit pas est nommé à l'écran, jamais écarté en silence.

Ouvrir la page : bouton « Red Stack » de la barre d'état, ou commande « Red Stack : ouvrir ».
Au premier lancement, la page demande deux dossiers : votre dépôt de zips et le dossier du jeu.
Elle propose ensuite de lire le jeu pour créer le profil « actuel » ; cette lecture n'écrit rien.

## Réglages

Le bouton « Réglages » de la page règle tout ce que l'outil retient :

- les dossiers : dépôt, jeu, magasin (un arbre extrait par mod, lié au jeu), sauvegardes,
  référence du jeu, journal ;
- la convention de votre dépôt : quels dossiers sont des piles, lesquels sont parqués, nouveaux,
  retirés, quels dossiers d'un zip ne sont jamais posés ;
- les fichiers de réglages des mods, copiés au lieu d'être liés pour survivre aux mises à jour ;
- « hors Red Stack » : les dossiers d'un installateur tiers (ReShade), jamais touchés ;
  Dans le détail d'un mod, une case par fichier dit « ce fichier est à ce mod » : il part alors
  avec lui.
- les sauvegardes des réglages : « Sauvegarder maintenant » copie dans le dossier des sauvegardes
  tous les réglages des mods présents dans le jeu, livrés par un zip ou écrits en jeu ;
  « Comparer au jeu » montre ce qui a changé depuis, « Restaurer… » le remet (jeu fermé, les
  fichiers d'aujourd'hui sont copiés avant) ;
- une commande à lancer avant toute écriture du jeu (votre sauvegarde, par exemple) ;
- la référence du jeu : copie du jeu sans ses archives, pour contrôler ou remettre le socle.

Ces réglages vivent dans `config.json`, dans le dossier des données. Deux réglages sont propres au
poste et se trouvent aussi dans les réglages de VS Code :

| Réglage | Rôle |
| --- | --- |
| `redStack.python` | Commande Python (défaut : `python`) |
| `redStack.donnees` | Dossier des données : profils, registre de pose, `config.json` (défaut : le dossier de stockage de l'extension) |
| `redStack.moteur` | Un autre `red_stack.py` que celui du paquet (développement) |
| `redStack.actualisationAuto` | Relire seul le dépôt et le jeu quand le disque change (coché d'office) |
| `redStack.barreEnCouleur` | Thèmes Red Stack : toutes les icônes de la barre d'activité à la couleur d'accent |
| `redStack.langue` | Langue de l'interface : `auto` (celle de VS Code), `fr`, `en`, `de`, `es`, `pt-br`, `it`, `pl`, `ru`, `zh-cn`, `ja` ou `ko` |

## Langues

La page, la barre latérale et les messages de l'extension existent en onze langues (français, anglais, allemand, espagnol,
portugais du Brésil, italien, polonais, russe, chinois simplifié, japonais, coréen) ; le choix se fait dans
« Réglages », section « Langue » (d'office : la langue de VS Code, l'anglais pour une langue que Red Stack n'a pas).
Les messages du moteur suivent ce choix (`red_stack.py --langue <code>`, même catalogue) ; ses états rendus en JSON
(« posé », « coupé »…) restent des codes, que la page dit dans sa langue. Les deux serveurs MCP parlent anglais. Le manuel
intégré existe en français et en anglais (l'anglais pour toute langue autre que le français). Un catalogue est un fichier `langues/<code>.json` dont les clés sont les textes
français du code (extension, page et moteur) ; `tests/langues_test.py` dit ce qui manque. Un pluriel s'écrit
`N(n, '{n} fichier', '{n} fichiers')` (extension, page et moteur) : le catalogue porte alors un objet de formes (`one`,
`few`, `many`, `other`, celles que la langue demande). Les neuf langues après l'anglais sont des traductions faites par
une IA, contrôlées par le banc et pas encore relues par des locuteurs : les corrections se proposent par ticket.

## Thèmes

Deux thèmes de couleurs complets viennent avec l'extension : « Red Stack Rouge » et « Red Stack
Jaune ». Ils s'activent d'un clic dans « Réglages », section « Thème » (ou par `Ctrl+K Ctrl+T`). Fond bleu nuit, un accent, un bleu vif en second ; la page
Red Stack suit le thème en cours, le vôtre compris. Les captures de cette page sont faites avec le
pack d'icônes [vscode-icons](https://marketplace.visualstudio.com/items?itemName=vscode-icons-team.vscode-icons),
que nous recommandons avec ces thèmes.

## Pilotage par une session Claude Code

Le paquet porte un serveur MCP (26 outils) : une session lit l'état, les conflits, l'historique,
les arrivages et les mises à jour proposées, change un profil et prépare un plan. Elle n'écrit ni
le jeu ni le dépôt de zips : parquer, renommer, télécharger restent vos gestes, dans la page.
Pour le jeu, elle dépose une demande, que cette extension vous montre (plan
chiffré, Appliquer ou Refuser). La commande qui le déclare, avec les bons chemins, se copie depuis
la page : « Réglages », section « Ce poste ».

Un second serveur MCP (11 outils `wk_`), à déclarer à part, pilote la CLI WolvenKit : chercher une
ressource dans les archives du jeu et des mods, lister une archive, extraire, exporter une texture
ou un mesh, lire un fichier CR2W en JSON, le retoucher (la CLI refait le fichier puis le relit),
importer une image ou un `.glb`, packer un dossier en `.archive`, construire un projet WolvenKit.
Il ne lit pour fabriquer et n'écrit que dans un dossier d'atelier que vous désignez (« Réglages »,
section « WolvenKit »), refuse un motif qui prendrait tout et compte les fichiers avant d'extraire.
Ce qu'il fabrique reste dans l'atelier : le poser dans le jeu reste votre geste. La CLI WolvenKit
se télécharge à part.
