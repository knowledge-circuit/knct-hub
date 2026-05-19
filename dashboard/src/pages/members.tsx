import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
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

export function MembersPage() {
  const { org } = useParams<{ org: string }>();
  const qc = useQueryClient();
  const { data: orgData } = useQuery({
    queryKey: ["org", org],
    queryFn: () => api.getOrg(org!),
    enabled: !!org,
  });
  const { data: members } = useQuery({
    queryKey: ["members", org],
    queryFn: () => api.listMembers(org!),
    enabled: !!org,
  });
  const { data: bundles } = useQuery({
    queryKey: ["bundles", org],
    queryFn: () => api.listBundles(org!),
    enabled: !!org,
  });

  const [defaults, setDefaults] = useState<string[]>([]);
  useEffect(() => {
    if (orgData) setDefaults(orgData.default_bundles);
  }, [orgData]);

  const saveDefaults = useMutation({
    mutationFn: () => api.setDefaultBundles(org!, defaults),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org", org] }),
  });

  const setRole = useMutation({
    mutationFn: ({ user, role }: { user: string; role: string }) =>
      api.setMemberRole(org!, user, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", org] }),
  });
  const remove = useMutation({
    mutationFn: (user: string) => api.removeMember(org!, user),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", org] }),
  });

  const [newUser, setNewUser] = useState("");
  const [newRole, setNewRole] = useState("member");

  const toggle = (id: string) =>
    setDefaults((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <div className="space-y-8 max-w-3xl">
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Members</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="text-right w-32">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members?.map((m) => (
              <TableRow key={m.user_id}>
                <TableCell className="font-mono text-xs">{m.user_id}</TableCell>
                <TableCell>
                  <select
                    value={m.role}
                    onChange={(e) =>
                      setRole.mutate({ user: m.user_id, role: e.target.value })
                    }
                    className="border rounded p-1 text-sm bg-background"
                  >
                    <option value="owner">owner</option>
                    <option value="admin">admin</option>
                    <option value="member">member</option>
                  </select>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => confirm("Remove?") && remove.mutate(m.user_id)}
                  >
                    Remove
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <div className="flex gap-2 items-end">
          <div className="flex-1 space-y-1">
            <Label htmlFor="nu">Add user id</Label>
            <Input id="nu" value={newUser} onChange={(e) => setNewUser(e.target.value)} />
          </div>
          <select
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
            className="border rounded p-2 text-sm bg-background h-9"
          >
            <option value="member">member</option>
            <option value="admin">admin</option>
            <option value="owner">owner</option>
          </select>
          <Button
            disabled={!newUser}
            onClick={() => {
              setRole.mutate({ user: newUser, role: newRole });
              setNewUser("");
            }}
          >
            Add
          </Button>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Default bundles</h2>
        <p className="text-xs text-muted-foreground">
          Bundles inherited by every project in this org, in order.
        </p>
        <div className="border rounded p-2 max-h-48 overflow-auto space-y-1">
          {bundles?.length === 0 && (
            <p className="text-xs text-muted-foreground">No bundles yet.</p>
          )}
          {bundles?.map((b) => (
            <label key={b.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={defaults.includes(b.id)}
                onChange={() => toggle(b.id)}
              />
              <code className="font-mono text-xs">{b.id}</code>
              <span className="text-muted-foreground">
                {b.name} ({b.version})
              </span>
            </label>
          ))}
        </div>
        <Button onClick={() => saveDefaults.mutate()} disabled={saveDefaults.isPending}>
          Save default bundles
        </Button>
      </section>
    </div>
  );
}
