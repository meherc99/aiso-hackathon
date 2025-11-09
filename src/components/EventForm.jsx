import React, { useEffect, useMemo, useState } from 'react'

export default function EventForm({ events = [], categories = [], onCreate, onUpdate, editing, onCancel }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [category, setCategory] = useState('work')

  const fallbackCategory = useMemo(() => {
    if (!Array.isArray(categories) || categories.length === 0) {
      return 'work'
    }
    const preferred = categories.find(cat => cat.id === 'work') ?? categories[0]
    return preferred?.id || 'work'
  }, [categories])

  useEffect(() => {
    if (editing) {
      setTitle(editing.title || '')
      setDescription(editing.description || '')
      setStartDate(editing.startDate || '')
      setEndDate(editing.endDate || '')
      setStartTime(editing.startTime || '')
      setEndTime(editing.endTime || '')
      setCategory(editing.category || fallbackCategory)
    } else {
      setTitle('')
      setDescription('')
      setStartDate('')
      setEndDate('')
      setStartTime('')
      setEndTime('')
      setCategory(fallbackCategory)
    }
  }, [editing, fallbackCategory])

  const timedEvents = useMemo(() => Array.isArray(events) ? events : [], [events])

  function timeToMinutes(value) {
    if (!value || typeof value !== 'string') return null
    const match = value.match(/^(\d{1,2}):(\d{2})$/)
    if (!match) return null
    const hours = Number(match[1])
    const minutes = Number(match[2])
    if (
      Number.isNaN(hours) || Number.isNaN(minutes) ||
      hours < 0 || hours > 23 || minutes < 0 || minutes > 59
    ) {
      return null
    }
    return hours * 60 + minutes
  }

  function computeRange(event) {
    const start = timeToMinutes(event.startTime)
    const end = timeToMinutes(event.endTime)

    if (start === null && end === null) {
      // Treat events without explicit times as occupying the full day
      return { start: 0, end: 24 * 60 }
    }

    const safeStart = start ?? 0
    let safeEnd = end
    if (safeEnd === null) {
      safeEnd = start !== null ? Math.min(start + 60, 24 * 60) : 24 * 60
    }
    if (safeEnd <= safeStart) {
      safeEnd = Math.min(safeStart + 1, 24 * 60)
    }
    return { start: safeStart, end: safeEnd }
  }

  function hasConflict(candidate, excludeId) {
    if (!candidate.startDate) return false
    const candidateRange = computeRange(candidate)

    return timedEvents.some(existing => {
      if (!existing || existing.id === excludeId) return false
      if (existing.startDate !== candidate.startDate) return false

      const existingRange = computeRange(existing)
      const overlaps = existingRange.start < candidateRange.end && candidateRange.start < existingRange.end
      return overlaps
    })
  }

  async function handleSubmit(e) {
    // Prevent the browser's default form submission so we can handle it in React
    e.preventDefault()

    const safeCategory = category || fallbackCategory
    const payload = { title, description, startDate, endDate, startTime, endTime, category: safeCategory }

    if (!startDate) {
      window.alert('Please select a start date for the event.')
      return
    }

    if (hasConflict(payload, editing?.id)) {
      window.alert('There is already a meeting scheduled for this time. Please choose a different slot.')
      return
    }

    try {
      if (editing) {
        await onUpdate(editing.id, payload)
      } else {
        await onCreate(payload)
      }
      clear()
    } catch (err) {
      console.error('Failed to save event', err)
      window.alert('Failed to save event. See console for details.')
    }
  }

  function clear() {
    setTitle('')
    setDescription('')
    setStartDate('')
    setEndDate('')
    setStartTime('')
    setEndTime('')
    setCategory(fallbackCategory)
    if (onCancel) onCancel()
  }

  function handleCategoryChange(e) {
    setCategory(e.target.value)
  }

  return (
    <>
      <form className="event-form" onSubmit={handleSubmit}>
        <h2>{editing ? 'Edit Event' : 'New Event'}</h2>
        <label>Title
          <input value={title} onChange={e => setTitle(e.target.value)} required />
        </label>

        <label>Description
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} />
        </label>

        <div className="row">
          <label>Start Date
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} required />
          </label>
          <label>Start Time
            <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} />
          </label>
        </div>

        <div className="row">
          <label>End Date
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
          </label>
          <label>End Time
            <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} />
          </label>
        </div>

        <label>Category
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <select value={category} onChange={handleCategoryChange} style={{ flex: 1 }}>
              {categories.map(c => (
                <option value={c.id} key={c.id}>{c.name}</option>
              ))}
            </select>
            {category && (() => {
              const sel = categories.find(c => c.id === category)
              if (sel) {
                return (
                  <span 
                    style={{ 
                      display: 'inline-block', 
                      width: '20px', 
                      height: '20px', 
                      background: sel.color, 
                      borderRadius: '4px',
                      border: '1px solid #ccc'
                    }} 
                    aria-label={`Color: ${sel.color}`}
                    title={sel.color}
                  />
                )
              }
              return null
            })()}
          </div>
        </label>

        <div className="form-actions">
          <button type="submit" className="btn primary">{editing ? 'Update' : 'Create'}</button>
          {editing ? <button type="button" className="btn" onClick={clear}>Cancel</button> : <button type="button" className="btn" onClick={clear}>Clear</button>}
        </div>
      </form>
    </>
  )
}
