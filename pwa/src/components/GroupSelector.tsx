import { useState, useMemo } from "react";
import type { GroupMeta } from "../types/schedule";
import { useAppStore } from "../store";

interface Props {
  groups: GroupMeta[];
}

const DEGREE_LABELS: Record<string, string> = {
  bachelor: "Бакалавриат",
  specialist: "Специалитет",
  master: "Магистратура",
};

const FORM_LABELS: Record<string, string> = {
  full_time: "Очная",
  part_time: "Очно-заочная",
  correspondence: "Заочная",
};

const DEGREE_ORDER = ["bachelor", "specialist", "master"];

const NO_DIRECTION = "Без направления";
const NO_PROFILE = "Без профиля";

/** Каталог: направление → профиль → группы. Группы без направления не
 *  выкидываются, а уходят в хвостовую секцию — потерять группу хуже. */
function buildCatalog(groups: GroupMeta[]) {
  const byDirection = new Map<string, Map<string, GroupMeta[]>>();
  for (const g of groups) {
    const dir = g.direction?.trim() || NO_DIRECTION;
    const prof = g.profile?.trim() || NO_PROFILE;
    const profiles = byDirection.get(dir) ?? new Map<string, GroupMeta[]>();
    byDirection.set(dir, profiles);
    profiles.set(prof, [...(profiles.get(prof) ?? []), g]);
  }
  // Секции-заглушки всегда в хвосте, остальные — по алфавиту.
  const byName = (fallback: string) => (a: [string, unknown], b: [string, unknown]) =>
    Number(a[0] === fallback) - Number(b[0] === fallback) || a[0].localeCompare(b[0]);
  return [...byDirection.entries()]
    .sort(byName(NO_DIRECTION))
    .map(([direction, profiles]) => ({
      direction,
      profiles: [...profiles.entries()]
        .sort(byName(NO_PROFILE))
        .map(([profile, list]) => ({
          profile,
          groups: [...list].sort(
            (a, b) => (a.year ?? 0) - (b.year ?? 0) || a.name.localeCompare(b.name)
          ),
        })),
    }));
}

/** Поиск сразу по направлению, профилю и коду группы. */
function matches(g: GroupMeta, q: string): boolean {
  return (
    g.name.toLowerCase().includes(q) ||
    (g.direction ?? "").toLowerCase().includes(q) ||
    (g.profile ?? "").toLowerCase().includes(q)
  );
}

function GroupMetaButton({
  g,
  selected,
  pinned,
  onSelect,
  onPin,
}: {
  g: GroupMeta;
  selected: boolean;
  pinned: boolean;
  onSelect: () => void;
  onPin: () => void;
}) {
  return (
    <div className="relative">
      <button
        onClick={onSelect}
        className={`w-full rounded-xl px-3 py-2.5 border text-left transition-colors pr-8 ${
          selected
            ? "bg-indigo-700 text-white border-indigo-700"
            : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:bg-gray-700"
        }`}
      >
        <div className="font-semibold text-sm">{g.name}</div>
        {(g.year || g.form !== "full_time") && (
          <div className={`text-xs ${selected ? "text-indigo-200" : "text-gray-400 dark:text-gray-500"}`}>
            {[g.year ? `${g.year} курс` : null, FORM_LABELS[g.form] ?? g.form]
              .filter(Boolean)
              .join(" · ")}
          </div>
        )}
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onPin();
        }}
        className={`absolute right-2 top-1/2 -translate-y-1/2 text-sm leading-none transition-opacity ${
          pinned
            ? "opacity-100"
            : "opacity-30 hover:opacity-80"
        }`}
        aria-label={pinned ? "Открепить группу" : "Закрепить группу"}
      >
        {pinned ? "⭐" : "☆"}
      </button>
    </div>
  );
}

export default function GroupMetaSelector({ groups }: Props) {
  const setGroup = useAppStore((s) => s.setGroup);
  const selected = useAppStore((s) => s.selectedGroupName);
  const pinnedGroups = useAppStore((s) => s.pinnedGroups);
  const togglePin = useAppStore((s) => s.togglePin);

  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const filtered = useMemo(
    () => (q ? groups.filter((g) => matches(g, q)) : groups),
    [groups, q]
  );

  const catalog = useMemo(() => buildCatalog(filtered), [filtered]);

  // Источники без шапки направления: там навигация остаётся по уровню.
  const hasDirections = useMemo(
    () => catalog.some((d) => d.direction !== NO_DIRECTION),
    [catalog]
  );

  const byDegree = useMemo(
    () =>
      filtered.reduce<Record<string, GroupMeta[]>>((acc, g) => {
        const key = g.degree ?? "bachelor";
        (acc[key] ??= []).push(g);
        return acc;
      }, {}),
    [filtered]
  );

  const pinnedGroupMetaObjects = useMemo(
    () =>
      pinnedGroups
        .map((name) => groups.find((g) => g.name === name))
        .filter((g): g is GroupMeta => g !== undefined),
    [groups, pinnedGroups]
  );

  const showSearch = groups.length > 8;

  return (
    <div className="p-4">
      {showSearch && (
        <div className="relative mb-4">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск: направление, профиль или код…"
            className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2.5 pr-9 text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900"
            autoFocus
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none"
              aria-label="Очистить"
            >
              ×
            </button>
          )}
        </div>
      )}

      {q && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
          {filtered.length === 0
            ? "Ничего не найдено"
            : `Найдено: ${filtered.length} из ${groups.length}`}
        </p>
      )}

      {!showSearch && (
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider">
          Выберите направление и группу
        </h2>
      )}

      {/* Pinned groups block */}
      {!q && pinnedGroupMetaObjects.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-bold text-gray-400 dark:text-gray-500 mb-2 uppercase flex items-center gap-1">
            <span>⭐</span> Закреплённые
          </div>
          <div className="grid grid-cols-2 gap-2">
            {pinnedGroupMetaObjects.map((g) => (
              <GroupMetaButton
                key={g.name}
                g={g}
                selected={selected === g.name}
                pinned={pinnedGroups.includes(g.name)}
                onSelect={() => setGroup(g.name)}
                onPin={() => togglePin(g.name)}
              />
            ))}
          </div>
        </div>
      )}

      {hasDirections &&
        catalog.map(({ direction, profiles }) => (
          <div key={direction} className="mb-5">
            <div className="text-xs font-bold text-indigo-600 dark:text-indigo-300 mb-2 uppercase tracking-wide">
              {direction}
            </div>
            {profiles.map(({ profile, groups: list }) => (
              <div key={profile} className="mb-3">
                {(profile !== NO_PROFILE || profiles.length > 1) && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                    {profile}
                  </div>
                )}
                <div className="grid grid-cols-2 gap-2">
                  {list.map((g) => (
                    <GroupMetaButton
                      key={g.name}
                      g={g}
                      selected={selected === g.name}
                      pinned={pinnedGroups.includes(g.name)}
                      onSelect={() => setGroup(g.name)}
                      onPin={() => togglePin(g.name)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))}

      {!hasDirections &&
        DEGREE_ORDER.filter((d) => byDegree[d]?.length).map((degree) => (
        <div key={degree} className="mb-4">
          <div className="text-xs font-bold text-gray-400 dark:text-gray-500 mb-2 uppercase">
            {DEGREE_LABELS[degree] ?? degree}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {byDegree[degree]
              .sort((a, b) => (a.year ?? 0) - (b.year ?? 0) || a.name.localeCompare(b.name))
              .map((g) => (
                <GroupMetaButton
                  key={g.name}
                  g={g}
                  selected={selected === g.name}
                  pinned={pinnedGroups.includes(g.name)}
                  onSelect={() => setGroup(g.name)}
                  onPin={() => togglePin(g.name)}
                />
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
