import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ProjectDetailPage() {
  const { org, slug } = useParams<{ org: string; slug: string }>();
  const qc = useQueryClient();
  const { data: project } = useQuery({
    queryKey: ["project", slug],
    queryFn: () => api.getProject(slug!),
    enabled: !!slug,
  });
  const { data: bundles } = useQuery({
    queryKey: ["bundles", org],
    queryFn: () => api.listBundles(org!),
    enabled: !!org,
  });
  const { data: kpatches } = useQuery({
    queryKey: ["kpatches", org],
    queryFn: () => api.listKpatches(org!),
    enabled: !!org,
  });

  const [accessMode, setAccessMode] = useState<"org" | "invite_only">("org");
  const [members, setMembers] = useState("");
  const [attached, setAttached] = useState<string[]>([]);
  const [disabled, setDisabled] = useState<string[]>([]);

  useEffect(() => {
    if (project) {
      setAccessMode(project.access_mode);
      setMembers(project.members.join(", "));
      setAttached(project.attached_bundles);
      setDisabled(project.disabled_kpatch_ids);
    }
  }, [project]);

  const saveAccess = useMutation({
    mutationFn: () =>
      api.setProjectAccess(slug!, {
        access_mode: accessMode,
        members: members.split(",").map((m) => m.trim()).filter(Boolean),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", slug] }),
  });
  const saveAttached = useMutation({
    mutationFn: () => api.setAttachedBundles(slug!, attached),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", slug] }),
  });
  const saveDisabled = useMutation({
    mutationFn: () => api.setDisabledKpatches(slug!, disabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", slug] }),
  });

  if (!project) return null;

  const toggle = <T,>(arr: T[], v: T, set: (next: T[]) => void) =>
    set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <Link
          to={`/o/${org}/projects`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← projects
        </Link>
        <h2 className="text-xl font-semibold mt-1 font-mono">{project.slug}</h2>
      </div>

      <section className="space-y-3">
        <h3 className="font-medium">Access</h3>
        <div className="space-y-1">
          <Label htmlFor="am">Mode</Label>
          <select
            id="am"
            value={accessMode}
            onChange={(e) => setAccessMode(e.target.value as "org" | "invite_only")}
            className="w-full border rounded p-2 text-sm bg-background"
          >
            <option value="org">org (any org member; silent join on first hook)</option>
            <option value="invite_only">invite_only (members list only)</option>
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="mem">Members (comma-separated user ids)</Label>
          <Input
            id="mem"
            value={members}
            onChange={(e) => setMembers(e.target.value)}
          />
        </div>
        <Button onClick={() => saveAccess.mutate()} disabled={saveAccess.isPending}>
          Save access
        </Button>
      </section>

      <section className="space-y-3">
        <h3 className="font-medium">Attached bundles</h3>
        <div className="border rounded p-2 max-h-48 overflow-auto space-y-1">
          {bundles?.length === 0 && (
            <p className="text-xs text-muted-foreground">No bundles in this org.</p>
          )}
          {bundles?.map((b) => (
            <label key={b.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={attached.includes(b.id)}
                onChange={() => toggle(attached, b.id, setAttached)}
              />
              <code className="font-mono text-xs">{b.id}</code>
              <span className="text-muted-foreground">{b.name} ({b.version})</span>
            </label>
          ))}
        </div>
        <Button onClick={() => saveAttached.mutate()} disabled={saveAttached.isPending}>
          Save attached bundles
        </Button>
      </section>

      <section className="space-y-3">
        <h3 className="font-medium">Disabled kpatches</h3>
        <p className="text-xs text-muted-foreground">
          Kpatches inherited from org/community bundles to suppress in this project.
        </p>
        <div className="border rounded p-2 max-h-48 overflow-auto space-y-1">
          {kpatches?.map((k) => (
            <label key={k.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={disabled.includes(k.id)}
                onChange={() => toggle(disabled, k.id, setDisabled)}
              />
              <code className="font-mono text-xs">{k.id}</code>
              <span className="text-muted-foreground">{k.name}</span>
            </label>
          ))}
        </div>
        <Button onClick={() => saveDisabled.mutate()} disabled={saveDisabled.isPending}>
          Save disabled
        </Button>
      </section>

      <section className="space-y-2">
        <h3 className="font-medium">Overridden kpatches</h3>
        <p className="text-xs text-muted-foreground">
          Project-level kpatch redefinitions replace inherited entries by id. Edit raw
          JSON — UI editor lands in a follow-up.
        </p>
        <pre className="bg-muted/40 p-2 rounded text-xs overflow-auto max-h-32">
          {JSON.stringify(project.overridden_kpatches, null, 2)}
        </pre>
      </section>
    </div>
  );
}
