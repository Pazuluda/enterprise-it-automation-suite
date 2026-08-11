# Sauvegarde et reprise

Ce document décrit les limites, données critiques et principes de reprise actuellement validés pour EITAS.

## État actuel

EITAS ne dispose pas, à ce stade, d’un mécanisme général de sauvegarde et de reprise après sinistre validé de bout en bout.

Les écritures atomiques utilisées par certains composants réduisent le risque de fichiers partiellement écrits, mais elles ne constituent ni une sauvegarde, ni une réplication, ni un plan de reprise après sinistre.

Toute procédure de sauvegarde doit donc être considérée comme une responsabilité d’exploitation distincte jusqu’à validation explicite d’un mécanisme EITAS dédié.

## Données runtime

Le répertoire de données runtime actuellement validé sur Debian est `/var/lib/eitas`.

Il est séparé du dépôt source `/opt/enterprise-it-automation-suite`.

Cette séparation doit être préservée : restaurer le code source ne restaure pas automatiquement les données runtime, et restaurer les données runtime ne remplace pas une version cohérente du code.

## Configuration sensible

La configuration du service API est notamment fournie par `/etc/eitas-api.env`.

Ce fichier peut contenir des secrets ou paramètres sensibles et ne doit jamais être copié dans Git ni exposé dans les journaux de validation.

Une sauvegarde de configuration doit conserver des permissions restrictives et être protégée indépendamment du dépôt source.

## Périmètre de données à protéger

Le périmètre runtime principal actuellement observé est `/var/lib/eitas`.

Il contient notamment les données fonctionnelles et historiques EITAS : `templates.json`, `requests.json`, `audit.jsonl`, `worker-events.jsonl`, `worker-status.json`, `agent-status.json`, `ad-admin-jobs.json`, `ad-check-jobs.json`, `ad-lookup-jobs.json` et `ad-explorer-jobs.json`.

Il contient également les caches et vues runtime `ad-snapshot.json` et `ad-domain-catalog.json`, ainsi que `agent-config.json`.

Les mécanismes de sécurité avancés utilisent aussi des registres persistants dans `/var/lib/eitas`, notamment pour la délégation ACL et la restauration contrôlée des objets supprimés. Ces fichiers incluent des états d’autorisation, de consommation, de ticket, de replay et de transport.

Le sous-ensemble `identity-update` possède également son propre état runtime, ses requêtes, rapports et fichiers de statut.

Pour une stratégie de sauvegarde cohérente, `/var/lib/eitas` doit donc être traité comme un ensemble de données runtime, plutôt que de sélectionner arbitrairement quelques fichiers isolés.

## Permissions et propriétaires

Les fichiers runtime n’utilisent pas tous les mêmes permissions ou propriétaires. L’audit a observé notamment des fichiers `600`, `640` et des répertoires `700`, `750` ou `775`, appartenant selon les cas à `eitas:eitas`, `root:eitas` ou `root:root`.

Une restauration ne doit donc pas seulement remettre les octets : elle doit aussi préserver ou rétablir les propriétaires et permissions attendus.

Le fichier `/etc/eitas-api.env` est actuellement en mode `600` et appartient à `root:root`. Son contenu sensible doit rester séparé des sauvegardes de code source et protégé en conséquence.

## Sauvegardes ponctuelles existantes

Le runtime contient plusieurs répertoires historiques tels que `backups`, `deploy-backups` et `static-backups`, créés lors de validations ou déploiements précédents.

Ces copies ponctuelles sont utiles pour certaines opérations de rollback local, mais leur présence ne démontre pas un système général de sauvegarde, une politique de rétention, une réplication hors machine ou un plan de reprise après sinistre validé.

Les répertoires de validation présents dans `/var/lib/eitas/validation` ont également une fonction de preuve ou de contrôle et ne doivent pas être assimilés à un PRA.

## Principes de reprise

Aucune procédure automatisée de reprise après sinistre n’est actuellement validée de bout en bout pour EITAS.

Une reprise manuelle doit traiter séparément le code applicatif, les données runtime et la configuration sensible, puis vérifier leur cohérence avant de remettre les workers en fonctionnement normal.

Le dépôt Git constitue la source de vérité pour le code versionné. Il ne remplace pas `/var/lib/eitas` ni `/etc/eitas-api.env`.

À l’inverse, une copie de `/var/lib/eitas` ne garantit pas à elle seule que le code déployé correspond à la version attendue.

Une reprise doit donc identifier explicitement la version Git cible, restaurer les données compatibles avec cette version, rétablir la configuration nécessaire et conserver le mode global `Simulation` tant que les contrôles ne sont pas terminés.

La restauration de fichiers de sécurité persistants, notamment les registres de tickets, autorisations, consommations et replay, doit être effectuée avec prudence afin de ne pas réintroduire un état ancien considéré à tort comme encore valide.

## Validation après reprise

Avant de considérer une reprise comme réussie, il faut au minimum vérifier la version Git déployée, les propriétaires et permissions des données runtime, la présence de la configuration requise, le démarrage du service API et la disponibilité du portail.

Il faut ensuite confirmer le mode `Simulation`, contrôler les workers Windows et leurs heartbeats, puis effectuer des validations fonctionnelles en lecture seule avant toute réouverture éventuelle d’un chemin d’écriture.

Les fichiers de jobs, événements et audit doivent être contrôlés pour vérifier qu’ils sont lisibles et cohérents avec la reprise effectuée.

Une restauration ne doit jamais être déclarée réussie uniquement parce que le service démarre.

## Limites actuellement non couvertes

Aucun objectif RPO ou RTO formel n’est actuellement défini ou validé dans EITAS.

Aucune réplication hors machine, rotation de sauvegardes, politique de rétention, chiffrement de sauvegarde, restauration automatique complète ou test périodique de PRA ne doit être présenté comme existant tant que ces capacités n’ont pas été implémentées et validées.

La Corbeille Active Directory et le mécanisme C9.5 de restauration contrôlée concernent la restauration d’objets AD supprimés. Ils ne constituent pas un système de sauvegarde général d’EITAS.

## Documentation associée

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Déploiement](deployment.md)
- [Workers Windows](windows-workers.md)
- [Architecture de sécurité](../architecture/security.md)
- [Corbeille Active Directory](../features/ad-recycle-bin.md)

## Règle de maintenance

Cette page doit être mise à jour lorsqu’un mécanisme réel de sauvegarde, une politique de rétention, un objectif RPO/RTO ou une procédure de reprise validée est introduit dans EITAS.
