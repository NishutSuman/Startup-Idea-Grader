import React, { useEffect, useRef, useState } from 'react'
import { expandIdea, evaluate, getHistory, getEvaluation } from './api.js'

const PROVIDERS = [
  { id: 'gemini', label: 'Gemini (free)' },
  { id: 'openai', label: 'ChatGPT (OpenAI)' },
  { id: 'anthropic', label: 'Claude (Anthropic)' },
]
const COST = {
  gemini: 'Free tier, roughly zero cost per idea',
  anthropic: 'About Rs 3 to 4 per idea (Claude Haiku)',
  openai: 'About Rs 4 to 6 per idea (gpt-4o-mini)',
}
const FORM_FIELDS = [
  { key: 'idea', full: true, label: 'What are you building?',
    help: 'Describe the product or service in a sentence or two. What does it actually do for someone?' },
  { key: 'core_problem', full: true, label: 'What problem does it solve, and for whom?',
    help: 'What real, painful problem are you fixing? Who feels it most, and how do they cope today?' },
  { key: 'target_customer', label: 'Who is the paying customer?',
    help: 'Who pulls out their wallet? Be specific.' },
  { key: 'key_differentiator', label: 'What makes it better or different?',
    help: 'Your edge over existing options, or over doing nothing.' },
  { key: 'business_model', label: 'How does it make money?',
    help: 'Subscription, commission, one-time, ads? Who pays?' },
  { key: 'pricing', label: 'Pricing (if you know)', help: 'A rough price point is fine.' },
  { key: 'geography', label: 'Where do you start?', help: 'First city, country, or segment.' },
  { key: 'stage', label: 'What stage are you at?', help: 'Idea, prototype, or launched.' },
]
const LABELS = Object.fromEntries(FORM_FIELDS.map(f => [f.key, f.label]))
const LOADER_LINES = [
  'Reading your pitch the way an investor would',
  'Pressure-testing the problem and the market',
  'Sizing the opportunity and the competition',
  'Checking the moat and how easily it copies',
  'Running the unit economics',
  'Reviewing go-to-market and retention',
  'Weighing execution and the real risks',
  'Writing the final assessment',
]
const LI_PATH = 'M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.8 0 0 .78 0 1.73v20.54C0 23.22.8 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .78 23.2 0 22.22 0z'

export default function App() {
  const [view, setView] = useState('new')        // 'new' | 'history'
  const [report, setReport] = useState(null)      // { inputs, result, from }

  const [mode, setMode] = useState('structured')
  const [provider, setProvider] = useState('gemini')
  const [grounding, setGrounding] = useState('reasoned')
  const [apiKey, setApiKey] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)

  const [form, setForm] = useState({})
  const [quick, setQuick] = useState('')
  const [expandFields, setExpandFields] = useState(null)
  const [answers, setAnswers] = useState({})

  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])
  const scroller = useRef()

  useEffect(() => { getHistory().then(setHistory) }, [])
  useEffect(() => { if (scroller.current) scroller.current.scrollTop = 0 }, [report, view, busy])

  const common = () => ({ provider, apiKey, grounding })
  const go = (v) => { setReport(null); setError(''); setView(v); if (v === 'history') getHistory().then(setHistory) }

  async function runExpand() {
    setError(''); setExpandFields(null)
    if (!quick.trim()) return setError('Type a one-line idea first.')
    setBusy('expand')
    try {
      const { fields } = await expandIdea({ idea: quick, ...common() })
      setExpandFields(fields || [])
      const seed = {}; for (const f of fields || []) seed[f.key] = (f.options && f.options[0]) || ''
      setAnswers(seed)
    } catch (e) { setError(e.message) } finally { setBusy('') }
  }
  async function runEvaluate(inputs, m) {
    setError(''); setBusy('evaluate')
    try {
      const res = await evaluate({ mode: m, inputs, ...common() })
      setReport({ inputs, result: res, from: 'new' })
      getHistory().then(setHistory)
    } catch (e) { setError(e.message) } finally { setBusy('') }
  }
  async function openHistory(id) {
    setError(''); setBusy('load')
    try {
      const rec = await getEvaluation(id)
      setReport({ inputs: rec.inputs, result: rec.result, from: 'history' })
    } catch (e) { setError(e.message) } finally { setBusy('') }
  }
  const submitStructured = () =>
    (form.idea || '').trim() ? runEvaluate(form, 'structured') : setError('Describe the idea first.')
  const submitQuick = () => runEvaluate({ idea: quick, ...answers }, 'quick')

  const field = (f) => (
    <div className="field" key={f.key}>
      <label>{f.label}</label>
      <p className="help">{f.help}</p>
      {f.full
        ? <textarea rows={3} value={form[f.key] || ''} onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
        : <input value={form[f.key] || ''} onChange={e => setForm({ ...form, [f.key]: e.target.value })} />}
    </div>
  )

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand" onClick={() => go('new')}><span className="logo">◈</span> PitchLens</div>
        <nav className="nav">
          <button className={!report && view === 'new' ? 'navlink on' : 'navlink'} onClick={() => go('new')}>New Idea</button>
          <button className={!report && view === 'history' ? 'navlink on' : 'navlink'} onClick={() => go('history')}>History</button>
        </nav>
        <button className="gear" title="Settings" onClick={() => setSettingsOpen(true)}>⚙</button>
      </header>

      <main className="content" ref={scroller}>
        <div className="inner">
          {busy === 'evaluate' ? <Loader />
            : report ? <ReportView data={report} onBack={() => go(report.from)} />
            : view === 'history' ? <HistoryPage items={history} onOpen={openHistory} busy={busy === 'load'} />
            : (
              <>
                <div className="hero">
                  <h1>Grade Your Startup Idea</h1>
                  <p>Pitch an idea and get it scored out of 100 across five areas: market, product, finance, growth and execution.</p>
                </div>
                <div className="tabs">
                  <button className={mode === 'structured' ? 'tab on' : 'tab'} onClick={() => setMode('structured')}>Detailed Idea</button>
                  <button className={mode === 'quick' ? 'tab on' : 'tab'} onClick={() => setMode('quick')}>Quick Idea</button>
                </div>

                {mode === 'structured' ? (
                  <section className="card">
                    {FORM_FIELDS.filter(f => f.full).map(field)}
                    <div className="grid2">{FORM_FIELDS.filter(f => !f.full).map(field)}</div>
                    <button className="primary" disabled={!!busy} onClick={submitStructured}>Grade This Idea</button>
                  </section>
                ) : (
                  <section className="card">
                    <div className="field">
                      <label>Your idea in one line</label>
                      <p className="help">A rough thought is fine. We will fill in the blanks with you.</p>
                      <input placeholder='e.g. "alumni management system" or "used-car showroom platform"'
                        value={quick} onChange={e => setQuick(e.target.value)} />
                    </div>
                    {!expandFields && (
                      <button className="primary" disabled={!!busy} onClick={runExpand}>
                        {busy === 'expand' ? 'Thinking' : 'Fill in the blanks'}
                      </button>
                    )}
                    {expandFields && (
                      <>
                        <p className="hint">This idea is too thin to grade as-is, so pick the closest assumption for each, or type your own. We grade the strongest version and show what we assumed.</p>
                        {expandFields.map(f => (
                          <div className="field" key={f.key}>
                            <label>{f.question}</label>
                            <div className="chips">
                              {(f.options || []).map(opt => (
                                <button key={opt} className={answers[f.key] === opt ? 'chip on' : 'chip'}
                                  onClick={() => setAnswers({ ...answers, [f.key]: opt })}>{opt}</button>
                              ))}
                            </div>
                            <input className="other" placeholder="or type your own"
                              value={answers[f.key] || ''} onChange={e => setAnswers({ ...answers, [f.key]: e.target.value })} />
                          </div>
                        ))}
                        <button className="primary" disabled={!!busy} onClick={submitQuick}>Grade this idea</button>
                      </>
                    )}
                  </section>
                )}
                {error && <div className="error">{error}</div>}
              </>
            )}
        </div>
      </main>

      <footer className="bottombar">
        Built with ❤️ by{' '}
        <a className="li" href="https://www.linkedin.com/in/nishutsuman" target="_blank" rel="noreferrer">
          Nishut Suman
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d={LI_PATH} /></svg>
        </a>
      </footer>

      {settingsOpen && (
        <Settings provider={provider} setProvider={setProvider} grounding={grounding} setGrounding={setGrounding}
          apiKey={apiKey} setApiKey={setApiKey} cost={COST[provider]} onClose={() => setSettingsOpen(false)} />
      )}
    </div>
  )
}

function HistoryPage({ items, onOpen, busy }) {
  return (
    <div className="page-hist">
      <h2 className="rt">History</h2>
      {busy && <p className="help">Loading…</p>}
      {items.length === 0 ? (
        <p className="empty">No evaluations yet. Grade an idea and it will show up here.</p>
      ) : (
        <div className="histgrid">
          {items.map(h => (
            <button className="histcard" key={h.id} onClick={() => onOpen(h.id)}>
              <span className={'pill g-' + (h.grade || '')}>{h.grade}</span>
              <span className="hc-title">{h.title}</span>
              <span className="hc-meta">{h.total_score}/100 · {h.provider}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/* ---------------- report dashboard ---------------- */
function ReportView({ data, onBack }) {
  const { inputs, result } = data
  const g = result.grade || {}
  const syn = result.synthesis || {}
  const stats = collectStats(result.stages || [])
  const title = inputs.idea || inputs.core_problem || 'Your idea'

  return (
    <div className="reportv">
      <button className="back" onClick={onBack}>← Back</button>
      <h2 className="rt">{title}</h2>

      <div className="dash">
        <div className="ringcard">
          <ScoreRing score={result.total_score} grade={g.grade} />
          <div className="glabel">{g.label}</div>
          {syn.recommendation && <RecoBadge reco={syn.recommendation} />}
        </div>
        <div className="barscard">
          <div className="cap">Score by area</div>
          <StageBars stages={result.stages || []} />
        </div>
      </div>

      <div className="verdict-block">
        <h3>Final Verdict</h3>
        <p className="verdict-line">{syn.verdict}</p>
        <p className="summary">{syn.overall_summary}</p>
      </div>

      {stats.cards.length > 0 && (
        <div className="statgrid">
          {stats.cards.map((c, i) => (
            <div className="stat" key={i}><div className="sl">{prettyKey(c.label)}</div><div className="sv">{c.value}</div></div>
          ))}
        </div>
      )}

      <div className="two">
        <div className="col-card good-card"><h4>Key strengths</h4><ul>{(syn.top_strengths || []).map((s, i) => <li key={i}>{s}</li>)}</ul></div>
        <div className="col-card bad-card"><h4>Key risks</h4><ul>{(syn.key_risks || []).map((s, i) => <li key={i}>{s}</li>)}</ul></div>
      </div>

      {(syn.questions_for_founder || []).length > 0 && (
        <Expander title="Questions to resolve next" defaultOpen>
          <ul className="ql">{syn.questions_for_founder.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </Expander>
      )}

      <Expander title="Full breakdown by area">
        {(result.stages || []).map(st => (
          <div className="stage" key={st.stage}>
            <div className="stage-h"><h3>{st.stage_name}</h3><span className="ss">{st.stage_score}/100</span></div>
            {(st.atoms || []).map(a => (
              <div className="atom" key={a.key}>
                <div className="atom-head"><span>{a.name}</span><span className="as">{a.score}/10</span></div>
                <div className="bar"><i style={{ width: Math.max(0, Math.min(100, (a.score || 0) * 10)) + '%' }} /></div>
                <p className="why">{a.reasoning}</p>
                {a.concerns && <p className="watch"><b>Watch:</b> {a.concerns}</p>}
              </div>
            ))}
          </div>
        ))}
      </Expander>

      <Expander title="What was submitted">
        <div className="inputs">
          {Object.entries(inputs).map(([k, v]) => v ? (
            <div className="inrow" key={k}><b>{LABELS[k] || prettyKey(k)}</b><span>{String(v)}</span></div>
          ) : null)}
        </div>
      </Expander>
    </div>
  )
}

function ScoreRing({ score, grade }) {
  const r = 54, c = 2 * Math.PI * r
  const off = c * (1 - Math.max(0, Math.min(100, score)) / 100)
  const color = ['A', 'B'].includes(grade) ? 'var(--good)' : grade === 'C' ? 'var(--warn)' : 'var(--bad)'
  return (
    <svg viewBox="0 0 130 130" className="ring">
      <circle cx="65" cy="65" r={r} fill="none" stroke="var(--line)" strokeWidth="12" />
      <circle cx="65" cy="65" r={r} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 65 65)" />
      <text x="65" y="62" textAnchor="middle" className="ring-score">{score}</text>
      <text x="65" y="84" textAnchor="middle" className="ring-sub">/100 · {grade}</text>
    </svg>
  )
}
function StageBars({ stages }) {
  return (
    <div className="stagebars">
      {stages.map(s => {
        const v = s.stage_score || 0
        const cls = v >= 65 ? 'hi' : v >= 45 ? 'mid' : 'lo'
        return (
          <div className="sb" key={s.stage}>
            <div className="sb-top"><span>{s.stage_name}</span><span>{v}</span></div>
            <div className="sb-bar"><i className={cls} style={{ width: v + '%' }} /></div>
          </div>
        )
      })}
    </div>
  )
}
function RecoBadge({ reco }) {
  const map = { Pursue: 'r-pursue', Refine: 'r-refine', Reconsider: 'r-recon', Pass: 'r-pass' }
  return <div className={'reco ' + (map[reco] || 'r-recon')}>{reco}</div>
}
function Expander({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="exp">
      <button className="exp-h" onClick={() => setOpen(o => !o)}><span>{title}</span><span className="chev">{open ? '−' : '+'}</span></button>
      {open && <div className="exp-b">{children}</div>}
    </div>
  )
}
function collectStats(stages) {
  const cards = []
  for (const s of stages) {
    const e = s.estimates; if (!e) continue
    for (const [k, v] of Object.entries(e)) {
      if (k === 'assumptions') continue
      cards.push({ label: k, value: Array.isArray(v) ? v.join(', ') : String(v) })
    }
  }
  return { cards }
}
function prettyKey(k) {
  const up = ['tam', 'sam', 'som', 'cac', 'ltv']
  if (up.includes(k.toLowerCase())) return k.toUpperCase()
  return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

/* ---------------- settings + loader ---------------- */
function Settings({ provider, setProvider, grounding, setGrounding, apiKey, setApiKey, cost, onClose }) {
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head"><h3>Settings</h3><button className="x" onClick={onClose}>×</button></div>
        <div className="field">
          <label>AI provider</label>
          <select value={provider} onChange={e => setProvider(e.target.value)}>
            {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
          <p className="help">{cost}</p>
        </div>
        <div className="field">
          <label>Market data</label>
          <select value={grounding} onChange={e => setGrounding(e.target.value)}>
            <option value="reasoned">Reasoned estimate (fast)</option>
            <option value="live">Grounded with live web data</option>
          </select>
        </div>
        <div className="field">
          <label>Your own API key (optional)</label>
          <input type="password" placeholder="Leave blank to use the built-in key"
            value={apiKey} onChange={e => setApiKey(e.target.value)} />
          <p className="help">Used only for your requests, never stored.</p>
        </div>
        <button className="primary" onClick={onClose}>Done</button>
      </div>
    </div>
  )
}
function Loader() {
  const [i, setI] = useState(0)
  const ref = useRef()
  useEffect(() => {
    ref.current = setInterval(() => setI(v => (v + 1) % LOADER_LINES.length), 2200)
    return () => clearInterval(ref.current)
  }, [])
  return (
    <div className="loader">
      <div className="orbit"><span /><span /><span /></div>
      <div className="loader-text">{LOADER_LINES[i]}</div>
      <div className="loader-sub">Analysing across five business areas</div>
    </div>
  )
}
