import * as THREE from "three";
import { add, dist, norm, sub, v } from "./math";
import { boreOd, PROFILES } from "./specs";
import type { TreeItem } from "./types";

const MAT = {
  pipe: new THREE.MeshStandardMaterial({
    color: 0xd4a017,
    metalness: 0.55,
    roughness: 0.35,
  }),
  valve: new THREE.MeshStandardMaterial({
    color: 0xc0392b,
    metalness: 0.4,
    roughness: 0.4,
  }),
  flange: new THREE.MeshStandardMaterial({
    color: 0x7f8c8d,
    metalness: 0.6,
    roughness: 0.3,
  }),
  equipment: new THREE.MeshStandardMaterial({
    color: 0x5dade2,
    metalness: 0.25,
    roughness: 0.45,
  }),
  dish: new THREE.MeshStandardMaterial({
    color: 0x3498db,
    metalness: 0.25,
    roughness: 0.45,
  }),
  structure: new THREE.MeshStandardMaterial({
    color: 0x95a5a6,
    metalness: 0.5,
    roughness: 0.4,
  }),
  platform: new THREE.MeshStandardMaterial({
    color: 0x7f8c8d,
    metalness: 0.3,
    roughness: 0.6,
  }),
  nozzle: new THREE.MeshStandardMaterial({
    color: 0xf39c12,
    metalness: 0.45,
    roughness: 0.4,
  }),
  selected: new THREE.MeshStandardMaterial({
    color: 0xffffff,
    emissive: 0xe67e22,
    emissiveIntensity: 0.35,
    metalness: 0.2,
    roughness: 0.4,
  }),
};

function n(item: TreeItem, key: string, fallback = 0): number {
  const value = item.props[key];
  return typeof value === "number" ? value : Number(value ?? fallback) || fallback;
}

function s(item: TreeItem, key: string, fallback = ""): string {
  const value = item.props[key];
  return typeof value === "string" ? value : fallback;
}

function alignCylinder(mesh: THREE.Mesh, a: THREE.Vector3, b: THREE.Vector3) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const length = dir.length();
  if (length < 1e-6) return;
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  mesh.scale.set(1, length, 1);
}

function cylinderBetween(
  a: { x: number; y: number; z: number },
  b: { x: number; y: number; z: number },
  radius: number,
  material: THREE.Material,
  radial = 20,
): THREE.Mesh {
  const geo = new THREE.CylinderGeometry(radius, radius, 1, radial);
  const mesh = new THREE.Mesh(geo, material);
  alignCylinder(mesh, new THREE.Vector3(a.x, a.y, a.z), new THREE.Vector3(b.x, b.y, b.z));
  return mesh;
}

function elbowMesh(item: TreeItem, material: THREE.Material): THREE.Object3D | null {
  const p1 = v(n(item, "x1"), n(item, "y1"), n(item, "z1"));
  const p2 = v(n(item, "x2"), n(item, "y2"), n(item, "z2"));
  const c = v(n(item, "cx"), n(item, "cy"), n(item, "cz"));
  const bore = n(item, "bore", 100);
  const radius = n(item, "radius") || dist(p1, c);
  if (radius < 1) return null;

  const v1 = norm(sub(p1, c));
  const v2 = norm(sub(p2, c));
  const normal = norm({
    x: v1.y * v2.z - v1.z * v2.y,
    y: v1.z * v2.x - v1.x * v2.z,
    z: v1.x * v2.y - v1.y * v2.x,
  });
  const angle = Math.acos(Math.min(1, Math.max(-1, v1.x * v2.x + v1.y * v2.y + v1.z * v2.z)));
  const tube = boreOd(bore) / 2;
  const geo = new THREE.TorusGeometry(radius, tube, 14, 24, angle || Math.PI / 2);
  const mesh = new THREE.Mesh(geo, material);

  const xAxis = new THREE.Vector3(v1.x, v1.y, v1.z);
  const zAxis = new THREE.Vector3(normal.x, normal.y, normal.z);
  if (zAxis.length() < 1e-4) zAxis.set(0, 0, 1);
  const yAxis = new THREE.Vector3().crossVectors(zAxis, xAxis).normalize();
  zAxis.crossVectors(xAxis, yAxis).normalize();
  const m = new THREE.Matrix4().makeBasis(xAxis, yAxis, zAxis);
  mesh.setRotationFromMatrix(m);
  mesh.position.set(c.x, c.y, c.z);
  return mesh;
}

function valveMesh(item: TreeItem, material: THREE.Material): THREE.Group {
  const a = v(n(item, "x1"), n(item, "y1"), n(item, "z1"));
  const b = v(n(item, "x2"), n(item, "y2"), n(item, "z2"));
  const bore = n(item, "bore", 80);
  const r = boreOd(bore) / 2;
  const group = new THREE.Group();
  group.add(cylinderBetween(a, b, r * 1.15, material, 16));
  const mid = add(a, { x: (b.x - a.x) / 2, y: (b.y - a.y) / 2, z: (b.z - a.z) / 2 });
  const body = new THREE.Mesh(new THREE.SphereGeometry(r * 1.8, 16, 12), material);
  body.position.set(mid.x, mid.y, mid.z);
  group.add(body);
  if (s(item, "kind") !== "CHECK") {
    const stem = new THREE.Mesh(
      new THREE.CylinderGeometry(r * 0.28, r * 0.28, r * 4, 10),
      MAT.flange,
    );
    stem.position.set(mid.x, mid.y, mid.z + r * 2.2);
    group.add(stem);
    const wheel = new THREE.Mesh(new THREE.TorusGeometry(r * 1.4, r * 0.18, 8, 16), MAT.flange);
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(mid.x, mid.y, mid.z + r * 4.1);
    group.add(wheel);
  }
  return group;
}

function flangeMesh(item: TreeItem): THREE.Mesh {
  const bore = n(item, "bore", 80);
  const r = boreOd(bore) / 2;
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(r * 1.9, r * 1.9, Math.max(18, r * 0.45), 20),
    MAT.flange,
  );
  const origin = new THREE.Vector3(n(item, "x"), n(item, "y"), n(item, "z"));
  const dir = new THREE.Vector3(n(item, "dx", 1), n(item, "dy"), n(item, "dz")).normalize();
  mesh.position.copy(origin);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  return mesh;
}

function primitiveMesh(item: TreeItem, selected: boolean): THREE.Object3D | null {
  const material = selected ? MAT.selected : materialFor(item.type);
  switch (item.type) {
    case "TUBE":
    case "REDU":
      return cylinderBetween(
        v(n(item, "x1"), n(item, "y1"), n(item, "z1")),
        v(n(item, "x2"), n(item, "y2"), n(item, "z2")),
        boreOd(n(item, "bore", 80)) / 2 * (item.type === "REDU" ? 1 : 1),
        material,
      );
    case "ELBO":
      return elbowMesh(item, material);
    case "VALV":
      return valveMesh(item, material);
    case "FLAN":
      return flangeMesh(item);
    case "CAP": {
      const r = boreOd(n(item, "bore", 80)) / 2;
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 10, 0, Math.PI), material);
      mesh.position.set(n(item, "x"), n(item, "y"), n(item, "z"));
      return mesh;
    }
    case "CYLI": {
      const h = n(item, "height", 1000);
      const r = n(item, "diameter", 400) / 2;
      const mesh = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 28), material);
      const dir = new THREE.Vector3(n(item, "dx"), n(item, "dy"), n(item, "dz", 1)).normalize();
      mesh.position.set(n(item, "x"), n(item, "y"), n(item, "z"));
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      return mesh;
    }
    case "BOX": {
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(n(item, "lx", 400), n(item, "ly", 400), n(item, "lz", 400)),
        material,
      );
      mesh.position.set(n(item, "x"), n(item, "y"), n(item, "z"));
      return mesh;
    }
    case "DISH": {
      const r = n(item, "diameter", 1000) / 2;
      const h = n(item, "height", 250);
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), material);
      mesh.position.set(n(item, "x"), n(item, "y"), n(item, "z"));
      mesh.scale.y = h / r;
      if (n(item, "flip")) mesh.rotation.x = Math.PI;
      return mesh;
    }
    case "NOZZ": {
      const length = n(item, "length", 250);
      const r = boreOd(n(item, "bore", 80)) / 2;
      const origin = v(n(item, "x"), n(item, "y"), n(item, "z"));
      const dir = { x: n(item, "dx"), y: n(item, "dy"), z: n(item, "dz", 1) };
      const tip = add(origin, { x: dir.x * length, y: dir.y * length, z: dir.z * length });
      const group = new THREE.Group();
      group.add(cylinderBetween(origin, tip, r, selected ? MAT.selected : MAT.nozzle));
      const fl = new THREE.Mesh(
        new THREE.CylinderGeometry(r * 1.8, r * 1.8, 22, 16),
        MAT.flange,
      );
      alignCylinder(fl, new THREE.Vector3(tip.x, tip.y, tip.z), new THREE.Vector3(origin.x, origin.y, origin.z));
      fl.position.set(tip.x, tip.y, tip.z);
      group.add(fl);
      return group;
    }
    case "SCTN": {
      const profile = PROFILES.find((p) => p.name === s(item, "profile")) ?? PROFILES[0];
      const a = v(n(item, "x1"), n(item, "y1"), n(item, "z1"));
      const b = v(n(item, "x2"), n(item, "y2"), n(item, "z2"));
      const group = new THREE.Group();
      const web = cylinderBetween(a, b, profile.tw * 0.6, material, 8);
      group.add(web);
      const flange = cylinderBetween(a, b, profile.bf * 0.18, material, 8);
      group.add(flange);
      return group;
    }
    case "PLAT": {
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(n(item, "lx", 2000), n(item, "ly", 2000), n(item, "lz", 12)),
        selected ? MAT.selected : MAT.platform,
      );
      mesh.position.set(n(item, "x"), n(item, "y"), n(item, "z"));
      return mesh;
    }
    case "TEE": {
      const c = v(n(item, "cx"), n(item, "cy"), n(item, "cz"));
      const p1 = v(n(item, "x1"), n(item, "y1"), n(item, "z1"));
      const p2 = v(n(item, "x2"), n(item, "y2"), n(item, "z2"));
      const p3 = v(n(item, "x3"), n(item, "y3"), n(item, "z3"));
      const r = boreOd(n(item, "bore", 80)) / 2;
      const g = new THREE.Group();
      g.add(cylinderBetween(p1, c, r, material));
      g.add(cylinderBetween(c, p2, r, material));
      g.add(cylinderBetween(c, p3, r, material));
      return g;
    }
    default:
      return null;
  }
}

function materialFor(type: TreeItem["type"]): THREE.Material {
  if (type === "VALV") return MAT.valve;
  if (type === "FLAN") return MAT.flange;
  if (type === "NOZZ") return MAT.nozzle;
  if (type === "SCTN") return MAT.structure;
  if (type === "PLAT") return MAT.platform;
  if (type === "CYLI" || type === "BOX" || type === "DISH" || type === "CONE") return MAT.equipment;
  return MAT.pipe;
}

export function buildItemMesh(item: TreeItem, selected: boolean): THREE.Object3D | null {
  const mesh = primitiveMesh(item, selected);
  if (!mesh) return null;
  mesh.userData.itemId = item.id;
  mesh.traverse((child) => {
    child.userData.itemId = item.id;
    if ((child as THREE.Mesh).isMesh) {
      (child as THREE.Mesh).castShadow = true;
      (child as THREE.Mesh).receiveShadow = true;
    }
  });
  return mesh;
}

export function itemCenter(item: TreeItem): THREE.Vector3 {
  const keys = ["x", "cx", "x1"];
  for (const key of keys) {
    if (item.props[key] !== undefined) {
      const x = n(item, key === "x1" ? "x1" : key === "cx" ? "cx" : "x");
      const y = n(item, key === "x1" ? "y1" : key === "cx" ? "cy" : "y");
      const z = n(item, key === "x1" ? "z1" : key === "cx" ? "cz" : "z");
      return new THREE.Vector3(x, y, z);
    }
  }
  return new THREE.Vector3();
}

export { MAT };
