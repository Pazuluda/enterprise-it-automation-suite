# Instance parallèle EITAS Identity

## Runtime

- Répertoire : `/opt/eitas-identity/runtime/keycloak-26.7.0-eitas`
- Compte système : `eitas-identity`
- Configuration : `/etc/eitas-identity/eitas-identity-test.env`

## PostgreSQL

- Serveur : `127.0.0.1:5432`
- Base : `eitas_identity_test`
- Rôle : `eitas_identity_test`
- Base de production `keycloak` : séparée et inchangée

## Réseau prévu

- HTTP interne : `127.0.0.1:8280`
- Management : `127.0.0.1:9100`
- URL publique prévue : `https://10.10.10.11:62443/identity-test`
- Reverse proxy prévu : Nginx

## Cache

L'instance de test utilise un cache local afin de rester indépendante
de l'instance Keycloak de production.
