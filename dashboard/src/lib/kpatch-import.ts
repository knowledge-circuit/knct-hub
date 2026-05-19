import { parse as parseYaml } from "yaml";

export type ParsedKpatch = {
  id: string;
  name: string;
  description: string | null;
  keywords: string[];
  body: string;
  trigger: {
    event: "session_start" | "user_prompt" | "pre_tool_use";
    prompt_contains: string[] | null;
    path_match: string | null;
    once_per_session: boolean | null;
  } | null;
  /** Raw markdown source — sent to the server importer as-is. */
  source: string;
};

export type ParseResult =
  | { ok: true; kpatch: ParsedKpatch }
  | { ok: false; error: string };

const VALID_EVENTS = new Set([
  "session_start",
  "user_prompt",
  "pre_tool_use",
]);

export function parseKpatchMd(text: string): ParseResult {
  const lines = text.split("\n");
  if (lines[0]?.trim() !== "---") {
    return { ok: false, error: "Missing frontmatter (file must start with '---')." };
  }
  let endIdx = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      endIdx = i;
      break;
    }
  }
  if (endIdx === -1) {
    return { ok: false, error: "Unterminated frontmatter (no closing '---')." };
  }
  const fmText = lines.slice(1, endIdx).join("\n");
  const body = lines.slice(endIdx + 1).join("\n").replace(/^\n+/, "");
  let fm: Record<string, unknown>;
  try {
    fm = (parseYaml(fmText) ?? {}) as Record<string, unknown>;
  } catch (e) {
    return { ok: false, error: `Invalid YAML: ${(e as Error).message}` };
  }
  if (typeof fm !== "object" || Array.isArray(fm)) {
    return { ok: false, error: "Frontmatter must be a YAML mapping." };
  }

  const id = typeof fm.id === "string" ? fm.id.trim() : "";
  const name = typeof fm.name === "string" ? fm.name.trim() : "";
  if (!id) return { ok: false, error: "Missing 'id' in frontmatter." };
  if (!name) return { ok: false, error: "Missing 'name' in frontmatter." };

  const description =
    typeof fm.description === "string" ? fm.description : null;

  const keywords: string[] = [];
  const seen = new Set<string>();
  if (Array.isArray(fm.keywords)) {
    for (const k of fm.keywords) {
      if (typeof k !== "string") continue;
      const v = k.trim();
      if (!v || seen.has(v)) continue;
      seen.add(v);
      keywords.push(v);
    }
  }

  let trigger: ParsedKpatch["trigger"] = null;
  if (fm.trigger && typeof fm.trigger === "object") {
    const t = fm.trigger as Record<string, unknown>;
    const event = typeof t.event === "string" ? t.event : "";
    if (!VALID_EVENTS.has(event)) {
      return { ok: false, error: `trigger.event invalid: '${event}'` };
    }
    const pc = Array.isArray(t.prompt_contains)
      ? (t.prompt_contains.filter((s) => typeof s === "string") as string[])
      : null;
    const pm = typeof t.path_match === "string" ? t.path_match : null;
    const once =
      typeof t.once_per_session === "boolean" ? t.once_per_session : null;
    trigger = {
      event: event as NonNullable<ParsedKpatch["trigger"]>["event"],
      prompt_contains: pc,
      path_match: pm,
      once_per_session: once,
    };
  }

  return {
    ok: true,
    kpatch: { id, name, description, keywords, body, trigger, source: text },
  };
}
