import { uid } from "./math";
import type { ItemType, ProjectDoc, TreeItem } from "./types";

export function emptyProject(name = "NEW", code = "NEW"): ProjectDoc {
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
    name: `${code}-SITE`,
    parentId: world.id,
    visible: true,
    props: {},
  };
  const zone: TreeItem = {
    id: uid("zone"),
    type: "ZONE",
    name: `${code}-ZONE`,
    parentId: site.id,
    visible: true,
    props: {},
  };
  return {
    name,
    code,
    description: "PipeCAD Web project",
    units: "MM",
    spec: "A1A",
    items: [world, site, zone],
  };
}

export function childrenOf(doc: ProjectDoc, id: string): TreeItem[] {
  return doc.items.filter((it) => it.parentId === id);
}

export function findItem(doc: ProjectDoc, id: string | null): TreeItem | undefined {
  if (!id) return undefined;
  return doc.items.find((it) => it.id === id);
}

export function ancestors(doc: ProjectDoc, id: string): TreeItem[] {
  const out: TreeItem[] = [];
  let cur = findItem(doc, id);
  while (cur) {
    out.unshift(cur);
    cur = findItem(doc, cur.parentId);
  }
  return out;
}

export function descendants(doc: ProjectDoc, id: string): TreeItem[] {
  const out: TreeItem[] = [];
  const walk = (pid: string) => {
    for (const child of childrenOf(doc, pid)) {
      out.push(child);
      walk(child.id);
    }
  };
  walk(id);
  return out;
}

export function removeSubtree(doc: ProjectDoc, id: string): ProjectDoc {
  if (id === "world") return doc;
  const drop = new Set([id, ...descendants(doc, id).map((it) => it.id)]);
  return { ...doc, items: doc.items.filter((it) => !drop.has(it.id)) };
}

export function addItem(
  doc: ProjectDoc,
  parentId: string,
  type: ItemType,
  name: string,
  props: TreeItem["props"] = {},
): { doc: ProjectDoc; item: TreeItem } {
  const item: TreeItem = {
    id: uid(type.toLowerCase()),
    type,
    name,
    parentId,
    visible: true,
    props,
  };
  return { doc: { ...doc, items: [...doc.items, item] }, item };
}

export function updateItem(
  doc: ProjectDoc,
  id: string,
  patch: Partial<Pick<TreeItem, "name" | "visible" | "props">>,
): ProjectDoc {
  return {
    ...doc,
    items: doc.items.map((it) =>
      it.id === id
        ? {
            ...it,
            ...patch,
            props: patch.props ? { ...it.props, ...patch.props } : it.props,
          }
        : it,
    ),
  };
}

export function setVisible(doc: ProjectDoc, id: string, visible: boolean): ProjectDoc {
  const ids = new Set([id, ...descendants(doc, id).map((it) => it.id)]);
  return {
    ...doc,
    items: doc.items.map((it) => (ids.has(it.id) ? { ...it, visible } : it)),
  };
}

export function nextName(doc: ProjectDoc, prefix: string): string {
  const used = new Set(doc.items.map((it) => it.name));
  let i = 1;
  while (used.has(`${prefix}-${String(i).padStart(2, "0")}`)) i += 1;
  return `${prefix}-${String(i).padStart(2, "0")}`;
}

export function firstOfType(doc: ProjectDoc, type: ItemType): TreeItem | undefined {
  return doc.items.find((it) => it.type === type);
}

export function ensureParent(
  doc: ProjectDoc,
  preferred: TreeItem | undefined,
  allowed: ItemType[],
  fallbackType: ItemType,
): { doc: ProjectDoc; parent: TreeItem } {
  if (preferred && allowed.includes(preferred.type)) {
    return { doc, parent: preferred };
  }
  const existing = firstOfType(doc, fallbackType);
  if (existing) return { doc, parent: existing };
  const zone = firstOfType(doc, "ZONE") ?? firstOfType(doc, "SITE") ?? doc.items[0];
  const created = addItem(doc, zone.id, fallbackType, nextName(doc, fallbackType));
  return { doc: created.doc, parent: created.item };
}

export function cloneDoc(doc: ProjectDoc): ProjectDoc {
  return JSON.parse(JSON.stringify(doc)) as ProjectDoc;
}
