import React, { useEffect, useState } from 'react'
import Calendar from './components/Calendar'
import EventForm from './components/EventForm'
import EventList from './components/EventList'
import EventDetailModal from './components/EventDetailModal'
import { loadEvents, saveEvents, getSampleEvents, loadCategories, getCategoryById } from './store/events'

export default function App() {
  const [events, setEvents] = useState([])
  const [editing, setEditing] = useState(null)
  const [viewingEvent, setViewingEvent] = useState(null)
  const [filterCategory, setFilterCategory] = useState('all')
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    const loaded = loadEvents()
    console.log('Loaded events from localStorage:', loaded)
    if (!loaded || loaded.length === 0) {
      const samples = getSampleEvents()
      console.log('Creating sample events:', samples)
      saveEvents(samples)
      setEvents(samples)
    } else {
      setEvents(loaded)
    }
    setIsInitialized(true)
  }, [])

  useEffect(() => {
    if (isInitialized) {
      console.log('Saving events to localStorage:', events)
      saveEvents(events)
    }
  }, [events, isInitialized])

  function handleCreate(event) {
    setEvents(prev => [event, ...prev])
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

  // Get unique category IDs from events, then load full category objects
  const categoryIds = Array.from(new Set(events.map(e => e.category))).filter(Boolean)
  const categories = categoryIds.map(id => getCategoryById(id)).filter(Boolean)

  const displayedEvents = filterCategory === 'all' ? events : events.filter(e => e.category === filterCategory)

  return (
    <div className="app">
      <main className="app-main">
        <aside className="sidebar">
          <EventForm
            events={events}
            onCreate={handleCreate}
            onUpdate={handleUpdate}
            editing={editing}
            onCancel={() => setEditing(null)}
          />
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

      <footer className="app-footer">Built with localStorage • Smooth UI • Minimal</footer>
    </div>
  )
}
