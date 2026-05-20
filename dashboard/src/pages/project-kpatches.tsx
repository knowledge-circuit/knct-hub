import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ScopeRef } from "@/lib/api";
import { parseKpatchMd, type ParsedKpatch } from "@/lib/kpatch-import";
import { KpatchImportDialog } from "@/components/kpatch-import-dialog";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function ProjectKpatchesPage() {
  const { org, slug } = useParams<{ org: string; slug: string }>();
  const scope: ScopeRef = { org_id: org!, project_slug: slug };
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["kpatches", "project", org, slug],
    queryFn: () => api.listKpatches(scope, true),
    enabled: !!org && !!slug,
  });

  const [parsed, setParsed] = useState<ParsedKpatch | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const toggleDisable = useMutation({
    mutationFn: ({ slug: kslug, disable }: { slug: string; disable: boolean }) =>
      api.setDisable(scope, kslug, disable),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["kpatches", "project", org, slug] }),
  });

  const del = useMutation({
    mutationFn: (kslug: string) => api.deleteKpatch(scope, kslug),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["kpatches", "project", org, slug] }),
  });

  const handleFile = async (file: File) => {
    setImportError(null);
    if (!file.name.toLowerCase().endsWith(".md")) {
      setImportError("Only .md files are supported.");
      return;
    }
    const result = parseKpatchMd(await file.text());
    if (!result.ok) {
      setImportError(result.error);
      return;
    }
    setParsed(result.kpatch);
  };

  const rows = data ?? [];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Link
            to={`/o/${org}/projects/${slug}`}
            className="text-sm text-muted-foreground hover:underline"
          >
            ← project
          </Link>
          <h2 className="text-xl font-semibold">
            Kpatches for <code className="font-mono">{slug}</code>
          </h2>
          <p className="text-xs text-muted-foreground">
            Project-scope kpatches plus inherited from org. Toggle disable on
            an inherited row to suppress it just for this project.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".md,text/markdown"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
              e.target.value = "";
            }}
          />
          <Button variant="outline" onClick={() => fileRef.current?.click()}>
            Import (project)
          </Button>
        </div>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        className={`border-2 border-dashed rounded-md p-3 text-xs transition-colors ${
          dragOver ? "border-primary bg-accent/40" : "border-border"
        }`}
      >
        Drop a <code className="font-mono">.md</code> file to import at{" "}
        <span className="font-medium">project</span> scope.
        {importError && <p className="mt-2 text-destructive">{importError}</p>}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Slug</TableHead>
            <TableHead>Origin</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Disable</TableHead>
            <TableHead className="text-right w-32">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-muted-foreground text-center">
                No kpatches here yet (and nothing inherited).
              </TableCell>
            </TableRow>
          )}
          {rows.map((k) => {
            const isOwn = k.origin_scope === "project";
            const shadowed = k.shadowed_at_current && !isOwn;
            return (
              <TableRow
                key={`${k.origin_scope}-${k.slug}-${k.pk_id}`}
                className={shadowed ? "opacity-50" : ""}
              >
                <TableCell className="font-mono text-xs">{k.slug}</TableCell>
                <TableCell className="text-xs">
                  <span
                    className={
                      isOwn
                        ? "font-medium text-primary"
                        : "text-muted-foreground"
                    }
                  >
                    {k.origin_scope}
                  </span>
                  {shadowed && (
                    <span className="ml-1 text-muted-foreground">
                      (shadowed by project)
                    </span>
                  )}
                </TableCell>
                <TableCell>{k.name}</TableCell>
                <TableCell>
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={k.disable}
                      disabled={shadowed}
                      onChange={(e) =>
                        toggleDisable.mutate({
                          slug: k.slug,
                          disable: e.target.checked,
                        })
                      }
                    />
                    {k.disable ? "disabled" : "enabled"}
                  </label>
                </TableCell>
                <TableCell className="text-right">
                  {isOwn && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        confirm(`Delete project-scope ${k.slug}?`) && del.mutate(k.slug)
                      }
                    >
                      Delete
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {parsed && (
        <KpatchImportDialog
          scope={scope}
          parsed={parsed}
          onClose={() => setParsed(null)}
        />
      )}
    </div>
  );
}
