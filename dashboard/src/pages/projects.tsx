import { useState } from "react";
import { Link, useParams } from "react-router-dom";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function ProjectsPage() {
  const { org } = useParams<{ org: string }>();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["projects", org],
    queryFn: () => api.listProjects(org!),
    enabled: !!org,
  });
  const [creating, setCreating] = useState(false);
  const [slug, setSlug] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => api.createProject(org!, slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", org] });
      setSlug("");
      setCreating(false);
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Projects</h2>
        <Button onClick={() => setCreating(true)}>New project</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Slug</TableHead>
            <TableHead>Access</TableHead>
            <TableHead>Members</TableHead>
            <TableHead>Bundles</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-muted-foreground text-center">
                No projects yet.
              </TableCell>
            </TableRow>
          )}
          {data?.map((p) => (
            <TableRow key={p.slug}>
              <TableCell className="font-mono text-xs">
                <Link
                  to={`/o/${org}/projects/${p.slug}`}
                  className="hover:underline"
                >
                  {p.slug}
                </Link>
              </TableCell>
              <TableCell className="text-xs">{p.access_mode}</TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {p.members.length}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {p.attached_bundles.length}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {p.created_at.slice(0, 10)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {creating && (
        <Dialog open onOpenChange={(o) => !o && setCreating(false)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New project</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="ps">Slug</Label>
                <Input
                  id="ps"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                />
              </div>
              {err && <p className="text-sm text-destructive">{err}</p>}
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setCreating(false)}>
                Cancel
              </Button>
              <Button
                disabled={!slug || create.isPending}
                onClick={() => create.mutate()}
              >
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
