import { useRef, useEffect } from 'react'
import { Niivue } from '@niivue/niivue'

interface NiiVueViewerProps {
  backgroundUrl: string
  overlayUrl?: string
}

export function NiiVueViewer({ backgroundUrl, overlayUrl }: NiiVueViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const nvRef = useRef<Niivue | null>(null)

  useEffect(() => {
    if (!canvasRef.current) return

    // Only instantiate NiiVue once; reuse for volume reloads
    let nv = nvRef.current
    if (!nv) {
      nv = new Niivue({
        backColor: [0.05, 0.05, 0.05, 1],
        show3Dcrosshair: true,
        crosshairColor: [1, 0, 0, 0.5],
      })
      nv.attachToCanvas(canvasRef.current)
      nvRef.current = nv
    }

    // Build volumes array - always reload when URLs change
    const volumes: Array<{ url: string; colormap: string; opacity: number }> = [
      { url: backgroundUrl, colormap: 'gray', opacity: 1 },
    ]

    if (overlayUrl) {
      volumes.push({
        url: overlayUrl,
        colormap: 'red',
        opacity: 0.5,
      })
    }

    // Load volumes (async but we don't await - just fire off)
    void nv.loadVolumes(volumes)

    // Cleanup on unmount - CRITICAL: Release WebGL context
    // Browsers limit WebGL contexts (~16 in Chrome). Without cleanup,
    // navigating between results will exhaust contexts and break the viewer.
    return () => {
      if (nvRef.current) {
        // Capture gl BEFORE cleanup (cleanup may null internal state)
        const gl = nvRef.current.gl
        try {
          // NiiVue's cleanup() releases event listeners and observers
          // See: https://niivue.github.io/niivue/devdocs/classes/Niivue.html#cleanup
          nvRef.current.cleanup()
          // Force WebGL context loss to free GPU memory immediately
          if (gl) {
            const ext = gl.getExtension('WEBGL_lose_context')
            ext?.loseContext()
          }
        } catch {
          // Ignore cleanup errors
        }
        nvRef.current = null
      }
    }
  }, [backgroundUrl, overlayUrl])

  return (
    <div className="bg-gray-900 rounded-lg p-2">
      <canvas ref={canvasRef} className="w-full h-[500px] rounded" />
      <div className="flex gap-4 mt-2 text-xs text-gray-400">
        <span>Scroll: Navigate slices</span>
        <span>Drag: Adjust contrast</span>
        <span>Right-click: Pan</span>
      </div>
    </div>
  )
}
