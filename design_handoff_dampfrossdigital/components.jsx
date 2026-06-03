// components.jsx — Buttons, panels, dialogs, badges, inputs, player cards, HUD

const { useState: useStateC } = React;

// ============================================================
// COMPONENTS ARTBOARD
// ============================================================
function ComponentsArtboard() {
  const [seg, setSeg] = useStateC('build');
  const [tog, setTog] = useStateC(true);

  return (
    <div className="dr-art dr-pad-m" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Components</div>
      <div className="dr-title">A small kit. Used often.</div>
      <p className="dr-sub">Pill buttons, paper panels, mono micro‑labels. Forms feel like ticket stubs; alerts feel like station announcements.</p>

      {/* BUTTONS */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Buttons</h3>
      <div className="dr-panel" style={{padding:'22px'}}>
        <div className="row gap-10 ai-c" style={{flexWrap:'wrap'}}>
          <button className="dr-btn dr-btn--lg">Start the round <Arrow/></button>
          <button className="dr-btn">Commit track</button>
          <button className="dr-btn dr-btn--secondary">Cancel</button>
          <button className="dr-btn dr-btn--ghost">Skip turn</button>
          <button className="dr-btn dr-btn--success">Roll engine die</button>
          <button className="dr-btn dr-btn--danger">Forfeit race</button>
        </div>
        <div className="row gap-10 ai-c" style={{flexWrap:'wrap', marginTop:14}}>
          <button className="dr-btn dr-btn--sm">Undo</button>
          <button className="dr-btn dr-btn--sm dr-btn--secondary">Redo</button>
          <button className="dr-btn dr-btn--sm dr-btn--ghost">Inspect</button>
          <button className="dr-iconbtn"><Plus/></button>
          <button className="dr-iconbtn"><Minus/></button>
          <button className="dr-iconbtn"><Gear/></button>
          <button className="dr-iconbtn"><InfoI/></button>
        </div>
      </div>

      {/* BADGES & CHIPS */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Badges, chips, status</h3>
      <div className="dr-panel" style={{padding:'22px'}}>
        <div className="row gap-8 ai-c" style={{flexWrap:'wrap'}}>
          <span className="dr-badge">Round 4 / 9</span>
          <span className="dr-badge dr-badge--solid">Your turn</span>
          <span className="dr-badge dr-badge--success"><span className="dot"/> Track laid</span>
          <span className="dr-badge dr-badge--warn"><span className="dot"/> Pay 2 coin</span>
          <span className="dr-badge dr-badge--danger"><span className="dot"/> Blocked</span>
        </div>
        <div className="row gap-8 ai-c" style={{flexWrap:'wrap', marginTop:14}}>
          <span className="dr-chip" style={{'--c':'var(--p2)'}}><span className="swatch"/> Lukas (S2)</span>
          <span className="dr-chip" style={{'--c':'var(--p1)'}}><span className="swatch"/> Mira (S1)</span>
          <span className="dr-chip" style={{'--c':'var(--p4)'}}><span className="swatch"/> Pieter (S4)</span>
          <span className="dr-chip" style={{'--c':'var(--p7)'}}><span className="swatch"/> Sasha (S7)</span>
        </div>
      </div>

      {/* SEGMENTED + TOGGLE + INPUTS */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Controls</h3>
      <div className="dr-panel" style={{padding:'22px'}}>
        <div className="row gap-32 ai-c" style={{flexWrap:'wrap'}}>
          <div className="col gap-8">
            <span className="dr-eyebrow">Phase</span>
            <div className="dr-seg">
              <button className={seg==='build'?'is-on':''} onClick={()=>setSeg('build')}>Network</button>
              <button className={seg==='race'?'is-on':''}  onClick={()=>setSeg('race')}>Race</button>
              <button className={seg==='audit'?'is-on':''} onClick={()=>setSeg('audit')}>Audit</button>
            </div>
          </div>
          <div className="col gap-8">
            <span className="dr-eyebrow">Snap to grid</span>
            <div className={`dr-toggle ${tog?'is-on':''}`} onClick={()=>setTog(!tog)}><div className="knob"/></div>
          </div>
          <div className="col gap-8" style={{minWidth:220}}>
            <span className="dr-label">Session name</span>
            <input className="dr-input" defaultValue="Sunday at Tilman's"/>
          </div>
          <div className="col gap-8" style={{minWidth:120}}>
            <span className="dr-label">Seed</span>
            <input className="dr-input mono" defaultValue="DR‑074‑MBG" style={{fontFamily:'var(--font-mono)'}}/>
          </div>
        </div>
      </div>

      {/* PANEL & DIALOG */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Panels &amp; dialogs</h3>
      <div className="row gap-16" style={{alignItems:'flex-start'}}>
        <div className="dr-panel" style={{flex:1, minWidth:280}}>
          <div className="dr-panel__head">
            <div className="dr-panel__title">Turn order</div>
            <span className="dr-panel__sub">Round 4</span>
          </div>
          <div className="dr-panel__body col gap-8">
            {[
              {n:'Mira',   p:1, on:true},
              {n:'Lukas',  p:2, on:false},
              {n:'Pieter', p:4, on:false},
              {n:'Sasha',  p:7, on:false},
            ].map(r => (
              <div key={r.n} className="row jc-sb ai-c">
                <div className="row ai-c gap-10">
                  <span style={{width:10, height:10, borderRadius:'50%', background:`var(--p${r.p})`}}/>
                  <span style={{fontWeight:500}}>{r.n}</span>
                </div>
                {r.on
                  ? <span className="dr-badge dr-badge--solid">Now</span>
                  : <span className="mono" style={{fontSize:11, color:'var(--ink-3)'}}>WAITING</span>}
              </div>
            ))}
          </div>
        </div>

        <div className="dr-dialog" style={{margin:0}}>
          <span className="dr-badge dr-badge--warn" style={{marginBottom:12}}><span className="dot"/> Mountain ahead</span>
          <h3>Pay 2 coin to lay through Aschberg ridge?</h3>
          <p>This segment crosses a mountain hex. You'll spend 2 of your 6 remaining coins and one of your two track placements this turn.</p>
          <div className="actions">
            <button className="dr-btn dr-btn--secondary">Choose another hex</button>
            <button className="dr-btn">Pay &amp; build</button>
          </div>
        </div>
      </div>

      {/* TOASTS */}
      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Announcements</h3>
      <div className="col gap-10" style={{alignItems:'flex-start'}}>
        <div className="dr-toast" style={{'--c':'var(--success)'}}><span className="icon">✓</span> Lukas connected Aschberg → Marienburg</div>
        <div className="dr-toast" style={{'--c':'var(--p1)'}}><span className="icon">!</span> Mira's locomotive is delayed two turns</div>
        <div className="dr-toast" style={{'--c':'var(--p4)'}}><span className="icon">★</span> Pieter completed all 3 race objectives</div>
      </div>
    </div>
  );
}

// Icons used inline
function Arrow() { return <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8m-3-3 3 3-3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>; }
function Plus()  { return <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 3v8m-4-4h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>; }
function Minus() { return <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>; }
function Gear()  { return <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.4"/><path d="M8 2v1.6M8 12.4V14M2 8h1.6M12.4 8H14M3.5 3.5l1.1 1.1M11.4 11.4l1.1 1.1M12.5 3.5l-1.1 1.1M4.6 11.4l-1.1 1.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>; }
function InfoI() { return <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.4"/><path d="M7 6v3.4M7 4.3v.4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>; }
function Pause() { return <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"><rect x="3" y="2" width="3" height="10" rx="1"/><rect x="8" y="2" width="3" height="10" rx="1"/></svg>; }
function Play()  { return <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"><path d="M4 2l8 5-8 5z"/></svg>; }
window.Arrow=Arrow; window.Plus=Plus; window.Minus=Minus; window.Gear=Gear; window.InfoI=InfoI; window.Pause=Pause; window.Play=Play;

// ============================================================
// PLAYER CARDS ARTBOARD
// ============================================================
function PlayerCardsArtboard() {
  const players = [
    { p:2, name:'Lukas',  state:'active',  hand:'02:14 left',   score: 128, coins: 6, trains: 11},
    { p:1, name:'Mira',   state:'idle',    hand:'next',         score: 112, coins: 4, trains: 13},
    { p:4, name:'Pieter', state:'idle',    hand:'next',         score: 98,  coins: 9, trains: 9},
    { p:7, name:'Sasha',  state:'idle',    hand:'next',         score: 91,  coins: 3, trains: 14},
    { p:3, name:'Hannah', state:'winner',  hand:'completed',    score: 142, coins: 0, trains: 0},
    { p:5, name:'Otto',   state:'out',     hand:'eliminated',   score: 64,  coins: 0, trains: 0},
  ];
  return (
    <div className="dr-art dr-pad-m" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">Player Card · Scoreboard</div>
      <div className="dr-title">Identity = color, position, score.</div>
      <p className="dr-sub">Every player gets one of eight line identities. The card carries it through active, waiting, winning, and eliminated states.</p>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>States</h3>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:14}}>
        {players.map(P => <PlayerCard key={P.name} {...P}/>)}
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Compact scoreboard</h3>
      <div className="dr-panel">
        <div className="dr-panel__head">
          <div className="dr-panel__title">Standings · Round 6</div>
          <span className="dr-panel__sub">Net + race</span>
          <span className="dr-badge" style={{marginLeft:'auto'}}>Live</span>
        </div>
        <table style={{width:'100%', borderCollapse:'collapse', fontSize:13}}>
          <thead>
            <tr style={{textAlign:'left', color:'var(--ink-3)'}}>
              <th style={{padding:'10px 18px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase'}}>#</th>
              <th style={{padding:'10px 8px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase'}}>Line · Player</th>
              <th style={{padding:'10px 8px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase'}}>Net</th>
              <th style={{padding:'10px 8px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase'}}>Race</th>
              <th style={{padding:'10px 18px', fontWeight:500, fontSize:11, letterSpacing:'.08em', textTransform:'uppercase', textAlign:'right'}}>Total</th>
            </tr>
          </thead>
          <tbody>
            {players.slice().sort((a,b)=>b.score-a.score).map((P,i) => (
              <tr key={P.name} style={{borderTop:'1px solid var(--rule-soft)'}}>
                <td className="mono" style={{padding:'12px 18px', color:'var(--ink-3)'}}>0{i+1}</td>
                <td style={{padding:'12px 8px'}}>
                  <div className="row ai-c gap-10">
                    <span style={{width:10, height:10, borderRadius:'50%', background:`var(--p${P.p})`}}/>
                    <span style={{fontWeight:500}}>{P.name}</span>
                    <span className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em'}}>S{P.p}</span>
                  </div>
                </td>
                <td className="mono tnum" style={{padding:'12px 8px', color:'var(--ink-1)'}}>{Math.round(P.score*0.6)}</td>
                <td className="mono tnum" style={{padding:'12px 8px', color:'var(--ink-1)'}}>{Math.round(P.score*0.4)}</td>
                <td className="mono tnum" style={{padding:'12px 18px', textAlign:'right', fontWeight:600, fontSize:15, color:'var(--ink)'}}>{P.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PlayerCard({p, name, state, hand, score, coins, trains}) {
  const stateClass = state === 'active' ? 'is-active' : state === 'out' ? 'is-out' : state === 'winner' ? 'is-winner' : '';
  return (
    <div className={`dr-player ${stateClass}`} style={{'--c':`var(--p${p})`}}>
      <div className="avatar">{name.slice(0,2).toUpperCase()}</div>
      <div>
        <div className="name">{name}</div>
        <div className="meta">
          <span>Line S{p}</span>
          <span style={{margin:'0 6px'}}>·</span>
          <span>{coins} coin</span>
          <span style={{margin:'0 6px'}}>·</span>
          <span>{trains} track</span>
        </div>
      </div>
      <div style={{textAlign:'right'}}>
        <div className="score">{score}<span className="unit">pts</span></div>
        <div className="mono" style={{fontSize:10, color: state==='active' ? `var(--p${p})` : 'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase', marginTop:2, fontWeight:600}}>
          {state==='active' ? '● PLAYING · '+hand : state==='winner' ? '★ WINNER' : state==='out' ? hand : hand.toUpperCase()}
        </div>
      </div>
    </div>
  );
}
window.PlayerCard = PlayerCard;
window.PlayerCardsArtboard = PlayerCardsArtboard;
window.ComponentsArtboard = ComponentsArtboard;

// ============================================================
// HUD & OVERLAYS ARTBOARD
// ============================================================
function HudArtboard() {
  return (
    <div className="dr-art dr-pad-m" style={{overflow:'auto'}}>
      <div className="dr-eyebrow">HUD &amp; Overlays</div>
      <div className="dr-title">In‑map chrome.</div>
      <p className="dr-sub">Floats over the board. Stays out of the way until the player needs it; absorbs the active player's color so identity is unmistakable.</p>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Turn bar</h3>
      <div className="dr-panel" style={{padding:'40px', background:'var(--paper)'}}>
        <div className="row jc-c">
          <div className="dr-hud" style={{position:'static', transform:'none', '--c':'var(--p2)'}}>
            <span className="lineish"/>
            <span>Lukas · S2</span>
            <span className="divider"/>
            <span className="turn">Network · 2 of 5 left</span>
            <span className="divider"/>
            <button className="dr-btn dr-btn--sm" style={{background:'var(--paper)', color:'var(--ink)'}}><Pause/></button>
            <button className="dr-btn dr-btn--sm" style={{background:'var(--p3)', color:'#fff'}}>End turn</button>
          </div>
        </div>
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Engine die</h3>
      <div className="dr-panel" style={{padding:'40px', display:'flex', justifyContent:'center', gap:18}}>
        {[1,2,3,4,5,6].map(n => <Die key={n} value={n}/>)}
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Map overlays</h3>
      <div className="dr-panel" style={{padding:'24px', background:'var(--surface)'}}>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:14}}>
          <Overlay title="Cost preview" body="Aschberg → Lichtenau" foot="3 coins · 2 turns" tone="warn"/>
          <Overlay title="Race objective" body="Connect any 4 capitals" foot="2 / 4 reached" tone="info"/>
          <Overlay title="Last action" body="Mira laid 2 segments" foot="Round 4 · 00:12 ago" tone="neutral"/>
        </div>
      </div>

      <h3 style={{fontFamily:'var(--font-display)', fontWeight:600, fontSize:14, color:'var(--ink-2)', textTransform:'uppercase', letterSpacing:'.1em', margin:'32px 0 14px'}}>Action bar (mobile)</h3>
      <div className="dr-panel" style={{padding:'24px', display:'flex', justifyContent:'center', background:'var(--paper)'}}>
        <div style={{
          width:380, background:'var(--surface)', borderRadius:20, boxShadow:'var(--sh-2)',
          border:'1px solid var(--rule)', padding:'14px 18px',
          display:'grid', gridTemplateColumns:'1fr auto', alignItems:'center', gap:14
        }}>
          <div>
            <div className="mono" style={{fontSize:10, color:'var(--ink-3)', letterSpacing:'.08em', textTransform:'uppercase'}}>TAP A HEX</div>
            <div style={{fontWeight:600, fontSize:15, color:'var(--ink)', marginTop:2}}>Lay segment 2 of 5</div>
          </div>
          <div className="row gap-8">
            <button className="dr-iconbtn"><Minus/></button>
            <button className="dr-btn dr-btn--sm">Confirm</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Die({value=3}) {
  const pips = {
    1:[4],
    2:[0,8],
    3:[0,4,8],
    4:[0,2,6,8],
    5:[0,2,4,6,8],
    6:[0,2,3,5,6,8],
  }[value] || [];
  return (
    <div className="dr-die">
      <div className="pips">
        {Array.from({length:9}).map((_,i) => (
          <div key={i} className={`pip ${pips.includes(i)?'':'off'}`}/>
        ))}
      </div>
    </div>
  );
}
window.Die = Die;

function Overlay({title, body, foot, tone='neutral'}) {
  const c = tone === 'warn' ? 'var(--p4)' : tone === 'info' ? 'var(--p2)' : 'var(--ink)';
  return (
    <div style={{
      background:'var(--surface)',
      border:'1px solid var(--rule)',
      borderRadius: 12,
      padding: '14px 16px',
      position:'relative',
      overflow:'hidden',
    }}>
      <span style={{position:'absolute', left:0, top:0, bottom:0, width:3, background:c}}/>
      <div className="dr-eyebrow">{title}</div>
      <div style={{fontWeight:600, fontSize:15, color:'var(--ink)', margin:'6px 0 6px'}}>{body}</div>
      <div className="mono" style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'.05em'}}>{foot}</div>
    </div>
  );
}
window.HudArtboard = HudArtboard;
