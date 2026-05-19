import YAML from "yaml";

export type ParsedSkill = {
  id: string;
  name: string;
  description: string | null;
  keywords: string[];
  body: string;
};

export type ParseResult =
  | { ok: true; skill: ParsedSkill }
  | { ok: false; error: string };

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/;

function asString(v: unknown): string {
  if (typeof v === "string") return v;
  if (v == null) return "";
  return String(v);
}

export function parseSkillMd(text: string): ParseResult {
  const match = text.match(FRONTMATTER_RE);
  if (!match) {
    return {
      ok: false,
      error:
        "Missing frontmatter. The file must begin with `---`, contain YAML, then close with `---` on its own line.",
    };
  }

  const [, raw, body] = match;
  let parsed: unknown;
  try {
    parsed = YAML.parse(raw);
  } catch (err) {
    return { ok: false, error: `YAML parse error: ${(err as Error).message}` };
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, error: "Frontmatter must be a YAML mapping (key: value pairs)." };
  }

  const fm = parsed as Record<string, unknown>;
  const id = asString(fm.id).trim();
  const name = asString(fm.name).trim();
  const description = fm.description == null ? null : asString(fm.description).trim() || null;

  const missing: string[] = [];
  if (!id) missing.push("id");
  if (!name) missing.push("name");

  const trimmedBody = body.trim();
  if (!trimmedBody) missing.push("body");

  if (missing.length) {
    return { ok: false, error: `Missing required field(s): ${missing.join(", ")}.` };
  }

  const rawKw = fm.keywords;
  let keywords: string[] = [];
  if (Array.isArray(rawKw)) {
    const seen = new Set<string>();
    for (const k of rawKw) {
      const s = asString(k).trim();
      if (s && !seen.has(s)) {
        seen.add(s);
        keywords.push(s);
      }
    }
  } else if (rawKw != null) {
    return {
      ok: false,
      error: "`keywords` must be a YAML list of strings if present.",
    };
  }

  return {
    ok: true,
    skill: { id, name, description, keywords, body: trimmedBody },
  };
}
