import {
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import { useLocation } from "react-router-dom";
import { NavLink } from "react-router-dom";
import { environment } from "./environment";
import style from "./PageNav.module.css";

type NavigationItem = {
  path: string;
  label: string;
  shortLabel: string;
  enabled: boolean;
};

type NavigationGroup = {
  title: string;
  items: NavigationItem[];
};

const basePath = decodeURIComponent(
  new URL(environment.baseUrl).pathname,
).replace(/\/+$/, "");

const destination = (path: string) =>
  `${basePath}/${path}`.replace(/\/{2,}/g, "/");

const navigationGroups: NavigationGroup[] = [
  {
    title: "Principal",
    items: [
      {
        path: "overview",
        label: "Vue d’ensemble",
        shortLabel: "VE",
        enabled: true,
      },
    ],
  },
  {
    title: "Identité",
    items: [
      {
        path: "personal-info",
        label: "Informations personnelles",
        shortLabel: "ID",
        enabled: true,
      },
      {
        path: "groups",
        label: "Groupes",
        shortLabel: "GR",
        enabled:
          environment.features
            .isViewGroupsEnabled,
      },
      {
        path: "organizations",
        label: "Organisations",
        shortLabel: "OR",
        enabled:
          environment.features
            .isViewOrganizationsEnabled,
      },
    ],
  },
  {
    title: "Sécurité",
    items: [
      {
        path: "account-security/signing-in",
        label: "Authentification",
        shortLabel: "AU",
        enabled: true,
      },
      {
        path:
          "account-security/device-activity",
        label: "Appareils et sessions",
        shortLabel: "AS",
        enabled: true,
      },
      {
        path:
          "account-security/linked-accounts",
        label: "Comptes associés",
        shortLabel: "CA",
          enabled: true,
      },
    ],
  },
  {
    title: "Accès",
    items: [
      {
        path: "applications",
        label: "Applications",
        shortLabel: "AP",
        enabled: true,
      },
      {
        path: "resources",
        label: "Ressources partagées",
        shortLabel: "RS",
        enabled:
          environment.features
            .isMyResourcesEnabled,
      },
      {
        path: "verifiable-credentials",
        label: "Justificatifs vérifiables",
        shortLabel: "JV",
        enabled: environment.features.isOid4VciEnabled,
      },
    ],
  },
];

export const PageNav = () => {
  const location = useLocation();
  const { keycloak } = useEnvironment();

  const isAdmin =
    keycloak.hasRealmRole("admin")
    || keycloak.hasRealmRole("UltraAdmin");

  const serverBaseUrl =
    environment.serverBaseUrl.replace(/\/+$/, "");

  const adminUrl =
    `${serverBaseUrl}/admin/`
    + `${encodeURIComponent("master")}`
    + "/console/";

  const visibleNavigationGroups = isAdmin
    ? navigationGroups
    : navigationGroups
        .map((group) => ({
          ...group,
          items: group.items.filter(
            (item) => item.enabled,
          ),
        }))
        .filter(
          (group) => group.items.length > 0,
        );

  const normalizedCurrentPath =
    location.pathname.replace(/\/+$/, "");

  const isActive = (path: string) => {
    const target =
      destination(path).replace(/\/+$/, "");

    if (
      path === "overview" &&
      normalizedCurrentPath === basePath
    ) {
      return true;
    }

    return normalizedCurrentPath === target;
  };

  return (
    <aside className={style.sidebar}>
      <div className={style.sidebarIntro}>
        <span className={style.eyebrow}>
          Espace personnel
        </span>

        <strong>Mon identité</strong>

        <p>
          Gérez votre profil, vos méthodes
          de connexion et vos accès.
        </p>
      </div>

      <nav
        className={style.navigation}
        aria-label="Navigation EITAS Identity"
      >
        {visibleNavigationGroups.map((group) => (
          <section
            className={style.navGroup}
            key={group.title}
          >
            <span className={style.groupTitle}>
              {group.title}
            </span>

            <div className={style.groupItems}>
              {group.items.map((item) => {
                const active =
                  isActive(item.path);

                if (!item.enabled) {
                  return (
                    <div
                      key={item.path}
                      className={[
                        style.navItem,
                        style.disabled,
                      ].join(" ")}
                      aria-disabled="true"
                      title="Fonction non activée dans ce realm"
                    >

                      <span
                        className={style.navLabel}
                      >
                        {item.label}
                      </span>

                      <span
                        className={style.unavailable}
                      >
                        Non activé
                      </span>
                    </div>
                  );
                }

                return (
                  <NavLink
                    key={item.path}
                    to={destination(item.path)}
                    className={[
                      style.navItem,
                      active
                        ? style.active
                        : "",
                    ].join(" ")}
                  >

                    <span
                      className={style.navLabel}
                    >
                      {item.label}
                    </span>
                  </NavLink>
                );
              })}
            </div>
          </section>
        ))}

          {isAdmin && (
            <section className={style.navGroup}>
              <span className={style.groupTitle}>
                Administration
              </span>

              <div className={style.groupItems}>
                <a
                  href={adminUrl}
                  className={style.navItem}
                >
                  <span className={style.navLabel}>
                    Console d’administration
                  </span>
                </a>

                <NavLink
                  to={destination(
                    "administration/update-center",
                  )}
                  className={[
                    style.navItem,
                    isActive(
                      "administration/update-center",
                    )
                      ? style.active
                      : "",
                  ].join(" ")}
                >
                  <span className={style.navLabel}>
                    Centre de mise à jour
                  </span>
                </NavLink>
              </div>
            </section>
          )}

      </nav>

      <div className={style.sidebarFooter}>
        <span className={style.statusDot} />
        <span>Session sécurisée</span>
      </div>
    </aside>
  );
};
