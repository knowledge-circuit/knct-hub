import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Bundle } from "@/lib/api";
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

type Editing = { mode: "create" } | { mode: "edit"; bundle: Bundle } | null;

export function BundlesPage() {
  const { org } = useParams<{ org: string }>();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["bundles", org],
    queryFn: () => api.listBundles(org!),
    enabled: !!org,
  });
  const [editing, setEditing] = useState<Editing>(null);

  const del = useMutation({
    mutationFn: (id: string) => api.deleteBundle(org!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bundles", org] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Bundles</h2>
        <Button onClick={() => setEditing({ mode: "create" })}>New bundle</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Version</TableHead>
            <TableHead>Kpatches</TableHead>
            <TableHead className="w-40 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-muted-foreground text-center">
                No bundles yet.
              </TableCell>
            </TableRow>
          )}
          {data?.map((b) => (
            <TableRow key={b.id}>
              <TableCell className="font-mono text-xs">{b.id}</TableCell>
              <TableCell>{b.name}</TableCell>
              <TableCell className="font-mono text-xs">{b.version}</TableCell>
              <TableCell className="text-muted-foreground text-xs">
                {b.kpatch_ids.length} ({b.kpatch_ids.slice(0, 3).join(", ")}
                {b.kpatch_ids.length > 3 ? "…" : ""})
              </TableCell>
              <TableCell className="text-right space-x-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditing({ mode: "edit", bundle: b })}
                >
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => confirm(`Delete ${b.id}?`) && del.mutate(b.id)}
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {editing && (
        <BundleDialog org={org!} editing={editing} onClose={() => setEditing(null)} />
      )}
    </div>
  );
}

function BundleDialog({
  org,
  editing,
  onClose,
}: {
  org: string;
  editing: Exclude<Editing, null>;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const isCreate = editing.mode === "create";
  const b = isCreate ? null : editing.bundle;
  const { data: kpatches } = useQuery({
    queryKey: ["kpatches", org],
    queryFn: () => api.listKpatches(org),
  });

  const [id, setId] = useState(b?.id ?? "");
  const [name, setName] = useState(b?.name ?? "");
  const [version, setVersion] = useState(b?.version ?? "1.0.0");
  const [selected, setSelected] = useState<string[]>(b?.kpatch_ids ?? []);
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      api.upsertBundle(org, id, { name, version, kpatch_ids: selected }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bundles", org] });
      onClose();
    },
    onError: (e: Error) => setErr(e.message),
  });

  const toggle = (kid: string) =>
    setSelected((s) => (s.includes(kid) ? s.filter((x) => x !== kid) : [...s, kid]));

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{isCreate ? "New bundle" : `Edit ${b!.id}`}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="bid">ID</Label>
            <Input
              id="bid"
              value={id}
              onChange={(e) => setId(e.target.value)}
              disabled={!isCreate}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="bname">Name</Label>
            <Input id="bname" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="bver">Version (semver, must increase)</Label>
            <Input
              id="bver"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="1.0.0"
            />
          </div>
          <div className="space-y-1">
            <Label>Kpatches in bundle (ordered)</Label>
            <div className="border rounded p-2 max-h-48 overflow-auto space-y-1">
              {kpatches?.length === 0 && (
                <p className="text-xs text-muted-foreground">No kpatches in this org.</p>
              )}
              {kpatches?.map((k) => (
                <label
                  key={k.id}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(k.id)}
                    onChange={() => toggle(k.id)}
                  />
                  <code className="font-mono text-xs">{k.id}</code>
                  <span className="text-muted-foreground">— {k.name}</span>
                </label>
              ))}
            </div>
            {selected.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Order: {selected.join(", ")}
              </p>
            )}
          </div>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button
            disabled={!id || !name || !version || save.isPending}
            onClick={() => save.mutate()}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
