import React from 'react'

export default function EventDetailModal({ event, categoryMap = {}, onClose, onEdit, onDelete, onToggleDone }) {
  if (!event) return null

  const category = event?.category ? categoryMap[event.category] : null

  function handleEdit() {
    onEdit(event)
    onClose()
  }

  function handleDelete() {
    if (window.confirm(`Delete "${event.title}"?`)) {
      onDelete(event.id)
      onClose()
    }
  }

  function handleToggleDone() {
    onToggleDone(event.id)
  }

  return (
    <div 
      className="modal-backdrop" 
      onClick={onClose}
    >
      <div 
        className="event-detail-modal"
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2>{event.title}</h2>
          <button 
            className="close-btn" 
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="modal-body">
          {event.description && (
            <div className="detail-section">
              <label>Description</label>
              <p>{event.description}</p>
            </div>
          )}

          <div className="detail-section">
            <label>Start Date</label>
            <p>
              {event.startDate || 'Not set'}
              {event.startTime && ` at ${event.startTime}`}
            </p>
          </div>

          {event.endDate && event.endDate !== event.startDate && (
            <div className="detail-section">
              <label>End Date</label>
              <p>
                {event.endDate}
                {event.endTime && ` at ${event.endTime}`}
              </p>
            </div>
          )}

          {((event.endDate === event.startDate) || !event.endDate) && event.endTime && (
            <div className="detail-section">
              <label>End Time</label>
              <p>{event.endTime}</p>
            </div>
          )}

          {category && (
            <div className="detail-section">
              <label>Category</label>
              <p>
                <span 
                  className="category-badge"
                  style={{ 
                    backgroundColor: category.color,
                    color: '#fff',
                    padding: '4px 12px',
                    borderRadius: '4px',
                    display: 'inline-block'
                  }}
                >
                  {category.name}
                </span>
              </p>
            </div>
          )}

          <div className="detail-section">
            <label>Status</label>
            <p>
              <button 
                onClick={handleToggleDone}
                className={`status-btn ${event.done ? 'done' : 'pending'}`}
              >
                {event.done ? '✓ Completed' : '○ Pending'}
              </button>
            </p>
          </div>

          {event.created_at && (
            <div className="detail-section">
              <label>Created</label>
              <p style={{ fontSize: '12px', color: 'var(--muted)' }}>
                {new Date(event.created_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={handleEdit} className="btn">
            ✎ Edit
          </button>
          <button onClick={handleDelete} className="btn delete-btn">
            🗑 Delete
          </button>
        </div>
      </div>
    </div>
  )
}
