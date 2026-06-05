const BASE = import.meta.env.VITE_API_URL || 'https://fatbot-0xxn.onrender.com'

function getInitData() {
  return window.Telegram?.WebApp?.initData || ''
}

async function request(method, path, body, isFormData = false) {
  const headers = { 'X-Init-Data': getInitData() }
  if (!isFormData) headers['Content-Type'] = 'application/json'

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isFormData ? body : (body ? JSON.stringify(body) : undefined),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getMe: () => request('GET', '/api/me'),
  getToday: () => request('GET', '/api/today'),
  searchFood: (q) => request('GET', `/api/food/search?q=${encodeURIComponent(q)}`),
  addFood: (data) => request('POST', '/api/food/add', data),
  deleteFood: (id) => request('DELETE', `/api/food/${id}`),
  updateFood: (id, amount_g) => request('PUT', `/api/food/${id}`, { amount_g }),
  analyzePhoto: (file) => {
    const fd = new FormData()
    fd.append('photo', file)
    return request('POST', '/api/food/photo', fd, true)
  },
  getWeekStats: () => request('GET', '/api/stats/week'),
  getWater: () => request('GET', '/api/water'),
  addWater: (glasses) => request('POST', '/api/water', { glasses }),
  logWeight: (weight_kg) => request('POST', '/api/weight', { weight_kg }),
  getWeightHistory: () => request('GET', '/api/weight/history'),
  updateProfile: (data) => request('PUT', '/api/profile', data),
  updateProfilePhoto: (photo) => request('POST', '/api/profile/photo', { photo }),
  getUserFoods: (q) => request('GET', `/api/user-foods${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  createUserFood: (data) => request('POST', '/api/user-foods', data),
  updateUserFood: (id, data) => request('PUT', `/api/user-foods/${id}`, data),
  deleteUserFood: (id) => request('DELETE', `/api/user-foods/${id}`),
}
