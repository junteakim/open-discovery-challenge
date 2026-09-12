import type { Vec3 } from "./types";

export const EPS = 1e-6;

export function v(x: number, y: number, z: number): Vec3 {
  return { x, y, z };
}

export function add(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

export function sub(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

export function scale(a: Vec3, s: number): Vec3 {
  return { x: a.x * s, y: a.y * s, z: a.z * s };
}

export function dot(a: Vec3, b: Vec3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

export function cross(a: Vec3, b: Vec3): Vec3 {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x,
  };
}

export function len(a: Vec3): number {
  return Math.hypot(a.x, a.y, a.z);
}

export function dist(a: Vec3, b: Vec3): number {
  return len(sub(a, b));
}

export function norm(a: Vec3): Vec3 {
  const l = len(a);
  if (l < EPS) return { x: 0, y: 0, z: 0 };
  return scale(a, 1 / l);
}

export function lerp(a: Vec3, b: Vec3, t: number): Vec3 {
  return add(a, scale(sub(b, a), t));
}

export function eq(a: Vec3, b: Vec3, tol = 0.5): boolean {
  return dist(a, b) <= tol;
}

export function axisName(d: Vec3): "E" | "W" | "N" | "S" | "U" | "D" | "?" {
  const n = norm(d);
  const ax = Math.abs(n.x);
  const ay = Math.abs(n.y);
  const az = Math.abs(n.z);
  if (ax >= ay && ax >= az) return n.x >= 0 ? "E" : "W";
  if (ay >= ax && ay >= az) return n.y >= 0 ? "N" : "S";
  if (az >= ax && az >= ay) return n.z >= 0 ? "U" : "D";
  return "?";
}

export function parsePoint(raw: string): Vec3 | null {
  const parts = raw
    .trim()
    .split(/[,\s]+/)
    .map(Number)
    .filter((n) => Number.isFinite(n));
  if (parts.length < 3) return null;
  return { x: parts[0], y: parts[1], z: parts[2] };
}

export function fmt(n: number, digits = 0): string {
  return n.toFixed(digits);
}

export function uid(prefix = "id"): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}
