import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 py-4">
        <div className="container mx-auto px-4">
          <h1 className="text-2xl font-bold">Stroke Lesion Segmentation</h1>
          <p className="text-gray-400 text-sm mt-1">
            DeepISLES segmentation on ISLES24 dataset
          </p>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">{children}</main>
    </div>
  )
}
