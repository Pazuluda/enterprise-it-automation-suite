# Agents Windows EITAS

Ce document décrit l’architecture actuelle de la couche Windows de **Enterprise IT Automation Suite (EITAS)**.

Il complète [l’architecture générale](overview.md), [l’architecture de sécurité](security.md) et [l’architecture backend](backend-api.md).

## Rôle de la couche Windows

Les agents Windows constituent la frontière d’exécution entre l’API EITAS sur Debian et Microsoft Active Directory.

Ils prennent en charge les opérations nécessitant :

- Windows Server ;
- PowerShell ;
- les cmdlets Active Directory ;
- l’accès au domaine ;
- des contrôles d’exécution spécifiques à l’environnement Windows.

Le backend prépare et autorise les opérations ; le worker Windows exécute uniquement les traitements correspondant à son contrat.

## Entry points

Les entrypoints PowerShell actuellement présents à la racine de `agent-windows/` sont :

- `Invoke-EmployeeLifecycleAgent.ps1` ;
- `Run-AdAdminWorker.ps1` ;
- `Run-AdCheckWorker.ps1` ;
- `Run-AdLookupWorker.ps1` ;
- `Run-EitasAgent.ps1`.

Ces scripts ne doivent pas être considérés comme interchangeables : chaque worker possède un rôle ou un périmètre d’exécution propre.

## Modules partagés

Les modules actuellement présents sous `agent-windows/modules/` sont :

- `EitasActiveDirectory.ps1` ;
- `EitasAdAdmin.ps1` ;
- `EitasAdLookup.ps1` ;
- `EitasAdSnapshot.ps1` ;
- `EitasApi.ps1` ;
- `EitasConfig.ps1` ;
- `EitasLogging.ps1`.

### Responsabilités générales

`EitasConfig.ps1` centralise notamment l’accès à la configuration worker.

`EitasApi.ps1` porte les primitives de communication avec l’API.

`EitasActiveDirectory.ps1` contient des fonctions communes liées à Active Directory et aux préflights.

`EitasAdAdmin.ps1` porte une part importante des opérations administratives Active Directory et de leurs barrières Simulation / Production.

`EitasAdLookup.ps1` et `EitasAdSnapshot.ps1` servent les capacités de lecture, lookup et snapshot.

`EitasLogging.ps1` fournit les primitives communes de journalisation côté worker.

## Authentification worker

Les workers s’authentifient actuellement auprès de l’API avec `X-API-Key`.

La configuration d’exemple contient une propriété `ApiKey`, et les modules de configuration/API récupèrent cette valeur pour construire l’en-tête technique correspondant.

Cette identité technique est distincte de l’identité humaine OIDC utilisée par le portail.

Un worker ne doit pas recevoir ni réutiliser le jeton Bearer d’un utilisateur comme substitut à son authentification technique.

### Évolution future

Aucune authentification mTLS généralisée par worker n’a été identifiée dans le périmètre audité.

La documentation de référence conserve donc `X-API-Key` comme mécanisme worker actuellement déployé.

## Modes Simulation et Production

La couche Windows connaît explicitement les modes `Simulation` et `Production`.

La configuration d’exemple utilise `Simulation`, et plusieurs handlers vérifient directement le mode avant de préparer ou d’exécuter une opération.

### Simulation

La Simulation permet, selon la fonctionnalité :

- de valider les entrées ;
- de résoudre les objets Active Directory ;
- de calculer un résultat attendu ;
- de construire une prévisualisation ;
- de vérifier les préconditions ;
- de retourner un résultat sans appliquer la mutation correspondante.

Certaines fonctions sont volontairement limitées à la Simulation tant que leur chemin Production n’a pas été autorisé ou implémenté.

### Production

Les chemins Production sont distincts des chemins Simulation.

Le passage au mode `Production` ne doit jamais être interprété comme une autorisation universelle permettant toutes les écritures Active Directory.

Une fonctionnalité sensible peut imposer ses propres conditions supplémentaires :

- préflight spécifique ;
- indicateur d’autorisation ;
- ticket ;
- enveloppe verrouillée ;
- liaison à une identité ou à une cible ;
- contrôle de fraîcheur ;
- consommation unique ;
- validation du contexte d’exécution.

## Opérations administratives Active Directory

`EitasAdAdmin.ps1` contient actuellement de nombreuses opérations avec séparation Simulation / Production, notamment autour de :

- création d’OU ;
- création de conteneurs ;
- création de contacts ;
- création de groupes ;
- création d’utilisateurs ;
- création d’ordinateurs ;
- appartenances de groupes ;
- propriétés des objets ;
- suppression ;
- renommage ;
- déplacement ;
- activation et désactivation de comptes ;
- déverrouillage ;
- réinitialisation de mot de passe ;
- attributs LDAP ;
- ACL et délégation ;
- Corbeille Active Directory ;
- restauration d’objets supprimés.

Toutes ces capacités ne partagent pas nécessairement le même niveau d’autorisation Production.

La documentation fonctionnelle de chaque domaine reste la référence pour ses conditions exactes d’écriture réelle.

## Cycle de vie des collaborateurs

`Invoke-EmployeeLifecycleAgent.ps1` contient des chemins distincts pour :

- onboarding ;
- offboarding ;
- modification ;
- Simulation ;
- Production.

Le script possède également un préflight Production et des mécanismes liés aux tâches planifiées Windows.

La présence de ces mécanismes ne signifie pas que tous les autres workers utilisent exactement la même stratégie de scheduling ou de Production.

## Tâches planifiées

Le code audité contient des interactions avec les tâches planifiées Windows, notamment via `Get-ScheduledTask`, `Get-ScheduledTaskInfo`, `New-ScheduledTaskTrigger` et `Set-ScheduledTask`.

Les workers peuvent donc être exploités via des tâches Windows dédiées selon leur rôle.

La configuration opérationnelle exacte des tâches installées doit être documentée dans la future documentation d’exploitation plutôt que déduite uniquement du code source.

## Flux général

Le flux worker typique peut être résumé ainsi :

1. charger la configuration locale ;
2. récupérer l’identité technique worker ;
3. interroger l’API pour le travail autorisé ;
4. valider le mode et le contrat du job ;
5. exécuter la Simulation ou le traitement Windows autorisé ;
6. produire un résultat structuré ;
7. renvoyer le résultat à l’API ;
8. journaliser l’exécution.

Les opérations fortement sensibles peuvent ajouter plusieurs étapes d’autorisation avant l’étape 5.

## Barrières spécialisées C8 et C9

Les travaux récents sur les ACL/délégations et la Corbeille Active Directory ont introduit des chaînes d’autorisation plus spécialisées que le simple couple `Simulation` / `Production`.

Le backend possède notamment des services dédiés aux enveloppes d’identité, tickets, confirmations, préexécutions et consommations uniques.

La couche Windows possède également des fonctions spécialisées de préparation ou d’exécution pour ces chemins.

Il est donc incorrect de documenter ces opérations comme de simples commandes rendues possibles par le seul mode global Production.

## Séparation des responsabilités

### Debian / API

Responsable notamment de :

- l’identité humaine ;
- le RBAC ;
- les workflows ;
- les autorisations applicatives ;
- les tickets et enveloppes lorsqu’ils existent ;
- la persistance runtime ;
- l’audit applicatif ;
- la préparation des jobs.

### Windows worker

Responsable notamment de :

- la validation du contrat Windows ;
- l’utilisation des cmdlets Windows/AD ;
- les préflights locaux ;
- l’exécution du handler autorisé ;
- la vérification locale des garde-fous ;
- le retour du résultat.

### Active Directory

Active Directory reste la cible finale des lectures et mutations réellement autorisées.

## Configuration et secrets

Le dépôt contient `agent-windows/config.example.json` uniquement comme exemple.

Les valeurs réelles d’authentification ne doivent pas être commitées dans Git.

La clé API worker ne doit pas être exposée au frontend ni intégrée dans un bundle navigateur.

## Compatibilité

La couche worker est conçue autour de PowerShell Windows et des modules Active Directory disponibles sur le serveur d’exécution.

Les changements apportés aux modules doivent rester compatibles avec l’environnement Windows Server réellement utilisé et être validés avec le parser/runtime PowerShell correspondant avant déploiement.

## Maintenance

Toute évolution importante de la couche Windows doit mettre à jour ce document après validation réelle, notamment en cas de :

- nouvel entrypoint ;
- nouveau module ;
- changement du mécanisme d’authentification worker ;
- modification du modèle Simulation / Production ;
- nouveau type d’enveloppe d’exécution ;
- changement du scheduling ;
- modification de la frontière Active Directory.
