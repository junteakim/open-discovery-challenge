import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { buildItemMesh, itemCenter } from "./geometry";
import { childrenOf } from "./project";
import type { MeasureResult, ProjectDoc, TreeItem, Vec3 } from "./types";

export interface ViewportApi {
  render: (doc: ProjectDoc, selectedId: string | null) => void;
  resize: () => void;
  setView: (name: "iso" | "top" | "front" | "east" | "west") => void;
  pick: (clientX: number, clientY: number) => string | null;
  worldOnGrid: (clientX: number, clientY: number) => Vec3 | null;
  fit: (doc: ProjectDoc, id?: string | null) => void;
  setMeasure: (result: MeasureResult | null) => void;
  dispose: () => void;
}

export function createViewport(canvas: HTMLCanvasElement): ViewportApi {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0d1520);
  scene.fog = new THREE.Fog(0x0d1520, 28000, 72000);

  const camera = new THREE.PerspectiveCamera(50, 1, 10, 200000);
  camera.up.set(0, 0, 1);
  camera.position.set(14000, -12000, 9000);

  const controls = new OrbitControls(camera, canvas);
  controls.target.set(6000, 3500, 1500);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minDistance = 400;
  controls.maxDistance = 80000;

  scene.add(new THREE.AmbientLight(0x9fb3c8, 0.55));
  const key = new THREE.DirectionalLight(0xffffff, 1.05);
  key.position.set(12000, -8000, 18000);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -20000;
  key.shadow.camera.right = 20000;
  key.shadow.camera.top = 20000;
  key.shadow.camera.bottom = -20000;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x7fdbff, 0.25);
  fill.position.set(-10000, 8000, 6000);
  scene.add(fill);

  const hemi = new THREE.HemisphereLight(0xbdd4ea, 0x1b2838, 0.35);
  scene.add(hemi);

  const root = new THREE.Group();
  scene.add(root);

  const grid = new THREE.GridHelper(24000, 24, 0x3d5a73, 0x243447);
  grid.rotation.x = Math.PI / 2;
  grid.position.set(6000, 4000, 0);
  scene.add(grid);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(48000, 48000),
    new THREE.MeshStandardMaterial({ color: 0x13202e, roughness: 1, metalness: 0 }),
  );
  ground.position.set(6000, 4000, -2);
  ground.receiveShadow = true;
  scene.add(ground);

  const axes = new THREE.AxesHelper(2500);
  axes.position.set(0, 0, 2);
  scene.add(axes);

  const measureGroup = new THREE.Group();
  scene.add(measureGroup);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  let raf = 0;
  const loop = () => {
    raf = requestAnimationFrame(loop);
    controls.update();
    renderer.render(scene, camera);
  };
  loop();

  function resize() {
    const wrap = canvas.parentElement;
    const w = wrap?.clientWidth ?? 800;
    const h = wrap?.clientHeight ?? 600;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(h, 1);
    camera.updateProjectionMatrix();
  }

  function buildGrid(item: TreeItem) {
    const group = new THREE.Group();
    const nx = Number(item.props.nx ?? 4);
    const ny = Number(item.props.ny ?? 3);
    const nz = Number(item.props.nz ?? 2);
    const sx = Number(item.props.sx ?? 4000);
    const sy = Number(item.props.sy ?? 4000);
    const sz = Number(item.props.sz ?? 4000);
    const x0 = Number(item.props.x0 ?? 0);
    const y0 = Number(item.props.y0 ?? 0);
    const z0 = Number(item.props.z0 ?? 0);
    const mat = new THREE.LineBasicMaterial({ color: 0x4a90a4, transparent: true, opacity: 0.55 });
    for (let i = 0; i < nx; i += 1) {
      for (let k = 0; k < nz; k += 1) {
        const geo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(x0 + i * sx, y0, z0 + k * sz),
          new THREE.Vector3(x0 + i * sx, y0 + (ny - 1) * sy, z0 + k * sz),
        ]);
        group.add(new THREE.Line(geo, mat));
      }
    }
    for (let j = 0; j < ny; j += 1) {
      for (let k = 0; k < nz; k += 1) {
        const geo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(x0, y0 + j * sy, z0 + k * sz),
          new THREE.Vector3(x0 + (nx - 1) * sx, y0 + j * sy, z0 + k * sz),
        ]);
        group.add(new THREE.Line(geo, mat));
      }
    }
    return group;
  }

  function render(doc: ProjectDoc, selectedId: string | null) {
    root.clear();
    for (const item of doc.items) {
      if (!item.visible) continue;
      if (item.type === "GRID") {
        const g = buildGrid(item);
        g.userData.itemId = item.id;
        root.add(g);
        continue;
      }
      const mesh = buildItemMesh(item, item.id === selectedId);
      if (mesh) root.add(mesh);
    }
    void childrenOf;
  }

  function ndc(clientX: number, clientY: number) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  }

  function pick(clientX: number, clientY: number): string | null {
    ndc(clientX, clientY);
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(root.children, true);
    for (const hit of hits) {
      const id = hit.object.userData.itemId as string | undefined;
      if (id) return id;
    }
    return null;
  }

  function worldOnGrid(clientX: number, clientY: number): Vec3 | null {
    ndc(clientX, clientY);
    raycaster.setFromCamera(pointer, camera);
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    const out = new THREE.Vector3();
    if (!raycaster.ray.intersectPlane(plane, out)) return null;
    return {
      x: Math.round(out.x / 100) * 100,
      y: Math.round(out.y / 100) * 100,
      z: 0,
    };
  }

  function setView(name: "iso" | "top" | "front" | "east" | "west") {
    const t = controls.target.clone();
    const d = 16000;
    if (name === "iso") camera.position.set(t.x + 11000, t.y - 11000, t.z + 8000);
    if (name === "top") camera.position.set(t.x, t.y, t.z + d);
    if (name === "front") camera.position.set(t.x, t.y - d, t.z + 1200);
    if (name === "east") camera.position.set(t.x + d, t.y, t.z + 1200);
    if (name === "west") camera.position.set(t.x - d, t.y, t.z + 1200);
    camera.lookAt(t);
    controls.update();
  }

  function fit(doc: ProjectDoc, id?: string | null) {
    const box = new THREE.Box3();
    const targetItems = id ? doc.items.filter((it) => it.id === id) : doc.items;
    let any = false;
    for (const item of targetItems) {
      const c = itemCenter(item);
      if (c.length() > 0 || item.props.x !== undefined || item.props.x1 !== undefined) {
        box.expandByPoint(c);
        any = true;
      }
    }
    if (!any) return;
    const center = box.getCenter(new THREE.Vector3());
    const size = Math.max(box.getSize(new THREE.Vector3()).length(), 4000);
    controls.target.copy(center);
    camera.position.set(center.x + size * 0.9, center.y - size * 0.9, center.z + size * 0.7);
  }

  function setMeasure(result: MeasureResult | null) {
    measureGroup.clear();
    if (!result) return;
    const a = new THREE.Vector3(result.a.x, result.a.y, result.a.z);
    const b = new THREE.Vector3(result.b.x, result.b.y, result.b.z);
    const mat = new THREE.LineBasicMaterial({ color: 0xf1c40f });
    measureGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), mat));
    const mid = a.clone().add(b).multiplyScalar(0.5);
    const sprite = makeLabel(
      `${Math.round(result.distance)} mm\nΔX ${Math.round(result.dx)}  ΔY ${Math.round(result.dy)}  ΔZ ${Math.round(result.dz)}`,
    );
    sprite.position.copy(mid);
    sprite.position.z += 250;
    measureGroup.add(sprite);
  }

  function dispose() {
    cancelAnimationFrame(raf);
    controls.dispose();
    renderer.dispose();
  }

  resize();
  return { render, resize, setView, pick, worldOnGrid, fit, setMeasure, dispose };
}

function makeLabel(text: string): THREE.Sprite {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 128;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = "rgba(13,21,32,0.85)";
  ctx.fillRect(0, 0, 512, 128);
  ctx.strokeStyle = "#f1c40f";
  ctx.strokeRect(2, 2, 508, 124);
  ctx.fillStyle = "#f8f4e8";
  ctx.font = "28px Segoe UI, sans-serif";
  const lines = text.split("\n");
  lines.forEach((line, i) => ctx.fillText(line, 24, 50 + i * 36));
  const tex = new THREE.CanvasTexture(c);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(2200, 550, 1);
  return sprite;
}
