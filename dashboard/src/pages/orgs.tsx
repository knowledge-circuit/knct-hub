import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
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

export function OrgsPage() {
  const { data } = useQuery({ queryKey: ["orgs"], queryFn: api.listOrgs });
  const [creating, setCreating] = useState(false);

  if (data && data.length === 1) {
    return <Navigate to={`/o/${data[0].id}/kpatches`} replace />;
  }

  return (
    <div className="mx-auto max-w-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Your orgs</h1>
        <Button onClick={() => setCreating(true)}>New org</Button>
      </div>
      {!data?.length && (
        <p className="text-muted-foreground text-sm">
          No orgs yet. Create one to get started.
        </p>
      )}
      <ul className="space-y-1">
        {data?.map((o) => (
          <li key={o.id}>
            <a
              href={`/o/${o.id}/kpatches`}
              className="block rounded border p-3 hover:bg-accent/50"
            >
              <div className="font-medium">{o.name}</div>
              <div className="text-xs text-muted-foreground font-mono">{o.id}</div>
            </a>
          </li>
        ))}
      </ul>
      {creating && <CreateDialog onClose={() => setCreating(false)} />}
    </div>
  );
}

function CreateDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: () => api.createOrg(id, name),
    onSuccess: (org) => {
      qc.invalidateQueries({ queryKey: ["orgs"] });
      onClose();
      navigate(`/o/${org.id}/kpatches`);
    },
    onError: (e: Error) => setErr(e.message),
  });
  useEffect(() => setErr(null), [id, name]);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New org</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="oid">ID (kebab-case)</Label>
            <Input id="oid" value={id} onChange={(e) => setId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="oname">Name</Label>
            <Input id="oname" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button disabled={!id || !name || m.isPending} onClick={() => m.mutate()}>
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
