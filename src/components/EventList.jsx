import React from 'react'

export default function EventList({ events, categoryMap = {}, onEdit, onDelete, onToggleDone, onViewEvent }) {
  const sorted = [...events].sort((a,b) => new Date(a.startDate) - new Date(b.startDate))
  return (
    <div className="event-list">
      <h3>Events</h3>
      {sorted.length === 0 && <p>No events yet</p>}
      <ul>
        {sorted.map(ev => {
          const category = ev?.category ? categoryMap[ev.category] : null
          return (
            <li key={ev.id} className={ev.done ? 'done' : ''}>
              <div className="ev-main" onClick={() => onViewEvent && onViewEvent(ev)} style={{ cursor: 'pointer' }}>
                <strong>{ev.title}</strong>
                <div className="ev-meta">
                  {ev.startDate}
                  {ev.startTime && ` ${ev.startTime.substring(0, 5)}`}
                  {ev.endDate && ev.endDate !== ev.startDate ? ` — ${ev.endDate}` : ''}
                  {ev.endTime && ` ${ev.endTime.substring(0, 5)}`}
                  {category && (
                    <span style={{ color: category.color, marginLeft: '8px' }}>
                      • {category.name}
                    </span>
                  )}
                </div>
              </div>
              <div className="ev-actions">
                <button onClick={() => onToggleDone(ev.id)} title="Toggle done">{ev.done ? 'Undo' : 'Done'}</button>
                <button onClick={() => onEdit(ev)} title="Edit">✏️</button>
                <button onClick={() => onDelete(ev.id)} title="Delete">🗑️</button>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
