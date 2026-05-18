import { Link, NavLink, Navigate, Route, Routes, useParams } from "react-router-dom";
import { ProjectsPage } from "@/pages/projects";
import { SkillsPage } from "@/pages/skills";
import { RulesPage } from "@/pages/rules";
import { TracesPage } from "@/pages/traces";

function ProjectLayout() {
  const { slug } = useParams<{ slug: string }>();
  const nav = [
    { to: `/p/${slug}/skills`, label: "Skills" },
    { to: `/p/${slug}/rules`, label: "Rules" },
    { to: `/p/${slug}/traces`, label: "Traces" },
  ];
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r p-4 space-y-1">
        <Link to="/" className="block text-sm text-muted-foreground mb-2 hover:underline">
          ← projects
        </Link>
        <div className="text-sm font-medium mb-2">{slug}</div>
        {nav.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `block px-2 py-1 rounded text-sm ${
                isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
              }`
            }
          >
            {n.label}
          </NavLink>
        ))}
      </aside>
      <main className="flex-1 p-6">
        <Routes>
          <Route index element={<Navigate to="skills" replace />} />
          <Route path="skills" element={<SkillsPage />} />
          <Route path="rules" element={<RulesPage />} />
          <Route path="traces" element={<TracesPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ProjectsPage />} />
      <Route path="/p/:slug/*" element={<ProjectLayout />} />
    </Routes>
  );
}
