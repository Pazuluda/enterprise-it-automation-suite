# Dépannage

Ce document fournit une méthode de diagnostic sûre pour le runtime EITAS actuellement validé.

## Principes de diagnostic

Commencer par observer avant de modifier.

Un diagnostic ne doit pas redémarrer un service, modifier une tâche planifiée, changer le mode global, éditer une configuration ou ouvrir un chemin Production uniquement pour obtenir davantage d’informations.

Les contrôles lecture seule doivent être privilégiés et les secrets doivent rester masqués.

## Ordre de vérification recommandé

Pour un incident portail ou API, vérifier dans cet ordre : état du service API, listener FastAPI loopback, listener Nginx public, réponse HTTPS, puis authentification et autorisation.

Pour un incident Active Directory, vérifier ensuite l’état des workers Windows, nombre de processus, heartbeat, mode Simulation et files de jobs concernées.

Cette progression évite de redémarrer plusieurs composants alors que l’origine de l’incident se trouve sur une seule couche.

## Référence runtime actuelle

Le service API validé fonctionne sous utilisateur `eitas` et écoute FastAPI sur `127.0.0.1:8000`.

Nginx expose actuellement le portail et API sur `https://10.10.10.11:62443`.

Le runtime Windows Active Directory validé est installé sur `SRV-DC01` dans `C:\EnterpriseIT\agent-windows`.

Le mode global attendu pendant les opérations normales de développement et de validation reste `Simulation` sauf ouverture explicite et contrôlée du chemin concerné.

## API inaccessible

Si l’API EITAS ne répond plus, commencer par vérifier `eitas-api.service` sans le redémarrer.

Les contrôles utiles comprennent `systemctl status eitas-api.service --no-pager`, `journalctl -u eitas-api.service` et la présence du listener `127.0.0.1:8000` avec `ss -ltnp`.

Le listener FastAPI attendu est uniquement loopback. Réouvrir le port 8000 sur le réseau ne constitue pas une méthode de dépannage valide.

Si le service échoue au démarrage, vérifier ensuite les erreurs de configuration, accès à `/var/lib/eitas`, permissions et variables fournies par `/etc/eitas-api.env`, sans afficher les secrets.

## Portail HTTPS inaccessible

Si le portail ne répond pas sur `https://10.10.10.11:62443/app/`, vérifier d’abord Nginx, son listener 62443 et ses journaux, puis seulement le backend FastAPI.

Le chemin normal est navigateur vers Nginx en HTTPS, puis Nginx vers FastAPI sur `127.0.0.1:8000`.

Le serveur de développement Vite sur 5173 ne fait pas partie du runtime de production et ne doit pas être rouvert comme correctif de dépannage.

Les routes publiques `/docs`, `/redoc` et `/openapi.json` sont volontairement bloquées en production ; une réponse 404 sur ces chemins ne prouve donc pas une panne API.

## Problème d’authentification ou d’autorisation

Distinguer un problème d’authentification d’un refus RBAC avant de modifier la configuration.

Les utilisateurs du portail utilisent le flux OIDC/Bearer avec EITAS Identity, tandis que les workers Windows utilisent `X-API-Key`.

Un diagnostic ne doit jamais afficher un Bearer token, une clé API ou un secret OIDC.

Une réponse 401 oriente d’abord vers l’authentification ou le credential présenté. Une réponse 403 peut indiquer que l’identité est reconnue mais ne possède pas le rôle requis pour l’opération demandée.

Avant de changer les rôles ou clients Identity, vérifier le endpoint concerné, le type de credential utilisé et le rôle attendu.

## Worker Windows absent ou stale

Pour un worker Windows annoncé absent ou stale, vérifier d’abord la tâche planifiée, son état, son action, puis le processus correspondant et son heartbeat.

Les commandes de lecture telles que `Get-ScheduledTask`, `Get-ScheduledTaskInfo` et `Get-CimInstance Win32_Process` permettent de diagnostiquer cette chaîne sans redémarrage.

Les trois workers spécialisés AD Admin, AD Check et AD Lookup sont normalement persistants après le démarrage, alors que Employee Lifecycle est périodique.

Un `LastTaskResult` non nul ou inhabituel doit être interprété avec l’état réel de la tâche, du processus et du heartbeat ; il ne doit pas être utilisé seul pour déclarer un worker en panne.

## Job bloqué ou non consommé

Pour un job qui reste en attente, identifier d’abord sa famille : AD Admin, AD Check, AD Lookup ou AD Explorer.

Vérifier ensuite le worker responsable, son heartbeat et le fichier de jobs correspondant dans `/var/lib/eitas`.

Les principaux fichiers observés sont `ad-admin-jobs.json`, `ad-check-jobs.json`, `ad-lookup-jobs.json` et `ad-explorer-jobs.json`.

Ne pas éditer manuellement un fichier de jobs pour débloquer une demande. Une modification directe peut casser l’historique, audit, mécanismes de consommation ou garanties de sécurité.

Si un job concerne un chemin sensible C8 ou C9, vérifier également les registres de sécurité associés avant toute tentative de reprise.

## Mode global inattendu

Si le mode attendu et le mode observé divergent, ne pas essayer de corriger la situation en basculant immédiatement vers Production.

Comparer d’abord la configuration locale Windows avec la réponse `GET /api/agent/mode` et identifier quel composant porte la valeur inattendue.

Pendant un diagnostic ou après une reprise, `Simulation` reste le mode sûr attendu tant qu’une ouverture Production n’a pas été explicitement autorisée par le lot concerné.

## Erreur PowerShell ou Active Directory

Une erreur PowerShell doit d’abord être attribuée au runner, au module chargé ou à la commande Active Directory concernée.

Vérifier le script réellement exécuté par la tâche planifiée, les modules chargés, les journaux disponibles et le contexte `SYSTEM` avant de modifier le code ou les permissions.

Un module candidat doit être validé avec le parseur Windows PowerShell 5.1 avant déploiement.

Pour un problème Active Directory, confirmer le DN ou objet cible, le contrôleur de domaine et le mode Simulation avant toute action corrective.

Ne pas transformer une erreur de lecture ou de résolution en écriture AD exploratoire.

## Restauration C9.5 non disponible

Le chemin réel de restauration des objets supprimés est volontairement fail-closed hors validation contrôlée.

Le switch `-EnableDeletedObjectRestoreExecution` ne fait pas partie de la tâche AD Admin permanente actuellement installée.

Les états audités `RESTORE_OPTIN_IN_TASK_ACTIONS=NO` et `RESTORE_OPTIN_IN_RUNNING_PROCESSES=NO` sont donc normaux après la validation C9.5.

Une restauration refusée ne doit pas être contournée en ajoutant manuellement le switch à la tâche planifiée. Il faut reprendre la chaîne d’autorisation et les gates C9.5 prévus.

## Erreur de permissions ou accès runtime

Si le service ne peut plus lire ou écrire une donnée runtime, vérifier le propriétaire, le groupe, le mode du fichier et ceux de son répertoire parent avant de lancer un `chmod` ou `chown` correctif.

Le répertoire `/var/lib/eitas` et ses contenus utilisent volontairement plusieurs combinaisons de permissions et propriétaires selon leur rôle.

Une correction globale récursive des permissions peut affaiblir les protections ou rendre certains composants incompatibles.

Le fichier `/etc/eitas-api.env` doit rester protégé et son contenu ne doit pas être affiché pour diagnostiquer une simple erreur de permissions.

## Secrets dans les sorties de diagnostic

Si une commande de diagnostic risque de retourner une clé API, un Bearer token, un mot de passe ou un secret OIDC, filtrer ou masquer la valeur avant de partager la sortie.

Un contrôle peut confirmer la présence d’un secret avec un marqueur tel que `<REDACTED_PRESENT>` sans révéler sa valeur.

Ne jamais copier un secret réel dans un ticket, une documentation, une issue Git ou une conversation de validation.

## Documentation associée

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Déploiement](deployment.md)
- [Workers Windows](windows-workers.md)
- [Sauvegarde et reprise](backup-recovery.md)
- [Architecture de sécurité](../architecture/security.md)
- [Corbeille Active Directory](../features/ad-recycle-bin.md)

## Règle de maintenance

Cette page doit être mise à jour lorsqu’un nouveau composant runtime, worker, mécanisme d’authentification, chemin sensible ou procédure de diagnostic validée est introduit dans EITAS.
