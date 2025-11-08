import { v4 as uuidv4 } from 'uuid'

// API base URL - change this if your backend runs on a different port
const API_BASE = 'http://localhost:7860/api'

/**
 * Fetch all events from the backend API
 * @returns {Promise<Array>} Array of event objects
 */
export async function loadEvents() {
  try {
    const response = await fetch(`${API_BASE}/events`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    // Backend returns array directly, not wrapped in { events: [...] }
    return Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Failed to load events from API', err)
    return []
  }
}

/**
 * Save events is no longer needed as each operation saves directly to backend
 * Keeping it as a no-op for backwards compatibility
 */
export function saveEvents(events) {
  console.warn('saveEvents is deprecated - use createEvent, updateEvent, or deleteEvent instead')
}

/**
 * Create a new event in the backend
 * @param {Object} eventData - Event data
 * @returns {Promise<Object>} The created event
 */
export async function createEvent({ title, description, startDate, endDate, startTime, endTime, category }) {
  const now = new Date().toISOString()
  const eventData = {
    id: uuidv4(),
    title: title || 'Untitled',
    description: description || '',
    created_at: now,
    done: false,
    startDate: normalizeDateToISO(startDate),
    endDate: normalizeDateToISO(endDate),
    startTime: startTime || '',
    endTime: endTime || '',
    category: category || ''
  }

  try {
    const response = await fetch(`${API_BASE}/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(eventData)
    })
    console.log(response)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    // Backend returns event directly, not wrapped in { event: {...} }
    return result
  } catch (err) {
    console.error('Failed to create event', err)
    throw err
  }
}

/**
 * Update an existing event in the backend
 * @param {string} eventId - Event ID
 * @param {Object} eventData - Updated event data
 * @returns {Promise<Object>} The updated event
 */
export async function updateEvent(eventId, eventData) {
  try {
    const response = await fetch(`${API_BASE}/events/${eventId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(eventData)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    // Backend returns event directly, not wrapped in { event: {...} }
    return result
  } catch (err) {
    console.error('Failed to update event', err)
    throw err
  }
}

/**
 * Delete an event from the backend
 * @param {string} eventId - Event ID
 * @returns {Promise<void>}
 */
export async function deleteEvent(eventId) {
  try {
    const response = await fetch(`${API_BASE}/events/${eventId}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return true
  } catch (err) {
    console.error('Failed to delete event', err)
    throw err
  }
}

/**
 * Get or create default categories (Work, Personal).
 * Returns { workId, personalId }
 */
async function ensureDefaultCategories() {
  let cats = await loadCategories()
  
  // Check if Work and Personal already exist
  let work = cats.find(c => c.name === 'Work')
  let personal = cats.find(c => c.name === 'Personal')
  
  if (!work) {
    work = await createCategory({
      name: 'Work',
      color: '#3089ce'
    })
  }
  
  if (!personal) {
    personal = await createCategory({
      name: 'Personal',
      color: '#41ba49'
    })
  }
  
  return { workId: work.id, personalId: personal.id }
}

/**
 * Generate sample events with default categories.
 * Call this function instead of using a static export.
 */
export async function getSampleEvents() {
  const { workId, personalId } = await ensureDefaultCategories()
  
  const sampleData = [
    { 
      title: 'Team Meeting', 
      description: 'Discuss roadmap', 
      startDate: new Date().toISOString().slice(0,10), 
      endDate: new Date().toISOString().slice(0,10),
      startTime: '09:00',
      endTime: '10:30',
      category: workId 
    },
    { 
      title: 'Doctor', 
      description: 'Annual checkup', 
      startDate: addDaysISO(2), 
      endDate: addDaysISO(2),
      startTime: '14:00',
      endTime: '15:00',
      category: personalId 
    },
    { 
      title: 'Project deadline', 
      description: 'Finish MVP', 
      startDate: addDaysISO(7), 
      endDate: addDaysISO(7),
      startTime: '17:00',
      endTime: '18:00',
      category: workId 
    }
  ]

  // Create all sample events
  const events = []
  for (const data of sampleData) {
    const event = await createEvent(data)
    events.push(event)
  }
  
  return events
}

function addDaysISO(days) {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0,10)
}

function normalizeDateToISO(input) {
  if (!input) return ''
  // Already ISO YYYY-MM-DD
  if (typeof input === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(input)) return input

  // Date instance -> local date components
  if (input instanceof Date && !isNaN(input)) {
    const y = input.getFullYear()
    const m = String(input.getMonth() + 1).padStart(2, '0')
    const d = String(input.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }

  if (typeof input === 'string') {
    // Common formats like MM/DD/YYYY or DD/MM/YYYY (we assume MM/DD/YYYY by default)
    const mdy = input.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/)
    if (mdy) {
      const month = String(Number(mdy[1])).padStart(2, '0')
      const day = String(Number(mdy[2])).padStart(2, '0')
      const year = mdy[3]
      return `${year}-${month}-${day}`
    }

    // Fallback: try parsing with Date and read local components
    const parsed = new Date(input)
    if (!isNaN(parsed)) {
      const y = parsed.getFullYear()
      const m = String(parsed.getMonth() + 1).padStart(2, '0')
      const d = String(parsed.getDate()).padStart(2, '0')
      return `${y}-${m}-${d}`
    }
  }

  // If we can't parse, return the original input to avoid data loss
  return input
}

// ============================================================================
// Category Management API
// ============================================================================

/**
 * Load all categories from backend
 * @returns {Promise<Array>} Array of category objects
 */
export async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    // Backend returns array directly, not wrapped in { categories: [...] }
    return Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Failed to load categories from API', err)
    return []
  }
}

/**
 * Save categories is deprecated - use createCategory, updateCategory, deleteCategory
 */
export function saveCategories(categories) {
  console.warn('saveCategories is deprecated - use createCategory, updateCategory, or deleteCategory instead')
}

/**
 * Create a new category in the backend
 * @param {Object} categoryData - Category data with name and color
 * @returns {Promise<Object>} The created category
 */
export async function createCategory(categoryData) {
  const cat = {
    id: uuidv4(),
    name: (categoryData && categoryData.name) ? String(categoryData.name) : 'Unnamed',
    color: (categoryData && categoryData.color) ? String(categoryData.color) : '#666666'
  }

  try {
    const response = await fetch(`${API_BASE}/categories`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(cat)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    // Backend returns category directly, not wrapped
    return result
  } catch (err) {
    console.error('Failed to create category', err)
    throw err
  }
}

/**
 * Update an existing category
 * @param {string} categoryId - Category ID
 * @param {Object} categoryData - Updated category data
 * @returns {Promise<Object>} The updated category
 */
export async function updateCategory(categoryId, categoryData) {
  try {
    const response = await fetch(`${API_BASE}/categories/${categoryId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(categoryData)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    // Backend returns category directly, not wrapped
    return result
  } catch (err) {
    console.error('Failed to update category', err)
    throw err
  }
}

/**
 * Delete a category
 * @param {string} categoryId - Category ID
 * @returns {Promise<void>}
 */
export async function deleteCategory(categoryId) {
  try {
    const response = await fetch(`${API_BASE}/categories/${categoryId}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return true
  } catch (err) {
    console.error('Failed to delete category', err)
    throw err
  }
}

/**
 * Get category by ID. Returns the full category object { id, name, color } or null.
 * @param {string} categoryId - Category ID
 * @returns {Promise<Object|null>} Category object or null
 */
export async function getCategoryById(categoryId) {
  if (!categoryId) return null
  
  try {
    const response = await fetch(`${API_BASE}/categories/${categoryId}`)
    if (!response.ok) {
      if (response.status === 404) return null
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    // Backend returns category directly, not wrapped
    return data || null
  } catch (err) {
    console.error('Failed to get category', err)
    return null
  }
}
