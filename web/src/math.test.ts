import { describe, expect, it } from "vitest";
import { add, axisName, dist, norm, parsePoint, sub, v } from "./math";
import { exportPcf, importPcf } from "./pcf";
import { SAMPLE_PCF } from "./pcf.sample";
import { buildMto } from "./mto";
import { routePipe } from "./commands";
import { emptyProject } from "./project";
import { sampleProject } from "./sample";
import { elbowRadius } from "./specs";
import { buildIsoSvg } from "./iso";

describe("math", () => {
  it("adds and measures vectors", () => {
    expect(add(v(1, 2, 3), v(4, 5, 6))).toEqual({ x: 5, y: 7, z: 9 });
    expect(dist(v(0, 0, 0), v(3, 4, 0))).toBe(5);
    expect(axisName(v(0, 0, 10))).toBe("U");
    expect(axisName(v(-2, 0, 0))).toBe("W");
  });

  it("parses points", () => {
    expect(parsePoint("1000, 2000 3000")).toEqual({ x: 1000, y: 2000, z: 3000 });
    expect(norm(v(0, 0, 0))).toEqual({ x: 0, y: 0, z: 0 });
    expect(sub(v(5, 5, 5), v(1, 2, 3))).toEqual({ x: 4, y: 3, z: 2 });
  });
});

describe("pcf", () => {
  it("imports a pipeline and exports PCF text", () => {
    const doc = importPcf(SAMPLE_PCF);
    expect(doc.items.some((it) => it.type === "TUBE")).toBe(true);
    expect(doc.items.some((it) => it.type === "ELBO")).toBe(true);
    expect(doc.items.some((it) => it.type === "VALV")).toBe(true);
    const text = exportPcf(doc);
    expect(text).toContain("PIPELINE-REFERENCE");
    expect(text).toContain("ELBOW");
    expect(text).toContain("VALVE");
  });
});

describe("mto and iso", () => {
  it("aggregates sample plant materials", () => {
    const rows = buildMto(sampleProject());
    expect(rows.some((r) => r.type === "PIPE" && r.qty > 1)).toBe(true);
    expect(rows.some((r) => r.type === "ELBO")).toBe(true);
    expect(rows.some((r) => r.type === "EQUI")).toBe(true);
  });

  it("builds an isometric svg", () => {
    const svg = buildIsoSvg(sampleProject());
    expect(svg).toContain("<svg");
    expect(svg).toContain("ISOMETRIC");
  });
});

describe("routing", () => {
  it("creates tubes and elbows from a polyline", () => {
    const result = routePipe(emptyProject(), undefined, "80-P-9", [v(0, 0, 0), v(2000, 0, 0), v(2000, 0, 2000)], 80, "A1A");
    expect(result.doc.items.filter((it) => it.type === "TUBE").length).toBeGreaterThanOrEqual(2);
    expect(result.doc.items.some((it) => it.type === "ELBO")).toBe(true);
    expect(elbowRadius(80)).toBeGreaterThan(100);
  });
});
