import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Rule } from "@/lib/api";
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

type Editing = { mode: "create" } | { mode: "edit"; rule: Rule } | null;

const EVENTS = ["session_start", "user_prompt_submit", "pre_edit", "pre_read"];

export function RulesPage() {
  const { slug } = useParams<{ slug: string }>();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["rules", slug],
    queryFn: () => api.listRules(slug!),
    enabled: !!slug,
  });
  const [editing, setEditing] = useState<Editing>(null);

  const del = useMutation({
    mutationFn: (id: number) => api.deleteRule(slug!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules", slug] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Rules</h2>
        <Button onClick={() => setEditing({ mode: "create" })}>New rule</Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>Event</TableHead>
            <TableHead>Match</TableHead>
            <TableHead>Inject</TableHead>
            <TableHead className="w-20">Once</TableHead>
            <TableHead className="w-32 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-muted-foreground text-center">
                No rules yet.
              </TableCell>
            </TableRow>
          )}
          {data?.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="font-mono text-xs">{r.id}</TableCell>
              <TableCell className="font-mono text-xs">{r.on_event}</TableCell>
              <TableCell className="font-mono text-xs">{r.match ?? "—"}</TableCell>
              <TableCell className="text-xs">{r.inject.join(", ")}</TableCell>
              <TableCell className="text-xs">{r.once_per_session ? "✓" : ""}</TableCell>
              <TableCell className="text-right space-x-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditing({ mode: "edit", rule: r })}
                >
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => confirm(`Delete rule #${r.id}?`) && del.mutate(r.id)}
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {editing && (
        <RuleDialog
          slug={slug!}
          editing={editing}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function RuleDialog({
  slug,
  editing,
  onClose,
}: {
  slug: string;
  editing: Exclude<Editing, null>;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isCreate = editing.mode === "create";
  const initial = isCreate ? null : editing.rule;
  const [onEvent, setOnEvent] = useState(initial?.on_event ?? "pre_edit");
  const [match, setMatch] = useState(initial?.match ?? "");
  const [inject, setInject] = useState(initial?.inject.join(", ") ?? "");
  const [oncePerSession, setOnce] = useState<boolean | null>(
    initial ? initial.once_per_session : null,
  );
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => {
      const body = {
        on_event: onEvent,
        match: match || null,
        inject: inject
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        once_per_session: oncePerSession ?? onEvent === "pre_read",
      };
      return isCreate
        ? api.createRule(slug, body)
        : api.updateRule(slug, editing.rule.id, body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rules", slug] });
      onClose();
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isCreate ? "New rule" : `Edit rule #${editing.rule.id}`}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="on">Event</Label>
            <select
              id="on"
              className="w-full border rounded-md h-9 px-2 text-sm"
              value={onEvent}
              onChange={(e) => setOnEvent(e.target.value)}
            >
              {EVENTS.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="match">Match (glob, optional)</Label>
            <Input
              id="match"
              value={match}
              onChange={(e) => setMatch(e.target.value)}
              placeholder="*payments*"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="inject">Inject skill ids (comma-separated)</Label>
            <Input
              id="inject"
              value={inject}
              onChange={(e) => setInject(e.target.value)}
              placeholder="payments, fastapi-style"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="once"
              checked={
                oncePerSession ?? (onEvent === "pre_read")
              }
              onChange={(e) => setOnce(e.target.checked)}
            />
            <Label htmlFor="once" className="text-sm font-normal">
              Once per session (default on for pre_read)
            </Label>
          </div>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter>
          <Button disabled={!inject || save.isPending} onClick={() => save.mutate()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
