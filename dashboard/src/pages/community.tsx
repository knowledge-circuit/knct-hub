import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function CommunityPage() {
  const { org } = useParams<{ org: string }>();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["community-bundles"],
    queryFn: api.listCommunityBundles,
  });
  const importBundle = useMutation({
    mutationFn: (id: string) => api.importCommunityBundle(org!, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bundles", org] });
      qc.invalidateQueries({ queryKey: ["kpatches", org] });
    },
  });

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Community library</h2>
      <p className="text-sm text-muted-foreground">
        Public bundles available to import into <code className="font-mono">{org}</code>.
        Imports create a private copy in your org — future updates to the source do not
        propagate.
      </p>
      {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {!isLoading && !data?.length && (
        <p className="text-sm text-muted-foreground">
          No community bundles yet. (Backend endpoint lands in a later change.)
        </p>
      )}
      <ul className="space-y-2">
        {data?.map((b) => (
          <li
            key={b.id}
            className="border rounded p-3 flex items-center justify-between"
          >
            <div>
              <div className="font-medium">{b.name}</div>
              <code className="font-mono text-xs text-muted-foreground">
                {b.id} · v{b.version} · {b.kpatch_ids.length} kpatches
              </code>
            </div>
            <Button
              size="sm"
              disabled={importBundle.isPending}
              onClick={() => importBundle.mutate(b.id)}
            >
              Import
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
