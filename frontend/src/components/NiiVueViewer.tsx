import { useRef, useEffect, useState } from "react";
import { Niivue } from "@niivue/niivue";

interface NiiVueViewerProps {
  backgroundUrl: string;
  overlayUrl?: string;
  onError?: (error: string) => void;
}

export function NiiVueViewer({
  backgroundUrl,
  overlayUrl,
  onError,
}: NiiVueViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nvRef = useRef<Niivue | null>(null);
  const onErrorRef = useRef(onError);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Keep onError ref current without triggering effect re-runs
  useEffect(() => {
    onErrorRef.current = onError;
  });

  // Effect 1: Mount/unmount - instantiate and cleanup NiiVue ONCE
  useEffect(() => {
    if (!canvasRef.current) return;

    const nv = new Niivue({
      backColor: [0.05, 0.05, 0.05, 1],
      show3Dcrosshair: true,
      crosshairColor: [1, 0, 0, 0.5],
    });
    nv.attachToCanvas(canvasRef.current);
    nvRef.current = nv;

    // Cleanup on unmount ONLY - CRITICAL: Release WebGL context
    // Browsers limit WebGL contexts (~16 in Chrome). Without cleanup,
    // navigating between cases will exhaust contexts and break the viewer.
    return () => {
      // Capture gl BEFORE cleanup (cleanup may null internal state)
      const gl = nv.gl;
      try {
        // NiiVue's cleanup() releases event listeners and observers
        // See: https://niivue.github.io/niivue/devdocs/classes/Niivue.html#cleanup
        nv.cleanup();
        // Force WebGL context loss to free GPU memory immediately
        if (gl) {
          const ext = gl.getExtension("WEBGL_lose_context");
          ext?.loseContext();
        }
      } catch {
        // Ignore cleanup errors
      }
      nvRef.current = null;
    };
  }, []);

  // Effect 2: URL changes - reload volumes on existing NiiVue instance
  // Uses isCurrent flag to ignore stale loads when URLs change rapidly
  useEffect(() => {
    const nv = nvRef.current;
    if (!nv) return;

    let isCurrent = true;

    // Clear previous error before new load (valid pattern for async operations)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadError(null);

    const volumes: Array<{ url: string; colormap: string; opacity: number }> = [
      { url: backgroundUrl, colormap: "gray", opacity: 1 },
    ];

    if (overlayUrl) {
      volumes.push({
        url: overlayUrl,
        colormap: "red",
        opacity: 0.5,
      });
    }

    // Load volumes with error handling - ignore stale results
    nv.loadVolumes(volumes).catch((err: unknown) => {
      if (!isCurrent) return; // Ignore errors from stale loads
      const message =
        err instanceof Error ? err.message : "Failed to load volume";
      setLoadError(message);
      onErrorRef.current?.(message);
    });

    // Cleanup: mark this effect instance as stale
    return () => {
      isCurrent = false;
    };
  }, [backgroundUrl, overlayUrl]);

  return (
    <div className="bg-gray-900 rounded-lg p-2">
      <canvas ref={canvasRef} className="w-full h-[500px] rounded" />
      {loadError && (
        <div className="mt-2 p-2 bg-red-900/50 rounded text-red-300 text-sm">
          Failed to load volume: {loadError}
        </div>
      )}
      <div className="flex gap-4 mt-2 text-xs text-gray-400">
        <span>Scroll: Navigate slices</span>
        <span>Drag: Adjust contrast</span>
        <span>Right-click: Pan</span>
      </div>
    </div>
  );
}
