# Workers Windows

Ce document décrit le runtime Windows actuellement validé pour les workers EITAS Active Directory.

Il distingue les valeurs réellement déployées des valeurs par défaut présentes dans le code source.

## Hôte actuellement validé

Le runtime Active Directory audité fonctionne actuellement sur `SRV-DC01` avec Windows PowerShell 5.1.

Le répertoire installé est `C:\EnterpriseIT\agent-windows`.

Les procédures de cette page décrivent cet environnement validé. Elles ne constituent pas un installateur Windows universel.

## Rôle du serveur Windows

Le serveur Windows assure les opérations nécessitant les outils et APIs Active Directory natives de Windows.

Le runtime utilise plusieurs workers spécialisés : Employee Lifecycle, AD Admin, AD Check et AD Lookup Live.

## Configuration locale

La configuration installée est chargée depuis `C:\EnterpriseIT\agent-windows\config.json`.

Les propriétés observées lors du dernier audit sont : `ApiBaseUrl`, `ApiKey`, `AutoCreateMissingGroups`, `AutoCreateMissingOUs`, `DisabledUsersOu`, `EitasBaseOu`, `GroupsOu`, `Mode`, `PollIntervalSeconds` et `UsersBaseOu`.

La valeur `ApiKey` est un secret local. Elle ne doit jamais être affichée, documentée ou commitée.

## Endpoint API réellement utilisé

Le runtime Windows utilise actuellement `https://10.10.10.11:62443`.

Les workers ne contactent donc pas directement le listener FastAPI interne `127.0.0.1:8000`.

Le fichier historique `agent-windows/config.example.json` contenant `http://10.10.10.11:8000` ne doit pas être copié tel quel sur une nouvelle installation.

## Mode global

La configuration Windows auditée contient actuellement `Mode = Simulation`.

Le contrôle distant `GET /api/agent/mode` a également retourné `Simulation`.

Le mode local et le mode exposé par API étaient donc convergents lors du dernier audit.

Une opération de maintenance ou un déploiement ne doit jamais activer Production implicitement.

## Tâches planifiées Windows

Quatre tâches EITAS ont été observées sur `SRV-DC01`.

### EITAS AD Admin Worker

État audité : `Running`, principal `SYSTEM`, `ServiceAccount`, niveau `Highest`, déclenchement au démarrage.

Action installée : `Run-AdAdminWorker.ps1 -IntervalSeconds 1`.

Lors du dernier audit, exactement un processus AD Admin était actif.

### EITAS AD Check Worker

État audité : `Running`, principal `SYSTEM`, `ServiceAccount`, niveau `Highest`, déclenchement au démarrage.

Action installée : `Run-AdCheckWorker.ps1 -IntervalSeconds 5`.

Lors du dernier audit, exactement un processus AD Check était actif.

### EITAS AD Lookup Live Worker

État audité : `Running`, principal `SYSTEM`, `ServiceAccount`, niveau `Highest`, déclenchement au démarrage.

Action installée : `Run-AdLookupWorker.ps1 -IntervalSeconds 1`.

Cette valeur runtime surcharge le polling par défaut plus court présent dans le code.

Lors du dernier audit, exactement un processus AD Lookup était actif.

### EITAS Employee Lifecycle Agent

État audité : `Ready`, principal `SYSTEM`, `ServiceAccount`, niveau `Highest`.

Action installée : `Run-EitasAgent.ps1`.

La tâche est répétée toutes les deux minutes avec une répétition `PT2M`.

Contrairement aux trois workers spécialisés, Employee Lifecycle est périodique et ne reste pas nécessairement actif entre deux déclenchements.

Lors du dernier audit, `LastTaskResult = 0` et aucun processus lifecycle permanent était attendu entre deux exécutions.

## AD Check et contrat de packaging

Le runner `agent-windows/Run-AdCheckWorker.ps1` charge explicitement `agent-windows/modules/EitasAdCheck.ps1` puis utilise `Process-PendingAdCheckJobs`.

Un audit réalisé pendant la refonte documentaire a identifié un défaut historique de packaging : le runner était versionné alors que le module `EitasAdCheck.ps1` installé sur Windows ne l’était pas dans Git.

La provenance du module installé a été vérifiée avant récupération : les neuf fonctions métier correspondent exactement aux fonctions historiques retirées de l’Employee Lifecycle lors de la modularisation, et le wrapper local `Invoke-EitasApi` délègue uniquement vers `Invoke-EitasApiRequest` avec la configuration du worker.

Le fichier installé parse avec zéro erreur sous Windows PowerShell 5.1.

Le module récupéré dans le candidat possède le SHA-256 `41cb6bef4b244c2e173eca1cda00949fd108d71d78cd1daa8bf2e954ed976808`, identique au module actuellement installé sur `SRV-DC01`.

Le test permanent `api/tests/test_ad_check_worker_packaging.py` protège désormais la présence du module, son chargement par le runner, le contrat de ses fonctions et la délégation vers le helper API partagé.

Une simulation de checkout Git propre contenant le correctif a passé les 4 tests de packaging.

La régression de la couche Windows worker a ensuite passé 302 tests et 16 subtests, avec 17 warnings historiques connus dans le périmètre exécuté.

Aucun redéploiement Windows du module AD Check n’était nécessaire : le fichier installé était déjà celui validé.

## Restauration contrôlée C9.5

La restauration réelle des objets supprimés dispose d’une autorisation supplémentaire indépendante du mode global Simulation.

Le runner AD Admin accepte explicitement le switch `-EnableDeletedObjectRestoreExecution` pour ce chemin contrôlé.

Ce switch ne fait pas partie de la tâche planifiée permanente actuellement installée.

Lors du dernier audit, `RESTORE_OPTIN_IN_TASK_ACTIONS=NO` et `RESTORE_OPTIN_IN_RUNNING_PROCESSES=NO`.

Le runtime Windows est donc revenu à l’état fail-closed attendu après la validation contrôlée C9.5.

Ajouter ce switch à une tâche permanente sans suivre toute la chaîne d’autorisation C9.5 est interdit.

## AD Lookup Live

Le runner `agent-windows/Run-AdLookupWorker.ps1` utilise principalement `agent-windows/modules/EitasAdLookup.ps1` pour les lectures temps réel de l’Explorateur AD.

Le code contient notamment un polling worker par défaut de 250 ms, un rafraîchissement snapshot de 5 secondes, un catalogue domaine de 15 secondes et un heartbeat de 60 secondes.

La tâche planifiée actuellement installée surcharge le polling worker avec `-IntervalSeconds 1`.

La documentation du runtime doit toujours distinguer les valeurs par défaut du code des valeurs effectivement déployées.

## Périmètre Active Directory actuellement configuré

Le runtime audité utilise `OU=EITAS,DC=API,DC=LOCAL` comme base EITAS.

Les utilisateurs utilisent `OU=Users,OU=EITAS,DC=API,DC=LOCAL`.

Les groupes utilisent `OU=Groups,OU=EITAS,DC=API,DC=LOCAL`.

Les utilisateurs désactivés utilisent `OU=Disabled Users,OU=EITAS,DC=API,DC=LOCAL`.

Les options `AutoCreateMissingGroups` et `AutoCreateMissingOUs` étaient actives lors du dernier audit.

Ces valeurs décrivent le serveur actuel et ne doivent pas être généralisées sans validation à un autre environnement.

## Déploiement Windows

Un changement Git ne doit jamais être copié aveuglément vers `C:\EnterpriseIT\agent-windows`.

Avant un déploiement Windows, il faut identifier les fichiers concernés, valider le parseur PowerShell 5.1, exécuter les tests ciblés, contrôler le SHA candidat, sauvegarder le fichier installé lorsque la procédure du lot le demande, copier uniquement le composant concerné, vérifier le SHA installé puis contrôler le worker et son heartbeat.

Un changement purement documentaire ne nécessite aucun déploiement Windows.

## Sécurité des secrets

Les clés API, tokens, mots de passe et secrets de service ne doivent jamais apparaître dans Git, la documentation ou les sorties de validation partagées.

Un audit peut confirmer la présence d un secret sans afficher sa valeur, par exemple avec le marqueur `<REDACTED_PRESENT>`.

## Audit lecture seule

Pour un contrôle du runtime Windows, privilégier `Get-ScheduledTask`, `Get-ScheduledTaskInfo`, `Get-CimInstance Win32_Process`, `Get-FileHash`, `Get-Content` et les requêtes GET strictement nécessaires.

Un audit de lecture seule ne doit pas démarrer, arrêter, recréer ou modifier une tâche planifiée.

## Documentation associée

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Déploiement](deployment.md)
- [Agent Windows](../architecture/windows-agent.md)
- [Architecture de sécurité](../architecture/security.md)
- [Corbeille Active Directory](../features/ad-recycle-bin.md)

## Règle de maintenance

Cette page doit être mise à jour après toute modification validée des tâches planifiées, runners, intervalles runtime, configuration locale, mécanismes de heartbeat ou autorisations spécialisées des workers Windows.
