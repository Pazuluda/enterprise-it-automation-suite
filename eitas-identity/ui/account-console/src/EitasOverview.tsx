import {
  type AccountEnvironment,
  getApplications,
  getCredentials,
  getDevices,
  getPersonalInfo,
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { environment } from "./environment";
import style from "./EitasOverview.module.css";

type PersonalInfo = Awaited<
  ReturnType<typeof getPersonalInfo>
>;

type Credentials = Awaited<
  ReturnType<typeof getCredentials>
>;

type Devices = Awaited<
  ReturnType<typeof getDevices>
>;

type Applications = Awaited<
  ReturnType<typeof getApplications>
>;

type OverviewState = {
  loading: boolean;
  profile: PersonalInfo | null;
  credentials: Credentials;
  devices: Devices;
  applications: Applications;
  unavailable: string[];
};

type StatusTone =
  | "success"
  | "warning"
  | "neutral"
  | "info";

type StatusCardProps = {
  label: string;
  value: string;
  description: string;
  tone: StatusTone;
  path: string;
  action: string;
  badge: string;
};

const basePath = decodeURIComponent(
  new URL(environment.baseUrl).pathname,
).replace(/\/+$/, "");

const accountUrl = (path: string) =>
  `${basePath}/${path}`.replace(/\/{2,}/g, "/");

const initialState: OverviewState = {
  loading: true,
  profile: null,
  credentials: [],
  devices: [],
  applications: [],
  unavailable: [],
};

const getCredentialSearchText = (
  credentials: Credentials,
) =>
  JSON.stringify(credentials ?? []).toLowerCase();

const countSessions = (devices: Devices) =>
  devices.reduce((total, device) => {
    const sessions = Array.isArray(device.sessions)
      ? device.sessions.length
      : 0;

    return total + sessions;
  }, 0);

const getDisplayName = (
  profile: PersonalInfo | null,
) => {
  if (!profile) {
    return "Utilisateur EITAS";
  }

  const fullName = [
    profile.firstName,
    profile.lastName,
  ]
    .filter(Boolean)
    .join(" ")
    .trim();

  return (
    fullName ||
    profile.username ||
    profile.email ||
    "Utilisateur EITAS"
  );
};

const StatusCard = ({
  label,
  value,
  description,
  tone,
  path,
  action,
  badge,
}: StatusCardProps) => (
  <article className={style.statusCard}>
    <div className={style.statusCardHeader}>
      <span className={style.statusLabel}>
        {label}
      </span>

      <span
        className={[
          style.statusBadge,
          style[tone],
        ].join(" ")}
      >
        {badge}
      </span>
    </div>

    <strong className={style.statusValue}>
      {value}
    </strong>

    <p>{description}</p>

    <Link
      className={style.cardLink}
      to={accountUrl(path)}
    >
      {action}
      <span aria-hidden="true">→</span>
    </Link>
  </article>
);

const FeatureItem = ({
  title,
  description,
  enabled,
}: {
  title: string;
  description: string;
  enabled: boolean;
}) => (
  <div className={style.featureItem}>
    <span
      className={[
        style.featureIndicator,
        enabled ? style.featureEnabled : "",
      ].join(" ")}
      aria-hidden="true"
    />

    <div>
      <strong>{title}</strong>
      <span>{description}</span>
    </div>

    <span
      className={[
        style.featureState,
        enabled ? style.stateEnabled : "",
      ].join(" ")}
    >
      {enabled
          ? "Disponible"
          : title === "Comptes associés"
            ? "Aucun fournisseur configuré"
            : "Non activé"}
    </span>
  </div>
);

export const EitasOverview = () => {
  const context =
    useEnvironment<AccountEnvironment>();

  const [state, setState] =
    useState<OverviewState>(initialState);

  useEffect(() => {
    const controller = new AbortController();
    const unavailable: string[] = [];

    const safeLoad = async <T,>(
      label: string,
      factory: () => Promise<T>,
      fallback: T,
    ): Promise<T> => {
      try {
        return await factory();
      } catch (error) {
        if (
          error instanceof Error &&
          error.name === "AbortError"
        ) {
          throw error;
        }

        console.warn(
          `Donnée Account indisponible : ${label}`,
          error,
        );

        unavailable.push(label);

        return fallback;
      }
    };

    const loadOverview = async () => {
      try {
        const [
          profile,
          credentials,
          devices,
          applications,
        ] = await Promise.all([
          safeLoad(
            "profil",
            () =>
              getPersonalInfo({
                signal: controller.signal,
                context,
              }),
            null,
          ),
          safeLoad(
            "identifiants",
            () =>
              getCredentials({
                signal: controller.signal,
                context,
              }),
            [],
          ),
          safeLoad(
            "sessions",
            () =>
              getDevices({
                signal: controller.signal,
                context,
              }),
            [],
          ),
          safeLoad(
            "applications",
            () =>
              getApplications({
                signal: controller.signal,
                context,
              }),
            [],
          ),
        ]);

        if (controller.signal.aborted) {
          return;
        }

        setState({
          loading: false,
          profile,
          credentials,
          devices,
          applications,
          unavailable,
        });
      } catch (error) {
        if (
          error instanceof Error &&
          error.name === "AbortError"
        ) {
          return;
        }

        console.error(
          "Chargement de la vue d’ensemble impossible.",
          error,
        );

        setState((current) => ({
          ...current,
          loading: false,
          unavailable: [
            ...current.unavailable,
            "vue d’ensemble",
          ],
        }));
      }
    };

    void loadOverview();

    return () => controller.abort();
  }, [context]);

  const credentialText = useMemo(
    () =>
      getCredentialSearchText(
        state.credentials,
      ),
    [state.credentials],
  );

  const hasPassword =
    credentialText.includes("password");

  const hasMfa =
    credentialText.includes("otp") ||
    credentialText.includes("totp") ||
    credentialText.includes("webauthn") ||
    credentialText.includes("passkey") ||
    credentialText.includes("recovery");

  const displayName =
    getDisplayName(state.profile);

  const profileComplete = Boolean(
    state.profile?.email &&
      state.profile?.firstName &&
      state.profile?.lastName,
  );

  const sessionCount =
    countSessions(state.devices);

  const applicationCount =
    state.applications.length;

  const availableFeatures = [
    environment.features
      .isLinkedAccountsEnabled,
    environment.features
      .isViewGroupsEnabled,
    environment.features
      .isViewOrganizationsEnabled,
    environment.features
      .isMyResourcesEnabled,
    environment.features
      .isOid4VciEnabled,
  ].filter(Boolean).length;

  if (state.loading) {
    return (
      <section className={style.loading}>
        <div className={style.loadingMark}>
          E
        </div>

        <div>
          <strong>
            Préparation de votre espace
          </strong>
          <span>
            Chargement des informations de sécurité…
          </span>
        </div>
      </section>
    );
  }

  return (
    <div className={style.overview}>
      <section className={style.hero}>
        <div>
          <span className={style.eyebrow}>
            Espace personnel sécurisé
          </span>

          <h1>
            Bonjour, {displayName}
          </h1>

          <p>
            Retrouvez l’état de votre identité,
            de vos méthodes d’authentification
            et de vos accès professionnels.
          </p>
        </div>

        <div className={style.heroIdentity}>
          <span className={style.avatar}>
            {displayName
              .split(/\s+/)
              .slice(0, 2)
              .map((part: string) => part.charAt(0))
              .join("")
              .toUpperCase()}
          </span>

          <div>
            <strong>{displayName}</strong>
            <span>
              {state.profile?.email ||
                state.profile?.username ||
                "Compte EITAS Identity"}
            </span>
          </div>
        </div>
      </section>

      {state.unavailable.length > 0 && (
        <section className={style.notice}>
          <strong>
            Certaines données sont temporairement
            indisponibles.
          </strong>

          <span>
            Modules concernés :{" "}
            {state.unavailable.join(", ")}.
          </span>
        </section>
      )}

      <section className={style.section}>
        <div className={style.sectionHeader}>
          <div>
            <span className={style.sectionEyebrow}>
              Situation du compte
            </span>

            <h2>
              Votre sécurité en un coup d’œil
            </h2>
          </div>

          <span className={style.securePill}>
            <span />
            Session sécurisée
          </span>
        </div>

        <div className={style.statusGrid}>
          <StatusCard
            label="Identité"
            value={
              profileComplete
                ? "Profil complet"
                : "À compléter"
            }
            description="Informations personnelles et préférences du compte."
            tone={
              profileComplete
                ? "success"
                : "warning"
            }
            badge={
              profileComplete
                ? "Conforme"
                : "Attention"
            }
            path="personal-info"
            action="Gérer mon profil"
          />

          <StatusCard
            label="Mot de passe"
            value={
              hasPassword
                ? "Configuré"
                : "À vérifier"
            }
            description="Méthode principale utilisée pour accéder à votre compte."
            tone={
              hasPassword
                ? "success"
                : "neutral"
            }
            badge={
              hasPassword
                ? "Actif"
                : "État inconnu"
            }
            path="account-security/signing-in"
            action="Voir mes méthodes"
          />

          <StatusCard
            label="Double authentification"
            value={
              hasMfa
                ? "Protégé"
                : "Non configurée"
            }
            description="Renforcez la protection de votre compte avec un second facteur."
            tone={
              hasMfa
                ? "success"
                : "warning"
            }
            badge={
              hasMfa
                ? "MFA active"
                : "Recommandé"
            }
            path="account-security/signing-in"
            action={
              hasMfa
                ? "Gérer la MFA"
                : "Configurer la MFA"
            }
          />

          <StatusCard
            label="Sessions"
            value={`${sessionCount} active${
              sessionCount > 1 ? "s" : ""
            }`}
            description="Consultez les appareils connectés à votre identité."
            tone="info"
            badge="Surveillé"
            path="account-security/device-activity"
            action="Voir les appareils"
          />

          <StatusCard
            label="Applications"
            value={`${applicationCount} autorisée${
              applicationCount > 1 ? "s" : ""
            }`}
            description="Applications professionnelles utilisant votre identité."
            tone="info"
            badge="Accès"
            path="applications"
            action="Consulter les accès"
          />

          <StatusCard
            label="Services d’identité"
            value={`${availableFeatures} disponible${
              availableFeatures > 1 ? "s" : ""
            }`}
            description="Fonctions complémentaires activées pour votre organisation."
            tone="neutral"
            badge="Environnement"
            path="applications"
            action="Voir les services"
          />
        </div>
      </section>

      <section className={style.detailsGrid}>
        <article className={style.panel}>
          <div className={style.panelHeader}>
            <div>
              <span className={style.sectionEyebrow}>
                Capacités du compte
              </span>

              <h2>
                Services disponibles
              </h2>
            </div>
          </div>

          <div className={style.featureList}>
            <FeatureItem
              title="Comptes associés"
              description="Connexion via des fournisseurs d’identité externes."
              enabled={
                environment.features
                  .isLinkedAccountsEnabled
              }
            />

            <FeatureItem
              title="Groupes"
              description="Consultation des appartenances et groupes de sécurité."
              enabled={
                environment.features
                  .isViewGroupsEnabled
              }
            />

            <FeatureItem
              title="Organisations"
              description="Affichage des organisations auxquelles votre compte appartient."
              enabled={
                environment.features
                  .isViewOrganizationsEnabled
              }
            />

            <FeatureItem
              title="Ressources partagées"
              description="Gestion des ressources et autorisations utilisateur."
              enabled={
                environment.features
                  .isMyResourcesEnabled
              }
            />

            <FeatureItem
              title="Justificatifs vérifiables"
              description="Consultation des justificatifs numériques associés au compte."
              enabled={
                environment.features
                  .isOid4VciEnabled
              }
            />
          </div>
        </article>

        <article className={style.panel}>
          <div className={style.panelHeader}>
            <div>
              <span className={style.sectionEyebrow}>
                Actions recommandées
              </span>

              <h2>
                Protéger mon identité
              </h2>
            </div>
          </div>

          <div className={style.actionList}>
            <Link
              to={accountUrl(
                "account-security/signing-in",
              )}
            >
              <span className={style.actionIcon}>
                01
              </span>

              <span>
                <strong>
                  Vérifier mes méthodes
                  d’authentification
                </strong>

                <small>
                  Mot de passe, MFA et clés
                  de sécurité.
                </small>
              </span>

              <b aria-hidden="true">→</b>
            </Link>

            <Link
              to={accountUrl(
                "account-security/device-activity",
              )}
            >
              <span className={style.actionIcon}>
                02
              </span>

              <span>
                <strong>
                  Contrôler mes sessions actives
                </strong>

                <small>
                  Déconnectez les appareils
                  que vous ne reconnaissez pas.
                </small>
              </span>

              <b aria-hidden="true">→</b>
            </Link>

            <Link
              to={accountUrl("personal-info")}
            >
              <span className={style.actionIcon}>
                03
              </span>

              <span>
                <strong>
                  Maintenir mon profil à jour
                </strong>

                <small>
                  Informations personnelles,
                  courriel et langue.
                </small>
              </span>

              <b aria-hidden="true">→</b>
            </Link>
          </div>
        </article>
      </section>
    </div>
  );
};

export default EitasOverview;
