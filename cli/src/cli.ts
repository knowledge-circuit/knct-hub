import { mkdir, writeFile } from "node:fs/promises";
import { parseArgs } from "node:util";
import { basename, dirname, join } from "node:path";
import { input, select } from "@inquirer/prompts";
import TOML from "@iarna/toml";

type Project = { slug: string; created_at: string };

const SLUG_RE = /^[a-z0-9][a-z0-9-]*$/;
const DEFAULT_HUB = "http://localhost:8765";
const HOOK_EVENTS = [
  "SessionStart",
  "UserPromptSubmit",
  "PreToolUse",
  "PostToolUse",
  "Stop",
  "PostCompact",
];

function kebabize(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/^[^a-z0-9]/, "x")
    || "project";
}

async function fetchProjects(hubUrl: string): Promise<Project[]> {
  let res: Response;
  try {
    res = await fetch(`${hubUrl}/api/v1/projects`);
  } catch (err) {
    throw new Error(
      `Could not reach hub at ${hubUrl}. Is the server running? ` +
        `Pass --hub <url> or start it locally.`,
    );
  }
  if (!res.ok) {
    throw new Error(`Hub returned HTTP ${res.status} for GET /projects`);
  }
  return (await res.json()) as Project[];
}

async function createProject(hubUrl: string, slug: string): Promise<void> {
  const res = await fetch(`${hubUrl}/api/v1/projects`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ slug }),
  });
  if (res.status === 201) return;
  if (res.status === 409) {
    throw new Error(`Slug "${slug}" is already taken on this hub.`);
  }
  const detail = await res.text();
  throw new Error(`Hub rejected slug "${slug}" (HTTP ${res.status}): ${detail}`);
}

async function pickProject(
  projects: Project[],
  cwd: string,
  hubUrl: string,
): Promise<string> {
  const choices = [
    { name: "<Create new>", value: "__create__" },
    ...projects
      .map((p) => p.slug)
      .sort()
      .map((slug) => ({ name: slug, value: slug })),
  ];
  const choice = await select({
    message: "Pick a project on this hub",
    choices,
  });
  if (choice !== "__create__") return choice;

  while (true) {
    const slug = await input({
      message: "New project slug",
      default: kebabize(basename(cwd)),
      validate: (v) =>
        SLUG_RE.test(v) || "Use lowercase letters, digits, hyphens (start with letter/digit).",
    });
    try {
      await createProject(hubUrl, slug);
      return slug;
    } catch (err) {
      console.error(`  ${(err as Error).message}`);
    }
  }
}

async function writeKnctConfig(cwd: string, slug: string, hubUrl: string): Promise<string> {
  const path = join(cwd, ".knct", "config.toml");
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, TOML.stringify({ slug, hub_url: hubUrl }));
  return path;
}

async function writeClaudeSettings(
  cwd: string,
  slug: string,
  hubUrl: string,
): Promise<string> {
  const path = join(cwd, ".claude", "settings.json");
  await mkdir(dirname(path), { recursive: true });
  const hookEntry = {
    hooks: [
      {
        type: "http",
        url: `${hubUrl}/api/v1/hook`,
        headers: { "X-Project-Slug": slug },
      },
    ],
  };
  const settings = {
    hooks: Object.fromEntries(HOOK_EVENTS.map((e) => [e, [hookEntry]])),
  };
  await writeFile(path, JSON.stringify(settings, null, 2) + "\n");
  return path;
}

function printHelp(): void {
  console.log(`Usage: knct init [--hub <url>]

Link this repository to a knct-hub project.

Options:
  --hub <url>   Hub URL (default: prompted, fallback ${DEFAULT_HUB})
  -h, --help    Show this help
`);
}

async function main(): Promise<void> {
  const { values, positionals } = parseArgs({
    args: process.argv.slice(2),
    options: {
      hub: { type: "string" },
      help: { type: "boolean", short: "h" },
    },
    allowPositionals: true,
  });

  if (values.help) {
    printHelp();
    return;
  }
  const cmd = positionals[0];
  if (cmd !== "init") {
    printHelp();
    process.exit(cmd ? 1 : 0);
  }

  const hubUrl =
    values.hub ??
    (await input({ message: "Hub URL", default: DEFAULT_HUB })).replace(/\/+$/, "");
  const cwd = process.cwd();

  const projects = await fetchProjects(hubUrl);
  const slug = await pickProject(projects, cwd, hubUrl);

  const configPath = await writeKnctConfig(cwd, slug, hubUrl);
  const settingsPath = await writeClaudeSettings(cwd, slug, hubUrl);

  console.log(`
✓ Linked to project "${slug}" on ${hubUrl}
✓ Wrote ${configPath}
✓ Wrote ${settingsPath}

Restart Claude Code to pick up the new hooks.
`);
}

main().catch((err) => {
  console.error(`error: ${(err as Error).message}`);
  process.exit(1);
});
