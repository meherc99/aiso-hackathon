import React, { useEffect, useMemo, useState } from 'react'
import Calendar from './components/Calendar'
import EventForm from './components/EventForm'
import EventList from './components/EventList'
import EventDetailModal from './components/EventDetailModal'
import { loadEvents, createEvent, updateEvent, deleteEvent, loadCategories, createCategory, buildCategoryMap } from './store/events'

export default function App() {
  const [events, setEvents] = useState([])
  const [loadingEvents, setLoadingEvents] = useState(true)
  const [editing, setEditing] = useState(null)
  const [viewingEvent, setViewingEvent] = useState(null)
  const [filterCategory, setFilterCategory] = useState('all')
  const [categories, setCategories] = useState([])

  useEffect(() => {
    let cancelled = false

    async function init() {
      try {
        const [fetchedEvents] = await Promise.all([loadEvents()])
        if (!cancelled) {
          setEvents(Array.isArray(fetchedEvents) ? fetchedEvents : [])
        }
      } catch (err) {
        console.error('Failed to load events from API', err)
        if (!cancelled) {
          setEvents([])
        }
      } finally {
        if (!cancelled) {
          setLoadingEvents(false)
        }
      }
    }

    init()

    // categories are stored locally; load synchronously
    const localCategories = loadCategories()
    setCategories(localCategories)

    return () => {
      cancelled = true
    }
  }, [])

  const categoryMap = useMemo(() => buildCategoryMap(categories, events), [categories, events])
  const categoryOptions = useMemo(() => Object.values(categoryMap), [categoryMap])

  async function handleCreate(payload) {
    try {
      const created = await createEvent(payload)
      setEvents(prev => [created, ...prev])
    } catch (err) {
      console.error('Failed to create event', err)
      window.alert('Failed to create event. See console for details.')
    }
  }

  async function handleUpdate(id, updates) {
    try {
      const updated = await updateEvent(id, updates)
      setEvents(prev => prev.map(e => e.id === id ? updated : e))
      setEditing(null)
    } catch (err) {
      console.error('Failed to update event', err)
      window.alert('Failed to update event. See console for details.')
    }
  }

  async function handleDelete(id) {
    try {
      await deleteEvent(id)
      setEvents(prev => prev.filter(e => e.id !== id))
      if (viewingEvent?.id === id) {
        setViewingEvent(null)
      }
    } catch (err) {
      console.error('Failed to delete event', err)
      window.alert('Failed to delete event. See console for details.')
    }
  }

  async function handleToggleDone(id) {
    const target = events.find(event => event.id === id)
    if (!target) return

    try {
      const updated = await updateEvent(id, { done: !target.done })
      setEvents(prev => prev.map(e => e.id === id ? updated : e))
    } catch (err) {
      console.error('Failed to toggle event status', err)
      window.alert('Failed to update event status. See console for details.')
    }
  }

  async function handleCreateCategory(data) {
    const created = createCategory(data)
    const next = loadCategories()
    setCategories(next)
    return created
  }

  function handleViewEvent(event) {
    setViewingEvent(event)
  }

  function handleCloseDetail() {
    setViewingEvent(null)
  }

  const displayedEvents = filterCategory === 'all' ? events : events.filter(e => e.category === filterCategory)

  if (loadingEvents) {
    return (
      <div className="app loading-state">
        <p>Loading calendar…</p>
      </div>
    )
  }

  return (
    <div className="app">
      <main className="app-main">
        <aside className="sidebar">
          <EventForm
            events={events}
            categories={categoryOptions}
            onCreate={handleCreate}
            onUpdate={handleUpdate}
            onCreateCategory={handleCreateCategory}
            editing={editing}
            onCancel={() => setEditing(null)}
          />
          <EventList 
            events={events} 
            categoryMap={categoryMap}
            onEdit={setEditing} 
            onDelete={handleDelete} 
            onToggleDone={handleToggleDone}
            onViewEvent={handleViewEvent}
          />
        </aside>

        <section className="calendar-area">
          <Calendar 
            events={displayedEvents}
            filterCategory={filterCategory}
            onFilterChange={setFilterCategory}
            categories={categoryOptions}
            categoryMap={categoryMap}
            onEdit={setEditing} 
            onDelete={handleDelete} 
            onToggleDone={handleToggleDone}
            onViewEvent={handleViewEvent}
          />
        </section>
      </main>

      {viewingEvent && (
        <EventDetailModal
          event={viewingEvent}
          categoryMap={categoryMap}
          onClose={handleCloseDetail}
          onEdit={setEditing}
          onDelete={handleDelete}
          onToggleDone={handleToggleDone}
        />
      )}

      <footer className="app-footer">Built with localStorage • Smooth UI • Minimal</footer>
    </div>
  )
}
