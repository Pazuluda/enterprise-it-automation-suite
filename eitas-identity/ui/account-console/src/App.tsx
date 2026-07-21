import {
  Header,
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import { Spinner } from "@patternfly/react-core";
import { Suspense } from "react";
import { Outlet } from "react-router-dom";
import style from "./App.module.css";
import { environment } from "./environment";
import { PageNav } from "./PageNav";

const BrandShield = () => (
  <svg
    className={style.brandShield}
    viewBox="0 0 48 56"
    role="img"
    aria-label="EITAS Identity"
  >
    <path
      d="M24 2 44 10v16c0 13.2-8.2 23.4-20 28C12.2 49.4 4 39.2 4 26V10L24 2Z"
      fill="#628BFF"
    />

    <path
      d="M24 10 36 15v11c0 8.2-4.8 14.8-12 18-7.2-3.2-12-9.8-12-18V15l12-5Z"
      fill="#DCE7FF"
    />

    <path
      d="m18.5 26.5 4 4 8-9"
      fill="none"
      stroke="#13233B"
      strokeWidth="3.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const EitasHeader = () => {
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

  return (
    <header className={style.topbar}>
      <div className={style.brand}>
        <BrandShield />

        <div className={style.brandText}>
          <div className={style.brandName}>
            EITAS <span>Identity</span>
          </div>

          <div className={style.brandTagline}>
            Identity &amp; Access Management
          </div>
        </div>
      </div>

      <div className={style.headerSession}>
        {isAdmin && (
          <a
            href={adminUrl}
            className={style.interfaceSwitch}
          >
            Administration
          </a>
        )}

        <Header />
      </div>
    </header>
  );
};

const LoadingView = () => (
  <div className={style.loading}>
    <Spinner size="xl" />
    <span>Chargement de votre espace EITAS…</span>
  </div>
);

function App() {
  return (
    <div className={style.shell}>
      <EitasHeader />

      <div className={style.workspace}>
        <PageNav />

        <main className={style.main}>
          <div className={style.mainInner}>
            <Suspense fallback={<LoadingView />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
