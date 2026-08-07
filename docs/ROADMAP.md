# Feuille de route EITAS

## État à la sortie de v0.1.0

| Indicateur | Avancement |
|---|---:|
| C1 — Fenêtres Propriétés complètes | 100 % |
| Explorateur Active Directory complet | 25 % |
| Projet EITAS global | 82 % |

Les pourcentages sont recalculés uniquement après une validation formelle.

## État courant — v0.4.0-alpha.04

| Indicateur | Avancement |
|---|---:|
| C4 — Groupes, imbrication et appartenances | 73 % |
| Explorateur Active Directory complet | 52 % |
| Projet EITAS global | 80 % |

La version `v0.4.0-alpha.04` clôt C4.2 et valide C4.3 « Membre de / groupe principal » en Simulation de bout en bout, y compris depuis l’interface réelle.

C3 est validé fonctionnellement à 100 %. La gestion avancée des utilisateurs couvre les actions de compte, les options de sécurité, la copie contrôlée, les profils avancés, RDS, Unix / POSIX, HAB et le lookup live complet. L’ouverture des propriétés est immédiate et le chargement détaillé reste non bloquant.

## Roadmap de l'Explorateur Active Directory

| Chantier | Objectif | Version cible | État |
|---|---|---:|---|
| C1 | Fenêtres Propriétés complètes | `v0.1.0` | Terminé |
| C2 | Éditeur d'attributs LDAP | `v0.2.0` | Terminé — 100 % |
| C3 | Gestion avancée des utilisateurs | `v0.3.0` | Terminé — 100 % |
| C4 | Groupes, imbrication et appartenances | `v0.4.0` | En cours — C4.2 clôturé et C4.3 validé — 73 % |
| C5 | Ordinateurs, OU, conteneurs et contacts | `v0.5.0` | Planifié |
| C6 | Recherche, colonnes, filtres et requêtes | `v0.6.0` | Planifié |
| C7 | Sélection multiple, copie et glisser-déposer | `v0.7.0` | Planifié |
| C8 | ACL, sécurité et délégation | `v0.8.0` | Planifié |
| C9 | Corbeille Active Directory et restauration | `v0.9.0` | Planifié |
| C10 | Performance, audit, tests et finition | `v0.10.0` | Planifié |

## Version actuelle

### v0.4.0-alpha.04 — Checkpoint C4.3

Ce checkpoint valide C4.3 « Membre de / groupe principal » en Simulation. Le chemin UI → API → worker Windows → Active Directory a été validé sans écriture AD réelle.

## Versions de chantier terminées

### v0.2.0 — C2

Objectif : fournir un éditeur d'attributs LDAP contrôlé, auditable et sécurisé.

Le chantier C2 est terminé et validé à 100 %. La consultation HAB et sa simulation dédiée sont disponibles sans autoriser d’écriture Active Directory. Toute activation HAB en Production reste fermée par conception.

### v0.3.0 — C3

Le chantier C3 est terminé et validé à 100 %. La gestion avancée des utilisateurs est disponible avec des contrôles de sécurité, des validations réelles et un lookup live complet.

## Prochaine version

### v0.4.0 — C4

Objectif : développer la gestion avancée des groupes, de l’imbrication et des appartenances.

**Checkpoint actuel :** **`v0.4.0-alpha.04`**

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

## Version v1.0.0

Elle nécessitera notamment une documentation d'exploitation complète, une stratégie de migration et de sauvegarde, des tests de non-régression, une revue de sécurité et une stabilisation globale.
