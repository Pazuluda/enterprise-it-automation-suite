# Architecture UI downstream EITAS Identity

## Objectif

Créer une distribution visuelle EITAS basée sur le moteur officiel
Keycloak sans modifier les mécanismes d’authentification ou de sécurité.

## Composants

- `ui/account-console` : espace compte utilisateur EITAS ;
- `ui/admin-console` : console d’administration EITAS ;
- `ui/shared` : styles, composants, logos et traductions partagés ;
- `overlay/themes/eitas/login` : formulaires de connexion ;
- futurs thèmes `email` et `welcome`.

## Mise à jour de Keycloak

Le moteur Keycloak reste issu de la distribution officielle.

Lors d’une montée de version :

1. mettre à jour le runtime officiel Keycloak ;
2. mettre à jour les dépendances UI Keycloak correspondantes ;
3. reconstruire les consoles EITAS ;
4. déployer sur l’instance parallèle ;
5. exécuter les tests de non-régression ;
6. migrer uniquement après validation.

## Interdictions

- ne pas modifier directement les thèmes embarqués de Keycloak ;
- ne pas modifier le backend d’authentification pour le branding ;
- ne pas versionner de secrets ;
- ne pas déployer directement sur `/auth` sans validation parallèle.
