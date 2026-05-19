import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Trigger } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Editing = { mode: "create" } | { mode: "edit"; trigger: Trigger } | null;

export function KpatchDetailPage() {
  const { org, id } = useParams<{ org: string; id: string }>();
  const qc = useQueryClient();
  const { data: kpatch } = useQuery({
    queryKey: ["kpatch", org, id],
    queryFn: () => api.getKpatch(org!, id!),
    enabled: !!org && !!id,
  });
  const { data: triggers } = useQuery({
    queryKey: ["triggers", org, id],
    queryFn: () => api.listTriggers(org!, id!),
    enabled: !!org && !!id,
  });
  const [editing, setEditing] = useState<Editing>(null);

  const del = useMutation({
    mutationFn: (tid: number) => api.deleteTrigger(org!, id!, tid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["triggers", org, id] }),
  });

  if (!kpatch) return null;
  return (
    <div className="space-y-6">
      <div>
        <Link
          to={`/o/${org}/kpatches`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← kpatches
        </Link>
        <h2 className="text-xl font-semibold mt-1">{kpatch.name}</h2>
        <code className="font-mono text-xs text-muted-foreground">{kpatch.id}</code>
        {kpatch.description && (
          <p className="text-sm text-muted-foreground mt-2">{kpatch.description}</p>
        )}
      </div>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Triggers</h3>
          <Button size="sm" onClick={() => setEditing({ mode: "create" })}>
            New trigger
          </Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Event</TableHead>
              <TableHead>prompt_contains</TableHead>
              <TableHead>path_match</TableHead>
              <TableHead>once</TableHead>
              <TableHead className="text-right w-32">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {triggers?.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground text-center">
                  No triggers yet — this kpatch won't fire.
                </TableCell>
              </TableRow>
            )}
            {triggers?.map((t) => (
              <TableRow key={t.id}>
                <TableCell className="font-mono text-xs">{t.event}</TableCell>
                <TableCell className="font-mono text-xs">
                  {t.prompt_contains?.join(", ") ?? "—"}
                </TableCell>
                <TableCell className="font-mono text-xs">{t.path_match ?? "—"}</TableCell>
                <TableCell className="text-xs">{t.once_per_session ? "yes" : "no"}</TableCell>
                <TableCell className="text-right space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setEditing({ mode: "edit", trigger: t })}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => confirm("Delete trigger?") && del.mutate(t.id)}
                  >
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>

      <section className="space-y-2">
        <h3 className="font-medium">Body</h3>
        <pre className="bg-muted/40 p-3 rounded text-xs overflow-auto whitespace-pre-wrap">
          {kpatch.body}
        </pre>
      </section>

      {editing && (
        <TriggerDialog
          org={org!}
          kpatchId={id!}
          editing={editing}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function TriggerDialog({
  org,
  kpatchId,
  editing,
  onClose,
}: {
  org: string;
  kpatchId: string;
  editing: Exclude<Editing, null>;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isCreate = editing.mode === "create";
  const t = isCreate ? null : editing.trigger;
  const [event, setEvent] = useState<Trigger["event"]>(t?.event ?? "user_prompt");
  const [pc, setPc] = useState(t?.prompt_contains?.join(", ") ?? "");
  const [pm, setPm] = useState(t?.path_match ?? "");
  const [once, setOnce] = useState(t?.once_per_session ?? false);
  const [err, setErr] = useState<string | null>(null);

  const body = () => ({
    event,
    prompt_contains:
      pc.trim()
        ? pc.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
    path_match: pm.trim() || null,
    once_per_session: once,
  });

  const save = useMutation({
    mutationFn: () =>
      isCreate
        ? api.createTrigger(org, kpatchId, body())
        : api.updateTrigger(org, kpatchId, t!.id, body()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["triggers", org, kpatchId] });
      onClose();
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isCreate ? "New trigger" : `Edit trigger #${t!.id}`}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="event">Event</Label>
            <select
              id="event"
              value={event}
              onChange={(e) => setEvent(e.target.value as Trigger["event"])}
              className="w-full border rounded p-2 text-sm bg-background"
            >
              <option value="session_start">session_start</option>
              <option value="user_prompt">user_prompt</option>
              <option value="pre_tool_use">pre_tool_use</option>
            </select>
          </div>
          {event === "user_prompt" && (
            <div className="space-y-1">
              <Label htmlFor="pc">prompt_contains (comma-separated)</Label>
              <Input id="pc" value={pc} onChange={(e) => setPc(e.target.value)} placeholder="commit, ship" />
            </div>
          )}
          <div className="space-y-1">
            <Label htmlFor="pm">path_match (glob)</Label>
            <Input
              id="pm"
              value={pm}
              onChange={(e) => setPm(e.target.value)}
              placeholder="services/payments/**"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={once}
              onChange={(e) => setOnce(e.target.checked)}
            />
            once_per_session
          </label>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button disabled={save.isPending} onClick={() => save.mutate()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
