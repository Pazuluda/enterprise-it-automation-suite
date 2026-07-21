import {
  type AccountEnvironment,
  getApplications,
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import style from "./EitasApplicationsPage.module.css";

type NamedItem = {
  id?: string;
  name?: string;
  displayText?: string;
  description?: string;
};

type ApplicationItem = {
  clientId?: string;
  clientName?: string;
  name?: string;
  description?: string;

  effectiveUrl?: string;
  baseUrl?: string;
  rootUrl?: string;

  inUse?: boolean;
  consentRequired?: boolean;

  realmRoles?: NamedItem[];
  clientScopes?: NamedItem[];
  additionalGrants?: NamedItem[];

  [key: string]: unknown;
};

const normalizeApplications = (
  value: unknown,
): ApplicationItem[] => {
  if (Array.isArray(value)) {
    return value as ApplicationItem[];
  }

  if (
    value &&
    typeof value === "object" &&
    "applications" in value
  ) {
    const applications = (
      value as {
        applications?: unknown;
      }
    ).applications;

    if (Array.isArray(applications)) {
      return applications as ApplicationItem[];
    }
  }

  return [];
};

const humanizeClientId = (
  clientId: string,
) => {
  if (clientId === "account-console") {
    return "Console de gestion du compte";
  }

  if (clientId === "account") {
    return "Gestion du compte";
  }

  const label = clientId
    .replace(/^client_/, "")
    .replace(/[-_]+/g, " ")
    .trim();

  if (!label) {
    return "Application";
  }

  return (
    label.charAt(0).toUpperCase()
    + label.slice(1)
  );
};

const resolveClientLabel = (
  label: string | undefined,
  clientId: string | undefined,
) => {
  const placeholder = label?.match(
    /^\$\{client_(.+)\}$/,
  );

  if (placeholder) {
    return humanizeClientId(
      placeholder[1],
    );
  }

  if (label?.trim()) {
    return label;
  }

  if (clientId?.trim()) {
    return humanizeClientId(clientId);
  }

  return "Application";
};

const getApplicationName = (
  application: ApplicationItem,
) =>
  resolveClientLabel(
    application.clientName
      || application.name,
    application.clientId,
  );

const getApplicationDescription = (
  application: ApplicationItem,
) =>
  application.description?.trim() ||
  (
    application.clientId === "account-console"
      ? "Console sécurisée de gestion du compte EITAS Identity."
      : "Application autorisée à utiliser votre identité."
  );

const getApplicationUrl = (
  application: ApplicationItem,
) =>
  application.effectiveUrl ||
  application.baseUrl ||
  application.rootUrl ||
  "";

const getApplicationType = (
  application: ApplicationItem,
) => {
  if (
    application.clientId === "account" ||
    application.clientId === "account-console"
  ) {
    return "Service d’identité";
  }

  return "Application";
};

const countItems = (
  value: unknown,
) =>
  Array.isArray(value)
    ? value.length
    : 0;

const ApplicationIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M4.75 3.5h5.5A1.25 1.25 0 0 1 11.5 4.75v5.5a1.25 1.25 0 0 1-1.25 1.25h-5.5A1.25 1.25 0 0 1 3.5 10.25v-5.5A1.25 1.25 0 0 1 4.75 3.5Zm9 0h5.5a1.25 1.25 0 0 1 1.25 1.25v5.5a1.25 1.25 0 0 1-1.25 1.25h-5.5a1.25 1.25 0 0 1-1.25-1.25v-5.5a1.25 1.25 0 0 1 1.25-1.25Zm-9 9h5.5a1.25 1.25 0 0 1 1.25 1.25v5.5a1.25 1.25 0 0 1-1.25 1.25h-5.5a1.25 1.25 0 0 1-1.25-1.25v-5.5a1.25 1.25 0 0 1 1.25-1.25Zm9 0h5.5a1.25 1.25 0 0 1 1.25 1.25v5.5a1.25 1.25 0 0 1-1.25 1.25h-5.5a1.25 1.25 0 0 1-1.25-1.25v-5.5a1.25 1.25 0 0 1 1.25-1.25Z"
      fill="currentColor"
    />
  </svg>
);

const ExternalLinkIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M14 4h6v6h-2V7.41l-7.3 7.3-1.4-1.42 7.29-7.29H14V4ZM5.5 6H11v2H6v10h10v-5h2v5.5A1.5 1.5 0 0 1 16.5 20h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6Z"
      fill="currentColor"
    />
  </svg>
);

export const EitasApplicationsPage = () => {
  const context =
    useEnvironment<AccountEnvironment>();

  const [applications, setApplications] =
    useState<ApplicationItem[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [refreshKey, setRefreshKey] =
    useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((current) => current + 1);
  }, []);

  useEffect(() => {
    const controller =
      new AbortController();

    setLoading(true);
    setError("");

    getApplications({
      signal: controller.signal,
      context,
    })
      .then((result: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setApplications(
          normalizeApplications(result),
        );

        setLoading(false);
      })
      .catch((caughtError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        console.error(
          "Chargement des applications impossible.",
          caughtError,
        );

        setError(
          "Les applications autorisées ne peuvent "
            + "pas être chargées actuellement.",
        );

        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [context, refreshKey]);

  const sortedApplications = useMemo(
    () =>
      [...applications].sort(
        (left, right) =>
          getApplicationName(left).localeCompare(
            getApplicationName(right),
            "fr",
            {
              sensitivity: "base",
            },
          ),
      ),
    [applications],
  );

  const usedApplications = useMemo(
    () =>
      sortedApplications.filter(
        (application) =>
          application.inUse === true,
      ).length,
    [sortedApplications],
  );

  return (
    <section className={style.page}>
      <header className={style.pageHeader}>
        <div>
          <span className={style.eyebrow}>
            Accès et autorisations
          </span>

          <h1>Applications</h1>

          <p>
            Consultez les applications autorisées
            à utiliser votre identité EITAS.
          </p>
        </div>

        <div className={style.summaryGroup}>
          <div className={style.summary}>
            <strong>
              {sortedApplications.length}
            </strong>

            <span>
              application
              {sortedApplications.length > 1
                ? "s"
                : ""}
            </span>
          </div>

          <div className={style.summary}>
            <strong>
              {usedApplications}
            </strong>

            <span>
              utilisée
              {usedApplications > 1
                ? "s"
                : ""}
            </span>
          </div>
        </div>
      </header>

      <section className={style.panel}>
        <div className={style.toolbar}>
          <div className={style.toolbarTitle}>
            <strong>
              Mes applications
            </strong>

            <span>
              Services ayant reçu un accès à
              votre compte.
            </span>
          </div>

          <button
            type="button"
            className={style.refreshButton}
            onClick={refresh}
            disabled={loading}
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                d="M19 7.5V3.8l-1.55 1.55A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.95-4.42L14 9.63h5V7.5Z"
                fill="currentColor"
              />
            </svg>

            Actualiser
          </button>
        </div>

        {loading && (
          <div className={style.state}>
            <span className={style.spinner} />

            <strong>
              Chargement des applications
            </strong>

            <span>
              Récupération des autorisations
              depuis EITAS Identity…
            </span>
          </div>
        )}

        {!loading && error && (
          <div
            className={[
              style.state,
              style.error,
            ].join(" ")}
          >
            <strong>
              Chargement impossible
            </strong>

            <span>{error}</span>

            <button
              type="button"
              onClick={refresh}
            >
              Réessayer
            </button>
          </div>
        )}

        {!loading &&
          !error &&
          sortedApplications.length === 0 && (
            <div className={style.state}>
              <span
                className={style.emptyIcon}
              >
                <ApplicationIcon />
              </span>

              <strong>
                Aucune application
              </strong>

              <span>
                Aucun service n’utilise
                actuellement votre identité.
              </span>
            </div>
          )}

        {!loading &&
          !error &&
          sortedApplications.length > 0 && (
            <div className={style.applicationList}>
              {sortedApplications.map(
                (application, index) => {
                  const name =
                    getApplicationName(
                      application,
                    );

                  const url =
                    getApplicationUrl(
                      application,
                    );

                  const roleCount =
                    countItems(
                      application.realmRoles,
                    );

                  const scopeCount =
                    countItems(
                      application.clientScopes,
                    );

                  const grantCount =
                    countItems(
                      application.additionalGrants,
                    );

                  const permissionCount =
                    roleCount +
                    scopeCount +
                    grantCount;

                  const key =
                    application.clientId ||
                    url ||
                    `${name}-${index}`;

                  return (
                    <article
                      className={
                        style.applicationCard
                      }
                      key={key}
                    >
                      <span
                        className={
                          style.applicationIcon
                        }
                      >
                        <ApplicationIcon />
                      </span>

                      <div
                        className={
                          style.applicationContent
                        }
                      >
                        <div
                          className={
                            style.applicationHeading
                          }
                        >
                          <div>
                            <strong>{name}</strong>

                            <span>
                              {getApplicationType(
                                application,
                              )}
                            </span>
                          </div>

                          <span
                            className={[
                              style.status,
                              application.inUse
                                ? style.used
                                : style.available,
                            ].join(" ")}
                          >
                            <i aria-hidden="true" />

                            {application.inUse
                              ? "Utilisée"
                              : "Disponible"}
                          </span>
                        </div>

                        <p>
                          {getApplicationDescription(
                            application,
                          )}
                        </p>

                        <div
                          className={
                            style.applicationMeta
                          }
                        >
                          <div>
                            <small>
                              Identifiant
                            </small>

                            <strong>
                              {application.clientId ||
                                "Non renseigné"}
                            </strong>
                          </div>

                          <div>
                            <small>
                              Autorisations
                            </small>

                            <strong>
                              {permissionCount}
                            </strong>
                          </div>

                          <div>
                            <small>
                              Consentement
                            </small>

                            <strong>
                              {application.consentRequired
                                ? "Requis"
                                : "Non requis"}
                            </strong>
                          </div>
                        </div>
                      </div>

                      {url && (
                        <a
                          className={style.openButton}
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Ouvrir

                          <ExternalLinkIcon />
                        </a>
                      )}
                    </article>
                  );
                },
              )}
            </div>
          )}
      </section>
    </section>
  );
};

export default EitasApplicationsPage;
