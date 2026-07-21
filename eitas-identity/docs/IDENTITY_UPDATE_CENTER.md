# Centre de mise à jour EITAS Identity

Le Centre de mise à jour permet aux utilisateurs disposant du rôle
`UltraAdmin` de consulter l’état assaini d’EITAS Identity et de lancer
uniquement une vérification d’intégrité de la source upstream.

Il ne télécharge, n’installe et ne déploie aucune mise à jour.

## Flux sécurisé

1. La console Account appelle l’API avec un jeton Bearer.
2. L’API vérifie le rôle `UltraAdmin`.
3. Une requête fixe `verify_upstream` est placée dans la file d’attente.
4. Une unité systemd `.path` déclenche un runner root confiné.
5. Le runner exécute uniquement `scripts/verify-upstream.sh`.
6. Le résultat assaini est enregistré dans `status.json`.

Aucun argument ou nom de commande n’est fourni par le navigateur.

## Sécurité

- clé API des workers refusée ;
- source, tag et commit verrouillés ;
- quinze patches cœur contrôlés par SHA-256 ;
- timeout de 120 secondes ;
- `ProtectSystem=strict` ;
- `NoNewPrivileges=yes` ;
- production verrouillée ;
- mises à jour automatiques désactivées.

## Installation

Installation sans démarrer le watcher :

    ./scripts/install-identity-update-source-check.sh

Installation puis démarrage pour la session courante :

    ./scripts/install-identity-update-source-check.sh --start-path

Le watcher reste toujours désactivé au démarrage du serveur.
