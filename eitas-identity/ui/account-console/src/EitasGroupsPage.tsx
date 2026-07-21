import {
  type AccountEnvironment,
  getGroups,
  useEnvironment,
} from "@keycloak/keycloak-account-ui";
import {
  useEffect,
  useMemo,
  useState,
} from "react";
import style from "./EitasGroupsPage.module.css";

type EitasGroup = {
  id?: string;
  name: string;
  path: string;
};

const sortGroups = (
  groups: EitasGroup[],
): EitasGroup[] =>
  [...groups].sort((left, right) =>
    left.path.localeCompare(
      right.path,
      "fr",
      {
        sensitivity: "base",
      },
    ),
  );

const includeParentGroups = (
  sourceGroups: EitasGroup[],
): EitasGroup[] => {
  const groupsByPath = new Map<
    string,
    EitasGroup
  >();

  sourceGroups.forEach((group) => {
    groupsByPath.set(
      group.path,
      { ...group },
    );
  });

  sourceGroups.forEach((group) => {
    let parentPath = group.path.slice(
      0,
      group.path.lastIndexOf("/"),
    );

    while (parentPath) {
      if (!groupsByPath.has(parentPath)) {
        const parentName = parentPath.slice(
          parentPath.lastIndexOf("/") + 1,
        );

        groupsByPath.set(parentPath, {
          name: parentName,
          path: parentPath,
        });
      }

      parentPath = parentPath.slice(
        0,
        parentPath.lastIndexOf("/"),
      );
    }
  });

  return sortGroups(
    Array.from(groupsByPath.values()),
  );
};

const GroupIcon = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      d="M8.25 11.25a3.25 3.25 0 1 0 0-6.5 3.25 3.25 0 0 0 0 6.5Zm7.5-.75a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM2.75 18.75c0-3.05 2.47-5.5 5.5-5.5s5.5 2.45 5.5 5.5v.5h-11v-.5Zm11.75.5v-.5c0-1.72-.6-3.3-1.6-4.55.86-.62 1.9-.95 2.98-.95 2.97 0 5.37 2.4 5.37 5.37v.63H14.5Z"
      fill="currentColor"
    />
  </svg>
);

export const EitasGroupsPage = () => {
  const context =
    useEnvironment<AccountEnvironment>();

  const [groups, setGroups] =
    useState<EitasGroup[]>([]);

  const [directOnly, setDirectOnly] =
    useState(false);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    const controller =
      new AbortController();

    setLoading(true);
    setError("");

    getGroups({
      signal: controller.signal,
      context,
    })
      .then((result) => {
        if (controller.signal.aborted) {
          return;
        }

        setGroups(
          Array.isArray(result)
            ? (result as EitasGroup[])
            : [],
        );

        setLoading(false);
      })
      .catch((caughtError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        console.error(
          "Chargement des groupes impossible.",
          caughtError,
        );

        setError(
          "Les appartenances aux groupes "
            + "ne peuvent pas être chargées.",
        );

        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [context]);

  const visibleGroups = useMemo(
    () =>
      directOnly
        ? sortGroups(
            groups.filter(
              (group) => group.id != null,
            ),
          )
        : includeParentGroups(groups),
    [directOnly, groups],
  );

  const directCount = useMemo(
    () =>
      groups.filter(
        (group) => group.id != null,
      ).length,
    [groups],
  );

  return (
    <section className={style.page}>
      <header className={style.pageHeader}>
        <div>
          <span className={style.eyebrow}>
            Identité et accès
          </span>

          <h1>Groupes</h1>

          <p>
            Consultez les groupes associés à
            votre compte et leur emplacement
            dans l’organisation.
          </p>
        </div>

        <div className={style.summary}>
          <strong>{directCount}</strong>

          <span>
            appartenance
            {directCount > 1 ? "s" : ""} directe
            {directCount > 1 ? "s" : ""}
          </span>
        </div>
      </header>

      <section className={style.panel}>
        <div className={style.toolbar}>
          <div className={style.toolbarTitle}>
            <strong>
              Mes appartenances
            </strong>

            <span>
              {visibleGroups.length} groupe
              {visibleGroups.length > 1
                ? "s"
                : ""} affiché
              {visibleGroups.length > 1
                ? "s"
                : ""}
            </span>
          </div>

          <label className={style.filter}>
            <input
              type="checkbox"
              checked={directOnly}
              onChange={(event) =>
                setDirectOnly(
                  event.target.checked,
                )
              }
            />

            <span
              className={style.switch}
              aria-hidden="true"
            />

            <span>
              Appartenances directes uniquement
            </span>
          </label>
        </div>

        {loading && (
          <div className={style.loading}>
            <span className={style.spinner} />

            <div>
              <strong>
                Chargement des groupes
              </strong>

              <span>
                Récupération des appartenances
                depuis EITAS Identity…
              </span>
            </div>
          </div>
        )}

        {!loading && error && (
          <div className={style.error}>
            <strong>
              Chargement impossible
            </strong>

            <span>{error}</span>
          </div>
        )}

        {!loading &&
          !error &&
          visibleGroups.length === 0 && (
            <div className={style.empty}>
              <GroupIcon />

              <strong>
                Aucun groupe à afficher
              </strong>

              <span>
                Votre compte n’est associé à
                aucun groupe correspondant à
                ce filtre.
              </span>
            </div>
          )}

        {!loading &&
          !error &&
          visibleGroups.length > 0 && (
            <div className={style.groupList}>
              {visibleGroups.map((group) => {
                const isDirect =
                  group.id != null;

                return (
                  <article
                    className={style.groupRow}
                    key={group.path}
                  >
                    <span
                      className={style.groupIcon}
                    >
                      <GroupIcon />
                    </span>

                    <div
                      className={
                        style.groupIdentity
                      }
                    >
                      <strong>
                        {group.name}
                      </strong>

                      <span>
                        {group.path}
                      </span>
                    </div>

                    <span
                      className={[
                        style.membership,
                        isDirect
                          ? style.direct
                          : style.inherited,
                      ].join(" ")}
                    >
                      <span aria-hidden="true" />

                      {isDirect
                        ? "Appartenance directe"
                        : "Groupe parent"}
                    </span>
                  </article>
                );
              })}
            </div>
          )}
      </section>
    </section>
  );
};

export default EitasGroupsPage;
