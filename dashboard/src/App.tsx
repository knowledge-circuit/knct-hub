import { Link, NavLink, Navigate, Route, Routes, useParams } from "react-router-dom";
import { OrgsPage } from "@/pages/orgs";
import { KpatchesPage } from "@/pages/kpatches";
import { KpatchDetailPage } from "@/pages/kpatch-detail";
import { ProjectsPage } from "@/pages/projects";
import { ProjectDetailPage } from "@/pages/project-detail";
import { ProjectKpatchesPage } from "@/pages/project-kpatches";
import { MembersPage } from "@/pages/members";
import { TracesPage } from "@/pages/traces";

function OrgLayout() {
  const { org } = useParams<{ org: string }>();
  const nav = [
    { to: `/o/${org}/kpatches`, label: "Kpatches" },
    { to: `/o/${org}/projects`, label: "Projects" },
    { to: `/o/${org}/members`, label: "Members" },
    { to: `/o/${org}/traces`, label: "Traces" },
  ];
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r p-4 space-y-1">
        <Link
          to="/"
          className="block text-sm text-muted-foreground mb-2 hover:underline"
        >
          ← orgs
        </Link>
        <div className="text-sm font-medium mb-2 font-mono">{org}</div>
        {nav.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `block px-2 py-1 rounded text-sm ${
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50"
              }`
            }
          >
            {n.label}
          </NavLink>
        ))}
      </aside>
      <main className="flex-1 p-6">
        <Routes>
          <Route index element={<Navigate to="kpatches" replace />} />
          <Route path="kpatches" element={<KpatchesPage />} />
          <Route path="kpatches/:id" element={<KpatchDetailPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:slug" element={<ProjectDetailPage />} />
          <Route path="projects/:slug/kpatches" element={<ProjectKpatchesPage />} />
          <Route path="members" element={<MembersPage />} />
          <Route path="traces" element={<TracesPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<OrgsPage />} />
      <Route path="/o/:org/*" element={<OrgLayout />} />
    </Routes>
  );
}
