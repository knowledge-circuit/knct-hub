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

  const [accessMode, setAccessMode] = useState<"org" | "invite_only">("org");
  const [members, setMembers] = useState("");

  useEffect(() => {
    if (project) {
      setAccessMode(project.access_mode);
      setMembers(project.members.join(", "));
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

  if (!project) return null;
  return (
    <div className="space-y-8 max-w-3xl">
      <div className="flex items-end justify-between">
        <div>
          <Link
            to={`/o/${org}/projects`}
            className="text-sm text-muted-foreground hover:underline"
          >
            ← projects
          </Link>
          <h2 className="text-xl font-semibold mt-1 font-mono">{project.slug}</h2>
        </div>
        <Link
          to={`/o/${org}/projects/${project.slug}/kpatches`}
          className="text-sm underline"
        >
          Project kpatches →
        </Link>
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
    </div>
  );
}
