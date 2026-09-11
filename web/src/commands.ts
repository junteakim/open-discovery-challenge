import { add, dist, norm, scale, sub, v } from "./math";
import { addItem, ensureParent, nextName } from "./project";
import { elbowRadius } from "./specs";
import type { ProjectDoc, TreeItem, Vec3 } from "./types";

function num(n: number): number {
  return Math.round(n * 10) / 10;
}

export function placeVessel(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  name: string,
  p: Vec3,
  diameter: number,
  height: number,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["ZONE", "SITE"], "ZONE");
  let next = addItem(ready.doc, ready.parent.id, "EQUI", name, {
    kind: "vessel",
    x: p.x,
    y: p.y,
    z: p.z,
    diameter,
    height,
    description: "Vertical vessel",
  });
  const id = next.item.id;
  const shellH = height * 0.84;
  next = addItem(next.doc, id, "CYLI", `${name}-SHELL`, {
    x: p.x,
    y: p.y,
    z: p.z + height * 0.5,
    dx: 0,
    dy: 0,
    dz: 1,
    diameter,
    height: shellH,
  });
  next = addItem(next.doc, id, "DISH", `${name}-HEAD-B`, {
    x: p.x,
    y: p.y,
    z: p.z + height * 0.08,
    diameter,
    height: diameter * 0.25,
    flip: 1,
  });
  next = addItem(next.doc, id, "DISH", `${name}-HEAD-T`, {
    x: p.x,
    y: p.y,
    z: p.z + height * 0.92,
    diameter,
    height: diameter * 0.25,
    flip: 0,
  });
  next = addItem(next.doc, id, "NOZZ", "N1", {
    x: p.x,
    y: p.y,
    z: p.z + height,
    dx: 0,
    dy: 0,
    dz: 1,
    bore: 100,
    length: 280,
  });
  next = addItem(next.doc, id, "NOZZ", "N2", {
    x: p.x,
    y: p.y,
    z: p.z,
    dx: 0,
    dy: 0,
    dz: -1,
    bore: 100,
    length: 280,
  });
  return { doc: next.doc, id };
}

export function placeTank(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  name: string,
  p: Vec3,
  diameter: number,
  height: number,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["ZONE", "SITE"], "ZONE");
  let next = addItem(ready.doc, ready.parent.id, "EQUI", name, {
    kind: "tank",
    x: p.x,
    y: p.y,
    z: p.z,
    diameter,
    height,
    description: "Storage tank",
  });
  const id = next.item.id;
  next = addItem(next.doc, id, "CYLI", `${name}-SHELL`, {
    x: p.x,
    y: p.y,
    z: p.z + height / 2,
    dx: 0,
    dy: 0,
    dz: 1,
    diameter,
    height,
  });
  next = addItem(next.doc, id, "NOZZ", "N1", {
    x: p.x - diameter / 2,
    y: p.y,
    z: p.z + height * 0.55,
    dx: -1,
    dy: 0,
    dz: 0,
    bore: 80,
    length: 280,
  });
  return { doc: next.doc, id };
}

export function placePump(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  name: string,
  p: Vec3,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["ZONE", "SITE"], "ZONE");
  let next = addItem(ready.doc, ready.parent.id, "EQUI", name, {
    kind: "pump",
    x: p.x,
    y: p.y,
    z: p.z,
    description: "Centrifugal pump",
  });
  const id = next.item.id;
  next = addItem(next.doc, id, "BOX", `${name}-BASE`, {
    x: p.x,
    y: p.y,
    z: p.z + 150,
    lx: 1400,
    ly: 800,
    lz: 300,
  });
  next = addItem(next.doc, id, "CYLI", `${name}-CASE`, {
    x: p.x + 200,
    y: p.y,
    z: p.z + 620,
    dx: 1,
    dy: 0,
    dz: 0,
    diameter: 520,
    height: 480,
  });
  next = addItem(next.doc, id, "CYLI", `${name}-MOTOR`, {
    x: p.x - 550,
    y: p.y,
    z: p.z + 620,
    dx: 1,
    dy: 0,
    dz: 0,
    diameter: 420,
    height: 700,
  });
  next = addItem(next.doc, id, "NOZZ", "S", {
    x: p.x + 200,
    y: p.y + 260,
    z: p.z + 620,
    dx: 0,
    dy: 1,
    dz: 0,
    bore: 100,
    length: 220,
  });
  next = addItem(next.doc, id, "NOZZ", "D", {
    x: p.x + 440,
    y: p.y,
    z: p.z + 880,
    dx: 0,
    dy: 0,
    dz: 1,
    bore: 80,
    length: 220,
  });
  return { doc: next.doc, id };
}

export function placeExchanger(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  name: string,
  p: Vec3,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["ZONE", "SITE"], "ZONE");
  let next = addItem(ready.doc, ready.parent.id, "EQUI", name, {
    kind: "exchanger",
    x: p.x,
    y: p.y,
    z: p.z,
    description: "Shell & tube exchanger",
  });
  const id = next.item.id;
  next = addItem(next.doc, id, "CYLI", `${name}-SHELL`, {
    x: p.x,
    y: p.y,
    z: p.z,
    dx: 1,
    dy: 0,
    dz: 0,
    diameter: 700,
    height: 3200,
  });
  next = addItem(next.doc, id, "BOX", `${name}-S1`, {
    x: p.x - 1100,
    y: p.y,
    z: p.z - 500,
    lx: 240,
    ly: 700,
    lz: 400,
  });
  next = addItem(next.doc, id, "BOX", `${name}-S2`, {
    x: p.x + 1100,
    y: p.y,
    z: p.z - 500,
    lx: 240,
    ly: 700,
    lz: 400,
  });
  next = addItem(next.doc, id, "NOZZ", "N1", {
    x: p.x - 1600,
    y: p.y,
    z: p.z,
    dx: -1,
    dy: 0,
    dz: 0,
    bore: 80,
    length: 240,
  });
  return { doc: next.doc, id };
}

export function placeColumn(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  p: Vec3,
  height: number,
  profile: string,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["STRU", "ZONE"], "STRU");
  let work = ready.doc;
  let parent = ready.parent;
  if (parent.type !== "STRU") {
    const created = addItem(work, parent.id, "STRU", nextName(work, "ST"));
    work = created.doc;
    parent = created.item;
  }
  const next = addItem(work, parent.id, "SCTN", nextName(work, "COL"), {
    x1: p.x,
    y1: p.y,
    z1: p.z,
    x2: p.x,
    y2: p.y,
    z2: p.z + height,
    profile,
  });
  return { doc: next.doc, id: next.item.id };
}

export function placeBeam(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  a: Vec3,
  b: Vec3,
  profile: string,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["STRU", "ZONE"], "STRU");
  let work = ready.doc;
  let parent = ready.parent;
  if (parent.type !== "STRU") {
    const created = addItem(work, parent.id, "STRU", nextName(work, "ST"));
    work = created.doc;
    parent = created.item;
  }
  const next = addItem(work, parent.id, "SCTN", nextName(work, "BM"), {
    x1: a.x,
    y1: a.y,
    z1: a.z,
    x2: b.x,
    y2: b.y,
    z2: b.z,
    profile,
  });
  return { doc: next.doc, id: next.item.id };
}

export function placePlatform(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  p: Vec3,
  lx: number,
  ly: number,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["STRU", "ZONE"], "STRU");
  let work = ready.doc;
  let parent = ready.parent;
  if (parent.type !== "STRU") {
    const created = addItem(work, parent.id, "STRU", nextName(work, "ST"));
    work = created.doc;
    parent = created.item;
  }
  const next = addItem(work, parent.id, "PLAT", nextName(work, "PLAT"), {
    x: p.x,
    y: p.y,
    z: p.z,
    lx,
    ly,
    lz: 12,
  });
  return { doc: next.doc, id: next.item.id };
}

export function placeGrid(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  values: Record<string, string>,
): { doc: ProjectDoc; id: string } {
  const ready = ensureParent(doc, parentHint, ["ZONE", "SITE"], "ZONE");
  const next = addItem(ready.doc, ready.parent.id, "GRID", values.name || nextName(ready.doc, "GRID"), {
    x0: Number(values.x0 || 0),
    y0: Number(values.y0 || 0),
    z0: Number(values.z0 || 0),
    nx: Number(values.nx || 4),
    ny: Number(values.ny || 3),
    nz: Number(values.nz || 3),
    sx: Number(values.sx || 4000),
    sy: Number(values.sy || 4000),
    sz: Number(values.sz || 4000),
    labelsX: values.labelsX || "A,B,C,D",
    labelsY: values.labelsY || "1,2,3",
  });
  return { doc: next.doc, id: next.item.id };
}

export function routePipe(
  doc: ProjectDoc,
  parentHint: TreeItem | undefined,
  name: string,
  points: Vec3[],
  bore: number,
  spec: string,
): { doc: ProjectDoc; id: string } {
  if (points.length < 2) return { doc, id: parentHint?.id ?? "world" };
  const ready = ensureParent(doc, parentHint, ["ZONE", "SITE", "PIPE"], "ZONE");
  let work = ready.doc;
  let zone = ready.parent;
  if (zone.type !== "ZONE" && zone.type !== "SITE") {
    const z = addItem(work, zone.parentId ?? "world", "ZONE", nextName(work, "ZONE"));
    work = z.doc;
    zone = z.item;
  }
  const pipe = addItem(work, zone.id, "PIPE", name, { spec, bore, description: name });
  work = pipe.doc;
  const head = points[0];
  const tail = points[points.length - 1];
  const bran = addItem(work, pipe.item.id, "BRAN", `${name}-B1`, {
    spec,
    hbore: bore,
    tbore: bore,
    hx: head.x,
    hy: head.y,
    hz: head.z,
    tx: tail.x,
    ty: tail.y,
    tz: tail.z,
  });
  work = bran.doc;
  work = appendPolyline(work, bran.item.id, points, bore, spec);
  return { doc: work, id: pipe.item.id };
}

export function appendPolyline(
  doc: ProjectDoc,
  branchId: string,
  points: Vec3[],
  bore: number,
  spec: string,
): ProjectDoc {
  let work = doc;
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const c = points[i + 2];
    let start = a;
    let end = b;
    if (i > 0) {
      const prev = elbowGeom(points[i - 1], a, b, bore);
      start = prev.p2;
    }
    if (c) {
      const next = elbowGeom(a, b, c, bore);
      end = next.p1;
      const created = addItem(work, branchId, "ELBO", nextName(work, "ELBO"), {
        x1: num(next.p1.x),
        y1: num(next.p1.y),
        z1: num(next.p1.z),
        x2: num(next.p2.x),
        y2: num(next.p2.y),
        z2: num(next.p2.z),
        cx: num(next.center.x),
        cy: num(next.center.y),
        cz: num(next.center.z),
        bore,
        radius: next.radius,
        spec,
        skey: "ELSW",
        description: `ELBOW ${bore} LR 90 SCH40`,
      });
      work = created.doc;
    }
    if (dist(start, end) > 2) {
      const tube = addItem(work, branchId, "TUBE", nextName(work, "TUBE"), {
        x1: num(start.x),
        y1: num(start.y),
        z1: num(start.z),
        x2: num(end.x),
        y2: num(end.y),
        z2: num(end.z),
        bore,
        spec,
        skey: "PIPE",
        description: `PIPE ${bore} SCH40 ANSI B36.10`,
      });
      work = tube.doc;
    }
  }
  return work;
}

function elbowGeom(a: Vec3, corner: Vec3, c: Vec3, bore: number) {
  const r = elbowRadius(bore);
  const da = norm(sub(a, corner));
  const dc = norm(sub(c, corner));
  return {
    p1: add(corner, scale(da, r)),
    p2: add(corner, scale(dc, r)),
    center: corner,
    radius: r,
  };
}

export function addValveOnTube(doc: ProjectDoc, tube: TreeItem, kind: "GATE" | "CHECK"): ProjectDoc {
  const a = v(Number(tube.props.x1), Number(tube.props.y1), Number(tube.props.z1));
  const b = v(Number(tube.props.x2), Number(tube.props.y2), Number(tube.props.z2));
  const bore = Number(tube.props.bore ?? 80);
  const spec = String(tube.props.spec ?? "A1A");
  const dir = norm(sub(b, a));
  const mid = add(a, scale(dir, dist(a, b) * 0.5));
  const half = 180;
  const va = add(mid, scale(dir, -half));
  const vb = add(mid, scale(dir, half));
  const parentId = tube.parentId ?? "world";
  let work = doc;
  const valv = addItem(work, parentId, "VALV", nextName(work, kind === "CHECK" ? "CHECK" : "GATE"), {
    x1: num(va.x),
    y1: num(va.y),
    z1: num(va.z),
    x2: num(vb.x),
    y2: num(vb.y),
    z2: num(vb.z),
    bore,
    spec,
    kind,
    skey: kind === "CHECK" ? "CKSW" : "VGSW",
    description: kind === "CHECK" ? `CHECK VALVE ${bore}` : `GATE VALVE ${bore} RF 150LB`,
  });
  return valv.doc;
}

export { v };
