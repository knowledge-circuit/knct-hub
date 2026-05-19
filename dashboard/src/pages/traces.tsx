import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

type Trace = {
  id: number;
  ts: string;
  event: string;
  session_id: string | null;
  cwd: string | null;
  tool_name: string | null;
  payload: unknown;
  response: unknown;
  kpatch_ids: string[];
  triggered_by: number[];
  project_org_id: string | null;
  project_slug: string | null;
};

async function fetchTraces(params: URLSearchParams): Promise<Trace[]> {
  const res = await fetch(`/api/v1/traces?${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

const EVENTS = [
  "all",
  "SessionStart",
  "UserPromptSubmit",
  "PreToolUse",
  "PostCompact",
] as const;
type EventFilter = (typeof EVENTS)[number];

export function TracesPage() {
  const { org } = useParams<{ org: string }>();
  const [onlyInj, setOnlyInj] = useState(false);
  const [event, setEvent] = useState<EventFilter>("all");
  const [slug, setSlug] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Trace | null>(null);

  const params = useMemo(() => {
    const p = new URLSearchParams({ limit: "200" });
    if (org) p.set("org_id", org);
    if (onlyInj) p.set("only_injections", "true");
    if (event !== "all") p.set("event", event);
    if (slug.trim()) p.set("project_slug", slug.trim());
    return p;
  }, [org, onlyInj, event, slug]);

  const { data } = useQuery({
    queryKey: ["traces", params.toString()],
    queryFn: () => fetchTraces(params),
    refetchInterval: 5_000,
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return data ?? [];
    const needle = search.toLowerCase();
    return (data ?? []).filter((t) => {
      const blob = JSON.stringify(t.payload).toLowerCase();
      return (
        blob.includes(needle) ||
        t.kpatch_ids.some((k) => k.toLowerCase().includes(needle))
      );
    });
  }, [data, search]);

  const injCount = (data ?? []).filter((t) => t.kpatch_ids.length > 0).length;
  const total = data?.length ?? 0;

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)] gap-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={onlyInj}
            onChange={(e) => setOnlyInj(e.target.checked)}
          />
          Only injections
        </label>
        <select
          value={event}
          onChange={(e) => setEvent(e.target.value as EventFilter)}
          className="border rounded p-1 bg-background"
        >
          {EVENTS.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
        <input
          placeholder="project slug"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          className="border rounded p-1 text-sm w-32"
        />
        <input
          placeholder="search payload / kpatch"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded p-1 text-sm flex-1 min-w-48"
        />
        <span className="text-xs text-muted-foreground ml-auto">
          {injCount} injections / {total} traces
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        <div className="overflow-auto border rounded-md">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-background border-b">
              <tr>
                <th className="text-left p-2">Time</th>
                <th className="text-left p-2">Event</th>
                <th className="text-left p-2">Project</th>
                <th className="text-left p-2">Kpatches</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-4 text-center text-muted-foreground">
                    No traces match.
                  </td>
                </tr>
              )}
              {filtered.map((t) => {
                const fired = t.kpatch_ids.length > 0;
                return (
                  <tr
                    key={t.id}
                    onClick={() => setSelected(t)}
                    className={`cursor-pointer hover:bg-accent/50 border-b ${
                      selected?.id === t.id ? "bg-accent" : ""
                    } ${fired ? "" : "opacity-60"}`}
                  >
                    <td className="p-2 font-mono text-xs text-muted-foreground whitespace-nowrap">
                      {t.ts?.slice(11, 19)}
                    </td>
                    <td className="p-2 font-mono text-xs">
                      {t.event}
                      {t.tool_name && (
                        <span className="text-muted-foreground">:{t.tool_name}</span>
                      )}
                    </td>
                    <td className="p-2 font-mono text-xs">{t.project_slug ?? "—"}</td>
                    <td className="p-2">
                      {fired ? (
                        <div className="flex flex-wrap gap-1">
                          {t.kpatch_ids.map((id) => (
                            <span
                              key={id}
                              className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary"
                            >
                              {id}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="overflow-auto border rounded-md p-3">
          {!selected ? (
            <p className="text-sm text-muted-foreground">
              Pick a trace to see its payload + response.
            </p>
          ) : (
            <div className="space-y-3 text-xs">
              <div className="font-semibold">
                {selected.event} — {selected.ts}
              </div>
              {selected.kpatch_ids.length > 0 && (
                <div className="space-y-1">
                  <div className="font-medium">Kpatches injected</div>
                  <div className="flex flex-wrap gap-1">
                    {selected.kpatch_ids.map((id) => (
                      <span
                        key={id}
                        className="font-mono px-1.5 py-0.5 rounded bg-primary/10 text-primary"
                      >
                        {id}
                      </span>
                    ))}
                  </div>
                  {selected.triggered_by.length > 0 && (
                    <div className="text-muted-foreground">
                      triggers: {selected.triggered_by.join(", ")}
                    </div>
                  )}
                </div>
              )}
              <details open>
                <summary className="cursor-pointer font-medium">payload</summary>
                <pre className="bg-muted/40 p-2 rounded overflow-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(selected.payload, null, 2)}
                </pre>
              </details>
              <details open={selected.kpatch_ids.length > 0}>
                <summary className="cursor-pointer font-medium">response</summary>
                <pre className="bg-muted/40 p-2 rounded overflow-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(selected.response, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
