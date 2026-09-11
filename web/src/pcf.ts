import { uid } from "./math";
import type { ProjectDoc, TreeItem } from "./types";

interface PcfComp {
  type: string;
  points: { x: number; y: number; z: number; bore?: number }[];
  center?: { x: number; y: number; z: number };
  skey?: string;
  code?: string;
  description?: string;
  spec?: string;
}

function num(item: TreeItem, key: string, fallback = 0): number {
  const value = item.props[key];
  return typeof value === "number" ? value : Number(value ?? fallback) || fallback;
}

function str(item: TreeItem, key: string, fallback = ""): string {
  const value = item.props[key];
  return typeof value === "string" ? value : String(value ?? fallback);
}

export function exportPcf(doc: ProjectDoc, pipeId?: string): string {
  const pipes = doc.items.filter(
    (it) => it.type === "PIPE" && (!pipeId || it.id === pipeId || it.name === pipeId),
  );
  const target = pipes[0];
  const lines: string[] = [
    "ISOGEN-FILES   ISOGEN.FLS",
    "UNITS-BORE   MM",
    "UNITS-CO-ORDS   MM",
    "UNITS-BOLT-LENGTH   MM",
    "UNITS-BOLT-DIA   MM",
    "UNITS-WEIGHT  KGS",
    `PIPELINE-REFERENCE   ${target?.name ?? doc.name}`,
    `    PIPING-SPEC   ${target ? str(target, "spec", doc.spec) : doc.spec}`,
    "    INSULATION-SPEC   ",
    "    PAINTING-SPEC   ",
    "    TRACING-SPEC   ",
  ];

  const codes = new Map<string, string>();
  const components = doc.items.filter((it) =>
    ["TUBE", "ELBO", "VALV", "FLAN", "REDU", "TEE", "CAP"].includes(it.type),
  );

  const scoped = target
    ? components.filter((it) => belongsTo(doc, it.id, target.id))
    : components;

  for (const it of scoped) {
    const type = pcfType(it);
    lines.push(type);
    if (it.type === "FLAN") {
      lines.push(
        `    END-POINT    ${fmt(num(it, "x"))} ${fmt(num(it, "y"))} ${fmt(num(it, "z"))} ${num(it, "bore")}`,
      );
    } else if (it.type === "TEE") {
      lines.push(endPoint(it, "x1", "y1", "z1"));
      lines.push(endPoint(it, "x2", "y2", "z2"));
      lines.push(
        `    CENTRE-POINT   ${fmt(num(it, "cx"))} ${fmt(num(it, "cy"))} ${fmt(num(it, "cz"))}`,
      );
      lines.push(endPoint(it, "x3", "y3", "z3", "BRANCH1-POINT"));
    } else {
      lines.push(endPoint(it, "x1", "y1", "z1"));
      lines.push(endPoint(it, "x2", "y2", "z2"));
      if (it.type === "ELBO") {
        lines.push(
          `    CENTRE-POINT   ${fmt(num(it, "cx"))} ${fmt(num(it, "cy"))} ${fmt(num(it, "cz"))}`,
        );
      }
    }
    lines.push(`    SKEY     ${str(it, "skey")}`);
    lines.push(`    PIPING-SPEC   ${str(it, "spec", doc.spec)}`);
    lines.push("    WEIGHT   ");
    const code = str(it, "skey") || it.type;
    const desc = str(it, "description", it.name);
    lines.push(`    ITEM-CODE   ${code}`);
    lines.push(`    ITEM-DESCRIPTION   ${desc}`);
    codes.set(code, desc);
  }

  lines.push("MATERIALS");
  for (const [code, desc] of codes) {
    lines.push(`ITEM-CODE    ${code}`);
    lines.push(`    DESCRIPTION    ${desc}`);
  }
  lines.push("");
  return lines.join("\n");
}

function belongsTo(doc: ProjectDoc, id: string, ancestorId: string): boolean {
  let cur = doc.items.find((it) => it.id === id);
  while (cur) {
    if (cur.id === ancestorId) return true;
    cur = doc.items.find((it) => it.id === cur?.parentId);
  }
  return false;
}

function pcfType(it: TreeItem): string {
  switch (it.type) {
    case "TUBE":
      return "PIPE";
    case "ELBO":
      return "ELBOW";
    case "VALV":
      return str(it, "kind") === "CHECK" ? "CHECK-VALVE" : "VALVE";
    case "FLAN":
      return "FLANGE";
    case "REDU":
      return "REDUCER-CONCENTRIC";
    case "TEE":
      return "TEE";
    case "CAP":
      return "CAP";
    default:
      return it.type;
  }
}

function endPoint(it: TreeItem, x: string, y: string, z: string, tag = "END-POINT"): string {
  return `    ${tag}    ${fmt(num(it, x))} ${fmt(num(it, y))} ${fmt(num(it, z))} ${num(it, "bore")}`;
}

function fmt(n: number): string {
  return String(Math.round(n * 100) / 100);
}

export function importPcf(text: string, name = "PCF-IMPORT"): ProjectDoc {
  const lines = text.replace(/\r/g, "").split("\n");
  const items: TreeItem[] = [];
  const world: TreeItem = {
    id: "world",
    type: "WORLD",
    name: "/*",
    parentId: null,
    visible: true,
    props: {},
  };
  const site: TreeItem = {
    id: uid("site"),
    type: "SITE",
    name: "PCF-SITE",
    parentId: world.id,
    visible: true,
    props: {},
  };
  const zone: TreeItem = {
    id: uid("zone"),
    type: "ZONE",
    name: "PCF-ZONE",
    parentId: site.id,
    visible: true,
    props: {},
  };
  items.push(world, site, zone);

  let pipeline = name;
  let spec = "A1A";
  let current: PcfComp | null = null;
  const comps: PcfComp[] = [];

  const flush = () => {
    if (current) comps.push(current);
    current = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) continue;
    const indent = raw.startsWith(" ") || raw.startsWith("\t");
    if (!indent) {
      if (line.startsWith("PIPELINE-REFERENCE")) {
        pipeline = line.replace("PIPELINE-REFERENCE", "").trim();
        continue;
      }
      if (line.startsWith("MATERIALS") || line.startsWith("ITEM-CODE") || line.startsWith("ISOGEN") || line.startsWith("UNITS")) {
        flush();
        continue;
      }
      flush();
      current = { type: line.trim(), points: [] };
      continue;
    }
    const body = line.trim();
    if (body.startsWith("PIPING-SPEC")) spec = body.replace("PIPING-SPEC", "").trim() || spec;
    if (!current) continue;
    if (body.startsWith("END-POINT") || body.startsWith("BRANCH1-POINT")) {
      const nums = body.replace(/^[A-Z0-9-]+\s+/, "").trim().split(/\s+/).map(Number);
      current.points.push({ x: nums[0], y: nums[1], z: nums[2], bore: nums[3] });
    } else if (body.startsWith("CENTRE-POINT")) {
      const nums = body.replace("CENTRE-POINT", "").trim().split(/\s+/).map(Number);
      current.center = { x: nums[0], y: nums[1], z: nums[2] };
    } else if (body.startsWith("SKEY")) {
      current.skey = body.replace("SKEY", "").trim();
    } else if (body.startsWith("ITEM-CODE")) {
      current.code = body.replace("ITEM-CODE", "").trim();
    } else if (body.startsWith("ITEM-DESCRIPTION")) {
      current.description = body.replace("ITEM-DESCRIPTION", "").trim();
    }
  }
  flush();

  const pipe: TreeItem = {
    id: uid("pipe"),
    type: "PIPE",
    name: pipeline || name,
    parentId: zone.id,
    visible: true,
    props: { spec },
  };
  const bran: TreeItem = {
    id: uid("bran"),
    type: "BRAN",
    name: `${pipe.name}-B1`,
    parentId: pipe.id,
    visible: true,
    props: { spec },
  };
  items.push(pipe, bran);

  for (const comp of comps) {
    const bore = comp.points[0]?.bore ?? 80;
    const mapped = mapComp(comp, bran.id, bore, spec);
    if (mapped) items.push(mapped);
  }

  return {
    name: pipeline || name,
    code: "PCF",
    description: "Imported from PCF",
    units: "MM",
    spec,
    items,
  };
}

function mapComp(comp: PcfComp, parentId: string, bore: number, spec: string): TreeItem | null {
  const p1 = comp.points[0];
  const p2 = comp.points[1];
  const kind = comp.type.toUpperCase();
  const base = {
    parentId,
    visible: true,
    props: {
      bore,
      spec,
      skey: comp.skey ?? "",
      description: comp.description ?? kind,
    } as TreeItem["props"],
  };

  if (kind === "PIPE" && p1 && p2) {
    return {
      ...base,
      id: uid("tube"),
      type: "TUBE",
      name: "TUBE",
      props: { ...base.props, x1: p1.x, y1: p1.y, z1: p1.z, x2: p2.x, y2: p2.y, z2: p2.z },
    };
  }
  if (kind === "ELBOW" && p1 && p2) {
    const c = comp.center ?? { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2, z: (p1.z + p2.z) / 2 };
    return {
      ...base,
      id: uid("elbo"),
      type: "ELBO",
      name: "ELBO",
      props: {
        ...base.props,
        x1: p1.x,
        y1: p1.y,
        z1: p1.z,
        x2: p2.x,
        y2: p2.y,
        z2: p2.z,
        cx: c.x,
        cy: c.y,
        cz: c.z,
      },
    };
  }
  if ((kind === "VALVE" || kind === "CHECK-VALVE") && p1 && p2) {
    return {
      ...base,
      id: uid("valv"),
      type: "VALV",
      name: kind === "CHECK-VALVE" ? "CHECK" : "VALVE",
      props: {
        ...base.props,
        x1: p1.x,
        y1: p1.y,
        z1: p1.z,
        x2: p2.x,
        y2: p2.y,
        z2: p2.z,
        kind: kind === "CHECK-VALVE" ? "CHECK" : "GATE",
      },
    };
  }
  if (kind === "FLANGE" && p1) {
    return {
      ...base,
      id: uid("flan"),
      type: "FLAN",
      name: "FLAN",
      props: { ...base.props, x: p1.x, y: p1.y, z: p1.z, dx: 1, dy: 0, dz: 0 },
    };
  }
  if (kind === "TEE" && p1 && p2) {
    const p3 = comp.points[2] ?? p2;
    const c = comp.center ?? p1;
    return {
      ...base,
      id: uid("tee"),
      type: "TEE",
      name: "TEE",
      props: {
        ...base.props,
        x1: p1.x,
        y1: p1.y,
        z1: p1.z,
        x2: p2.x,
        y2: p2.y,
        z2: p2.z,
        x3: p3.x,
        y3: p3.y,
        z3: p3.z,
        cx: c.x,
        cy: c.y,
        cz: c.z,
      },
    };
  }
  return null;
}
