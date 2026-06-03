// foundations.jsx — Brand, Colors, Type

// ============================================================
// BRAND COVER
// ============================================================
function BrandCover() {
  return (
    <div className="dr-art dr-pad-l" style={{display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
      <div className="row jc-sb ai-c">
        <Logo size={32} />
        <div className="dr-eyebrow">Design&nbsp;System · v0.1</div>
      </div>
      <div>
        <div className="dr-eyebrow" style={{marginBottom:18}}>Dampfrossdigital</div>
        <h1 style={{
          fontFamily:'var(--font-display)', fontWeight:600,
          fontSize: 124, lineHeight:0.94, letterSpacing:'-0.04em',
          margin:'0 0 28px', color:'var(--ink)'
        }}>
          Lay the lines.<br/>
          <span style={{color:'var(--ink-3)'}}>Race the rails.</span>
        </h1>
        <p style={{fontSize: 19, lineHeight:1.5, color:'var(--ink-2)', maxWidth:'58ch', margin:0}}>
          A digital adaptation of the Dampfross board game. This system codifies the
          schematic transit‑map aesthetic, the eight player lines, and every component
          needed to build, race, and tally a network.
        </p>
      </div>
      <div className="row gap-16 ai-c">
        <div className="row gap-6">
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i} style={{
              width:24, height:24, borderRadius:'50%',
              background:`var(--p${i})`,
              boxShadow:'0 0 0 2px var(--surface), 0 0 0 3px var(--rule)'
            }}/>
          ))}
        </div>
        <div className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>
          Eight&nbsp;lines · One&nbsp;map · Two&nbsp;phases
        </div>
      </div>
    </div>
  );
}

function Logo({size=24, mark='full'}) {
  const s = size;
  return (
    <div className="row ai-c gap-10">
      <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
        {/* Eight radial line ends meeting at a central station — abstract mark */}
        <circle cx="16" cy="16" r="15" fill="var(--ink)"/>
        {[0,45,90,135,180,225,270,315].map((deg,i) => (
          <g key={i} transform={`rotate(${deg} 16 16)`}>
            <rect x="15" y="3" width="2" height="6" rx="1" fill={`var(--p${i+1})`}/>
          </g>
        ))}
        <circle cx="16" cy="16" r="4" fill="var(--paper)"/>
        <circle cx="16" cy="16" r="2" fill="var(--ink)"/>
      </svg>
      {mark === 'full' && (
        <span style={{
          fontFamily:'var(--font-display)', fontWeight:700,
          fontSize: s*0.62, letterSpacing:'-.025em', color:'var(--ink)'
        }}>
          dampfross<span style={{color:'var(--ink-3)', fontWeight:500}}>digital</span>
        </span>
      )}
    </div>
  );
}
window.Logo = Logo;

// ============================================================
// COLOR PALETTE
// ============================================================
const NEUTRALS = [
  ['paper',    '--paper'],
  ['surface',  '--surface'],
  ['surface‑2','--surface-2'],
  ['sunk',     '--sunk'],
  ['rule',     '--rule'],
  ['ink‑4',    '--ink-4'],
  ['ink‑3',    '--ink-3'],
  ['ink‑2',    '--ink-2'],
  ['ink‑1',    '--ink-1'],
  ['ink',      '--ink'],
];

const TERRAIN = [
  ['plain',    '--terrain-plain'],
  ['forest',   '--terrain-forest'],
  ['mountain', '--terrain-mountain'],
  ['water',    '--terrain-water'],
  ['desert',   '--terrain-desert'],
  ['swamp',    '--terrain-swamp'],
];

const LINES = [
  { id: 1, code:'S1', name:'Krapotkin Red',    hex:'#e23b3b' },
  { id: 2, code:'S2', name:'Nordpol Blue',     hex:'#1f6fd9' },
  { id: 3, code:'S3', name:'Vossberg Green',   hex:'#1f7a4a' },
  { id: 4, code:'S4', name:'Lichtenau Yellow', hex:'#e8a915' },
  { id: 5, code:'S5', name:'Sandhafen Orange', hex:'#e76018' },
  { id: 6, code:'S6', name:'Aschberg Violet',  hex:'#7a4dd0' },
  { id: 7, code:'S7', name:'Kupferstadt Teal', hex:'#0a9aa1' },
  { id: 8, code:'S8', name:'Marienburg Pink',  hex:'#d3398a' },
];

function ColorsArtboard() {
  return (
    <div className="dr-art dr-pad-m" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Colors</div>
      <div className="dr-title">Eight lines on warm paper.</div>
      <p className="dr-sub">The map is the surface; the network is the figure. Neutrals stay desaturated so the eight player lines can sing without competing.</p>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'36px 0 14px'}}>Neutrals</h3>
      <div style={{display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:12}}>
        {NEUTRALS.map(([n,v]) => (
          <div key={n} className="dr-swatch" style={{'--c':`var(${v})`}}>
            <div className="chip" style={{borderBottom:'1px solid var(--rule)'}}/>
            <div className="info"><span className="name">{n}</span><span className="hex mono">{v}</span></div>
          </div>
        ))}
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'36px 0 14px'}}>Player Lines · S1–S8</h3>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
        {LINES.map(L => (
          <div key={L.id} className="dr-line-card" style={{'--c':`var(--p${L.id})`}}>
            <div className="dot"/>
            <div className="meta">
              <div className="lbl">{L.name}</div>
              <div className="sub">Line {L.code} · Player {L.id}</div>
            </div>
            <div className="hex">{L.hex}</div>
          </div>
        ))}
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'36px 0 14px'}}>Terrain</h3>
      <div style={{display:'grid', gridTemplateColumns:'repeat(6, 1fr)', gap:10}}>
        {TERRAIN.map(([n,v]) => (
          <div key={n} className="dr-swatch" style={{'--c':`var(${v})`}}>
            <div className="chip" style={{height:60}}/>
            <div className="info"><span className="name">{n}</span></div>
          </div>
        ))}
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'36px 0 14px'}}>Tints (for line halos, soft fills, ghost track)</h3>
      <div style={{display:'grid', gridTemplateColumns:'repeat(8, 1fr)', gap:8}}>
        {LINES.map(L => (
          <div key={L.id} style={{
            height:64, borderRadius:8,
            background:`var(--p${L.id}-tint)`,
            border: `1px solid var(--rule)`,
            display:'flex', alignItems:'flex-end', padding:8,
          }}>
            <span className="mono" style={{fontSize:10, color:'var(--ink-2)', letterSpacing:'.05em'}}>p{L.id}/tint</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================
// COLOR VARIATION B (alt palette)
// ============================================================
function ColorsVariantB() {
  return (
    <div className="dr-art dr-pad-m" data-variant="b" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Variation B · Compass</div>
      <div className="dr-title">Cooler ink, deeper lines.</div>
      <p className="dr-sub">A second color story for civic / atlas contexts — paper trades warmth for slate, player lines deepen one stop. Same 8‑line discipline.</p>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Neutrals · Slate</h3>
      <div style={{display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:12}}>
        {NEUTRALS.map(([n,v]) => (
          <div key={n} className="dr-swatch" style={{'--c':`var(${v})`}}>
            <div className="chip" style={{borderBottom:'1px solid var(--rule)'}}/>
            <div className="info"><span className="name">{n}</span></div>
          </div>
        ))}
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Player Lines · Deepened</h3>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
        {LINES.map(L => (
          <div key={L.id} className="dr-line-card" style={{'--c':`var(--p${L.id})`}}>
            <div className="dot"/>
            <div className="meta">
              <div className="lbl">{L.name.replace(/(Red|Blue|Green|Yellow|Orange|Violet|Teal|Pink)/, (m) => `${m}`)}</div>
              <div className="sub">Line {L.code}</div>
            </div>
            <div className="hex">var(--p{L.id})</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================
// TYPOGRAPHY
// ============================================================
function TypeArtboard() {
  return (
    <div className="dr-art dr-pad-m" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Typography</div>
      <div className="dr-title">Geist + Geist Mono</div>
      <p className="dr-sub">
        A neo‑grotesque pair: <strong>Geist</strong> for display and UI, <strong>Geist Mono</strong> for numerics,
        timetables, station codes, and the small caps that label everything on the board.
      </p>

      <div style={{marginTop:32}}>
        <div className="dr-type-row">
          <div className="meta">Display</div>
          <div className="dr-t-display">Aschberg&nbsp;→&nbsp;Marienburg</div>
          <div className="spec">64 / 65 · −2.5%</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">H1</div>
          <div className="dr-t-h1">Round 7 · Network Phase</div>
          <div className="spec">40 / 43 · −2.0%</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">H2</div>
          <div className="dr-t-h2">Build up to 5 segments</div>
          <div className="spec">28 / 32 · −1.5%</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">H3</div>
          <div className="dr-t-h3">Krapotkin Red is rolling</div>
          <div className="spec">20 / 25 · −1.0%</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">Body</div>
          <div className="dr-t-body">Roll the engine die and choose where to lay your next two segments. Tracks cannot cross other lines, and entering a mountain costs an extra coin.</div>
          <div className="spec">15 / 23 · 0</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">Small</div>
          <div className="dr-t-small">Click a hex to preview; press <kbd style={{padding:'1px 5px', border:'1px solid var(--rule)', borderRadius:4, fontFamily:'var(--font-mono)', fontSize:11}}>Enter</kbd> to commit.</div>
          <div className="spec">13 / 19 · 0</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">Caption</div>
          <div className="dr-t-caption">Station · Trans‑Provinz Line</div>
          <div className="spec">11 / 15 · +6%</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">Numeric</div>
          <div className="dr-t-num" style={{fontSize:38, lineHeight:1}}>
            <span style={{color:'var(--p2)'}}>128</span> <span style={{color:'var(--ink-3)', fontSize:18}}>pts</span> <span style={{color:'var(--ink-3)', fontSize:18}}>·</span> <span>04:21</span>
          </div>
          <div className="spec">tabular‑nums</div>
        </div>
      </div>
    </div>
  );
}

function TypeVariantB() {
  return (
    <div className="dr-art dr-pad-m" data-variant="b" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Variation B · DM Sans + IBM Plex Mono</div>
      <div className="dr-title">A softer cartographic voice.</div>
      <p className="dr-sub">Same scale; rounder terminals on display, more humanist body, plex mono for technical legends.</p>

      <div style={{marginTop:24}}>
        <div className="dr-type-row">
          <div className="meta">Display</div>
          <div className="dr-t-display">Aschberg&nbsp;→&nbsp;Marienburg</div>
          <div className="spec">64 / 65</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">H1</div>
          <div className="dr-t-h1">Round 7 · Network Phase</div>
          <div className="spec">40 / 43</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">H2</div>
          <div className="dr-t-h2">Build up to 5 segments</div>
          <div className="spec">28 / 32</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">Body</div>
          <div className="dr-t-body">Build out from your home station, claiming hex edges. Crossing another player's line costs you a turn.</div>
          <div className="spec">15 / 23</div>
        </div>
        <div className="dr-type-row">
          <div className="meta">Mono</div>
          <div className="dr-t-caption">Plex · 0123456789 · S1 → S8</div>
          <div className="spec">11 / 15</div>
        </div>
      </div>
    </div>
  );
}

window.BrandCover = BrandCover;
window.ColorsArtboard = ColorsArtboard;
window.ColorsVariantB = ColorsVariantB;
window.TypeArtboard = TypeArtboard;
window.TypeVariantB = TypeVariantB;
window.LINES = LINES;
