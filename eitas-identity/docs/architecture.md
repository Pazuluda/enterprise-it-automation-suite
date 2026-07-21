# EITAS Identity — Architecture parallèle

## Objectif

Créer une distribution IAM EITAS basée sur le code source de Keycloak,
sans modifier l'instance Keycloak actuellement utilisée en production.

## Base amont

- Projet amont : Keycloak
- Version initiale figée : 26.7.0
- Licence du code amont : Apache License 2.0
- Politique : modifications minimales du cœur
- Priorité : thèmes, extensions SPI, configuration et automatisation

## Production actuelle — ne pas modifier pendant le développement

- Service systemd : keycloak.service
- Répertoire actif : /opt/keycloak
- Version installée : /opt/keycloak-26.7.0
- Configuration : /etc/keycloak/keycloak.env
- Port HTTP interne : 127.0.0.1:8180
- Port de management : 127.0.0.1:9000
- URL publique : https://10.10.10.11:62443/auth
- Base PostgreSQL : keycloak
- Realm applicatif : eitas

## Instance parallèle EITAS Identity

- Service prévu : eitas-identity-test.service
- Compte système : eitas-identity
- Racine projet : /opt/eitas-identity
- Configuration : /etc/eitas-identity
- Données : /var/lib/eitas-identity
- Journaux : /var/log/eitas-identity
- Port HTTP prévu : 127.0.0.1:8280
- Port de management prévu : 127.0.0.1:9100
- URL publique prévue : https://10.10.10.11:62443/identity-test
- Base PostgreSQL prévue : eitas_identity_test
- Realm de validation prévu : eitas

## Garanties de séparation

L'instance de développement ne doit jamais utiliser :

- le service keycloak.service ;
- le port 8180 ;
- le port de management 9000 ;
- la base PostgreSQL keycloak ;
- l'URL publique /auth ;
- le répertoire /opt/keycloak ;
- le fichier /etc/keycloak/keycloak.env.

## Stratégie produit

EITAS Identity conservera :

- OIDC ;
- Authorization Code avec PKCE ;
- JWT RS256 ;
- MFA TOTP ;
- WebAuthn et passkeys ;
- sessions et renouvellement des jetons ;
- rôles et groupes ;
- console d'administration.

EITAS Identity personnalisera :

- identité visuelle ;
- pages de connexion ;
- espace compte utilisateur ;
- courriels ;
- messages d'erreur ;
- paramètres de confidentialité ;
- règles de conservation ;
- extensions EITAS ;
- configuration sécurisée ;
- construction reproductible ;
- SBOM et suivi des versions amont.

## Migration finale

La migration vers /auth sera effectuée seulement après :

1. validation fonctionnelle complète ;
2. validation MFA ;
3. validation OIDC du portail ;
4. validation JWT de l'API ;
5. validation des rôles ;
6. sauvegarde de la base ;
7. procédure de rollback testée.
