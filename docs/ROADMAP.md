# Feuille de route EITAS

## État à la sortie de v0.1.0

| Indicateur | Avancement |
|---|---:|
| C1 — Fenêtres Propriétés complètes | 100 % |
| Explorateur Active Directory complet | 25 % |
| Projet EITAS global | 81 % |

Les pourcentages sont recalculés uniquement après une validation formelle.

## État courant — v0.5.0-alpha.04

| Indicateur | Avancement |
|---|---:|
| C4 — Groupes, imbrication et appartenances |      100 % |
| C5 — Ordinateurs, OU, conteneurs et contacts |       80 % |
| Explorateur Active Directory complet       |       70 % |
| Projet EITAS global | 84 % |

La version `v0.5.0-alpha.04` clôt C5.4 « Conteneurs Active Directory natifs » à 100 %. C5.1 à C5.4 sont désormais terminés ; `v0.4.0` reste la version stable de clôture du chantier C4 à 100 %.

C3 est validé fonctionnellement à 100 %. La gestion avancée des utilisateurs couvre les actions de compte, les options de sécurité, la copie contrôlée, les profils avancés, RDS, Unix / POSIX, HAB et le lookup live complet. L’ouverture des propriétés est immédiate et le chargement détaillé reste non bloquant.

## Roadmap de l'Explorateur Active Directory

| Chantier | Objectif | Version cible | État |
|---|---|---:|---|
| C1 | Fenêtres Propriétés complètes | `v0.1.0` | Terminé |
| C2 | Éditeur d'attributs LDAP | `v0.2.0` | Terminé — 100 % |
| C3 | Gestion avancée des utilisateurs | `v0.3.0` | Terminé — 100 % |
| C4 | Groupes, imbrication et appartenances | `v0.4.0` | Terminé — 100 % |
| C5 | Ordinateurs, OU, conteneurs et contacts | `v0.5.0` | En cours — 80 % |
| C6 | Recherche, colonnes, filtres et requêtes | `v0.6.0` | Planifié |
| C7 | Sélection multiple, copie et glisser-déposer | `v0.7.0` | Planifié |
| C8 | ACL, sécurité et délégation | `v0.8.0` | Planifié |
| C9 | Corbeille Active Directory et restauration | `v0.9.0` | Planifié |
| C10 | Performance, audit, tests et finition | `v0.10.0` | Planifié |

## Version actuelle

### v0.5.0-alpha.04 — C5.4 Conteneurs Active Directory natifs
- Objet `container` pris en charge de bout en bout comme classe Active Directory native.
- Création Windows via `New-ADObject -Type container` avec parent OU ou conteneur.
- Snapshot, lookup live, arborescence et breadcrumbs enrichis pour les conteneurs.
- Création, modification, renommage, déplacement et suppression validés en Simulation.
- Protection contre la suppression accidentelle exposée et prévalidée.
- Collisions, doublons et vacuité vérifiés avant toute frontière d’écriture.
- Recette navigateur validée sur une fixture native composée de trois conteneurs.
- Preuve zero-write finale validée puis cleanup complet avec zéro objet résiduel.
- Historique des propriétés désormais filtré par DN d’objet avec fenêtre AD Admin à 1000 jobs.
- Toasts de succès validés pour modification et renommage.
- Suite backend complète : 452 tests, 36 warnings connus et 339 sous-tests validés.
- Suite frontend complète : 229 tests, 0 échec ; lint : 34 warnings connus, 0 erreur.
- Build de production, déploiement `/static/app/` et hashes publics SHA-256 validés.
- C5.4 terminé à 100 %.
- **Progression après C5.4 : C5 80 %, Explorateur AD 70 %, EITAS 84 %.**
### v0.5.0-alpha.03 — C5.3 Contacts

- Cycle de vie des contacts Active Directory valide de bout en bout.
- Nouvelle action `create_contact` dans le backend AD Admin.
- Creation native Windows via `New-ADObject -Type contact`.
- Prevalidation Simulation du parent, du perimetre EITAS et des doublons.
- Collisions de renommage et deplacement validees avant toute ecriture.
- Suppression des contacts proteges validee avec lecture de `ProtectedFromAccidentalDeletion` avant la frontiere Simulation.
- Formulaire React complet : identite, communication, organisation, description et protection contre la suppression accidentelle.
- Action disponible dans la barre Explorateur et le menu contextuel.
- Historique traduit avec `Creer un contact`.
- Runtime Windows valide en Simulation avec preuve d absence d ecriture AD.
- Recette navigateur validee avec `C53-UI-SIM-0808`.
- Polish cible de la modale contacts et footer sticky valide.
- Publication frontend validee sous `/static/app/` avec controle SHA-256 des fichiers servis.
- Regression de chemin statique couverte par un test frontend dedie.
- Validation finale : 206 tests frontend, 434 tests backend, 337 sous-tests backend, lint sans erreur et controles de securite verts.

**Progression apres C5.3 : C5 60 %, Explorateur AD 66 %, EITAS 83 %.**

### v0.5.0-alpha.02 — Checkpoint C5.2

Ce checkpoint clôt C5.2 « OU : consolidation et validation formelle ».

- création d’OU prévalidée sur le parent Active Directory réel avant Simulation ;
- parent limité aux classes `organizationalUnit` et `container` dans le périmètre EITAS ;
- doublon d’OU détecté avant le retour Simulation ;
- suppression d’OU prévalidée sur la vacuité et l’état de protection avant Simulation ;
- désactivation réelle de la protection et suppression conservées strictement en Production ;
- collision d’OU sœur détectée avant renommage simulé ;
- collision de nom dans la destination détectée avant déplacement simulé ;
- `managedBy` et `protectedFromAccidentalDeletion` couverts pour les propriétés OU ;
- huit scénarios runtime validés, avec quatre succès Simulation et quatre refus attendus ;
- Active Directory confirmé inchangé après les scénarios Simulation ;
- fixtures C5.2 supprimées avec `FIXTURE_REMAINING=0` ;
- module Windows actif SHA-256 `3673C85799DFB5ED8ADF90AA2E253D0CEF1FA67236C164A4B1D0ECB0C7C74196` ;
- 13 tests backend dédiés C5.2 validés ;
- 5 tests frontend dédiés OU validés ;
- suite frontend complète : 198 tests validés ;
- lint frontend : 34 warnings connus, 0 erreur ;
- build Vite de production validé ;
- suite backend complète : 420 tests, 32 warnings connus et 326 sous-tests validés ;
- C5.2 terminé à 100 % ;
- C5 global : 40 % ; Explorateur AD : 62 % ; EITAS : 82 %.

### v0.5.0-alpha.01 — Checkpoint C5.1

Ce checkpoint clôt C5.1 « Ordinateurs : consolidation et validation formelle ».

- création ordinateur consolidée avec validation réelle de l’OU cible avant le retour Simulation ;
- détection des comptes ordinateur déjà existants dans le domaine avant Simulation ;
- règles de nom ordinateur alignées : 1 à 15 caractères, A-Z, chiffres et tirets, sans tiret initial/final et sans valeur uniquement numérique ;
- renommage ordinateur prévalidé avant Simulation avec synchronisation prévue du `sAMAccountName` et détection des conflits ;
- mise à jour ordinateur prévalidée avant Simulation pour `sAMAccountName`, propriétés système, `managedBy` et protection contre la suppression accidentelle ;
- toutes les écritures Active Directory restent après la frontière Simulation ;
- resolver AD corrigé pour utiliser `Get-EitasAdDomainDn` et retourner proprement « Objet AD introuvable » au lieu d’un `SearchBase` nul ;
- validations runtime Windows PowerShell 5.1 confirmées sans écriture Active Directory ;
- fixture ordinateur temporaire supprimé après validation ;
- module Windows actif SHA-256 `2BDF63F9F8FEFB841D22E2E83936E7CAC1CBC949E0C2E4E0FECBCE0580578BE5` ;
- 21 tests dédiés C5.1 validés ;
- suite backend complète : 407 tests, 32 warnings connus et 326 sous-tests validés ;
- `git diff --check` validé ;
- C5.1 terminé à 100 % ;
- C5 global : 20 % ; Explorateur AD : 58 % ; EITAS : 82 %.

### v0.4.0-alpha.07 — Checkpoint C4.6

Ce checkpoint clôt C4.6 « Propriétés avancées et gestionnaire des groupes ». La Simulation d’une modification de propriétés résout désormais l’objet Active Directory réel avant son retour, et `managedBy` est prévalidé comme utilisateur actif du domaine autorisé sans imposer à tort le sous-périmètre `OU=EITAS`.

- objet cible résolu dans Active Directory avant le retour Simulation ;
- `managedBy` résolu avec `Get-ADUser` avant le retour Simulation lorsqu’une valeur non vide est fournie ;
- gestionnaire limité au domaine Active Directory autorisé et vérifié actif ;
- gestionnaire actif situé hors `OU=EITAS` mais dans `API.LOCAL` accepté au runtime ;
- DN de gestionnaire inexistant refusé avant le retour Simulation ;
- utilisateur désactivé refusé comme gestionnaire ;
- suppression de `managedBy` par valeur vide conservée et validée en Simulation ;
- aucune commande d’écriture Active Directory déplacée avant le retour Simulation ;
- module Windows validé sous PowerShell 5.1 avec zéro erreur de parsing ;
- SHA-256 actif `B6B7E9C11228F3789D92B271F5039715A3D04D000B9F0F530DC7F1BA8511D7E4` ;
- worker `EITAS AD Admin Worker` redémarré et confirmé actif ;
- 4 tests dédiés C4.6 validés ;
- régression groupes C4.2 à C4.6 : 60 tests, 17 warnings connus et 16 sous-tests validés ;
- suite backend complète : 386 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` propre.

### v0.4.0-alpha.06 — Checkpoint C4.5

Ce checkpoint clôt C4.5 « Cycle de vie structurel des groupes ». Les opérations de création, suppression, renommage et déplacement sont prévalidées sur l’état Active Directory réel avant le retour Simulation, sans écriture AD.

## Versions de chantier terminées

### v0.2.0 — C2

Objectif : fournir un éditeur d'attributs LDAP contrôlé, auditable et sécurisé.

Le chantier C2 est terminé et validé à 100 %. La consultation HAB et sa simulation dédiée sont disponibles sans autoriser d’écriture Active Directory. Toute activation HAB en Production reste fermée par conception.

### v0.3.0 — C3

Le chantier C3 est terminé et validé à 100 %. La gestion avancée des utilisateurs est disponible avec des contrôles de sécurité, des validations réelles et un lookup live complet.

### v0.4.0 — C4

Objectif : développer la gestion avancée des groupes, de l’imbrication et des appartenances.

**Version stable :** **`v0.4.0`**

- C4.1 : audit fonctionnel et technique terminé ;
- C4.2A : ajout groupe vers groupe sécurisé et validé ;
- auto-imbrication et cycles transitifs bloqués ;
- Simulation validée de bout en bout sans modification AD ;
- C4.2B : compatibilité des portées d’imbrication validée ;
- matrice Global / Universal / DomainLocal prévalidée avant toute écriture ;
- validation E2E Simulation des chemins autorisé et refusé ;
- Active Directory confirmé inchangé après validation ;
- C4.2C : retrait de membre prévalidé sur l’état AD réel et validé ;
- Simulation du retrait enrichie avec `was_member` sans écriture Active Directory ;
- retrait d’un membre déjà absent validé comme opération idempotente ;
- validation runtime et E2E des cas présent et absent terminée ;
- C4.2 : gestion des membres et de l’imbrication clôturée ;
- C4.3 : onglet `Membre de` enrichi avec le groupe principal ;
- action `set_primary_group` disponible uniquement en Simulation ;
- prévalidation du groupe cible : Security, même domaine SID et appartenance directe ;
- garde-fou hors périmètre EITAS validé ;
- validation runtime et E2E depuis le portail vers `GG_IT_Admin` et `GG_Server_Admin` ;
- Active Directory confirmé inchangé après les Simulations ;
- 365 tests backend et 317 sous-tests validés ;
- C4.3 est validé fonctionnellement.
- C4.4 : conversion contrôlée de `GroupScope` et `GroupCategory` ;
- état réel du groupe lu avant le retour Simulation ;
- conversion directe `Global ↔ DomainLocal` refusée avec passage intermédiaire par `Universal` ;
- transitions `Global → Universal`, `DomainLocal → Universal`, `Universal → Global` et `Universal → DomainLocal` validées au runtime ;
- changement `Security → Distribution` accompagné d’un avertissement explicite sur l’impact sécurité ;
- helper de prévalidation confirmé strictement read-only ;
- groupe Universal temporaire de validation supprimé après les tests ;
- suite backend complète : 376 tests et 317 sous-tests validés ;
- C4.4 est validé fonctionnellement.
- C4.5 : cycle de vie structurel des groupes validé ;
- `create_group` prévalide l’existence réelle du groupe avant le retour Simulation ;
- `delete_object` résout l’objet réel et vérifie le `confirm_dn` avant le retour Simulation ;
- `rename_object` résout l’objet réel avant le retour Simulation ;
- `move_object` résout la source et la destination réelles avant le retour Simulation ;
- les destinations de déplacement sont limitées aux `organizationalUnit` et `container` ;
- validation runtime Windows PowerShell 5.1 avec le module final ;
- worker `EITAS AD Admin Worker` redémarré pour recharger le module final ;
- validations Simulation confirmées sans écriture Active Directory ;
- suite backend complète : 382 tests, 31 warnings connus et 317 sous-tests validés ;
- C4.5 est validé fonctionnellement.
- C4.6 : propriétés avancées et gestionnaire des groupes validés ;
  - résolution de l’objet cible avant tout retour Simulation ;
  - résolution réelle de `managedBy` comme utilisateur Active Directory ;
  - validation du domaine autorisé sans restriction indue à `OU=EITAS` ;
  - refus des gestionnaires inexistants ou désactivés ;
  - clear `managedBy` validé ;
  - Simulation confirmée sans écriture Active Directory ;
- C4.6 est validé fonctionnellement.
- test frontend de clôture `adGroupAdvancedManagementUi.test.mjs` validé ;
- suite frontend complète validée depuis la racine du dépôt avec `TEST_FAILED=0` ;
- lint frontend validé avec 34 warnings connus et 0 erreur ;
- build Vite de production validé ;
- suite backend complète finale : 386 tests, 31 warnings connus et 317 sous-tests validés ;
- `git diff --check` final propre ;
- C4 est terminé et validé à 100 %.

## Version v1.0.0

Elle nécessitera notamment une documentation d'exploitation complète, une stratégie de migration et de sauvegarde, des tests de non-régression, une revue de sécurité et une stabilisation globale.
