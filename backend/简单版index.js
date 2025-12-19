// index.js
const ui = window.uibuilder   // IIFE 全局对象
const el = id => document.getElementById(id)

// 亮度调节保护
let adjustingBrightness = false
let adjustTimer = null
const startAdjust = () => {
  adjustingBrightness = true
  clearTimeout(adjustTimer)
  adjustTimer = setTimeout(() => { adjustingBrightness = false }, 800) // 手指松开 0.8s 后允许同步
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
  if (on) {
    flag.textContent = '警戒'
    flag.classList.remove('off'); flag.classList.add('on')
  } else {
    flag.textContent = '正常'
    flag.classList.remove('on'); flag.classList.add('off')
  }
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
    setAlert(true)
    alertActive = true
    if (!alertLock) {
      alertLock = true
      sendAnim({ type: 'warning' })             // 触发一次 warning
      setTimeout(() => { alertLock = false }, 10000)
    }
  } else {
    setAlert(false)
    if (alertActive) {
      // 警戒解除，清掉动画
      sendSet({})
    }
    alertActive = false
  }
}

// 闹钟调度
let alarmTimer = null
let alarmData = { time: null, duration: 600, nextTs: null }

function loadAlarm() {
  try {
    const saved = JSON.parse(localStorage.getItem('sunlamp_alarm') || '{}')
    alarmData = { ...alarmData, ...saved }
    if (alarmData.time) el('alarm-time').value = alarmData.time
    if (alarmData.duration) el('alarm-duration').value = alarmData.duration
    if (alarmData.nextTs) scheduleAlarm()
    updateAlarmStatus()
  } catch (e) { }
}

function saveAlarm() {
  const timeStr = el('alarm-time').value
  const dur = parseInt(el('alarm-duration').value, 10) || 600
  if (!timeStr) return
  const now = new Date()
  const [h, m] = timeStr.split(':').map(Number)
  let next = new Date()
  next.setHours(h, m, 0, 0)
  if (next.getTime() <= now.getTime()) next = new Date(next.getTime() + 24 * 3600 * 1000) // 过时则顺延一天
  alarmData = { time: timeStr, duration: dur, nextTs: next.getTime() }
  localStorage.setItem('sunlamp_alarm', JSON.stringify(alarmData))
  scheduleAlarm()
  updateAlarmStatus()
}

function cancelAlarm() {
  alarmData = { time: null, duration: 600, nextTs: null }
  localStorage.removeItem('sunlamp_alarm')
  if (alarmTimer) clearTimeout(alarmTimer)
  alarmTimer = null
  updateAlarmStatus()
}

function scheduleAlarm() {
  if (alarmTimer) clearTimeout(alarmTimer)
  if (!alarmData.nextTs) return
  const now = Date.now()
  const delay = alarmData.nextTs - now
  if (delay <= 0) {
    triggerAlarm()
    return
  }
  alarmTimer = setTimeout(triggerAlarm, delay)
}

function triggerAlarm() {
  // 发 wakeup 动画
  sendAnim({ type: 'wakeup', duration_s: alarmData.duration })
  // 预定下一天
  alarmData.nextTs = alarmData.nextTs + 24 * 3600 * 1000
  localStorage.setItem('sunlamp_alarm', JSON.stringify(alarmData))
  scheduleAlarm()
  updateAlarmStatus(true)
}

function updateAlarmStatus(justTriggered = false) {
  const st = el('alarm-status')
  if (!alarmData.nextTs) { st.textContent = '未设置'; st.style.color = 'var(--muted)'; return }
  const remaining = Math.max(0, alarmData.nextTs - Date.now())
  const hh = Math.floor(remaining / 3600000)
  const mm = Math.floor((remaining % 3600000) / 60000)
  st.textContent = justTriggered ? '已触发，下一次已排程' : `下次：${hh}h ${mm}m 后`
  st.style.color = 'var(--primary)'
}

// 事件绑定
el('alarm-save').addEventListener('click', saveAlarm)
el('alarm-cancel').addEventListener('click', cancelAlarm)

// 启动时加载闹钟
loadAlarm()
// 可选：每分钟刷新显示
setInterval(updateAlarmStatus, 60000)


// 更新显示
function renderState(state = {}) {
  const sensor = state.sensor || {}
  const net = state.network || {}
  const lamp = state.lamp || {}
  el('wifi').textContent = net.wifi || '-'
  el('mqtt').textContent = net.mqtt || '-'
  el('th').textContent = `${sensor.temperature ?? '-'}°C / ${sensor.humidity ?? '-'}%`
  el('gas').textContent = `eCO2 ${sensor.eco2 ?? '-'} ppm / TVOC ${sensor.tvoc ?? '-'}`
  el('lux').textContent = sensor.light ?? '-'
  el('lamp').textContent = `${lamp.is_on ? 'ON' : 'OFF'} | ${lamp.brightness ?? 0}% | ${lamp.color_mode || '-'}`
  if (lamp.hasOwnProperty('is_on')) el('is_on').checked = !!lamp.is_on
  if (!adjustingBrightness && lamp.hasOwnProperty('brightness')) {
    el('brightness').value = lamp.brightness
    el('brightness-val').textContent = lamp.brightness
  }
  // 阈值检测
  checkThresholds(sensor)
}

// 发送 set 命令
function sendSet(payload) {
  ui.send({ topic: 'set', payload })
}

// 发送 anim 命令
function sendAnim(payload) {
  ui.send({ topic: 'anim', payload })
}

// 事件绑定
el('brightness').addEventListener('input', e => {
  const v = parseInt(e.target.value, 10) || 0
  el('brightness-val').textContent = v
  startAdjust()
  sendSet({ brightness: v })        // 如需降频可改为 change 事件
})
el('is_on').addEventListener('change', e => {
  sendSet({ is_on: e.target.checked })
})
document.querySelectorAll('.btn-group button').forEach(btn => {
  btn.addEventListener('click', () => {
    const k = parseInt(btn.dataset.ct, 10)
    sendSet({ color_temp_k: k })
  })
})
el('night').addEventListener('click', () => {
  sendSet({ is_on: true, color_temp_k: 2200, brightness: 30 })
})
el('send-rgb').addEventListener('click', () => {
  const hex = el('color').value // like #rrggbb
  sendSet({ color_hex: hex, is_on: true })
})
el('send-anim').addEventListener('click', () => {
  const typ = el('anim-type').value
  const dur = parseInt(el('anim-duration').value, 10) || 600
  sendAnim({ type: typ, duration_s: dur })
})
// 快捷动画按钮
const quick = [
  { id: 'quick-wakeup', type: 'wakeup', dur: 600 },
  { id: 'quick-sunset', type: 'sunset', dur: 900 },
  { id: 'quick-breathe', type: 'breathe', dur: 3 },
  { id: 'quick-warning', type: 'warning', dur: 0 }
]
quick.forEach(q => {
  const btn = el(q.id)
  if (btn) {
    btn.addEventListener('click', () => {
      // 同步选择器与时长输入，方便后续手动调节
      el('anim-type').value = q.type
      el('anim-duration').value = q.dur
      sendAnim({ type: q.type, duration_s: q.dur })
    })
  }
})
el('refresh').addEventListener('click', () => {
  ui.send({ topic: 'get_state' })
})
// 保存阈值
el('save-th').addEventListener('click', () => {
  saveThresholds()
})

// 处理来自 Node-RED 的消息
ui.onChange('msg', msg => {
  if (msg.topic === 'state') {
    renderState(msg.payload)
  }
})

// 初始加载
loadThresholds()
ui.send({ topic: 'get_state' })

