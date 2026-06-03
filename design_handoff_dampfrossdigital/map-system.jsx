// map-system.jsx — Hex map primitives, tracks, train tokens

// ============================================================
// HEX GEOMETRY HELPERS
// ============================================================
// Flat-top hex layout
function hexCorners(cx, cy, r) {
  const pts = [];
  for (let i=0; i<6; i++) {
    const a = (Math.PI/180) * (60*i);
    pts.push([cx + r*Math.cos(a), cy + r*Math.sin(a)]);
  }
  return pts;
}
function hexPath(cx, cy, r) {
  const c = hexCorners(cx, cy, r);
  return 'M' + c.map(p => p.join(',')).join('L') + 'Z';
}
// axial -> pixel (flat-top)
function axialToPx(q, r, size) {
  const x = size * (3/2) * q;
  const y = size * (Math.sqrt(3) * (r + q/2));
  return [x, y];
}

window.hexCorners = hexCorners;
window.hexPath = hexPath;
window.axialToPx = axialToPx;

// ============================================================
// HEX TILE — terrain types
// ============================================================
const TERRAINS = {
  plain:    { fill:'var(--terrain-plain)',    stroke:'var(--rule)', glyph:null },
  forest:   { fill:'var(--terrain-forest)',   stroke:'var(--rule)', glyph:'forest' },
  mountain: { fill:'var(--terrain-mountain)', stroke:'var(--rule)', glyph:'mountain' },
  water:    { fill:'var(--terrain-water)',    stroke:'var(--rule)', glyph:'wave' },
  desert:   { fill:'var(--terrain-desert)',   stroke:'var(--rule)', glyph:'dots' },
  swamp:    { fill:'var(--terrain-swamp)',    stroke:'var(--rule)', glyph:'tuft' },
  city:     { fill:'var(--surface)',          stroke:'var(--ink)',  glyph:'city' },
};

function HexGlyph({type, cx, cy, r=14}) {
  if (type === 'forest') {
    return (
      <g>
        <polygon points={`${cx-6},${cy+4} ${cx},${cy-5} ${cx+6},${cy+4}`} fill="var(--p3)" opacity=".55"/>
        <polygon points={`${cx-9},${cy+4} ${cx-12},${cy+4} ${cx-10.5},${cy+1}`} fill="var(--p3)" opacity=".4"/>
        <polygon points={`${cx+9},${cy+4} ${cx+12},${cy+4} ${cx+10.5},${cy+1}`} fill="var(--p3)" opacity=".4"/>
      </g>
    );
  }
  if (type === 'mountain') {
    return (
      <g>
        <polygon points={`${cx-10},${cy+5} ${cx-3},${cy-6} ${cx+4},${cy+5}`} fill="var(--ink-2)" opacity=".5"/>
        <polygon points={`${cx+2},${cy+5} ${cx+8},${cy-3} ${cx+13},${cy+5}`} fill="var(--ink-2)" opacity=".35"/>
        <polygon points={`${cx-4},${cy-5} ${cx-2.5},${cy-7} ${cx-1},${cy-5}`} fill="var(--surface)"/>
      </g>
    );
  }
  if (type === 'wave') {
    return (
      <g stroke="var(--river)" strokeWidth="1.2" fill="none" strokeLinecap="round">
        <path d={`M ${cx-10} ${cy-2} q 5 -4 10 0 t 10 0`}/>
        <path d={`M ${cx-10} ${cy+4} q 5 -4 10 0 t 10 0`}/>
      </g>
    );
  }
  if (type === 'dots') {
    return (
      <g fill="var(--ink-3)">
        <circle cx={cx-6} cy={cy-3} r="1"/>
        <circle cx={cx+2} cy={cy-1} r="1"/>
        <circle cx={cx-2} cy={cy+4} r="1"/>
        <circle cx={cx+7} cy={cy+3} r="1"/>
      </g>
    );
  }
  if (type === 'tuft') {
    return (
      <g stroke="var(--ink-2)" strokeWidth="1" strokeLinecap="round">
        <line x1={cx-6} y1={cy+3} x2={cx-6} y2={cy-1}/>
        <line x1={cx} y1={cy+3} x2={cx} y2={cy-3}/>
        <line x1={cx+6} y1={cy+3} x2={cx+6} y2={cy-1}/>
      </g>
    );
  }
  return null;
}
window.HexGlyph = HexGlyph;

// Hex tile (one cell)
function HexTile({cx, cy, r=28, type='plain', label, code, selected, ghost, children}) {
  const t = TERRAINS[type] || TERRAINS.plain;
  return (
    <g className={`hex hex-${type} ${selected?'is-selected':''} ${ghost?'is-ghost':''}`}>
      <path d={hexPath(cx, cy, r)} fill={t.fill} stroke={t.stroke} strokeWidth={selected?1.5:.6}
            opacity={ghost?.5:1}/>
      <HexGlyph type={t.glyph} cx={cx} cy={cy}/>
      {selected && <path d={hexPath(cx, cy, r-1)} fill="none" stroke="var(--ink)" strokeWidth="1.5" strokeDasharray="3 3"/>}
      {children}
    </g>
  );
}
window.HexTile = HexTile;

// City (a major node on the network)
function CityNode({cx, cy, name, code, size='m', label='right'}) {
  const r = size === 'l' ? 9 : size === 's' ? 5 : 7;
  const labelDx = label === 'right' ? r+8 : -(r+8);
  const labelAnchor = label === 'right' ? 'start' : 'end';
  return (
    <g>
      {/* halo */}
      <circle cx={cx} cy={cy} r={r+4} fill="var(--paper)" opacity=".85"/>
      <circle cx={cx} cy={cy} r={r} fill="var(--surface)" stroke="var(--ink)" strokeWidth="2"/>
      {size === 'l' && <circle cx={cx} cy={cy} r={r-3} fill="var(--ink)"/>}
      {name && (
        <text x={cx+labelDx} y={cy+4} className="city-label" textAnchor={labelAnchor}>{name}</text>
      )}
      {code && (
        <text x={cx+labelDx} y={cy+15} className="city-meta" textAnchor={labelAnchor}>{code}</text>
      )}
    </g>
  );
}
window.CityNode = CityNode;

// River — smooth polyline through control points
function River({points}) {
  const d = points.map((p,i) => (i===0?'M':'L')+p.join(' ')).join(' ');
  return (
    <g>
      <path d={d} fill="none" stroke="var(--coast)" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" opacity=".55"/>
      <path d={d} fill="none" stroke="var(--river)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"/>
    </g>
  );
}
window.River = River;

// Track segment between two hex centers (or via mid points)
function Track({points, player=2, ghost=false, casing=true}) {
  const d = points.map((p,i) => (i===0?'M':'L')+p.join(' ')).join(' ');
  return (
    <g style={{'--c':`var(--p${player})`}}>
      {casing && <path d={d} className="dr-track dr-track--casing"/>}
      <path d={d} className={ghost ? 'dr-track dr-track--ghost' : 'dr-track'}/>
    </g>
  );
}
window.Track = Track;

// Train token (SVG version, positioned at point)
function TrainSVG({x, y, player=2, rotation=0, size=1}) {
  return (
    <g transform={`translate(${x},${y}) rotate(${rotation}) scale(${size})`} style={{'--c':`var(--p${player})`}}>
      {/* casing */}
      <rect x="-16" y="-9" width="32" height="18" rx="4" fill="var(--surface)" stroke="var(--rule)" strokeWidth="1"/>
      {/* body */}
      <rect x="-14" y="-7" width="24" height="14" rx="2" fill={`var(--p${player})`}/>
      {/* nose */}
      <polygon points="10,-7 16,0 10,7" fill={`var(--p${player})`}/>
      {/* window */}
      <rect x="-10" y="-4" width="5" height="8" rx="1" fill="rgba(255,255,255,.85)"/>
      <rect x="-3" y="-4" width="5" height="8" rx="1" fill="rgba(255,255,255,.85)"/>
      {/* wheels */}
      <circle cx="-9" cy="9" r="2.5" fill="var(--ink)"/>
      <circle cx="0" cy="9" r="2.5" fill="var(--ink)"/>
      <circle cx="8" cy="9" r="2.5" fill="var(--ink)"/>
    </g>
  );
}
window.TrainSVG = TrainSVG;

// ============================================================
// HEX-LIBRARY ARTBOARD (shows all terrain types + glyph guide)
// ============================================================
function MapSystemArtboard() {
  const r = 36;
  const w = 980, h = 640;
  return (
    <div className="dr-art dr-pad-m" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Map System</div>
      <div className="dr-title">A schematic grid, just enough texture.</div>
      <p className="dr-sub">Flat‑top hex tiles. Terrains read at a glance through restrained glyphs — never illustrative. Cities are the only typographic anchors on the board.</p>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Terrain tiles</h3>
      <div style={{display:'grid', gridTemplateColumns:'repeat(6, 1fr)', gap:14}}>
        {['plain','forest','mountain','water','desert','swamp'].map(t => (
          <div key={t} className="dr-panel dr-panel--flat" style={{padding:'18px 12px 14px', textAlign:'center'}}>
            <svg width="80" height="86" viewBox="-44 -48 88 96">
              <HexTile cx={0} cy={0} r={40} type={t}/>
            </svg>
            <div style={{fontSize:13, fontWeight:600, marginTop:4, color:'var(--ink)'}}>{t}</div>
            <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase', marginTop:2}}>
              {{plain:'cost 1', forest:'cost 2', mountain:'cost 3', water:'impassable', desert:'cost 2', swamp:'cost 2'}[t]}
            </div>
          </div>
        ))}
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>City scales</h3>
      <div className="dr-panel" style={{padding:'24px', display:'flex', alignItems:'center', justifyContent:'space-around', background:'var(--surface)'}}>
        <svg width="160" height="80" viewBox="0 0 160 80">
          <CityNode cx={80} cy={32} name="Marienburg" code="MBG · capital" size="l"/>
        </svg>
        <svg width="160" height="80" viewBox="0 0 160 80">
          <CityNode cx={80} cy={32} name="Aschberg" code="ABG · city" size="m"/>
        </svg>
        <svg width="160" height="80" viewBox="0 0 160 80">
          <CityNode cx={80} cy={32} name="Vossberg" code="VBG · town" size="s"/>
        </svg>
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Map sample</h3>
      <MapSample width={w} height={420}/>
    </div>
  );
}

// A small playable-looking slice of the map
function MapSample({width=900, height=420, showTracks=true, showTrains=false, mood='static'}) {
  // Generate axial hex grid
  const size = 32;
  const cols = Math.ceil(width / (size*1.5)) + 2;
  const rows = Math.ceil(height / (size*Math.sqrt(3))) + 1;
  const tiles = [];
  for (let q=-2; q<cols; q++) {
    for (let rr=-2; rr<rows; rr++) {
      const [x, y] = axialToPx(q, rr - Math.floor(q/2), size);
      if (x < -50 || x > width+50 || y < -50 || y > height+50) continue;
      // Deterministic-ish terrain seed
      const seed = (q*73 + rr*131 + 7) % 17;
      let type = 'plain';
      if (seed === 1 || seed === 4) type = 'forest';
      else if (seed === 7 || seed === 11) type = 'mountain';
      else if (seed === 13) type = 'desert';
      else if (seed === 9) type = 'swamp';
      tiles.push({q, r:rr, x, y, type, key:`${q}_${rr}`});
    }
  }

  // Water band (a "sea" on the right)
  const waterTiles = tiles.filter(t => t.x > width - 90);
  waterTiles.forEach(t => t.type = 'water');

  // Cities — placed at chosen axial coords
  const cities = [
    { x: 120, y: 110, name:'Aschberg',    code:'ABG · city',     size:'m'},
    { x: 280, y: 240, name:'Vossberg',    code:'VBG · town',     size:'s'},
    { x: 470, y: 130, name:'Lichtenau',   code:'LCH · town',     size:'s', label:'left'},
    { x: 560, y: 300, name:'Marienburg',  code:'MBG · capital',  size:'l'},
    { x: 760, y: 180, name:'Kupferstadt', code:'KPF · port',     size:'m', label:'left'},
    { x: 380, y: 380, name:'Sandhafen',   code:'SND · port',     size:'m'},
  ];

  // Tracks (player lines connecting cities)
  const tracks = [
    { player: 2, points: [[120,110],[200,160],[280,240],[380,380]] },         // Blue: Aschberg → Vossberg → Sandhafen
    { player: 1, points: [[120,110],[260,90],[470,130],[560,300]] },           // Red:  Aschberg → Lichtenau → Marienburg
    { player: 3, points: [[560,300],[660,260],[760,180]] },                    // Green: Marienburg → Kupferstadt
    { player: 4, points: [[280,240],[380,200],[470,130]], ghost:true },        // Yellow ghost (planned)
  ];

  return (
    <div className="dr-map" style={{height, borderRadius:12, border:'1px solid var(--rule)', overflow:'hidden', background:'var(--paper)'}}>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid slice">
        {/* Background ruled grid */}
        <defs>
          <pattern id="paperGrid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--rule-soft)" strokeWidth=".5"/>
          </pattern>
        </defs>
        <rect width={width} height={height} fill="url(#paperGrid)"/>

        {/* Tiles */}
        {tiles.map(t => (
          <HexTile key={t.key} cx={t.x} cy={t.y} r={size*0.96} type={t.type}/>
        ))}

        {/* River */}
        <River points={[[40, 50],[150, 100],[250, 180],[330, 240],[380, 380],[470, height-20]]}/>

        {/* Tracks */}
        {showTracks && tracks.map((tr, i) => (
          <Track key={i} points={tr.points} player={tr.player} ghost={tr.ghost}/>
        ))}

        {/* Cities */}
        {cities.map((c,i) => (
          <CityNode key={i} cx={c.x} cy={c.y} name={c.name} code={c.code} size={c.size} label={c.label || 'right'}/>
        ))}

        {/* Trains */}
        {showTrains && (
          <>
            <TrainSVG x={210} y={170} player={2} rotation={35}/>
            <TrainSVG x={350} y={108} player={1} rotation={-12}/>
          </>
        )}

        {/* Compass tag */}
        <g transform={`translate(${width-90}, ${height-50})`}>
          <circle r="22" fill="var(--surface)" stroke="var(--rule)"/>
          <line x1="0" y1="-14" x2="0" y2="14" stroke="var(--ink)" strokeWidth="1"/>
          <polygon points="0,-15 -4,-6 4,-6" fill="var(--ink)"/>
          <text y="-26" textAnchor="middle" className="mono" fontSize="9" fill="var(--ink-3)" letterSpacing=".15em">NORTH</text>
        </g>
      </svg>
    </div>
  );
}
window.MapSample = MapSample;

// ============================================================
// TRACKS & TRAINS ARTBOARD
// ============================================================
function TracksAndTrainsArtboard() {
  return (
    <div className="dr-art dr-pad-m" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Network · Tracks &amp; Trains</div>
      <div className="dr-title">Lines that belong to people.</div>
      <p className="dr-sub">Every track is owned. Strokes get a paper‑colored casing so colored lines stay legible when crossing terrain — the same trick metro maps use over rivers and parks.</p>

      {/* Track varieties */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Track states</h3>
      <div className="dr-panel" style={{padding:'24px'}}>
        <svg viewBox="0 0 800 220" width="100%" height="200">
          <rect width="800" height="220" fill="var(--surface)"/>
          {/* Confirmed */}
          <Track points={[[40,40],[200,40],[260,40]]} player={2}/>
          <text x="40" y="74" className="mono" fontSize="11" fill="var(--ink-3)" letterSpacing=".08em">CONFIRMED · this turn</text>
          {/* Ghost / planned */}
          <Track points={[[40,110],[200,110],[260,110]]} player={2} ghost/>
          <text x="40" y="144" className="mono" fontSize="11" fill="var(--ink-3)" letterSpacing=".08em">PLANNED · click to commit</text>
          {/* Junction (3-way) */}
          <Track points={[[400, 180],[480, 100],[560, 100]]} player={1}/>
          <Track points={[[480, 100],[480, 40]]} player={1}/>
          <circle cx="480" cy="100" r="6" fill="var(--surface)" stroke="var(--p1)" strokeWidth="3"/>
          <text x="400" y="210" className="mono" fontSize="11" fill="var(--ink-3)" letterSpacing=".08em">JUNCTION · 3‑way</text>
          {/* Crossing (parallel) */}
          <Track points={[[600, 40],[760, 40]]} player={3}/>
          <Track points={[[600, 60],[760, 60]]} player={5}/>
          <text x="600" y="92" className="mono" fontSize="11" fill="var(--ink-3)" letterSpacing=".08em">SHARED EDGE · parallel</text>
        </svg>
      </div>

      {/* Train tokens */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Train tokens · all 8 players</h3>
      <div className="dr-panel" style={{padding:'24px'}}>
        <div style={{display:'grid', gridTemplateColumns:'repeat(8, 1fr)', gap:12}}>
          {[1,2,3,4,5,6,7,8].map(p => (
            <div key={p} style={{textAlign:'center', padding:'12px 4px'}}>
              <svg viewBox="-26 -18 52 36" width="64" height="44">
                <TrainSVG x={0} y={0} player={p}/>
              </svg>
              <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', marginTop:6}}>S{p}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Ownership badges */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Line markers</h3>
      <div className="row gap-10" style={{flexWrap:'wrap'}}>
        {[1,2,3,4,5,6,7,8].map(p => (
          <div key={p} className="dr-chip" style={{'--c':`var(--p${p})`}}>
            <span className="swatch"/>
            <span>Line S{p}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
window.TracksAndTrainsArtboard = TracksAndTrainsArtboard;
window.MapSystemArtboard = MapSystemArtboard;
