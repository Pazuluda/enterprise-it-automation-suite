# Clôture C3 — Gestion avancée des utilisateurs

## Statut

- Chantier : C3
- Version : `v0.3.0`
- Date de clôture : 2026-08-06
- État fonctionnel : terminé à 100 %
- Mode final de l’agent : Simulation

## Périmètre livré

C3 complète la gestion avancée des utilisateurs dans l’Explorateur Active Directory.

Les fonctions validées comprennent :

- lecture détaillée et modification contrôlée du profil utilisateur ;
- état du compte et actions de compte ;
- réinitialisation sécurisée du mot de passe ;
- options de sécurité Active Directory ;
- copie contrôlée d’un utilisateur ;
- identité, organisation, coordonnées et adresse ;
- restrictions des stations de travail ;
- horaires de connexion ;
- profil RDS ;
- profil Unix / POSIX ;
- consultation et simulation HAB par un pipeline dédié ;
- lookup live utilisateur complet ;
- cache des détails utilisateur ;
- ouverture immédiate des propriétés et enrichissement en arrière-plan.

## Sécurité

Les validations de clôture confirment :

- contrôle du mode agent avant les opérations sensibles ;
- validation en Simulation avant les écritures Production testées ;
- restauration de la baseline Active Directory ;
- absence de valeur sensible dans les métadonnées d’audit ;
- `directReports` conservé en lecture seule ;
- HAB limité à son pipeline dédié de Simulation ;
- mode final revenu à Simulation ;
- contrôle de sécurité Git avant chaque checkpoint publié.

## Validation technique

Résultats consolidés :

- 309 tests backend réussis ;
- 301 sous-tests backend réussis ;
- 190 tests frontend réussis ;
- lint frontend sans erreur ;
- builds de production validés ;
- modules Windows validés syntaxiquement ;
- module Lookup Windows déployé ;
- worker Lookup confirmé actif ;
- affichage visuel validé dans le portail ;
- ouverture des propriétés sans délai bloquant ;
- dépôts `origin` et `backup` synchronisés sur les checkpoints C3.

## Limites conservées

Les éléments suivants ne font pas partie du périmètre C3 clôturé :

- accès distant et attributs RADIUS ;
- SPN et délégation avancée ;
- politiques d’authentification avancées ;
- certificats et photographies ;
- `proxyAddresses` et autres attributs multivalués complexes ;
- ACL et délégation générale ;
- GPO ;
- corbeille Active Directory ;
- fonctions avancées des groupes, ordinateurs, contacts et OU.

Ces éléments restent affectés aux chantiers ultérieurs de la roadmap.
