import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../api.js'
import { colors, card, font, shadows } from '../theme.js'

const MEAL_ICONS = { breakfast: '🌅', lunch: '☀️', dinner: '🌙', snack: '🍎' }
const MEAL_ORDER = ['breakfast', 'lunch', 'dinner', 'snack']
const MEAL_COLORS = { breakfast: '#f59e0b', lunch: '#34d399', dinner: '#a78bfa', snack: '#60a5fa' }

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Доброе утро 🌅'
  if (h < 17) return 'Добрый день ☀️'
  return 'Добрый вечер 🌙'
}

function getDateStr() {
  return new Date().toLocaleDateString('ru', { weekday: 'long', day: 'numeric', month: 'long' })
}

function CalorieRing({ current, limit }) {
  const [animated, setAnimated] = useState(false)
  useEffect(() => { const t = setTimeout(() => setAnimated(true), 100); return () => clearTimeout(t) }, [])

  const r = 68, cx = 85, cy = 85, stroke = 10
  const circ = 2 * Math.PI * r
  const pct = limit ? Math.min(current / limit, 1) : 0
  const dash = animated ? circ * pct : 0
  const left = Math.max(0, limit - current)

  return (
    <div style={s.ringCard}>
      <div style={s.ringRow}>
        <div style={s.ringStat}>
          <div style={s.ringNum}>{Math.round(current)}</div>
          <div style={s.ringSub}>съедено</div>
        </div>
        <div style={{ position: 'relative', width: 170, height: 170, flexShrink: 0 }}>
          <svg width="170" height="170" viewBox="0 0 170 170">
            <defs>
              <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#7c5cfc"/>
                <stop offset="100%" stopColor="#a78bfa"/>
              </linearGradient>
            </defs>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke}/>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke="url(#ringGrad)" strokeWidth={stroke}
              strokeDasharray={`${dash} ${circ}`} strokeDashoffset={0}
              strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`}
              style={{ transition: 'stroke-dasharray 900ms cubic-bezier(0.34,1.56,0.64,1)' }}
            />
          </svg>
          <div style={s.ringCenter}>
            <div style={s.ringBig}>{Math.round(pct * 100)}%</div>
            <div style={s.ringLabel}>ккал</div>
          </div>
        </div>
        <div style={s.ringStat}>
          <div style={s.ringNum}>{Math.round(left)}</div>
          <div style={s.ringSub}>осталось</div>
        </div>
      </div>
      <div style={s.ringLimit}>из {limit || '—'} ккал в день</div>
    </div>
  )
}

function MacroBar({ label, current, limit, grad, delay }) {
  const [animated, setAnimated] = useState(false)
  useEffect(() => { const t = setTimeout(() => setAnimated(true), 200 + delay); return () => clearTimeout(t) }, [])
  const pct = limit ? Math.min(current / limit * 100, 100) : 0

  return (
    <div style={s.macroRow}>
      <div style={s.macroLabel}>{label}</div>
      <div style={s.barTrack}>
        <div style={{ ...s.barFill, background: grad, width: animated ? `${pct}%` : '0%' }} />
      </div>
      <div style={s.macroVal}>{Math.round(current)}<span style={{ color: colors.textMuted }}>/{limit}г</span></div>
    </div>
  )
}

function EditModal({ entry, onSave, onClose }) {
  const [grams, setGrams] = useState(String(entry.amount_g))
  const [saving, setSaving] = useState(false)

  const g = parseFloat(grams) || 0
  const factor = entry.amount_g > 0 ? g / entry.amount_g : 0
  const newCal = Math.round(entry.calories * factor)
  const newP = (entry.protein * factor).toFixed(1)
  const newF = (entry.fat * factor).toFixed(1)
  const newC = (entry.carbs * factor).toFixed(1)
  const valid = g > 0 && g <= 5000

  const save = async () => {
    if (!valid || saving) return
    setSaving(true)
    try { await onSave(entry.id, g); onClose() }
    catch (e) { alert(e.message); setSaving(false) }
  }

  return createPortal(
    <div style={em.overlay}>
      <div style={em.backdrop} onClick={onClose} />
      <div style={em.sheet}>
        <div style={em.handle} />
        <div style={em.label}>Изменить порцию</div>
        <div style={em.foodName}>{entry.food_name}</div>
        <div style={em.inputRow}>
          <input
            style={em.input}
            type="number"
            inputMode="decimal"
            value={grams}
            onChange={e => setGrams(e.target.value)}
            min="1"
            max="5000"
            autoFocus
          />
          <span style={em.unit}>г</span>
        </div>
        {g > 0 && (
          <div style={em.preview}>
            <div style={em.previewItem}><span style={em.previewVal}>{newCal}</span><span style={em.previewKey}>ккал</span></div>
            <div style={em.previewItem}><span style={em.previewVal}>{newP}</span><span style={em.previewKey}>белки</span></div>
            <div style={em.previewItem}><span style={em.previewVal}>{newF}</span><span style={em.previewKey}>жиры</span></div>
            <div style={em.previewItem}><span style={em.previewVal}>{newC}</span><span style={em.previewKey}>углев.</span></div>
          </div>
        )}
        <div style={em.btns}>
          <button style={em.cancelBtn} onClick={onClose}>Отмена</button>
          <button style={{ ...em.saveBtn, opacity: valid ? 1 : 0.45 }} onClick={save} disabled={!valid || saving}>
            {saving ? '…' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

export default function Today({ onNavigate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [editEntry, setEditEntry] = useState(null)

  const load = () => {
    setLoading(true)
    api.getToday()
      .then(setData).catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const handleDelete = async (id) => {
    setDeleting(id)
    try { await api.deleteFood(id); load() }
    catch (e) { alert(e.message) }
    finally { setDeleting(null) }
  }

  const handleWater = async () => {
    try { await api.addWater(1); load() } catch (e) { alert(e.message) }
  }

  const handleEditSave = async (id, amount_g) => {
    await api.updateFood(id, amount_g)
    load()
  }

  if (loading) return (
    <div style={s.center}>
      <div style={{ width: 44, height: 44, borderRadius: '50%', border: `3px solid ${colors.accentSubtle}`, borderTop: `3px solid ${colors.accent}`, animation: 'spin 0.8s linear infinite' }} />
      <div style={{ color: colors.textSub, fontSize: 14, marginTop: 12 }}>Загрузка...</div>
    </div>
  )

  if (error) return (
    <div style={s.center}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>⚠️</div>
      <div style={{ color: colors.danger, fontWeight: 700, fontSize: 16, marginBottom: 8 }}>{error}</div>
      {(error.includes('404') || error.includes('not found')) &&
        <div style={{ color: colors.textSub, fontSize: 13, textAlign: 'center' }}>Настрой профиль через бота: /setup</div>
      }
      <button style={{ ...s.accentBtn, marginTop: 20 }} onClick={load}>Повторить</button>
    </div>
  )

  const { totals, limits, entries, water_glasses } = data
  const grouped = MEAL_ORDER.reduce((acc, meal) => {
    const items = entries.filter(e => e.meal_type === meal)
    if (items.length) acc[meal] = items
    return acc
  }, {})

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div style={s.greeting}>{getGreeting()}</div>
        <div style={s.dateStr}>{getDateStr()}</div>
      </div>

      <CalorieRing current={totals.calories} limit={limits.calories} />

      <div style={card}>
        <MacroBar label="Белки" current={totals.protein} limit={limits.protein} grad={colors.proteinGrad} delay={0} />
        <MacroBar label="Жиры"  current={totals.fat}     limit={limits.fat}     grad={colors.fatGrad}     delay={80} />
        <MacroBar label="Углеводы" current={totals.carbs} limit={limits.carbs}  grad={colors.carbsGrad}   delay={160} />
      </div>

      <div style={card}>
        <div style={s.waterHeader}>
          <span style={s.waterTitle}>💧 Вода</span>
          <button style={s.waterBtn} onClick={handleWater}>+1 стакан</button>
        </div>
        <div style={s.glasses}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} style={{ ...s.glass, background: i < water_glasses ? colors.water : 'rgba(255,255,255,0.10)', boxShadow: i < water_glasses ? `0 0 8px rgba(56,189,248,0.5)` : 'none' }} />
          ))}
        </div>
        <div style={{ color: colors.textSub, fontSize: 12, textAlign: 'center', marginTop: 8 }}>{water_glasses} из 8 стаканов</div>
      </div>

      {Object.keys(grouped).length === 0 ? (
        <div style={s.empty}>
          <div style={s.emptyCircle}>🍽️</div>
          <div style={s.emptyTitle}>Начни свой день!</div>
          <div style={s.emptySub}>Добавь первый приём пищи</div>
          <button style={s.accentBtn} onClick={() => onNavigate('add')}>➕ Добавить еду</button>
        </div>
      ) : (
        Object.entries(grouped).map(([meal, items]) => {
          const mealCal = items.reduce((s, e) => s + e.calories, 0)
          return (
            <div key={meal} style={card}>
              <div style={s.mealHeader}>
                <div style={{ ...s.mealDot, background: MEAL_COLORS[meal] }} />
                <span style={s.mealName}>{MEAL_ICONS[meal]} {items[0].meal_label}</span>
                <span style={{ ...s.mealCal, color: MEAL_COLORS[meal] }}>{Math.round(mealCal)} ккал</span>
              </div>
              {items.map((item, idx) => (
                <div key={item.id} style={{ ...s.entry, animation: `slideUp 250ms ease ${idx * 40}ms both` }}>
                  <div style={{ ...s.entryAccent, background: MEAL_COLORS[meal] }} />
                  <div style={s.entryInfo}>
                    <div style={s.entryName}>{item.food_name}</div>
                    <div style={s.entrySub}>{item.amount_g}г · {Math.round(item.calories)} ккал · Б{item.protein} Ж{item.fat} У{item.carbs}</div>
                  </div>
                  <button style={s.editBtn} onClick={() => setEditEntry(item)}>✏</button>
                  <button style={s.deleteBtn} onClick={() => handleDelete(item.id)} disabled={deleting === item.id}>
                    {deleting === item.id ? '…' : '✕'}
                  </button>
                </div>
              ))}
            </div>
          )
        })
      )}
      <div style={{ height: 16 }} />
      {editEntry && <EditModal entry={editEntry} onSave={handleEditSave} onClose={() => setEditEntry(null)} />}
    </div>
  )
}

const s = {
  page: { padding: '16px 14px' },
  center: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '65vh', gap: 8 },
  header: { marginBottom: 18 },
  greeting: { ...font.display, fontSize: 24, color: colors.text, marginBottom: 4 },
  dateStr: { fontSize: 13, color: colors.textSub, textTransform: 'capitalize' },
  ringCard: { ...card, textAlign: 'center', padding: 20, marginBottom: 12 },
  ringRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  ringStat: { flex: 1, textAlign: 'center' },
  ringNum: { fontSize: 22, fontWeight: 800, color: colors.text },
  ringSub: { fontSize: 11, color: colors.textSub, marginTop: 2 },
  ringCenter: { position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' },
  ringBig: { fontSize: 28, fontWeight: 800, color: colors.text },
  ringLabel: { fontSize: 12, color: colors.textSub },
  ringLimit: { fontSize: 12, color: colors.textMuted, marginTop: 10 },
  macroRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 },
  macroLabel: { width: 70, fontSize: 13, color: colors.textSub, fontWeight: 500 },
  barTrack: { flex: 1, height: 7, background: 'rgba(255,255,255,0.08)', borderRadius: 4, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 4, transition: 'width 700ms cubic-bezier(0.34,1.56,0.64,1)' },
  macroVal: { fontSize: 12, color: colors.text, fontWeight: 600, width: 72, textAlign: 'right' },
  waterHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  waterTitle: { fontSize: 15, fontWeight: 700 },
  waterBtn: { background: colors.accentGradient, border: 'none', borderRadius: 10, padding: '7px 14px', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' },
  glasses: { display: 'flex', gap: 7, justifyContent: 'center' },
  glass: { width: 28, height: 28, borderRadius: 7, transition: 'all 300ms ease' },
  empty: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 20px', gap: 10 },
  emptyCircle: { width: 80, height: 80, borderRadius: '50%', background: colors.accentSubtle, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 36, marginBottom: 8 },
  emptyTitle: { fontSize: 20, fontWeight: 700, color: colors.text },
  emptySub: { fontSize: 14, color: colors.textSub, marginBottom: 8 },
  accentBtn: { background: colors.accentGradient, border: 'none', borderRadius: 16, padding: '14px 28px', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer', boxShadow: shadows.btn },
  mealHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 },
  mealDot: { width: 8, height: 8, borderRadius: '50%' },
  mealName: { flex: 1, fontSize: 14, fontWeight: 700, color: colors.textSub },
  mealCal: { fontSize: 13, fontWeight: 700 },
  entry: { display: 'flex', alignItems: 'center', gap: 10, paddingTop: 10, borderTop: `1px solid ${colors.divider}`, marginTop: 4 },
  entryAccent: { width: 3, height: 36, borderRadius: 2, flexShrink: 0 },
  entryInfo: { flex: 1 },
  entryName: { fontSize: 14, fontWeight: 600, color: colors.text },
  entrySub: { fontSize: 11, color: colors.textSub, marginTop: 2 },
  deleteBtn: { background: 'rgba(248,113,113,0.15)', border: 'none', borderRadius: '50%', width: 28, height: 28, color: colors.danger, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  editBtn: { background: 'rgba(124,92,252,0.15)', border: 'none', borderRadius: '50%', width: 28, height: 28, color: colors.accent, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
}

const em = {
  overlay: { position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' },
  backdrop: { position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)' },
  sheet: { position: 'relative', zIndex: 1, background: 'linear-gradient(160deg, #13132a 0%, #0f0f25 100%)', borderRadius: '20px 20px 0 0', padding: '12px 20px calc(32px + env(safe-area-inset-bottom, 0px))', border: '1px solid rgba(124,92,252,0.2)', borderBottom: 'none' },
  handle: { width: 36, height: 4, background: 'rgba(255,255,255,0.2)', borderRadius: 2, margin: '0 auto 20px' },
  label: { fontSize: 11, color: 'rgba(167,139,250,0.7)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 },
  foodName: { fontSize: 17, fontWeight: 700, color: '#fff', marginBottom: 20 },
  inputRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 },
  input: { flex: 1, background: 'rgba(255,255,255,0.07)', border: '1.5px solid rgba(124,92,252,0.4)', borderRadius: 12, padding: '14px 16px', color: '#fff', fontSize: 28, fontWeight: 700, outline: 'none', textAlign: 'center' },
  unit: { fontSize: 18, color: 'rgba(255,255,255,0.5)', fontWeight: 600 },
  preview: { display: 'flex', gap: 8, marginBottom: 24, background: 'rgba(124,92,252,0.1)', borderRadius: 12, padding: 12 },
  previewItem: { flex: 1, textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 3 },
  previewVal: { fontSize: 15, fontWeight: 700, color: '#fff' },
  previewKey: { fontSize: 10, color: 'rgba(255,255,255,0.4)' },
  btns: { display: 'flex', gap: 10 },
  cancelBtn: { flex: 1, background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 14, padding: 15, color: 'rgba(255,255,255,0.7)', fontSize: 15, fontWeight: 600, cursor: 'pointer' },
  saveBtn: { flex: 2, background: 'linear-gradient(135deg, #7c5cfc 0%, #a78bfa 100%)', border: 'none', borderRadius: 14, padding: 15, color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer' },
}
