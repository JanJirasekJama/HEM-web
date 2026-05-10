import { describe, expect, it } from 'vitest'

import manifestRaw from '../../public/manifest.webmanifest?raw'
import offlineHtml from '../../public/offline.html?raw'
import serviceWorker from '../../public/service-worker.js?raw'

describe('PWA public assets', () => {
  it('keeps the manifest installable with the offline shell assets', () => {
    const manifest = JSON.parse(manifestRaw) as {
      name?: string
      start_url?: string
      display?: string
      icons?: Array<{ src?: string; purpose?: string }>
    }

    expect(manifest).toMatchObject({
      name: 'HEM',
      start_url: '/',
      display: 'standalone',
    })
    expect(manifest.icons?.some((icon) => icon.src === '/pwa-icon.svg' && icon.purpose?.includes('maskable'))).toBe(true)
    expect(offlineHtml).toContain('<html lang="cs">')
    expect(serviceWorker).toContain("const OFFLINE_URL = '/offline.html'")
  })
})
