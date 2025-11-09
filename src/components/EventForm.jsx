import React, { useEffect, useState } from 'react'
import { createEvent, loadCategories, createCategory } from '../store/events'

export default function EventForm({ onCreate, onUpdate, editing, onCancel }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [category, setCategory] = useState('')
  const [categories, setCategories] = useState([])
  
  // Create-new-category modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newCatName, setNewCatName] = useState('')
  const [newCatColor, setNewCatColor] = useState('#3b82f6')

  useEffect(() => {
    // Load categories on mount
    async function fetchCategories() {
      try {
        const cats = await loadCategories()
        setCategories(Array.isArray(cats) ? cats : [])
      } catch (error) {
        console.error('Error loading categories:', error)
        setCategories([])
      }
    }
    fetchCategories()
  }, [])

  useEffect(() => {
    if (editing) {
      setTitle(editing.title || '')
      setDescription(editing.description || '')
      setStartDate(editing.startDate || '')
      setEndDate(editing.endDate || '')
      setStartTime(editing.startTime || '')
      setEndTime(editing.endTime || '')
      setCategory(editing.category || '')
    } else {
      setTitle('')
      setDescription('')
      setStartDate('')
      setEndDate('')
      setStartTime('')
      setEndTime('')
      setCategory('')
    }
  }, [editing])

  async function handleSubmit(e) {
    // Prevent the browser's default form submission so we can handle it in React
    e.preventDefault()
    try {
      if (editing) {
        onUpdate(editing.id, { title, description, startDate, endDate, startTime, endTime, category })
      } else {
        const ev = await createEvent({ title, description, startDate, endDate, startTime, endTime, category })
        onCreate(ev)
      }
      clear()
    } catch (error) {
      console.error('Error submitting event:', error)
    }
  }

  function clear() {
    setTitle('')
    setDescription('')
    setStartDate('')
    setEndDate('')
    setStartTime('')
    setEndTime('')
    setCategory('')
    if (onCancel) onCancel()
  }

  function handleCategoryChange(e) {
    const val = e.target.value
    if (val === '__create__') {
      setNewCatName('')
      setNewCatColor('#3b82f6')
      setShowCreateModal(true)
      return
    }
    setCategory(val)
  }

  async function handleCreateCategory(e) {
    e.preventDefault()
    if (!newCatName.trim()) return
    try {
      const cat = await createCategory({ name: newCatName.trim(), color: newCatColor })
      const updated = await loadCategories()
      setCategories(Array.isArray(updated) ? updated : [])
      setCategory(cat.id)
      setShowCreateModal(false)
    } catch (error) {
      console.error('Error creating category:', error)
    }
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
              <option value="">None</option>
              {(categories || []).map(c => (
                <option value={c.id} key={c.id}>{c.name}</option>
              ))}
              <option value="__create__">+ Create new category...</option>
            </select>
            {category && (() => {
              const sel = (categories || []).find(c => c.id === category)
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

      {showCreateModal && (
      <div 
        className="modal-backdrop" 
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}
        onClick={() => setShowCreateModal(false)}
      >
        <div 
          className="modal-content"
          style={{
            background: '#fff',
            padding: '24px',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '400px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}
          onClick={e => e.stopPropagation()}
        >
          <h3 style={{ marginTop: 0 }}>Create New Category</h3>
          <form onSubmit={handleCreateCategory}>
            <label style={{ display: 'block', marginBottom: '16px' }}>
              <div style={{ marginBottom: '4px', fontWeight: 500 }}>Category Name</div>
              <input 
                type="text"
                value={newCatName} 
                onChange={e => setNewCatName(e.target.value)} 
                placeholder="e.g., Work, Personal"
                required 
                style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                autoFocus
              />
            </label>
            
            <label style={{ display: 'block', marginBottom: '16px' }}>
              <div style={{ marginBottom: '4px', fontWeight: 500 }}>Color</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <input 
                  type="color" 
                  value={newCatColor} 
                  onChange={e => setNewCatColor(e.target.value)}
                  style={{ width: '60px', height: '40px', border: 'none', cursor: 'pointer' }}
                />
                <input 
                  type="text"
                  value={newCatColor}
                  onChange={e => setNewCatColor(e.target.value)}
                  pattern="^#[0-9A-Fa-f]{6}$"
                  style={{ flex: 1, padding: '8px', fontFamily: 'monospace' }}
                />
              </div>
            </label>
            
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button 
                type="button" 
                onClick={() => setShowCreateModal(false)}
                className="btn"
              >
                Cancel
              </button>
              <button type="submit" className="btn primary">
                Create
              </button>
            </div>
          </form>
        </div>
      </div>
    )}
    </>
  )
}
