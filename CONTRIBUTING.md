# Contribuer à EITAS

## Principes

Toute contribution doit respecter le chantier actif, la sécurité, la confidentialité, la compatibilité et la traçabilité.

## Avant de modifier le code

1. sélectionner une issue ;
2. confirmer le chantier et la version cible ;
3. documenter le besoin ;
4. identifier les composants concernés ;
5. préparer les validations et le retour arrière.

## Avant un commit

```bash
./scripts/pre-commit-security-check.sh
git diff --check
git status --short
```

## Secrets interdits

Ne jamais committer de mots de passe, clés API, jetons, clés privées, certificats privés, fichiers `.env` de production, cookies, données client, exports Active Directory sensibles ou sauvegardes runtime.

## Style des commits

```text
feat(scope): description
fix(scope): description
docs(scope): description
test(scope): description
refactor(scope): description
security(scope): description
```

## Validation

Selon le changement : tests Python, tests Node, build frontend, vérification PowerShell, appels API, contrôle Active Directory et validation visuelle dans Microsoft Edge.

## Versionnement

Voir [`docs/policies/versioning.md`](docs/policies/versioning.md).
