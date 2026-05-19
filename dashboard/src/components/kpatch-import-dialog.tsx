import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ParsedKpatch } from "@/lib/kpatch-import";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type Props = {
  org: string;
  parsed: ParsedKpatch;
  onClose: () => void;
};

export function KpatchImportDialog({ org, parsed, onClose }: Props) {
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => api.importKpatch(org, parsed.source),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpatches", org] });
      qc.invalidateQueries({ queryKey: ["triggers", org, parsed.id] });
      onClose();
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="!max-w-3xl w-[min(48rem,90vw)]">
        <DialogHeader>
          <DialogTitle>Import kpatch — preview</DialogTitle>
        </DialogHeader>
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-muted-foreground">id:</span>{" "}
            <code className="font-mono">{parsed.id}</code>
          </div>
          <div>
            <span className="text-muted-foreground">name:</span> {parsed.name}
          </div>
          {parsed.description && (
            <div>
              <span className="text-muted-foreground">description:</span>{" "}
              {parsed.description}
            </div>
          )}
          {parsed.keywords.length > 0 && (
            <div>
              <span className="text-muted-foreground">keywords:</span>{" "}
              <span className="font-mono text-xs">
                {parsed.keywords.join(", ")}
              </span>
            </div>
          )}
          {parsed.trigger && (
            <div className="border rounded p-2 bg-muted/30">
              <div className="font-medium">Default trigger</div>
              <div className="text-xs font-mono">
                event: {parsed.trigger.event}
                {parsed.trigger.prompt_contains && (
                  <>
                    <br />
                    prompt_contains: [
                    {parsed.trigger.prompt_contains.join(", ")}]
                  </>
                )}
                {parsed.trigger.path_match && (
                  <>
                    <br />
                    path_match: {parsed.trigger.path_match}
                  </>
                )}
              </div>
            </div>
          )}
          <details>
            <summary className="cursor-pointer text-xs text-muted-foreground">
              body ({parsed.body.length} chars)
            </summary>
            <pre className="bg-muted/40 p-2 rounded overflow-auto max-h-72 text-xs whitespace-pre-wrap break-words">
              {parsed.body}
            </pre>
          </details>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={save.isPending} onClick={() => save.mutate()}>
            Import
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
