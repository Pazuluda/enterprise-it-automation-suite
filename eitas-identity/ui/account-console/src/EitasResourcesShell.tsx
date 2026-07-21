import type { ReactNode } from "react";
import style from "./EitasResourcesShell.module.css";

type EitasResourcesShellProps = {
  content: ReactNode;
};

const LibraryIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M5 3.5h10.25A2.75 2.75 0 0 1 18 6.25V8h1.25A2.75 2.75 0 0 1 22 10.75v7.5A2.75 2.75 0 0 1 19.25 21H8.75A2.75 2.75 0 0 1 6 18.25V17H4.75A2.75 2.75 0 0 1 2 14.25v-8A2.75 2.75 0 0 1 4.75 3.5H5Zm1 11.5V10.75A2.75 2.75 0 0 1 8.75 8H16V6.25c0-.41-.34-.75-.75-.75H4.75a.75.75 0 0 0-.75.75v8c0 .41.34.75.75.75H6Zm2.75-5a.75.75 0 0 0-.75.75v7.5c0 .41.34.75.75.75h10.5a.75.75 0 0 0 .75-.75v-7.5a.75.75 0 0 0-.75-.75H8.75Z"
      fill="currentColor"
    />
  </svg>
);

const ShareIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M18 15.5a3.5 3.5 0 0 0-2.72 1.3l-6.1-3.18a3.7 3.7 0 0 0 0-3.24l6.1-3.18A3.5 3.5 0 1 0 14.5 5c0 .12.01.24.02.36l-6.3 3.28a3.5 3.5 0 1 0 0 6.72l6.3 3.28A3.5 3.5 0 1 0 18 15.5Zm0-12A1.5 1.5 0 1 1 18 6.5a1.5 1.5 0 0 1 0-3ZM6 13.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm12 6.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Z"
      fill="currentColor"
    />
  </svg>
);

export const EitasResourcesShell = ({
  content,
}: EitasResourcesShellProps) => (
  <section className={style.page}>
    <header className={style.pageHeader}>
      <div>
        <span className={style.eyebrow}>
          Accès et autorisations
        </span>

        <h1>Ressources partagées</h1>

        <p>
          Gérez les ressources appartenant à votre identité
          et contrôlez leur partage avec les autres utilisateurs.
        </p>
      </div>

      <div className={style.securityStatus}>
        <span className={style.securityStatusIcon}>
          <ShareIcon />
        </span>

        <div>
          <strong>Partage contrôlé</strong>
          <span>Autorisations UMA sécurisées</span>
        </div>
      </div>
    </header>

    <section className={style.panel}>
      <header className={style.panelHeader}>
        <span className={style.panelIcon}>
          <LibraryIcon />
        </span>

        <div>
          <strong>Bibliothèque de ressources</strong>

          <span>
            Consultez vos ressources et les éléments que
            d’autres utilisateurs ont partagés avec vous.
          </span>
        </div>
      </header>

      <div className={style.panelBody}>
        {content}
      </div>
    </section>
  </section>
);

export default EitasResourcesShell;
