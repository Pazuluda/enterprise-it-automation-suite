# Feuille de route EITAS

## État à la sortie de v0.1.0

| Indicateur | Avancement |
|---|---:|
| C1 — Fenêtres Propriétés complètes | 100 % |
| Explorateur Active Directory complet | 25 % |
| Projet EITAS global | 82 % |

Les pourcentages sont recalculés uniquement après une validation formelle.

## État courant — v0.2.0-alpha.17

| Indicateur | Avancement |
|---|---:|
| C2 — Éditeur d’attributs LDAP | 100 % |
| Explorateur Active Directory complet | 67 % |
| Projet EITAS global | 87 % |

C2 est validé fonctionnellement à 100 %. Le pipeline LDAP HAB typé, les jobs runtime en Simulation, la consultation en lecture seule et le contrôle frontend dédié sont validés. Le catalogue générique reste sans exposition HAB. Toute écriture Active Directory et toute exécution HAB en Production restent fermées.

## Roadmap de l'Explorateur Active Directory

| Chantier | Objectif | Version cible | État |
|---|---|---:|---|
| C1 | Fenêtres Propriétés complètes | `v0.1.0` | Terminé |
| C2 | Éditeur d'attributs LDAP | `v0.2.0` | Terminé — 100 % |
| C3 | Gestion avancée des utilisateurs | `v0.3.0` | Planifié |
| C4 | Groupes, imbrication et appartenances | `v0.4.0` | Planifié |
| C5 | Ordinateurs, OU, conteneurs et contacts | `v0.5.0` | Planifié |
| C6 | Recherche, colonnes, filtres et requêtes | `v0.6.0` | Planifié |
| C7 | Sélection multiple, copie et glisser-déposer | `v0.7.0` | Planifié |
| C8 | ACL, sécurité et délégation | `v0.8.0` | Planifié |
| C9 | Corbeille Active Directory et restauration | `v0.9.0` | Planifié |
| C10 | Performance, audit, tests et finition | `v0.10.0` | Planifié |

## Prochaine version

### v0.2.0 — C2

Objectif : fournir un éditeur d'attributs LDAP contrôlé, auditable et sécurisé.

Le chantier fonctionnel est validé à 100 %. La préversion `v0.2.0-alpha.17` constitue la candidate de clôture avant la publication de `v0.2.0`. La consultation HAB et sa simulation dédiée sont disponibles sans autoriser d’écriture Active Directory. Toute activation HAB en Production reste fermée par conception.

## Version v1.0.0

Elle nécessitera notamment une documentation d'exploitation complète, une stratégie de migration et de sauvegarde, des tests de non-régression, une revue de sécurité et une stabilisation globale.
