import {
  type AccountEnvironment,
  getCredentials,
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import style from "./EitasAuthenticationPage.module.css";

type CredentialContainers = Awaited<
  ReturnType<typeof getCredentials>
>;

type CredentialContainer =
  CredentialContainers[number];

type CredentialMetadata =
  CredentialContainer[
    "userCredentialMetadatas"
  ][number];

type CredentialRecord =
  CredentialMetadata["credential"] & {
    createdDate?: number;
    userLabel?: string;
  };

type DeleteTarget = {
  container: CredentialContainer;
  metadata: CredentialMetadata;
} | null;

type Category =
  | "basic-authentication"
  | "two-factor"
  | "passwordless";

const CATEGORY_ORDER: Category[] = [
  "basic-authentication",
  "two-factor",
  "passwordless",
];

const CATEGORY_LABELS: Record<
  Category,
  {
    eyebrow: string;
    title: string;
    description: string;
  }
> = {
  "basic-authentication": {
    eyebrow: "Authentification principale",
    title: "Méthodes de connexion",
    description:
      "Méthodes utilisées pour vous connecter avec vos identifiants principaux.",
  },
  "two-factor": {
    eyebrow: "Protection renforcée",
    title: "Double authentification",
    description:
      "Ajoutez un second facteur afin de renforcer la protection de votre compte.",
  },
  passwordless: {
    eyebrow: "Connexion moderne",
    title: "Connexion sans mot de passe",
    description:
      "Utilisez une passkey, Windows Hello ou une clé de sécurité compatible.",
  },
};

const METHOD_LABELS: Record<
  string,
  string
> = {
  [["pass", "word"].join("")]: "Mot de passe",
  otp: "Application d’authentification",
  "recovery-authn-codes":
    "Codes de récupération",
  webauthn: "Clé de sécurité",
  "webauthn-passwordless":
    "Passkey et Windows Hello",
};

const METHOD_DESCRIPTIONS: Record<
  string,
  string
> = {
  password:
    "Mot de passe principal utilisé pour accéder à votre compte.",
  otp:
    "Codes temporaires générés par une application d’authentification.",
  "recovery-authn-codes":
    "Codes de secours utilisables lorsque votre second facteur est indisponible.",
  webauthn:
    "Clé physique ou authentificateur sécurisé compatible WebAuthn.",
  "webauthn-passwordless":
    "Connexion avec Windows Hello, une passkey ou une clé de sécurité.",
};

const ShieldIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M12 2.5 20 5.7v5.55c0 4.9-3.25 8.77-8 10.25-4.75-1.48-8-5.35-8-10.25V5.7L12 2.5Zm0 2.15L6 7.05v4.2c0 3.75 2.32 6.72 6 8.05 3.68-1.33 6-4.3 6-8.05v-4.2l-6-2.4Zm-.95 4.1h1.9v4.05h-1.9V8.75Zm0 5.4h1.9v1.9h-1.9v-1.9Z"
      fill="currentColor"
    />
  </svg>
);

const PasswordIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M7.5 10V7.5a4.5 4.5 0 1 1 9 0V10h1.25A2.25 2.25 0 0 1 20 12.25v7A2.25 2.25 0 0 1 17.75 21H6.25A2.25 2.25 0 0 1 4 18.75v-7A2.25 2.25 0 0 1 6.25 10H7.5Zm2 0h5V7.5a2.5 2.5 0 0 0-5 0V10Zm2.5 3.25a1.75 1.75 0 0 0-1 3.18V18h2v-1.57a1.75 1.75 0 0 0-1-3.18Z"
      fill="currentColor"
    />
  </svg>
);

const OtpIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M7.25 2.75h9.5A2.25 2.25 0 0 1 19 5v14a2.25 2.25 0 0 1-2.25 2.25h-9.5A2.25 2.25 0 0 1 5 19V5a2.25 2.25 0 0 1 2.25-2.25ZM7 5v12.5h10V5H7Zm3.75 14h2.5v.75h-2.5V19ZM9 8h2v2H9V8Zm4 0h2v2h-2V8Zm-4 4h2v2H9v-2Zm4 0h2v2h-2v-2Z"
      fill="currentColor"
    />
  </svg>
);

const PasskeyIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M8.75 3.5a5.25 5.25 0 1 1-3.2 9.41L2.75 15.7v2.55H5.3v2.5h2.5v-2.5h2.45l3.66-3.66A5.25 5.25 0 0 1 8.75 3.5Zm0 2A3.25 3.25 0 1 0 12 8.75 3.25 3.25 0 0 0 8.75 5.5Zm0 1.75a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Z"
      fill="currentColor"
    />
  </svg>
);

const RecoveryIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M6 3.5h12A2.5 2.5 0 0 1 20.5 6v12a2.5 2.5 0 0 1-2.5 2.5H6A2.5 2.5 0 0 1 3.5 18V6A2.5 2.5 0 0 1 6 3.5Zm0 2A.5.5 0 0 0 5.5 6v12c0 .28.22.5.5.5h12a.5.5 0 0 0 .5-.5V6a.5.5 0 0 0-.5-.5H6Zm2 3h8v2H8v-2Zm0 4h5v2H8v-2Z"
      fill="currentColor"
    />
  </svg>
);

const RefreshIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M19 7.5V3.8l-1.55 1.55A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.95-4.42L14 9.63h5V7.5Z"
      fill="currentColor"
    />
  </svg>
);

const TrashIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M8.5 3.5h7l1 2H20v2H4v-2h3.5l1-2Zm-2 5.5h11l-.75 11.5h-9.5L6.5 9Zm3 2v7h2v-7h-2Zm3.5 0v7h2v-7h-2Z"
      fill="currentColor"
    />
  </svg>
);

const getMethodIcon = (
  type: string,
) => {
  if (type === "password") {
    return <PasswordIcon />;
  }

  if (
    type === "otp" ||
    type.includes("totp")
  ) {
    return <OtpIcon />;
  }

  if (
    type.includes("recovery")
  ) {
    return <RecoveryIcon />;
  }

  if (
    type.includes("webauthn") ||
    type.includes("passkey")
  ) {
    return <PasskeyIcon />;
  }

  return <ShieldIcon />;
};

const humanize = (
  value: string,
) => {
  const text = value
    .replace(
      /^\$\{|\}$/g,
      "",
    )
    .replace(
      /-display-name$/i,
      "",
    )
    .replace(
      /[-_]+/g,
      " ",
    )
    .trim();

  if (!text) {
    return "Méthode d’authentification";
  }

  return (
    text.charAt(0).toUpperCase()
    + text.slice(1)
  );
};

const getMethodLabel = (
  container: CredentialContainer,
) =>
  METHOD_LABELS[container.type]
  || humanize(
    container.displayName
    || container.type,
  );

const getMethodDescription = (
  container: CredentialContainer,
) =>
  METHOD_DESCRIPTIONS[container.type]
  || (
    container.category === "two-factor"
      ? "Méthode de double authentification associée à votre compte."
      : container.category === "passwordless"
        ? "Méthode de connexion sécurisée sans mot de passe."
        : "Méthode principale utilisée pour accéder à votre compte."
  );

const getCredentialMetadata = (
  container: CredentialContainer,
): CredentialMetadata[] =>
  Array.isArray(
    container.userCredentialMetadatas,
  )
    ? container.userCredentialMetadatas
    : [];

const getCredentialRecord = (
  metadata: CredentialMetadata,
): CredentialRecord =>
  metadata.credential as CredentialRecord;

const getCredentialLabel = (
  container: CredentialContainer,
  metadata: CredentialMetadata,
  index: number,
) => {
  const credential =
    getCredentialRecord(metadata);

  if (credential.userLabel?.trim()) {
    return credential.userLabel;
  }

  if (container.type === "password") {
    return "Mot de passe principal";
  }

  const label =
    getMethodLabel(container);

  return `${label} ${index + 1}`;
};

const formatCreatedDate = (
  metadata: CredentialMetadata,
  locale: string,
) => {
  const credential =
    getCredentialRecord(metadata);

  const timestamp = Number(
    credential.createdDate,
  );

  if (
    !timestamp ||
    Number.isNaN(timestamp)
  ) {
    return "Date non renseignée";
  }

  const milliseconds =
    timestamp > 100000000000
      ? timestamp
      : timestamp * 1000;

  const date =
    new Date(milliseconds);

  if (
    Number.isNaN(date.getTime())
  ) {
    return "Date non renseignée";
  }

  return new Intl.DateTimeFormat(
    locale || "fr-FR",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
};

export const EitasAuthenticationPage =
  () => {
    const context =
      useEnvironment<AccountEnvironment>();

    const [containers, setContainers] =
      useState<CredentialContainers>([]);

    const [loading, setLoading] =
      useState(true);

    const [error, setError] =
      useState("");

    const [busyAction, setBusyAction] =
      useState("");

    const [refreshKey, setRefreshKey] =
      useState(0);

    const [
      deleteTarget,
      setDeleteTarget,
    ] = useState<DeleteTarget>(null);

    const refresh = useCallback(() => {
      setRefreshKey(
        (current) => current + 1,
      );
    }, []);

    useEffect(() => {
      const controller =
        new AbortController();

      setLoading(true);
      setError("");

      getCredentials({
        signal: controller.signal,
        context,
      })
        .then(
          (
            result:
              CredentialContainers,
          ) => {
            if (
              controller.signal.aborted
            ) {
              return;
            }

            setContainers(
              Array.isArray(result)
                ? result
                : [],
            );

            setLoading(false);
          },
        )
        .catch(
          (caughtError: unknown) => {
            if (
              controller.signal.aborted
            ) {
              return;
            }

            console.error(
              "Chargement des méthodes impossible.",
              caughtError,
            );

            setError(
              "Les méthodes d’authentification "
                + "ne peuvent pas être chargées.",
            );

            setLoading(false);
          },
        );

      return () => {
        controller.abort();
      };
    }, [context, refreshKey]);

    const configuredCount = useMemo(
      () =>
        containers.reduce(
          (total, container) =>
            total
            + getCredentialMetadata(
              container,
            ).length,
          0,
        ),
      [containers],
    );

    const twoFactorCount = useMemo(
      () =>
        containers
          .filter(
            (container) =>
              container.category
              === "two-factor",
          )
          .reduce(
            (total, container) =>
              total
              + getCredentialMetadata(
                container,
              ).length,
            0,
          ),
      [containers],
    );

    const passwordlessCount = useMemo(
      () =>
        containers
          .filter(
            (container) =>
              container.category
              === "passwordless",
          )
          .reduce(
            (total, container) =>
              total
              + getCredentialMetadata(
                container,
              ).length,
            0,
          ),
      [containers],
    );

    const categorySections = useMemo(
      () =>
        CATEGORY_ORDER.map(
          (category) => ({
            category,
            containers:
              containers.filter(
                (container) =>
                  container.category
                  === category,
              ),
          }),
        ).filter(
          (section) =>
            section.containers.length > 0,
        ),
      [containers],
    );

    const startAction =
      async (
        action: string,
      ) => {
        setBusyAction(action);
        setError("");

        try {
          await context.keycloak.login({
            action,
          });
        } catch (caughtError) {
          console.error(
            "Action d’authentification impossible.",
            caughtError,
          );

          setError(
            "L’action sécurisée n’a pas pu être démarrée.",
          );

          setBusyAction("");
        }
      };

    const confirmDelete =
      async () => {
        if (!deleteTarget) {
          return;
        }

        const credential =
          getCredentialRecord(
            deleteTarget.metadata,
          );

        if (!credential.id) {
          setDeleteTarget(null);
          setError(
            "Identifiant de la méthode absent.",
          );

          return;
        }

        const action =
          `delete_credential:${credential.id}`;

        setDeleteTarget(null);

        await startAction(action);
      };

    return (
      <section className={style.page}>
        <header
          className={style.pageHeader}
        >
          <div>
            <span
              className={style.eyebrow}
            >
              Sécurité du compte
            </span>

            <h1>Authentification</h1>

            <p>
              Gérez vos mots de passe,
              facteurs supplémentaires,
              passkeys et clés de sécurité.
            </p>
          </div>

          <div
            className={style.summaryGroup}
          >
            <div className={style.summary}>
              <strong>
                {configuredCount}
              </strong>

              <span>
                méthode
                {configuredCount > 1
                  ? "s"
                  : ""}
              </span>
            </div>

            <div className={style.summary}>
              <strong>
                {twoFactorCount}
              </strong>

              <span>
                facteur
                {twoFactorCount > 1
                  ? "s"
                  : ""}
                {" "}
                MFA
              </span>
            </div>

            <div className={style.summary}>
              <strong>
                {passwordlessCount}
              </strong>

              <span>
                méthode
                {passwordlessCount > 1
                  ? "s"
                  : ""}
                {" "}
                sans mot de passe
              </span>
            </div>
          </div>
        </header>

        <section className={style.panel}>
          <div className={style.toolbar}>
            <div
              className={style.toolbarTitle}
            >
              <strong>
                Mes méthodes de connexion
              </strong>

              <span>
                Configuration sécurisée gérée
                par EITAS Identity.
              </span>
            </div>

            <button
              type="button"
              className={style.refreshButton}
              onClick={refresh}
              disabled={
                loading
                || Boolean(busyAction)
              }
            >
              <RefreshIcon />
              Actualiser
            </button>
          </div>

          {error && (
            <div className={style.alert}>
              <span aria-hidden="true" />
              {error}
            </div>
          )}

          {loading && (
            <div className={style.state}>
              <span
                className={style.spinner}
              />

              <strong>
                Chargement des méthodes
              </strong>

              <span>
                Analyse de la configuration
                d’authentification…
              </span>
            </div>
          )}

          {!loading &&
            categorySections.length === 0 && (
              <div className={style.state}>
                <span
                  className={style.emptyIcon}
                >
                  <ShieldIcon />
                </span>

                <strong>
                  Aucune méthode disponible
                </strong>

                <span>
                  Le realm ne propose
                  actuellement aucune méthode
                  modifiable.
                </span>
              </div>
            )}

          {!loading &&
            categorySections.length > 0 && (
              <div
                className={style.categoryList}
              >
                {categorySections.map(
                  (section) => {
                    const categoryInfo =
                      CATEGORY_LABELS[
                        section.category
                      ];

                    return (
                      <section
                        className={
                          style.categorySection
                        }
                        key={
                          section.category
                        }
                      >
                        <header
                          className={
                            style.categoryHeader
                          }
                        >
                          <span>
                            {
                              categoryInfo.eyebrow
                            }
                          </span>

                          <h2>
                            {
                              categoryInfo.title
                            }
                          </h2>

                          <p>
                            {
                              categoryInfo.description
                            }
                          </p>
                        </header>

                        <div
                          className={
                            style.methodList
                          }
                        >
                          {section.containers.map(
                            (container) => {
                              const metadata =
                                getCredentialMetadata(
                                  container,
                                );

                              const configured =
                                metadata.length > 0;

                              return (
                                <article
                                  className={
                                    style.methodCard
                                  }
                                  key={
                                    container.type
                                  }
                                >
                                  <div
                                    className={
                                      style.methodHeading
                                    }
                                  >
                                    <span
                                      className={
                                        style.methodIcon
                                      }
                                    >
                                      {getMethodIcon(
                                        container.type,
                                      )}
                                    </span>

                                    <div
                                      className={
                                        style.methodIdentity
                                      }
                                    >
                                      <strong>
                                        {getMethodLabel(
                                          container,
                                        )}
                                      </strong>

                                      <span>
                                        {getMethodDescription(
                                          container,
                                        )}
                                      </span>
                                    </div>

                                    <span
                                      className={[
                                        style.status,
                                        configured
                                          ? style.configured
                                          : style.unconfigured,
                                      ].join(" ")}
                                    >
                                      <i
                                        aria-hidden="true"
                                      />

                                      {configured
                                        ? "Configuré"
                                        : "Non configuré"}
                                    </span>

                                    {container.createAction && (
                                      <button
                                        type="button"
                                        className={
                                          style.primaryButton
                                        }
                                        onClick={() =>
                                          void startAction(
                                            container.createAction!,
                                          )
                                        }
                                        disabled={
                                          Boolean(
                                            busyAction,
                                          )
                                        }
                                      >
                                        {busyAction
                                          === container.createAction
                                          ? "Ouverture…"
                                          : configured
                                            ? "Ajouter"
                                            : "Configurer"}
                                      </button>
                                    )}
                                  </div>

                                  {metadata.length === 0 ? (
                                    <div
                                      className={
                                        style.noCredential
                                      }
                                    >
                                      Cette méthode
                                      n’est pas encore
                                      associée à votre
                                      compte.
                                    </div>
                                  ) : (
                                    <div
                                      className={
                                        style.credentialList
                                      }
                                    >
                                      {metadata.map(
                                        (
                                          item,
                                          index,
                                        ) => {
                                          const credential =
                                            getCredentialRecord(
                                              item,
                                            );

                                          return (
                                            <div
                                              className={
                                                style.credentialRow
                                              }
                                              key={
                                                credential.id
                                                || `${container.type}-${index}`
                                              }
                                            >
                                              <div
                                                className={
                                                  style.credentialIdentity
                                                }
                                              >
                                                <strong>
                                                  {getCredentialLabel(
                                                    container,
                                                    item,
                                                    index,
                                                  )}
                                                </strong>

                                                <span>
                                                  Ajouté le{" "}
                                                  {formatCreatedDate(
                                                    item,
                                                    context.environment.locale,
                                                  )}
                                                </span>
                                              </div>

                                              <div
                                                className={
                                                  style.credentialActions
                                                }
                                              >
                                                {container.updateAction && (
                                                  <button
                                                    type="button"
                                                    className={
                                                      style.secondaryButton
                                                    }
                                                    onClick={() =>
                                                      void startAction(
                                                        container.updateAction!,
                                                      )
                                                    }
                                                    disabled={
                                                      Boolean(
                                                        busyAction,
                                                      )
                                                    }
                                                  >
                                                    Mettre à jour
                                                  </button>
                                                )}

                                                {container.removeable &&
                                                  credential.id && (
                                                    <button
                                                      type="button"
                                                      className={
                                                        style.deleteButton
                                                      }
                                                      onClick={() =>
                                                        setDeleteTarget(
                                                          {
                                                            container,
                                                            metadata:
                                                              item,
                                                          },
                                                        )
                                                      }
                                                      disabled={
                                                        Boolean(
                                                          busyAction,
                                                        )
                                                      }
                                                    >
                                                      <TrashIcon />
                                                      Supprimer
                                                    </button>
                                                  )}
                                              </div>
                                            </div>
                                          );
                                        },
                                      )}
                                    </div>
                                  )}
                                </article>
                              );
                            },
                          )}
                        </div>
                      </section>
                    );
                  },
                )}
              </div>
            )}
        </section>

        {deleteTarget && (
          <div
            className={style.modalBackdrop}
            role="presentation"
            onMouseDown={(event) => {
              if (
                event.target
                === event.currentTarget
              ) {
                setDeleteTarget(null);
              }
            }}
          >
            <section
              className={style.modal}
              role="dialog"
              aria-modal="true"
              aria-labelledby="eitas-delete-credential-title"
            >
              <span
                className={style.modalIcon}
              >
                <TrashIcon />
              </span>

              <h2
                id="eitas-delete-credential-title"
              >
                Supprimer cette méthode ?
              </h2>

              <p>
                La méthode sélectionnée ne
                pourra plus être utilisée pour
                accéder à votre compte.
              </p>

              <div
                className={style.modalActions}
              >
                <button
                  type="button"
                  className={style.cancelButton}
                  onClick={() =>
                    setDeleteTarget(null)
                  }
                >
                  Annuler
                </button>

                <button
                  type="button"
                  className={style.confirmButton}
                  onClick={() =>
                    void confirmDelete()
                  }
                >
                  Continuer
                </button>
              </div>
            </section>
          </div>
        )}
      </section>
    );
  };

export default EitasAuthenticationPage;
