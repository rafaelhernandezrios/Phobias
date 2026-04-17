import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const PHOBIA_JP: Record<string, string> = {
  arachnophobia: 'アラクノフォビア',
  claustrophobia: 'クラクストフォビア',
  acrophobia: 'アクロフォビア',
  ophidiophobia: 'オフィディオフォビア',
  entomophobia: 'エントモフォビア',
}

function clamp01(v: number): number {
  if (!Number.isFinite(v)) return 0
  return Math.max(0, Math.min(1, v))
}

function normalize(value: number, min: number, max: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(min) || !Number.isFinite(max) || min === max) return 0
  return clamp01((value - min) / (max - min))
}

function fmtMetric(v: unknown): string {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  if (Number.isFinite(n)) return n.toPrecision(4)
  return String(v)
}

const LEGACY_LOW = -0.3
const LEGACY_HIGH = 0.8
const STRESS_PCT = 15

/** Match scripts/eeg_adaptive.fear_stress_threshold (μ + pct·σ, not μ·(1+pct/100)) */
function stressThrFromCalibration(mu: number, sd: number): number {
  const sigma = Math.max(sd, 0.05)
  return mu + (STRESS_PCT / 100) * sigma
}

function moodFromFear(
  fear: number | null,
  stressThrFromServer?: number | null,
  refMean?: number | null,
  refStd?: number | null,
  adaptivePhase?: string | null,
  fearAggregate?: number | null,
): string {
  if (fear === null || !Number.isFinite(fear)) return '—'
  // Calibration: no ref yet — same legacy bands on instant index as before.
  if (adaptivePhase === 'calibration' || stressThrFromServer == null || !Number.isFinite(stressThrFromServer)) {
    if (fear <= LEGACY_LOW) return 'CALM / 落ち着き'
    if (fear >= LEGACY_HIGH) return 'STRESSED / ストレス高'
    return 'MEDIUM / 中間'
  }
  let thr = stressThrFromServer
  if (
    (thr == null || !Number.isFinite(thr)) &&
    refMean != null &&
    refStd != null &&
    Number.isFinite(refMean) &&
    Number.isFinite(refStd)
  ) {
    thr = stressThrFromCalibration(refMean, refStd)
  }
  if (thr != null && Number.isFinite(thr)) {
    const metric =
      fearAggregate != null && Number.isFinite(fearAggregate) ? fearAggregate : fear
    return metric >= thr ? 'STRESSED / ストレス高' : 'CALM / 落ち着き'
  }
  if (fear <= LEGACY_LOW) return 'CALM / 落ち着き'
  if (fear >= LEGACY_HIGH) return 'STRESSED / ストレス高'
  return 'MEDIUM / 中間'
}

type WsMsg = {
  type?: string
  fear_index?: number
  fear_index_aggregate?: number
  fear_ref_mean?: number
  fear_ref_std?: number
  fear_stress_threshold?: number
  adaptive_phase?: string
  level_suggestion?: string
  current_level?: number
  level?: number
  enabled?: boolean
  metrics?: {
    theta_fz?: number
    beta_alpha_fz_cz?: number
    alpha_posterior?: number
    faa?: number
  }
}

type Range = { min: number; max: number }

function metricFillStyle(fill: number | null): React.CSSProperties {
  const pct = fill == null ? 0 : Math.round(fill * 1000) / 10
  return { width: `${pct}%` }
}

function moodFillFromFear(
  fear: number | null,
  stressThrFromServer?: number | null,
  refMean?: number | null,
  refStd?: number | null,
  adaptivePhase?: string | null,
  fearAggregate?: number | null,
): number | null {
  if (fear == null || !Number.isFinite(fear)) return null
  if (adaptivePhase === 'calibration' || stressThrFromServer == null || !Number.isFinite(stressThrFromServer)) {
    return normalize(fear, LEGACY_LOW, LEGACY_HIGH)
  }
  let thr: number | null = stressThrFromServer
  if (
    (thr == null || !Number.isFinite(thr)) &&
    refMean != null &&
    refStd != null &&
    Number.isFinite(refMean) &&
    Number.isFinite(refStd)
  ) {
    thr = stressThrFromCalibration(refMean, refStd)
  }
  if (thr != null && Number.isFinite(thr)) {
    const metric =
      fearAggregate != null && Number.isFinite(fearAggregate) ? fearAggregate : fear
    return normalize(metric, thr - 0.5, thr + 0.5)
  }
  return normalize(fear, LEGACY_LOW, LEGACY_HIGH)
}

export default function App(): JSX.Element {
  const api = window.monitorAPI

  const [activeTab, setActiveTab] = useState<'metrics' | 'session'>('metrics')

  type SessionType = 'hybrid' | 'auto_sequence'
  const [sessionType, setSessionType] = useState<SessionType>('hybrid')

  const [conn, setConn] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const [wsUrl, setWsUrl] = useState<string>('')
  const [webAppUrl, setWebAppUrl] = useState('https://127.0.0.1:8443/')

  const [fearIndex, setFearIndex] = useState<string>('—')
  const [fearNum, setFearNum] = useState<number | null>(null)
  const [fearRefMean, setFearRefMean] = useState<number | null>(null)
  const [fearRefStd, setFearRefStd] = useState<number | null>(null)
  const [fearStressThr, setFearStressThr] = useState<number | null>(null)
  const [fearAggNum, setFearAggNum] = useState<number | null>(null)
  const [adaptPhase, setAdaptPhase] = useState<string | null>(null)

  const [levelSuggestion, setLevelSuggestion] = useState<string>('—')
  const [currentLevel, setCurrentLevel] = useState<string>('—')

  const [thetaFz, setThetaFz] = useState<string>('—')
  const [thetaNum, setThetaNum] = useState<number | null>(null)
  const [thetaRange, setThetaRange] = useState<Range | null>(null)

  const [betaAlpha, setBetaAlpha] = useState<string>('—')
  const [betaAlphaNum, setBetaAlphaNum] = useState<number | null>(null)
  const [betaAlphaRange, setBetaAlphaRange] = useState<Range | null>(null)

  const [alphaPost, setAlphaPost] = useState<string>('—')
  const [alphaPostNum, setAlphaPostNum] = useState<number | null>(null)
  const [alphaPostRange, setAlphaPostRange] = useState<Range | null>(null)

  const [faa, setFaa] = useState<string>('—')
  const [faaNum, setFaaNum] = useState<number | null>(null)

  const [mood, setMood] = useState<string>('—')

  const [phobias, setPhobias] = useState<{ id: string; name: string }[]>([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [startLevel, setStartLevel] = useState('0')
  const [experimentId, setExperimentId] = useState(() => `exp_${Math.floor(Date.now() / 1000)}`)
  const [durationSec, setDurationSec] = useState('120')
  const [baselineCalSec, setBaselineCalSec] = useState('45')
  const [autoAdapt, setAutoAdapt] = useState(true)

  const [logos, setLogos] = useState<{ atr: string | null; mirai: string | null }>({
    atr: null,
    mirai: null,
  })

  const [sendError, setSendError] = useState<string | null>(null)

  const prevConnRef = useRef(conn)
  const [dotAnimNonce, setDotAnimNonce] = useState(0)

  useEffect(() => {
    if (prevConnRef.current !== 'connected' && conn === 'connected') {
      setDotAnimNonce((x) => x + 1)
    }
    prevConnRef.current = conn
  }, [conn])

  useEffect(() => {
    void api.getConfig().then((c) => setWebAppUrl(c.webAppUrl))
  }, [api])

  useEffect(() => {
    void api.loadPhobias().then((res) => {
      if (res.phobias?.length) setPhobias(res.phobias)
    })
    void api.getLogos().then(setLogos)
  }, [api])

  useEffect(() => {
    const offMsg = api.onWsMessage((raw) => {
      const data = raw as WsMsg
      const t = data.type
      if (t === 'adaptive_state') {
        setConn('connected')
        if (data.fear_index !== undefined && data.fear_index !== null) {
          const fi = Number(data.fear_index)
          setFearNum(Number.isFinite(fi) ? fi : null)
          setFearIndex(Number.isFinite(fi) ? fi.toFixed(2) : '—')
          const mu =
            data.fear_ref_mean !== undefined && data.fear_ref_mean !== null
              ? Number(data.fear_ref_mean)
              : null
          const sd =
            data.fear_ref_std !== undefined && data.fear_ref_std !== null
              ? Number(data.fear_ref_std)
              : null
          const st =
            data.fear_stress_threshold !== undefined && data.fear_stress_threshold !== null
              ? Number(data.fear_stress_threshold)
              : null
          setFearRefMean(mu != null && Number.isFinite(mu) ? mu : null)
          setFearRefStd(sd != null && Number.isFinite(sd) ? sd : null)
          setFearStressThr(st != null && Number.isFinite(st) ? st : null)
          const aggRaw =
            data.fear_index_aggregate !== undefined && data.fear_index_aggregate !== null
              ? Number(data.fear_index_aggregate)
              : null
          setFearAggNum(aggRaw != null && Number.isFinite(aggRaw) ? aggRaw : null)
          setAdaptPhase(data.adaptive_phase != null ? String(data.adaptive_phase) : null)
          setMood(
            moodFromFear(
              Number.isFinite(fi) ? fi : null,
              st != null && Number.isFinite(st) ? st : null,
              mu != null && Number.isFinite(mu) ? mu : null,
              sd != null && Number.isFinite(sd) ? sd : null,
              data.adaptive_phase != null ? String(data.adaptive_phase) : null,
              aggRaw != null && Number.isFinite(aggRaw) ? aggRaw : null,
            ),
          )
        }

        setLevelSuggestion(String(data.level_suggestion ?? '—'))
        setCurrentLevel(String(data.current_level ?? '—'))

        const m = data.metrics ?? {}
        const thetaVal = m.theta_fz ?? null
        const baVal = m.beta_alpha_fz_cz ?? null
        const apVal = m.alpha_posterior ?? null
        const faaVal = m.faa ?? null

        setThetaFz(fmtMetric(thetaVal))
        setBetaAlpha(fmtMetric(baVal))
        setAlphaPost(fmtMetric(apVal))
        setFaa(fmtMetric(faaVal))

        if (thetaVal !== null && thetaVal !== undefined) {
          const x = Number(thetaVal)
          if (Number.isFinite(x)) {
            setThetaNum(x)
            setThetaRange((prev) => {
              if (!prev) return { min: x, max: x }
              return { min: Math.min(prev.min, x), max: Math.max(prev.max, x) }
            })
          } else setThetaNum(null)
        } else setThetaNum(null)

        if (baVal !== null && baVal !== undefined) {
          const x = Number(baVal)
          if (Number.isFinite(x)) {
            setBetaAlphaNum(x)
            setBetaAlphaRange((prev) => {
              if (!prev) return { min: x, max: x }
              return { min: Math.min(prev.min, x), max: Math.max(prev.max, x) }
            })
          } else setBetaAlphaNum(null)
        } else setBetaAlphaNum(null)

        if (apVal !== null && apVal !== undefined) {
          const x = Number(apVal)
          if (Number.isFinite(x)) {
            setAlphaPostNum(x)
            setAlphaPostRange((prev) => {
              if (!prev) return { min: x, max: x }
              return { min: Math.min(prev.min, x), max: Math.max(prev.max, x) }
            })
          } else setAlphaPostNum(null)
        } else setAlphaPostNum(null)

        if (faaVal !== null && faaVal !== undefined) {
          const x = Number(faaVal)
          setFaaNum(Number.isFinite(x) ? x : null)
        } else setFaaNum(null)
      } else if (t === 'force_level') {
        setCurrentLevel(String(data.level ?? '—'))
      } else if (t === 'stop_video') {
        setConn('connected')
      } else if (t === 'auto_adaptation_toggle') {
        setAutoAdapt(Boolean(data.enabled))
      }
    })

    const offStatus = api.onWsStatus((s) => {
      if (s.connected) {
        setConn('connected')
        if (s.url) setWsUrl(s.url)
      } else {
        setConn('disconnected')
        setWsUrl('')
      }
    })

    return () => {
      offMsg()
      offStatus()
    }
  }, [api])

  const selectedPhobia = phobias[selectedIdx] ?? phobias[0] ?? { id: 'arachnophobia', name: 'Arachnophobia' }

  const send = useCallback(
    async (payload: Record<string, unknown>) => {
      setSendError(null)
      const r = await api.sendWs(payload)
      if (!r.ok) setSendError(r.error ?? 'Send failed')
    },
    [api],
  )

  const onStart = useCallback(() => {
    let lvl = parseInt(startLevel, 10)
    if (sessionType === 'auto_sequence') lvl = 0
    if (Number.isNaN(lvl) || lvl < 0 || lvl > 5) lvl = 0
    let dur = parseFloat(durationSec)
    if (Number.isNaN(dur)) dur = 0
    let bcal = parseFloat(baselineCalSec)
    if (Number.isNaN(bcal)) bcal = 0
    bcal = Math.max(0, bcal)

    const eid = experimentId.trim() || `exp_${Math.floor(Date.now() / 1000)}`
    void send({
      type: 'controller_start',
      phobia_id: selectedPhobia.id,
      phobia_name: selectedPhobia.name,
      level: lvl,
      experiment_id: eid,
      duration_seconds: dur,
      session_type: sessionType,
      baseline_calibration_seconds: bcal,
    })

    // Keep metrics as default active view during an experiment.
    setActiveTab('metrics')
  }, [baselineCalSec, durationSec, experimentId, selectedPhobia.id, selectedPhobia.name, send, sessionType, startLevel])

  const onStop = useCallback(() => void send({ type: 'stop' }), [send])

  const toggleAdapt = useCallback(() => {
    const next = !autoAdapt
    setAutoAdapt(next)
    void send({ type: 'set_auto_adaptation', enabled: next })
  }, [autoAdapt, send])

  const manualLevel = useCallback(
    async (level: number) => {
      setSendError(null)
      const r = await api.sendWs({ type: 'manual_level', level })
      if (!r.ok) setSendError(r.error ?? 'Send failed')
      else setCurrentLevel(String(level))
    },
    [api],
  )

  const durationHint = useMemo(() => {
    const d = parseFloat(durationSec)
    if (!Number.isFinite(d) || d <= 0) return ''
    const mins = d / 60
    const minsPretty = mins < 10 ? mins.toFixed(1).replace(/\.0$/, '') : mins.toFixed(0)
    return `${Math.round(d)} seconds = ${minsPretty} min`
  }, [durationSec])

  const fearFill = useMemo(() => {
    if (fearNum == null) return null
    return clamp01((fearNum + 3) / 6)
  }, [fearNum])

  const moodFill = useMemo(
    () =>
      moodFillFromFear(fearNum, fearStressThr, fearRefMean, fearRefStd, adaptPhase, fearAggNum),
    [adaptPhase, fearAggNum, fearNum, fearRefMean, fearRefStd, fearStressThr],
  )

  const thetaFill = useMemo(() => {
    if (thetaNum == null || !thetaRange) return null
    return normalize(thetaNum, thetaRange.min, thetaRange.max)
  }, [thetaNum, thetaRange])

  const baFill = useMemo(() => {
    if (betaAlphaNum == null || !betaAlphaRange) return null
    return normalize(betaAlphaNum, betaAlphaRange.min, betaAlphaRange.max)
  }, [betaAlphaNum, betaAlphaRange])

  const apFill = useMemo(() => {
    if (alphaPostNum == null || !alphaPostRange) return null
    return normalize(alphaPostNum, alphaPostRange.min, alphaPostRange.max)
  }, [alphaPostNum, alphaPostRange])

  const faaFill = useMemo(() => {
    if (faaNum == null) return null
    return clamp01((faaNum + 1) / 2)
  }, [faaNum])

  const connText = useMemo(() => {
    if (conn === 'connected') return 'Connected / 接続済'
    if (conn === 'connecting') return 'Connecting… / 接続中…'
    return 'Disconnected / 未接続'
  }, [conn])

  const copyExperimentId = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(experimentId)
    } catch {
      // Fallback: best-effort clipboard copy using a temporary textarea.
      try {
        const ta = document.createElement('textarea')
        ta.value = experimentId
        ta.setAttribute('readonly', 'true')
        ta.style.position = 'absolute'
        ta.style.left = '-9999px'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      } catch {
        // If clipboard copy is not available, we just silently fail.
      }
    }
  }, [api, experimentId])

  const startLevelOptions = useMemo(() => {
    const map: Record<string, string> = {
      '0': '0 — Baseline / 0：ベースライン',
      '1': '1 — Low exposure / 1：低刺激',
      '2': '2 — Medium exposure / 2：中刺激',
      '3': '3 — High exposure / 3：高刺激',
      '4': '4 — Very high exposure / 4：非常に高刺激',
      '5': '5 — Maximum exposure / 5：最大刺激',
    }
    return ['0', '1', '2', '3', '4', '5'].map((v) => ({ value: v, label: map[v] ?? v }))
  }, [])

  const onCopy = useCallback(() => {
    void copyExperimentId()
  }, [copyExperimentId])

  return (
    <div className="app">
      <header className="header">
        <div className="logo-slot">
          {logos.atr ? <img className="logo-img logo-img-atr" src={logos.atr} alt="ATR" /> : <div />}
        </div>
        <div className="logo-slot">
          {logos.mirai ? <img className="logo-img logo-img-mirai" src={logos.mirai} alt="Mirai" /> : <div />}
        </div>
      </header>

      <div className="title-block">
        <h1>Adaptive state (EEG) / EEG適応状態</h1>
        <p className="sub">Research monitor — WebSocket to aura_recorder</p>
      </div>

      <div className="status-row">
        <div className="status-pill" role="status" aria-live="polite">
          <span
            key={dotAnimNonce}
            className={`status-dot ${conn === 'connected' ? 'status-dot-connected' : conn === 'connecting' ? 'status-dot-connecting' : 'status-dot-disconnected'} ${
              conn === 'connected' ? 'status-dot-anim' : ''
            }`}
          />
          <span className="status-text">{connText}</span>
        </div>
        {wsUrl ? <span className="pill pill-muted" style={{ fontWeight: 400 }}>{wsUrl}</span> : null}
        <button type="button" className="link-web" onClick={() => void api.openUrl(webAppUrl)}>
          Open web (browser / VR) / ウェブを開く
        </button>
      </div>

      <div className="tabs">
        <button type="button" className={`tab-btn ${activeTab === 'metrics' ? 'active' : ''}`} onClick={() => setActiveTab('metrics')}>
          Metrics / 指標
        </button>
        <button type="button" className={`tab-btn ${activeTab === 'session' ? 'active' : ''}`} onClick={() => setActiveTab('session')}>
          Session / セッション
        </button>
      </div>

      {activeTab === 'metrics' ? (
        <>
          <div className="section-title">Metrics / 指標</div>
          <div className="card-grid">
            <div className="card">
              <div className="card-label">Fear / Engagement / 恐怖・関与</div>
              <div className="card-value">{fearIndex}</div>
              <div className="metric-bar">
                <div className="metric-bar-fill fill-fear" style={metricFillStyle(fearFill)} />
              </div>
              <div className="metric-range-labels">low / high</div>
            </div>

            <div className="card">
              <div className="card-label">Mood (EEG) / EEGストレス</div>
              <div className="card-value sm mood">{mood}</div>
              <div className="metric-bar">
                <div className="metric-bar-fill fill-mood" style={metricFillStyle(moodFill)} />
              </div>
              <div className="metric-range-labels">calm / stressed</div>
            </div>

            <div className="card">
              <div className="card-label">Θ FZ / ΘFZ</div>
              <div className="card-subtitle">Frontal theta power / 前頭部シータパワー</div>
              <div className="card-value sm">{thetaFz}</div>
              <div className="metric-bar">
                <div className="metric-bar-fill fill-theta" style={metricFillStyle(thetaFill)} />
              </div>
              <div className="metric-range-labels">relaxed / alert</div>
            </div>

            <div className="card">
              <div className="card-label">β/α FZ,CZ</div>
              <div className="card-subtitle">Beta/Alpha ratio / ベータ・アルファ比</div>
              <div className="card-value sm">{betaAlpha}</div>
              <div className="metric-bar">
                <div className="metric-bar-fill fill-ba" style={metricFillStyle(baFill)} />
              </div>
              <div className="metric-range-labels">–1 / +1</div>
            </div>

            <div className="card">
              <div className="card-label">α posterior / A後部</div>
              <div className="card-subtitle">Alpha posterior sites / 後頭部アルファサイト</div>
              <div className="card-value sm">{alphaPost}</div>
              <div className="metric-bar">
                <div className="metric-bar-fill fill-ap" style={metricFillStyle(apFill)} />
              </div>
              <div className="metric-range-labels">low / high</div>
            </div>

            <div className="card">
              <div className="card-label">FAA (F3–F4)</div>
              <div className="card-subtitle">Frontal alpha asymmetry / 前頭部アルファ非対称性</div>
              <div className="card-value sm">{faa}</div>
              <div className="metric-bar">
                <div className="metric-bar-fill fill-faa" style={metricFillStyle(faaFill)} />
              </div>
              <div className="metric-range-labels">–1 / +1</div>
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="section-title">Session / セッション</div>

          <div className="card-grid">
            <div className="card">
              <div className="card-label">Level suggestion / レベル提案</div>
              <div className="card-value sm">{levelSuggestion}</div>
            </div>
            <div className="card">
              <div className="card-label">Current level / 現在のレベル</div>
              <div className="card-value">{currentLevel}</div>
            </div>
          </div>

          <div className="sep" />

          <div className="form-row">
            <label htmlFor="exp">Experiment / 実験</label>
            <select id="exp" value={selectedIdx} onChange={(e) => setSelectedIdx(Number(e.target.value))}>
              {phobias.map((p, i) => {
                const jp = PHOBIA_JP[p.id] ?? p.id
                return (
                  <option key={p.id} value={i}>
                    {p.id} — {p.name} / {jp}
                  </option>
                )
              })}
            </select>
          </div>

          <div className="form-row">
            <label htmlFor="sessionType">Session mode / セッションモード</label>
            <select id="sessionType" value={sessionType} onChange={(e) => setSessionType(e.target.value as SessionType)}>
              <option value="hybrid">Hybrid (EEG adaptive) / ハイブリッド（EEG適応）</option>
              <option value="auto_sequence">Auto sequence 0→5 / 自動シーケンス（0→5）</option>
            </select>
          </div>

          {sessionType !== 'auto_sequence' ? (
            <div className="form-row">
              <label htmlFor="lvl">Start level / 開始レベル (0–5)</label>
              <select id="lvl" value={startLevel} onChange={(e) => setStartLevel(e.target.value)}>
                {startLevelOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div className="form-row">
            <label htmlFor="eid">Experiment ID / 実験ID</label>
            <div className="id-row">
              <input id="eid" value={experimentId} onChange={(e) => setExperimentId(e.target.value)} />
              <button type="button" className="btn btn-secondary btn-copy" onClick={onCopy}>
                Copy / コピー
              </button>
            </div>
          </div>

          <div className="form-row">
            <label htmlFor="dur">Duration (sec) / 総時間（秒）</label>
            <div className="duration-input-row">
              <input id="dur" value={durationSec} onChange={(e) => setDurationSec(e.target.value)} />
              {durationHint ? <span className="duration-hint">{durationHint}</span> : null}
            </div>
          </div>

          {sessionType !== 'auto_sequence' ? (
            <div className="form-row">
              <label htmlFor="bcal">Baseline cal (sec) / 校正（秒）</label>
              <input
                id="bcal"
                value={baselineCalSec}
                onChange={(e) => setBaselineCalSec(e.target.value)}
                placeholder="45"
              />
              <p className="hint" style={{ marginTop: 6 }}>
                0 = 8-sample legacy ref. &gt;0: timed calibration at level 0, then auto level 1 + adaptation.
              </p>
            </div>
          ) : null}

          <div className="btn-row btn-row-2">
            <button type="button" className="btn btn-primary btn-half" onClick={onStart}>
              Start / 実験開始
            </button>
            <button type="button" className="btn btn-danger btn-half" onClick={onStop}>
              Stop / 実験停止
            </button>
          </div>

          <div className="thin-sep" />

          {sessionType !== 'auto_sequence' ? (
            <button type="button" className="btn btn-secondary btn-full" onClick={toggleAdapt}>
              Adaptive mood: {autoAdapt ? 'ON' : 'OFF'} / 適応モード：{autoAdapt ? 'ON' : 'OFF'}
            </button>
          ) : null}

          {sendError ? <div className="err-toast">{sendError}</div> : null}

          <div className="sep" />

          <div className="section-title">Manual level → VR / 手動レベル</div>
          <div className="level-grid">
            {[0, 1, 2, 3, 4, 5].map((level) => (
              <button
                key={level}
                type="button"
                className="btn btn-secondary btn-level"
                disabled={sessionType === 'auto_sequence'}
                onClick={() => void manualLevel(level)}
              >
                {level === 0 ? 'Baseline\nベースライン' : `Level ${level}\nレベル${level}`}
              </button>
            ))}
          </div>
          <p className="hint">(Changes scene in browser / VR) / ブラウザ・VRのシーンが変わります</p>
        </>
      )}
    </div>
  )
}
