import {
  type AccountEnvironment,
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import style from "./EitasOrganizationsPage.module.css";

type DomainLike =
  | string
  | {
      name?: string;
      verified?: boolean;
    };

type Organization = {
  id?: string;
  name?: string;
  alias?: string;
  description?: string;
  domains?: DomainLike[];
  membershipType?: string;
};

type OrganizationList = Organization[];

type AccountContext = {
  environment: AccountEnvironment;
  keycloak: {
    token?: string;
    updateToken: (
      minValidity: number,
    ) => Promise<boolean>;
    login: () => Promise<void>;
  };
};

/*
 * Keycloak 26.7.0 possède cette fonction en interne,
 * mais ne l’exporte pas dans l’API publique du paquet.
 * On appelle donc le même endpoint Account officiel.
 */
const fetchUserOrganizations = async ({
  signal,
  context,
}: {
  signal?: AbortSignal;
  context: AccountContext;
}): Promise<OrganizationList> => {
  try {
    await context.keycloak.updateToken(5);
  } catch {
    await context.keycloak.login();

    throw new Error(
      "La session EITAS Identity doit être renouvelée.",
    );
  }

  const token = context.keycloak.token;

  if (!token) {
    throw new Error(
      "Jeton EITAS Identity absent.",
    );
  }

  const serverBaseUrl =
    context.environment.serverBaseUrl.replace(
      /\/+$/,
      "",
    );

  const realm = encodeURIComponent(
    context.environment.realm,
  );

  const response = await fetch(
    `${serverBaseUrl}/realms/${realm}/account/organizations`,
    {
      signal,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      `Endpoint Organisations : HTTP ${response.status}`,
    );
  }

  const result: unknown =
    await response.json();

  if (!Array.isArray(result)) {
    throw new Error(
      "Réponse Organisations invalide.",
    );
  }

  return result as OrganizationList;
};

const OrganizationIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M5 3.5h9.5A1.5 1.5 0 0 1 16 5v4h2.5A1.5 1.5 0 0 1 20 10.5V21h-6v-4h-4v4H4V4.5A1 1 0 0 1 5 3.5Zm2 3v2h2v-2H7Zm4 0v2h2v-2h-2Zm-4 4v2h2v-2H7Zm4 0v2h2v-2h-2Zm6 1.5v2h1v-2h-1Zm0 4v2h1v-2h-1Z"
      fill="currentColor"
    />
  </svg>
);

const DomainIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M12 2.75a9.25 9.25 0 1 0 0 18.5 9.25 9.25 0 0 0 0-18.5Zm5.9 5.5h-2.72a14.5 14.5 0 0 0-1.15-3.02 7.29 7.29 0 0 1 3.87 3.02ZM12 4.7c.76.88 1.48 2.08 1.88 3.55h-3.76C10.52 6.78 11.24 5.58 12 4.7ZM4.7 12c0-.62.08-1.22.23-1.8h3.6a15.9 15.9 0 0 0 0 3.6h-3.6A7.3 7.3 0 0 1 4.7 12Zm1.4 3.75h2.72c.25 1.1.64 2.12 1.15 3.02a7.29 7.29 0 0 1-3.87-3.02Zm2.72-7.5H6.1a7.29 7.29 0 0 1 3.87-3.02 14.5 14.5 0 0 0-1.15 3.02ZM12 19.3c-.76-.88-1.48-2.08-1.88-3.55h3.76c-.4 1.47-1.12 2.67-1.88 3.55Zm2.23-5.5H9.77a13.62 13.62 0 0 1 0-3.6h4.46a13.62 13.62 0 0 1 0 3.6Zm-.2 4.97c.51-.9.9-1.92 1.15-3.02h2.72a7.29 7.29 0 0 1-3.87 3.02Zm1.44-4.97a15.9 15.9 0 0 0 0-3.6h3.6a7.38 7.38 0 0 1 0 3.6h-3.6Z"
      fill="currentColor"
    />
  </svg>
);

const getName = (
  organization: Organization,
) =>
  organization.name ||
  organization.alias ||
  "Organisation";

const getAlias = (
  organization: Organization,
) =>
  organization.alias || "";

const getDescription = (
  organization: Organization,
) =>
  organization.description?.trim() ||
  "Aucune description n’a été renseignée.";

const getDomains = (
  organization: Organization,
): string[] => {
  const domains = organization.domains;

  if (!Array.isArray(domains)) {
    return [];
  }

  return domains
    .map((domain: DomainLike) => {
      if (typeof domain === "string") {
        return domain;
      }

      return domain?.name || "";
    })
    .filter(
      (domain): domain is string =>
        Boolean(domain),
    );
};

const getMembershipLabel = (
  organization: Organization,
) => {
  const representation =
    organization as Organization & {
      membershipType?: string;
    };

  const membership =
    representation.membershipType
      ?.trim()
      .toLowerCase();

  if (membership === "managed") {
    return "Adhésion gérée";
  }

  if (membership === "invited") {
    return "Utilisateur invité";
  }

  return "Membre";
};

export const EitasOrganizationsPage = () => {
  const context =
    useEnvironment<AccountEnvironment>();

  const [organizations, setOrganizations] =
    useState<OrganizationList>([]);

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

    fetchUserOrganizations({
      signal: controller.signal,
      context,
    })
      .then((result: OrganizationList) => {
        if (controller.signal.aborted) {
          return;
        }

        setOrganizations(
          Array.isArray(result)
            ? result
            : [],
        );

        setLoading(false);
      })
      .catch((caughtError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        console.error(
          "Chargement des organisations impossible.",
          caughtError,
        );

        setError(
          "Les organisations associées à votre "
            + "compte ne peuvent pas être chargées.",
        );

        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [context, refreshKey]);

  const sortedOrganizations = useMemo(
    () =>
      [...organizations].sort(
        (left, right) =>
          getName(left).localeCompare(
            getName(right),
            "fr",
            {
              sensitivity: "base",
            },
          ),
      ),
    [organizations],
  );

  const domainCount = useMemo(
    () =>
      new Set(
        sortedOrganizations.flatMap(
          getDomains,
        ),
      ).size,
    [sortedOrganizations],
  );

  return (
    <section className={style.page}>
      <header className={style.pageHeader}>
        <div>
          <span className={style.eyebrow}>
            Identité et accès
          </span>

          <h1>Organisations</h1>

          <p>
            Consultez les organisations auxquelles
            votre identité est rattachée.
          </p>
        </div>

        <div className={style.summaryGroup}>
          <div className={style.summary}>
            <strong>
              {sortedOrganizations.length}
            </strong>

            <span>
              organisation
              {sortedOrganizations.length > 1
                ? "s"
                : ""}
            </span>
          </div>

          <div className={style.summary}>
            <strong>{domainCount}</strong>

            <span>
              domaine
              {domainCount > 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </header>

      <section className={style.panel}>
        <div className={style.toolbar}>
          <div className={style.toolbarTitle}>
            <strong>
              Mes organisations
            </strong>

            <span>
              Appartenances disponibles pour
              votre compte EITAS.
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
              Chargement des organisations
            </strong>

            <span>
              Récupération des appartenances
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
          sortedOrganizations.length === 0 && (
            <div className={style.state}>
              <span
                className={style.emptyIcon}
              >
                <OrganizationIcon />
              </span>

              <strong>
                Aucune organisation
              </strong>

              <span>
                Votre compte n’est actuellement
                rattaché à aucune organisation.
              </span>
            </div>
          )}

        {!loading &&
          !error &&
          sortedOrganizations.length > 0 && (
            <div className={style.organizationList}>
              {sortedOrganizations.map(
                (organization, index) => {
                  const name =
                    getName(organization);

                  const alias =
                    getAlias(organization);

                  const domains =
                    getDomains(organization);

                  const key =
                    organization.id ||
                    alias ||
                    `${name}-${index}`;

                  return (
                    <article
                      className={
                        style.organizationCard
                      }
                      key={key}
                    >
                      <span
                        className={
                          style.organizationIcon
                        }
                      >
                        <OrganizationIcon />
                      </span>

                      <div
                        className={
                          style.organizationContent
                        }
                      >
                        <div
                          className={
                            style.organizationHeading
                          }
                        >
                          <div>
                            <strong>{name}</strong>

                            {alias && (
                              <span>
                                Identifiant : {alias}
                              </span>
                            )}
                          </div>

                          <span
                            className={
                              style.membership
                            }
                          >
                            <i aria-hidden="true" />

                            {getMembershipLabel(
                              organization,
                            )}
                          </span>
                        </div>

                        <p>
                          {getDescription(
                            organization,
                          )}
                        </p>

                        <div
                          className={
                            style.organizationMeta
                          }
                        >
                          <div>
                            <span
                              className={
                                style.metaIcon
                              }
                            >
                              <DomainIcon />
                            </span>

                            <div>
                              <small>
                                Domaines
                              </small>

                              {domains.length > 0 ? (
                                <div
                                  className={
                                    style.domainList
                                  }
                                >
                                  {domains.map(
                                    (domain) => (
                                      <span
                                        key={domain}
                                      >
                                        {domain}
                                      </span>
                                    ),
                                  )}
                                </div>
                              ) : (
                                <strong>
                                  Aucun domaine
                                </strong>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
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

export default EitasOrganizationsPage;
