import { dist, v } from "./math";
import { buildMto } from "./mto";
import type { ProjectDoc, TreeItem } from "./types";

function num(item: TreeItem, key: string, fallback = 0): number {
  const value = item.props[key];
  return typeof value === "number" ? value : Number(value ?? fallback) || fallback;
}

function isoProject(x: number, y: number, z: number): { x: number; y: number } {
  const c = Math.cos(Math.PI / 6);
  const s = Math.sin(Math.PI / 6);
  return { x: (x - y) * c, y: -z - (x + y) * s };
}

function pipingItems(doc: ProjectDoc, rootId?: string): TreeItem[] {
  const types = new Set(["TUBE", "ELBO", "VALV", "FLAN", "TEE", "REDU", "CAP"]);
  return doc.items.filter((it) => {
    if (!types.has(it.type)) return false;
    if (!rootId) return true;
    let cur: TreeItem | undefined = it;
    while (cur) {
      if (cur.id === rootId) return true;
      cur = doc.items.find((x) => x.id === cur?.parentId);
    }
    return false;
  });
}

export function buildIsoSvg(doc: ProjectDoc, rootId?: string): string {
  const items = pipingItems(doc, rootId);
  const pts: { x: number; y: number }[] = [];
  const segs: { a: { x: number; y: number }; b: { x: number; y: number }; type: string; label?: string }[] = [];

  for (const it of items) {
    if (it.type === "FLAN") {
      const p = isoProject(num(it, "x"), num(it, "y"), num(it, "z"));
      pts.push(p);
      continue;
    }
    const a = isoProject(num(it, "x1"), num(it, "y1"), num(it, "z1"));
    const b = isoProject(num(it, "x2"), num(it, "y2"), num(it, "z2"));
    pts.push(a, b);
    const length = dist(
      v(num(it, "x1"), num(it, "y1"), num(it, "z1")),
      v(num(it, "x2"), num(it, "y2"), num(it, "z2")),
    );
    segs.push({
      a,
      b,
      type: it.type,
      label: it.type === "TUBE" && length > 200 ? `${Math.round(length)}` : it.type === "VALV" ? String(it.props.kind ?? "VALVE") : undefined,
    });
  }

  if (!pts.length) {
    return emptySheet(doc, "배관 부재가 없습니다. PIPE를 선택하거나 샘플을 불러오세요.");
  }

  const minX = Math.min(...pts.map((p) => p.x));
  const maxX = Math.max(...pts.map((p) => p.x));
  const minY = Math.min(...pts.map((p) => p.y));
  const maxY = Math.max(...pts.map((p) => p.y));
  const pad = 80;
  const boxW = 1180;
  const boxH = 620;
  const w = Math.max(maxX - minX, 1);
  const h = Math.max(maxY - minY, 1);
  const scale = Math.min((boxW - pad * 2) / w, (boxH - pad * 2) / h);
  const ox = 80 + pad + (boxW - pad * 2 - w * scale) / 2;
  const oy = 70 + pad + (boxH - pad * 2 - h * scale) / 2;
  const tx = (p: { x: number; y: number }) => ox + (p.x - minX) * scale;
  const ty = (p: { x: number; y: number }) => oy + (p.y - minY) * scale;

  const paths = segs
    .map((seg) => {
      const color =
        seg.type === "VALV" ? "#c0392b" : seg.type === "ELBO" ? "#e67e22" : "#1a5276";
      const width = seg.type === "VALV" ? 6 : 3;
      const x1 = tx(seg.a);
      const y1 = ty(seg.a);
      const x2 = tx(seg.b);
      const y2 = ty(seg.b);
      let extra = "";
      if (seg.label) {
        extra = `<text x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2 - 8}" font-size="11" fill="#1c2833" text-anchor="middle">${esc(seg.label)}</text>`;
      }
      if (seg.type === "VALV") {
        extra += `<rect x="${(x1 + x2) / 2 - 7}" y="${(y1 + y2) / 2 - 7}" width="14" height="14" fill="#c0392b" transform="rotate(45 ${(x1 + x2) / 2} ${(y1 + y2) / 2})"/>`;
      }
      return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${width}" stroke-linecap="round"/>${extra}`;
    })
    .join("\n");

  const mto = buildMto(doc, rootId).filter((r) => r.type !== "EQUI" && r.type !== "SCTN").slice(0, 8);
  const rows = mto
    .map(
      (r, i) =>
        `<text x="976" y="${136 + i * 18}" font-size="12" font-family="Noto Sans KR, Segoe UI, sans-serif" fill="#1c2833">${esc(r.type.padEnd(5))} ${String(r.bore).padStart(4)}  ${r.qty.toFixed(1).padStart(6)}${r.unit.padEnd(3)}  ${esc(r.description.slice(0, 26))}</text>`,
    )
    .join("\n");

  const title = rootId
    ? doc.items.find((it) => it.id === rootId)?.name ?? doc.name
    : doc.name;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 900" width="1400" height="900">
  <rect width="1400" height="900" fill="#f4f1ea"/>
  <rect x="24" y="24" width="1352" height="852" fill="none" stroke="#1c2833" stroke-width="2"/>
  <rect x="32" y="32" width="1336" height="836" fill="none" stroke="#1c2833" stroke-width="1"/>
  <text x="48" y="58" font-size="20" font-family="Segoe UI, sans-serif" fill="#1c2833">PIPECAD WEB  ·  PIPING ISOMETRIC</text>
  <text x="48" y="80" font-size="13" fill="#566573">${esc(doc.description)}</text>
  ${paths}
  <rect x="960" y="90" width="400" height="220" fill="#fff" stroke="#1c2833"/>
  <text x="980" y="112" font-size="13" font-weight="700">BILL OF MATERIALS</text>
  ${rows}
  <rect x="960" y="720" width="400" height="128" fill="#fff" stroke="#1c2833"/>
  <text x="980" y="748" font-size="12">LINE  ${esc(title)}</text>
  <text x="980" y="770" font-size="12">SPEC  ${esc(doc.spec)}    UNIT  MM</text>
  <text x="980" y="792" font-size="12">PROJ  ${esc(doc.name)} / ${esc(doc.code)}</text>
  <text x="980" y="814" font-size="12">DRAWN  PipeCAD Web    DATE  ${new Date().toISOString().slice(0, 10)}</text>
  <g transform="translate(60 780)">
    <polygon points="0,30 40,30 20,0" fill="#1c2833"/>
    <text x="48" y="20" font-size="11">N</text>
    <text x="70" y="38" font-size="11">ISO VIEW  ·  Z UP</text>
  </g>
</svg>`;
}

function emptySheet(doc: ProjectDoc, message: string): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 900" width="1400" height="900">
  <rect width="1400" height="900" fill="#f4f1ea"/>
  <text x="80" y="80" font-size="22">PIPECAD WEB  ·  ISOMETRIC</text>
  <text x="80" y="120" font-size="16">${esc(message)}</text>
  <text x="80" y="160" font-size="14">${esc(doc.name)}</text>
</svg>`;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
