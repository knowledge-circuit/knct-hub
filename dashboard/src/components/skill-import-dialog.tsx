import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ParsedSkill } from "@/lib/skill-import";
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

type Props = {
  slug: string;
  parsed: ParsedSkill;
  onClose: () => void;
};

export function SkillImportDialog({ slug, parsed, onClose }: Props) {
  const qc = useQueryClient();
  const [id, setId] = useState(parsed.id);
  const [name, setName] = useState(parsed.name);
  const [description, setDescription] = useState(parsed.description ?? "");
  const [keywords, setKeywords] = useState(parsed.keywords.join(", "));
  const [body, setBody] = useState(parsed.body);
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

  const canSave = !!id.trim() && !!name.trim() && !!body.trim() && !save.isPending;

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Import skill — preview</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="import-id">ID</Label>
            <Input id="import-id" value={id} onChange={(e) => setId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="import-name">Name</Label>
            <Input id="import-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="import-desc">Description</Label>
            <Input
              id="import-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="import-kw">Keywords (comma-separated)</Label>
            <Input
              id="import-kw"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="import-body">Body (markdown)</Label>
            <textarea
              id="import-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="w-full min-h-48 border rounded-md p-2 font-mono text-sm"
            />
          </div>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!canSave} onClick={() => save.mutate()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
