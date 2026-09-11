import { add, dist, norm, scale, sub, uid, v } from "./math";
import { elbowRadius } from "./specs";
import type { ProjectDoc, TreeItem, Vec3 } from "./types";

function item(
  type: TreeItem["type"],
  name: string,
  parentId: string,
  props: TreeItem["props"] = {},
): TreeItem {
  return { id: uid(type.toLowerCase()), type, name, parentId, visible: true, props };
}

function num(n: number): number {
  return Math.round(n * 10) / 10;
}

function elbowFromCorner(a: Vec3, corner: Vec3, c: Vec3, bore: number) {
  const r = elbowRadius(bore);
  const da = norm(sub(a, corner));
  const dc = norm(sub(c, corner));
  const p1 = add(corner, scale(da, r));
  const p2 = add(corner, scale(dc, r));
  return { p1, p2, center: corner, radius: r };
}

function pushRun(
  items: TreeItem[],
  branchId: string,
  points: Vec3[],
  bore: number,
  spec: string,
  extras: { valveAt?: number; valveKind?: string; flangeEnds?: boolean } = {},
) {
  const tubes: { a: Vec3; b: Vec3 }[] = [];
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const c = points[i + 2];
    let start = a;
    let end = b;
    if (i > 0) {
      const prev = elbowFromCorner(points[i - 1], a, b, bore);
      start = prev.p2;
    }
    if (c) {
      const next = elbowFromCorner(a, b, c, bore);
      end = next.p1;
      items.push(
        item("ELBO", `ELBO-${items.length}`, branchId, {
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
        }),
      );
    }
    if (dist(start, end) > 2) {
      tubes.push({ a: start, b: end });
    }
  }

  tubes.forEach((tube, idx) => {
    if (extras.valveAt === idx) {
      const dir = norm(sub(tube.b, tube.a));
      const mid = add(tube.a, scale(dir, dist(tube.a, tube.b) * 0.5));
      const half = 180;
      const va = add(mid, scale(dir, -half));
      const vb = add(mid, scale(dir, half));
      if (dist(tube.a, va) > 2) {
        items.push(tubeItem(branchId, items.length, tube.a, va, bore, spec));
      }
      items.push(
        item("VALV", extras.valveKind === "CHECK" ? "CHECK-01" : "GATE-01", branchId, {
          x1: num(va.x),
          y1: num(va.y),
          z1: num(va.z),
          x2: num(vb.x),
          y2: num(vb.y),
          z2: num(vb.z),
          bore,
          spec,
          kind: extras.valveKind ?? "GATE",
          skey: extras.valveKind === "CHECK" ? "CKSW" : "VGSW",
          description:
            extras.valveKind === "CHECK"
              ? `CHECK VALVE ${bore} SW`
              : `GATE VALVE ${bore} RF 150LB`,
        }),
      );
      items.push(
        item("FLAN", `FLAN-${items.length}`, branchId, {
          x: num(va.x),
          y: num(va.y),
          z: num(va.z),
          dx: num(dir.x),
          dy: num(dir.y),
          dz: num(dir.z),
          bore,
          spec,
          skey: "FLSO",
          description: `FLANGE SO ${bore} 150LB`,
        }),
      );
      items.push(
        item("FLAN", `FLAN-${items.length}`, branchId, {
          x: num(vb.x),
          y: num(vb.y),
          z: num(vb.z),
          dx: num(dir.x),
          dy: num(dir.y),
          dz: num(dir.z),
          bore,
          spec,
          skey: "FLSO",
          description: `FLANGE SO ${bore} 150LB`,
        }),
      );
      if (dist(vb, tube.b) > 2) {
        items.push(tubeItem(branchId, items.length, vb, tube.b, bore, spec));
      }
    } else {
      items.push(tubeItem(branchId, items.length, tube.a, tube.b, bore, spec));
    }
  });
}

function tubeItem(
  branchId: string,
  n: number,
  a: Vec3,
  b: Vec3,
  bore: number,
  spec: string,
): TreeItem {
  return item("TUBE", `TUBE-${n}`, branchId, {
    x1: num(a.x),
    y1: num(a.y),
    z1: num(a.z),
    x2: num(b.x),
    y2: num(b.y),
    z2: num(b.z),
    bore,
    spec,
    skey: "PIPE",
    description: `PIPE ${bore} SCH40 ANSI B36.10`,
  });
}

export function sampleProject(): ProjectDoc {
  const items: TreeItem[] = [];
  const world = item("WORLD", "/*", "", {});
  world.id = "world";
  world.parentId = null;
  items.push(world);

  const site = item("SITE", "SAM-SITE", world.id);
  const zone = item("ZONE", "PROCESS", site.id);
  items.push(site, zone);

  items.push(
    item("GRID", "GRID-A", zone.id, {
      x0: 0,
      y0: 0,
      z0: 0,
      nx: 4,
      ny: 3,
      nz: 3,
      sx: 4000,
      sy: 4000,
      sz: 4000,
      labelsX: "A,B,C,D",
      labelsY: "1,2,3",
    }),
  );

  const vessel = item("EQUI", "V-101", zone.id, {
    kind: "vessel",
    x: 2000,
    y: 2000,
    z: 0,
    diameter: 1600,
    height: 6200,
    description: "Vertical process vessel",
  });
  items.push(vessel);
  items.push(
    item("CYLI", "V-101-SHELL", vessel.id, {
      x: 2000,
      y: 2000,
      z: 3100,
      dx: 0,
      dy: 0,
      dz: 1,
      diameter: 1600,
      height: 5200,
    }),
    item("DISH", "V-101-HEAD-B", vessel.id, {
      x: 2000,
      y: 2000,
      z: 500,
      diameter: 1600,
      height: 400,
      flip: 1,
    }),
    item("DISH", "V-101-HEAD-T", vessel.id, {
      x: 2000,
      y: 2000,
      z: 5700,
      diameter: 1600,
      height: 400,
      flip: 0,
    }),
    item("NOZZ", "N1", vessel.id, {
      x: 2000,
      y: 2000,
      z: 6100,
      dx: 0,
      dy: 0,
      dz: 1,
      bore: 100,
      length: 280,
    }),
    item("NOZZ", "N2", vessel.id, {
      x: 2000,
      y: 2000,
      z: 100,
      dx: 0,
      dy: 0,
      dz: -1,
      bore: 100,
      length: 280,
    }),
    item("NOZZ", "N3", vessel.id, {
      x: 2800,
      y: 2000,
      z: 4200,
      dx: 1,
      dy: 0,
      dz: 0,
      bore: 80,
      length: 260,
    }),
  );

  const pump = item("EQUI", "P-101", zone.id, {
    kind: "pump",
    x: 6000,
    y: 1200,
    z: 0,
    description: "Centrifugal pump",
  });
  items.push(pump);
  items.push(
    item("BOX", "P-101-BASE", pump.id, {
      x: 6000,
      y: 1200,
      z: 150,
      lx: 1400,
      ly: 800,
      lz: 300,
    }),
    item("CYLI", "P-101-CASE", pump.id, {
      x: 6200,
      y: 1200,
      z: 620,
      dx: 1,
      dy: 0,
      dz: 0,
      diameter: 520,
      height: 480,
    }),
    item("CYLI", "P-101-MOTOR", pump.id, {
      x: 5450,
      y: 1200,
      z: 620,
      dx: 1,
      dy: 0,
      dz: 0,
      diameter: 420,
      height: 700,
    }),
    item("NOZZ", "S", pump.id, {
      x: 6200,
      y: 1460,
      z: 620,
      dx: 0,
      dy: 1,
      dz: 0,
      bore: 100,
      length: 220,
    }),
    item("NOZZ", "D", pump.id, {
      x: 6440,
      y: 1200,
      z: 880,
      dx: 0,
      dy: 0,
      dz: 1,
      bore: 80,
      length: 220,
    }),
  );

  const tank = item("EQUI", "T-101", zone.id, {
    kind: "tank",
    x: 10000,
    y: 2200,
    z: 0,
    diameter: 2800,
    height: 3600,
    description: "Storage tank",
  });
  items.push(tank);
  items.push(
    item("CYLI", "T-101-SHELL", tank.id, {
      x: 10000,
      y: 2200,
      z: 1800,
      dx: 0,
      dy: 0,
      dz: 1,
      diameter: 2800,
      height: 3600,
    }),
    item("NOZZ", "N1", tank.id, {
      x: 8600,
      y: 2200,
      z: 2200,
      dx: -1,
      dy: 0,
      dz: 0,
      bore: 80,
      length: 300,
    }),
  );

  const exch = item("EQUI", "E-101", zone.id, {
    kind: "exchanger",
    x: 6000,
    y: 6000,
    z: 1600,
    description: "Shell & tube exchanger",
  });
  items.push(exch);
  items.push(
    item("CYLI", "E-101-SHELL", exch.id, {
      x: 6000,
      y: 6000,
      z: 1600,
      dx: 1,
      dy: 0,
      dz: 0,
      diameter: 700,
      height: 3200,
    }),
    item("BOX", "E-101-SADDLE-1", exch.id, {
      x: 4900,
      y: 6000,
      z: 1100,
      lx: 240,
      ly: 700,
      lz: 400,
    }),
    item("BOX", "E-101-SADDLE-2", exch.id, {
      x: 7100,
      y: 6000,
      z: 1100,
      lx: 240,
      ly: 700,
      lz: 400,
    }),
    item("NOZZ", "N1", exch.id, {
      x: 4600,
      y: 6000,
      z: 1600,
      dx: -1,
      dy: 0,
      dz: 0,
      bore: 80,
      length: 240,
    }),
  );

  const stru = item("STRU", "ST-01", zone.id, { description: "Vessel platform" });
  items.push(stru);
  const cols = [
    v(800, 800, 0),
    v(3200, 800, 0),
    v(800, 3200, 0),
    v(3200, 3200, 0),
  ];
  cols.forEach((p, i) => {
    items.push(
      item("SCTN", `COL-${i + 1}`, stru.id, {
        x1: p.x,
        y1: p.y,
        z1: 0,
        x2: p.x,
        y2: p.y,
        z2: 4000,
        profile: "H250x250x9x14",
      }),
    );
  });
  const beams = [
    [v(800, 800, 4000), v(3200, 800, 4000)],
    [v(800, 3200, 4000), v(3200, 3200, 4000)],
    [v(800, 800, 4000), v(800, 3200, 4000)],
    [v(3200, 800, 4000), v(3200, 3200, 4000)],
  ];
  beams.forEach(([a, b], i) => {
    items.push(
      item("SCTN", `BM-${i + 1}`, stru.id, {
        x1: a.x,
        y1: a.y,
        z1: a.z,
        x2: b.x,
        y2: b.y,
        z2: b.z,
        profile: "H200x200x8x12",
      }),
    );
  });
  items.push(
    item("PLAT", "PLAT-01", stru.id, {
      x: 2000,
      y: 2000,
      z: 4000,
      lx: 2400,
      ly: 2400,
      lz: 12,
    }),
  );

  const pipe1 = item("PIPE", "100-P-101", zone.id, {
    spec: "A1A",
    bore: 100,
    description: "Vessel outlet to pump suction",
  });
  const bran1 = item("BRAN", "100-P-101-B1", pipe1.id, {
    spec: "A1A",
    hbore: 100,
    tbore: 100,
    hx: 2000,
    hy: 2000,
    hz: -180,
    tx: 6200,
    ty: 1680,
    tz: 620,
  });
  items.push(pipe1, bran1);
  pushRun(
    items,
    bran1.id,
    [v(2000, 2000, -180), v(2000, 2000, 620), v(2000, 1680, 620), v(6200, 1680, 620)],
    100,
    "A1A",
    { valveAt: 2, valveKind: "GATE" },
  );

  const pipe2 = item("PIPE", "80-P-102", zone.id, {
    spec: "A1A",
    bore: 80,
    description: "Pump discharge to tank",
  });
  const bran2 = item("BRAN", "80-P-102-B1", pipe2.id, {
    spec: "A1A",
    hbore: 80,
    tbore: 80,
    hx: 6440,
    hy: 1200,
    hz: 1100,
    tx: 8300,
    ty: 2200,
    tz: 2200,
  });
  items.push(pipe2, bran2);
  pushRun(
    items,
    bran2.id,
    [v(6440, 1200, 1100), v(6440, 1200, 2200), v(8300, 1200, 2200), v(8300, 2200, 2200)],
    80,
    "A1A",
    { valveAt: 1, valveKind: "CHECK" },
  );

  const pipe3 = item("PIPE", "80-P-103", zone.id, {
    spec: "A1B",
    bore: 80,
    description: "Vessel side to exchanger",
  });
  const bran3 = item("BRAN", "80-P-103-B1", pipe3.id, {
    spec: "A1B",
    hbore: 80,
    tbore: 80,
    hx: 3060,
    hy: 2000,
    hz: 4200,
    tx: 4360,
    ty: 6000,
    tz: 1600,
  });
  items.push(pipe3, bran3);
  pushRun(
    items,
    bran3.id,
    [
      v(3060, 2000, 4200),
      v(4000, 2000, 4200),
      v(4000, 6000, 4200),
      v(4000, 6000, 1600),
      v(4360, 6000, 1600),
    ],
    80,
    "A1B",
  );

  return {
    name: "SAMPLE",
    code: "SAM",
    description: "PipeCAD Sample — process unit V-101 / P-101 / T-101 / E-101",
    units: "MM",
    spec: "A1A",
    items,
  };
}
