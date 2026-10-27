const BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
let accessToken: string | null = null
export const setAccessToken = (token: string | null) => {
  accessToken = token
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof URLSearchParams))
    headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = body.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item: { msg?: string }) => item.msg || 'Invalid value')
              .join('; ')
          : `Request failed (${response.status})`
    throw new ApiError(message, response.status)
  }
  return (response.status === 204 ? null : await response.json()) as T
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  form: <T>(path: string, body: URLSearchParams) =>
    request<T>(path, { method: 'POST', body }),
}
