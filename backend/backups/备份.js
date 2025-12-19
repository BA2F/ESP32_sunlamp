// @ts-ignore
uibuilder.start();

// --- DOM 元素引用 ---
const powerSwitch = document.getElementById('power-switch');
const brightnessSlider = document.getElementById('brightness-slider');
const brightnessValue = document.getElementById('brightness-value');
const colorSelect = document.getElementById('color-select');
const btnWakeup = document.getElementById('btn-wakeup');
const btnWarning = document.getElementById('btn-warning');

// --- 发送消息到 Node-RED ---
function sendCommand(topic, payload) {
  // @ts-ignore
  uibuilder.send({
    topic: topic,
    payload: payload
  });
}

// --- 为控件添加事件监听器 ---
powerSwitch.addEventListener('change', () => {
  sendCommand('set', { is_on: powerSwitch.checked });
});

brightnessSlider.addEventListener('input', () => {
  const value = brightnessSlider.value;
  brightnessValue.textContent = value;
  sendCommand('set', { brightness: parseInt(value) });
});

colorSelect.addEventListener('change', () => {
  sendCommand('set', { color_mode: colorSelect.value });
});

btnWakeup.addEventListener('click', () => {
  sendCommand('anim', { type: 'wakeup', duration_s: 600 });
});

btnWarning.addEventListener('click', () => {
  sendCommand('anim', { type: 'warning' });
});

// --- 从 Node-RED 接收消息并更新 UI ---
// @ts-ignore
uibuilder.on('msg', (msg) => {
  console.log('收到状态更新:', msg.payload);
  const state = msg.payload;

  if (state.lamp) {
    // 更新开关
    powerSwitch.checked = !!state.lamp.is_on;

    // 更新亮度
    if (state.lamp.brightness !== undefined) {
      brightnessSlider.value = state.lamp.brightness;
      brightnessValue.textContent = state.lamp.brightness;
    }

    // 更新颜色模式
    if (state.lamp.color_mode) {
      colorSelect.value = state.lamp.color_mode;
    }
  }
});




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

