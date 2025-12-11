import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, afterAll, vi } from 'vitest'
import { server } from '../mocks/server'

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Clean up after each test
afterEach(() => {
  cleanup()
  server.resetHandlers()
})

// Clean up after all tests
afterAll(() => server.close())

// Mock ResizeObserver (needed for some UI components)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock WebGL2 context for NiiVue
// NiiVue requires specific extensions for float textures (overlays)
// See: https://github.com/niivue/niivue#browser-requirements
const mockExtensions: Record<string, object> = {
  // Required for float textures (overlay rendering)
  EXT_color_buffer_float: {},
  OES_texture_float_linear: {},
  // Required for WebGL context management
  WEBGL_lose_context: {
    loseContext: vi.fn(),
    restoreContext: vi.fn(),
  },
  // Optional but commonly requested
  EXT_texture_filter_anisotropic: {
    TEXTURE_MAX_ANISOTROPY_EXT: 0x84fe,
    MAX_TEXTURE_MAX_ANISOTROPY_EXT: 0x84ff,
  },
  WEBGL_debug_renderer_info: {
    UNMASKED_VENDOR_WEBGL: 0x9245,
    UNMASKED_RENDERER_WEBGL: 0x9246,
  },
}

const mockWebGL2Context = {
  canvas: null as HTMLCanvasElement | null,
  drawingBufferWidth: 640,
  drawingBufferHeight: 480,
  createShader: vi.fn(() => ({})),
  shaderSource: vi.fn(),
  compileShader: vi.fn(),
  getShaderParameter: vi.fn(() => true),
  getShaderInfoLog: vi.fn(() => ''),
  createProgram: vi.fn(() => ({})),
  attachShader: vi.fn(),
  linkProgram: vi.fn(),
  getProgramParameter: vi.fn(() => true),
  getProgramInfoLog: vi.fn(() => ''),
  useProgram: vi.fn(),
  getAttribLocation: vi.fn(() => 0),
  getUniformLocation: vi.fn(() => ({})),
  createBuffer: vi.fn(() => ({})),
  bindBuffer: vi.fn(),
  bufferData: vi.fn(),
  enableVertexAttribArray: vi.fn(),
  vertexAttribPointer: vi.fn(),
  createTexture: vi.fn(() => ({})),
  bindTexture: vi.fn(),
  texParameteri: vi.fn(),
  texParameterf: vi.fn(),
  texImage2D: vi.fn(),
  texImage3D: vi.fn(),
  texStorage2D: vi.fn(),
  texStorage3D: vi.fn(),
  texSubImage2D: vi.fn(),
  texSubImage3D: vi.fn(),
  activeTexture: vi.fn(),
  generateMipmap: vi.fn(),
  uniform1i: vi.fn(),
  uniform1f: vi.fn(),
  uniform2f: vi.fn(),
  uniform2fv: vi.fn(),
  uniform3f: vi.fn(),
  uniform3fv: vi.fn(),
  uniform4f: vi.fn(),
  uniform4fv: vi.fn(),
  uniformMatrix4fv: vi.fn(),
  viewport: vi.fn(),
  scissor: vi.fn(),
  clear: vi.fn(),
  clearColor: vi.fn(),
  clearDepth: vi.fn(),
  enable: vi.fn(),
  disable: vi.fn(),
  blendFunc: vi.fn(),
  blendFuncSeparate: vi.fn(),
  depthFunc: vi.fn(),
  depthMask: vi.fn(),
  cullFace: vi.fn(),
  drawArrays: vi.fn(),
  drawElements: vi.fn(),
  // CRITICAL: Return stub extensions for NiiVue float texture support
  getExtension: vi.fn((name: string) => mockExtensions[name] || null),
  getParameter: vi.fn((pname: number) => {
    // Return reasonable defaults for common parameter queries
    if (pname === 0x0d33) return 16384 // MAX_TEXTURE_SIZE
    if (pname === 0x8073) return 2048 // MAX_3D_TEXTURE_SIZE
    if (pname === 0x851c) return 16 // MAX_TEXTURE_IMAGE_UNITS
    return 0
  }),
  getSupportedExtensions: vi.fn(() => Object.keys(mockExtensions)),
  pixelStorei: vi.fn(),
  readPixels: vi.fn(),
  createFramebuffer: vi.fn(() => ({})),
  bindFramebuffer: vi.fn(),
  framebufferTexture2D: vi.fn(),
  checkFramebufferStatus: vi.fn(() => 36053), // FRAMEBUFFER_COMPLETE
  createRenderbuffer: vi.fn(() => ({})),
  bindRenderbuffer: vi.fn(),
  renderbufferStorage: vi.fn(),
  framebufferRenderbuffer: vi.fn(),
  deleteTexture: vi.fn(),
  deleteBuffer: vi.fn(),
  deleteProgram: vi.fn(),
  deleteShader: vi.fn(),
  deleteFramebuffer: vi.fn(),
  deleteRenderbuffer: vi.fn(),
  createVertexArray: vi.fn(() => ({})),
  bindVertexArray: vi.fn(),
  deleteVertexArray: vi.fn(),
  flush: vi.fn(),
  finish: vi.fn(),
  isContextLost: vi.fn(() => false),
}

HTMLCanvasElement.prototype.getContext = function (
  contextType: string
): RenderingContext | null {
  if (contextType === 'webgl2' || contextType === 'webgl') {
    return {
      ...mockWebGL2Context,
      canvas: this,
    } as unknown as WebGL2RenderingContext
  }
  return null
}
