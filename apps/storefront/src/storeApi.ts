export async function request<T>(url: string, token?: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers({ Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) })
  new Headers(init.headers).forEach((value, name) => headers.set(name, value))
  const response = await fetch(url, { ...init, headers })
  if (!response.ok) throw new Error(response.status === 401 ? 'Sign in to manage your saved items.' : `Could not complete that request (${response.status}).`)
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
