import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Skill } from "@/lib/api";
import { parseSkillMd, type ParsedSkill } from "@/lib/skill-import";
import { SkillImportDialog } from "@/components/skill-import-dialog";
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

type Editing =
  | { mode: "create" }
  | { mode: "edit"; skill: Skill }
  | null;

export function SkillsPage() {
  const { slug } = useParams<{ slug: string }>();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["skills", slug],
    queryFn: () => api.listSkills(slug!),
    enabled: !!slug,
  });
  const [editing, setEditing] = useState<Editing>(null);
  const [imported, setImported] = useState<ParsedSkill | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const del = useMutation({
    mutationFn: (id: string) => api.deleteSkill(slug!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["skills", slug] }),
  });

  const handleFile = async (file: File) => {
    setImportError(null);
    if (!file.name.toLowerCase().endsWith(".md")) {
      setImportError("Only .md files are supported.");
      return;
    }
    const text = await file.text();
    const result = parseSkillMd(text);
    if (!result.ok) {
      setImportError(result.error);
      return;
    }
    setImported(result.skill);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Skills</h2>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".md,text/markdown"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
              e.target.value = "";
            }}
          />
          <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
            Import
          </Button>
          <Button onClick={() => setEditing({ mode: "create" })}>New skill</Button>
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
          <code className="font-mono">name</code>.
        </p>
        {importError && <p className="mt-2 text-destructive">{importError}</p>}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Keywords</TableHead>
            <TableHead className="w-32 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-muted-foreground text-center">
                No skills yet.
              </TableCell>
            </TableRow>
          )}
          {data?.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-mono text-xs">{s.id}</TableCell>
              <TableCell>{s.name}</TableCell>
              <TableCell className="text-muted-foreground text-xs">
                {s.keywords.join(", ")}
              </TableCell>
              <TableCell className="text-right space-x-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditing({ mode: "edit", skill: s })}
                >
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => confirm(`Delete ${s.id}?`) && del.mutate(s.id)}
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {editing && (
        <SkillDialog
          slug={slug!}
          editing={editing}
          onClose={() => setEditing(null)}
        />
      )}

      {imported && (
        <SkillImportDialog
          slug={slug!}
          parsed={imported}
          onClose={() => setImported(null)}
        />
      )}
    </div>
  );
}

function SkillDialog({
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
  const [id, setId] = useState(isCreate ? "" : editing.skill.id);
  const [name, setName] = useState(isCreate ? "" : editing.skill.name);
  const [description, setDescription] = useState(
    isCreate ? "" : editing.skill.description ?? "",
  );
  const [body, setBody] = useState(isCreate ? "" : editing.skill.body);
  const [keywords, setKeywords] = useState(
    isCreate ? "" : editing.skill.keywords.join(", "),
  );
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      api.upsertSkill(slug, id, {
        name,
        description: description || null,
        body,
        keywords: keywords
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills", slug] });
      onClose();
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{isCreate ? "New skill" : `Edit ${editing.skill.id}`}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="id">ID</Label>
            <Input
              id="id"
              value={id}
              onChange={(e) => setId(e.target.value)}
              disabled={!isCreate}
              placeholder="payments"
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
              placeholder="payment, retry"
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
