export type Vec3 = { x: number; y: number; z: number };

export type ItemType =
  | "WORLD"
  | "SITE"
  | "ZONE"
  | "GRID"
  | "EQUI"
  | "NOZZ"
  | "STRU"
  | "SCTN"
  | "PLAT"
  | "PIPE"
  | "BRAN"
  | "TUBE"
  | "ELBO"
  | "TEE"
  | "VALV"
  | "FLAN"
  | "REDU"
  | "CAP"
  | "CYLI"
  | "BOX"
  | "DISH"
  | "CONE";

export interface TreeItem {
  id: string;
  type: ItemType;
  name: string;
  parentId: string | null;
  visible: boolean;
  props: Record<string, number | string | boolean>;
}

export interface ProjectDoc {
  name: string;
  code: string;
  description: string;
  units: "MM";
  spec: string;
  items: TreeItem[];
}

export interface MeasureResult {
  a: Vec3;
  b: Vec3;
  dx: number;
  dy: number;
  dz: number;
  distance: number;
}

export type ToolMode =
  | "select"
  | "place"
  | "measure"
  | "route";

export interface PlaceDraft {
  kind:
    | "vessel"
    | "tank"
    | "pump"
    | "exchanger"
    | "column"
    | "beam"
    | "platform"
    | "grid";
  values: Record<string, string>;
}

export const TYPE_LABEL: Record<ItemType, string> = {
  WORLD: "World",
  SITE: "Site",
  ZONE: "Zone",
  GRID: "Grid",
  EQUI: "Equipment",
  NOZZ: "Nozzle",
  STRU: "Structure",
  SCTN: "Section",
  PLAT: "Platform",
  PIPE: "Pipe",
  BRAN: "Branch",
  TUBE: "Tube",
  ELBO: "Elbow",
  TEE: "Tee",
  VALV: "Valve",
  FLAN: "Flange",
  REDU: "Reducer",
  CAP: "Cap",
  CYLI: "Cylinder",
  BOX: "Box",
  DISH: "Dish",
  CONE: "Cone",
};
