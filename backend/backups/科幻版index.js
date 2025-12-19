// IIFE 版 uibuilder
const ui = window.uibuilder
const el = id => document.getElementById(id)

// 亮度调节保护
let adjustingBrightness = false
let adjustTimer = null
const startAdjust = () => {
  adjustingBrightness = true
  clearTimeout(adjustTimer)
  adjustTimer = setTimeout(() => { adjustingBrightness = false }, 800)
}

// 阈值与报警
let thresholds = { temp: null, humid: null, eco2: null, tvoc: null, light: null }
let alertLock = false
let alertActive = false

function loadThresholds() {
  try {
    const saved = JSON.parse(localStorage.getItem('sunlamp_thresholds') || '{}')
    thresholds = { ...thresholds, ...saved }
  } catch (e) { }
  el('th-temp').value = thresholds.temp ?? ''
  el('th-humid').value = thresholds.humid ?? ''
  el('th-eco2').value = thresholds.eco2 ?? ''
  el('th-tvoc').value = thresholds.tvoc ?? ''
  el('th-light').value = thresholds.light ?? ''
}
function saveThresholds() {
  thresholds = {
    temp: parseFloat(el('th-temp').value) || null,
    humid: parseFloat(el('th-humid').value) || null,
    eco2: parseFloat(el('th-eco2').value) || null,
    tvoc: parseFloat(el('th-tvoc').value) || null,
    light: parseFloat(el('th-light').value) || null,
  }
  localStorage.setItem('sunlamp_thresholds', JSON.stringify(thresholds))
}
function setAlert(on) {
  const flag = el('alert-flag')
  if (on) { flag.textContent = '警戒'; flag.classList.remove('off'); flag.classList.add('on') }
  else { flag.textContent = '正常'; flag.classList.remove('on'); flag.classList.add('off') }
}
function checkThresholds(sensor = {}) {
  const mapping = [
    ['temp', sensor.temperature],
    ['humid', sensor.humidity],
    ['eco2', sensor.eco2],
    ['tvoc', sensor.tvoc],
    ['light', sensor.light],
  ]
  const hit = mapping.some(([k, v]) => thresholds[k] != null && v != null && v > thresholds[k])
  if (hit) {
    setAlert(true); alertActive = true
    if (!alertLock) {
      alertLock = true
      sendAnim({ type: 'warning' })
      setTimeout(() => { alertLock = false }, 10000)
    }
  } else {
    setAlert(false)
    if (alertActive) sendSet({}) // 清动画
    alertActive = false
  }
}

// 工具：设置卡片条与状态
function updateCard(id, val, maxVal = 100, warn = false) {
  el(id).textContent = val ?? '-'
  const fill = el('bar-' + id)
  if (fill) fill.style.width = (val != null ? Math.min(100, (val / maxVal) * 100) : 0) + '%'
  const tag = el('tag-' + id)
  if (tag) tag.textContent = warn ? 'HIGH' : 'NORMAL'
}

// 发送命令
function sendSet(payload) { ui.send({ topic: 'set', payload }) }
function sendAnim(payload) { ui.send({ topic: 'anim', payload }) }

// 渲染 WS2812 预览
function renderPixels(color = '#0ff') {
  const c = el('color').value || color
  const px = el('pixels')
  px.innerHTML = ''
  for (let i = 0; i < 8; i++) {
    const d = document.createElement('div'); d.className = 'pixel'; d.style.background = c; d.style.boxShadow = `0 0 12px ${c}`
    px.appendChild(d)
  }
}

// 更新显示
function renderState(state = {}) {
  const sensor = state.sensor || {}
  const net = state.network || {}
  const lamp = state.lamp || {}
  el('wifi').textContent = net.wifi || '-'
  el('mqtt').textContent = net.mqtt || '-'
  el('temp').textContent = sensor.temperature ?? '-'
  el('humid').textContent = sensor.humidity ?? '-'
  el('eco2').textContent = sensor.eco2 ?? '-'
  el('tvoc').textContent = sensor.tvoc ?? '-'
  el('light').textContent = sensor.light ?? '-'
  el('lamp').textContent = `${lamp.is_on ? 'ON' : 'OFF'} | ${lamp.brightness ?? 0}% | ${lamp.color_mode || '-'}`
  el('last-ts').textContent = state.ts ? new Date(state.ts * 1000).toLocaleTimeString() : '-'
  // 卡片条
  updateCard('temp', sensor.temperature, 50, thresholds.temp != null && sensor.temperature > thresholds.temp)
  updateCard('humid', sensor.humidity, 100, thresholds.humid != null && sensor.humidity > thresholds.humid)
  updateCard('eco2', sensor.eco2, 2000, thresholds.eco2 != null && sensor.eco2 > thresholds.eco2)
  updateCard('tvoc', sensor.tvoc, 1000, thresholds.tvoc != null && sensor.tvoc > thresholds.tvoc)
  updateCard('light', sensor.light, 8000, thresholds.light != null && sensor.light > thresholds.light)
  // 开关/亮度
  if (lamp.hasOwnProperty('is_on')) el('is_on').checked = !!lamp.is_on
  if (!adjustingBrightness && lamp.hasOwnProperty('brightness')) {
    el('brightness').value = lamp.brightness
    el('brightness-val').textContent = lamp.brightness
  }
  // 预览色
  if (lamp.color_mode === 'custom' && lamp.custom_rgb) {
    const [r, g, b] = lamp.custom_rgb; renderPixels(rgbToHex(r, g, b))
  } else {
    renderPixels(el('color').value)
  }
  // 状态胶囊
  el('pill-online').textContent = net.wifi === 'connected' && net.mqtt === 'connected' ? 'ONLINE' : 'OFFLINE'
  setAlert(alertActive)
  // 阈值检测
  checkThresholds(sensor)
}

function rgbToHex(r, g, b) { return '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('') }

// 事件绑定
el('brightness').addEventListener('input', e => {
  const v = parseInt(e.target.value, 10) || 0
  el('brightness-val').textContent = v
  startAdjust()
  sendSet({ brightness: v })
})
el('is_on').addEventListener('change', e => sendSet({ is_on: e.target.checked }))
document.querySelectorAll('.btn-group button').forEach(btn => {
  btn.addEventListener('click', () => {
    const k = parseInt(btn.dataset.ct, 10); sendSet({ color_temp_k: k })
  })
})
el('night').addEventListener('click', () => sendSet({ is_on: true, color_temp_k: 2200, brightness: 30 }))
el('send-rgb').addEventListener('click', () => {
  const hex = el('color').value; renderPixels(hex); sendSet({ color_hex: hex, is_on: true })
})
el('send-anim').addEventListener('click', () => {
  const typ = el('anim-type').value
  const dur = parseInt(el('anim-duration').value, 10) || 600
  sendAnim({ type: typ, duration_s: dur })
})
el('refresh').addEventListener('click', () => ui.send({ topic: 'get_state' }))
el('save-th').addEventListener('click', saveThresholds)

// 消息处理
ui.onChange('msg', msg => { if (msg.topic === 'state') renderState(msg.payload) })

// 时钟
setInterval(() => {
  const now = new Date(); el('clock').textContent = now.toLocaleTimeString()
}, 1000)

// 启动
loadThresholds()
renderPixels()
ui.send({ topic: 'get_state' })
