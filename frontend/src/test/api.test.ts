import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiGet, login, logout } from '@/shared/api'

describe('API helpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetches JSON with credentials and forwards abort signals', async () => {
    const signal = new AbortController().signal
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ api: 'ok' }), {
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiGet('/api/health', { signal })).resolves.toEqual({ api: 'ok' })
    expect(fetchMock).toHaveBeenCalledWith('/api/health', { credentials: 'include', signal })
  })

  it('raises ApiError with response status and body text', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('Forbidden', { status: 403 })))

    await expect(apiGet('/api/private')).rejects.toMatchObject({
      status: 403,
      message: 'Forbidden',
    } satisfies Pick<ApiError, 'status' | 'message'>)
  })

  it('posts login/logout requests with expected auth headers and payloads', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrf_token: 'csrf-1', user: { id: '1', username: 'eva' } }), {
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(login('eva', 'secret')).resolves.toMatchObject({ csrf_token: 'csrf-1' })
    await logout('csrf-1')

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'eva', password: 'secret' }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/auth/logout',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRF-Token': 'csrf-1' },
      }),
    )
  })
})
