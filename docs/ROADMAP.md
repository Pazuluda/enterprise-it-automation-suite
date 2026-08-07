# Feuille de route EITAS

## État à la sortie de v0.1.0

| Indicateur | Avancement |
|---|---:|
| C1 — Fenêtres Propriétés complètes | 100 % |
| Explorateur Active Directory complet | 25 % |
| Projet EITAS global | 81 % |

Les pourcentages sont recalculés uniquement après une validation formelle.

## État courant — v0.4.0

| Indicateur | Avancement |
|---|---:|
| C4 — Groupes, imbrication et appartenances |      100 % |
| Explorateur Active Directory complet       |       58 % |
| Projet EITAS global | 82 % |

La version `v0.4.0` clôt le chantier C4 « Groupes, imbrication et appartenances » à 100 % après validation fonctionnelle, runtime, frontend et backend de l’ensemble du périmètre C4.

C3 est validé fonctionnellement à 100 %. La gestion avancée des utilisateurs couvre les actions de compte, les options de sécurité, la copie contrôlée, les profils avancés, RDS, Unix / POSIX, HAB et le lookup live complet. L’ouverture des propriétés est immédiate et le chargement détaillé reste non bloquant.

## Roadmap de l'Explorateur Active Directory

| Chantier | Objectif | Version cible | État |
|---|---|---:|---|
| C1 | Fenêtres Propriétés complètes | `v0.1.0` | Terminé |
| C2 | Éditeur d'attributs LDAP | `v0.2.0` | Terminé — 100 % |
| C3 | Gestion avancée des utilisateurs | `v0.3.0` | Terminé — 100 % |
| C4 | Groupes, imbrication et appartenances | `v0.4.0` | Terminé — 100 % |
| C5 | Ordinateurs, OU, conteneurs et contacts | `v0.5.0` | Planifié |
| C6 | Recherche, colonnes, filtres et requêtes | `v0.6.0` | Planifié |
| C7 | Sélection multiple, copie et glisser-déposer | `v0.7.0` | Planifié |
| C8 | ACL, sécurité et délégation | `v0.8.0` | Planifié |
| C9 | Corbeille Active Directory et restauration | `v0.9.0` | Planifié |
| C10 | Performance, audit, tests et finition | `v0.10.0` | Planifié |

## Version actuelle

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
