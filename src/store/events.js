import { v4 as uuidv4 } from 'uuid'

const KEY = 'simple_calendar_events_v1'

export function loadEvents() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : []
  } catch (err) {
    console.error('Failed to load events', err)
    return []
  }
}

export function saveEvents(events) {
  try {
    localStorage.setItem(KEY, JSON.stringify(events))
  } catch (err) {
    console.error('Failed to save events', err)
  }
}

export function createEvent({ title, description, startDate, endDate, startTime, endTime, category }) {
  const now = new Date().toISOString()
  return {
    id: uuidv4(),
    title: title || 'Untitled',
    description: description || '',
    created_at: now,
    done: false,
    startDate: normalizeDateToISO(startDate),
    endDate: normalizeDateToISO(endDate),
    startTime: startTime || '',
    endTime: endTime || '',
    category: category || '' // Store category ID only, not object
  }
}

/**
 * Get or create default categories (Work, Personal).
 * Returns { workId, personalId }
 */
function ensureDefaultCategories() {
  let cats = loadCategories()
  
  // Check if Work and Personal already exist
  let work = cats.find(c => c.name === 'Work')
  let personal = cats.find(c => c.name === 'Personal')
  
  if (!work) {
    work = {
      id: uuidv4(),
      name: 'Work',
      color: '#3089ce'
    }
    cats.push(work)
  }
  
  if (!personal) {
    personal = {
      id: uuidv4(),
      name: 'Personal',
      color: '#41ba49'
    }
    cats.push(personal)
  }
  
  saveCategories(cats)
  return { workId: work.id, personalId: personal.id }
}

/**
 * Generate sample events with default categories.
 * Call this function instead of using a static export.
 */
export function getSampleEvents() {
  const { workId, personalId } = ensureDefaultCategories()
  
  return [
    createEvent({ 
      title: 'Team Meeting', 
      description: 'Discuss roadmap', 
      startDate: new Date().toISOString().slice(0,10), 
      endDate: new Date().toISOString().slice(0,10),
      startTime: '09:00',
      endTime: '10:30',
      category: workId 
    }),
    createEvent({ 
      title: 'Doctor', 
      description: 'Annual checkup', 
      startDate: addDaysISO(2), 
      endDate: addDaysISO(2),
      startTime: '14:00',
      endTime: '15:00',
      category: personalId 
    }),
    createEvent({ 
      title: 'Project deadline', 
      description: 'Finish MVP', 
      startDate: addDaysISO(7), 
      endDate: addDaysISO(7),
      startTime: '17:00',
      endTime: '18:00',
      category: workId 
    })
  ]
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

// Category management
const CAT_KEY = 'simple_calendar_categories_v1'

export function loadCategories() {
  try {
    const raw = localStorage.getItem(CAT_KEY)
    if (!raw) return []
    return JSON.parse(raw)
  } catch (err) {
    console.error('Failed to load categories', err)
    return []
  }
}

export function saveCategories(categories) {
  try {
    localStorage.setItem(CAT_KEY, JSON.stringify(categories))
  } catch (err) {
    console.error('Failed to save categories', err)
  }
}

export function createCategory(categoryData) {
  const cats = loadCategories()
  const cat = {
    id: uuidv4(),
    name: (categoryData && categoryData.name) ? String(categoryData.name) : 'Unnamed',
    color: (categoryData && categoryData.color) ? String(categoryData.color) : '#666666'
  }
  cats.push(cat)
  saveCategories(cats)
  return cat
}

/**
 * Get category by ID. Returns the full category object { id, name, color } or null.
 */
export function getCategoryById(categoryId) {
  if (!categoryId) return null
  const cats = loadCategories()
  return cats.find(c => c.id === categoryId) || null
}
