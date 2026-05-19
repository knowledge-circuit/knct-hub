import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Kpatch } from "@/lib/api";
import { parseKpatchMd, type ParsedKpatch } from "@/lib/kpatch-import";
import { KpatchImportDialog } from "@/components/kpatch-import-dialog";
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

type Editing = { mode: "create" } | { mode: "edit"; kpatch: Kpatch } | null;

export function KpatchesPage() {
  const { org } = useParams<{ org: string }>();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["kpatches", org],
    queryFn: () => api.listKpatches(org!),
    enabled: !!org,
  });
  const [editing, setEditing] = useState<Editing>(null);
  const [parsed, setParsed] = useState<ParsedKpatch | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const del = useMutation({
    mutationFn: (id: string) => api.deleteKpatch(org!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kpatches", org] }),
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Kpatches</h2>
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
            Import
          </Button>
          <Button onClick={() => setEditing({ mode: "create" })}>New kpatch</Button>
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
        className={`border-2 border-dashed rounded-md p-4 text-sm transition-colors ${
          dragOver ? "border-primary bg-accent/40" : "border-border"
        }`}
      >
        <p className="text-muted-foreground">
          Drop a <code className="font-mono">.md</code> file here, or click{" "}
          <span className="font-medium">Import</span>. The file must start with a YAML
          frontmatter block containing <code className="font-mono">id</code> and{" "}
          <code className="font-mono">name</code>. Optional <code className="font-mono">trigger</code>{" "}
          block creates a default trigger.
        </p>
        {importError && <p className="mt-2 text-destructive">{importError}</p>}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Keywords</TableHead>
            <TableHead className="w-40 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-muted-foreground text-center">
                No kpatches yet.
              </TableCell>
            </TableRow>
          )}
          {data?.map((k) => (
            <TableRow key={k.id}>
              <TableCell className="font-mono text-xs">
                <Link
                  to={`/o/${org}/kpatches/${k.id}`}
                  className="hover:underline"
                >
                  {k.id}
                </Link>
              </TableCell>
              <TableCell>{k.name}</TableCell>
              <TableCell className="text-muted-foreground text-xs">
                {k.keywords.join(", ")}
              </TableCell>
              <TableCell className="text-right space-x-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditing({ mode: "edit", kpatch: k })}
                >
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => confirm(`Delete ${k.id}?`) && del.mutate(k.id)}
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {editing && (
        <KpatchDialog
          org={org!}
          editing={editing}
          onClose={() => setEditing(null)}
        />
      )}
      {parsed && (
        <KpatchImportDialog
          org={org!}
          parsed={parsed}
          onClose={() => setParsed(null)}
        />
      )}
    </div>
  );
}

function KpatchDialog({
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
  const k = isCreate ? null : editing.kpatch;
  const [id, setId] = useState(k?.id ?? "");
  const [name, setName] = useState(k?.name ?? "");
  const [description, setDescription] = useState(k?.description ?? "");
  const [body, setBody] = useState(k?.body ?? "");
  const [keywords, setKeywords] = useState(k?.keywords.join(", ") ?? "");
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      api.upsertKpatch(org, id, {
        name,
        description: description || null,
        body,
        keywords: keywords.split(",").map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpatches", org] });
      onClose();
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {isCreate ? "New kpatch" : `Edit ${k!.id}`}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="id">ID</Label>
            <Input
              id="id"
              value={id}
              onChange={(e) => setId(e.target.value)}
              disabled={!isCreate}
              placeholder="commit-conventions"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="desc">Description</Label>
            <Input
              id="desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="kw">Keywords (comma-separated)</Label>
            <Input
              id="kw"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="git, commit"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="body">Body (markdown)</Label>
            <textarea
              id="body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="w-full min-h-48 border rounded-md p-2 font-mono text-sm"
            />
          </div>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter>
          <Button
            disabled={!id || !name || !body || save.isPending}
            onClick={() => save.mutate()}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
