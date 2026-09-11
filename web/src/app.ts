import {
  addValveOnTube,
  placeBeam,
  placeColumn,
  placeExchanger,
  placeGrid,
  placePlatform,
  placePump,
  placeTank,
  placeVessel,
  routePipe,
} from "./commands";
import { buildIsoSvg } from "./iso";
import { parsePoint, v } from "./math";
import { buildMto, mtoCsv } from "./mto";
import { exportPcf, importPcf } from "./pcf";
import {
  ancestors,
  childrenOf,
  emptyProject,
  findItem,
  firstOfType,
  nextName,
  removeSubtree,
  setVisible,
  updateItem,
} from "./project";
import { sampleProject } from "./sample";
import { PIPING_SPECS, PROFILES } from "./specs";
import { TYPE_LABEL, type MeasureResult, type ProjectDoc, type ToolMode, type TreeItem, type Vec3 } from "./types";
import { createViewport, type ViewportApi } from "./viewport";

const SAMPLE_USER = "SYSTEM";
const SAMPLE_PASS = "XXXXXX";

interface AppState {
  screen: "login" | "design";
  user: string;
  module: "Design" | "Admin" | "Paragon";
  doc: ProjectDoc;
  selectedId: string | null;
  tab: "home" | "grid" | "equi" | "stru" | "pipe" | "draft" | "tools";
  tool: ToolMode;
  status: string;
  measurePts: Vec3[];
  measure: MeasureResult | null;
  routePts: Vec3[];
  dialog: null | { kind: string; title: string };
  error: string;
}

export function startApp(root: HTMLElement) {
  let state: AppState = {
    screen: "login",
    user: SAMPLE_USER,
    module: "Design",
    doc: sampleProject(),
    selectedId: null,
    tab: "home",
    tool: "select",
    status: "SAMPLE 프로젝트 — 사용자 SYSTEM",
    measurePts: [],
    measure: null,
    routePts: [],
    dialog: null,
    error: "",
  };

  let viewport: ViewportApi | null = null;
  let shellReady = false;
  const fileInput = Object.assign(document.createElement("input"), {
    type: "file",
    accept: ".json,.pcf,.idf,application/json,text/plain",
  });
  fileInput.className = "hidden";
  document.body.appendChild(fileInput);

  const set = (patch: Partial<AppState>) => {
    state = { ...state, ...patch };
    paint();
  };

  const setDoc = (doc: ProjectDoc, extra: Partial<AppState> = {}) => {
    state = { ...state, doc, ...extra };
    paint();
  };

  function paint() {
    if (state.screen === "login") {
      teardownDesign();
      root.innerHTML = loginHtml(state);
      bindLogin();
      return;
    }
    if (!shellReady) {
      root.innerHTML = workspaceShell();
      const canvas = root.querySelector("canvas") as HTMLCanvasElement;
      viewport = createViewport(canvas);
      canvas.addEventListener("pointerdown", onPointer);
      window.addEventListener("resize", onResize);
      bindShell();
      shellReady = true;
    }
    syncWorkspace();
  }

  function teardownDesign() {
    viewport?.dispose();
    viewport = null;
    shellReady = false;
    window.removeEventListener("resize", onResize);
  }

  function onResize() {
    viewport?.resize();
  }

  function syncWorkspace() {
    const selected = findItem(state.doc, state.selectedId) ?? null;
    const brand = root.querySelector("[data-proj]")!;
    brand.textContent = `${state.doc.name} / ${state.doc.code}`;
    root.querySelector("[data-session]")!.textContent =
      `${state.module}  ·  ${state.user}  ·  ${state.doc.spec}  ·  MM`;
    root.querySelector("[data-ribbon]")!.innerHTML = ribbonInner(state);
    root.querySelector("[data-tree]")!.innerHTML = treeHtml(state.doc, "world", 0, state.selectedId);
    root.querySelector("[data-props]")!.innerHTML = propsHtml(selected);
    root.querySelector("[data-hud]")!.innerHTML = `${escapeHtml(state.status)}${state.tool === "route" ? routeHud(state) : ""}`;
    root.querySelector("[data-status-tool]")!.textContent = state.tool.toUpperCase();
    root.querySelector("[data-status-count]")!.textContent = `${state.doc.items.length} items`;
    root.querySelector("[data-status-path]")!.textContent = selected
      ? ancestors(state.doc, selected.id).map((i) => i.name).join(" / ")
      : "";
    root.querySelector("[data-dialogs]")!.innerHTML = dialogHtml(state, selected);
    bindDynamic(selected);
    viewport?.render(state.doc, state.selectedId);
    viewport?.setMeasure(state.measure);
    viewport?.resize();
  }

  function onPointer(ev: PointerEvent) {
    if (ev.button !== 0) return;
    if (state.tool === "measure") {
      const p = viewport?.worldOnGrid(ev.clientX, ev.clientY);
      if (!p) return;
      const pts = [...state.measurePts, p];
      if (pts.length >= 2) {
        const [a, b] = pts.slice(-2);
        const measure = {
          a,
          b,
          dx: b.x - a.x,
          dy: b.y - a.y,
          dz: b.z - a.z,
          distance: Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z),
        };
        set({
          measurePts: [],
          measure,
          status: `거리 ${Math.round(measure.distance)} mm  ΔX ${Math.round(measure.dx)}  ΔY ${Math.round(measure.dy)}  ΔZ ${Math.round(measure.dz)}`,
        });
      } else {
        set({ measurePts: pts, status: "두 번째 점을 클릭하세요" });
      }
      return;
    }
    if (state.tool === "route") {
      const p = viewport?.worldOnGrid(ev.clientX, ev.clientY);
      if (!p) return;
      const z = Number((root.querySelector("[data-route-z]") as HTMLInputElement | null)?.value ?? 1000);
      set({
        routePts: [...state.routePts, { ...p, z }],
        status: `라우트 점 ${state.routePts.length + 1}개 — Enter로 배관 생성, Esc로 취소`,
      });
      return;
    }
    const id = viewport?.pick(ev.clientX, ev.clientY);
    if (id) {
      const item = findItem(state.doc, id);
      set({ selectedId: id, status: item ? `${item.type}  ${item.name}` : id });
    }
  }

  function bindLogin() {
    root.querySelector("#login-btn")?.addEventListener("click", () => {
      const user = (root.querySelector("#user") as HTMLInputElement).value.trim();
      const pass = (root.querySelector("#pass") as HTMLInputElement).value;
      const module = (root.querySelector("#module") as HTMLSelectElement).value as AppState["module"];
      const project = (root.querySelector("#project") as HTMLSelectElement).value;
      if (user.toUpperCase() !== SAMPLE_USER || pass !== SAMPLE_PASS) {
        set({ error: "샘플 프로젝트는 SYSTEM / XXXXXX 로 로그인하세요." });
        return;
      }
      const doc = project === "blank" ? emptyProject("NEW", "NEW") : sampleProject();
      set({
        screen: "design",
        user,
        module,
        doc,
        selectedId: firstOfType(doc, "ZONE")?.id ?? "world",
        error: "",
        status: `${doc.name}  ·  ${module}  ·  ${user}`,
      });
    });
  }

  function bindShell() {
    root.querySelector("[data-cmd='save-top']")?.addEventListener("click", () => runCommand("save", null));
    root.querySelector("[data-cmd='open-top']")?.addEventListener("click", () => runCommand("open", null));
    root.querySelector("#logout")?.addEventListener("click", () => {
      teardownDesign();
      set({ screen: "login", dialog: null, tool: "select" });
    });
    root.querySelectorAll("[data-view]").forEach((btn) => {
      btn.addEventListener("click", () => viewport?.setView((btn as HTMLElement).dataset.view as "iso"));
    });
    root.querySelector("[data-cmd='fit-view']")?.addEventListener("click", () => viewport?.fit(state.doc, state.selectedId));
    window.addEventListener("keydown", onKey);
  }

  function onKey(ev: KeyboardEvent) {
    if (state.screen !== "design") return;
    if (ev.key === "Escape") {
      set({ tool: "select", routePts: [], measurePts: [], dialog: null, status: "선택 모드" });
    }
    if (ev.key === "Delete" && state.selectedId && state.selectedId !== "world") {
      const next = removeSubtree(state.doc, state.selectedId);
      setDoc(next, { selectedId: firstOfType(next, "ZONE")?.id ?? "world", status: "삭제됨" });
    }
    if (ev.key === "Enter" && state.tool === "route" && state.routePts.length >= 2) {
      finishRoute(findItem(state.doc, state.selectedId) ?? null);
    }
    if (ev.key.toLowerCase() === "f" && !isTyping(ev)) viewport?.fit(state.doc, state.selectedId);
  }

  function bindDynamic(selected: TreeItem | null) {
    root.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => set({ tab: (btn as HTMLElement).dataset.tab as AppState["tab"] }));
    });
    root.querySelectorAll("[data-cmd]").forEach((btn) => {
      btn.addEventListener("click", () => runCommand((btn as HTMLElement).dataset.cmd!, selected));
    });
    root.querySelectorAll("[data-tree]").forEach((el) => {
      el.addEventListener("click", () => set({ selectedId: (el as HTMLElement).dataset.tree! }));
    });
    root.querySelectorAll("[data-vis]").forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const id = (el as HTMLElement).dataset.vis!;
        const item = findItem(state.doc, id);
        if (item) setDoc(setVisible(state.doc, id, !item.visible));
      });
    });
    root.querySelector("#prop-apply")?.addEventListener("click", () => {
      if (!selected) return;
      const name = (root.querySelector("#prop-name") as HTMLInputElement).value;
      const props: TreeItem["props"] = {};
      root.querySelectorAll("[data-prop]").forEach((input) => {
        const key = (input as HTMLInputElement).dataset.prop!;
        const raw = (input as HTMLInputElement).value;
        props[key] = raw === "" || Number.isNaN(Number(raw)) ? raw : Number(raw);
      });
      setDoc(updateItem(state.doc, selected.id, { name, props }), { status: `${name} 속성 적용` });
    });
    root.querySelector("#dlg-cancel")?.addEventListener("click", () => set({ dialog: null }));
    root.querySelector("#dlg-ok")?.addEventListener("click", () => applyDialog(selected));
    root.querySelector("#sheet-close")?.addEventListener("click", () => set({ dialog: null }));
    root.querySelector("#mto-export")?.addEventListener("click", () => {
      download(`${state.doc.name}-mto.csv`, mtoCsv(buildMto(state.doc, selected?.id)), "text/csv");
    });
    root.querySelector("#iso-export")?.addEventListener("click", () => {
      const svg = buildIsoSvg(state.doc, selected && ["PIPE", "BRAN"].includes(selected.type) ? selected.id : undefined);
      download(`${state.doc.name}.iso.svg`, svg, "image/svg+xml");
    });
    root.querySelector("[data-cmd='start-route']")?.addEventListener("click", () => {
      set({ tool: "route", routePts: [], dialog: null, status: "뷰에서 점을 클릭한 뒤 Enter" });
    });
  }

  function runCommand(cmd: string, selected: TreeItem | null) {
    switch (cmd) {
      case "sample": {
        const doc = sampleProject();
        setDoc(doc, { selectedId: firstOfType(doc, "ZONE")?.id ?? "world", status: "SAMPLE 프로젝트 로드" });
        break;
      }
      case "new":
        setDoc(emptyProject(), { selectedId: "world", status: "새 프로젝트" });
        break;
      case "save":
      case "save-top":
        download(`${state.doc.name}.pipecad.json`, JSON.stringify(state.doc, null, 2), "application/json");
        set({ status: "프로젝트 JSON 저장" });
        break;
      case "open":
      case "open-top":
        fileInput.onchange = async () => {
          const file = fileInput.files?.[0];
          fileInput.value = "";
          if (!file) return;
          const text = await file.text();
          if (/\.(pcf|idf)$/i.test(file.name)) {
            const doc = importPcf(text, file.name.replace(/\.[^.]+$/, ""));
            setDoc(doc, { selectedId: firstOfType(doc, "PIPE")?.id ?? "world", status: `PCF 가져옴 · ${file.name}` });
          } else {
            const doc = JSON.parse(text) as ProjectDoc;
            setDoc(doc, { selectedId: "world", status: `열림 · ${file.name}` });
          }
        };
        fileInput.click();
        break;
      case "pcf-out":
        download(`${selected?.name ?? state.doc.name}.pcf`, exportPcf(state.doc, selected?.id), "text/plain");
        set({ status: "PCF 내보내기" });
        break;
      case "iso":
        set({ dialog: { kind: "iso", title: "배관 축측도 ISO" } });
        break;
      case "mto":
        set({ dialog: { kind: "mto", title: "재료 집계 MTO" } });
        break;
      case "draft":
        set({ dialog: { kind: "draft", title: "평면도 DRAFT" } });
        break;
      case "measure":
        set({ tool: "measure", measurePts: [], status: "거리 측정: 두 점을 클릭하세요" });
        break;
      case "fit":
        viewport?.fit(state.doc, state.selectedId);
        break;
      case "grid":
        set({ dialog: { kind: "grid", title: "축망 GRID" } });
        break;
      case "vessel":
        set({ dialog: { kind: "vessel", title: "수직 용기 VESSEL" } });
        break;
      case "tank":
        set({ dialog: { kind: "tank", title: "탱크 TANK" } });
        break;
      case "pump":
        set({ dialog: { kind: "pump", title: "펌프 PUMP" } });
        break;
      case "exchanger":
        set({ dialog: { kind: "exchanger", title: "열교환기 EXCHANGER" } });
        break;
      case "column":
        set({ dialog: { kind: "column", title: "기둥 COLUMN" } });
        break;
      case "beam":
        set({ dialog: { kind: "beam", title: "보 BEAM" } });
        break;
      case "platform":
        set({ dialog: { kind: "platform", title: "플랫폼 PLATFORM" } });
        break;
      case "pipe":
        set({ dialog: { kind: "pipe", title: "배관 라우트 PIPE" } });
        break;
      case "valve":
        if (selected?.type === "TUBE") setDoc(addValveOnTube(state.doc, selected, "GATE"), { status: "게이트 밸브 추가" });
        else set({ status: "밸브를 넣으려면 TUBE를 선택하세요" });
        break;
      case "check":
        if (selected?.type === "TUBE") setDoc(addValveOnTube(state.doc, selected, "CHECK"), { status: "체크 밸브 추가" });
        else set({ status: "밸브를 넣으려면 TUBE를 선택하세요" });
        break;
      case "delete":
        if (selected && selected.id !== "world") {
          const next = removeSubtree(state.doc, selected.id);
          setDoc(next, { selectedId: selected.parentId ?? "world", status: "삭제됨" });
        }
        break;
      default:
        break;
    }
  }

  function applyDialog(selected: TreeItem | null) {
    const values = collectFields();
    const pos = parsePoint(values.pos || "0 0 0") ?? v(0, 0, 0);
    const kind = state.dialog?.kind;
    let result = { doc: state.doc, id: selected?.id ?? "world" };
    if (kind === "vessel") {
      result = placeVessel(state.doc, selected ?? undefined, values.name || nextName(state.doc, "V"), pos, Number(values.diameter || 1600), Number(values.height || 6000));
    } else if (kind === "tank") {
      result = placeTank(state.doc, selected ?? undefined, values.name || nextName(state.doc, "T"), pos, Number(values.diameter || 2800), Number(values.height || 3600));
    } else if (kind === "pump") {
      result = placePump(state.doc, selected ?? undefined, values.name || nextName(state.doc, "P"), pos);
    } else if (kind === "exchanger") {
      result = placeExchanger(state.doc, selected ?? undefined, values.name || nextName(state.doc, "E"), pos);
    } else if (kind === "column") {
      result = placeColumn(state.doc, selected ?? undefined, pos, Number(values.height || 4000), values.profile || PROFILES[0].name);
    } else if (kind === "beam") {
      const b = parsePoint(values.pos2 || "4000 0 4000") ?? v(4000, 0, 4000);
      result = placeBeam(state.doc, selected ?? undefined, pos, b, values.profile || PROFILES[0].name);
    } else if (kind === "platform") {
      result = placePlatform(state.doc, selected ?? undefined, pos, Number(values.lx || 2400), Number(values.ly || 2400));
    } else if (kind === "grid") {
      result = placeGrid(state.doc, selected ?? undefined, values);
    } else if (kind === "pipe") {
      const pts = (values.points || "")
        .split("\n")
        .map((line) => parsePoint(line))
        .filter((p): p is Vec3 => !!p);
      result = routePipe(state.doc, selected ?? undefined, values.name || nextName(state.doc, "P"), pts, Number(values.bore || 80), values.spec || state.doc.spec);
    }
    setDoc(result.doc, { selectedId: result.id, dialog: null, status: `${state.dialog?.title ?? "항목"} 생성` });
    viewport?.fit(result.doc, result.id);
  }

  function finishRoute(selected: TreeItem | null) {
    const bore = Number((root.querySelector("[data-route-bore]") as HTMLInputElement | null)?.value ?? 80);
    const spec = (root.querySelector("[data-route-spec]") as HTMLSelectElement | null)?.value ?? state.doc.spec;
    const result = routePipe(state.doc, selected ?? undefined, nextName(state.doc, `${bore}-P`), state.routePts, bore, spec);
    setDoc(result.doc, { selectedId: result.id, tool: "select", routePts: [], status: "배관 라우트 생성" });
  }

  function collectFields(): Record<string, string> {
    const values: Record<string, string> = {};
    root.querySelectorAll("[data-field]").forEach((el) => {
      values[(el as HTMLInputElement).dataset.field!] = (el as HTMLInputElement).value;
    });
    return values;
  }

  paint();
}

function isTyping(ev: KeyboardEvent): boolean {
  const t = ev.target as HTMLElement | null;
  return !!t && ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName);
}

function download(name: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

function loginHtml(state: AppState): string {
  return `
  <section class="login">
    <div class="login-card">
      <div class="login-hero">
        <h1>PIPE<em>CAD</em> WEB</h1>
        <p>플랜트 배관 설계용 브라우저 CAD입니다. 데스크톱 PipeCAD의 공개 기능(축망, 설비, 구조, 배관, ISO, MTO, PCF)을 웹에서 바로 모델링합니다.</p>
        <p class="hint">샘플 로그인: <b>SYSTEM</b> / <b>XXXXXX</b><br/>원본 릴리스: github.com/eryar/PipeCAD/releases</p>
      </div>
      <div class="login-form">
        <label>프로젝트
          <select id="project">
            <option value="sample">SAMPLE — Process Unit</option>
            <option value="blank">NEW — 빈 프로젝트</option>
          </select>
        </label>
        <label>사용자 <input id="user" value="SYSTEM" /></label>
        <label>비밀번호 <input id="pass" type="password" value="XXXXXX" /></label>
        <label>모듈
          <select id="module">
            <option>Design</option>
            <option>Paragon</option>
            <option>Admin</option>
          </select>
        </label>
        <div class="error">${escapeHtml(state.error)}</div>
        <button id="login-btn" type="button">모듈 시작</button>
      </div>
    </div>
  </section>`;
}

function workspaceShell(): string {
  return `
  <section class="workspace">
    <header class="topbar">
      <div class="brand">PIPE<em>CAD</em> WEB</div>
      <div data-proj></div>
      <div class="session" data-session></div>
      <button data-cmd="save-top">저장</button>
      <button data-cmd="open-top">열기</button>
      <button id="logout">로그아웃</button>
    </header>
    <div class="ribbon" data-ribbon></div>
    <div class="main">
      <aside class="tree">
        <div class="panel-h">CE 트리</div>
        <div class="tree-list" data-tree></div>
      </aside>
      <div class="viewport">
        <canvas></canvas>
        <div class="view-btns">
          <button data-view="iso">ISO</button>
          <button data-view="top">TOP</button>
          <button data-view="front">FRONT</button>
          <button data-view="east">EAST</button>
          <button data-view="west">WEST</button>
          <button data-cmd="fit-view">FIT</button>
        </div>
        <div class="hud" data-hud></div>
      </div>
      <aside class="props">
        <div class="panel-h">속성</div>
        <div data-props></div>
      </aside>
    </div>
    <footer class="status">
      <span data-status-tool></span>
      <span data-status-count></span>
      <span data-status-path></span>
    </footer>
    <div data-dialogs></div>
  </section>`;
}

function routeHud(state: AppState): string {
  return `<div style="margin-top:8px;display:flex;gap:8px;align-items:center">
    구경 <input data-route-bore type="number" value="80" style="width:64px;background:#0d1520;border:1px solid #2a3f55;padding:3px"/>
    SPEC <select data-route-spec>${PIPING_SPECS.map((s) => `<option ${s === state.doc.spec ? "selected" : ""}>${s}</option>`).join("")}</select>
    Z <input data-route-z type="number" value="1000" style="width:72px;background:#0d1520;border:1px solid #2a3f55;padding:3px"/>
    점 ${state.routePts.length} · Enter 생성
  </div>`;
}

function ribbonInner(state: AppState): string {
  const tabs = [
    ["home", "Home"],
    ["grid", "Grid"],
    ["equi", "Equipment"],
    ["stru", "Structure"],
    ["pipe", "Piping"],
    ["draft", "Draft"],
    ["tools", "Tools"],
  ] as const;
  const body: Record<string, string> = {
    home: group("프로젝트", [cmd("sample", "샘플"), cmd("new", "새 파일"), cmd("open", "열기"), cmd("save", "저장")]) + group("선택", [cmd("fit", "맞춤"), cmd("delete", "삭제")]),
    grid: group("축망", [cmd("grid", "GRID")]),
    equi: group("설비", [cmd("vessel", "용기"), cmd("tank", "탱크"), cmd("pump", "펌프"), cmd("exchanger", "열교환기")]),
    stru: group("구조", [cmd("column", "기둥"), cmd("beam", "보"), cmd("platform", "플랫폼")]),
    pipe: group("배관", [cmd("pipe", "라우트"), cmd("valve", "게이트"), cmd("check", "체크")]) + group("내보내기", [cmd("pcf-out", "PCF")]),
    draft: group("산출물", [cmd("iso", "ISO 축측도"), cmd("draft", "평면도"), cmd("mto", "MTO")]),
    tools: group("측정", [cmd("measure", "거리")]) + group("파일", [cmd("pcf-out", "PCF 내보내기"), cmd("open", "PCF 가져오기")]),
  };
  return `<div class="ribbon-tabs">${tabs.map(([id, label]) => `<button data-tab="${id}" class="${state.tab === id ? "active" : ""}">${label}</button>`).join("")}</div>
    <div class="ribbon-body">${body[state.tab]}</div>`;
}

function cmd(id: string, label: string): string {
  return `<button type="button" data-cmd="${id}">${label}</button>`;
}

function group(title: string, buttons: string[]): string {
  return `<div class="rgroup"><h4>${title}</h4><div class="rbtns">${buttons.join("")}</div></div>`;
}

function treeHtml(doc: ProjectDoc, id: string, depth: number, selectedId: string | null): string {
  const item = findItem(doc, id);
  if (!item) return "";
  const kids = childrenOf(doc, id);
  return `<div class="tree-item ${item.id === selectedId ? "sel" : ""}" data-tree="${item.id}" style="--pad:${8 + depth * 14}px">
    <span class="badge">${item.type}</span>
    <span>${escapeHtml(item.name)}</span>
    <span data-vis="${item.id}" title="표시">${item.visible ? "●" : "○"}</span>
  </div>${kids.map((c) => treeHtml(doc, c.id, depth + 1, selectedId)).join("")}`;
}

function propsHtml(item: TreeItem | null): string {
  if (!item) return `<p class="hint" style="padding:12px">항목을 선택하세요.</p>`;
  const skip = new Set(["description"]);
  const fields = Object.entries(item.props)
    .filter(([k]) => !skip.has(k))
    .map(([k, val]) => `<dt>${escapeHtml(k)}</dt><dd><input data-prop="${escapeHtml(k)}" value="${escapeHtml(String(val))}" /></dd>`)
    .join("");
  return `<dl>
    <dt>이름</dt><dd><input id="prop-name" value="${escapeHtml(item.name)}" /></dd>
    <dt>타입</dt><dd>${item.type} · ${TYPE_LABEL[item.type]}</dd>
    ${fields}
    <dt></dt><dd><button id="prop-apply" type="button">적용</button></dd>
  </dl>`;
}

function dialogHtml(state: AppState, selected: TreeItem | null): string {
  if (!state.dialog) return "";
  if (state.dialog.kind === "iso") {
    const svg = buildIsoSvg(state.doc, selected && ["PIPE", "BRAN"].includes(selected.type) ? selected.id : undefined);
    return `<div class="overlay"><div class="sheet">
      <header><strong>${state.dialog.title}</strong><span><button id="iso-export" type="button">SVG</button> <button id="sheet-close" type="button">닫기</button></span></header>
      <div class="iso-frame">${svg}</div>
    </div></div>`;
  }
  if (state.dialog.kind === "mto") {
    const rows = buildMto(state.doc, selected?.id);
    return `<div class="overlay"><div class="sheet">
      <header><strong>${state.dialog.title}</strong><span><button id="mto-export" type="button">CSV</button> <button id="sheet-close" type="button">닫기</button></span></header>
      <div style="overflow:auto;flex:1;padding:12px">
        <table><thead><tr><th>Type</th><th>Description</th><th>Spec</th><th>Bore</th><th>Qty</th><th>Unit</th><th>kg</th></tr></thead>
        <tbody>${rows.map((r) => `<tr><td>${r.type}</td><td>${escapeHtml(r.description)}</td><td>${r.spec}</td><td>${r.bore}</td><td>${r.qty.toFixed(2)}</td><td>${r.unit}</td><td>${r.weight.toFixed(1)}</td></tr>`).join("")}</tbody></table>
      </div>
    </div></div>`;
  }
  if (state.dialog.kind === "draft") {
    return `<div class="overlay"><div class="sheet">
      <header><strong>${state.dialog.title}</strong><span><button id="sheet-close" type="button">닫기</button></span></header>
      <div class="iso-frame">${buildDraftSvg(state.doc)}</div>
    </div></div>`;
  }
  return `<div class="overlay"><div class="dialog">
    <h3>${state.dialog.title}</h3>
    <div class="grid">${dialogFields(state.dialog.kind)}</div>
    <div class="actions">
      ${state.dialog.kind === "pipe" ? `<button data-cmd="start-route" type="button">3D에서 찍기</button>` : ""}
      <button id="dlg-cancel" type="button">취소</button>
      <button id="dlg-ok" class="ok" type="button">생성</button>
    </div>
  </div></div>`;
}

function dialogFields(kind: string): string {
  const field = (id: string, label: string, value: string) =>
    `<label>${label}<input data-field="${id}" value="${escapeHtml(value)}" /></label>`;
  if (kind === "grid") {
    return field("name", "이름", "GRID-B") + field("nx", "X 개수", "4") + field("ny", "Y 개수", "3") + field("nz", "Z 개수", "3") + field("sx", "X 간격", "4000") + field("sy", "Y 간격", "4000");
  }
  if (kind === "vessel" || kind === "tank") {
    return field("name", "이름", kind === "vessel" ? "V-201" : "T-201") + field("pos", "위치 X Y Z", "4000 4000 0") + field("diameter", "직경", kind === "vessel" ? "1600" : "2800") + field("height", "높이", kind === "vessel" ? "6000" : "3600");
  }
  if (kind === "pump" || kind === "exchanger") {
    return field("name", "이름", kind === "pump" ? "P-201" : "E-201") + field("pos", "위치 X Y Z", "8000 2000 0");
  }
  if (kind === "column") {
    return field("pos", "위치 X Y Z", "1000 1000 0") + field("height", "높이", "4000") + `<label>형강<select data-field="profile">${PROFILES.map((p) => `<option>${p.name}</option>`).join("")}</select></label>`;
  }
  if (kind === "beam") {
    return field("pos", "시작 X Y Z", "1000 1000 4000") + field("pos2", "끝 X Y Z", "5000 1000 4000") + `<label>형강<select data-field="profile">${PROFILES.map((p) => `<option>${p.name}</option>`).join("")}</select></label>`;
  }
  if (kind === "platform") {
    return field("pos", "중심 X Y Z", "2000 2000 4000") + field("lx", "길이 X", "2400") + field("ly", "길이 Y", "2400");
  }
  if (kind === "pipe") {
    return field("name", "라인", "80-P-201") + field("bore", "구경", "80") + `<label>SPEC<select data-field="spec">${PIPING_SPECS.map((s) => `<option>${s}</option>`).join("")}</select></label>` +
      `<label style="grid-column:1/-1">경로 (한 줄에 X Y Z)<textarea data-field="points" rows="6">0 0 1000
4000 0 1000
4000 3000 1000
4000 3000 2000</textarea></label>`;
  }
  return field("name", "이름", "ITEM");
}

function buildDraftSvg(doc: ProjectDoc): string {
  const items = doc.items.filter((it) => ["TUBE", "ELBO", "CYLI", "BOX", "SCTN", "PLAT"].includes(it.type));
  const xs: number[] = [];
  const ys: number[] = [];
  const segs: { x1: number; y1: number; x2: number; y2: number; type: string }[] = [];
  for (const it of items) {
    const x1 = Number(it.props.x ?? it.props.x1 ?? it.props.cx ?? 0);
    const y1 = Number(it.props.y ?? it.props.y1 ?? it.props.cy ?? 0);
    const x2 = Number(it.props.x2 ?? x1);
    const y2 = Number(it.props.y2 ?? y1);
    xs.push(x1, x2);
    ys.push(y1, y2);
    segs.push({ x1, y1, x2, y2, type: it.type });
  }
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);
  const s = Math.min(1100 / Math.max(maxX - minX, 1), 700 / Math.max(maxY - minY, 1));
  const mapX = (x: number) => 80 + (x - minX) * s;
  const mapY = (y: number) => 780 - (y - minY) * s;
  const lines = segs
    .map((seg) => {
      const color = seg.type === "CYLI" || seg.type === "BOX" ? "#2874a6" : seg.type === "SCTN" ? "#7f8c8d" : "#b9770e";
      return `<line x1="${mapX(seg.x1)}" y1="${mapY(seg.y1)}" x2="${mapX(seg.x2)}" y2="${mapY(seg.y2)}" stroke="${color}" stroke-width="2"/>`;
    })
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 900" width="1400" height="900">
    <rect width="1400" height="900" fill="#f4f1ea"/>
    <text x="48" y="48" font-size="20" fill="#1c2833">PIPECAD WEB  ·  PLOT PLAN</text>
    <text x="48" y="72" font-size="13">${escapeHtml(doc.name)} / ${escapeHtml(doc.description)}</text>
    ${lines}
    <rect x="960" y="720" width="400" height="128" fill="#fff" stroke="#1c2833"/>
    <text x="980" y="750" font-size="12">VIEW  PLAN  Z+</text>
    <text x="980" y="772" font-size="12">UNIT  MM</text>
  </svg>`;
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
