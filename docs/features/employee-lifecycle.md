# Cycle de vie des collaborateurs

Ce document décrit le workflow Employee Lifecycle actuellement implémenté dans EITAS.

Il couvre la création de collaborateurs, leur départ et les modifications d’un compte utilisateur via le portail, l’API et l’agent Windows dédié.

## Périmètre actuel

Le workflow possède actuellement trois types de demandes :

- `onboarding` : création d’un collaborateur ;
- `offboarding` : départ d’un collaborateur ;
- `modification` : modification d’un utilisateur existant.

Il n’existe actuellement **aucun quatrième type de demande `reactivation` autonome**.

La réactivation éventuelle d’un compte appartient au traitement de modification et comporte plusieurs limites décrites plus bas.

## Architecture du workflow

Le cycle général est :

1. un opérateur prépare une demande dans le portail ;
2. le backend valide et persiste la demande ;
3. la demande commence en `waiting_approval` ;
4. une approbation la passe en `pending` ;
5. l’agent Windows récupère uniquement les demandes `pending` ;
6. l’agent claim la demande et la passe en `processing` ;
7. il exécute le chemin Simulation ou Production ;
8. il renvoie un résultat ;
9. le backend termine en `completed` ou `failed`.

Le portail humain et le worker Windows ont donc des responsabilités distinctes.

## États des demandes

Une demande nouvellement créée utilise :

- `waiting_approval`.

Après approbation :

- `pending`.

Lorsqu’un worker réclame la demande :

- `processing`.

Après retour du worker :

- `completed` lorsque `success = true` ;
- `failed` lorsque `success = false`.

Un rejet utilise :

- `rejected`.

## Approbation

L’endpoint d’approbation n’accepte qu’une demande actuellement en `waiting_approval`.

L’approbation :

- définit `approved = true` ;
- enregistre `approved_by` ;
- enregistre `approved_at` ;
- conserve le commentaire éventuel ;
- passe directement la demande à `pending`.

Une demande approuvée devient donc disponible pour l’agent Windows.

## Rejet

Le rejet est actuellement accepté depuis :

- `waiting_approval` ;
- `pending`.

Il passe la demande en `rejected` et enregistre l’acteur et le commentaire fournis au workflow.

Une demande déjà en `processing`, `completed`, `failed` ou `rejected` ne suit pas ce chemin de rejet.

## Retry

Le backend possède un endpoint de retry qui remet directement une demande existante en :

- `pending`.

Il :

- enregistre `retried_at` ;
- efface `completed_at` ;
- efface `agent_result`.

Le backend de cette route ne réintroduit pas une étape `waiting_approval`.

Le frontend limite les actions de retry qu’il propose, mais la documentation ne doit pas transformer cette convention UI en une contrainte backend inexistante.

## Claim par le worker

L’agent ne récupère que les demandes `pending`.

Lors du claim, le backend exige encore que le statut soit exactement `pending`, puis stocke :

- `processing_at` ;
- `processing_by`.

Cette transition évite qu’une même demande déjà prise en charge soit simplement réclamée comme une nouvelle demande pending.

## Résultat agent

Le worker retourne :

- `success` ;
- `message` ;
- `details`.

Le backend conserve le résultat complet dans `agent_result` et écrit `completed_at`.

La demande passe ensuite à `completed` ou `failed`.

## Modes Simulation et Production

L’agent Employee Lifecycle synchronise son mode avec :

- `/api/agent/mode`.

Les modes reconnus sont :

- `Simulation` ;
- `Production`.

Le mode par défaut du script reste `Simulation`.

Lorsque le mode est `Production`, le worker exécute également son preflight Production avant de traiter les demandes.

Chaque type de demande possède un handler Simulation et un handler Production distinct.

## Simulation

En Simulation, les handlers :

- décrivent l’opération prévue ;
- retournent un résultat marqué `simulated = true` ;
- n’exécutent pas les primitives d’écriture Active Directory correspondantes.

La Simulation permet ainsi de faire passer une demande complète dans le workflow sans créer, désactiver ou modifier réellement un compte AD.

## Onboarding

### Modèle de demande

Une demande onboarding contient obligatoirement :

- `first_name` ;
- `last_name` ;
- `department` ;
- `job_title` ;
- `start_date`.

Elle peut aussi contenir :

- `manager` ;
- `manual_groups`.

`manual_groups` vaut une liste vide par défaut.

## Templates onboarding

Le backend onboarding utilise réellement les templates EITAS.

Le département demandé doit exister dans `templates.json`.

Le poste demandé doit également exister dans les rôles de ce département.

Un template département définit notamment :

- `default_ou` ;
- `default_groups`.

Un template de poste définit :

- ses groupes supplémentaires.

## Fusion des groupes

Pour l’onboarding, le backend fusionne :

1. les groupes par défaut du département ;
2. les groupes du poste ;
3. `manual_groups`.

Les doublons sont supprimés et la liste finale est triée.

Les groupes manuels sont donc de vrais overrides/additions au template et non un simple champ décoratif.

## Identité générée

Le backend génère notamment :

- le `username` ;
- l’adresse e-mail ;
- le `display_name`.

La demande persistée contient ensuite un `ad_payload` destiné au worker Windows.

## Onboarding Production

En Production, le worker :

- vérifie que l’OU cible est dans le périmètre EITAS ;
- vérifie que l’OU existe ;
- refuse un login AD déjà existant ;
- génère un mot de passe temporaire ;
- crée le compte avec `New-ADUser` ;
- active le compte ;
- impose le changement du mot de passe à la première connexion ;
- renseigne notamment nom, prénom, UPN, e-mail, département et poste ;
- ajoute le compte aux groupes calculés.

## Mot de passe temporaire

Le mot de passe initial est généré localement sur le worker Windows.

Il est affiché localement au moment de la création et le résultat indique explicitement :

- `password_generated = true` ;
- `password_stored_in_api = false`.

Le mot de passe temporaire ne doit donc pas être présenté comme stocké ou récupérable depuis l’API EITAS.

## Offboarding

### Modèle de demande

Une demande offboarding exige notamment :

- `username` ;
- `display_name` ;
- `end_date`.

Elle peut transporter :

- département ;
- manager ;
- désactivation du compte ;
- retrait des groupes ;
- OU de destination ;
- demande de conversion mailbox ;
- adresse de forwarding ;
- commentaire.

Les valeurs par défaut du modèle activent actuellement :

- `disable_account = true` ;
- `remove_groups = true` ;
- `convert_mailbox = false`.

## Offboarding Production

Le worker Production :

- résout le compte AD ;
- vérifie que son DN reste dans le périmètre EITAS ;
- détermine une OU d’offboarding contrôlée ;
- peut retirer ses appartenances aux groupes EITAS / `GG_*` ;
- peut désactiver le compte ;
- écrit une description d’offboarding ;
- déplace le compte vers l’OU prévue si nécessaire.

Le worker refuse une OU de destination hors périmètre EITAS.

## Exchange et messagerie

Les options suivantes existent actuellement dans le modèle et dans l’interface :

- `convert_mailbox` ;
- `forward_to`.

Elles ne constituent cependant pas une intégration Exchange opérationnelle.

Même dans le handler Production, le worker indique que la conversion mailbox n’est pas exécutée sans Exchange et que la redirection reste une demande non appliquée.

Le résultat conserve explicitement :

- `mailbox_handled = false`.

Aucune primitive `Set-Mailbox`, `Set-RemoteMailbox` ou `Set-MailUser` n’a été identifiée dans ce worker.

## Modification

### Modèle de demande

Une demande modification exige :

- `username` ;
- `display_name` ;
- `effective_date`.

Elle peut transporter :

- département actuel ;
- poste actuel ;
- nouveau département ;
- nouveau poste ;
- manager ;
- groupes à ajouter ;
- groupes à retirer ;
- OU de destination ;
- commentaire.

Les listes `add_groups` et `remove_groups` sont vides par défaut.

## Modification Production

Le worker peut actuellement :

- mettre à jour le département ;
- mettre à jour le poste ;
- mettre à jour l’e-mail et l’UPN lorsqu’un champ compatible est présent dans le payload ;
- ajouter des groupes ;
- retirer des groupes ;
- déplacer l’utilisateur vers une OU autorisée ;
- réactiver un compte dans certaines conditions.

Les modifications d’attributs utilisent `Set-ADUser`.

Les groupes utilisent `Add-ADGroupMember` et `Remove-ADGroupMember`.

Les déplacements utilisent `Move-ADObject`.

## Réactivation : état actuel

La réactivation n’est pas un type de demande autonome.

Le worker de modification sait techniquement lire un indicateur comme :

- `reactivate_account` ;
- `enable_account`.

Il peut ensuite appeler `Enable-ADAccount`.

Cependant, le chemin portail/API actuel présente une incohérence importante.

Le frontend possède et transmet actuellement `reactivate_account`, mais :

- `ModificationRequest` ne définit pas ce champ ;
- `create_modification_request()` ne le copie pas dans `modification_payload` ;
- le `ad_payload` standard construit par ce service ne garantit donc pas la présence de cette demande explicite.

La case de réactivation du frontend ne doit par conséquent **pas être présentée comme un chemin end-to-end garanti dans l’état actuel**.

## Réactivation automatique

Indépendamment de cette incohérence, le worker possède une logique de réactivation automatique.

Lorsqu’un utilisateur est désactivé et que la cible calculée n’est pas considérée comme l’OU `Disabled Users`, le worker peut forcer la réactivation et exécuter :

- `Enable-ADAccount` ;
- une mise à jour de la description indiquant la réactivation EITAS.

Cette logique est une capacité réelle du worker et doit être distinguée de la case frontend actuellement mal liée au backend.

## Manager : état actuel

Le champ `manager` existe dans :

- `OnboardingRequest` ;
- `OffboardingRequest` ;
- `ModificationRequest`.

Le backend le transporte également dans plusieurs payloads Employee Lifecycle.

En revanche, le worker Employee Lifecycle audité ne l’utilise actuellement pas dans ses primitives Active Directory.

La documentation ne doit donc pas présenter ce workflow comme appliquant actuellement le manager AD.

La gestion de l’attribut manager disponible dans d’autres fonctions de l’Explorateur AD est un chemin distinct.

## Dates métier

Les modèles contiennent notamment :

- `start_date` pour l’onboarding ;
- `end_date` pour l’offboarding ;
- `effective_date` pour la modification.

Ces valeurs sont actuellement conservées comme données métier de la demande.

Le worker audité traite les demandes dès qu’elles deviennent `pending` et ne contient pas dans ces handlers de scheduler différant automatiquement l’exécution jusqu’à ces dates.

Ces champs ne doivent donc pas être présentés comme un moteur de planification automatique.

## Import CSV onboarding

Le portail possède un workflow d’import CSV pour créer plusieurs onboarding.

L’import permet notamment de préparer :

- prénom ;
- nom ;
- département ;
- poste ;
- manager ;
- date de début ;
- groupes.

Les demandes importées rejoignent ensuite le workflow normal de demandes et d’approbation.

L’import CSV ne contourne donc pas la mécanique principale Employee Lifecycle.

## Administration des templates

Le portail permet d’administrer :

- les départements ;
- leur OU par défaut ;
- leurs groupes par défaut ;
- les postes ;
- les groupes associés aux postes.

Le service backend permet la création, modification et suppression de ces templates.

Les modifications de templates produisent également des événements d’audit.

## Audit

Les événements principaux couvrent notamment :

- création de demande ;
- approbation ;
- rejet ;
- retry ;
- claim par le worker ;
- succès ou échec du traitement ;
- administration des templates.

Le workflow historique Employee Lifecycle ne doit toutefois pas être confondu avec les chaînes d’autorisation plus récentes de C8/C9.

Par exemple, certains champs d’acteur tels que `approved_by` sont fournis dans le payload d’approbation après contrôle RBAC de la route ; ils ne constituent pas le même mécanisme de binding cryptographique d’identité que les enveloppes spécialisées C8/C9.

## Séparation avec les workers spécialisés

`Invoke-EmployeeLifecycleAgent.ps1` ne lance plus les workers spécialisés AD Explorer, AD Admin ou AD Check.

Ces fonctionnalités utilisent leurs propres entrypoints.

Le worker Employee Lifecycle reste consacré aux demandes :

- onboarding ;
- offboarding ;
- modification.

## Sécurité Production

Avant une exécution Production, le worker applique son preflight AD.

Les opérations utilisant une OU vérifient également le périmètre avec `Test-EitasDnSafe`.

Le mode Production global est donc pertinent pour ce workflow historique, contrairement à certaines capacités spécialisées plus récentes qui possèdent leurs propres gates indépendants.

## Limites actuelles à ne pas masquer

La documentation doit conserver les limites suivantes tant qu’elles ne sont pas corrigées et revalidées :

- aucun type `reactivation` autonome ;
- binding `reactivate_account` frontend → backend incomplet ;
- champ `manager` transporté mais non appliqué par ce worker ;
- aucune intégration Exchange effective pour conversion ou forwarding ;
- les dates métier ne déclenchent pas de planification différée ;
- le champ de résultat `account_reactivated` de l’offboarding ne doit pas être utilisé comme preuve fonctionnelle de réactivation.

## Maintenance

Ce document doit être mis à jour après validation réelle si changent :

- les types de demandes ;
- le workflow de statuts ;
- les règles d’approbation ou de retry ;
- les templates ;
- les primitives Production ;
- le traitement du manager ;
- le binding de réactivation ;
- l’intégration Exchange ;
- le scheduler métier ;
- ou le worker Employee Lifecycle.
