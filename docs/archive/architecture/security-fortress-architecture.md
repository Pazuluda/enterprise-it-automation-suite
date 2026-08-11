# Architecture de sécurité Forteresse EITAS

## 1. Décision

EITAS adopte une architecture Zero Trust : refus par défaut, moindre privilège, séparation stricte des identités humaines et techniques, authentification forte, droits temporaires, double approbation pour les actions critiques et audit complet.

## 2. Principes

- Aucun service applicatif exécuté en root.
- Aucun worker membre de Domain Admins.
- Aucun mot de passe Active Directory stocké ou reçu par EITAS.
- Aucune permission implicite liée au réseau interne.
- L’API contrôle chaque autorisation, indépendamment du frontend.
- Les privilèges élevés sont temporaires, justifiés et révocables.
- Toute action sensible est tracée.
- Le contrôleur de domaine SRV-DC01 ne doit jamais être modifié ou supprimé par les tests EITAS.

## 3. Architecture cible

```text
Poste utilisateur ou PAW
        |
        | HTTPS + FIDO2 / Windows Hello
        v
Reverse proxy TLS
        |
        v
Keycloak
OIDC + AD/LDAP + Kerberos + WebAuthn
        |
        v
API EITAS
RBAC + ABAC + JIT + approbations
        |
        +---- PostgreSQL
        +---- Audit distant
        |
        | mTLS
        v
Workers Windows séparés
        |
        v
Active Directory
```

## 4. Identités

### Humains

- Comptes locaux de secours.
- Comptes Active Directory fédérés via Keycloak.
- Liaison par SID ou objectGUID, jamais uniquement par sAMAccountName.

### Linux

L’API fonctionne sous un compte système dédié :

```text
eitas:eitas
```

### Workers

Chaque worker possède :

- un certificat mTLS propre ;
- un identifiant propre ;
- des permissions API propres ;
- un périmètre propre ;
- une révocation indépendante.

### Comptes de service AD

```text
svc_eitas_snapshot
svc_eitas_lookup
svc_eitas_lifecycle
svc_eitas_adadmin
svc_eitas_adcheck
```

Aucun de ces comptes ne doit être Domain Admin.

## 5. UltraAdmin

Le rôle UltraAdmin peut gérer les utilisateurs, rôles, permissions, périmètres AD, workers, certificats, mode Production, audits et opérations de récupération.

Un compte quotidien ne conserve pas ce rôle en permanence.

L’élévation UltraAdmin utilise le JIT :

- durée limitée ;
- justification obligatoire ;
- MFA résistante au phishing ;
- expiration automatique ;
- révocation immédiate ;
- audit complet.

Deux comptes locaux de secours doivent rester disponibles. Le dernier compte de secours ne peut pas être supprimé.

## 6. Authentification

La cible est Keycloak avec :

- OIDC ;
- fédération AD/LDAP ;
- Kerberos/SPNEGO ;
- WebAuthn/FIDO2 ;
- Windows Hello for Business ;
- sessions révocables ;
- réauthentification pour les actions critiques.

EITAS ne reçoit jamais le mot de passe AD humain.

## 7. Autorisations

EITAS utilise RBAC et ABAC.

Exemples RBAC :

```text
requests.read
requests.create
requests.approve
requests.reject

ad.users.read
ad.users.create
ad.users.update
ad.users.disable
ad.users.delete

ad.groups.read
ad.groups.create
ad.groups.members.add
ad.groups.members.remove

ad.computers.read
ad.computers.create
ad.computers.update
ad.computers.delete

ad.ous.read
ad.ous.create
ad.ous.move
ad.ous.delete

workers.read
workers.manage

templates.read
templates.manage

audit.read

security.users.manage
security.roles.manage
security.permissions.manage
security.scopes.manage

system.production.enable
system.settings.manage
```

Les règles ABAC peuvent limiter selon :

- l’OU ;
- le type d’objet ;
- le service ;
- le groupe ;
- l’heure ;
- le poste utilisé ;
- la force de l’authentification ;
- le mode Simulation ou Production ;
- une approbation ;
- le niveau Tier.

Un refus explicite reste prioritaire sur une autorisation héritée.

## 8. Double approbation

La règle des quatre yeux s’applique notamment à :

- suppression d’une OU ;
- suppression massive ;
- suppression d’un compte privilégié ;
- attribution ou retrait du rôle UltraAdmin ;
- modification des périmètres AD ;
- passage en Production ;
- changement de politique de sécurité ;
- restauration complète ;
- autorisation d’agir hors OU=EITAS.

Le demandeur ne peut pas approuver sa propre demande.

## 9. Sécurité Active Directory

Périmètre opérationnel par défaut :

```text
OU=EITAS,DC=API,DC=LOCAL
```

EITAS interdit par défaut les modifications de :

- contrôleurs de domaine ;
- comptes Domain Admins ;
- groupes protégés ;
- comptes critiques ;
- objets adminCount=1 ;
- objets hors périmètre autorisé.

Séparation cible :

```text
Tier 0 : DC, identités de secours, Keycloak, sécurité centrale
Tier 1 : serveurs, workers, comptes de services
Tier 2 : utilisateurs, groupes métiers, postes clients, helpdesk
```

## 10. Données et fichiers runtime

Cible :

```text
/opt/enterprise-it-automation-suite
    Code applicatif

/var/lib/eitas
    Données runtime

/etc/eitas
    Configuration

/etc/eitas-api.env
    Secrets initiaux

/var/backups/eitas
    Sauvegardes chiffrées

/var/log/eitas
    Journaux éventuels
```

Permissions cibles :

```text
/var/lib/eitas       0750 eitas:eitas
Fichiers PII         0640 ou 0600
/etc/eitas-api.env   0600 root:root
Code /opt            lecture seule pour eitas
```

Les comptes, rôles, permissions, sessions, élévations, approbations, révocations et identités workers doivent migrer vers PostgreSQL.

## 11. Écritures atomiques

Chaque écriture doit utiliser :

- un fichier temporaire unique ;
- le même système de fichiers ;
- fsync lorsque nécessaire ;
- un remplacement atomique ;
- aucune extension temporaire fixe partagée.

Interdit :

```text
worker-status.json.tmp
```

Attendu :

```text
.worker-status.<identifiant-unique>.tmp
```

## 12. Durcissement systemd

Cible :

```ini
User=eitas
Group=eitas
UMask=0027

NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/eitas
```

Les options sont activées progressivement avec validation et rollback.

Vite ne doit jamais rester exposé sur `0.0.0.0:5173`.

## 13. Reverse proxy

Les utilisateurs accèdent à EITAS en HTTPS via un reverse proxy.

Le reverse proxy gère :

- TLS ;
- HSTS ;
- en-têtes de sécurité ;
- limitation de débit ;
- taille maximale des requêtes ;
- délais ;
- journalisation ;
- éventuellement le mTLS des workers.

Uvicorn ne doit pas être directement exposé aux utilisateurs finaux.

## 14. Workers et mTLS

La clé API partagée est progressivement remplacée par un certificat client par worker.

Chaque certificat possède :

- une identité ;
- une expiration ;
- un usage autorisé ;
- une chaîne de confiance ;
- une révocation.

Un worker ne peut appeler que ses routes.

Les appels sensibles utilisent un identifiant unique, un horodatage, un nonce et une vérification anti-rejeu.

PowerShell JEA doit être utilisé lorsque pertinent.

## 15. Audit

Chaque événement sensible doit contenir :

- l’identité ;
- la session ;
- le rôle actif ;
- l’adresse IP ;
- le poste ;
- l’action ;
- la cible ;
- le périmètre ;
- la justification ;
- l’approbateur éventuel ;
- le résultat ;
- l’horodatage.

Les événements forment une chaîne de hashes et sont envoyés vers une destination distante append-only, SIEM, syslog sécurisé ou stockage WORM.

## 16. Sauvegardes

Les sauvegardes sont :

- chiffrées ;
- versionnées ;
- hors du dépôt Git ;
- soumises à une rétention ;
- copiées hors du serveur principal ;
- restaurées régulièrement dans un environnement de test.

Une sauvegarde n’est valide qu’après un test de restauration.

## 17. Mode dégradé

En cas de panne AD ou Keycloak :

- les opérations AD sont bloquées par défaut ;
- les comptes locaux de secours restent disponibles ;
- les actions de récupération sont fortement auditées ;
- aucune permission n’est accordée sur la seule base d’un cache expiré.

## 18. Phases de migration

### Phase 303 — socle Linux et données

- arrêter ou limiter Vite ;
- créer le compte eitas ;
- déplacer le runtime dans /var/lib/eitas ;
- appliquer des permissions sûres ;
- corriger les écritures atomiques ;
- protéger toutes les routes ;
- ajouter rotation et rétention ;
- conserver un rollback complet.

### Phase 304 — exposition TLS

- reverse proxy ;
- HTTPS ;
- en-têtes de sécurité ;
- limitation de débit ;
- restriction réseau d’Uvicorn.

### Phase 305 — PostgreSQL et comptes locaux

- schéma PostgreSQL ;
- comptes locaux ;
- comptes de secours ;
- sessions sécurisées ;
- première console UltraAdmin.

### Phase 306 — Keycloak et Active Directory

- OIDC ;
- fédération LDAP/AD ;
- Kerberos ;
- liaison par SID/objectGUID ;
- WebAuthn/FIDO2.

### Phase 307 — RBAC et ABAC

- rôles ;
- permissions ;
- périmètres ;
- refus explicites ;
- protections backend ;
- adaptation frontend.

### Phase 308 — JIT et approbations

- élévation temporaire ;
- expiration ;
- justification ;
- double approbation ;
- réauthentification forte.

### Phase 309 — mTLS et workers

- autorité de certification ;
- certificat par worker ;
- révocation ;
- anti-rejeu ;
- comptes AD délégués ;
- JEA.

### Phase 310 — audit et sauvegardes

- chaîne de hashes ;
- audit distant ;
- sauvegardes chiffrées ;
- restauration testée ;
- rétention automatique.

### Phase 311 — validation de sécurité

- OWASP ASVS ;
- tests d’autorisation ;
- tests de concurrence ;
- tests de restauration ;
- tests de compromission de worker ;
- revue des permissions AD ;
- test d’intrusion.

## 19. Ordre obligatoire

1. sécuriser l’existant ;
2. séparer code et données ;
3. supprimer l’exécution root ;
4. protéger toutes les routes ;
5. ajouter PostgreSQL ;
6. ajouter les comptes de secours ;
7. ajouter Keycloak et AD ;
8. ajouter RBAC et ABAC ;
9. ajouter JIT et approbations ;
10. remplacer les clés API workers par mTLS ;
11. ajouter l’audit distant ;
12. effectuer la recette complète.

## 20. Première étape technique

Le premier lot d’implémentation sera `303B-1` :

- arrêter proprement le serveur Vite exposé ;
- corriger l’écriture concurrente de `worker-status.json` ;
- rendre le chemin runtime configurable ;
- préparer le compte système `eitas` ;
- préparer `/var/lib/eitas` ;
- tester la migration sans basculer immédiatement la production.

Aucune migration de données ne sera effectuée avant validation complète de ce lot.
