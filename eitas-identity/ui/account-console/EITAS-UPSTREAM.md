# Origine de l’Account Console

## Socle

- Runtime Keycloak cible : `26.7.0`
- Account UI : `26.7.0`
- Admin Client : `26.7.0`
- UI Shared : `26.7.0`
- PatternFly : `5.4.2 / 5.4.14`
- Gestionnaire de paquets : `pnpm`

## Générateur d’origine

Le premier squelette provenait de `create-keycloak-theme`
et utilisait un modèle `25.0.4`.

Les dépendances, le paquet et les ressources ont ensuite été
alignés explicitement sur Keycloak `26.7.0`.

## Périmètre EITAS

Le projet remplace uniquement la couche React, le thème,
le branding et l’expérience visuelle de l’Account Console.

Le moteur d’authentification, les sessions, OIDC, OAuth2,
MFA, WebAuthn et les API Keycloak restent inchangés.
