"use client";

import { motion } from "framer-motion";
import { RED, BLUE } from "@/lib/theme";

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
            "linear-gradient(rgba(255,255,255,0.055) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(255,255,255,0.055) 1px, transparent 1px)",
          backgroundSize: "42px 42px",
          maskImage:
            "radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)",
        }}
      />

      {/* red glow, top-left */}
      <motion.div
        style={{
          position: "absolute",
          top: "-15%",
          left: "-10%",
          width: "50vw",
          height: "50vw",
          borderRadius: "50%",
          background: `radial-gradient(circle, ${RED}33 0%, transparent 70%)`,
          filter: "blur(40px)",
        }}
        animate={{
          x: [0, 40, 0],
          y: [0, 25, 0],
          opacity: [0.55, 0.85, 0.55],
        }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* blue glow, bottom-right */}
      <motion.div
        style={{
          position: "absolute",
          bottom: "-20%",
          right: "-10%",
          width: "55vw",
          height: "55vw",
          borderRadius: "50%",
          background: `radial-gradient(circle, ${BLUE}33 0%, transparent 70%)`,
          filter: "blur(40px)",
        }}
        animate={{
          x: [0, -30, 0],
          y: [0, -20, 0],
          opacity: [0.5, 0.8, 0.5],
        }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
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
