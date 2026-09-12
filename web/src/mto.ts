import { dist, v } from "./math";
import { boreWeight } from "./specs";
import type { ProjectDoc, TreeItem } from "./types";

export interface MtoRow {
  type: string;
  description: string;
  spec: string;
  bore: string;
  qty: number;
  unit: string;
  weight: number;
}

function num(item: TreeItem, key: string, fallback = 0): number {
  const value = item.props[key];
  return typeof value === "number" ? value : Number(value ?? fallback) || fallback;
}

function str(item: TreeItem, key: string, fallback = ""): string {
  const value = item.props[key];
  return typeof value === "string" ? value : fallback;
}

export function buildMto(doc: ProjectDoc, rootId?: string): MtoRow[] {
  const items = rootId
    ? doc.items.filter((it) => it.id === rootId || isUnder(doc, it.id, rootId))
    : doc.items;

  const buckets = new Map<string, MtoRow>();
  const add = (row: MtoRow) => {
    const key = `${row.type}|${row.description}|${row.bore}|${row.spec}`;
    const prev = buckets.get(key);
    if (prev) {
      prev.qty += row.qty;
      prev.weight += row.weight;
    } else {
      buckets.set(key, { ...row });
    }
  };

  for (const it of items) {
    const bore = num(it, "bore");
    const spec = str(it, "spec", doc.spec);
    const desc = str(it, "description", it.name);
    if (it.type === "TUBE") {
      const length = dist(
        v(num(it, "x1"), num(it, "y1"), num(it, "z1")),
        v(num(it, "x2"), num(it, "y2"), num(it, "z2")),
      );
      const meters = length / 1000;
      add({
        type: "PIPE",
        description: desc || `PIPE ${bore} SCH40`,
        spec,
        bore: String(bore),
        qty: meters,
        unit: "m",
        weight: meters * boreWeight(bore),
      });
    } else if (["ELBO", "VALV", "FLAN", "REDU", "TEE", "CAP"].includes(it.type)) {
      const unitWeight =
        it.type === "VALV" ? bore * 0.12 : it.type === "FLAN" ? bore * 0.04 : bore * 0.03;
      add({
        type: it.type,
        description: desc,
        spec,
        bore: String(bore || "-"),
        qty: 1,
        unit: "ea",
        weight: unitWeight,
      });
    } else if (it.type === "EQUI") {
      add({
        type: "EQUI",
        description: desc || it.name,
        spec: "-",
        bore: "-",
        qty: 1,
        unit: "ea",
        weight: 0,
      });
    } else if (it.type === "SCTN") {
      const length =
        dist(
          v(num(it, "x1"), num(it, "y1"), num(it, "z1")),
          v(num(it, "x2"), num(it, "y2"), num(it, "z2")),
        ) / 1000;
      add({
        type: "SCTN",
        description: str(it, "profile", it.name),
        spec: "-",
        bore: "-",
        qty: length,
        unit: "m",
        weight: length * 42,
      });
    }
  }

  return [...buckets.values()].sort((a, b) => a.type.localeCompare(b.type) || a.bore.localeCompare(b.bore));
}

function isUnder(doc: ProjectDoc, id: string, rootId: string): boolean {
  let cur = doc.items.find((it) => it.id === id);
  while (cur) {
    if (cur.parentId === rootId || cur.id === rootId) return true;
    cur = doc.items.find((it) => it.id === cur?.parentId);
  }
  return false;
}

export function mtoCsv(rows: MtoRow[]): string {
  const header = "Type,Description,Spec,Bore,Qty,Unit,Weight(kg)";
  const body = rows.map(
    (r) =>
      `${r.type},"${r.description}",${r.spec},${r.bore},${r.qty.toFixed(2)},${r.unit},${r.weight.toFixed(2)}`,
  );
  return [header, ...body].join("\n");
}
