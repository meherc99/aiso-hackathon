import { v4 as uuidv4 } from 'uuid'

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
  return request('/events')
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
// Category helpers (still stored locally)
// ============================================================================

const CAT_KEY = 'simple_calendar_categories_v1'

function readCategoryStore() {
  try {
    const raw = localStorage.getItem(CAT_KEY)
    return raw ? JSON.parse(raw) : []
  } catch (err) {
    console.error('Failed to read categories', err)
    return []
  }
}

function writeCategoryStore(categories) {
  try {
    localStorage.setItem(CAT_KEY, JSON.stringify(categories))
  } catch (err) {
    console.error('Failed to persist categories', err)
  }
}

function ensureDefaultCategories(categories) {
  const exists = (name) => categories.find(c => c.name.toLowerCase() === name.toLowerCase())
  const updated = [...categories]

  if (!exists('Work')) {
    updated.push({ id: 'work', name: 'Work', color: '#3089ce' })
  }
  if (!exists('Personal')) {
    updated.push({ id: 'personal', name: 'Personal', color: '#41ba49' })
  }
  return updated
}

export function loadCategories() {
  const categories = ensureDefaultCategories(readCategoryStore())
  writeCategoryStore(categories)
  return categories
}

export function createCategory(categoryData) {
  const categories = loadCategories()
  const id = categoryData?.id || uuidv4()
  const category = {
    id,
    name: categoryData?.name ? String(categoryData.name) : 'Unnamed',
    color: categoryData?.color ? String(categoryData.color) : '#666666',
  }
  const updated = [...categories.filter(c => c.id !== id), category]
  writeCategoryStore(updated)
  return category
}

export function getCategoryById(categoryId) {
  if (!categoryId) return null
  const categories = loadCategories()
  return categories.find(c => c.id === categoryId) || null
}

export function buildCategoryMap(categories = [], events = []) {
  const map = Object.create(null)
  categories.forEach(cat => {
    map[cat.id] = cat
  })

  events.forEach(event => {
    const key = event?.category
    if (!key) return
    if (!map[key]) {
      map[key] = {
        id: key,
        name: key.charAt(0).toUpperCase() + key.slice(1),
        color: '#64748b',
      }
    }
  })

  return map
}
