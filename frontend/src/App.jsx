import React, {useState, useEffect, useCallback, useRef} from 'react';
import {ShieldCheck, LayoutDashboard, Video, Search, ClipboardCheck, Map, GitBranch, Upload, Download, ArrowRight, AlertTriangle, CheckCircle2, RefreshCw, Activity} from 'lucide-react';
import {request, postJSON} from './services/api';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './styles/workflow.css';

const tabs = [
  ['dashboard', 'Overview', LayoutDashboard], ['live', 'Live Monitor', Activity], ['studio', 'Video studio', Video],
  ['events', 'Incident explorer', Search], ['review', 'Human review', ClipboardCheck],
  ['heatmap', 'Risk map', Map], ['replay', 'What-if replay', GitBranch]
];
const number = (value, suffix = '', digits = 2) => value == null || !Number.isFinite(value) ? 'Not available' : value.toFixed(digits) + suffix;
const words = value => (value || '').replaceAll('_', ' ');
const decision = event => event.human_review?.decision || 'pending';
function Badge({children, tone = ''}) { return <span className={'ng-badge ' + tone}>{children}</span>; }
function Empty({children}) {return <div className="ng-empty">{children}</div>;}
function Stat({label, value, note}) {return <div className="ng-card ng-stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;}

export default function App() {
  const [tab, setTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [jobId, setJobId] = useState(() => localStorage.getItem('nearguard_job') || '');
  const [eventRows, setEvents] = useState([]);
  const activeJobRef = useRef(jobId);
  activeJobRef.current = jobId;
  const events = eventRows.filter(event => event.job_id === jobId);
  const [selectedId, setSelectedId] = useState('');
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const job = jobs.find(j => j.id === jobId);
  const selected = events.find(e => e.id === selectedId);
  const pending = events.filter(e => decision(e) === 'pending');
  const accepted = events.filter(e => decision(e) === 'approved');
  const included = events.filter(e => decision(e) !== 'rejected');
  const refreshJobs = useCallback(async () => {
    const results = await request('/jobs');
    setJobs(results);
    setJobId(previous => results.some(j => j.id === previous) ? previous : results[0]?.id || '');
  }, []);
  const refreshEvents = useCallback(async () => {
    if (!jobId || job?.status !== 'completed') {setEvents([]); return;}
    const rows = await request('/events?job_id=' + encodeURIComponent(jobId));
    if (activeJobRef.current === jobId) setEvents(rows);
  }, [jobId, job?.status]);
  useEffect(() => {
    let live = true;
    const update = async () => {
      try {await refreshJobs(); const status = await request('/health'); if (live) setHealth(status);}
      catch(e) {if (live) {setHealth(null); setError('Backend unavailable: ' + e.message);}}
      finally {if (live) setLoading(false);}
    };
    update();
    const timer = setInterval(update, 3000);
    return () => {live = false; clearInterval(timer);};
  }, [refreshJobs]);
  useEffect(() => {
    localStorage.setItem('nearguard_job', jobId);
    setSelectedId('');
    setEvents([]);
  }, [jobId]);
  useEffect(() => {refreshEvents().catch(e => setError(e.message));}, [refreshEvents]);
  function openEvent(event, target = 'events') {setSelectedId(event.id); setTab(target);}
  async function onSubmitted(newJob) {
    setJobs(previous => [newJob, ...previous.filter(j => j.id !== newJob.id)]);
    setJobId(newJob.id);
    setError('');
    await refreshJobs();
  }
  const choose = event => setSelectedId(event.id);
  return <div className="ng-shell">
    <aside className="ng-sidebar">
      <div className="ng-brand"><ShieldCheck size={34}/><div>NearGuard<span>BITHAWK / SENSORA</span></div></div>
      <div className="ng-sidebar-caption">ROAD SAFETY WORKSPACE</div>
      <nav aria-label="Main navigation">{tabs.map(([id, label, Icon]) =>
        <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>
          <Icon size={18}/>{label}{id === 'review' && pending.length > 0 && <span className="ng-count">{pending.length}</span>}
        </button>)}</nav>
      <div className="ng-sidebar-bottom"><Badge tone={health ? 'approved' : 'rejected'}>{health ? 'Backend connected' : 'Connecting to backend'}</Badge>
        <p>Local prototype · v2.0.1<br/>Candidate screening + human review</p></div>
    </aside>
    <main className="ng-main">
      <header className="ng-header"><div><div className="ng-eyebrow">BITHAWK · NEAR-MISS ANALYSIS</div>
        <h1>{tabs.find(t => t[0] === tab)[1]}</h1></div>
        <label className="ng-job-select">Selected analysis<select aria-label="Selected analysis" value={jobId} onChange={e => {setJobId(e.target.value); setError('');}}>
          {!jobs.length && <option value="">No analysis yet</option>}
          {jobs.map(j => <option key={j.id} value={j.id}>{j.video_name} · {j.status} · {j.id.slice(-6)}</option>)}
        </select></label>
      </header>
      {error && <div className="ng-alert" role="alert"><AlertTriangle size={18}/><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
      {loading && <p role="status">Connecting to the local backend…</p>}
      {job && <div className="ng-source"><Badge tone={job.metadata.source_type === 'synthetic_demo' ? 'pending' : ''}>{job.metadata.source_type === 'synthetic_demo' ? 'Synthetic demo' : 'Uploaded footage'}</Badge>
        <Badge>{job.metadata.detector_mode === 'yolo' ? 'YOLO detector' : 'Motion baseline · unknown classes'}</Badge>
        <Badge>{job.metadata.camera_config ? 'Calibrated area' : 'Tracking only · no metric calibration'}</Badge>
        {job.metadata.resized && <Badge>Auto resized: {job.metadata.source_resolution.width} × {job.metadata.source_resolution.height} → {job.metadata.resolution.width} × {job.metadata.resolution.height}</Badge>}
        <span>{job.video_name}</span></div>}
      {job && ['queued', 'processing', 'failed'].includes(job.status) && <section className="ng-card ng-progress" aria-live="polite">
        <div className="ng-row"><strong>{words(job.status)}</strong><span>{Math.round(job.progress)}%</span></div>
        <progress max="100" value={job.progress}/><p>{job.status_message}</p>
      </section>}

      {tab === 'studio' && <Studio health={health} onSubmitted={onSubmitted} onError={setError}/>}
      {tab === 'dashboard' && <>
        <section className="ng-hero ng-card"><div><div className="ng-eyebrow">FROM VIDEO TO REVIEWABLE EVIDENCE</div>
          <h2>Find the moments<br/>worth a closer look.</h2>
          <p>Track movement, inspect possible conflicts and keep a record of human decisions.</p>
          <button className="ng-primary" onClick={() => setTab('studio')}>Analyze a video <ArrowRight size={17}/></button>
        </div><div className="ng-hero-mark"><ShieldCheck size={110}/><span>OBSERVE · CHECK · REVIEW</span></div></section>
        <div className="ng-stats"><Stat label="Candidate events" value={events.length} note="From the selected video"/>
          <Stat label="Confirmed by reviewer" value={accepted.length} note="Evidence checked by a person"/>
          <Stat label="Awaiting review" value={pending.length} note="Automatic results are provisional"/>
          <Stat label="Tracked objects" value={job?.metadata.track_count ?? '—'} note="Total road users"/>
          <Stat label="Near-Miss Rate" value={job?.metadata.track_count ? (events.length / job.metadata.track_count * 1000).toFixed(1) : '—'} note="Events per 1000 objects"/></div>
        <div className="ng-columns">
          <section className="ng-card"><h2>Analysis summary</h2>{!job ? <Empty>Choose Video studio to run your first analysis.</Empty> :
            <><p>{job.status_message}</p><dl className="ng-facts"><dt>Video duration</dt><dd>{number(job.metadata.duration_seconds, ' s', 1)}</dd>
              <dt>Processed frames</dt><dd>{job.metadata.frame_count ?? '—'}</dd>
              {job.metadata.video_health && <><dt>Video Health</dt><dd>Visibility: {job.metadata.video_health.visibility}%, Sharpness: {job.metadata.video_health.sharpness}%</dd></>}
              <dt>Source</dt><dd>{job.metadata.source_type === 'synthetic_demo' ? 'Generated scene; illustrative scale' : 'Uploaded file'}</dd></dl>
              {job.annotated_url && <a className="ng-link" href={job.annotated_url} download>Download annotated video <Download size={15}/></a>}
              {job.tracks_url && <a className="ng-link" href={job.tracks_url} download>Download measured tracks <Download size={15}/></a>}
            </>}</section>
          <section className="ng-card"><h2>Candidate severity</h2><p>A ranking aid, not a probability of a crash. Rejected candidates are excluded.</p>
            {['critical', 'high', 'medium', 'low'].map(level => {const count = included.filter(e => e.risk_level === level).length;
              return <div className="ng-bar-row" key={level}><span>{level}</span><div><i className={level} style={{width: (included.length ? count/included.length*100 : 0)+'%'}}/></div><b>{count}</b></div>;})}
          </section></div>
        {job?.metadata.warnings?.length > 0 && <section className="ng-card ng-note"><h3>Read the results with these limits</h3>
          {job.metadata.warnings.map(w => <p key={w}>{w}</p>)}</section>}
      </>}

      {(tab === 'events' || tab === 'review') && <div className="ng-explorer">
        <EventList events={tab === 'review' ? pending : events} selectedId={selectedId} onSelect={choose} reviewOnly={tab === 'review'} jobId={jobId}/>
        <EventDetail key={selected?.id || 'empty'} event={selected} onReplay={() => setTab('replay')}
          onSaved={async () => {await refreshEvents();}} onError={setError}/>
      </div>}
      {tab === 'heatmap' && <RiskMap job={job} events={included} onSelect={event => openEvent(event)}/>}
      {tab === 'replay' && <Replay key={selected?.id || 'none'} event={selected} events={events} onSelect={choose} onError={setError}/>}
      {tab === 'live' && <LiveMonitor />}
      <footer className="ng-footer">NearGuard supports review. Video quality, camera geometry and tracking errors affect every estimate.</footer>
    </main>
  </div>;
}

function Studio({health, onSubmitted, onError}) {
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  const [frame, setFrame] = useState(null);
  const [points, setPoints] = useState([]);
  const [width, setWidth] = useState('');
  const [length, setLength] = useState('');
  const [calibrate, setCalibrate] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [mode, setMode] = useState('motion');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const video = useRef(null);
  useEffect(() => {
    setFrame(null); setPoints([]); setConfirmed(false); setNotice('');
    if (!file) {setUrl(''); return;}
    const value = URL.createObjectURL(file); setUrl(value);
    return () => URL.revokeObjectURL(value);
  }, [file]);
  function captureFrame() {
    const source = video.current;
    if (!source?.videoWidth) return;
    source.pause();
    const canvas = document.createElement('canvas');
    canvas.width = source.videoWidth; canvas.height = source.videoHeight;
    canvas.getContext('2d').drawImage(source, 0, 0);
    setFrame({url: canvas.toDataURL('image/jpeg'), width: canvas.width, height: canvas.height});
    setPoints([]); setConfirmed(false);
  }
  function addPoint(event) {
    if (!frame || points.length >= 4) return;
    const box = event.currentTarget.getBoundingClientRect();
    setPoints([...points, [(event.clientX-box.left)/box.width*frame.width, (event.clientY-box.top)/box.height*frame.height]]);
    setConfirmed(false);
  }
  async function submit(useDemo, scenario = 'demo_video.mp4') {
    setBusy(true); onError(''); setNotice('');
    try {
      if (!useDemo && !file) throw new Error('Choose a video first.');
      const form = new FormData();
      form.append('use_demo', String(useDemo)); form.append('scenario', scenario);
      form.append('detector_mode', useDemo ? 'motion' : mode);
      if (!useDemo) {
        form.append('file', file);
        if (calibrate) {
          if (!frame || points.length !== 4 || !confirmed || Number(width) <= 0 || Number(length) <= 0)
            throw new Error('Select four corners, enter measured lengths and confirm the calibration.');
          form.append('calibration_json', JSON.stringify({resolution: {width: frame.width, height: frame.height}, calibration: {
            source_pixel_points: points, dest_ground_points: [[0,0], [Number(width),0], [Number(width),Number(length)], [0,Number(length)]]
          }}));
        }
      }
      const job = await request('/upload', {method: 'POST', body: form});
      await onSubmitted(job);
      setNotice('Analysis queued. Progress appears above; results will be available in Overview and Incident explorer.');
    } catch(e) {onError(e.message);} finally {setBusy(false);}
  }
  return <>
    <div className="ng-columns"><section className="ng-card"><div className="ng-section-title"><Upload size={20}/><h2>1. Choose your footage</h2></div>
      <p>Use a short, fixed-camera clip. Up to 150 MB and two minutes. 4K uploads are supported (up to 4096 pixels per side) and automatically resized for analysis.</p>
      <label className="ng-upload"><Upload size={30}/><strong>{file?.name || 'Choose a traffic video'}</strong><span>MP4 · MOV · AVI · WebM · MKV</span>
        <input aria-label="Choose traffic video" type="file" accept=".mp4,.mov,.avi,.webm,.mkv" disabled={busy} onChange={e => setFile(e.target.files[0] || null)}/></label>
      {url && <><video ref={video} src={url} controls preload="metadata" onLoadedData={captureFrame} onError={() => setNotice('Browser preview cannot decode this format. Try an H.264 MP4 for calibration, or use tracking-only mode.')}/>
        <button className="ng-secondary" onClick={captureFrame}>Use current frame for calibration</button></>}
      {frame && Math.max(frame.width, frame.height) > 1920 && Math.max(frame.width, frame.height) <= 4096 &&
        <p className="ng-notice">Your video is {frame.width} × {frame.height}. It will be resized automatically, without cropping, to a maximum side of 1920 pixels. Select calibration corners on this original preview as usual.</p>}
      <label className="ng-field">Detector<select aria-label="Detector" value={mode} onChange={e => setMode(e.target.value)}>
        <option value="motion">Motion baseline (runs without model weights)</option>
        <option value="yolo" disabled={!health?.yolo_available}>YOLO trained detector {health?.yolo_available ? '' : '— setup required'}</option>
      </select></label>
      <p className="ng-small">The motion baseline detects moving regions. It does not recognize cars or people. YOLO setup is described in README.</p>
    </section>
    <section className="ng-card"><div className="ng-section-title"><CheckCircle2 size={20}/><h2>2. Set the measurement area</h2></div>
      <label className="ng-check"><input type="checkbox" checked={calibrate} onChange={e => setCalibrate(e.target.checked)}/>Enable ground measurements</label>
      {!calibrate ? <p>Tracking-only mode creates an annotated video and track logs. It will not invent distances, speeds or near-miss scores.</p> : <>
        <p>Select four corners around a measured rectangle on the road, in order. Only objects inside this area receive metric estimates.</p>
        {frame ? <svg className="ng-calibration" viewBox={'0 0 '+frame.width+' '+frame.height} onClick={addPoint} aria-label="Calibration frame: select four road corners">
          <image href={frame.url} width={frame.width} height={frame.height}/>
          {points.length > 1 && <polygon points={points.map(p=>p.join(',')).join(' ')} fill="#00d9e522" stroke="#00e4ed" strokeWidth="3"/>}
          {points.map((p,i) => <g key={i}><circle cx={p[0]} cy={p[1]} r="10" fill="#00e4ed"/><text x={p[0]+14} y={p[1]-10} fill="white" fontSize="24">{i+1}</text></g>)}
        </svg> : <Empty>Choose a playable video to select its road corners.</Empty>}
        <div className="ng-row"><small>{points.length}/4 corners selected</small><button className="ng-text-button" onClick={() => {setPoints([]); setConfirmed(false);}}>Reset corners</button></div>
        <div className="ng-two-fields"><label className="ng-field">Edge 1 → 2 (metres)<input aria-label="Edge 1 to 2 metres" type="number" min=".1" max="1000" step=".1" value={width} onChange={e => {setWidth(e.target.value);setConfirmed(false);}}/></label>
          <label className="ng-field">Edge 2 → 3 (metres)<input aria-label="Edge 2 to 3 metres" type="number" min=".1" max="1000" step=".1" value={length} onChange={e => {setLength(e.target.value);setConfirmed(false);}}/></label></div>
        <label className="ng-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>These are measured dimensions on the same flat road surface, and the camera stays fixed.</label>
      </>}
      <button className="ng-primary ng-wide" disabled={busy || !file} onClick={() => submit(false)}>{busy ? 'Uploading…' : calibrate ? 'Analyze calibrated footage' : 'Run tracking only'}<ArrowRight size={17}/></button>
      {notice && <p role="status" className="ng-notice">{notice}</p>}
    </section></div>
    <section className="ng-card ng-demo"><div><Badge tone="pending">Synthetic demonstration</Badge><h2>Try the complete workflow</h2><p>Generated scenes with an illustrative 0.05 m/pixel scale. Candidates are computed from the video; the count may be zero.</p></div>
      <div className="ng-actions"><button className="ng-secondary" disabled={busy} onClick={() => submit(true)}>Run intersection demo</button>
        <button className="ng-secondary" disabled={busy} onClick={() => submit(true, 'pedestrian_school_zone.mp4')}>Run crossing demo</button></div>
    </section>
  </>;
}

function EventList({events, selectedId, onSelect, reviewOnly, jobId}) {
  const [risk, setRisk] = useState('');
  const [review, setReview] = useState('');
  const filtered = events.filter(e => (!risk || e.risk_level === risk) && (!review || decision(e) === review));
  return <section className="ng-card"><div className="ng-row"><h2>{reviewOnly ? 'Awaiting a decision' : 'Detected candidates'}</h2><Badge>{filtered.length}</Badge></div>
    <div className="ng-filters"><select aria-label="Severity filter" value={risk} onChange={e => setRisk(e.target.value)}><option value="">All severity levels</option>{['critical','high','medium','low'].map(r=><option key={r}>{r}</option>)}</select>
      {!reviewOnly && <select aria-label="Review filter" value={review} onChange={e => setReview(e.target.value)}><option value="">All review decisions</option>{['pending','approved','rejected'].map(r=><option key={r}>{r}</option>)}</select>}</div>
    {!filtered.length && <Empty>{reviewOnly ? 'No pending candidates for this analysis.' : 'No candidates to show. A completed analysis with zero events is a valid result.'}</Empty>}
    <div className="ng-event-list">{filtered.map(event => <button key={event.id} className={'ng-event '+(selectedId === event.id ? 'selected' : '')} onClick={() => onSelect(event)}>
      <div className="ng-row"><strong>{words(event.conflict_type)}</strong><Badge tone={event.risk_level}>{event.risk_level}</Badge></div>
      <p>{number(event.timestamp_peak, ' s')} · Objects {event.participant_ids.join(' & ')}</p>
      <div className="ng-row"><small>Priority score {event.risk_score}/100</small><Badge tone={decision(event)}>{decision(event)}</Badge></div>
    </button>)}</div>
    {jobId && <a className="ng-link" href={'/api/events/export.csv?job_id='+encodeURIComponent(jobId)} download>Export this analysis as CSV <Download size={15}/></a>}
  </section>;
}

function EventDetail({event, onReplay, onSaved, onError}) {
  const [notes, setNotes] = useState(event?.human_review?.notes || '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  if (!event) return <section className="ng-card"><Empty>Select a candidate to inspect its evidence and record a decision.</Empty></section>;
  const measures = event.surrogate_measures;
  async function save(value) {
    setBusy(true); onError(''); setMessage('');
    try {
      await postJSON('/review/'+event.id, {decision: value, notes, reviewer_id: 'BITHAWK reviewer'});
      await onSaved(); setMessage('Review saved. The measurement uncertainty remains visible.');
    } catch(e) {onError(e.message);} finally {setBusy(false);}
  }
  return <section className="ng-card ng-detail">
    <div className="ng-row"><h2>Evidence & review</h2><Badge tone={decision(event)}>{decision(event)}</Badge></div>
    <p>{event.id}</p>
    {event.evidence_clip_path ? <video key={event.evidence_clip_path} src={event.evidence_clip_path} controls preload="metadata"/> : <Empty>No evidence clip is available for this event.</Empty>}
    <p>Peak at {number(event.timestamp_peak, ' s')} in the source video. The clip includes context around the candidate.</p>
    <div className="ng-metrics"><Stat label="Estimated TTC" value={number(measures.min_ttc, ' s')} note="Time to circular-footprint overlap if velocity stays constant"/>
      <Stat label="Closest center distance" value={number(measures.min_distance_m, ' m')} note="Between tracked ground-contact points"/>
      <Stat label="Relative speed" value={number(measures.delta_v, ' km/h', 1)} note="Difference of two velocity vectors"/>
      <Stat label="Estimated DRAC" value={number(measures.max_drac, ' m/s²')} note="Same-heading closing conflicts only"/>
      <Stat label="Evidence Confidence" value={(event.quality_check.tracking_confidence * 100).toFixed(0) + '%'} note="Track reliability and temporal consensus"/>
    </div>
    {event.quality_check.tracking_confidence < 0.6 && <div className="ng-alert" role="alert"><AlertTriangle size={18}/><span><strong>Reliability Gate:</strong> Low evidence confidence. Human verification strongly required.</span></div>}
    <p className="ng-small">PET: not computed. TTC and distances are estimates, not observed crash outcomes.</p>
    <details><summary>Measurement limitations</summary>{event.quality_check.uncertainty_reasons.map(reason=><p key={reason}>{reason}</p>)}</details>
    <h3>Your decision</h3><label className="ng-field">Review notes<textarea aria-label="Review notes" rows="3" value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Check object IDs, paths and whether this is a real conflict."/></label>
    <div className="ng-actions"><button className="ng-primary" disabled={busy} onClick={()=>save('approved')}>Confirm candidate</button>
      <button className="ng-secondary" disabled={busy} onClick={()=>save('rejected')}>Reject candidate</button>
      <button className="ng-secondary" onClick={onReplay}>Explore what-if <GitBranch size={16}/></button></div>
    {message && <p className="ng-notice" role="status">{message}</p>}
    <details><summary>Suggested next step</summary><p>{event.recommendation.engineering_action}</p><p>{event.recommendation.policy_action}</p></details>
  </section>;
}

function RiskMap({job, events, onSelect}) {
  const [confirmedOnly, setConfirmedOnly] = useState(false);
  const points = events.filter(e=>!confirmedOnly || decision(e) === 'approved');
  
  // Dummy anchor for the prototype (Times Square, NY)
  const ANCHOR_LAT = 40.7580;
  const ANCHOR_LNG = -73.9855;
  const getLatLng = (ground_coords) => {
    // Very rough approximation: 111km per latitude degree, 84km per longitude degree at this latitude
    const lat = ANCHOR_LAT + (ground_coords[1] / 111111);
    const lng = ANCHOR_LNG + (ground_coords[0] / 84100);
    return [lat, lng];
  };

  return <section className="ng-card"><div className="ng-row"><div><h2>Geographic Risk Heat Map</h2><p>Interactive Map API showing near-miss hotspots. Larger markers indicate higher severity.</p></div>
    <label className="ng-check"><input type="checkbox" checked={confirmedOnly} onChange={e=>setConfirmedOnly(e.target.checked)}/>Confirmed only</label></div>
    <div style={{ height: "500px", width: "100%", borderRadius: "8px", overflow: "hidden", border: "1px solid #1a2f4c" }}>
      <MapContainer center={[ANCHOR_LAT, ANCHOR_LNG]} zoom={19} scrollWheelZoom={true} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.map(event => {
          const position = getLatLng(event.location.ground_coords);
          return (
            <CircleMarker 
              key={event.id} 
              center={position} 
              radius={8 + (event.risk_score * 0.15)} 
              pathOptions={{
                fillColor: '#ff7650', 
                color: '#ff946e', 
                weight: 2, 
                fillOpacity: 0.6
              }}
              eventHandlers={{
                click: () => onSelect(event)
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                {words(event.conflict_type)} · {decision(event)}<br/>
                Risk Score: {event.risk_score}
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
    <p>{points.length} markers · Rejected candidates excluded. (Dummy GPS anchor used for prototype).</p>
  </section>;
}

function Replay({event, events, onSelect, onError}) {
  const [participant, setParticipant] = useState(event?.participant_ids[0] || '');
  const [factor, setFactor] = useState(1);
  const [delay, setDelay] = useState(0);
  const [result, setResult] = useState(null);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    if (!playing || !result) return;
    const timer = setInterval(()=>setStep(previous => previous >= result.samples.length-1 ? 0 : previous+1), 70);
    return ()=>clearInterval(timer);
  }, [playing, result]);
  function invalidate() {setResult(null); setPlaying(false);}
  async function run() {
    setBusy(true); onError(''); invalidate();
    try {
      const data = await postJSON('/simulation/run', {event_id:event.id, modified_participant_id:Number(participant), speed_factor:Number(factor), delay_seconds:Number(delay)});
      setResult(data); setStep(0);
    } catch(e) {onError(e.message);} finally {setBusy(false);}
  }
  return <section className="ng-card">
    <h2>What if one participant moved differently?</h2><p>This experiment changes the timing of one measured path. It does not predict how either road user would react.</p>
    <label className="ng-field">Candidate<select aria-label="Replay candidate" value={event?.id || ''} onChange={e=>onSelect(events.find(item=>item.id===e.target.value))}>
      <option value="" disabled>Choose a candidate</option>{events.map(e=><option value={e.id} key={e.id}>{words(e.conflict_type)} · {number(e.timestamp_peak,' s')} · {e.id.slice(-7)}</option>)}</select></label>
    {!event ? <Empty>Select a candidate in Incident explorer or the menu above.</Empty> : <>
      <div className="ng-replay-controls"><label className="ng-field">Participant<select aria-label="Modified participant" value={participant} onChange={e=>{setParticipant(e.target.value);invalidate();}}>
        {event.participant_ids.map((id,i)=><option key={id} value={id}>Object {id} · {event.participant_classes[i]}</option>)}</select></label>
        <label className="ng-field">Speed factor: {Number(factor).toFixed(2)}×<input aria-label="Speed factor" type="range" min=".25" max="1.5" step=".05" value={factor} onChange={e=>{setFactor(e.target.value);invalidate();}}/></label>
        <label className="ng-field">Departure delay: {Number(delay).toFixed(1)} s<input aria-label="Departure delay" type="range" min="0" max="1" step=".1" value={delay} onChange={e=>{setDelay(e.target.value);invalidate();}}/></label>
      </div><button className="ng-primary" disabled={busy} onClick={run}>{busy ? 'Comparing…' : 'Compare measured paths'}<GitBranch size={16}/></button>
      {result && <><div className="ng-stats ng-replay-stats"><Stat label="Original minimum separation" value={number(result.original_min_distance_m,' m')} note="Within the compared time interval"/>
        <Stat label="Retimed minimum separation" value={number(result.simulated_min_distance_m,' m')} note="Same comparison interval"/>
        <Stat label="Separation change" value={number(result.distance_change_m,' m')} note="Positive means farther apart in this model"/></div>
        <PathReplay result={result} step={step}/>
        <div className="ng-player"><button className="ng-secondary" onClick={()=>setPlaying(!playing)}>{playing ? 'Pause replay' : 'Play replay'}</button>
          <input aria-label="Replay time" type="range" min="0" max={result.samples.length-1} value={step} onChange={e=>setStep(Number(e.target.value))}/><span>{number(result.samples[step].timestamp,' s')}</span></div>
        <p className="ng-small">{result.assumptions}</p><p className="ng-small">A larger separation in this experiment does not establish that an intervention would prevent a collision.</p>
      </>}
    </>}
  </section>;
}

function PathReplay({result, step}) {
  const positions = result.samples.flatMap(s=>[...Object.values(s.original),...Object.values(s.simulated)]);
  const minX=Math.min(...positions.map(p=>p[0])), maxX=Math.max(...positions.map(p=>p[0]));
  const minY=Math.min(...positions.map(p=>p[1])), maxY=Math.max(...positions.map(p=>p[1]));
  const scale = Math.min(600/Math.max(1,maxX-minX),320/Math.max(1,maxY-minY));
  const project = p => [50+(p[0]-minX)*scale, 370-(p[1]-minY)*scale];
  return <div className="ng-columns ng-replay-panels">{['original','simulated'].map(kind=><div key={kind}><h3>{kind==='original'?'Measured paths':'Retimed path experiment'}</h3>
    <svg viewBox="0 0 700 420" className="ng-path-chart" aria-label={kind+' ground paths'}>
      <text x="22" y="28" fill="#94a3b8" fontSize="14">Ground plane · metres · relative origin</text>
      {result.participant_ids.map((id,i)=>{const color=i===0?'#00e4ed':'#ffaf69';const current=project(result.samples[step][kind][id]);
        return <g key={id}><polyline fill="none" stroke={color} strokeWidth="3" opacity=".5" points={result.samples.map(s=>project(s[kind][id]).join(',')).join(' ')}/>
          <circle cx={current[0]} cy={current[1]} r="10" fill={color}/><text x={current[0]+15} y={current[1]-12} fill={color} fontSize="18">#{id}</text></g>;})}
      <text x="30" y="407" fill="#94a3b8" fontSize="13">X span {number(maxX-minX,' m')} · Y span {number(maxY-minY,' m')}</text>
    </svg></div>)}</div>;
}

function LiveMonitor() {
  const [telemetry, setTelemetry] = useState(null);
  
  useEffect(() => {
    const eventSource = new EventSource('/api/realtime/telemetry');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setTelemetry(data);
    };
    return () => eventSource.close();
  }, []);

  return (
    <div className="ng-columns">
      <section className="ng-card">
        <div className="ng-section-title"><Activity size={20}/><h2>Live CCTV Feed</h2></div>
        <video src="/demo_video.mp4" autoPlay loop muted style={{width: '100%', borderRadius: '12px'}} />
        <p className="ng-small" style={{marginTop: '12px'}}>Streaming mock feed from AI gateway...</p>
      </section>
      
      <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
        <section className="ng-card">
          <h2>Real-Time Metrics</h2>
          <p>Processing at edge node 04.</p>
          <div className="ng-stats" style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px'}}>
            <div className="ng-stat">
              <span>Vehicles Detected</span>
              <strong>{telemetry ? telemetry.vehicles_detected : '---'}</strong>
              <small>Per minute moving avg</small>
            </div>
            <div className="ng-stat">
              <span>Risk Index</span>
              <strong>{telemetry ? telemetry.risk_index : '-.-'}</strong>
              <small>System scale (1-10)</small>
            </div>
            <div className="ng-stat">
              <span>Active Anomalies</span>
              <strong>{telemetry ? telemetry.active_anomalies : '-'}</strong>
              <small>Pending review</small>
            </div>
            <div className="ng-stat">
              <span>Latency</span>
              <strong>{telemetry ? telemetry.latency_ms + ' ms' : '--'}</strong>
              <small>Glass-to-glass edge</small>
            </div>
          </div>
        </section>

        <section className="ng-card" style={{borderColor: telemetry?.active_anomalies > 1 ? '#ffc107' : 'var(--border-subtle)'}}>
          <h2>System Health</h2>
          <div className="ng-row">
            <span>Status</span>
            <Badge tone={telemetry?.system_health === 'Optimal' ? 'approved' : 'pending'}>
              {telemetry ? telemetry.system_health : 'Connecting...'}
            </Badge>
          </div>
        </section>
      </div>
    </div>
  );
}
