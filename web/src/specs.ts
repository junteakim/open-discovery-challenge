export interface BoreSpec {
  nps: string;
  od: number;
  sch40: number;
  weightKgPerM: number;
}

/** ANSI B36.10-ish schedule 40 outside diameters (mm). */
export const BORES: BoreSpec[] = [
  { nps: "15", od: 21.3, sch40: 2.77, weightKgPerM: 1.27 },
  { nps: "20", od: 26.7, sch40: 2.87, weightKgPerM: 1.69 },
  { nps: "25", od: 33.4, sch40: 3.38, weightKgPerM: 2.5 },
  { nps: "40", od: 48.3, sch40: 3.68, weightKgPerM: 4.05 },
  { nps: "50", od: 60.3, sch40: 3.91, weightKgPerM: 5.44 },
  { nps: "80", od: 88.9, sch40: 5.49, weightKgPerM: 11.29 },
  { nps: "100", od: 114.3, sch40: 6.02, weightKgPerM: 16.07 },
  { nps: "150", od: 168.3, sch40: 7.11, weightKgPerM: 28.26 },
  { nps: "200", od: 219.1, sch40: 8.18, weightKgPerM: 42.55 },
  { nps: "250", od: 273.1, sch40: 9.27, weightKgPerM: 60.31 },
  { nps: "300", od: 323.9, sch40: 10.31, weightKgPerM: 79.73 },
];

export const PIPING_SPECS = ["A1A", "A1B", "B1A", "C1A"] as const;

export function boreOd(boreMm: number): number {
  const hit = BORES.find((b) => Number(b.nps) === boreMm);
  return hit?.od ?? boreMm * 1.14;
}

export function boreWeight(boreMm: number): number {
  const hit = BORES.find((b) => Number(b.nps) === boreMm);
  return hit?.weightKgPerM ?? (boreMm * boreMm * 0.0246) / 1000;
}

export function elbowRadius(boreMm: number, longRadius = true): number {
  const od = boreOd(boreMm);
  return (longRadius ? 1.5 : 1.0) * od;
}

export const PROFILES = [
  { name: "H200x200x8x12", d: 200, bf: 200, tw: 8, tf: 12 },
  { name: "H250x250x9x14", d: 250, bf: 250, tw: 9, tf: 14 },
  { name: "H300x300x10x15", d: 300, bf: 300, tw: 10, tf: 15 },
  { name: "H350x350x12x19", d: 350, bf: 350, tw: 12, tf: 19 },
] as const;
