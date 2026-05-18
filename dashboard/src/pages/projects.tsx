import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ProjectsPage() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });
  const [open, setOpen] = useState(false);
  const [slug, setSlug] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (s: string) => api.createProject(s),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setOpen(false);
      setSlug("");
      setErr(null);
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>New project</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create project</DialogTitle>
            </DialogHeader>
            <div className="space-y-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                placeholder="my-app"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
              />
              {err && <p className="text-sm text-destructive">{err}</p>}
            </div>
            <DialogFooter>
              <Button
                onClick={() => create.mutate(slug)}
                disabled={!slug || create.isPending}
              >
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {error && <p className="text-destructive">{(error as Error).message}</p>}

      <div className="border rounded-md divide-y">
        {data?.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">No projects yet.</div>
        )}
        {data?.map((p) => (
          <Link
            key={p.slug}
            to={`/p/${p.slug}/skills`}
            className="block p-4 hover:bg-accent/50"
          >
            <div className="font-medium">{p.slug}</div>
            <div className="text-xs text-muted-foreground">{p.created_at}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
