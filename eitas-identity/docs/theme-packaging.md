# Paquet du thème EITAS Identity

## Construction

Commande :

    /opt/eitas-identity/scripts/build-theme.sh

## Archive produite

L’archive est générée sous :

    build/eitas-identity-theme-<version>.jar

Un fichier SHA-256 est créé à côté de l’archive.

## Structure attendue

    META-INF/MANIFEST.MF
    META-INF/keycloak-themes.json
    theme/eitas/login/theme.properties
    theme/eitas/login/messages/messages_fr.properties
    theme/eitas/login/messages/messages_en.properties
    theme/eitas/login/resources/css/eitas.css
    theme/eitas/login/resources/img/eitas-identity.svg

## Déploiement

L’archive sera installée dans le répertoire providers de l’instance
EITAS Identity parallèle.

Elle ne doit pas être déployée dans l’instance Keycloak de production
avant la validation complète de l’environnement parallèle.
