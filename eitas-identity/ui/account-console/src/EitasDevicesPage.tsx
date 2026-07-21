import {
  type AccountEnvironment,
  type DeviceRepresentation,
  type SessionRepresentation,
  deleteSession,
  getDevices,
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import style from "./EitasDevicesPage.module.css";

type Confirmation =
  | {
      type: "session";
      device: DeviceRepresentation;
      session: SessionRepresentation;
    }
  | {
      type: "all";
    }
  | null;

type ClientItem = {
  clientId?: string;
  clientName?: string;
};

const DeviceIcon = ({
  mobile,
}: {
  mobile: boolean;
}) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    {mobile ? (
      <path
        d="M8 2.75h8A1.75 1.75 0 0 1 17.75 4.5v15A1.75 1.75 0 0 1 16 21.25H8a1.75 1.75 0 0 1-1.75-1.75v-15A1.75 1.75 0 0 1 8 2.75Zm0 2V17.5h8V4.75H8Zm3 14.25h2v.75h-2V19Z"
        fill="currentColor"
      />
    ) : (
      <path
        d="M4.5 3.75h15A1.75 1.75 0 0 1 21.25 5.5v10A1.75 1.75 0 0 1 19.5 17.25h-6.25v2h3v1.5h-8.5v-1.5h3v-2H4.5a1.75 1.75 0 0 1-1.75-1.75v-10A1.75 1.75 0 0 1 4.5 3.75Zm-.25 2v10h15.5v-10H4.25Z"
        fill="currentColor"
      />
    )}
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

const LogoutIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M4.5 3.5h8A1.5 1.5 0 0 1 14 5v3h-2V5.5H5v13h7V16h2v3a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 3 19V5a1.5 1.5 0 0 1 1.5-1.5Zm12.8 5.2 4.3 3.3-4.3 3.3-1.2-1.6 1.9-1.45H9v-2h9L16.1 8.3l1.2-1.6Z"
      fill="currentColor"
    />
  </svg>
);

const isUnknown = (
  value: string | undefined,
) =>
  !value ||
  value.toLowerCase().includes(
    "unknown",
  );

const getDeviceName = (
  device: DeviceRepresentation,
) => {
  const os = isUnknown(device.os)
    ? "Appareil inconnu"
    : device.os;

  const version =
    isUnknown(device.osVersion)
      ? ""
      : ` ${device.osVersion}`;

  return `${os}${version}`.trim();
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

  const value = clientId
    .replace(/^client_/, "")
    .replace(/[-_]+/g, " ")
    .trim();

  return value
    ? value.charAt(0).toUpperCase()
      + value.slice(1)
    : "Application";
};

const resolveClientName = (
  client: ClientItem,
) => {
  const placeholder =
    client.clientName?.match(
      /^\$\{client_(.+)\}$/,
    );

  if (placeholder) {
    return humanizeClientId(
      placeholder[1],
    );
  }

  if (client.clientName?.trim()) {
    return client.clientName;
  }

  return humanizeClientId(
    client.clientId || "",
  );
};

const formatTimestamp = (
  value: number | undefined,
  locale: string,
) => {
  if (!value) {
    return "Non renseigné";
  }

  const date = new Date(value * 1000);

  if (
    Number.isNaN(date.getTime())
  ) {
    return "Non renseigné";
  }

  return new Intl.DateTimeFormat(
    locale || "fr-FR",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
};

const sortDevices = (
  devices: DeviceRepresentation[],
) =>
  [...devices]
    .map((device) => ({
      ...device,
      sessions: [
        ...(device.sessions || []),
      ].sort(
        (left, right) =>
          Number(right.current)
          - Number(left.current),
      ),
    }))
    .sort(
      (left, right) =>
        Number(right.current)
        - Number(left.current),
    );

export const EitasDevicesPage = () => {
  const context =
    useEnvironment<AccountEnvironment>();

  const [devices, setDevices] =
    useState<DeviceRepresentation[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [busy, setBusy] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  const [refreshKey, setRefreshKey] =
    useState(0);

  const [confirmation, setConfirmation] =
    useState<Confirmation>(null);

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

    getDevices({
      signal: controller.signal,
      context,
    })
      .then(
        (
          result:
            DeviceRepresentation[],
        ) => {
          if (
            controller.signal.aborted
          ) {
            return;
          }

          setDevices(
            sortDevices(
              Array.isArray(result)
                ? result
                : [],
            ),
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
            "Chargement des appareils impossible.",
            caughtError,
          );

          setError(
            "Les appareils et sessions "
              + "ne peuvent pas être chargés.",
          );

          setLoading(false);
        },
      );

    return () => {
      controller.abort();
    };
  }, [context, refreshKey]);

  const sessionCount = useMemo(
    () =>
      devices.reduce(
        (total, device) =>
          total
          + (
            device.sessions?.length
            || 0
          ),
        0,
      ),
    [devices],
  );

  const currentSessionCount = useMemo(
    () =>
      devices.reduce(
        (total, device) =>
          total
          + (
            device.sessions || []
          ).filter(
            (session) =>
              session.current,
          ).length,
        0,
      ),
    [devices],
  );

  const confirmDisconnect =
    async () => {
      if (!confirmation) {
        return;
      }

      setBusy(true);
      setError("");
      setSuccess("");

      try {
        if (
          confirmation.type === "all"
        ) {
          const response =
            await deleteSession(context);

          if (!response.ok) {
            throw new Error(
              `HTTP ${response.status}`,
            );
          }

          await context.keycloak.logout();

          return;
        }

        const response =
          await deleteSession(
            context,
            confirmation.session.id,
          );

        if (!response.ok) {
          throw new Error(
            `HTTP ${response.status}`,
          );
        }

        setSuccess(
          "La session distante a été déconnectée.",
        );

        setConfirmation(null);
        refresh();
      } catch (caughtError) {
        console.error(
          "Déconnexion impossible.",
          caughtError,
        );

        setError(
          "La session n’a pas pu être déconnectée.",
        );

        setConfirmation(null);
      } finally {
        setBusy(false);
      }
    };

  return (
    <section className={style.page}>
      <header className={style.pageHeader}>
        <div>
          <span className={style.eyebrow}>
            Sécurité du compte
          </span>

          <h1>Appareils et sessions</h1>

          <p>
            Surveillez les appareils connectés
            et déconnectez toute session que
            vous ne reconnaissez pas.
          </p>
        </div>

        <div className={style.summaryGroup}>
          <div className={style.summary}>
            <strong>{devices.length}</strong>

            <span>
              appareil
              {devices.length > 1
                ? "s"
                : ""}
            </span>
          </div>

          <div className={style.summary}>
            <strong>{sessionCount}</strong>

            <span>
              session
              {sessionCount > 1
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
              Activité de connexion
            </strong>

            <span>
              {currentSessionCount}
              {" "}
              session
              {currentSessionCount > 1
                ? "s"
                : ""}
              {" "}
              actuelle
              {currentSessionCount > 1
                ? "s"
                : ""}
            </span>
          </div>

          <div className={style.toolbarActions}>
            <button
              type="button"
              className={style.refreshButton}
              onClick={refresh}
              disabled={loading || busy}
            >
              <RefreshIcon />
              Actualiser
            </button>

            {sessionCount > 1 && (
              <button
                type="button"
                className={style.logoutAllButton}
                onClick={() =>
                  setConfirmation({
                    type: "all",
                  })
                }
                disabled={busy}
              >
                <LogoutIcon />
                Tout déconnecter
              </button>
            )}
          </div>
        </div>

        {success && (
          <div className={style.success}>
            <span aria-hidden="true" />
            {success}
          </div>
        )}

        {loading && (
          <div className={style.state}>
            <span className={style.spinner} />

            <strong>
              Chargement des sessions
            </strong>

            <span>
              Analyse de l’activité de votre
              compte…
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
          devices.length === 0 && (
            <div className={style.state}>
              <span
                className={style.emptyIcon}
              >
                <DeviceIcon mobile={false} />
              </span>

              <strong>
                Aucun appareil actif
              </strong>

              <span>
                Aucune session de connexion
                n’est actuellement enregistrée.
              </span>
            </div>
          )}

        {!loading &&
          !error &&
          devices.length > 0 && (
            <div className={style.deviceList}>
              {devices.map(
                (device, deviceIndex) => (
                  <article
                    className={style.deviceCard}
                    key={
                      `${getDeviceName(device)}-${deviceIndex}`
                    }
                  >
                    <div
                      className={style.deviceHeader}
                    >
                      <span
                        className={style.deviceIcon}
                      >
                        <DeviceIcon
                          mobile={device.mobile}
                        />
                      </span>

                      <div
                        className={style.deviceIdentity}
                      >
                        <strong>
                          {getDeviceName(device)}
                        </strong>

                        <span>
                          {device.mobile
                            ? "Appareil mobile"
                            : "Ordinateur"}
                        </span>
                      </div>

                      {device.current && (
                        <span
                          className={style.deviceStatus}
                        >
                          <i aria-hidden="true" />
                          Appareil actuel
                        </span>
                      )}
                    </div>

                    <div
                      className={style.sessionList}
                    >
                      {(device.sessions || []).map(
                        (session) => {
                          const clients =
                            (
                              session.clients
                              || []
                            ) as ClientItem[];

                          return (
                            <section
                              className={
                                style.sessionRow
                              }
                              key={session.id}
                            >
                              <div
                                className={
                                  style.sessionHeading
                                }
                              >
                                <div>
                                  <strong>
                                    {session.browser
                                      || "Navigateur inconnu"}
                                  </strong>

                                  <span>
                                    {session.ipAddress
                                      || "Adresse IP inconnue"}
                                  </span>
                                </div>

                                {session.current ? (
                                  <span
                                    className={
                                      style.currentBadge
                                    }
                                  >
                                    <i
                                      aria-hidden="true"
                                    />
                                    Session actuelle
                                  </span>
                                ) : (
                                  <button
                                    type="button"
                                    className={
                                      style.disconnectButton
                                    }
                                    onClick={() =>
                                      setConfirmation({
                                        type: "session",
                                        device,
                                        session,
                                      })
                                    }
                                    disabled={busy}
                                  >
                                    <LogoutIcon />
                                    Déconnecter
                                  </button>
                                )}
                              </div>

                              <div
                                className={
                                  style.sessionMeta
                                }
                              >
                                <div>
                                  <small>
                                    Dernier accès
                                  </small>

                                  <strong>
                                    {formatTimestamp(
                                      session.lastAccess,
                                      context.environment.locale,
                                    )}
                                  </strong>
                                </div>

                                <div>
                                  <small>
                                    Début
                                  </small>

                                  <strong>
                                    {formatTimestamp(
                                      session.started,
                                      context.environment.locale,
                                    )}
                                  </strong>
                                </div>

                                <div>
                                  <small>
                                    Expiration
                                  </small>

                                  <strong>
                                    {formatTimestamp(
                                      session.expires,
                                      context.environment.locale,
                                    )}
                                  </strong>
                                </div>
                              </div>

                              <div
                                className={
                                  style.clientSection
                                }
                              >
                                <small>
                                  Applications utilisées
                                </small>

                                <div
                                  className={
                                    style.clientList
                                  }
                                >
                                  {clients.length > 0 ? (
                                    clients.map(
                                      (
                                        client,
                                        clientIndex,
                                      ) => (
                                        <span
                                          key={
                                            client.clientId
                                            || clientIndex
                                          }
                                        >
                                          {resolveClientName(
                                            client,
                                          )}
                                        </span>
                                      ),
                                    )
                                  ) : (
                                    <span>
                                      Aucune application
                                    </span>
                                  )}
                                </div>
                              </div>
                            </section>
                          );
                        },
                      )}
                    </div>
                  </article>
                ),
              )}
            </div>
          )}
      </section>

      {confirmation && (
        <div
          className={style.modalBackdrop}
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target
              === event.currentTarget
            ) {
              setConfirmation(null);
            }
          }}
        >
          <section
            className={style.modal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="eitas-session-dialog-title"
          >
            <span className={style.modalIcon}>
              <LogoutIcon />
            </span>

            <h2 id="eitas-session-dialog-title">
              {confirmation.type === "all"
                ? "Déconnecter toutes les sessions ?"
                : "Déconnecter cette session ?"}
            </h2>

            <p>
              {confirmation.type === "all"
                ? (
                  "Toutes les sessions, y compris "
                  + "celle-ci, seront fermées. "
                  + "Vous devrez vous reconnecter."
                )
                : (
                  "La session sélectionnée perdra "
                  + "immédiatement l’accès à votre compte."
                )}
            </p>

            <div className={style.modalActions}>
              <button
                type="button"
                className={style.cancelButton}
                onClick={() =>
                  setConfirmation(null)
                }
                disabled={busy}
              >
                Annuler
              </button>

              <button
                type="button"
                className={style.confirmButton}
                onClick={() =>
                  void confirmDisconnect()
                }
                disabled={busy}
              >
                {busy
                  ? "Déconnexion…"
                  : "Confirmer"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
};

export default EitasDevicesPage;
