import React, { useEffect, useState } from 'react'
import Calendar from './components/Calendar'
import EventForm from './components/EventForm'
import EventList from './components/EventList'
import EventDetailModal from './components/EventDetailModal'
import { loadEvents, createEvent, loadCategories } from './store/events'

export default function App() {
  const [events, setEvents] = useState([])
  const [categories, setCategories] = useState([])
  const [editing, setEditing] = useState(null)
  const [viewingEvent, setViewingEvent] = useState(null)
  const [filterCategory, setFilterCategory] = useState('all')
  const [isInitialized, setIsInitialized] = useState(false)

  // Load events from API
  useEffect(() => {
    async function fetchEvents() {
      try {
        const loaded = await loadEvents() // Add await
        console.log('Loaded events from database:', loaded)
        setEvents(Array.isArray(loaded) ? loaded : []) // Ensure array
        setIsInitialized(true)
      } catch (error) {
        console.error('Error loading events:', error)
        setEvents([])
        setIsInitialized(true)
      }
    }
    fetchEvents()
  }, [])

  // Load categories from API
  useEffect(() => {
    async function fetchCategories() {
      try {
        const cats = await loadCategories() // Add await
        console.log('Loaded categories:', cats)
        setCategories(Array.isArray(cats) ? cats : []) // Ensure array
      } catch (error) {
        console.error('Error loading categories:', error)
        setCategories([])
      }
    }
    fetchCategories()
  }, [])

  async function handleCreate(eventData) {
    try {
      const newEvent = await createEvent(eventData) // Add await
      setEvents(prev => [newEvent, ...prev])
    } catch (error) {
      console.error('Error creating event:', error)
    }
  }

  function handleUpdate(id, updates) {
    setEvents(prev => prev.map(e => e.id === id ? { ...e, ...updates } : e))
    setEditing(null)
  }

  function handleDelete(id) {
    setEvents(prev => prev.filter(e => e.id !== id))
  }

  function handleToggleDone(id) {
    setEvents(prev => prev.map(e => e.id === id ? { ...e, done: !e.done } : e))
  }

  function handleViewEvent(event) {
    setViewingEvent(event)
  }

  function handleCloseDetail() {
    setViewingEvent(null)
  }

  // Filter displayed events
  const displayedEvents = filterCategory === 'all' ? events : events.filter(e => e.category === filterCategory)

  return (
    <div className="app">
      <main className="app-main">
        <aside className="sidebar">
          <EventForm onCreate={handleCreate} onUpdate={handleUpdate} editing={editing} onCancel={() => setEditing(null)} />
          <EventList 
            events={events} 
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
            categories={categories}
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
          onClose={handleCloseDetail}
          onEdit={setEditing}
          onDelete={handleDelete}
          onToggleDone={handleToggleDone}
        />
      )}

      <footer className="app-footer">Built with REST API • Smooth UI • Minimal</footer>
    </div>
  )
}
