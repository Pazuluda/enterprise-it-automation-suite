import { routes as keycloakAccountRoutes } from "@keycloak/keycloak-account-ui";
import {
  Resources,
} from "@keycloak/keycloak-account-ui";
import type {
  IndexRouteObject,
  RouteObject,
} from "react-router-dom";
import { Navigate } from "react-router-dom";
import App from "./App";
import { EitasOverview } from "./EitasOverview";
import { EitasGroupsPage } from "./EitasGroupsPage";
import { EitasOrganizationsPage } from "./EitasOrganizationsPage";
import { EitasApplicationsPage } from "./EitasApplicationsPage";
import { EitasDevicesPage } from "./EitasDevicesPage";
import { EitasAuthenticationPage } from "./EitasAuthenticationPage";
import { EitasPersonalInfoPage } from "./EitasPersonalInfoPage";
import { EitasLinkedAccountsPage } from "./EitasLinkedAccountsPage";
import { EitasUpdateCenterPage } from "./EitasUpdateCenterPage";
import { environment } from "./environment";

import { EitasResourcesShell } from "./EitasResourcesShell";
const basePath = decodeURIComponent(
  new URL(environment.baseUrl).pathname,
).replace(/\/+$/, "");

const overviewUrl = `${basePath}/overview`;

const unavailable = (
  <Navigate
    to={overviewUrl}
    replace
  />
);

const OverviewIndexRoute: IndexRouteObject = {
  index: true,
  element: <EitasOverview />,
};

const OverviewRoute: RouteObject = {
  path: "overview",
  element: <EitasOverview />,
};

const PersonalInfoRoute: RouteObject = {
  path: "personal-info",
  element: <EitasPersonalInfoPage />,
};

const LegacyPersonalInfoRoute: RouteObject = {
  path: "personalInfo",
  element: (
    <Navigate
      to={`${basePath}/personal-info`}
      replace
    />
  ),
};

const SigningInRoute: RouteObject = {
  path: "account-security/signing-in",
  element: <EitasAuthenticationPage />,
};

const LegacySigningInRoute: RouteObject = {
  path: "account-security/signingIn",
  element: (
    <Navigate
      to={`${basePath}/account-security/signing-in`}
      replace
    />
  ),
};

const DeviceActivityRoute: RouteObject = {
  path: "account-security/device-activity",
  element: <EitasDevicesPage />,
};

const LegacyDeviceActivityRoute: RouteObject = {
  path: "account-security/deviceActivity",
  element: (
    <Navigate
      to={`${basePath}/account-security/device-activity`}
      replace
    />
  ),
};

const LinkedAccountsRoute: RouteObject = {
  path: "account-security/linked-accounts",
  element: <EitasLinkedAccountsPage />,
};

const LegacyLinkedAccountsRoute: RouteObject = {
  path: "account-security/linkedAccounts",
  element: (
    <Navigate
      to={`${basePath}/account-security/linked-accounts`}
      replace
    />
  ),
};

const ApplicationsRoute: RouteObject = {
  path: "applications",
  element: <EitasApplicationsPage />,
};

const GroupsRoute: RouteObject = {
  path: "groups",
  element:
    environment.features.isViewGroupsEnabled
      ? <EitasGroupsPage />
      : unavailable,
};

const OrganizationsRoute: RouteObject = {
  path: "organizations",
  element:
    environment.features
      .isViewOrganizationsEnabled
      ? <EitasOrganizationsPage />
      : unavailable,
};

const ResourcesRoute: RouteObject = {
  path: "resources",
  element:
    <EitasResourcesShell content={environment.features
      .isMyResourcesEnabled
      ? <Resources />
      : unavailable} />,
};

const OfficialVerifiableCredentialsElement =
  keycloakAccountRoutes.find(
    (route) =>
      route.path === "verifiable-credentials",
  )?.element;

const UpdateCenterRoute: RouteObject = {
  path: "administration/update-center",
  element: <EitasUpdateCenterPage />,
};

const VerifiableCredentialsRoute: RouteObject = {
  path: "verifiable-credentials",
  element:
    environment.features.isOid4VciEnabled &&
    OfficialVerifiableCredentialsElement
      ? OfficialVerifiableCredentialsElement
      : unavailable,
};

export const RootRoute: RouteObject = {
  path: basePath,
  element: <App />,
  errorElement: (
    <div
      style={{
        padding: "32px",
        fontFamily:
          "Segoe UI, Arial, sans-serif",
      }}
    >
      Une erreur est survenue.
    </div>
  ),
  children: [
    OverviewIndexRoute,
    OverviewRoute,

    PersonalInfoRoute,
    LegacyPersonalInfoRoute,

    SigningInRoute,
    LegacySigningInRoute,

    DeviceActivityRoute,
    LegacyDeviceActivityRoute,

    LinkedAccountsRoute,
    LegacyLinkedAccountsRoute,

    ApplicationsRoute,
    GroupsRoute,
    OrganizationsRoute,
    ResourcesRoute,
    VerifiableCredentialsRoute,

    UpdateCenterRoute,
  ],
};

export const routes: RouteObject[] = [
  RootRoute,
];
