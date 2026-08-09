# Journal des modifications

Toutes les modifications importantes d'Enterprise IT Automation Suite sont consignées dans ce fichier.

## [À venir]


## [0.8.0-alpha.02] — 2026-08-09

### C8.2A — Exploration et filtrage read-only des ACL

- ajout d'une recherche locale dans les ACE de la DACL ;
- recherche sur principal, SID, droits AD, portée et GUID ;
- filtres combinables `Allow / Deny` et explicites / héritées ;
- compteurs locaux pour les ACE autorisées et refusées ;
- compteur du nombre d'ACE affichées sur le total ;
- remise à zéro automatique des filtres au changement d'objet ;
- message dédié lorsqu'aucune ACE ne correspond aux filtres ;
- styles dédiés aux outils d'exploration ACL ;
- aucune modification backend ou worker Windows ;
- aucune écriture ACL ajoutée.

### Validation

- 16 tests frontend C8.1 + C8.2A ciblés réussis ;
- 320 tests frontend complets réussis ;
- lint : 34 avertissements connus, 0 erreur ;
- build Vite 8.1.3 validé ;
- 12 fichiers statiques de production déployés ;
- intégrité SHA-256 `frontend/dist` / `api/static/app` validée ;
- portail HTTPS validé avec HTTP 200 ;
- recette Microsoft Edge validée sur 36 ACE ;
- filtre `Refuser + Explicites` isolant correctement l'ACE `Tout le monde` ;
- recherche sans résultat et remise à zéro au changement d'objet validées ;
- aucune primitive d'écriture ACL dans le composant source ;
- progression : C8.2A 100 %, C8 25 %, Explorateur AD 95 %, EITAS 90 %.


## [0.8.0-alpha.01] — 2026-08-09

### C8.1 — ACL / DACL Active Directory en lecture seule

- ajout de action `get_security_descriptor` au pipeline AD Explorer ;
- lecture du propriétaire et de la DACL via `Get-Acl` sur le provider Active Directory ;
- résolution des principaux et SID lorsque disponible ;
- exposition des droits AD, Allow / Deny, héritage et GUID objet ;
- comptage séparé des ACE explicites et héritées ;
- SACL volontairement exclue de C8.1 ;
- aucune opération `Set-Acl` ni modification des ACL ;
- ajout de onglet `Sécurité` en lecture seule dans Explorateur AD ;
- affichage du propriétaire, de héritage, des compteurs DACL et des ACE ;
- chargement à la demande avec cache et actualisation explicite.

### Validation

- module Windows PowerShell 5.1 validé avec 0 erreur de parsing ;
- module Windows actif SHA-256 `B2D0CE163EB385714C5D859225F06FA934ECF0E6CE4CAEC2E614C356AF0AEAB3` ;
- job réel read-only validé sur `OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL` ;
- propriétaire `API\\Admins du domaine` et SID correctement remontés ;
- 36 ACE DACL remontées : 10 explicites et 26 héritées ;
- héritage actif et règles non protégées ;
- ACE Deny `Tout le monde` confirmée ;
- 10 tests backend C8.1 ciblés réussis ;
- 10 tests frontend C8.1C ciblés réussis ;
- 314 tests frontend réussis ;
- 469 tests backend et 339 sous-tests réussis ;
- lint : 34 avertissements connus, 0 erreur ;
- build et intégrité SHA-256 du portail validés ;
- recette navigateur onglet Sécurité validée ;
- aucune écriture AD ou ACL ;
- progression : C8.1 100 %, C8 20 %, Explorateur AD 94 %, EITAS 90 %.

## [0.7.0] — 2026-08-08

### C7 — Sélection multiple, copie et glisser-déposer

- clôture stable de C7 ;
- multi-sélection clavier et souris ;
- copie groupée DN, noms et CSV ;
- copie utilisateur contrôlée ;
- glisser-déposer sécurisé vers OU et conteneurs ;
- réutilisation du workflow historique `move_object` ;
- refus des destinations invalides et du drag multi-objet ;
- nettoyage du cycle de vie des sélections validé.

### Validation

- 39 tests C7 consolidés ;
- 304 tests frontend réussis ;
- 459 tests backend et 339 sous-tests réussis ;
- lint : 34 avertissements connus, 0 erreur ;
- aucun bulk destructif ;
- recette navigateur C7.1, C7.2 et C7.3 validée ;
- contrôles de sécurité validés ;
- progression : C7 100 %, Explorateur AD 94 %, EITAS 90 %.

## [0.7.0-alpha.03] — 2026-08-08

### C7.3 — Glisser-déposer et déplacement

- ajout du glisser-déposer des objets AD gérés ;
- destinations limitées aux OU et conteneurs EITAS ;
- retour visuel valide/interdit pendant le drag ;
- refus du parent courant et des descendants invalides ;
- refus du drag en multi-sélection ;
- réutilisation du workflow historique `move_object` ;
- aucun déplacement direct au simple drop ;
- recette Simulation validée sans modification réelle AD.

### Validation

- 10 tests C7.3 ciblés réussis ;
- 297 tests frontend réussis ;
- 459 tests backend et 339 sous-tests réussis ;
- lint : 34 avertissements connus, 0 erreur ;
- build/runtime et SHA-256 publics validés ;
- recette navigateur complète validée ;
- progression : C7.3 100 %, C7 75 %, Explorateur AD 94 %, EITAS 90 %.

## [0.7.0-alpha.02] — 2026-08-08

### C7.2 — Actions de sélection et copie

- ajout d une barre compacte pour la sélection multiple ;
- copie groupée des DN ;
- copie groupée des noms ;
- export CSV vers le presse-papiers ;
- réutilisation du workflow de copie utilisateur pour une sélection utilisateur unique ;
- ajout d une action de désélection explicite ;
- aucun bulk destructif ajouté ;
- aucun changement backend.

### Validation

- 10 tests C7.2 ciblés réussis ;
- 287 tests frontend réussis ;
- lint : 34 avertissements connus, 0 erreur ;
- build et runtime public identiques ;
- intégrité SHA-256 publique validée ;
- recette navigateur des copies DN, noms et CSV validée ;
- navigation `Users` revalidée sans régression ;
- progression : C7.2 100 %, C7 50 %, Explorateur AD 94 %, EITAS 90 %.

## [0.7.0-alpha.01] — 2026-08-08

### C7.1 — Multi-sélection

- ajout de la sélection multiple dans l’Explorateur AD ;
- clic simple, Ctrl/Cmd + clic et Maj + clic ;
- combinaison Ctrl/Cmd + Maj + clic ;
- Ctrl/Cmd + A sur les objets visibles ;
- Échap pour vider la sélection ;
- compteur de sélection ;
- conservation d’un objet primaire pour les propriétés ;
- compatibilité avec les comportements historiques utilisateur et groupe ;

### Validation

- recette navigateur complète validée ;
- 12 tests C7.1 ciblés réussis ;
- 277 tests frontend réussis ;
- 459 tests backend et 339 sous-tests réussis ;
- lint : 34 avertissements connus, 0 erreur ;
- build et runtime public validés ;
- intégrité SHA-256 publique validée ;
- progression : C7.1 100 %, C7 25 %, Explorateur AD 94 %, EITAS 90 %.

## [0.6.0] — 2026-08-08

### C6 — Recherche, colonnes, filtres et requêtes

Cette version stable clôt le chantier C6 à 100 %.

### Fonctionnalités

- recherche Active Directory unifiée ;
- colonnes configurables et tri persistant ;
- filtres avancés combinables ;
- recherches enregistrées persistantes ;
- restauration complète de la requête, des filtres, des colonnes et du tri ;

### Qualification finale

- 34 tests C6 ciblés réussis ;
- 265 tests frontend réussis ;
- 459 tests backend et 339 sous-tests réussis ;
- lint : 34 avertissements connus et 0 erreur ;
- build Vite de production validé ;
- 12 fichiers statiques, 913870 octets ;
- build et runtime déployé strictement identiques ;
- intégrité SHA-256 publique validée ;
- API et portail publics validés ;
- contrôles de sécurité validés ;

### Progression

- C6 : 100 % ;
- Explorateur Active Directory : 94 % ;
- EITAS global : 90 % ;
- prochain chantier : C7.

## [0.6.0-alpha.04] — 2026-08-08

### C6.4 — Recherches enregistrées

- ajout des recherches Active Directory enregistrées ;
- mémorisation de la requête globale, des filtres, des colonnes et du tri ;
- persistance locale avec limite de 20 entrées ;
- protection contre les doublons de nom ;
- actions Charger, Remplacer et Supprimer ;
- chargement par le moteur unifié `search_objects` ;
- compatibilité C6.1, C6.2 et C6.3 conservée ;

### Validation

- recette navigateur complète validée ;
- 34 tests C6 ciblés réussis ;
- 265 tests frontend réussis ;
- 459 tests backend et 339 sous-tests réussis ;
- lint : 34 avertissements connus, 0 erreur ;
- build Vite et publication runtime validés ;
- contrôles de sécurité validés ;
- progression : C6.4 100 %, C6 80 %, Explorateur AD 90 %, EITAS 89 %.

## [0.6.0-alpha.03] — 2026-08-08

### C6.3 — Filtres avancés

- Ajout de filtres avancés dans l’Explorateur Active Directory.
- Filtrage par type d’objet et par état de compte.
- Ajout de critères par colonne avec opérateurs texte et présence/absence de valeur.
- Combinaison de plusieurs critères avec logique ET.
- Compteur de filtres actifs, suppression individuelle et action `Effacer tout`.
- Persistance sécurisée des filtres dans `localStorage`.
- Compatibilité préservée avec la recherche globale C6.1, les colonnes configurables et le tri C6.2.
- Recette navigateur validée avec quatre filtres simultanés, persistance après F5 et réinitialisation fonctionnelle.

### Validation

- 10 tests C6.3 dédiés validés.
- 22 tests ciblés C6.1/C6.2/C6.3 validés.
- Suite frontend complète : 253 tests, 0 échec.
- Lint frontend : 34 warnings connus, 0 erreur.
- Suite backend complète : 459 tests, 37 warnings connus et 339 sous-tests validés.
- Build Vite de production validé.
- Build/runtime exact et 12 fichiers statiques publics vérifiés par SHA-256 via HTTPS.
- Contrôles de sécurité pré-commit validés.
- Progression : C6.3 100 %, C6 60 %, Explorateur AD 86 %, EITAS 88 %.


## [0.6.0-alpha.02] — 2026-08-08

### C6.2 — Colonnes configurables et tri

- Ajout d’un modèle configurable de colonnes dans l’Explorateur Active Directory.
- `Nom` reste obligatoire ; les autres colonnes peuvent être activées ou masquées depuis `☷ Colonnes`.
- Ajout notamment de Compte SAM, UPN, E-mail, DN, Nom d’affichage, Nom DNS, Système, Activé, Étendue, Catégorie et Nom canonique.
- Tri ascendant / descendant par clic sur les en-têtes, avec valeurs vides placées en dernier.
- Persistance sécurisée des colonnes visibles et du tri dans `localStorage`.
- Action `Réinitialiser` pour revenir aux préférences par défaut.
- Correction de visibilité du menu de colonnes par durcissement du contexte d’empilement CSS.
- Recherche globale C6.1 conservée sans régression.
- Recette navigateur validée avec persistance après F5 et réinitialisation fonctionnelle.

### Validation

- 9 tests C6.2 dédiés validés.
- Suite frontend complète : 243 tests, 0 échec.
- Lint frontend : 34 warnings connus, 0 erreur.
- Suite backend complète : 459 tests, 37 warnings connus et 339 sous-tests validés.
- Build Vite de production validé.
- Build/runtime exact et 12 fichiers statiques publics vérifiés par SHA-256 via HTTPS.
- Contrôles de sécurité pré-commit validés.
- Progression : C6.2 100 %, C6 40 %, Explorateur AD 82 %, EITAS 87 %.


## [0.6.0-alpha.01] — 2026-08-08

### C6.1 — Recherche Active Directory unifiée

- Ajout de l’action AD Explorer `search_objects` exécutée nativement par le worker Windows.
- Recherche unifiée des utilisateurs, groupes, ordinateurs, OU, conteneurs Active Directory natifs et contacts.
- Recherche récursive sous une base DN explicite, avec racine de domaine autorisée en lecture seule, échappement LDAP et limite maximale de 1000 résultats.
- Normalisation stricte des six types supportés et exclusion des sous-classes de conteneur non prises en charge.
- Déduplication des résultats par DN dans le frontend.
- Remplacement du fan-out historique de la recherche globale par un seul job `search_objects`.
- Compatibilité Windows PowerShell 5.1 validée avant et après déploiement.
- Runtime réel Active Directory validé avec 175 résultats, exactement six types supportés et aucun DN dupliqué.
- Recette navigateur validée avec recherche globale puis ouverture des propriétés de `Liam Ve`.
- Build frontend publié et vérifié fichier par fichier par SHA-256 via HTTPS.

### Validation

- 7 tests C6.1 backend/worker dédiés validés.
- Suite backend complète : 459 tests, 37 warnings connus et 339 sous-tests validés.
- Suite frontend complète : 234 tests, 0 échec.
- Lint frontend : 34 warnings connus, 0 erreur.
- Build Vite de production validé.
- Contrôles de sécurité pré-commit validés.
- Progression : C6.1 100 %, C6 20 %, Explorateur AD 78 %, EITAS 86 %.


## [0.5.0] — 2026-08-08

### C5-FINAL — Ordinateurs, OU, conteneurs et contacts

- Clôture stable du chantier C5 à 100 %.
- Consolidation des quatre sous-lots C5.1 Ordinateurs, C5.2 OU, C5.3 Contacts et C5.4 Conteneurs Active Directory natifs.
- Ajout d’un test frontend dédié C5.1 pour verrouiller la gestion des ordinateurs.
- Validation navigateur croisée des OU, contacts et conteneurs.
- Protection lecture seule hors périmètre EITAS confirmée sur `SRV-DC01`.
- Aucun ordinateur n’étant actuellement présent sous `OU=EITAS`, aucun fixture artificiel n’a été recré pour la seule recette visuelle.
- Historique AD Admin filtré par objet confirmé en recette finale.
- Mode agent Simulation confirmé avant publication stable.

### Validation

- Matrice backend C5 : 63 tests et 22 sous-tests validés.
- Audit TODO/FIXME C5 : aucun marqueur incomplet réel.
- Suite backend complète : 452 tests, 36 warnings connus et 339 sous-tests validés.
- Suite frontend complète : 231 tests, 0 échec.
- Lint frontend : 34 warnings connus, 0 erreur.
- Build Vite de production validé.
- Contrôles de sécurité pré-commit validés.
- Runtime public HTTPS validé sur le port 62443.
- Progression : C5 100 %, Explorateur AD 74 %, EITAS 85 %.

## [0.5.0-alpha.04] — 2026-08-08
### C5.4 — Conteneurs Active Directory natifs
- Prise en charge de bout en bout des objets `objectClass=container` sans les déguiser en OU.
- Action backend `create_container` et exécution Windows native via `New-ADObject -Type container`.
- Navigation, création, propriétés, renommage, déplacement, suppression et protection contre la suppression accidentelle intégrés au portail.
- Parents structurels OU ou conteneur pris en charge dans le périmètre EITAS.
- Snapshot et lookup live enrichis pour exposer les conteneurs natifs.
- Prévalidations des doublons, collisions, vacuité et protection exécutées avant la frontière Simulation.
- Historique des propriétés filtré par objet et fenêtre AD Admin portée à 1000 jobs pour couvrir l’historique disponible.
- Toasts de succès ajoutés pour la modification de propriétés et le renommage.
- Badge C4 restauré dans le README et conservé à 100 %.
- Version API synchronisée avec le fichier `VERSION` afin d’éviter un numéro de version runtime obsolète.
### Validation
- Suite backend complète : 452 tests, 36 warnings connus et 339 sous-tests validés.
- Suite frontend complète : 229 tests, 0 échec.
- Lint frontend : 34 warnings connus, 0 erreur.
- Build Vite de production et publication `/static/app/` validés.
- Les 12 fichiers statiques publics ont été vérifiés par SHA-256 via HTTPS.
- Recette navigateur validée sur de vrais conteneurs Active Directory.
- Simulation validée pour création, modification, renommage, déplacement et suppression sans écriture Active Directory.
- Fixtures temporaires supprimées avec zéro objet C5.4 résiduel.
- Contrôles de sécurité pré-commit validés.

## [0.5.0-alpha.03] — 2026-08-08

### Ajoute
- Cycle de vie complet des contacts Active Directory.
- Action backend `create_contact` et execution Windows native avec `New-ADObject -Type contact`.
- Formulaire React de creation de contact et actions Explorateur associees.
- Tests backend, worker Simulation et frontend dedies aux contacts.
- Test de regression du chemin statique `/static/app/`.

### Securise
- Validation du parent, du perimetre EITAS et des doublons avant la frontiere Simulation.
- Validation des collisions de renommage/deplacement des contacts.
- Lecture de la protection contre suppression accidentelle avant Simulation.
- Runtime Simulation valide sans ecriture Active Directory.

### Interface
- Ajout de `Creer un contact` dans la barre d actions et le menu contextuel.
- Historique AD enrichi pour la creation de contacts.
- Modale contacts compactee : checkbox native 18 px, grille resserree, description reduite et footer sticky.

### Validation
- 206 tests frontend reussis.
- 434 tests backend et 337 sous-tests reussis.
- Lint frontend : 0 erreur.
- Build Vite et publication runtime valides.
- Controle SHA-256 des assets publics valide.
- Controles de securite pre-commit valides.

## [0.5.0-alpha.02] — 2026-08-08

### C5.2 — OU : consolidation et validation formelle

- deuxième checkpoint fonctionnel du chantier C5 ;
- création d’OU prévalidée sur le parent Active Directory réel avant Simulation ;
- parent de création limité à une OU ou un conteneur AD dans le périmètre autorisé ;
- doublon d’OU détecté avant toute réponse Simulation ;
- suppression d’OU prévalidée sur la vacuité et l’état de protection ;
- désactivation de la protection et suppression réelle maintenues exclusivement en Production ;
- renommage d’OU prévalidé contre les collisions avec une OU sœur ;
- déplacement prévalidé contre les collisions de nom dans la destination ;
- propriétés OU `managedBy` et protection contre la suppression accidentelle couvertes ;
- huit scénarios runtime Windows validés avec quatre succès Simulation et quatre refus attendus ;
- Active Directory confirmé inchangé après les validations Simulation ;
- fixtures temporaires supprimées, aucun objet C5.2 résiduel ;
- module Windows PowerShell 5.1 validé et déployé avec SHA-256 `3673C85799DFB5ED8ADF90AA2E253D0CEF1FA67236C164A4B1D0ECB0C7C74196` ;
- worker `EITAS AD Admin Worker` confirmé actif ;
- 13 tests backend dédiés C5.2 validés ;
- 5 tests frontend dédiés OU validés ;
- suite frontend complète : 198 tests, 0 échec ;
- lint frontend : 34 warnings connus, 0 erreur ;
- build Vite de production validé ;
- suite backend complète : 420 tests, 32 warnings connus et 326 sous-tests validés ;
- contrôles de sécurité sans secret validés ;
- C5.2 clôturé à 100 %, C5 global à 40 %.


## [0.5.0-alpha.01] — 2026-08-08

### C5.1 — Ordinateurs : consolidation et validation formelle

- premier checkpoint fonctionnel du chantier C5 ;
- création ordinateur prévalidée sur l’état Active Directory réel avant Simulation ;
- OU cible inexistante refusée et doublon ordinateur détecté au niveau du domaine ;
- renommage ordinateur normalisé et prévalidé avant Simulation, y compris conflits `sAMAccountName` ;
- règles de nom ordinateur harmonisées entre création et renommage ;
- mise à jour des propriétés ordinateur entièrement prévalidée avant la frontière Simulation ;
- propriétés système, `sAMAccountName`, `managedBy` et protection contre la suppression accidentelle couvertes ;
- aucune commande d’écriture Active Directory exécutée avant le retour Simulation ;
- resolver AD fiabilisé avec `Get-EitasAdDomainDn`, supprimant le défaut `SearchBase` nul sur objet inexistant ;
- validation runtime de création, renommage et mise à jour sans modification Active Directory ;
- fixture temporaire supprimé après les contrôles ;
- module Windows validé sous PowerShell 5.1 et déployé avec SHA-256 `2BDF63F9F8FEFB841D22E2E83936E7CAC1CBC949E0C2E4E0FECBCE0580578BE5` ;
- worker `EITAS AD Admin Worker` redémarré et confirmé actif ;
- 21 tests dédiés C5.1 validés ;
- suite backend complète : 407 tests, 32 warnings connus et 326 sous-tests validés ;
- C5.1 clôturé à 100 %, C5 global à 20 %.


## [0.4.0] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- version stable du chantier C4 ;
- C4.1 à C4.6 terminés et validés à 100 % ;
- gestion des membres et de l’imbrication sécurisée, avec blocage de l’auto-imbrication et des cycles transitifs ;
- compatibilité des portées Global / Universal / DomainLocal prévalidée avant toute écriture ;
- retrait de membre idempotent et validé sur l’état Active Directory réel ;
- groupe principal exposé et action `set_primary_group` maintenue strictement en Simulation ;
- conversions contrôlées de `GroupScope` et `GroupCategory` validées ;
- création, suppression, renommage et déplacement de groupes prévalidés sur l’état réel avant Simulation ;
- `managedBy` résolu comme utilisateur actif du domaine autorisé, avec clear contrôlé ;
- validations runtime Windows PowerShell 5.1 confirmées sans écriture Active Directory pour les chemins Simulation ;
- module Windows actif inchangé depuis `v0.4.0-alpha.07`, SHA-256 `B6B7E9C11228F3789D92B271F5039715A3D04D000B9F0F530DC7F1BA8511D7E4` ;
- ajout du test frontend de clôture `frontend/tests/adGroupAdvancedManagementUi.test.mjs` ;
- suite frontend complète validée depuis la racine du dépôt avec `TEST_FAILED=0` ;
- lint frontend : 34 warnings connus, 0 erreur ;
- build Vite de production validé ;
- suite backend complète finale : 386 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` final propre ;
- C4 clôturé à 100 %.


## [0.4.0-alpha.07] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- septième checkpoint fonctionnel du chantier C4 ;
- C4.6 « Propriétés avancées et gestionnaire des groupes » clôturé ;
- `update_object_properties` résout l’objet Active Directory réel avant le retour Simulation ;
- `managedBy` est prévalidé avec `Get-ADUser` avant le retour Simulation lorsqu’il est renseigné ;
- gestionnaire limité au domaine Active Directory autorisé et vérifié actif ;
- gestionnaire `Administrateur`, situé hors `OU=EITAS` mais dans `API.LOCAL`, accepté en Simulation ;
- DN de gestionnaire inexistant refusé avant le retour Simulation ;
- utilisateur désactivé refusé comme gestionnaire ;
- suppression de `managedBy` par valeur vide validée en Simulation ;
- Active Directory confirmé inchangé après chaque validation Simulation ;
- module final validé sous Windows PowerShell 5.1 puis déployé avec sauvegarde ;
- sauvegarde précédente conservée dans `C:\EnterpriseIT\backups\c4.6b4c-20260807-223953` ;
- SHA-256 actif final `B6B7E9C11228F3789D92B271F5039715A3D04D000B9F0F530DC7F1BA8511D7E4` ;
- worker `EITAS AD Admin Worker` redémarré et confirmé actif ;
- 4 tests dédiés au contrat C4.6 validés ;
- régression groupes C4.2 à C4.6 : 60 tests, 17 warnings connus et 16 sous-tests validés ;
- suite backend complète : 386 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` propre.


## [0.4.0-alpha.06] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- sixième checkpoint fonctionnel du chantier C4 ;
- C4.5 « Cycle de vie structurel des groupes » clôturé ;
- `create_group` contrôle l’existence réelle du groupe avant le retour Simulation ;
- `delete_object` résout l’objet réel et vérifie le `confirm_dn` avant le retour Simulation ;
- `rename_object` résout l’objet réel avant le retour Simulation ;
- `move_object` résout la source et la destination réelles avant le retour Simulation ;
- destination de déplacement limitée aux classes Active Directory `organizationalUnit` et `container` ;
- faux positif de Simulation sur une destination groupe détecté puis corrigé et revalidé au runtime ;
- destination OU réelle acceptée en Simulation sans déplacement Active Directory ;
- mauvais `confirm_dn` de suppression refusé avant le retour Simulation ;
- renommage simulé validé sans création ni renommage réel de l’objet ;
- création simulée validée pour un groupe inexistant, sans création Active Directory ;
- module final validé sous Windows PowerShell 5.1 puis déployé avec sauvegarde ;
- SHA-256 actif final `A914BD58FA8519C903CB9E397C2F56B841D6FE7E5FE9D2E73CC5683829AA0C8D` ;
- worker `EITAS AD Admin Worker` redémarré afin de recharger le module final ;
- 6 tests dédiés au contrat de cycle de vie C4.5 validés ;
- suite backend complète : 382 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` propre.

## [0.4.0-alpha.05] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- cinquième checkpoint fonctionnel du chantier C4 ;
- C4.4 « Conversion contrôlée de la portée et de la catégorie des groupes » clôturé ;
- prévalidation de `GroupScope` et `GroupCategory` sur l’état Active Directory réel avant le retour Simulation ;
- conversion directe `Global ↔ DomainLocal` refusée avec passage intermédiaire par `Universal` ;
- transitions `Global → Universal`, `DomainLocal → Universal`, `Universal → Global` et `Universal → DomainLocal` validées au runtime ;
- changement `Security → Distribution` validé en Simulation avec avertissement explicite sur l’impact des ACE ;
- helper de prévalidation confirmé strictement read-only, sans commande d’écriture Active Directory ;
- module Windows validé sous PowerShell 5.1 puis déployé avec sauvegarde et contrôle SHA-256 ;
- SHA-256 actif `93049F5F5DB033707B2FA61D1EE6C1E6832308C0FAC9CE96A3DF0BEBFEDD320A` ;
- groupe Universal temporaire `GG_C44_UNIVERSAL_TEST` supprimé après validation et absence confirmée dans Active Directory ;
- 35 tests dédiés C4.2/C4.3/C4.4 validés, avec 16 sous-tests ;
- suite backend complète : 376 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` propre et contrôle de sécurité pré-commit validé sur les fichiers fonctionnels.

## [0.4.0-alpha.04] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- quatrième checkpoint fonctionnel du chantier C4 ;
- C4.3 « Membre de / groupe principal » validé de bout en bout ;
- groupe principal exposé dans l’onglet `Membre de` sans duplication de l’appartenance directe ;
- groupes directs éligibles proposés comme nouveau groupe principal depuis le portail ;
- groupe principal actuel protégé contre le retrait depuis l’interface ;
- action `set_primary_group` intégrée à l’API AD Admin et au dispatcher Windows ;
- seuls les utilisateurs et ordinateurs sont acceptés comme objets cibles ;
- groupe cible obligatoire de catégorie Security, dans le même domaine SID et sous le périmètre EITAS ;
- changement de groupe principal conditionné par une appartenance directe réelle au groupe cible ;
- RID cible dérivé du SID Active Directory et comparé au `primaryGroupID` actuel ;
- chemin idempotent pris en charge lorsque le groupe cible est déjà le groupe principal ;
- Production strictement refusée pour cette action ;
- résultat Simulation explicite avec `simulated=true` et `production_authorized=false` ;
- garde-fou hors périmètre EITAS validé au runtime ;
- Simulation runtime validée vers `GG_IT_Admin` RID 1118 ;
- validation réelle depuis l’interface vers `GG_Server_Admin` RID 1119 ;
- worker `SRV-DC01` confirmé sur les jobs C4.3 ;
- Active Directory confirmé inchangé après les validations Simulation ;
- audit `created → claimed → completed/failed` validé ;
- 365 tests backend et 317 sous-tests validés ;
- tests frontend C4.2/C4.3, lint et build de production validés ;
- aucun secret détecté dans le diff du checkpoint.


## [0.4.0-alpha.03] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- troisième checkpoint fonctionnel du chantier C4 ;
- sécurisation du chemin `remove_group_member` ;
- résolution réelle du groupe et du membre avant le retour Simulation ;
- vérification de l’appartenance directe réelle avant toute réponse Simulation ;
- retour Simulation enrichi avec `was_member=true/false` selon l’état réel d’Active Directory ;
- retrait d’un membre déjà absent conservé comme opération idempotente ;
- `Remove-ADGroupMember` reste strictement réservé au chemin Production ;
- retrait groupe vers groupe pris en charge ;
- validation runtime directe des cas membre présent et membre absent ;
- validation E2E des deux cas via le worker SRV-DC01 ;
- Active Directory confirmé inchangé après les validations ;
- worker Windows déployé avec le SHA-256 `1DEA242C976515059024FF59BC86D97DEF45ED8A6B0CD59E57BD8E0C77DEBD49` ;
- PowerShell 5.1 validé sans erreur de parsing ;
- 25 tests ciblés C4.2 validés ;
- suite backend complète : 334 tests et 301 sous-tests validés.

## [0.4.0-alpha.02] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- second checkpoint fonctionnel du chantier C4 ;
- ajout d’une matrice de compatibilité des portées pour l’imbrication de groupes ;
- groupe cible Global : seuls les groupes Global compatibles sont acceptés ;
- groupe cible Universal : groupes Global et Universal pris en charge ;
- groupe cible DomainLocal : groupes Global, Universal et DomainLocal pris en charge dans le périmètre autorisé ;
- résolution réelle de `GroupScope` avant le retour Simulation ;
- combinaison incompatible `Global <- DomainLocal` refusée avant toute écriture Active Directory ;
- validation runtime sur SRV-DC01 des combinaisons disponibles dans le lab ;
- validation E2E Simulation de `Global <- Global` avec résultat `completed` ;
- validation E2E Simulation de `Global <- DomainLocal` avec résultat `failed` et motif de compatibilité attendu ;
- Active Directory confirmé inchangé après les deux scénarios E2E ;
- PowerShell 5.1 validé sans erreur de parsing sur SRV-DC01 ;
- 17 tests ciblés C4.2A/C4.2B validés ;
- suite backend complète : 326 tests et 301 sous-tests validés ;
- aucun groupe Universal n’étant actuellement présent dans le lab, ces branches restent couvertes par les tests automatisés.

## [0.4.0-alpha.01] — 2026-08-07

### C4 — Groupes, imbrication et appartenances

- premier checkpoint fonctionnel du chantier C4 ;
- ajout groupe vers groupe prévalidé sur les objets Active Directory réels ;
- auto-imbrication d’un groupe explicitement refusée ;
- détection transitive des cycles par parcours des groupes membres directs ;
- protection contre les boucles de parcours avec suivi des groupes visités ;
- mode Simulation conservé sans écriture Active Directory ;
- résolution réelle du groupe cible et du membre avant validation Simulation ;
- comportement idempotent conservé lorsqu’un membre direct existe déjà ;
- validation PowerShell 5.1 effectuée sur SRV-DC01 ;
- module AD Admin Windows déployé avec sauvegarde et contrôle SHA-256 ;
- job `add_group_member` validé de bout en bout en Simulation ;
- absence d’écriture vérifiée directement dans Active Directory après le job ;
- 7 tests ciblés C4 validés ;
- 316 tests backend complets validés.

## [0.3.1] — 2026-08-06

### Documentation

- badge de version du README corrigé ;
- version officielle actuelle mise à jour ;
- badge C3 ajouté ;
- clôtures C1, C2 et C3 présentées ensemble ;
- tableau de versionnement du README corrigé ;
- état courant et version actuelle de la roadmap corrigés ;
- aucune modification fonctionnelle de l’application.

## [0.3.0] — 2026-08-06

### C3 — Gestion avancée des utilisateurs

- chantier C3 validé fonctionnellement à 100 % ;
- actions de compte utilisateur et états Active Directory centralisés ;
- contrôles de sécurité liés au mode de l’agent renforcés ;
- réinitialisation sécurisée des mots de passe avec choix explicites ;
- options de compte et de sécurité avancées intégrées ;
- copie d’utilisateur contrôlée par liste blanche ;
- identité, profil, organisation, coordonnées et adresse enrichis ;
- restrictions de stations et horaires de connexion disponibles ;
- profils RDS complets intégrés ;
- profil Unix / POSIX intégré avec types Active Directory préservés ;
- attribut HAB consultable et simulable par son pipeline dédié ;
- ouverture immédiate des propriétés utilisateur ;
- chargement détaillé asynchrone sans fenêtre bloquante ;
- cache utilisateur dédié et invalidation après modification ;
- lookup live utilisateur complété avec toutes les propriétés attendues ;
- `directReports` conservé en lecture seule ;
- valeurs `logonHours` sérialisées sans perte ;
- valeurs multivaluées de `postOfficeBox` détectées et comptées ;
- lecture fidèle du triplet pays `c`, `co` et `countryCode` ;
- validations réelles en Simulation et en Production ;
- baseline Active Directory restaurée après les validations ;
- module Windows Lookup déployé et worker confirmé actif ;
- 309 tests backend complets validés ;
- 190 tests frontend complets validés ;
- contrôles de sécurité, lint et builds de production validés ;
- mode final de l’agent confirmé en Simulation ;
- version stable `v0.3.0` préparée.

## [0.2.0] — 2026-08-05

### C2 — Éditeur d’attributs LDAP

- chantier C2 validé fonctionnellement à 100 % ;
- pipeline LDAP HAB typé validé ;
- jobs HAB runtime dédiés disponibles uniquement en Simulation ;
- routes dédiées protégées par OIDC et RBAC ;
- accès de simulation réservé à `ADAdmin` et `UltraAdmin` ;
- type `integer32` préservé du portail au worker Windows ;
- opérations `set` et `clear` contrôlées ;
- bornes EITAS de `0` à `2147483647` appliquées ;
- validation de l’aperçu obligatoire avant la création du job ;
- confirmation explicite obligatoire avant la simulation ;
- aperçu Active Directory calculé sans écriture ;
- lookup utilisateur détaillé `get_user` étendu en lecture seule ;
- valeur HAB sérialisée sous forme d’un `integer32` nullable ;
- valeur absente présentée sous la forme `Non défini` ;
- contrôle frontend HAB dédié dans les propriétés utilisateur ;
- suivi du job et affichage persistant du résultat final ;
- défilement automatique vers le résultat de simulation ;
- ouverture des propriétés rendue immédiate ;
- enrichissement utilisateur asynchrone sans fermeture de la modale HAB ;
- identité fonctionnelle stabilisée par distinguished name ;
- catalogue du domaine et snapshot générique toujours sans exposition HAB ;
- aucune commande `Set-AD*` ajoutée aux chemins HAB ;
- aucune autorisation frontend ou backend d’écriture HAB réelle ;
- exécution HAB en Production toujours désactivée ;
- valeurs brutes HAB exclues des métadonnées d’audit ;
- état Active Directory confirmé inchangé après simulation ;
- 202 tests backend complets validés ;
- 53 tests frontend complets validés ;
- lint, build de production et contrôle de sécurité validés ;
- version `v0.2.0` finalisée.

### EITAS Identity

- accès Compte et Administration EITAS Identity restaurés dans le portail ;
- accès d’administration Identity limité à `SecurityAdmin` et `UltraAdmin`.

## [0.1.0] — 2026-07-28

### Version initiale officielle

Cette version marque la clôture à 100 % de C1 — Fenêtres de propriétés complètes de l'Explorateur Active Directory.

### Ajouté

- portail React ;
- API FastAPI ;
- agents PowerShell Windows Server ;
- workflows d'onboarding, modification, offboarding et réactivation ;
- authentification OIDC/PKCE et Bearer JWT ;
- authentification des workers par clé API ;
- contrôle d'accès RBAC ;
- Explorateur Active Directory ;
- snapshot EITAS et catalogue global du domaine ;
- opérations contrôlées sur les objets Active Directory ;
- propriétés complètes et métadonnées de l'onglet Objet.

### C1 validé

- 46 propriétés éditables sur 46 ;
- six types d'objets ;
- huit métadonnées de l'onglet Objet ;
- snapshot complet sur 43 objets sur 43 ;
- catalogue complet sur 85 objets sur 85 ;
- validation visuelle sur un utilisateur, un ordinateur et un groupe ;
- aucun mojibake réel restant dans l'interface.

### Documentation

- dossier de clôture C1 ;
- README professionnel ;
- politique de versionnement ;
- roadmap ;
- processus de suivi GitHub ;
- modèles d'issues et de pull requests.

## Historique antérieur

Le tag `v0.4-mvp-secured` correspond à un ancien jalon MVP créé avant le schéma de versionnement officiel actuel.
