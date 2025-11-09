import React, { useState, useMemo } from 'react'

//Month grid where events are displayed
function getMonthGrid(year, month) {
  const first = new Date(year, month, 1)
  const last = new Date(year, month + 1, 0)
  const startDay = first.getDay() // 0-6 (0=Sunday)
  
  // Adjust so Monday=0, Tuesday=1, ..., Sunday=6
  const adjustedStartDay = startDay === 0 ? 6 : startDay - 1
  
  const days = []
  // leading blanks
  for (let i = 0; i < adjustedStartDay; i++) days.push(null)
  for (let d = 1; d <= last.getDate(); d++) days.push(new Date(year, month, d))
  return { days, monthName: first.toLocaleString(undefined, { month: 'long' }), year }
}

export default function Calendar({ events = [], filterCategory, onFilterChange, categories = [], onEdit, onDelete, onToggleDone, onViewEvent }) {
  const today = new Date()
  const [selectedYear, setSelectedYear] = useState(today.getFullYear())
  const [selectedMonth, setSelectedMonth] = useState(today.getMonth())

  const { days, monthName } = useMemo(() => getMonthGrid(selectedYear, selectedMonth), [selectedYear, selectedMonth])

  // Format a Date to local YYYY-MM-DD to avoid UTC/timezone shifts from toISOString()
  function toLocalISO(date) {
    if (!date || !(date instanceof Date)) return ''
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }

  // Build month names and year options
  const months = useMemo(() => {
    return Array.from({ length: 12 }, (_, i) => new Date(2000, i, 1).toLocaleString(undefined, { month: 'long' }))
  }, [])

  // Provide a reasonable year range; 1970-2100 is broad enough for most cases
  const years = useMemo(() => {
    const start = 1970
    const end = 2100
    const arr = []
    for (let y = start; y <= end; y++) arr.push(y)
    return arr
  }, [])

  const eventsByDay = useMemo(() => events.reduce((acc, ev) => {
    if (!ev || !ev.startDate) return acc
    const day = ev.startDate
    acc[day] = acc[day] || []
    acc[day].push(ev)
    return acc
  }, {}), [events])

  function gotoPrevMonth() {
    setSelectedMonth(m => {
      if (m === 0) {
        setSelectedYear(y => y - 1)
        return 11
      }
      return m - 1
    })
  }

  function gotoNextMonth() {
    setSelectedMonth(m => {
      if (m === 11) {
        setSelectedYear(y => y + 1)
        return 0
      }
      return m + 1
    })
  }

  return (
    <div className="calendar">
      <div className="cal-header">
        <button onClick={gotoPrevMonth} aria-label="Previous month">‹</button>
        <div className="cal-selects">
          <select value={selectedMonth} onChange={e => setSelectedMonth(Number(e.target.value))} aria-label="Select month">
            {months.map((m, i) => <option value={i} key={i}>{m}</option>)}
          </select>
          <select value={selectedYear} onChange={e => setSelectedYear(Number(e.target.value))} aria-label="Select year">
            {years.map(y => <option value={y} key={y}>{y}</option>)}
          </select>
          <button onClick={() => { setSelectedMonth(today.getMonth()); setSelectedYear(today.getFullYear()) }} className="today-btn" aria-label="Go to current month and year">Today</button>
        </div>
        <button onClick={gotoNextMonth} aria-label="Next month">›</button>
      </div>
      <h2>{monthName} {selectedYear}</h2>
      <div className="filters">
        <label>
          Category:
          <select value={filterCategory} onChange={e => onFilterChange(e.target.value)}>
            <option value="all">All</option>
            {(categories || []).map(c => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="cal-grid">
        <div className="cal-weekdays">
          <div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div><div>Sun</div>
        </div>
        <div className="cal-days">
          {days.map((d, i) => {
            const key = d ? toLocalISO(d) : `empty-${i}`
            const dayKey = d ? toLocalISO(d) : null
            const dayEvents = dayKey ? eventsByDay[dayKey] || [] : []
            const isToday = d && toLocalISO(d) === toLocalISO(new Date())
            return (
              <div className={`cal-day ${isToday ? 'today' : ''}`} key={key}>
                {d && <div className="day-num">{d.getDate()}</div>}
                <div className="day-events">
                {dayEvents.map(ev => {
                  const category = categories.find(c => c.id === ev.category) || null
                  let timeDisplay = ''
                  if (ev.startTime) {
                    timeDisplay = ev.startTime.substring(0, 5)
                    if (ev.endTime) {
                      timeDisplay += `-${ev.endTime.substring(0, 5)}`
                    }
                  }
                  return (
                    <div key={ev.id} className={`cal-event ${ev.done ? 'done' : ''}`} style={{ borderLeftColor: category?.color || '#ccc' }}>
                      <span 
                        className="ev-title" 
                        onClick={(e) => {
                          e.stopPropagation()
                          onViewEvent && onViewEvent(ev)
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        {timeDisplay && <span className="ev-time">{timeDisplay}</span>}
                        {ev.title}
                      </span>
                      {category && <span className="ev-category" style={{ color: category.color }}>• {category.name}</span>}
                      
                    </div>
                  )
                })}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
