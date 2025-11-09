const API_BASE = import.meta.env.VITE_CALENDAR_API ?? 'http://localhost:5050/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Calendar API error (${response.status}): ${text}`)
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

// ============================================================================
// Event endpoints
// ============================================================================

export async function loadEvents() {
  const events = await request('/events')
  return Array.isArray(events)
    ? events.map(ev => {
        const startTime = ev.startTime || ev.start_time || ev.time || ''
        const rawCategory = typeof ev.category === 'string' ? ev.category.toLowerCase() : ''
        const category = rawCategory === 'personal' ? 'personal' : 'work'
        return {
          ...ev,
          category,
          startTime,
          time: startTime,
        }
      })
    : []
}

export async function createEvent(payload) {
  return request('/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateEvent(eventId, updates) {
  return request(`/events/${eventId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  })
}

export async function deleteEvent(eventId) {
  await request(`/events/${eventId}`, {
    method: 'DELETE',
  })
}

// ============================================================================
// Category helpers
// ============================================================================

const DEFAULT_CATEGORIES = [
  { id: 'work', name: 'Work', color: '#3089ce' },
  { id: 'personal', name: 'Personal', color: '#41ba49' },
]

const CAT_KEY = 'simple_calendar_categories_v1'

function writeCategoryStore(categories) {
  try {
    localStorage.setItem(CAT_KEY, JSON.stringify(categories))
  } catch (err) {
    console.error('Failed to persist categories', err)
  }
}

export function loadCategories() {
  writeCategoryStore(DEFAULT_CATEGORIES)
  return DEFAULT_CATEGORIES
}

export function createCategory(categoryData) {
  const candidate = (categoryData?.id || categoryData?.name || '').toString().toLowerCase()
  if (candidate === 'personal') {
    return DEFAULT_CATEGORIES[1]
  }
  if (candidate === 'work') {
    return DEFAULT_CATEGORIES[0]
  }
  console.warn('Custom categories are disabled; defaulting to Work.')
  return DEFAULT_CATEGORIES[0]
}

export function getCategoryById(categoryId) {
  if (!categoryId) return null
  return DEFAULT_CATEGORIES.find(c => c.id === categoryId) || null
}

export function buildCategoryMap(categories = [], events = []) {
  const map = Object.create(null)
  const source = Array.isArray(categories) && categories.length > 0 ? categories : DEFAULT_CATEGORIES
  source.forEach(cat => {
    map[cat.id] = cat
  })

  events.forEach(event => {
    const key = event?.category === 'personal' ? 'personal' : 'work'
    if (!map[key]) {
      const fallback = DEFAULT_CATEGORIES.find(cat => cat.id === key)
      if (fallback) {
        map[key] = fallback
      }
    }
  })

  return map
}
