// screens.jsx — Sample game screens (7)
// Sized for desktop (1280×800) artboards; responsive enough for tablet.

// ============================================================
// 1 · TITLE / MAIN MENU
// ============================================================
function TitleScreen() {
  return (
    <div className="dr-art" style={{display:'grid', gridTemplateColumns:'1fr 1.1fr', height:'100%'}}>
      {/* Left — branding column */}
      <div style={{
        padding:'56px 56px 40px',
        display:'flex', flexDirection:'column', justifyContent:'space-between',
        background:'var(--paper)', borderRight:'1px solid var(--rule)'
      }}>
        <div className="row jc-sb ai-c">
          <Logo size={28}/>
          <span className="dr-badge">v0.1 · build 074</span>
        </div>

        <div>
          <div className="dr-eyebrow" style={{marginBottom:18}}>A digital dampfross</div>
          <h1 style={{
            fontFamily:'var(--font-display)', fontWeight:600,
            fontSize:92, lineHeight:0.95, letterSpacing:'-.04em',
            margin:'0 0 24px', color:'var(--ink)'
          }}>
            Lay the lines.<br/>Race&nbsp;the rails.
          </h1>
          <p style={{fontSize:17, lineHeight:1.5, color:'var(--ink-2)', margin:'0 0 32px', maxWidth:'42ch'}}>
            Build the densest rail network on the board. Then send your locomotives racing across it. Two phases. Eight lines. One winner.
          </p>
          <div className="row gap-10 ai-c" style={{flexWrap:'wrap'}}>
            <button className="dr-btn dr-btn--lg">New game <Arrow/></button>
            <button className="dr-btn dr-btn--lg dr-btn--secondary">Resume Sunday at Tilman's</button>
          </div>
          <div className="row gap-16 ai-c" style={{marginTop:24}}>
            <button className="dr-btn dr-btn--ghost dr-btn--sm">Join by code</button>
            <button className="dr-btn dr-btn--ghost dr-btn--sm">Tutorial · 6 min</button>
            <button className="dr-btn dr-btn--ghost dr-btn--sm">Rules</button>
          </div>
        </div>

        <div className="row jc-sb ai-c">
          <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.1em', textTransform:'uppercase'}}>3 friends online</span>
          <div className="row gap-6">
            {[1,4,7].map(i => <span key={i} style={{width:18, height:18, borderRadius:'50%', background:`var(--p${i})`, boxShadow:'0 0 0 2px var(--paper)'}}/>)}
          </div>
        </div>
      </div>

      {/* Right — animated map preview */}
      <div style={{position:'relative', overflow:'hidden', background:'var(--paper)'}}>
        <MapSample width={720} height={800} showTracks={true}/>
        {/* Soft fade across top + bottom */}
        <div style={{position:'absolute', inset:0, pointerEvents:'none', background:'linear-gradient(180deg, var(--paper) 0%, transparent 12%, transparent 88%, var(--paper) 100%)'}}/>
        {/* Floating recent-games card */}
        <div style={{
          position:'absolute', right:32, top:32, width:240,
          background:'var(--surface)', border:'1px solid var(--rule)', borderRadius:12, padding:'14px 16px',
          boxShadow:'var(--sh-2)'
        }}>
          <div className="dr-eyebrow" style={{marginBottom:8}}>Last 3 games</div>
          {[{n:'Sunday at Tilman’s', w:'Hannah', d:'2d ago'},
            {n:'Quiet Tuesday',      w:'Lukas',  d:'5d ago'},
            {n:'Office break',       w:'Mira',   d:'1w ago'}].map((g,i) => (
              <div key={i} className="row jc-sb ai-c" style={{padding:'8px 0', borderTop: i?'1px solid var(--rule-soft)':'none'}}>
                <div>
                  <div style={{fontSize:13, fontWeight:500}}>{g.n}</div>
                  <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase', marginTop:2}}>{g.w} won · {g.d}</div>
                </div>
                <Arrow/>
              </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// 2 · MAP VIEW (mid-game, observing)
// ============================================================
function MapViewScreen() {
  return (
    <div className="dr-art" style={{display:'grid', gridTemplateRows:'56px 1fr', height:'100%'}}>
      {/* Top bar */}
      <header style={{
        borderBottom:'1px solid var(--rule)', background:'var(--surface)',
        display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 20px'
      }}>
        <div className="row ai-c gap-16">
          <Logo size={22}/>
          <span className="dr-badge">Round 4 / 9 · Network phase</span>
          <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Sunday at Tilman’s</span>
        </div>
        <div className="row ai-c gap-10">
          <div className="dr-seg">
            <button className="is-on">Map</button>
            <button>Standings</button>
            <button>Log</button>
          </div>
          <button className="dr-iconbtn"><Gear/></button>
        </div>
      </header>

      <div style={{display:'grid', gridTemplateColumns:'260px 1fr 280px', height:'100%'}}>
        {/* Left rail — players */}
        <aside style={{borderRight:'1px solid var(--rule)', background:'var(--surface-2)', padding:'18px 16px', overflow:'auto'}}>
          <div className="dr-eyebrow" style={{marginBottom:12}}>Players · 4</div>
          <div className="col gap-8">
            <PlayerCard p={2} name="Lukas"  state="active" hand="laying"  score={128} coins={6} trains={11}/>
            <PlayerCard p={1} name="Mira"   state="idle"   hand="next"    score={112} coins={4} trains={13}/>
            <PlayerCard p={4} name="Pieter" state="idle"   hand="next"    score={98}  coins={9} trains={9}/>
            <PlayerCard p={7} name="Sasha"  state="idle"   hand="next"    score={91}  coins={3} trains={14}/>
          </div>

          <div className="dr-eyebrow" style={{margin:'24px 0 10px'}}>Race objectives</div>
          <div className="col gap-8">
            <Overlay title="Capitals" body="Connect 4 capitals" foot="2 / 4 reached" tone="info"/>
            <Overlay title="Coast to coast" body="Sandhafen → Kupferstadt" foot="incomplete" tone="warn"/>
          </div>
        </aside>

        {/* Map */}
        <main style={{position:'relative'}}>
          <MapSample width={900} height={680} showTracks/>
          {/* Bottom HUD */}
          <div className="dr-hud" style={{'--c':'var(--p2)'}}>
            <span className="lineish"/>
            <span>Lukas · S2</span>
            <span className="divider"/>
            <span className="turn">Network · 2 of 5 left</span>
            <span className="divider"/>
            <button className="dr-btn dr-btn--sm" style={{background:'var(--paper)', color:'var(--ink)'}}>Undo</button>
            <button className="dr-btn dr-btn--sm" style={{background:'var(--p3)', color:'#fff'}}>End turn</button>
          </div>

          {/* Top-right map controls */}
          <div style={{position:'absolute', right:16, top:16, display:'flex', flexDirection:'column', gap:6}}>
            <button className="dr-iconbtn"><Plus/></button>
            <button className="dr-iconbtn"><Minus/></button>
            <button className="dr-iconbtn" title="Recenter">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="2" fill="currentColor"/><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3"/></svg>
            </button>
          </div>
        </main>

        {/* Right rail — inspector */}
        <aside style={{borderLeft:'1px solid var(--rule)', background:'var(--surface-2)', padding:'18px 16px', overflow:'auto'}}>
          <div className="dr-eyebrow" style={{marginBottom:12}}>Hovered · hex 17·G</div>
          <div className="dr-panel">
            <div className="dr-panel__head">
              <div className="dr-panel__title">Aschberg ridge</div>
              <span className="dr-panel__sub">mountain</span>
            </div>
            <div className="dr-panel__body">
              <div className="row jc-sb" style={{marginBottom:8}}>
                <span className="mono" style={{fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.08em'}}>Build cost</span>
                <span className="mono tnum" style={{fontWeight:600}}>3 coins</span>
              </div>
              <div className="row jc-sb" style={{marginBottom:8}}>
                <span className="mono" style={{fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.08em'}}>Race cost</span>
                <span className="mono tnum" style={{fontWeight:600}}>2 turns</span>
              </div>
              <div className="row jc-sb">
                <span className="mono" style={{fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.08em'}}>Lines through</span>
                <div className="row gap-4">
                  <span style={{width:10,height:10,borderRadius:'50%',background:'var(--p1)'}}/>
                  <span style={{width:10,height:10,borderRadius:'50%',background:'var(--p2)'}}/>
                </div>
              </div>
            </div>
          </div>

          <div className="dr-eyebrow" style={{margin:'18px 0 10px'}}>Recent log</div>
          <div className="col gap-6">
            {[
              {who:'Mira',   p:1, what:'laid 2 segments toward Lichtenau', t:'00:42'},
              {who:'Lukas',  p:2, what:'rolled a 4',                       t:'00:31'},
              {who:'Pieter', p:4, what:'connected Marienburg',             t:'01:08'},
              {who:'Sasha',  p:7, what:'passed turn',                      t:'01:24'},
            ].map((e,i) => (
              <div key={i} className="row ai-s gap-8" style={{fontSize:12, lineHeight:1.45}}>
                <span style={{width:8,height:8,borderRadius:'50%',background:`var(--p${e.p})`, flex:'0 0 auto', marginTop:5}}/>
                <span style={{color:'var(--ink-1)', flex:1}}><strong>{e.who}</strong> {e.what}</span>
                <span className="mono" style={{fontSize:10, color:'var(--ink-3)'}}>{e.t}</span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

// ============================================================
// 3 · NETWORK-BUILDING TURN (with hover preview)
// ============================================================
function BuildTurnScreen() {
  return (
    <div className="dr-art" style={{display:'grid', gridTemplateRows:'56px 1fr', height:'100%'}}>
      <header style={{borderBottom:'1px solid var(--rule)', background:'var(--surface)', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 20px'}}>
        <div className="row ai-c gap-16">
          <Logo size={22}/>
          <span className="dr-badge dr-badge--solid">Your turn · Lukas</span>
          <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Network phase · place up to 5</span>
        </div>
        <div className="row ai-c gap-10">
          <span className="mono tnum" style={{fontSize:13, color:'var(--ink-2)'}}>00:42 ▾</span>
          <button className="dr-iconbtn"><Gear/></button>
        </div>
      </header>

      <div style={{display:'grid', gridTemplateColumns:'1fr 320px', height:'100%'}}>
        <main style={{position:'relative'}}>
          <MapSample width={960} height={680} showTracks/>

          {/* Active-build prompt over map */}
          <div style={{
            position:'absolute', left:24, top:24,
            background:'var(--surface)', borderRadius:12, padding:'16px 18px',
            border:'1px solid var(--rule)', boxShadow:'var(--sh-2)', width:280,
          }}>
            <div className="row ai-c gap-8" style={{marginBottom:10}}>
              <span style={{width:12,height:12,borderRadius:'50%', background:'var(--p2)'}}/>
              <div className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Line S2 · Lukas</div>
            </div>
            <div style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:22, color:'var(--ink)', letterSpacing:'-.01em', lineHeight:1.15}}>
              Lay 2 more segments
            </div>
            <p style={{fontSize:13, color:'var(--ink-2)', margin:'8px 0 14px', lineHeight:1.45}}>
              Click an empty hex edge adjacent to your network. Mountains cost 3, forests cost 2.
            </p>
            <div className="row gap-6">
              <div style={{flex:1, height:6, borderRadius:3, background:'var(--rule-soft)', overflow:'hidden'}}>
                <div style={{width:'60%', height:'100%', background:'var(--p2)'}}/>
              </div>
              <span className="mono tnum" style={{fontSize:12, color:'var(--ink-2)'}}>3 / 5</span>
            </div>
          </div>

          {/* Cost preview on hovered edge */}
          <div style={{
            position:'absolute', right:48, top:200,
            background:'var(--surface)', borderRadius:10, padding:'10px 14px',
            boxShadow:'var(--sh-2)', border:'1px solid var(--rule)',
            display:'flex', alignItems:'center', gap:12,
          }}>
            <div>
              <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Aschberg ridge</div>
              <div style={{fontWeight:600, fontSize:14, color:'var(--ink)', marginTop:2}}>Cost: 3 coin</div>
            </div>
            <div className="col gap-4">
              <button className="dr-btn dr-btn--sm dr-btn--secondary" style={{padding:'5px 10px'}}>Cancel</button>
              <button className="dr-btn dr-btn--sm" style={{padding:'5px 10px'}}>Build</button>
            </div>
          </div>

          {/* Bottom action HUD */}
          <div className="dr-hud" style={{'--c':'var(--p2)'}}>
            <span className="lineish"/>
            <span>Lukas · S2</span>
            <span className="divider"/>
            <span className="turn">3 of 5 placed · 4 coin left</span>
            <span className="divider"/>
            <button className="dr-btn dr-btn--sm" style={{background:'var(--paper)', color:'var(--ink)'}}>Undo</button>
            <button className="dr-btn dr-btn--sm" style={{background:'var(--p3)', color:'#fff'}}>End turn</button>
          </div>
        </main>

        {/* Right side — actions + remaining */}
        <aside style={{borderLeft:'1px solid var(--rule)', background:'var(--surface-2)', padding:'18px 18px', overflow:'auto'}}>
          <div className="dr-panel">
            <div className="dr-panel__head">
              <div className="dr-panel__title">This turn</div>
              <span className="dr-panel__sub">Network</span>
            </div>
            <div className="dr-panel__body col gap-10">
              {[
                {n:'Roll engine', s:'4 — 5 placements available', done:true},
                {n:'Choose start edge', s:'Hex 12·F · committed', done:true},
                {n:'Lay segments', s:'3 of 5 placed', done:false, active:true},
                {n:'End turn', s:'Or pass remaining', done:false},
              ].map((step,i) => (
                <div key={i} className="row ai-s gap-10" style={{padding:'2px 0'}}>
                  <div style={{
                    width:18, height:18, borderRadius:'50%',
                    background: step.done ? 'var(--p3)' : step.active ? 'var(--surface)' : 'var(--surface)',
                    border: step.done ? 'none' : '1.5px solid '+(step.active ? 'var(--ink)' : 'var(--ink-4)'),
                    color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:10, fontWeight:700, flex:'0 0 auto', marginTop:2
                  }}>{step.done ? '✓' : i+1}</div>
                  <div style={{flex:1}}>
                    <div style={{fontSize:14, fontWeight: step.active ? 600 : 500, color: step.done ? 'var(--ink-2)' : 'var(--ink)'}}>{step.n}</div>
                    <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase', marginTop:2}}>{step.s}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="dr-eyebrow" style={{margin:'24px 0 10px'}}>Available actions</div>
          <div className="col gap-8">
            <button className="dr-btn dr-btn--block dr-btn--secondary">Pay 2 to ignore terrain (×1)</button>
            <button className="dr-btn dr-btn--block dr-btn--secondary">Buy extra placement</button>
            <button className="dr-btn dr-btn--block dr-btn--ghost">Pass remaining placements</button>
          </div>

          <div className="dr-eyebrow" style={{margin:'24px 0 10px'}}>Your line · S2</div>
          <div className="dr-panel">
            <div className="dr-panel__body" style={{padding:14}}>
              <div className="row jc-sb" style={{marginBottom:8}}>
                <span className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>SEGMENTS LAID</span>
                <span className="mono tnum" style={{fontWeight:600}}>17</span>
              </div>
              <div className="row jc-sb" style={{marginBottom:8}}>
                <span className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>CITIES REACHED</span>
                <span className="mono tnum" style={{fontWeight:600}}>3</span>
              </div>
              <div className="row jc-sb">
                <span className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>NETWORK PTS</span>
                <span className="mono tnum" style={{fontWeight:600, color:'var(--p2)'}}>+78</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

// ============================================================
// 4 · RACE PHASE
// ============================================================
function RaceScreen() {
  return (
    <div className="dr-art" style={{display:'grid', gridTemplateRows:'56px 1fr', height:'100%'}}>
      <header style={{borderBottom:'1px solid var(--rule)', background:'var(--surface)', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 20px'}}>
        <div className="row ai-c gap-16">
          <Logo size={22}/>
          <span className="dr-badge" style={{background:'var(--p5-tint)', color:'var(--p5)'}}><span className="dot"/>Race phase</span>
          <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Heat 2 of 3 · Marienburg → Sandhafen</span>
        </div>
        <div className="row ai-c gap-10">
          <span className="mono tnum" style={{fontSize:13, color:'var(--ink-2)'}}>03:21</span>
          <button className="dr-iconbtn"><Gear/></button>
        </div>
      </header>

      <div style={{display:'grid', gridTemplateColumns:'320px 1fr', height:'100%'}}>
        {/* Left — race standings */}
        <aside style={{borderRight:'1px solid var(--rule)', background:'var(--surface-2)', padding:'18px 16px', overflow:'auto'}}>
          <div className="dr-eyebrow">Heat 2 · Live</div>
          <div style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:24, letterSpacing:'-.015em', margin:'4px 0 16px'}}>Marienburg → Sandhafen</div>
          <div className="col gap-8">
            {[
              {p:2, n:'Lukas',  state:'leading',   d:'12 of 18', eta:'1 turn',  pos:1},
              {p:1, n:'Mira',   state:'chasing',   d:'10 of 18', eta:'2 turns', pos:2},
              {p:4, n:'Pieter', state:'chasing',   d:'8 of 18',  eta:'3 turns', pos:3},
              {p:7, n:'Sasha',  state:'derailed',  d:'5 of 18',  eta:'—',       pos:4},
            ].map(r => (
              <div key={r.n} className="dr-player" style={{'--c':`var(--p${r.p})`, padding:'12px 14px', display:'grid', gridTemplateColumns:'28px 1fr auto'}}>
                <div className="mono" style={{fontWeight:600, fontSize:13, color:'var(--ink-2)'}}>0{r.pos}</div>
                <div>
                  <div style={{fontWeight:600, fontSize:14}}>{r.n}</div>
                  <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase', marginTop:2}}>{r.d} · ETA {r.eta}</div>
                </div>
                <div style={{textAlign:'right'}}>
                  <span className={`dr-badge ${r.state==='leading'?'dr-badge--success':r.state==='derailed'?'dr-badge--danger':''}`}>{r.state}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="dr-eyebrow" style={{margin:'24px 0 10px'}}>Heat board</div>
          <div className="dr-panel">
            <div className="dr-panel__body col gap-6" style={{padding:'14px'}}>
              {[
                {h:'Heat 1', from:'Aschberg', to:'Lichtenau', winner:'Mira',   p:1, done:true},
                {h:'Heat 2', from:'Marienburg', to:'Sandhafen', winner:'',     p:2, done:false, active:true},
                {h:'Heat 3', from:'Vossberg', to:'Kupferstadt', winner:'',     p:null, done:false},
              ].map((h,i) => (
                <div key={i} className="row jc-sb ai-c" style={{padding:'6px 0'}}>
                  <div>
                    <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>{h.h}</div>
                    <div style={{fontSize:13, fontWeight:500, marginTop:2}}>{h.from} → {h.to}</div>
                  </div>
                  {h.done ? <span className="dr-chip" style={{'--c':`var(--p${h.p})`}}><span className="swatch"/>{h.winner}</span>
                    : h.active ? <span className="dr-badge dr-badge--solid">Live</span>
                    : <span className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>QUEUED</span>}
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Right — race map */}
        <main style={{position:'relative'}}>
          <RaceMap/>

          {/* Race HUD with dice */}
          <div style={{
            position:'absolute', left:'50%', bottom:24, transform:'translateX(-50%)',
            display:'flex', alignItems:'center', gap:16,
            background:'color-mix(in srgb, var(--ink) 92%, transparent)',
            color:'var(--paper)', padding:'10px 14px 10px 16px',
            borderRadius:'var(--r-pill)', boxShadow:'var(--sh-3)'
          }}>
            <div className="col" style={{gap:2}}>
              <span className="mono" style={{fontSize:10, letterSpacing:'.08em', textTransform:'uppercase', color:'color-mix(in srgb, var(--paper) 60%, transparent)'}}>Lukas rolls</span>
              <span style={{fontWeight:600, fontSize:14}}>+4 hex this turn</span>
            </div>
            <Die value={4}/>
            <Die value={3}/>
            <button className="dr-btn dr-btn--sm" style={{background:'var(--p3)', color:'#fff'}}>Advance train</button>
          </div>
        </main>
      </div>
    </div>
  );
}

function RaceMap() {
  return (
    <div className="dr-map" style={{height:'100%', background:'var(--paper)'}}>
      <svg viewBox="0 0 900 680" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id="paperGrid2" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--rule-soft)" strokeWidth=".5"/>
          </pattern>
        </defs>
        <rect width="900" height="680" fill="url(#paperGrid2)"/>
        {/* Stylized landmass */}
        {[
          {q:0,r:0,t:'forest'},{q:1,r:0,t:'plain'},{q:2,r:0,t:'mountain'},{q:3,r:0,t:'plain'},
          {q:4,r:0,t:'plain'},{q:5,r:0,t:'forest'},{q:6,r:0,t:'plain'},{q:7,r:0,t:'water'},
        ].map((_,i)=>null)}

        {/* Render a slim row of hexes along the race route */}
        {Array.from({length:14}).map((_,i) => {
          const x = 70 + i*55;
          const y = 280 + Math.sin(i/2)*48;
          const types = ['plain','plain','forest','plain','mountain','plain','plain','desert','plain','plain','forest','plain','plain','plain'];
          return <HexTile key={i} cx={x} cy={y} r={30} type={types[i]}/>;
        })}

        {/* The route — heavy black guide line + cities */}
        <path d="M 80 295 Q 220 200 350 300 T 600 320 T 820 285" fill="none" stroke="var(--ink)" strokeWidth="3" strokeDasharray="2 6" opacity=".4"/>

        {/* Player progress lines (sub-routes traced under route) */}
        <path d="M 80 295 Q 220 200 350 300 T 540 318" fill="none" stroke="var(--p2)" strokeWidth="8" strokeLinecap="round" opacity=".95"/>
        <path d="M 80 295 Q 220 200 350 300 T 480 305" fill="none" stroke="var(--p1)" strokeWidth="8" strokeLinecap="round" opacity=".8"/>
        <path d="M 80 295 Q 220 200 350 300 T 420 308" fill="none" stroke="var(--p4)" strokeWidth="8" strokeLinecap="round" opacity=".7"/>
        <path d="M 80 295 Q 220 200 350 300 T 310 312" fill="none" stroke="var(--p7)" strokeWidth="8" strokeLinecap="round" opacity=".55"/>

        {/* Trains along route */}
        <TrainSVG x={540} y={318} player={2} rotation={-10}/>
        <TrainSVG x={480} y={305} player={1} rotation={-12}/>
        <TrainSVG x={420} y={308} player={4} rotation={-15}/>
        <TrainSVG x={310} y={312} player={7} rotation={-22}/>

        {/* Start & finish stations */}
        <CityNode cx={80} cy={295} name="Marienburg" code="Start" size="l" label="left"/>
        <CityNode cx={820} cy={285} name="Sandhafen" code="Finish" size="l" label="right"/>

        {/* Mile markers */}
        {[3, 7, 11].map(i => (
          <g key={i}>
            <line x1={70 + i*55} y1={250} x2={70 + i*55} y2={350} stroke="var(--ink-4)" strokeWidth="0.5" strokeDasharray="2 3"/>
            <text x={70 + i*55} y={244} textAnchor="middle" className="mono" fontSize="9" fill="var(--ink-3)" letterSpacing=".15em">MI · {i}</text>
          </g>
        ))}

        {/* Top route ribbon */}
        <g transform="translate(20, 24)">
          <rect width="860" height="36" rx="18" fill="var(--surface)" stroke="var(--rule)"/>
          <text x="20" y="22" className="mono" fontSize="11" fill="var(--ink-3)" letterSpacing=".08em">HEAT 2</text>
          <text x="80" y="23" fontFamily="var(--font-display)" fontWeight="600" fontSize="14" fill="var(--ink)">Marienburg → Sandhafen</text>
          <text x="780" y="23" textAnchor="end" className="mono" fontSize="11" fill="var(--ink-2)" letterSpacing=".08em">18 hex · 3 mountain</text>
        </g>
      </svg>
    </div>
  );
}

// ============================================================
// 5 · PLAYER HUD / FULL SCOREBOARD
// ============================================================
function ScoreboardScreen() {
  const rows = [
    {p:3, n:'Hannah', net:84, race:58, total:142},
    {p:2, n:'Lukas',  net:76, race:52, total:128},
    {p:1, n:'Mira',   net:62, race:50, total:112},
    {p:4, n:'Pieter', net:58, race:40, total:98},
    {p:7, n:'Sasha',  net:53, race:38, total:91},
    {p:5, n:'Otto',   net:40, race:24, total:64},
  ];
  return (
    <div className="dr-art" style={{display:'grid', gridTemplateRows:'auto 1fr', height:'100%'}}>
      <header style={{padding:'28px 40px', borderBottom:'1px solid var(--rule)', background:'var(--surface)'}}>
        <div className="row jc-sb ai-c">
          <div>
            <div className="dr-eyebrow">Scoreboard · Round 6 of 9</div>
            <h1 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:38, letterSpacing:'-.02em', margin:'4px 0 0'}}>Standings</h1>
          </div>
          <div className="row gap-10 ai-c">
            <div className="dr-seg">
              <button className="is-on">Overall</button>
              <button>Network</button>
              <button>Race</button>
            </div>
            <button className="dr-btn dr-btn--secondary">Export round CSV</button>
          </div>
        </div>
      </header>

      <div style={{padding:'28px 40px', display:'grid', gridTemplateColumns:'1fr 360px', gap:28, overflow:'auto'}}>
        <div>
          <div className="dr-panel" style={{padding:'8px 0'}}>
            <table style={{width:'100%', borderCollapse:'collapse'}}>
              <thead>
                <tr style={{textAlign:'left', color:'var(--ink-3)'}}>
                  <th style={{padding:'12px 24px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase', width:60}}>#</th>
                  <th style={{padding:'12px 8px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase'}}>Line · Player</th>
                  <th style={{padding:'12px 8px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase', width:90}}>Network</th>
                  <th style={{padding:'12px 8px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase', width:80}}>Race</th>
                  <th style={{padding:'12px 8px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase'}}>Trend (last 6 rounds)</th>
                  <th style={{padding:'12px 24px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase', textAlign:'right', width:90}}>Total</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r,i) => (
                  <tr key={r.n} style={{borderTop:'1px solid var(--rule-soft)'}}>
                    <td className="mono" style={{padding:'16px 24px', color: i===0?'var(--p3)':'var(--ink-3)', fontWeight:600}}>0{i+1}</td>
                    <td style={{padding:'16px 8px'}}>
                      <div className="row ai-c gap-12">
                        <div style={{width:32, height:32, borderRadius:'50%', background:`var(--p${r.p})`, color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700, fontSize:12}}>
                          {r.n.slice(0,2).toUpperCase()}
                        </div>
                        <div>
                          <div style={{fontWeight:600}}>{r.n}</div>
                          <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase', marginTop:2}}>Line S{r.p}</div>
                        </div>
                      </div>
                    </td>
                    <td className="mono tnum" style={{padding:'16px 8px', color:'var(--ink-1)'}}>{r.net}</td>
                    <td className="mono tnum" style={{padding:'16px 8px', color:'var(--ink-1)'}}>{r.race}</td>
                    <td style={{padding:'16px 8px'}}>
                      <Trend p={r.p} seed={i}/>
                    </td>
                    <td className="mono tnum" style={{padding:'16px 24px', fontWeight:600, fontSize:18, textAlign:'right', color: i===0?'var(--p3)':'var(--ink)'}}>{r.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="dr-panel" style={{marginBottom:14}}>
            <div className="dr-panel__head">
              <div className="dr-panel__title">Hannah is leading</div>
              <span className="dr-panel__sub">+14</span>
            </div>
            <div className="dr-panel__body" style={{padding:'18px'}}>
              <div className="row ai-c gap-12" style={{marginBottom:14}}>
                <div style={{width:48, height:48, borderRadius:'50%', background:'var(--p3)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700}}>HN</div>
                <div>
                  <div style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:22}}>Hannah</div>
                  <div className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Line S3 · Vossberg Green</div>
                </div>
              </div>
              <div style={{fontSize:13, color:'var(--ink-2)', lineHeight:1.5}}>
                Won heats 1 &amp; 3, built the longest stretch through the Aschberg ridge, and is the only player to connect both capitals.
              </div>
            </div>
          </div>
          <div className="dr-panel">
            <div className="dr-panel__head">
              <div className="dr-panel__title">Round insights</div>
            </div>
            <div className="dr-panel__body col gap-10" style={{padding:'14px 18px'}}>
              {[
                'Mira built the most segments (9) this round.',
                'Sasha derailed twice — 6 race pts forfeit.',
                'Pieter is closest to the Coast‑to‑coast bonus.',
              ].map((t,i) => (
                <div key={i} className="row ai-s gap-10">
                  <div style={{width:6, height:6, borderRadius:'50%', background:'var(--ink-4)', marginTop:8, flex:'0 0 auto'}}/>
                  <div style={{fontSize:13, lineHeight:1.5, color:'var(--ink-1)'}}>{t}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Trend({p, seed=0}) {
  // generate a small sparkline
  const pts = Array.from({length:6}).map((_,i) => 8 + ((i*13+seed*7) % 24));
  const w = 140, h = 36;
  const xs = i => 4 + (i*(w-8)/5);
  const ys = v => h-6 - (v/32)*(h-12);
  const d = pts.map((v,i)=>(i===0?'M':'L')+xs(i)+' '+ys(v)).join(' ');
  return (
    <svg width={w} height={h}>
      <path d={d.replace(/^M/, 'M').replace(/$/, ` L ${xs(5)} ${h-2} L ${xs(0)} ${h-2} Z`)} fill={`var(--p${p}-tint)`}/>
      <path d={d} fill="none" stroke={`var(--p${p})`} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx={xs(5)} cy={ys(pts[5])} r="3" fill={`var(--p${p})`} stroke="var(--surface)" strokeWidth="1.5"/>
    </svg>
  );
}

// ============================================================
// 6 · END-OF-ROUND RESULTS
// ============================================================
function ResultsScreen() {
  return (
    <div className="dr-art" style={{display:'flex', flexDirection:'column', height:'100%'}}>
      {/* Hero band */}
      <div style={{
        padding:'48px 56px 36px',
        background:'var(--surface)',
        borderBottom:'1px solid var(--rule)'
      }}>
        <div className="row jc-sb ai-c" style={{marginBottom:24}}>
          <div className="dr-eyebrow">Round 6 · complete</div>
          <div className="row gap-10 ai-c">
            <button className="dr-btn dr-btn--secondary">Share recap</button>
            <button className="dr-btn">Start round 7 <Arrow/></button>
          </div>
        </div>
        <div className="row ai-end gap-24">
          <div style={{width:96, height:96, borderRadius:'50%', background:'var(--p3)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'var(--font-display)', fontWeight:700, fontSize:34}}>HN</div>
          <div>
            <div className="mono" style={{fontSize:11, color:'var(--p3)', letterSpacing:'.08em', textTransform:'uppercase', fontWeight:600}}>★ Round winner</div>
            <h1 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:64, letterSpacing:'-.03em', margin:'4px 0 4px', lineHeight:1}}>Hannah · Vossberg Green</h1>
            <div style={{fontSize:16, color:'var(--ink-2)'}}>+34 points · widened her lead to <span className="mono tnum" style={{fontWeight:600, color:'var(--ink)'}}>+14</span></div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{padding:'28px 56px', flex:1, overflow:'auto'}}>
        <div style={{display:'grid', gridTemplateColumns:'1.4fr 1fr', gap:24}}>
          {/* Highlights */}
          <div>
            <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'0 0 14px'}}>Round highlights</h3>
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
              {[
                {ico:'⊞', t:'Longest network', who:'Lukas',  v:'17 segments', p:2},
                {ico:'☆', t:'Most heats won',  who:'Hannah', v:'2 / 2',      p:3},
                {ico:'$', t:'Most efficient',  who:'Pieter', v:'1.4 pt/coin', p:4},
                {ico:'▲', t:'Boldest move',    who:'Mira',   v:'Aschberg ridge — 3 coin', p:1},
              ].map((h,i) => (
                <div key={i} className="dr-panel" style={{padding:'18px 18px'}}>
                  <div className="row jc-sb ai-c" style={{marginBottom:8}}>
                    <div className="row ai-c gap-8">
                      <div style={{width:24, height:24, borderRadius:'50%', background:`var(--p${h.p})`, color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:11, fontWeight:700}}>{h.who.slice(0,2).toUpperCase()}</div>
                      <span style={{fontWeight:600, fontSize:14}}>{h.who}</span>
                    </div>
                    <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>{h.t}</span>
                  </div>
                  <div style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:22, color:'var(--ink)', letterSpacing:'-.015em'}}>{h.v}</div>
                </div>
              ))}
            </div>

            <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'28px 0 14px'}}>Round timeline</h3>
            <div className="dr-panel" style={{padding:'20px'}}>
              <Timeline/>
            </div>
          </div>

          {/* Sidebar — round totals */}
          <div>
            <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'0 0 14px'}}>Round totals</h3>
            <div className="dr-panel">
              {[
                {p:3, n:'Hannah', d:'+34', t:142},
                {p:2, n:'Lukas',  d:'+22', t:128},
                {p:1, n:'Mira',   d:'+18', t:112},
                {p:4, n:'Pieter', d:'+16', t:98},
                {p:7, n:'Sasha',  d:'+8',  t:91},
                {p:5, n:'Otto',   d:'−4',  t:64},
              ].map((r,i) => (
                <div key={r.n} className="row ai-c gap-12" style={{padding:'14px 18px', borderTop: i?'1px solid var(--rule-soft)':'none'}}>
                  <span style={{width:10, height:10, borderRadius:'50%', background:`var(--p${r.p})`}}/>
                  <span style={{flex:1, fontWeight:500}}>{r.n}</span>
                  <span className="mono tnum" style={{fontSize:13, color: r.d.startsWith('+') ? 'var(--p3)':'var(--p1)', fontWeight:600}}>{r.d}</span>
                  <span className="mono tnum" style={{fontSize:15, fontWeight:600, minWidth:36, textAlign:'right'}}>{r.t}</span>
                </div>
              ))}
            </div>
            <div className="dr-panel" style={{marginTop:14}}>
              <div className="dr-panel__head">
                <div className="dr-panel__title">Next round preview</div>
              </div>
              <div className="dr-panel__body" style={{padding:'18px'}}>
                <div className="row jc-sb" style={{marginBottom:8}}>
                  <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Phase</span>
                  <span style={{fontWeight:600, fontSize:13}}>Race — Heat 3</span>
                </div>
                <div className="row jc-sb" style={{marginBottom:8}}>
                  <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Route</span>
                  <span style={{fontWeight:600, fontSize:13}}>Vossberg → Kupferstadt</span>
                </div>
                <div className="row jc-sb">
                  <span className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Distance</span>
                  <span style={{fontWeight:600, fontSize:13}}>21 hex · 1 mountain</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Timeline() {
  const events = [
    {t:'12:04', p:1, who:'Mira',   what:'rolled a 5, laid 5 segments'},
    {t:'12:08', p:2, who:'Lukas',  what:'connected Aschberg → Vossberg'},
    {t:'12:13', p:3, who:'Hannah', what:'won Heat 1 (Aschberg → Lichtenau)'},
    {t:'12:21', p:4, who:'Pieter', what:'paid 3 to cross the ridge'},
    {t:'12:28', p:7, who:'Sasha',  what:'derailed in mountains'},
    {t:'12:36', p:3, who:'Hannah', what:'won Heat 2 (Marienburg → Sandhafen)'},
  ];
  return (
    <div style={{position:'relative', paddingLeft:24}}>
      <div style={{position:'absolute', left:8, top:8, bottom:8, width:1, background:'var(--rule)'}}/>
      {events.map((e,i) => (
        <div key={i} className="row ai-c gap-12" style={{padding:'8px 0', position:'relative'}}>
          <span style={{position:'absolute', left:-21, width:14, height:14, borderRadius:'50%', background:`var(--p${e.p})`, border:'2px solid var(--surface)', boxShadow:'0 0 0 1px var(--rule)'}}/>
          <span className="mono tnum" style={{fontSize:11, color:'var(--ink-3)', width:42, letterSpacing:'.04em'}}>{e.t}</span>
          <span style={{fontSize:13, color:'var(--ink-1)'}}><strong>{e.who}</strong> {e.what}</span>
        </div>
      ))}
    </div>
  );
}

// ============================================================
// 7 · SETTINGS
// ============================================================
function SettingsScreen() {
  const [theme, setTheme] = useStateC('light');
  const [snap, setSnap] = useStateC(true);
  const [confirm, setConfirm] = useStateC(true);
  const [speed, setSpeed] = useStateC('normal');
  return (
    <div className="dr-art" style={{display:'grid', gridTemplateColumns:'240px 1fr', height:'100%'}}>
      <aside style={{borderRight:'1px solid var(--rule)', background:'var(--surface-2)', padding:'24px 18px'}}>
        <Logo size={20}/>
        <div className="dr-eyebrow" style={{margin:'28px 0 12px'}}>Settings</div>
        <nav className="col gap-2">
          {[
            {n:'Appearance', on:true},
            {n:'Gameplay'},
            {n:'Controls'},
            {n:'Audio'},
            {n:'Accessibility'},
            {n:'Account'},
          ].map(it => (
            <button key={it.n} style={{
              border:0, background: it.on?'var(--sunk)':'transparent', textAlign:'left',
              fontFamily:'var(--font-display)', fontWeight: it.on?600:500,
              fontSize:14, color: it.on?'var(--ink)':'var(--ink-2)',
              padding:'8px 10px', borderRadius:8, cursor:'pointer'
            }}>{it.n}</button>
          ))}
        </nav>
      </aside>

      <main style={{padding:'40px 48px', overflow:'auto'}}>
        <div className="dr-eyebrow">Settings · Appearance</div>
        <h1 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:38, letterSpacing:'-.02em', margin:'4px 0 8px'}}>Make it yours.</h1>
        <p className="dr-sub">Theme &amp; density preferences are saved per device. Player color isn't your account color — it's the line you're playing this session.</p>

        <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'36px 0 14px'}}>Theme</h3>
        <div className="row gap-12">
          {[
            {id:'light', label:'Paper',  bg:'#f4f2ec', ink:'#14171c'},
            {id:'dark',  label:'Slate',  bg:'#0f1218', ink:'#f1efe9'},
            {id:'sepia', label:'Atlas',  bg:'#efe3ca', ink:'#2a1d09'},
          ].map(t => (
            <button key={t.id} onClick={()=>setTheme(t.id)} style={{
              width:200, borderRadius:14, padding:'18px 18px 14px',
              background: t.bg, color: t.ink,
              border: '2px solid '+(theme===t.id?'var(--ink)':'var(--rule)'),
              cursor:'pointer', textAlign:'left',
            }}>
              <div style={{display:'flex', gap:6, marginBottom:14}}>
                {[1,2,3].map(i => <span key={i} style={{width:14, height:14, borderRadius:'50%', background:`var(--p${i+1})`}}/>)}
              </div>
              <div style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:18}}>{t.label}</div>
              <div className="mono" style={{fontSize:10, letterSpacing:'.08em', textTransform:'uppercase', opacity:.6, marginTop:2}}>{t.id}</div>
            </button>
          ))}
        </div>

        <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'36px 0 14px'}}>Behavior</h3>
        <div className="dr-panel">
          <SettingRow label="Snap track to hex centerlines" sub="Off — free placement. On — recommended." value={snap} onChange={setSnap}/>
          <SettingRow label="Confirm before ending turn" sub="Avoids accidental commits with unspent placements." value={confirm} onChange={setConfirm}/>
          <div className="row jc-sb ai-c" style={{padding:'16px 20px', borderTop:'1px solid var(--rule-soft)'}}>
            <div>
              <div style={{fontWeight:600, fontSize:14}}>Animation speed</div>
              <div className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase', marginTop:2}}>Train + transitions</div>
            </div>
            <div className="dr-seg">
              <button className={speed==='reduced'?'is-on':''} onClick={()=>setSpeed('reduced')}>Reduced</button>
              <button className={speed==='normal'?'is-on':''}  onClick={()=>setSpeed('normal')}>Normal</button>
              <button className={speed==='fast'?'is-on':''}    onClick={()=>setSpeed('fast')}>Fast</button>
            </div>
          </div>
        </div>

        <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'36px 0 14px'}}>Layout density</h3>
        <div className="dr-panel">
          <div className="row jc-sb ai-c" style={{padding:'18px 20px'}}>
            <div>
              <div style={{fontWeight:600, fontSize:14}}>HUD scale</div>
              <div className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase', marginTop:2}}>Compact · Comfortable · Roomy</div>
            </div>
            <div className="dr-seg">
              <button>Compact</button>
              <button className="is-on">Comfortable</button>
              <button>Roomy</button>
            </div>
          </div>
        </div>

        <div className="row jc-e gap-10" style={{margin:'36px 0'}}>
          <button className="dr-btn dr-btn--ghost">Reset to defaults</button>
          <button className="dr-btn">Save</button>
        </div>
      </main>
    </div>
  );
}

function SettingRow({label, sub, value, onChange}) {
  return (
    <div className="row jc-sb ai-c" style={{padding:'16px 20px', borderTop:'1px solid var(--rule-soft)', borderTopWidth: 'var(--first-row-no-border, 1px)'}}>
      <div>
        <div style={{fontWeight:600, fontSize:14}}>{label}</div>
        <div className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase', marginTop:2}}>{sub}</div>
      </div>
      <div className={`dr-toggle ${value?'is-on':''}`} onClick={()=>onChange(!value)}><div className="knob"/></div>
    </div>
  );
}

window.TitleScreen = TitleScreen;
window.MapViewScreen = MapViewScreen;
window.BuildTurnScreen = BuildTurnScreen;
window.RaceScreen = RaceScreen;
window.ScoreboardScreen = ScoreboardScreen;
window.ResultsScreen = ResultsScreen;
window.SettingsScreen = SettingsScreen;

// ============================================================
// 8 · MAP EDITOR
// ============================================================
function MapEditorScreen() {
  const [tool, setTool] = useStateC('paint');
  const [terrain, setTerrain] = useStateC('forest');
  const [brush, setBrush] = useStateC(1);
  const [layer, setLayer] = useStateC('terrain');

  return (
    <div className="dr-art" style={{display:'grid', gridTemplateRows:'48px 1fr 32px', height:'100%', background:'var(--paper)'}}>
      {/* Top bar */}
      <header style={{
        borderBottom:'1px solid var(--rule)', background:'var(--surface)',
        display:'grid', gridTemplateColumns:'1fr auto 1fr', alignItems:'center', padding:'0 14px'
      }}>
        <div className="row ai-c gap-12">
          <Logo size={20}/>
          <span style={{width:1, height:20, background:'var(--rule)'}}/>
          <span style={{fontWeight:600, fontSize:13}}>Mitteldeutschland 1875</span>
          <span className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>map · dr-074-mbg · modified</span>
        </div>

        <div className="row ai-c gap-2">
          {[
            {id:'select',  i:<EditorIcon name="select"/>,  k:'V'},
            {id:'paint',   i:<EditorIcon name="brush"/>,   k:'B'},
            {id:'erase',   i:<EditorIcon name="erase"/>,   k:'E'},
            {id:'fill',    i:<EditorIcon name="fill"/>,    k:'G'},
            {id:'track',   i:<EditorIcon name="track"/>,   k:'T'},
            {id:'city',    i:<EditorIcon name="city"/>,    k:'C'},
            {id:'river',   i:<EditorIcon name="river"/>,   k:'R'},
            {id:'measure', i:<EditorIcon name="measure"/>, k:'M'},
          ].map(t => (
            <button key={t.id} onClick={()=>setTool(t.id)} title={`${t.id} · ${t.k}`} style={{
              width:34, height:34, borderRadius:8, border:'1px solid '+(tool===t.id?'var(--ink)':'transparent'),
              background: tool===t.id ? 'var(--sunk)' : 'transparent',
              color: tool===t.id ? 'var(--ink)' : 'var(--ink-2)',
              cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center'
            }}>{t.i}</button>
          ))}
        </div>

        <div className="row ai-c gap-8 jc-e">
          <button className="dr-btn dr-btn--sm dr-btn--ghost"><EditorIcon name="undo"/></button>
          <button className="dr-btn dr-btn--sm dr-btn--ghost"><EditorIcon name="redo"/></button>
          <span style={{width:1, height:20, background:'var(--rule)', margin:'0 4px'}}/>
          <button className="dr-btn dr-btn--sm dr-btn--secondary">Preview</button>
          <button className="dr-btn dr-btn--sm dr-btn--secondary">Export</button>
          <button className="dr-btn dr-btn--sm">Save map</button>
        </div>
      </header>

      <div style={{display:'grid', gridTemplateColumns:'220px 1fr 280px', minHeight:0}}>
        {/* Left panel — palettes */}
        <aside style={{borderRight:'1px solid var(--rule)', background:'var(--surface-2)', overflow:'auto'}}>
          <PanelHead title="Terrain" sub="Paint with" />
          <div style={{padding:'10px 12px', display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
            {[
              {id:'plain',    cost:1, label:'Plain'},
              {id:'forest',   cost:2, label:'Forest'},
              {id:'mountain', cost:3, label:'Mountain'},
              {id:'water',    cost:'—', label:'Water'},
              {id:'desert',   cost:2, label:'Desert'},
              {id:'swamp',    cost:2, label:'Swamp'},
            ].map(t => (
              <button key={t.id} onClick={()=>setTerrain(t.id)} style={{
                padding:'8px 6px 6px', textAlign:'center', cursor:'pointer',
                background: terrain===t.id?'var(--surface)':'transparent',
                border:'1.5px solid '+(terrain===t.id?'var(--ink)':'var(--rule)'),
                borderRadius:8,
              }}>
                <svg width="44" height="48" viewBox="-24 -26 48 52">
                  <HexTile cx={0} cy={0} r={22} type={t.id}/>
                </svg>
                <div style={{fontSize:11, fontWeight:600, marginTop:2}}>{t.label}</div>
                <div className="mono" style={{fontSize:9, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase'}}>cost {t.cost}</div>
              </button>
            ))}
          </div>

          <PanelHead title="Brush"/>
          <div style={{padding:'4px 14px 14px'}}>
            <div className="dr-seg" style={{width:'100%'}}>
              {[1,2,3].map(s => (
                <button key={s} className={brush===s?'is-on':''} onClick={()=>setBrush(s)} style={{flex:1}}>
                  {s===1?'1 hex':s===2?'7 hex':'19 hex'}
                </button>
              ))}
            </div>
            <div className="row jc-sb" style={{marginTop:14}}>
              <span className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>Opacity</span>
              <span className="mono tnum" style={{fontSize:11}}>100%</span>
            </div>
            <div style={{height:6, background:'var(--sunk)', borderRadius:3, marginTop:6, overflow:'hidden'}}>
              <div style={{width:'100%', height:'100%', background:'var(--ink)'}}/>
            </div>
          </div>

          <PanelHead title="Symbols"/>
          <div style={{padding:'8px 12px 16px', display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:6}}>
            {[
              {n:'Capital', g:<circle r="6" fill="var(--surface)" stroke="var(--ink)" strokeWidth="2"/>},
              {n:'City',    g:<circle r="5" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.6"/>},
              {n:'Town',    g:<circle r="3" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.4"/>},
              {n:'Port',    g:<g><circle r="5" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.6"/><path d="M -2 0 L 2 0 M 0 -2 L 0 2" stroke="var(--ink)" strokeWidth="1"/></g>},
              {n:'Bridge',  g:<path d="M -7 0 Q 0 -6 7 0" fill="none" stroke="var(--ink)" strokeWidth="1.6"/>},
              {n:'Tunnel',  g:<path d="M -7 4 L -7 0 Q -7 -5 0 -5 Q 7 -5 7 0 L 7 4" fill="none" stroke="var(--ink)" strokeWidth="1.6"/>},
            ].map(s => (
              <button key={s.n} className="dr-iconbtn" style={{height:48, padding:0, flexDirection:'column'}}>
                <svg width="24" height="24" viewBox="-12 -12 24 24">{s.g}</svg>
                <span style={{fontSize:9, color:'var(--ink-3)', letterSpacing:'.05em', marginTop:1}}>{s.n}</span>
              </button>
            ))}
          </div>
        </aside>

        {/* Center — canvas */}
        <main style={{position:'relative', overflow:'hidden', background:'var(--paper)'}}>
          <EditorCanvas/>

          {/* Floating bottom-center pill: tool status */}
          <div style={{
            position:'absolute', left:'50%', bottom:18, transform:'translateX(-50%)',
            display:'flex', alignItems:'center', gap:10,
            background:'color-mix(in srgb, var(--ink) 92%, transparent)',
            color:'var(--paper)', padding:'7px 14px',
            borderRadius:'var(--r-pill)', boxShadow:'var(--sh-3)',
            fontSize:12, fontWeight:500,
          }}>
            <EditorIcon name="brush" size={14}/>
            <span style={{textTransform:'capitalize'}}>{tool}</span>
            <span style={{width:1, height:14, background:'color-mix(in srgb, var(--paper) 25%, transparent)'}}/>
            <span className="mono" style={{fontSize:11, letterSpacing:'.05em', textTransform:'uppercase', color:'color-mix(in srgb, var(--paper) 65%, transparent)'}}>Painting {terrain}</span>
            <span style={{width:1, height:14, background:'color-mix(in srgb, var(--paper) 25%, transparent)'}}/>
            <span className="mono tnum" style={{fontSize:11, color:'color-mix(in srgb, var(--paper) 65%, transparent)'}}>q&nbsp;14 · r&nbsp;−6</span>
          </div>

          {/* Floating top-right: zoom + grid + minimap */}
          <div style={{position:'absolute', right:16, top:16, display:'flex', flexDirection:'column', gap:8}}>
            <div style={{background:'var(--surface)', border:'1px solid var(--rule)', borderRadius:10, padding:4, display:'flex', flexDirection:'column', gap:2}}>
              <button className="dr-iconbtn" style={{border:0}}><Plus/></button>
              <button className="dr-iconbtn" style={{border:0}}><Minus/></button>
            </div>
            <button className="dr-iconbtn" title="Toggle grid">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 5h10M2 9h10M5 2v10M9 2v10" stroke="currentColor" strokeWidth="1.2"/>
              </svg>
            </button>
            <div style={{
              width:140, background:'var(--surface)', border:'1px solid var(--rule)', borderRadius:10,
              padding:8, marginTop:6, boxShadow:'var(--sh-1)'
            }}>
              <div className="mono" style={{fontSize:9, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase', marginBottom:4}}>Minimap</div>
              <div style={{position:'relative', width:'100%', height:80, background:'var(--sunk)', borderRadius:6, overflow:'hidden'}}>
                <svg viewBox="0 0 140 80" preserveAspectRatio="xMidYMid slice" width="100%" height="100%">
                  <rect width="140" height="80" fill="var(--terrain-plain)"/>
                  <ellipse cx="40" cy="30" rx="22" ry="14" fill="var(--terrain-forest)"/>
                  <ellipse cx="92" cy="44" rx="18" ry="10" fill="var(--terrain-mountain)"/>
                  <rect x="116" y="0" width="24" height="80" fill="var(--terrain-water)"/>
                  <path d="M 0 18 Q 60 30 140 28" stroke="var(--river)" strokeWidth="1.4" fill="none"/>
                  <rect x="38" y="22" width="48" height="32" fill="none" stroke="var(--ink)" strokeWidth="1.2"/>
                </svg>
              </div>
            </div>
          </div>

          {/* Floating top-left: layer chip */}
          <div style={{position:'absolute', left:16, top:16, display:'flex', flexDirection:'column', gap:6}}>
            <div className="dr-seg" style={{background:'var(--surface)', border:'1px solid var(--rule)', boxShadow:'var(--sh-1)'}}>
              {[
                {id:'terrain', l:'Terrain'},
                {id:'tracks',  l:'Tracks'},
                {id:'symbols', l:'Symbols'},
                {id:'labels',  l:'Labels'},
              ].map(L => (
                <button key={L.id} className={layer===L.id?'is-on':''} onClick={()=>setLayer(L.id)}>{L.l}</button>
              ))}
            </div>
          </div>
        </main>

        {/* Right panel — inspector */}
        <aside style={{borderLeft:'1px solid var(--rule)', background:'var(--surface-2)', overflow:'auto'}}>
          <PanelHead title="Map properties"/>
          <div style={{padding:'4px 16px 14px'}}>
            <Field label="Name" value="Mitteldeutschland 1875"/>
            <Field label="Author" value="t.kaufmann"/>
            <Field label="Players" value="2 – 6"/>
            <div className="row gap-6" style={{marginTop:10}}>
              <Field label="Width"  value="32 hex" mono inline/>
              <Field label="Height" value="22 hex" mono inline/>
            </div>
            <Field label="Seed" value="DR-074-MBG" mono/>
          </div>

          <PanelHead title="Selection · 1 tile" sub="hex 14·−6"/>
          <div style={{padding:'10px 16px 4px', display:'flex', alignItems:'center', gap:14}}>
            <svg width="64" height="68" viewBox="-34 -36 68 72">
              <HexTile cx={0} cy={0} r={30} type="mountain" selected/>
            </svg>
            <div>
              <div style={{fontWeight:600, fontSize:14}}>Aschberg ridge</div>
              <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase', marginTop:2}}>Mountain · build cost 3</div>
            </div>
          </div>
          <div style={{padding:'8px 16px 18px'}}>
            <div className="row jc-sb" style={{padding:'8px 0', borderTop:'1px solid var(--rule-soft)'}}>
              <span className="mono" style={{fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.08em'}}>Race delay</span>
              <span className="mono tnum" style={{fontWeight:600, fontSize:12}}>+2 turns</span>
            </div>
            <div className="row jc-sb" style={{padding:'8px 0', borderTop:'1px solid var(--rule-soft)'}}>
              <span className="mono" style={{fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.08em'}}>Elevation</span>
              <span className="mono tnum" style={{fontWeight:600, fontSize:12}}>820 m</span>
            </div>
            <div className="row jc-sb" style={{padding:'8px 0', borderTop:'1px solid var(--rule-soft)'}}>
              <span className="mono" style={{fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.08em'}}>Bridge allowed</span>
              <div className="dr-toggle is-on" style={{transform:'scale(.85)'}}><div className="knob"/></div>
            </div>
            <div className="row jc-sb" style={{padding:'8px 0', borderTop:'1px solid var(--rule-soft)'}}>
              <span className="mono" style={{fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.08em'}}>Tunnel allowed</span>
              <div className="dr-toggle is-on" style={{transform:'scale(.85)'}}><div className="knob"/></div>
            </div>
          </div>

          <PanelHead title="Layers"/>
          <div style={{padding:'4px 12px 14px'}}>
            {[
              {n:'Labels',   c:9, on:true},
              {n:'Symbols',  c:14, on:true, active: layer==='symbols'},
              {n:'Rivers',   c:3,  on:true},
              {n:'Tracks',   c:0,  on:false, active: layer==='tracks'},
              {n:'Terrain',  c:704, on:true, active: layer==='terrain', locked:false},
              {n:'Grid',     c:'—', on:true},
            ].map(L => (
              <div key={L.n} className="row ai-c gap-10" style={{
                padding:'8px 10px', borderRadius:6,
                background: L.active?'var(--sunk)':'transparent',
                marginBottom:2,
              }}>
                <button className="dr-iconbtn" style={{width:22, height:22, border:0, color: L.on?'var(--ink)':'var(--ink-3)'}}>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    {L.on
                      ? <><path d="M1 6c1.5-2.5 3.5-3.5 5-3.5s3.5 1 5 3.5c-1.5 2.5-3.5 3.5-5 3.5S2.5 8.5 1 6Z" stroke="currentColor" strokeWidth="1.2"/><circle cx="6" cy="6" r="1.6" fill="currentColor"/></>
                      : <><path d="M2 2l8 8M1 6c1.5-2.5 3.5-3.5 5-3.5s3.5 1 5 3.5c-1.5 2.5-3.5 3.5-5 3.5S2.5 8.5 1 6Z" stroke="currentColor" strokeWidth="1.2"/></>
                    }
                  </svg>
                </button>
                <span style={{fontSize:13, fontWeight: L.active?600:500, color: L.on?'var(--ink)':'var(--ink-3)', flex:1}}>{L.n}</span>
                <span className="mono tnum" style={{fontSize:10, color:'var(--ink-3)'}}>{L.c}</span>
              </div>
            ))}
          </div>

          <PanelHead title="Validation" sub="Auto-check"/>
          <div style={{padding:'4px 16px 18px'}}>
            <ValidationRow ok label="Reachability" detail="All 6 cities connectable"/>
            <ValidationRow ok label="No isolated tiles"/>
            <ValidationRow warn label="Race symmetry" detail="Heat 1 favors S1 by 1 hex"/>
            <ValidationRow ok label="Player start fairness"/>
          </div>
        </aside>
      </div>

      {/* Status bar */}
      <footer style={{
        borderTop:'1px solid var(--rule)', background:'var(--surface)',
        display:'flex', alignItems:'center', padding:'0 14px',
        fontSize:11, fontFamily:'var(--font-mono)', color:'var(--ink-3)', letterSpacing:'.05em',
      }}>
        <span>32 × 22 hex · 704 tiles · 6 cities · 3 rivers</span>
        <span style={{margin:'0 10px'}}>·</span>
        <span>zoom 100%</span>
        <span style={{margin:'0 10px'}}>·</span>
        <span>autosaved 00:14 ago</span>
        <span style={{flex:1}}/>
        <span style={{color:'var(--p3)'}}>● Validates for 2–6 players</span>
        <span style={{margin:'0 10px'}}>·</span>
        <span>DR · v0.1</span>
      </footer>
    </div>
  );
}

function EditorCanvas() {
  // Big editable map slice — same DNA as MapSample but denser, with a few selected tiles.
  const W = 980, H = 660;
  const size = 30;
  const tiles = [];
  for (let q=-1; q<20; q++) {
    for (let rr=-1; rr<22; rr++) {
      const [x, y] = axialToPx(q, rr - Math.floor(q/2), size);
      if (x < -40 || x > W+40 || y < -40 || y > H+40) continue;
      const seed = (q*73 + rr*131 + 11) % 17;
      let type = 'plain';
      if (seed === 1 || seed === 4) type = 'forest';
      else if (seed === 7 || seed === 11) type = 'mountain';
      else if (seed === 13) type = 'desert';
      else if (seed === 9) type = 'swamp';
      if (x > W - 90) type = 'water';
      tiles.push({q, r:rr, x, y, type, key:`${q}_${rr}`});
    }
  }
  // The "selected" tile (matches inspector)
  const selX = 14 * size * 1.5;
  const selY = ((-6) + 14/2) * size * Math.sqrt(3);

  return (
    <div style={{width:'100%', height:'100%', position:'relative', overflow:'hidden'}}>
      <svg viewBox={`-20 -20 ${W+40} ${H+40}`} preserveAspectRatio="xMidYMid slice" width="100%" height="100%">
        <defs>
          <pattern id="editorGrid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--rule-soft)" strokeWidth=".5"/>
          </pattern>
        </defs>
        <rect x="-20" y="-20" width={W+40} height={H+40} fill="url(#editorGrid)"/>

        {tiles.map(t => (
          <HexTile key={t.key} cx={t.x} cy={t.y} r={size*0.96} type={t.type}
                   selected={Math.abs(t.x-selX)<20 && Math.abs(t.y-selY)<20}/>
        ))}

        {/* River */}
        <River points={[[20, 80],[140, 130],[260, 200],[360, 260],[420, 380],[520, H-30]]}/>

        {/* Cities */}
        <CityNode cx={130} cy={130} name="Aschberg"   code="ABG" size="m"/>
        <CityNode cx={350} cy={260} name="Vossberg"   code="VBG" size="s"/>
        <CityNode cx={560} cy={170} name="Lichtenau"  code="LCH" size="s" label="left"/>
        <CityNode cx={620} cy={380} name="Marienburg" code="MBG · capital" size="l"/>

        {/* Selection ring (drawn on top) */}
        <path d={hexPath(selX, selY, size*0.98)} fill="none" stroke="var(--ink)" strokeWidth="2.5"/>
        <path d={hexPath(selX, selY, size*0.98)} fill="none" stroke="var(--paper)" strokeWidth="1" strokeDasharray="3 3"/>

        {/* Selection handles */}
        {hexCorners(selX, selY, size*1.05).map(([x,y], i) => (
          <circle key={i} cx={x} cy={y} r="3.5" fill="var(--surface)" stroke="var(--ink)" strokeWidth="1.5"/>
        ))}

        {/* Brush ghost (one cell over) — shows where next paint would go */}
        <g opacity=".55">
          <path d={hexPath(selX + size*1.5, selY - size*Math.sqrt(3)/2, size*0.94)}
                fill="var(--terrain-forest)" stroke="var(--ink)" strokeWidth="1.2" strokeDasharray="3 3"/>
        </g>

        {/* Marquee selection rectangle (hint that selection tool works) */}
        <rect x={680} y={420} width={180} height={120} fill="rgba(20,23,28,.06)" stroke="var(--ink)" strokeWidth="1" strokeDasharray="4 3"/>
        <text x={690} y={414} fontFamily="var(--font-mono)" fontSize="10" fill="var(--ink-2)" letterSpacing=".08em">12 TILES</text>
      </svg>
    </div>
  );
}

function PanelHead({title, sub}) {
  return (
    <div style={{padding:'14px 16px 6px', display:'flex', alignItems:'baseline', justifyContent:'space-between'}}>
      <div className="mono" style={{fontSize:10, color:'var(--ink-2)', letterSpacing:'.1em', textTransform:'uppercase', fontWeight:600}}>{title}</div>
      {sub && <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase'}}>{sub}</div>}
    </div>
  );
}
function Field({label, value, mono, inline}) {
  return (
    <div style={{marginTop:10, flex: inline?1:'initial'}}>
      <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.06em', textTransform:'uppercase'}}>{label}</div>
      <div style={{
        fontFamily: mono?'var(--font-mono)':'var(--font-body)',
        fontSize:13, fontWeight:500, color:'var(--ink)', marginTop:2
      }}>{value}</div>
    </div>
  );
}
function ValidationRow({label, detail, ok, warn, bad}) {
  const color = ok ? 'var(--p3)' : warn ? 'var(--p4)' : 'var(--p1)';
  const sym = ok ? '✓' : warn ? '!' : '✕';
  return (
    <div className="row ai-s gap-10" style={{padding:'6px 0', borderTop:'1px solid var(--rule-soft)'}}>
      <span style={{width:16, height:16, borderRadius:'50%', background:color, color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:10, fontWeight:700, flex:'0 0 auto', marginTop:2}}>{sym}</span>
      <div style={{flex:1}}>
        <div style={{fontSize:12, fontWeight:500, color:'var(--ink)'}}>{label}</div>
        {detail && <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.04em', marginTop:1}}>{detail}</div>}
      </div>
    </div>
  );
}

function EditorIcon({name, size=14}) {
  const s = size, vb = `0 0 14 14`;
  const stroke = { stroke:'currentColor', strokeWidth:1.4, fill:'none', strokeLinecap:'round', strokeLinejoin:'round' };
  switch(name) {
    case 'select':  return <svg width={s} height={s} viewBox={vb}><path d="M3 2l3 9 2-3 3-1z" {...stroke}/></svg>;
    case 'brush':   return <svg width={s} height={s} viewBox={vb}><path d="M10 2l2 2-6 6-3 1 1-3z" {...stroke}/><path d="M3 11l1 1" {...stroke}/></svg>;
    case 'erase':   return <svg width={s} height={s} viewBox={vb}><path d="M2 9l5-5 4 4-5 5z" {...stroke}/><path d="M5 6l4 4" {...stroke}/><path d="M2 12h10" {...stroke}/></svg>;
    case 'fill':    return <svg width={s} height={s} viewBox={vb}><path d="M3 7l5-5 5 5-5 5z" {...stroke}/><path d="M11 9c1 1.5 1 3 0 3s-1-1.5 0-3z" {...stroke} fill="currentColor"/></svg>;
    case 'track':   return <svg width={s} height={s} viewBox={vb}><path d="M2 7h10" {...stroke}/><path d="M3 4v6M6 4v6M9 4v6M12 4v6" {...stroke} strokeWidth="1"/></svg>;
    case 'city':    return <svg width={s} height={s} viewBox={vb}><circle cx="7" cy="7" r="4" {...stroke}/><circle cx="7" cy="7" r="1.4" fill="currentColor"/></svg>;
    case 'river':   return <svg width={s} height={s} viewBox={vb}><path d="M1 5q2-3 4 0t4 0 4 0" {...stroke}/><path d="M1 10q2-3 4 0t4 0 4 0" {...stroke}/></svg>;
    case 'measure': return <svg width={s} height={s} viewBox={vb}><path d="M2 9l7-7 3 3-7 7z" {...stroke}/><path d="M4 7l1 1M6 5l1 1M8 3l1 1" {...stroke} strokeWidth="1"/></svg>;
    case 'undo':    return <svg width={s} height={s} viewBox={vb}><path d="M5 4L2 7l3 3" {...stroke}/><path d="M2 7h6a3 3 0 0 1 0 6" {...stroke}/></svg>;
    case 'redo':    return <svg width={s} height={s} viewBox={vb}><path d="M9 4l3 3-3 3" {...stroke}/><path d="M12 7H6a3 3 0 0 0 0 6" {...stroke}/></svg>;
    default: return null;
  }
}

window.MapEditorScreen = MapEditorScreen;
