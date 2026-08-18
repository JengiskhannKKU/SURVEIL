"use client";

import { motion } from "framer-motion";
import { GREEN } from "@/lib/theme";
import { BinaryColumns } from "@/components/BinaryColumns";

export function GridBackground() {
  return (
    <div
      aria-hidden
      style={{
        position: "fixed",
        inset: 0,
        zIndex: -1,
        overflow: "hidden",
        backgroundColor: "#000",
      }}
    >
      {/* grid lines */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)",
          backgroundSize: "42px 42px",
          maskImage:
            "radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)",
        }}
      />

      <BinaryColumns />

      {/* green glow, upper-center — behind hero titles */}
      <motion.div
        style={{
          position: "absolute",
          top: "-10%",
          left: "50%",
          x: "-50%",
          width: "70vw",
          height: "40vw",
          borderRadius: "50%",
          background: `radial-gradient(ellipse, ${GREEN}26 0%, transparent 70%)`,
          filter: "blur(50px)",
        }}
        animate={{ opacity: [0.55, 0.85, 0.55] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* faint secondary glow, bottom-right, for depth */}
      <motion.div
        style={{
          position: "absolute",
          bottom: "-20%",
          right: "-10%",
          width: "45vw",
          height: "45vw",
          borderRadius: "50%",
          background: `radial-gradient(circle, ${GREEN}14 0%, transparent 70%)`,
          filter: "blur(50px)",
        }}
        animate={{ opacity: [0.4, 0.6, 0.4] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* vignette so text stays readable at the edges */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 90% 80% at 50% 20%, transparent 40%, #000 100%)",
        }}
      />
    </div>
  );
}
