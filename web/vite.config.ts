import { defineConfig } from "vitest/config";

export default defineConfig({
  root: ".",
  base: "./",
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
  test: {
    environment: "node",
  },
});
