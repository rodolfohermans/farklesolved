
/* ============================== DP TABLE ============================== */
const DP = JSON.parse(document.getElementById('dp-data').textContent);
const STEP = DP.STEP;
function vLookup(k, T){
  const idx = Math.min(Math.floor(T / STEP), DP.V[k].length - 1);
  return DP.V[k][idx];
}
function shouldContinue(k, T){
  return vLookup(k, T) > T + 1e-6;
}

/* ============================== SCORING ENGINE (ported from farkle_kcd.py) ============================== */
const THREE_KIND_VALUE = {1:1000, 2:200, 3:300, 4:400, 5:500, 6:600};
function groupValue(face, count){ return THREE_KIND_VALUE[face] * Math.pow(2, count - 3); }

const NUM_WORD = {0:'',1:'un',2:'dos',3:'tres',4:'cuatro',5:'cinco',6:'seis'};
const NUM_WORD_REV = {un:1, dos:2, tres:3, cuatro:4, cinco:5, seis:6};

// Splits a chosen action's label back into its separate scoring groups (e.g.
// "escalera 1–5 + un 5" -> the straight, worth 500, and a separate lone 5,
// worth 50), so Phase 3e can show them as distinct chips rather than merging
// a straight-plus-leftover bank into a single combined total. Mirrors the
// same per-face value rules used to build the label in the first place
// (faceOptions/genericValueLabel), so this never needs its own scoring logic.
function decomposeAction(action){
  if (!action.label) return [{label: action.label, val: action.val}];
  return action.label.split(' + ').map(part => {
    if (part === 'escalera 1–5') return {label: part, val: 500};
    if (part === 'escalera 2–6') return {label: part, val: 750};
    if (part === 'escalera completa 1–6') return {label: part, val: 1500};
    const m = part.match(/^(\w+) (\d)$/);
    if (!m) return {label: part, val: action.val};
    const count = NUM_WORD_REV[m[1]], face = Number(m[2]);
    const single = face === 1 ? 100 : (face === 5 ? 50 : null);
    const val = single !== null ? (count < 3 ? single * count : groupValue(face, count)) : groupValue(face, count);
    return {label: part, val};
  });
}

function renderBankedGroups(){
  const render1 = (groups, elId) => {
    const el = document.getElementById(elId);
    if (!el) return;
    el.innerHTML = groups.map(g => `<span class="banked-chip">${g.label} (+${g.val})</span>`).join('');
  };
  render1(state.bankedGroups.player, 'playerBankedGroups');
  render1(state.bankedGroups.opponent, 'oppBankedGroups');
}

// returns list of [bankedCount, value, label]
function faceOptions(face, count){
  const opts = [[0,0,'']];
  if (face === 1 || face === 5){
    const single = face === 1 ? 100 : 50;
    for (let b=1; b<=count; b++){
      const val = b < 3 ? single*b : groupValue(face,b);
      opts.push([b, val, `${NUM_WORD[b]} ${face}`]);
    }
  } else {
    for (let b=3; b<=count; b++){
      opts.push([b, groupValue(face,b), `${NUM_WORD[b]} ${face}`]);
    }
  }
  return opts;
}

function combosSums(optionLists){
  let combos = [[0,0,'']];
  for (const opts of optionLists){
    const next = [];
    for (const [bc,val,lab] of combos){
      for (const [bc2,val2,lab2] of opts){
        const label = lab && lab2 ? `${lab} + ${lab2}` : (lab || lab2);
        next.push([bc+bc2, val+val2, label]);
      }
    }
    combos = next;
  }
  // dedupe by (bc,val), keep first label seen
  const seen = new Map();
  for (const [bc,val,lab] of combos){
    const key = bc+','+val;
    if (!seen.has(key)) seen.set(key, {bc, val, label: lab});
  }
  return [...seen.values()];
}

function enumerateActions(dice){
  const counts = {1:0,2:0,3:0,4:0,5:0,6:0};
  for (const d of dice) counts[d]++;
  const k = dice.length;

  const perFace = [1,2,3,4,5,6].map(f => faceOptions(f, counts[f]));
  const actionMap = new Map(); // key "bc,val" -> label
  for (const {bc,val,label} of combosSums(perFace)){
    if (val > 0) actionMap.set(bc+','+val, label);
  }

  function leftoverCounts(exclude){
    const c = {...counts};
    for (const f of exclude) c[f] -= 1;
    return c;
  }
  const has = f => counts[f] >= 1;

  if ([1,2,3,4,5].every(has)){
    const lc = leftoverCounts([1,2,3,4,5]);
    const lopts = [1,2,3,4,5,6].map(f => faceOptions(f, lc[f]));
    for (const {bc,val,label} of combosSums(lopts)){
      const key = (5+bc)+','+(500+val);
      const lab = 'escalera 1–5' + (label ? ' + ' + label : '');
      if (!actionMap.has(key)) actionMap.set(key, lab);
    }
  }
  if ([2,3,4,5,6].every(has)){
    const lc = leftoverCounts([2,3,4,5,6]);
    const lopts = [1,2,3,4,5,6].map(f => faceOptions(f, lc[f]));
    for (const {bc,val,label} of combosSums(lopts)){
      const key = (5+bc)+','+(750+val);
      const lab = 'escalera 2–6' + (label ? ' + ' + label : '');
      if (!actionMap.has(key)) actionMap.set(key, lab);
    }
  }
  if (k === 6){
    const sorted = [...dice].sort((a,b)=>a-b).join(',');
    if (sorted === '1,2,3,4,5,6'){
      actionMap.set('6,1500', 'escalera completa 1–6');
    }
  }
  actionMap.delete('0,0');

  const actions = [...actionMap.entries()].map(([key,label]) => {
    const [bc,val] = key.split(',').map(Number);
    return {bc, val, label};
  });
  return {isBust: actions.length === 0, actions};
}

/* ---- Manual dice-selection validation: is THIS exact chosen subset of the
   roll a legal score, and what's it worth + what does it look like? Mirrors
   the same per-face rules as enumerateActions, applied to the dice the
   player actually clicked rather than a preset (bc,val) pair. ---- */
function countsOf(diceValues){
  const c = {1:0,2:0,3:0,4:0,5:0,6:0};
  for (const d of diceValues) c[d]++;
  return c;
}

// value+label for a set of counts with NO straight bonus, or null if illegal
// (a nonzero count of 2/3/4/6 below 3 can never be banked on its own).
function genericValueLabel(counts){
  let val = 0;
  const parts = [];
  for (let f=1; f<=6; f++){
    const c = counts[f];
    if (c === 0) continue;
    if (f === 1 || f === 5){
      const single = f === 1 ? 100 : 50;
      val += c < 3 ? single*c : groupValue(f,c);
    } else {
      if (c < 3) return null;
      val += groupValue(f,c);
    }
    parts.push(`${NUM_WORD[c]} ${f}`);
  }
  return {val, label: parts.join(' + ')};
}

function evaluateSelection(selectedCounts){
  const total = Object.values(selectedCounts).reduce((a,b)=>a+b,0);
  if (total === 0) return {valid:false, val:0, label:''};

  if ([1,2,3,4,5,6].every(f => selectedCounts[f] === 1)){
    return {valid:true, val:1500, label:'escalera completa 1–6'};
  }
  const tryStraight = (faces, bonus, name) => {
    if (!faces.every(f => selectedCounts[f] >= 1)) return null;
    const leftover = {...selectedCounts};
    for (const f of faces) leftover[f] -= 1;
    const rest = genericValueLabel(leftover);
    if (rest === null) return null;
    return {valid:true, val: bonus + rest.val, label: name + (rest.label ? ' + ' + rest.label : '')};
  };
  const s15 = tryStraight([1,2,3,4,5], 500, 'escalera 1–5');
  if (s15) return s15;
  const s26 = tryStraight([2,3,4,5,6], 750, 'escalera 2–6');
  if (s26) return s26;

  const generic = genericValueLabel(selectedCounts);
  if (generic !== null && generic.val > 0) return {valid:true, ...generic};
  return {valid:false, val:0, label:''};
}

function rollDice(k){
  const out = [];
  for (let i=0;i<k;i++) out.push(1 + Math.floor(Math.random()*6));
  return out;
}

const DIE_GLYPH = {1:'⚀', 2:'⚁', 3:'⚂', 4:'⚃', 5:'⚄', 6:'⚅'};
function diceGlyphs(dice){ return [...dice].sort((a,b) => a - b).map(d => DIE_GLYPH[d]).join(' '); }

function bestAction(k, T, actions){
  let best = null, bestV = -1;
  for (const a of actions){
    const kp = a.bc === k ? 6 : k - a.bc;
    const v = vLookup(kp, T + a.val);
    if (v > bestV){ bestV = v; best = {...a, kp, v}; }
  }
  return best;
}

/* ============================== OPPONENT POLICIES ============================== */
// Each policy plays one full turn and returns points banked (0 if bust).
function playOpponentTurn(strategy){
  let k = 6, T = 0;
  const decisions = [];
  const oppPreTurnScore = state.scores.opponent;
  while (true){
    const kBefore = k, TBefore = T;
    const dice = rollDice(k);
    const {isBust, actions} = enumerateActions(dice);
    if (isBust){
      return {points: 0, decisions, bustDice: dice};
    }
    let chosen, cont;
    if (strategy === 'optimal'){
      // Win-aware action choice: if any available action reaches the match
      // target outright this roll, take it (any one that reaches it is
      // equally correct, since the turn ends either way) instead of asking
      // bestAction for the race-blind single-turn-optimal pick. Without this,
      // the Scholar could decline a winning move in favor of a higher-EV
      // action and bust a turn it could have already banked as a win. Mirrors
      // the winningAction concept in showReview()'s own grading logic.
      const winningAction = actions.find(a => oppPreTurnScore + T + a.val >= state.target);
      if (winningAction){
        const kp = winningAction.bc === k ? 6 : k - winningAction.bc;
        chosen = winningAction;
        T += chosen.val; k = kp;
        cont = false;
      } else {
        chosen = bestAction(k, T, actions);
        T += chosen.val; k = chosen.kp;
        cont = shouldContinue(k, T);
      }
    } else if (strategy === 'thresholds'){
      chosen = actions.reduce((a,b)=> b.val > a.val ? b : a);
      const kp = chosen.bc === k ? 6 : k - chosen.bc;
      T += chosen.val; k = kp;
      cont = T <= DP.thresholds[k];
    } else if (strategy === 'stop3' || strategy === 'stop2'){
      chosen = actions.reduce((a,b)=> b.val > a.val ? b : a);
      const kp = chosen.bc === k ? 6 : k - chosen.bc;
      T += chosen.val; k = kp;
      const minDice = strategy === 'stop3' ? 3 : 2;
      cont = k >= minDice;
    } else { // firstscore
      chosen = actions.reduce((a,b)=> b.val > a.val ? b : a);
      const kp = chosen.bc === k ? 6 : k - chosen.bc;
      T += chosen.val; k = kp;
      cont = false;
    }
    // Win-aware override, applied regardless of strategy: none of these
    // heuristics know about the match target, so without this check even
    // "optimal" would keep rolling (risking the whole turn) after already
    // banking enough to win outright. Continuing past a secured win isn't a
    // meaningful feature of any of these strategies -- just irrational.
    if (cont && oppPreTurnScore + T >= state.target){
      cont = false;
    }
    decisions.push({kBefore, TBefore, dice, actionsAvailable: actions, actionChosen: chosen, continued: cont, resultingK: k, resultingT: T});
    if (!cont){
      return {points: T, decisions};
    }
  }
}

/* ============================== GAME STATE ============================== */
let state = null;

function startMatch(){
  const {target, oppStrategy} = readSettingsFromControls();
  state = {
    target, oppStrategy,
    scores: {player:0, opponent:0},
    turnOwner: 'player',
    k: 6, T: 0,
    pendingAction: null,
    decisions: [], // this turn's recorded player decisions
    bankedGroups: {player: [], opponent: []}, // this turn's banked dice, grouped by scoring choice
    gameOver: false,
  };
  document.getElementById('reviewArea').innerHTML = '';
  document.getElementById('bannerArea').innerHTML = '';
  document.getElementById('targetLine').textContent = `Carrera a ${target} puntos`;
  document.getElementById('oppWho').textContent = CHARACTER_NAME[oppStrategy];
  updateCharacterLayer(oppStrategy);
  document.getElementById('startBtn').textContent = 'Reiniciar partida';
  beginPlayerRoll_UI();
  render();
}

function isGameActive(){
  return state !== null && !state.gameOver;
}

function readSettingsFromControls(){
  const targetSel = document.getElementById('targetSelect').value;
  const target = targetSel === 'custom'
    ? Math.max(300, Math.round(Number(document.getElementById('customTarget').value)/50)*50)
    : Number(targetSel);
  return {
    target,
    oppStrategy: document.getElementById('oppSelect').value,
  };
}

function syncControlsFromState(){
  if (!state) return;
  const targetSelect = document.getElementById('targetSelect');
  const presetValues = Array.from(targetSelect.options).map(o => o.value).filter(v => v !== 'custom');
  if (presetValues.includes(String(state.target))){
    targetSelect.value = String(state.target);
    document.getElementById('customTarget').style.display = 'none';
  } else {
    targetSelect.value = 'custom';
    document.getElementById('customTarget').value = state.target;
    document.getElementById('customTarget').style.display = 'block';
  }
  document.getElementById('oppSelect').value = state.oppStrategy;
}

function renderIdle(){
  const {target, oppStrategy} = readSettingsFromControls();
  document.getElementById('playerScore').textContent = 0;
  document.getElementById('oppScore').textContent = 0;
  document.getElementById('playerTargetVal').textContent = target;
  document.getElementById('oppTargetVal').textContent = target;
  document.getElementById('playerRound').textContent = 0;
  document.getElementById('oppRound').textContent = 0;
  document.getElementById('playerSelected').textContent = 0;
  document.getElementById('oppSelected').textContent = 0;
  document.getElementById('oppWho').textContent = CHARACTER_NAME[oppStrategy];
  document.getElementById('characterLayer').classList.remove('visible'); // deferred to startMatch(): avoid loading a portrait before a match actually begins
  document.getElementById('targetLine').textContent = `Carrera a ${target} puntos`;
  document.getElementById('diceRow').innerHTML = '';
  setCupsRollable(false);
  document.getElementById('diceLeft').textContent = 6;
  document.getElementById('turnTotal').textContent = 0;
  document.getElementById('turnWho').textContent = 'Pulsa "Empezar partida" arriba para comenzar';
  document.getElementById('controls').innerHTML = '';
  document.getElementById('endgameHint').style.display = 'none';
  document.getElementById('turnLog').innerHTML = '';
  document.getElementById('reviewArea').innerHTML = '';
  document.getElementById('bannerArea').innerHTML = '';
  document.getElementById('playerBankedGroups').innerHTML = '';
  document.getElementById('oppBankedGroups').innerHTML = '';
}

// Changing target/opponent mid-match resets the match; confirm first.
function onSettingControlChanged(){
  if (isGameActive()){
    const ok = confirm('Esto reiniciará la partida en curso. ¿Continuar?');
    if (!ok){
      syncControlsFromState();
      return;
    }
    startMatch();
  } else {
    renderIdle();
  }
}

function render(){
  document.getElementById('playerScore').textContent = state.scores.player;
  document.getElementById('oppScore').textContent = state.scores.opponent;
  document.getElementById('playerTargetVal').textContent = state.target;
  document.getElementById('oppTargetVal').textContent = state.target;
  document.getElementById('playerRound').textContent = state.turnOwner === 'player' ? state.T : 0;
  document.getElementById('oppRound').textContent = 0; // opponent turns resolve instantly, no live round to show
  document.getElementById('playerBox').classList.toggle('active', state.turnOwner==='player');
  document.getElementById('oppBox').classList.toggle('active', state.turnOwner==='opponent');
  document.getElementById('diceLeft').textContent = state.k;
  document.getElementById('turnTotal').textContent = state.T;
  document.getElementById('turnWho').textContent = state.turnOwner==='player' ? 'Tu turno' : "Turno del oponente";

  const hintEl = document.getElementById('endgameHint');
  const gapYou = state.target - (state.scores.player + state.T);
  const gapOpp = state.target - state.scores.opponent;
  if (state.turnOwner==='player' && (gapYou <= 1000 || gapOpp <= 1000)){
    hintEl.style.display = 'block';
    hintEl.textContent = '⚠ Zona de final de partida (tú o tu oponente a menos de ~1000 del objetivo): el consejo exacto de abajo es ciego a la carrera. El juego óptimo que sí tiene en cuenta la carrera suele decir que sigas tirando a por la victoria exacta, salvo cuando vas ganando y te quedan entre 1 y 3 dados, donde lo correcto suele ser guardar pronto. Consulta el informe para la tabla exacta.';
  } else {
    hintEl.style.display = 'none';
  }
}

function logLine(text){
  const el = document.getElementById('turnLog');
  const div = document.createElement('div');
  div.textContent = text;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function clearLog(){ document.getElementById('turnLog').innerHTML = ''; }

{{DICE_SPRITES_JS}}

let diceJitter = [];
let diceVariant = [];

function renderDice(dice, selectable){
  const row = document.getElementById('diceRow');
  row.innerHTML = '';
  row.classList.toggle('opponent-row', !selectable && state.turnOwner === 'opponent');
  if (diceJitter.length !== dice.length){
    diceJitter = dice.map(() => ({
      rot: (Math.random() * 16 - 8).toFixed(1),
      dy: (Math.random() * 8 - 4).toFixed(1),
    }));
    diceVariant = dice.map(d => Math.floor(Math.random() * DICE_SPRITES[d].length));
  }

  // Two-row hex packing: top row gets the larger (or equal) half, bottom
  // row is offset by half a die-width so the rows nestle tightly together.
  const n = dice.length;
  const row1n = Math.ceil(n / 2);
  const subRow1 = document.createElement('div');
  subRow1.className = 'dice-subrow';
  const subRow2 = document.createElement('div');
  subRow2.className = 'dice-subrow dice-subrow-offset';

  dice.forEach((d, idx) => {
    const div = document.createElement('div');
    div.className = 'die' + (selectable ? ' selectable' : '');
    const isHeld = selectable && state.selectedSet.has(idx);
    if (isHeld) div.classList.add('held');
        div.style.backgroundImage = 'url(' + DICE_SPRITES[d][diceVariant[idx] % DICE_SPRITES[d].length] + ')';
    const j = diceJitter[idx];
    const heldLift = isHeld ? -5 : 0;
    div.style.transform = `rotate(${j.rot}deg) translateY(${(+j.dy) + heldLift}px)`;
    if (selectable){
      const toggle = () => {
        if (state.selectedSet.has(idx)) state.selectedSet.delete(idx);
        else state.selectedSet.add(idx);
        renderDice(dice, true);
        updateSelectionUI();
      };
      div.onclick = toggle;
      div.setAttribute('role', 'button');
      div.setAttribute('tabindex', '0');
      div.setAttribute('aria-pressed', isHeld ? 'true' : 'false');
      div.setAttribute('aria-label', `Dado mostrando ${d}${isHeld ? ', retenido' : ''}`);
      div.onkeydown = (e) => {
        if (e.key === 'Enter' || e.key === ' '){
          e.preventDefault();
          toggle();
        }
      };
    }
    (idx < row1n ? subRow1 : subRow2).appendChild(div);
  });

  row.appendChild(subRow1);
  if (n > row1n) row.appendChild(subRow2);
}

function setCupsRollable(on){
  const cup = document.getElementById('cupRoll');
  if (!cup) return;
  cup.classList.toggle('rollable', on);
  cup.onclick = on ? doPlayerRoll : null;
}

function beginPlayerRoll_UI(){
  clearLog();
  diceJitter = [];
  state.bankedGroups.player = [];
  renderBankedGroups();
  document.getElementById('diceRow').innerHTML = '';
  const controls = document.getElementById('controls');
  controls.innerHTML = '';
  const btn = document.createElement('button');
  btn.textContent = `Tirar ${state.k} dados`;
  btn.onclick = doPlayerRoll;
  controls.appendChild(btn);
  setCupsRollable(true);
}

function doPlayerRoll(){
  setCupsRollable(false);
  const dice = rollDice(state.k);
  state.currentDice = dice;
  state.selectedSet = new Set();
  logLine(`Tiras ${diceGlyphs(dice)}`);
  const {isBust, actions} = enumerateActions(dice);
  if (isBust){
    renderDice(dice, false);
    logLine(`TE PASASTE: pierdes ${state.T} puntos guardados este turno.`);
    finishPlayerTurn(0);
    return;
  }
  state.currentActions = actions;
  renderDice(dice, true);

  const controls = document.getElementById('controls');
  controls.innerHTML = '<div class="muted" style="margin-bottom:6px;">Haz clic en los dados que quieras guardar y confirma.</div>';
  const statusDiv = document.createElement('div');
  statusDiv.className = 'select-status';
  statusDiv.id = 'selectStatus';
  controls.appendChild(statusDiv);
  const confirmBtn = document.createElement('button');
  confirmBtn.id = 'confirmSelectionBtn';
  confirmBtn.textContent = 'Confirmar selección';
  confirmBtn.disabled = true;
  confirmBtn.onclick = confirmSelection;
  controls.appendChild(confirmBtn);

  const refDiv = document.createElement('div');
  refDiv.className = 'legal-ref';
  refDiv.textContent = 'Combinaciones válidas de esta tirada: ' + actions.map(a => `${a.label} (+${a.val})`).join('  ·  ');
  controls.appendChild(refDiv);

  updateSelectionUI();
}

// Non-1/5 faces held in a group smaller than 3 can never score, regardless of
// whatever else is held alongside them (a straight only ever consumes exactly
// one of each face, so any such face showing count 1 or 2 is always dead).
function deadFaces(counts){
  const dead = [];
  for (let f=2; f<=6; f++){
    if (f === 5) continue;
    if (counts[f] === 1 || counts[f] === 2) dead.push({face:f, count:counts[f]});
  }
  return dead;
}

function updateSelectionUI(){
  const selectedCounts = countsOf([...state.selectedSet].map(i => state.currentDice[i]));
  const result = evaluateSelection(selectedCounts);
  const statusEl = document.getElementById('selectStatus');
  const btn = document.getElementById('confirmSelectionBtn');
  if (!statusEl || !btn) return;
  document.getElementById('playerSelected').textContent = (state.selectedSet.size > 0 && result.valid) ? result.val : 0;
  if (state.selectedSet.size === 0){
    statusEl.textContent = 'Aún no has guardado ningún dado.';
    statusEl.className = 'select-status';
    btn.disabled = true;
  } else if (result.valid){
    statusEl.textContent = `Guardando ${result.label}: vale ${result.val} puntos. Válido.`;
    statusEl.className = 'select-status valid';
    btn.disabled = false;
    state.pendingSelection = {bc: state.selectedSet.size, val: result.val, label: result.label};
  } else {
    const dead = deadFaces(selectedCounts);
    if (dead.length > 0){
      const parts = dead.map(d => `${d.count===1?'un':'dos'} ${d.face}`).join(' y ');
      const singular = dead.length === 1 && dead[0].count === 1;
      statusEl.textContent = `No es válido: ${parts} no ${singular?"cuenta":"cuentan"} por separado, un 2, 3, 4 o 6 solo puntúa en un grupo de tres o más. Deselecciónalo${singular?"":"s"}, o guarda al menos tres de esa cara.`;
    } else {
      statusEl.textContent = `Esta selección no puntúa: un dado guardado debe ser un 1, un 5, parte de un trío o más del mismo valor, o una escalera completa (puede que te falte un dado para completarla).`;
    }
    statusEl.className = 'select-status invalid';
    btn.disabled = true;
  }
}

function confirmSelection(){
  const a = state.pendingSelection;
  const kBefore = state.k, TBefore = state.T;
  const kp = a.bc === kBefore ? 6 : kBefore - a.bc;
  const TAfter = TBefore + a.val;
  state.k = kp; state.T = TAfter;
  document.getElementById('playerSelected').textContent = 0;
  logLine(`Guardas ${a.label} (+${a.val}) → ${kp} dados restantes, total del turno ${TAfter}.`);
  state.bankedGroups.player.push(...decomposeAction(a));
  renderBankedGroups();
  render();

  const controls = document.getElementById('controls');
  controls.innerHTML = '<div class="muted" style="margin-bottom:6px;">¿Sigues tirando o guardas tus puntos?</div>';
  const rollMoreBtn = document.createElement('button');
  rollMoreBtn.textContent = kp === 6 ? `Seguir (¡dados calientes! tira los 6)` : `Seguir tirando (${kp} dados)`;
  rollMoreBtn.onclick = () => recordDecision(kBefore, TBefore, state.currentActions, a, true);
  const bankBtn = document.createElement('button');
  bankBtn.className = 'secondary';
  bankBtn.textContent = `Guardar y terminar turno (+${TAfter} puntos en total)`;
  bankBtn.onclick = () => recordDecision(kBefore, TBefore, state.currentActions, a, false);
  controls.appendChild(rollMoreBtn);
  controls.appendChild(bankBtn);
}

function recordDecision(kBefore, TBefore, actionsAvailable, actionChosen, continued){
  state.decisions.push({kBefore, TBefore, actionsAvailable, actionChosen, continued, resultingK: state.k, resultingT: state.T});
  if (continued){
    doPlayerRoll(); // nothing left to choose before rolling again, just roll
  } else {
    logLine(`Guardas el turno: +${state.T} puntos.`);
    finishPlayerTurn(state.T);
  }
}

function finishPlayerTurn(points){
  showReview(); // must run BEFORE scores.player updates: grading needs the pre-turn score to know what total would win
  state.scores.player += points;
  state.k = 6; state.T = 0;
  render();
  if (checkWin()) return;
  document.getElementById('controls').innerHTML = '';
  const btn = document.createElement('button');
  btn.textContent = 'Turno del oponente →';
  btn.onclick = runOpponentTurn;
  document.getElementById('controls').appendChild(btn);
  state.turnOwner = 'opponent';
  render();
}

const REAL_STRATEGIES = ['optimal', 'thresholds', 'stop3', 'stop2', 'firstscore'];
const CHARACTER_NAME = {
  random: 'El Bufón', optimal: 'El Erudito', thresholds: 'El Intendente',
  stop3: 'El Vigía', stop2: 'El Borracho', firstscore: 'El Sacerdote',
};
const CHARACTER_PORTRAIT = {
  random: 'jester', optimal: 'scholar', thresholds: 'quartermaster',
  stop3: 'watchman', stop2: 'drunk', firstscore: 'priest',
};
function updateCharacterLayer(oppStrategy){
  const el = document.getElementById('characterLayer');
  if (!el) return;
  const name = CHARACTER_PORTRAIT[oppStrategy];
  if (!name) return;
  el.style.backgroundImage = `url('assets/characters/${name}.png')`;
  el.classList.add('visible');
}

// In-memory only (never localStorage/sessionStorage, per this site's no-storage
// privacy commitment): "skip animation" is remembered for the rest of this page
// load, but resets on reload like everything else here.
let skipOpponentAnimation = false;
let opponentTurnSkipRequested = false;
function sleep(ms){ return new Promise(resolve => setTimeout(resolve, ms)); }

async function runOpponentTurn(){
  if (state.turnInProgress) return;
  document.getElementById('controls').innerHTML = '';
  clearLog();
  document.getElementById('diceRow').innerHTML = '';
  state.turnInProgress = true;
  opponentTurnSkipRequested = false;
  state.bankedGroups.opponent = [];
  renderBankedGroups();

  const controls = document.getElementById('controls');
  if (!skipOpponentAnimation){
    const skipBtn = document.createElement('button');
    skipBtn.className = 'secondary';
    skipBtn.textContent = 'Saltar animación';
    skipBtn.onclick = () => { opponentTurnSkipRequested = true; skipOpponentAnimation = true; };
    controls.appendChild(skipBtn);
  }
  const pace = async () => {
    if (opponentTurnSkipRequested || skipOpponentAnimation) return;
    await sleep(1500);
  };

  const strategy = state.oppStrategy === 'random'
    ? REAL_STRATEGIES[Math.floor(Math.random() * REAL_STRATEGIES.length)]
    : state.oppStrategy;
  if (state.oppStrategy === 'random') logLine(`Esta noche el Bufón juega como ${CHARACTER_NAME[strategy]}.`);
  const {points, decisions, bustDice} = playOpponentTurn(strategy);

  for (const d of decisions){
    renderDice(d.dice, false);
    logLine(`El oponente tiró ${diceGlyphs(d.dice)}`);
    await pace();
    logLine(`El oponente guarda ${d.actionChosen.label} (+${d.actionChosen.val}) → ${d.resultingK} dados restantes, total del turno ${d.resultingT}`);
    state.bankedGroups.opponent.push(...decomposeAction(d.actionChosen));
    renderBankedGroups();
    await pace();
  }
  if (bustDice){
    renderDice(bustDice, false);
    logLine(`El oponente tiró ${diceGlyphs(bustDice)}`);
    await pace();
  }
  if (points > 0){
    logLine(`El oponente guarda el turno: +${points} puntos.`);
  } else {
    logLine(`EL OPONENTE SE PASÓ: su turno termina sin guardar nada.`);
  }
  // Must run before scores.opponent updates: grading needs the pre-turn score.
  renderReview(decisions, state.scores.opponent, state.scores.player, state.target, OPPONENT_SUBJECT);
  state.scores.opponent += points;
  state.turnInProgress = false;
  render();
  if (checkWin()) return;
  // Don't auto-advance into your turn (and don't clear this log) until you've
  // actually seen what the opponent did -- beginPlayerRoll_UI() clears the log,
  // so it must wait for an explicit click, same as the player->opponent handoff.
  state.turnOwner = 'player';
  render();
  controls.innerHTML = '';
  const btn = document.createElement('button');
  btn.textContent = 'Tu turno →';
  btn.onclick = () => {
    state.decisions = [];
    beginPlayerRoll_UI();
  };
  controls.appendChild(btn);
}

function checkWin(){
  if (state.scores.player >= state.target){
    endGame('player');
    return true;
  }
  if (state.scores.opponent >= state.target){
    endGame('opponent');
    return true;
  }
  return false;
}

function endGame(winner){
  state.gameOver = true;
  document.getElementById('controls').innerHTML = '';
  const el = document.getElementById('bannerArea');
  if (winner === 'player'){
    el.innerHTML = `<div class="banner win">¡Ganas! ${state.scores.player} – ${state.scores.opponent}</div>`;
  } else {
    el.innerHTML = `<div class="banner lose">Gana el oponente. ${state.scores.opponent} – ${state.scores.player}</div>`;
  }
}

/* ============================== TURN-END REVIEW (grading vs exact DP) ============================== */
function describeAction(a, kBefore){
  const kp = a.bc === kBefore ? 6 : kBefore - a.bc;
  return `${a.label} (+${a.val}) → ${kp} dados restantes`;
}

const PLAYER_SUBJECT = {poss: 'tu', hadAvailable: 'tenías disponible', hadReached: 'habías', had: 'tenías', shouldHave: 'deberías haber', chose: 'elegiste'};
const OPPONENT_SUBJECT = {poss: 'su', hadAvailable: 'tenía disponible', hadReached: 'había', had: 'tenía', shouldHave: 'debería haber', chose: 'el oponente eligió'};

// Parameterized so both the player's and the opponent's turns can be graded by
// the identical logic (Phase 3b): preTurnScore/otherScore/decisions all come
// from whichever side is being reviewed, subj supplies the Spanish verb forms.
function renderReview(decisions, preTurnScore, otherScore, target, subj){
  const area = document.getElementById('reviewArea');
  if (decisions.length === 0){
    area.innerHTML = '<div class="review">El turno terminó en la primera tirada: no hay decisiones que revisar.</div>';
    return;
  }
  const reachesTarget = (T) => preTurnScore + T >= target;
  // Same "end-game zone" condition as the live hint banner: either side within
  // ~1000 of the target. The report's own exact race-aware solve shows real
  // optimal play diverges substantially from these race-blind thresholds here
  // (e.g. pushing far harder than the table says while badly behind) -- so
  // outside the hard win/lose cases above, verdicts in this zone get a caveat
  // instead of a confident right/wrong, rather than silently overclaiming.
  const endgameZone = (target - preTurnScore) <= 1000 || (target - otherScore) <= 1000;

  // actionOK/contOK are tri-state: true = correct, false = wrong, null = too
  // close to the target to confidently grade with the race-blind table (not
  // counted toward the tally either way).
  let correctCount = 0, gradedCount = 0, uncertainCount = 0;
  const rows = decisions.map((d, idx) => {
    // --- Win-aware override: reaching the match target is always correct,
    // full stop, regardless of what the race-blind EV table prefers. The
    // single-turn table has no concept of a match target at all, so without
    // this override it will (wrongly) tell you to keep pushing a win you've
    // already clinched. This override is exact, not an approximation, so it
    // always takes priority over the endgameZone caveat below. ---
    const winningAction = d.actionsAvailable.find(a => reachesTarget(d.TBefore + a.val));
    const chosenReachesTarget = reachesTarget(d.resultingT);

    let actionOK, actionHtml;
    if (winningAction){
      actionOK = chosenReachesTarget;
      if (actionOK){
        actionHtml = `<span class="tag ok">✓ mejor elección</span> esto alcanza ${subj.poss} objetivo de ${target}: nada supera ganar directamente, así que la preferencia de la tabla ciega a la carrera no importa aquí.`;
      } else {
        actionHtml = `<span class="tag no">✗ elección no óptima</span> ${subj.hadAvailable} una jugada ganadora: <i>${describeAction(winningAction, d.kBefore)}</i> habría alcanzado ${subj.poss} objetivo de ${target} directamente.`;
      }
    } else {
      const opt = bestAction(d.kBefore, d.TBefore, d.actionsAvailable);
      const chosenV = vLookup(d.resultingK, d.resultingT);
      const gap = opt.v - chosenV;
      const exactTie = Math.abs(gap) < 1e-6 || (d.actionChosen.bc === opt.bc && d.actionChosen.val === opt.val);
      const negligible = !exactTie && gap < Math.max(25, 0.02 * opt.v);
      if (exactTie){
        actionOK = true;
        actionHtml = `<span class="tag ok">✓ mejor elección</span>`;
      } else if (negligible){
        actionOK = true;
        actionHtml = `<span class="tag meh">≈ casi óptimo</span> otra elección (<i>${describeAction(opt, d.kBefore)}</i>) valía técnicamente un poco más (${opt.v.toFixed(1)} frente a ${chosenV.toFixed(1)}, una diferencia de ${gap.toFixed(1)} puntos), demasiado pequeña para importar en la práctica.`;
      } else if (endgameZone){
        actionOK = null;
        actionHtml = `<span class="tag meh">? incierto: zona de final de partida</span> la tabla ciega a la carrera prefiere <i>${describeAction(opt, d.kBefore)}</i> aquí, pero cualquiera de los dos lados está lo bastante cerca del objetivo como para que esta comparación sea poco fiable (consulta los resultados completos del informe sobre la carrera), no cuenta en el total.`;
      } else {
        actionOK = false;
        actionHtml = `<span class="tag no">✗ elección no óptima</span> lo óptimo era <i>${describeAction(opt, d.kBefore)}</i> (valor esperado ${opt.v.toFixed(0)} frente a ${chosenV.toFixed(0)}, una diferencia de ${gap.toFixed(0)} puntos)`;
      }
    }

    let contOK, contHtml;
    if (chosenReachesTarget){
      contOK = !d.continued;
      if (contOK){
        contHtml = `<span class="tag ok">✓ decisión correcta</span> guardar aquí alcanza ${subj.poss} objetivo de ${target} y gana la partida directamente.`;
      } else {
        contHtml = `<span class="tag no">✗ decisión equivocada</span> ya ${subj.hadReached} alcanzado ${subj.poss} objetivo de ${target} al guardar: seguir tirando solo arriesgaba una victoria que ya ${subj.had} asegurada.`;
      }
    } else if (endgameZone){
      const contOptimal = shouldContinue(d.resultingK, d.resultingT);
      contOK = null;
      contHtml = `<span class="tag meh">? incierto: zona de final de partida</span> la tabla ciega a la carrera dice ${contOptimal ? "seguir tirando" : "guardar"} aquí (el umbral para ${d.resultingK} dados es ${DP.thresholds[d.resultingK]}, ${subj.had} ${d.resultingT}), pero esa tabla no sabe que la partida está cerca de terminar, no cuenta en el total.`;
    } else {
      const contOptimal = shouldContinue(d.resultingK, d.resultingT);
      contOK = d.continued === contOptimal;
      if (contOK){
        contHtml = `<span class="tag ok">✓ decisión correcta</span>`;
      } else {
        contHtml = `<span class="tag no">✗ decisión equivocada</span> el juego exacto dice que ${subj.shouldHave} ${contOptimal ? "seguido tirando" : "guardado"} aquí (el umbral para ${d.resultingK} dados es ${DP.thresholds[d.resultingK]}, ${subj.had} ${d.resultingT}).`;
      }
    }

    if (actionOK === null || contOK === null){
      uncertainCount++;
    } else {
      gradedCount++;
      if (actionOK && contOK) correctCount++;
    }

    let html = `<div class="verdict-row">`;
    html += `<b>Tirada ${idx+1}</b> (${d.kBefore} dados, ${d.TBefore} guardados hasta ahora): ${subj.chose} <i>${describeAction(d.actionChosen, d.kBefore)}</i>. `;
    html += actionHtml;
    html += `<br>Después ${subj.chose} <b>${d.continued ? 'seguir tirando' : 'guardar'}</b>. `;
    html += contHtml;
    html += `</div>`;
    return html;
  }).join('');

  const cls = gradedCount === 0 ? '' : (correctCount === gradedCount ? 'good' : (correctCount === 0 ? 'bad' : ''));
  let header = `<b>${correctCount}/${gradedCount} decisiones coincidieron con el juego óptimo este turno</b>` +
    (uncertainCount > 0 ? ` (${uncertainCount} más estaban en la zona de final de partida y no se pueden evaluar con confianza: ver notas abajo).` : '.') +
    ` (Pasarse no es necesariamente un error: esto evalúa la calidad de cada decisión dado lo que sabías, no el resultado.)`;
  area.innerHTML = `<div class="review ${cls}">${header}${rows}</div>`;
}

function showReview(){
  // IMPORTANT: this must run before finishPlayerTurn adds this turn's points
  // to state.scores.player, so this is genuinely the player's PRE-turn total.
  renderReview(state.decisions, state.scores.player, state.scores.opponent, state.target, PLAYER_SUBJECT);
}

/* ============================== WIRING ============================== */
function handleStartButtonClick(){
  if (isGameActive()){
    const ok = confirm('Empezar una nueva partida reiniciará la partida en curso. ¿Continuar?');
    if (!ok) return;
  }
  startMatch();
}
document.getElementById('targetSelect').addEventListener('change', (e) => {
  document.getElementById('customTarget').style.display = e.target.value === 'custom' ? 'block' : 'none';
  onSettingControlChanged();
});
document.getElementById('customTarget').addEventListener('change', onSettingControlChanged);
document.getElementById('oppSelect').addEventListener('change', onSettingControlChanged);
document.getElementById('startBtn').addEventListener('click', handleStartButtonClick);
document.getElementById('newMatchBtn').addEventListener('click', handleStartButtonClick);

renderIdle();
