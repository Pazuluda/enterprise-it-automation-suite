# État du déploiement parallèle

## Instance de production conservée

- Service : `keycloak.service`
- Port interne : `127.0.0.1:8180`
- URL publique : `/auth`
- Base PostgreSQL : `keycloak`
- État : inchangé

## Instance EITAS Identity de test

- Service : `eitas-identity-test.service`
- Runtime : `/opt/eitas-identity/runtime/keycloak-26.7.0-eitas`
- Utilisateur système : `eitas-identity`
- Port HTTP : `127.0.0.1:8280`
- Port management : `127.0.0.1:9100`
- URL publique : `/identity-test`
- Base PostgreSQL : `eitas_identity_test`
- Cache : local
- Activation automatique au démarrage : désactivée

## Reverse proxy

Nginx reste l’unique reverse proxy.

La route `/identity-test/` transmet les requêtes vers
`127.0.0.1:8280`.

Le port de management `9100` n’est pas exposé par Nginx.

## Contrôles validés

- endpoint de santé : `UP` ;
- endpoint OIDC interne : HTTP 200 ;
- endpoint OIDC public : HTTP 200 ;
- issuer public conforme ;
- console d’administration accessible ;
- production `/auth` toujours disponible ;
- écoute des ports 8280 et 9100 limitée à la boucle locale ;
- service de test non activé automatiquement au démarrage.
