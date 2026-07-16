import { defineConfig } from "vite";
import babel from "@rolldown/plugin-babel";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
	plugins: [babel({ presets: [reactCompilerPreset()] }), react(), tailwindcss()],
	server: { proxy: { "/api": { changeOrigin: true, target: "http://127.0.0.1:8000" } } },
});
