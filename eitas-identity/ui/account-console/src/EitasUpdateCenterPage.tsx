import {
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import {
  useCallback,
  useEffect,
  useState,
} from "react";
import { Navigate } from "react-router-dom";
import { environment } from "./environment";
import style from "./EitasUpdateCenterPage.module.css";

type UpdateArtifact = {
  version: string;
  sha256: string;
};

type UpdateStage = {
  id: string;
  label: string;
  state: string;
};

type IdentityUpdateStatus = {
  schema_version: 1;
  status: string;
  environment: string;
  mode: string;
  generated_at: string;
  engine: {
    name: string;
    version: string;
    upstream_tag: string;
    upstream_commit: string;
  };
  interfaces: {
    account: UpdateArtifact;
    admin: UpdateArtifact;
    login: UpdateArtifact;
  };
  source: {
    locked: boolean;
    verification: string;
    patch_policy: string;
  };
  stages: UpdateStage[];
  production: {
    automatic_updates: boolean;
    locked: boolean;
  };
};

type SourceCheckResponse = {
  request_id: string;
  action: "verify_upstream";
  status: "queued";
  requested_at: string;
};

const basePath = decodeURIComponent(
  new URL(environment.baseUrl).pathname,
).replace(/\/+$/, "");

const overviewUrl = `${basePath}/overview`;

const updateStatusUrl =
  "/api/identity-update/status";

const sourceCheckUrl =
  "/api/identity-update/source-check";

const getAdminUrl = () => {
  const serverBaseUrl =
    environment.serverBaseUrl.replace(/\/+$/, "");

  return `${serverBaseUrl}/admin/master/console/`;
};

const stateLabels: Record<string, string> = {
  available: "Disponible",
  current: "Actuel",
  locked: "Verrouillé",
  pending: "Prévu",
  passed: "Validé",
  failed: "Échec",
};

const environmentLabels: Record<string, string> = {
  preproduction: "Préproduction",
  laboratory: "Laboratoire",
  production: "Production",
};

const verificationLabels: Record<string, string> = {
  not_run: "Non exécutée",
  running: "En cours",
  passed: "Validée",
  failed: "Échec",
};

const defaultStages: UpdateStage[] = [
  {
    id: "source",
    label: "Vérifier la source upstream",
    state: "available",
  },
  {
    id: "compatibility",
    label: "Analyser la compatibilité",
    state: "locked",
  },
  {
    id: "laboratory",
    label: "Tester en laboratoire",
    state: "locked",
  },
  {
    id: "preproduction",
    label: "Valider en préproduction",
    state: "current",
  },
  {
    id: "production",
    label: "Autoriser la production",
    state: "locked",
  },
];

const delay = (milliseconds: number) =>
  new Promise<void>((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });

const formatGeneratedAt = (
  value: string | undefined,
) => {
  if (!value) {
    return "État non chargé";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(parsed);
};

const compactHash = (
  value: string | undefined,
) => {
  if (!value) {
    return "SHA-256 en attente";
  }

  if (value.length <= 20) {
    return value;
  }

  return `${value.slice(0, 12)}…${value.slice(-8)}`;
};

const responseError = async (
  response: Response,
) => {
  if (response.status === 401) {
    return (
      "La session EITAS Identity n’est plus valide. " +
      "Reconnectez-vous puis réessayez."
    );
  }

  if (response.status === 403) {
    return (
      "Le rôle UltraAdmin est requis pour consulter " +
      "le Centre de mise à jour."
    );
  }

  try {
    const body = await response.json() as {
      detail?: unknown;
    };

    if (
      typeof body.detail === "string" &&
      body.detail.trim()
    ) {
      return body.detail;
    }
  } catch {
    // La réponse n’était pas un JSON exploitable.
  }

  return (
    "Le moteur d’état est momentanément indisponible " +
    `(HTTP ${response.status}).`
  );
};

const UpdateStep = ({
  number,
  stage,
}: {
  number: string;
  stage: UpdateStage;
}) => {
  const displayedState =
    stage.id === "source" &&
    stage.state === "current"
      ? "En cours"
      : stateLabels[stage.state] ?? stage.state;

  return (
    <article className={style.step}>
      <span className={style.stepNumber}>
        {number}
      </span>

      <div>
        <strong>{stage.label}</strong>

        <p>
          {stage.id === "source" &&
            "Contrôle du dépôt, du tag, du commit et des patches cœur EITAS approuvés."}

          {stage.id === "compatibility" &&
            "Comparaison des extensions, thèmes, migrations et paramètres actifs."}

          {stage.id === "laboratory" &&
            "Construction reproductible et validation dans une instance isolée."}

          {stage.id === "preproduction" &&
            "Sauvegarde, déploiement contrôlé, santé et capacité de rollback."}

          {stage.id === "production" &&
            "Validation humaine explicite après lecture du rapport complet."}
        </p>
      </div>

      <span
        className={style.stepState}
        data-state={stage.state}
      >
        {displayedState}
      </span>
    </article>
  );
};

export const EitasUpdateCenterPage = () => {
  const { keycloak } = useEnvironment();

  const isAdmin =
    keycloak.hasRealmRole("admin") ||
    keycloak.hasRealmRole("UltraAdmin");

  const [status, setStatus] =
    useState<IdentityUpdateStatus | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [sourceChecking, setSourceChecking] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [sourceMessage, setSourceMessage] =
    useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    await keycloak.updateToken(30);

    const token = keycloak.token;

    if (!token) {
      throw new Error(
        "Aucun jeton EITAS Identity actif.",
      );
    }

    const response = await fetch(
      updateStatusUrl,
      {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error(
        await responseError(response),
      );
    }

    const payload =
      await response.json() as IdentityUpdateStatus;

    if (
      payload.schema_version !== 1 ||
      !payload.engine ||
      !payload.interfaces ||
      !Array.isArray(payload.stages)
    ) {
      throw new Error(
        "Le moteur a retourné un état incompatible.",
      );
    }

    return payload;
  }, [keycloak]);

  const loadStatus = useCallback(async () => {
    if (!isAdmin) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = await fetchStatus();
      setStatus(payload);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Impossible de charger l’état.",
      );
    } finally {
      setLoading(false);
    }
  }, [fetchStatus, isAdmin]);

  const runSourceCheck = useCallback(async () => {
    if (!isAdmin || sourceChecking) {
      return;
    }

    setSourceChecking(true);
    setError(null);
    setSourceMessage(
      "Enregistrement de la demande de vérification…",
    );

    try {
      await keycloak.updateToken(30);

      const token = keycloak.token;

      if (!token) {
        throw new Error(
          "Aucun jeton EITAS Identity actif.",
        );
      }

      const response = await fetch(
        sourceCheckUrl,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (response.status === 409) {
        setSourceMessage(
          "Une vérification upstream est déjà en cours.",
        );

        await loadStatus();
        return;
      }

      if (!response.ok) {
        throw new Error(
          await responseError(response),
        );
      }

      const request =
        await response.json() as SourceCheckResponse;

      if (
        request.status !== "queued" ||
        request.action !== "verify_upstream" ||
        !request.requested_at
      ) {
        throw new Error(
          "La réponse de mise en file est incompatible.",
        );
      }

      const requestedAt =
        Date.parse(request.requested_at);

      setSourceMessage(
        "Vérification upstream en cours…",
      );

      for (let attempt = 0; attempt < 90; attempt += 1) {
        await delay(1000);

        const payload = await fetchStatus();
        setStatus(payload);

        const generatedAt =
          Date.parse(payload.generated_at);

        const freshResult =
          Number.isFinite(requestedAt) &&
          Number.isFinite(generatedAt) &&
          generatedAt >= requestedAt;

        if (
          freshResult &&
          payload.source.verification === "passed"
        ) {
          setSourceMessage(
            "Source upstream vérifiée avec succès.",
          );
          return;
        }

        if (
          freshResult &&
          payload.source.verification === "failed"
        ) {
          throw new Error(
            "La vérification de la source upstream a échoué.",
          );
        }
      }

      throw new Error(
        "La vérification n’a pas terminé dans le délai prévu.",
      );
    } catch (caughtError) {
      setSourceMessage(null);

      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Impossible de vérifier la source.",
      );
    } finally {
      setSourceChecking(false);
    }
  }, [
    fetchStatus,
    isAdmin,
    keycloak,
    loadStatus,
    sourceChecking,
  ]);

  useEffect(() => {
    if (isAdmin) {
      void loadStatus();
    }
  }, [isAdmin, loadStatus]);

  if (!isAdmin) {
    return (
      <Navigate
        to={overviewUrl}
        replace
      />
    );
  }

  const stages =
    status?.stages.length
      ? status.stages
      : defaultStages;

  const environmentLabel =
    environmentLabels[
      status?.environment ?? ""
    ] ??
    status?.environment ??
    "Préproduction";

  const verificationLabel =
    verificationLabels[
      status?.source.verification ?? ""
    ] ??
    status?.source.verification ??
    "Non chargée";

  return (
    <section className={style.page}>
      <header className={style.pageHeader}>
        <div>
          <span className={style.eyebrow}>
            Administration EITAS Identity
          </span>

          <h1>Centre de mise à jour</h1>

          <p>
            Contrôlez l’intégrité de la source et
            consultez l’état réel des composants sans
            autoriser d’installation automatique.
          </p>
        </div>

        <span className={style.securityBadge}>
          Mode contrôlé
        </span>
      </header>

      {error && (
        <section
          className={style.error}
          role="alert"
        >
          <strong>Opération impossible</strong>
          <p>{error}</p>
        </section>
      )}

      {sourceMessage && (
        <section
          className={style.notice}
          aria-live="polite"
        >
          <strong>Vérification upstream</strong>
          <p>{sourceMessage}</p>
        </section>
      )}

      <section className={style.summaryGrid}>
        <article className={style.summary}>
          <span>Moteur d’identité</span>

          <strong>
            {status
              ? `${status.engine.name} ${status.engine.version}`
              : "Chargement…"}
          </strong>

          <small>
            Tag upstream{" "}
            {status?.engine.upstream_tag ?? "—"}
          </small>
        </article>

        <article className={style.summary}>
          <span>Console Compte</span>

          <strong>
            {status?.interfaces.account.version ??
              "Chargement…"}
          </strong>

          <small
            className={style.hash}
            title={
              status?.interfaces.account.sha256
            }
          >
            {compactHash(
              status?.interfaces.account.sha256,
            )}
          </small>
        </article>

        <article className={style.summary}>
          <span>Console Admin</span>

          <strong>
            {status?.interfaces.admin.version ??
              "Chargement…"}
          </strong>

          <small
            className={style.hash}
            title={
              status?.interfaces.admin.sha256
            }
          >
            {compactHash(
              status?.interfaces.admin.sha256,
            )}
          </small>
        </article>

        <article className={style.summary}>
          <span>Environnement</span>

          <strong>{environmentLabel}</strong>

          <small>
            Production{" "}
            {status?.production.locked === false
              ? "déverrouillée"
              : "verrouillée"}
          </small>
        </article>
      </section>

      <section className={style.statusPanel}>
        <div>
          <span className={style.eyebrow}>
            État du moteur
          </span>

          <strong>
            {status?.status === "ready"
              ? "Service prêt"
              : "En attente de lecture"}
          </strong>
        </div>

        <div>
          <span>Source</span>

          <strong>
            {status?.source.locked
              ? "Verrouillée"
              : "Non verrouillée"}
          </strong>
        </div>

        <div>
          <span>Vérification</span>
          <strong>{verificationLabel}</strong>
        </div>

        <div>
          <span>Dernière génération</span>

          <strong>
            {formatGeneratedAt(
              status?.generated_at,
            )}
          </strong>
        </div>
      </section>

      <section className={style.panel}>
        <div className={style.panelHeader}>
          <div>
            <span className={style.eyebrow}>
              Processus contrôlé
            </span>

            <h2>Parcours de mise à jour</h2>
          </div>

          <span className={style.readOnly}>
            Aucun déploiement disponible
          </span>
        </div>

        <div className={style.steps}>
          {stages.map((stage, index) => (
            <UpdateStep
              key={stage.id}
              number={String(index + 1).padStart(
                2,
                "0",
              )}
              stage={stage}
            />
          ))}
        </div>
      </section>

      <section className={style.warning}>
        <strong>
          La production reste verrouillée.
        </strong>

        <p>
          Le contrôle upstream exécute seulement le
          vérificateur approuvé. Il ne télécharge,
          n’installe et ne déploie aucune version.
        </p>
      </section>

      <div className={style.actions}>
        <a
          href={getAdminUrl()}
          className={style.primaryAction}
        >
          Ouvrir la console d’administration
        </a>

        <button
          type="button"
          onClick={() => {
            void runSourceCheck();
          }}
          disabled={
            sourceChecking ||
            loading
          }
          className={style.sourceAction}
        >
          {sourceChecking
            ? "Vérification en cours…"
            : "Vérifier la source upstream"}
        </button>

        <button
          type="button"
          onClick={() => {
            void loadStatus();
          }}
          disabled={
            loading ||
            sourceChecking
          }
          className={style.refreshAction}
        >
          {loading
            ? "Actualisation…"
            : "Actualiser l’état"}
        </button>
      </div>
    </section>
  );
};
