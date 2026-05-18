import { useState } from "react";
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
};

async function fetchTraces(): Promise<Trace[]> {
  const res = await fetch("/api/v1/traces?limit=200");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function TracesPage() {
  const { data } = useQuery({
    queryKey: ["traces"],
    queryFn: fetchTraces,
    refetchInterval: 5_000,
  });
  const [selected, setSelected] = useState<Trace | null>(null);

  return (
    <div className="grid grid-cols-2 gap-4 h-[calc(100vh-5rem)]">
      <div className="overflow-auto border rounded-md">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-background border-b">
            <tr>
              <th className="text-left p-2">Time</th>
              <th className="text-left p-2">Event</th>
              <th className="text-left p-2">Tool</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((t) => (
              <tr
                key={t.id}
                onClick={() => setSelected(t)}
                className={`cursor-pointer hover:bg-accent/50 ${
                  selected?.id === t.id ? "bg-accent" : ""
                }`}
              >
                <td className="p-2 font-mono text-xs text-muted-foreground whitespace-nowrap">
                  {t.ts?.slice(11, 19)}
                </td>
                <td className="p-2 font-mono text-xs">{t.event}</td>
                <td className="p-2 font-mono text-xs">{t.tool_name ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="overflow-auto border rounded-md p-3">
        {!selected ? (
          <p className="text-sm text-muted-foreground">Pick a trace to see its payload + response.</p>
        ) : (
          <div className="space-y-3 text-xs">
            <div className="font-semibold">{selected.event} — {selected.ts}</div>
            <details open>
              <summary className="cursor-pointer font-medium">payload</summary>
              <pre className="bg-muted/40 p-2 rounded overflow-auto">{JSON.stringify(selected.payload, null, 2)}</pre>
            </details>
            <details open>
              <summary className="cursor-pointer font-medium">response</summary>
              <pre className="bg-muted/40 p-2 rounded overflow-auto">{JSON.stringify(selected.response, null, 2)}</pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
