import { mkdir, readFile, writeFile, chmod } from "node:fs/promises";
import { existsSync } from "node:fs";
import { parseArgs } from "node:util";
import { basename, dirname, join } from "node:path";
import { checkbox } from "@inquirer/prompts";
import TOML from "@iarna/toml";

import INJECT_PY from "../assets/inject.py";
import STATUSLINE_SH from "../assets/statusline.sh";
import { BUNDLED_KPATCHES } from "./kpatches.generated";

const INJECT_REL = ".knct/hooks/inject.py";
const STATUSLINE_REL = ".knct/bin/statusline.sh";
const KPATCH_DIR_REL = ".knct/kpatches";

type Frontmatter = Record<string, string>;

function parseFrontmatter(raw: string): { meta: Frontmatter; body: string } {
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) return { meta: {}, body: raw };
  const meta: Frontmatter = {};
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([A-Za-z_][\w-]*)\s*:\s*(.*)$/);
    if (!kv) continue;
    meta[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, "");
  }
  return { meta, body: m[2] };
}

function kebabize(s: string): string {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/^[^a-z0-9]/, "x") || "project"
  );
}

async function writeAsset(cwd: string, rel: string, body: string, exec = false): Promise<string> {
  const path = join(cwd, rel);
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, body);
  if (exec) await chmod(path, 0o755);
  return path;
}

async function writeKnctConfig(cwd: string, slug: string): Promise<string> {
  const path = join(cwd, ".knct", "config.toml");
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, TOML.stringify({ slug }));
  return path;
}

type Settings = {
  hooks?: Record<string, unknown[]>;
  statusLine?: unknown;
  [k: string]: unknown;
};

async function mergeClaudeSettings(cwd: string): Promise<string> {
  const path = join(cwd, ".claude", "settings.json");
  await mkdir(dirname(path), { recursive: true });

  let settings: Settings = {};
  if (existsSync(path)) {
    try {
      settings = JSON.parse(await readFile(path, "utf-8")) as Settings;
    } catch {
      // unparseable -> start fresh, but back up
      await writeFile(path + ".bak", await readFile(path, "utf-8"));
      settings = {};
    }
  }

  const hooks = (settings.hooks ??= {});
  const ups = ((hooks.UserPromptSubmit ??= []) as Array<Record<string, unknown>>).filter(
    (entry) => !isKnctInjectEntry(entry),
  );
  ups.push({
    hooks: [{ type: "command", command: `$CLAUDE_PROJECT_DIR/${INJECT_REL}` }],
  });
  hooks.UserPromptSubmit = ups;

  settings.statusLine = {
    type: "command",
    command: `$CLAUDE_PROJECT_DIR/${STATUSLINE_REL}`,
  };

  await writeFile(path, JSON.stringify(settings, null, 2) + "\n");
  return path;
}

function isKnctInjectEntry(entry: Record<string, unknown>): boolean {
  const hooks = entry?.hooks as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(hooks)) return false;
  return hooks.some((h) => {
    const cmd = typeof h?.command === "string" ? h.command : "";
    return cmd.includes(INJECT_REL);
  });
}

async function pickKpatches(): Promise<typeof BUNDLED_KPATCHES> {
  if (BUNDLED_KPATCHES.length === 0) return [];
  const choices = BUNDLED_KPATCHES.map((k) => {
    const { meta } = parseFrontmatter(k.body);
    const id = meta.id || k.filename.replace(/\.md$/, "");
    const name = meta.name || id;
    return {
      name,
      value: k.filename,
      description: meta.description,
      checked: false,
    };
  });
  const picked = await checkbox({
    message: "Pick starter kpatches to install",
    instructions: " (space to select, a to toggle all, enter to confirm)",
    choices,
    pageSize: Math.min(choices.length, 20),
  });
  return BUNDLED_KPATCHES.filter((k) => picked.includes(k.filename));
}

async function writeKpatches(
  cwd: string,
  kpatches: typeof BUNDLED_KPATCHES,
  { overwrite }: { overwrite: boolean },
): Promise<string[]> {
  const written: string[] = [];
  for (const k of kpatches) {
    const path = join(cwd, KPATCH_DIR_REL, k.filename);
    if (!overwrite && existsSync(path)) continue;
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, k.body);
    written.push(path);
  }
  return written;
}

async function cmdInit(): Promise<void> {
  const cwd = process.cwd();
  const slug = kebabize(basename(cwd));

  const picked = await pickKpatches();

  const configPath = await writeKnctConfig(cwd, slug);
  const injectPath = await writeAsset(cwd, INJECT_REL, INJECT_PY, true);
  const statuslinePath = await writeAsset(cwd, STATUSLINE_REL, STATUSLINE_SH, true);
  const kpatchPaths = await writeKpatches(cwd, picked, { overwrite: false });
  await mkdir(join(cwd, KPATCH_DIR_REL), { recursive: true });
  const settingsPath = await mergeClaudeSettings(cwd);

  console.log(`
✓ Wrote ${configPath}
✓ Wrote ${injectPath}
✓ Wrote ${statuslinePath}
✓ Wrote ${settingsPath}${
    kpatchPaths.length
      ? "\n✓ Installed kpatches:\n  " + kpatchPaths.join("\n  ")
      : "\n(no starter kpatches installed — add your own to .knct/kpatches/)"
  }

Restart Claude Code to pick up the new hooks.
`);
}

async function cmdUpgrade(): Promise<void> {
  const cwd = process.cwd();
  const injectPath = await writeAsset(cwd, INJECT_REL, INJECT_PY, true);
  const statuslinePath = await writeAsset(cwd, STATUSLINE_REL, STATUSLINE_SH, true);
  console.log(`✓ Refreshed ${injectPath}\n✓ Refreshed ${statuslinePath}`);
}

async function cmdKpatchAdd(): Promise<void> {
  const cwd = process.cwd();
  const picked = await pickKpatches();
  const written = await writeKpatches(cwd, picked, { overwrite: false });
  if (written.length === 0) {
    console.log("Nothing added (selected files already exist or no picks).");
    return;
  }
  console.log("✓ Installed:\n  " + written.join("\n  "));
}

function printHelp(): void {
  console.log(`Usage: knct <command>

Commands:
  init           Set up .knct/ in this repo and wire Claude Code hooks
  upgrade        Refresh bundled inject.py and statusline.sh
  kpatch add     Pick from the bundled kpatch library and install

Options:
  -h, --help     Show this help
`);
}

async function main(): Promise<void> {
  const { values, positionals } = parseArgs({
    args: process.argv.slice(2),
    options: { help: { type: "boolean", short: "h" } },
    allowPositionals: true,
    strict: false,
  });

  if (values.help) {
    printHelp();
    return;
  }

  const [cmd, sub] = positionals;
  if (cmd === "init") return cmdInit();
  if (cmd === "upgrade") return cmdUpgrade();
  if (cmd === "kpatch" && sub === "add") return cmdKpatchAdd();

  printHelp();
  process.exit(cmd ? 1 : 0);
}

main().catch((err) => {
  console.error(`error: ${(err as Error).message}`);
  process.exit(1);
});
