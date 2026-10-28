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
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(
      'Não foi possível conectar ao servidor. Tente novamente.',
      0,
    )
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = body.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item: { msg?: string }) => item.msg || 'Valor inválido')
              .join('; ')
          : `Falha na solicitação (${response.status})`
    const translated: Record<string, string> = {
      'Not authenticated': 'Entre para continuar',
      'Not Found': 'Recurso não encontrado',
      'Method Not Allowed': 'Operação não permitida',
    }
    throw new ApiError(translated[message] || message, response.status)
  }
  return (response.status === 204 ? null : await response.json()) as T
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown, headers?: HeadersInit) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body), headers }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path: string) => request<null>(path, { method: 'DELETE' }),
  form: <T>(path: string, body: URLSearchParams) =>
    request<T>(path, { method: 'POST', body }),
}
