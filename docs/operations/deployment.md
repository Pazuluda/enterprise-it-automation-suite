# Déploiement

Ce document décrit le modèle de déploiement actuellement validé pour EITAS.

Il ne lance aucune opération de déploiement et ne remplace pas les validations ciblées propres à chaque évolution.

Le dépôt ne possède actuellement pas de pipeline unique automatisant intégralement le déploiement Linux, frontend, Identity et workers Windows.

## Principes de déploiement

Un déploiement EITAS doit rester :

- explicite ;
- ciblé ;
- réversible lorsque le composant le permet ;
- validé avant et après modification ;
- indépendant de toute activation implicite du mode Production.

Le simple fait qu’un build ou qu’un service démarre ne suffit pas à considérer un déploiement comme validé.

## Topologie Production actuelle

Le chemin utilisateur actuellement validé est :

```text
Navigateur
  |
  | HTTPS :62443
  v
Nginx
  |
  | proxy HTTP loopback
  v
FastAPI 127.0.0.1:8000
  |
  +-- /app/*       -> api/static/app/index.html
  +-- /static/*    -> api/static/*
  +-- /api/*       -> routes FastAPI
```

EITAS Identity suit séparément :

```text
Navigateur
  |
  | HTTPS :62443/auth/
  v
Nginx
  |
  v
Keycloak Production 127.0.0.1:8180
```

Les ports internes ne constituent pas des interfaces publiques.

## Source du code

Le dépôt déployé se trouve actuellement sous :

```text
/opt/enterprise-it-automation-suite
```

Le déploiement ne doit pas déplacer les données runtime dans le dépôt.

Les données persistantes restent sous :

```text
/var/lib/eitas
```

et la configuration API sensible sous :

```text
/etc/eitas-api.env
```

## Backend FastAPI

Le service Production est :

```text
eitas-api.service
```

Son unité principale contient historiquement une commande Uvicorn utilisant `0.0.0.0:8000`.

Cette commande n’est **pas** la commande effective du runtime actuellement validé.

Le drop-in :

```text
/etc/systemd/system/eitas-api.service.d/40-loopback-only.conf
```

remplace `ExecStart` et lance :

```text
/usr/local/libexec/eitas-api-loopback
```

Le launcher effectif démarre Uvicorn sur :

```text
127.0.0.1:8000
```

Un déploiement ne doit donc jamais supprimer ou contourner ce confinement loopback sans nouvelle validation de sécurité.

## Durcissement systemd

Le service API actuel fonctionne sous :

```text
eitas:eitas
```

et possède notamment :

- `UMask=0027` ;
- `NoNewPrivileges=true` ;
- `PrivateTmp=true` ;
- `PrivateDevices=true` ;
- `ProtectSystem=strict` ;
- `ProtectHome=true` ;
- un `CapabilityBoundingSet` vide ;
- `ReadWritePaths=/var/lib/eitas`.

Toute nouvelle unité ou modification de service doit préserver ces protections ou faire l’objet d’une revue explicite.

## Dépendances backend

Les dépendances Python du projet sont décrites dans :

```text
api/requirements.txt
```

L’environnement virtuel utilisé par le service est actuellement :

```text
api/.venv
```

Une mise à jour backend nécessitant des dépendances différentes doit être validée dans cet environnement avant redémarrage du service.

## Frontend React

Le frontend source se trouve sous :

```text
frontend/
```

Le build Vite produit les artefacts dans :

```text
frontend/dist/
```

La configuration Vite utilise :

```text
base: /static/app/
```

Les noms des fichiers JavaScript et CSS de Production sont hashés par le build.

## Copie servie par FastAPI

FastAPI ne sert pas directement `frontend/dist`.

Le build effectivement servi se trouve dans :

```text
api/static/app/
```

`api/main.py` monte :

```text
/static -> api/static
```

et les routes :

```text
/app
/app/{full_path:path}
```

renvoient :

```text
api/static/app/index.html
```

Le routage SPA est donc géré par FastAPI.

## Synchronisation du frontend

Lors du dernier audit, les deux arbres :

```text
frontend/dist/
api/static/app/
```

contenaient exactement :

- `12` fichiers chacun ;
- le même ensemble de chemins ;
- `0` différence de contenu.

Les `10` ressources référencées directement par `index.html` répondaient toutes en HTTP `200`, aussi bien depuis FastAPI loopback que via Nginx HTTPS.

## Limite actuelle du déploiement frontend

Aucun script générique de déploiement tracké dans le dépôt n’automatise actuellement la synchronisation :

```text
frontend/dist -> api/static/app
```

La documentation ne doit donc pas prétendre qu’un `npm run build` publie automatiquement le nouveau frontend.

Un déploiement frontend est considéré incomplet tant que le contenu effectivement servi sous `api/static/app` n’a pas été synchronisé et vérifié.

Le mécanisme exact de copie peut évoluer ; il doit être automatisé et documenté séparément lorsqu’un outil officiel sera ajouté au dépôt.

## Validation frontend après synchronisation

Après mise à jour du frontend, les contrôles doivent au minimum vérifier :

1. que `api/static/app/index.html` correspond au build attendu ;
2. que les assets référencés existent ;
3. que `/app/` répond ;
4. que chaque asset principal répond via `/static/app/...` ;
5. que le même résultat est accessible via HTTPS `:62443` ;
6. que le portail peut terminer son authentification OIDC.

La comparaison de hash ou de contenu entre `frontend/dist` et `api/static/app` constitue un contrôle utile lorsque les deux arbres sont censés être identiques.

## Nginx Production

La configuration Production principale actuellement active est :

```text
/etc/nginx/sites-enabled/eitas.conf
```

Les limites de débit sont définies dans :

```text
/etc/nginx/conf.d/eitas-rate-limits.conf
```

Le serveur expose :

```text
62443/tcp TLS
```

avec TLS `1.2` et `1.3`.

## Routage Nginx

Le bloc Production actuel :

- masque publiquement `/docs` ;
- masque publiquement `/redoc` ;
- masque publiquement `/openapi.json` ;
- relaie `/auth/` vers Keycloak Production ;
- relaie le trafic applicatif restant vers FastAPI loopback.

FastAPI peut encore exposer certaines interfaces de documentation en loopback. Leur présence locale ne signifie donc pas qu’elles sont publiées par Nginx.

## Headers de sécurité

Le frontal Production applique notamment :

- HSTS ;
- `X-Content-Type-Options: nosniff` ;
- `X-Frame-Options: DENY` pour le serveur principal ;
- `Referrer-Policy: no-referrer` ;
- une `Permissions-Policy` restrictive ;
- `Cross-Origin-Opener-Policy` ;
- `Cross-Origin-Resource-Policy` ;
- une Content Security Policy.

Un changement Nginx doit conserver les protections pertinentes ou documenter explicitement leur remplacement.

## Limites de débit

Les zones actuellement observées utilisent :

```text
API      : 30 requêtes/seconde
Keycloak : 50 requêtes/seconde
```

Le serveur applique ensuite ses valeurs de burst et ses limites de connexions selon les locations concernées.

## TLS

Le certificat actuellement utilisé se trouve dans :

```text
/etc/eitas/pki/certs/eitas-server.crt
```

La clé privée se trouve dans :

```text
/etc/eitas/pki/private/eitas-server.key
```

La clé privée ne doit jamais être copiée dans le dépôt Git ou incluse dans un artefact de release.

## Firewall

Le firewall Linux observé autorise actuellement depuis le réseau EITAS :

```text
22/tcp
62443/tcp
```

Les ports internes `8000`, `8180`, `8280`, `8380`, `8480`, `9000` ou le port Vite `5173` ne font pas partie de l’exposition utilisateur Production validée.

## EITAS Identity

Le service Identity Production est :

```text
keycloak.service
```

Il dépend de PostgreSQL et fonctionne sous :

```text
keycloak:keycloak
```

Sa configuration sensible est chargée depuis :

```text
/etc/keycloak/keycloak.env
```

Un changement du portail ne doit pas nécessiter de redéployer ou redémarrer Keycloak sauf si la modification concerne réellement Identity.

## Routes Identity non Production

La configuration Nginx contient encore des routes pour plusieurs environnements ou candidats Identity.

La présence d’une location Nginx telle que :

```text
/identity-test/
/identity-preprod/
/identity-candidate/
```

ne prouve pas que le service correspondant est actif.

Le statut systemd et les listeners doivent être contrôlés avant de considérer un environnement disponible.

## Route temporaire HAB review

La configuration Nginx auditée contient encore une route temporaire :

```text
/app/hab-review/
```

Cette route provient d’un ancien artefact de revue HAB et ne doit pas être décrite comme un composant permanent du portail Production.

Sa suppression éventuelle relève d’un nettoyage opérationnel distinct et doit être validée avant modification Nginx.

## Ordre logique d’un déploiement applicatif

Pour une évolution applicative classique, l’ordre de travail recommandé est :

1. vérifier le commit et le worktree attendus ;
2. exécuter les tests ciblés ;
3. exécuter les régressions demandées par le lot ;
4. vérifier les dépendances modifiées ;
5. construire le frontend si nécessaire ;
6. vérifier le build produit ;
7. synchroniser explicitement le build vers `api/static/app` si le frontend change ;
8. valider la configuration avant toute relance de service ;
9. redémarrer uniquement les services réellement concernés ;
10. contrôler les listeners et les statuts ;
11. effectuer les validations HTTP/HTTPS ;
12. effectuer les validations fonctionnelles du lot.

Cette liste décrit un ordre de sécurité. Elle ne signifie pas que chaque déploiement doit redémarrer tous les composants.

## Redémarrages ciblés

Un changement de documentation ne nécessite aucun restart.

Un changement frontend statique ne doit pas entraîner automatiquement un restart Keycloak.

Un changement backend peut nécessiter un restart de `eitas-api.service`, mais uniquement après validation préalable.

Un changement Nginx doit être validé syntaxiquement avant reload.

Un changement Identity doit suivre les procédures spécifiques du composant Identity.

Les workers Windows sont gérés séparément du service Linux.

## Mode Simulation

Un déploiement de code, de frontend ou de documentation ne doit jamais modifier implicitement le mode global EITAS.

Le mode de référence hors opération explicitement autorisée reste :

```text
Simulation
```

Une activation Production constitue une décision fonctionnelle distincte d’un déploiement de fichiers.

## Capacités spécialisées

Les mécanismes ACL et Corbeille AD récents possèdent leurs propres gates de sécurité.

Leur présence dans le code déployé ne doit pas être interprétée comme une autorisation générale d’écriture Active Directory.

En particulier, la restauration contrôlée C9.5 reste une chaîne étroite avec opt-in worker et autorisations dédiées.

## Vérifications de santé

Après un déploiement touchant Linux, les contrôles pertinents comprennent notamment :

- état de `eitas-api.service` ;
- état de `keycloak.service` si Identity a été touché ;
- listener public `62443` ;
- listener FastAPI loopback `127.0.0.1:8000` ;
- listeners Keycloak attendus ;
- réponse HTTPS du portail ;
- disponibilité des assets React ;
- authentification OIDC ;
- accès API selon le rôle ;
- état des workers Windows via leurs heartbeats.

## Documentation API publique

Dans le déploiement Production actuel, Nginx retourne `404` pour :

```text
/docs
/redoc
/openapi.json
```

La documentation interactive locale `/docs-local` est une surface de développement/administration locale et ne doit pas être exposée publiquement sans décision de sécurité explicite.

## Données runtime

Le déploiement de code ne doit pas écraser :

```text
/var/lib/eitas
```

Ce répertoire contient les demandes, templates, audits, jobs, snapshots, catalogues, statuts workers ainsi que plusieurs registres de sécurité spécialisés.

La mise à jour du code et la migration éventuelle de données sont deux opérations distinctes.

## Sauvegarde avant changements sensibles

EITAS utilise des écritures atomiques pour plusieurs fichiers runtime, mais cela ne constitue pas une sauvegarde générale.

Avant toute modification structurelle de données, de configuration système ou Identity, une stratégie de sauvegarde adaptée au composant doit être définie.

La politique de backup/recovery est documentée séparément et ne doit pas être remplacée par la seule présence de fichiers temporaires ou de locks.

## Absence actuelle de pipeline universel

Le dépôt ne fournit pas actuellement un pipeline unique couvrant automatiquement :

- build backend ;
- migration des dépendances ;
- build frontend ;
- synchronisation frontend ;
- configuration systemd ;
- configuration Nginx ;
- Identity ;
- workers Windows ;
- validation fonctionnelle finale.

Cette absence doit rester visible dans la documentation afin de ne pas donner une fausse impression de déploiement entièrement automatisé.

## Documentation associée

- [Installation et prérequis](installation.md)
- [Configuration](configuration.md)
- [Vue architecture](../architecture/overview.md)
- [Backend et API](../architecture/backend-api.md)
- [Frontend](../architecture/frontend.md)
- [Agent Windows](../architecture/windows-agent.md)
- [Architecture de sécurité](../architecture/security.md)

## Règle de maintenance

Cette page doit être mise à jour dès qu’un pipeline de déploiement officiel, un mécanisme de synchronisation frontend, une nouvelle topologie réseau ou une nouvelle procédure de service est réellement validé.
