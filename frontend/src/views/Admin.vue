<template>
  <div class="app">
    <div v-if="authenticated" class="admin">
      <nav class="nav">
        <RouterLink to="/" class="nav-link">Map</RouterLink>
        <span class="nav-title">Admin</span>
      </nav>
      <main class="main">
        <h1 class="title">Events</h1>

        <form @submit.prevent="saveEvent" class="event-form">
          <div class="form-group">
            <label>Title</label>
            <input v-model="form.title" placeholder="Event title" required />
          </div>

          <div class="form-group">
            <label>Date</label>
            <input type="datetime-local" v-model="form.date" required />
            <span v-if="errors.date" class="error">{{ errors.date }}</span>
          </div>

          <div class="form-group">
          <label>Coordinates</label>
          <div class="coords-row">
            <input
              v-model="form.pointsStr"
              placeholder="46.5197,7.0; 46.52,7.01"
              @input="validatePoints"
            />
            <button type="button" class="btn-secondary" @click="showMapPicker = true">Pick on map</button>
          </div>
          <span class="hint">Format: lat,lng (use semicolon to add more points)</span>
          <span v-if="errors.points" class="error">{{ errors.points }}</span>
        </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary">{{ editing ? 'Update' : 'Add' }}</button>
            <button v-if="editing" type="button" class="btn-secondary" @click="cancelEdit">Cancel</button>
          </div>
        </form>

        <table v-if="events.length" class="events-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Date</th>
              <th>Points</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in events" :key="event.id">
              <td>{{ event.title }}</td>
              <td>{{ new Date(event.date).toLocaleString() }}</td>
              <td>
                <span v-if="event.points && event.points.coordinates">
                  {{ event.points.coordinates.map(c => c.join(',')).join('; ') }}
                </span>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <button class="btn-small" @click="editEvent(event)">Edit</button>
                <button class="btn-small btn-danger" @click="deleteEvent(event.id)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty">No events yet.</p>
      </main>
    </div>

    <form v-else class="login" @submit.prevent="login">
      <h2>Admin Login</h2>
      <input v-model="password" type="password" placeholder="Password" required />
      <button type="submit" class="btn-primary">Login</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>

    <div v-if="showMapPicker" class="modal" @click.self="showMapPicker = false">
      <div class="modal-content">
        <h3>Select coordinates</h3>
        <p class="hint">Click on the map to add points</p>
        <div id="picker-map"></div>
        <div class="picker-coords">
          <span v-for="(pt, i) in pickerPoints" :key="i" class="coord-tag">
            {{ pt[0].toFixed(4) }}, {{ pt[1].toFixed(4) }}
            <button type="button" @click="removePoint(i)">×</button>
          </span>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-secondary" @click="showMapPicker = false">Cancel</button>
          <button type="button" class="btn-primary" @click="applyPoints">Apply</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet marker icons in bundler
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const password = ref('')
const authenticated = ref(false)
const error = ref('')
const events = ref([])
const editing = ref(null)
const showMapPicker = ref(false)
const pickerPoints = ref([])

const form = reactive({
  title: '',
  date: '',
  pointsStr: '',
})

const errors = reactive({
  date: '',
  points: '',
})

onMounted(async () => {
  if (sessionStorage.getItem('adminToken')) {
    authenticated.value = true
    await loadEvents()
  }
})

function validateDate() {
  if (!form.date) {
    errors.date = 'Date is required'
    return false
  }
  const selected = new Date(form.date)
  const minDate = new Date('2000-01-01')
  if (selected < minDate) {
    errors.date = 'Date cannot be before year 2000'
    return false
  }
  errors.date = ''
  return true
}

function validatePoints() {
  if (!form.pointsStr.trim()) {
    errors.points = ''
    return true
  }

  const pairs = form.pointsStr.split(';')
  for (const pair of pairs) {
    const coords = pair.split(',').map(s => parseFloat(s.trim()))
    if (coords.length !== 2 || isNaN(coords[0]) || isNaN(coords[1])) {
      errors.points = 'Invalid format. Use: lat,lng;lat,lng'
      return false
    }
    if (coords[0] < -90 || coords[0] > 90) {
      errors.points = 'Latitude must be between -90 and 90'
      return false
    }
    if (coords[1] < -180 || coords[1] > 180) {
      errors.points = 'Longitude must be between -180 and 180'
      return false
    }
  }
  errors.points = ''
  return true
}

async function loadEvents() {
  const res = await fetch('/api/events', {
    headers: { 'Authorization': `Bearer ${sessionStorage.getItem('adminToken')}` },
  })
  events.value = await res.json()
}

function resetForm() {
  form.title = ''
  form.date = ''
  form.pointsStr = ''
  errors.date = ''
  errors.points = ''
  editing.value = null
}

function editEvent(event) {
  editing.value = event.id
  form.title = event.title
  form.date = event.date.slice(0, 16)
  form.pointsStr = event.points?.coordinates?.map(c => c.join(',')).join(';') || ''
}

async function saveEvent() {
  if (!validateDate() || !validatePoints()) return

  const points = form.pointsStr
    ? form.pointsStr.split(';').map(pair => pair.split(',').map(Number))
    : null

  const payload = {
    title: form.title,
    date: new Date(form.date).toISOString(),
    points: points ? { type: 'MultiPoint', coordinates: points } : null,
  }

  const url = editing.value
    ? `/api/events/${editing.value}`
    : '/api/events'
  const method = editing.value ? 'PUT' : 'POST'

  const res = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionStorage.getItem('adminToken')}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    error.value = 'Save failed'
    return
  }

  resetForm()
  await loadEvents()
}

async function deleteEvent(id) {
  if (!confirm('Delete this event?')) return

  const res = await fetch(`/api/events/${id}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${sessionStorage.getItem('adminToken')}`,
    },
  })

  if (res.ok) {
    await loadEvents()
  } else {
    error.value = 'Delete failed'
  }
}

function cancelEdit() {
  resetForm()
}

async function login() {
  try {
    const res = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value }),
    })

    if (!res.ok) {
      error.value = 'Wrong password'
      return
    }

    const data = await res.json()
    sessionStorage.setItem('adminToken', data.access_token)
    authenticated.value = true
    await loadEvents()
  } catch {
    error.value = 'Connection error'
  }
}

let pickerMap = null

function openMapPicker() {
  pickerPoints.value = []

  // Wait for DOM to update
  setTimeout(() => {
    const container = document.getElementById('picker-map')
    if (!container) return

    // Remove existing map if any
    if (pickerMap) {
      pickerMap.remove()
      pickerMap = null
    }

    pickerMap = L.map('picker-map', {
      center: [46.5197, 7.0],
      zoom: 8,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(pickerMap)

    pickerMap.on('click', function (e) {
      pickerPoints.value.push([e.latlng.lat, e.latlng.lng])
      addMarker(e.latlng.lat, e.latlng.lng)
    })
  }, 200)
}

function addMarker(lat, lng) {
  if (!pickerMap) return
  L.marker([lat, lng]).addTo(pickerMap)
}

function removePoint(i) {
  pickerPoints.value.splice(i, 1)
  // Recreate map to clear markers
  openMapPicker()
  // Restore points
  setTimeout(() => {
    pickerPoints.value.forEach(pt => addMarker(pt[0], pt[1]))
  }, 300)
}

function applyPoints() {
  form.pointsStr = pickerPoints.value.map(pt => `${pt[0]},${pt[1]}`).join(';')
  validatePoints()
  showMapPicker.value = false
}

watch(showMapPicker, (val) => {
  if (val) {
    openMapPicker()
  }
})
</script>

<style>
:root {
  --primary: #2c5f2d;
  --primary-hover: #1e4220;
  --secondary: #6c757d;
  --danger: #dc3545;
  --bg: #f8f9fa;
  --surface: #ffffff;
  --border: #dee2e6;
  --text: #212529;
  --text-muted: #6c757d;
  --radius: 8px;
  --shadow: 0 2px 8px rgba(0,0,0,0.1);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}

.app {
  min-height: 100vh;
}

.admin {
  padding: 2rem;
  max-width: 1000px;
  margin: 0 auto;
}

.nav {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--primary);
}

.nav-link {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: var(--radius);
  transition: background 0.2s;
}

.nav-link:hover {
  background: rgba(44, 95, 45, 0.1);
}

.nav-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text);
}

.title {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: var(--primary);
}

.event-form {
  background: var(--surface);
  padding: 1.5rem;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text);
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 1rem;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary);
}

.coords-row {
  display: flex;
  gap: 0.5rem;
}

.coords-row input {
  flex: 1;
}

.error {
  color: var(--danger);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-primary, .btn-secondary, .btn-small, .btn-danger {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: var(--radius);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--secondary);
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-small {
  padding: 0.4rem 0.8rem;
  font-size: 0.875rem;
  margin-right: 0.25rem;
}

.btn-danger {
  background: var(--danger);
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.events-table {
  width: 100%;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border-collapse: collapse;
  overflow: hidden;
}

.events-table th,
.events-table td {
  padding: 1rem;
  text-align: left;
}

.events-table th {
  background: var(--primary);
  color: white;
  font-weight: 600;
}

.events-table tr:nth-child(even) {
  background: #f8f9fa;
}

.events-table tr:hover {
  background: #e9ecef;
}

.text-muted {
  color: var(--text-muted);
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem;
}

.login {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 1rem;
  padding: 2rem;
}

.login h2 {
  color: var(--primary);
  margin-bottom: 1rem;
}

.login input {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 1rem;
  width: 100%;
  max-width: 300px;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 1.5rem;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: auto;
}

.modal-content h3 {
  color: var(--primary);
  margin-bottom: 0.5rem;
}

.hint {
  display: block;
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

#picker-map {
  height: 400px;
  border-radius: var(--radius);
  margin-bottom: 1rem;
}

.picker-coords {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.coord-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: #e9ecef;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.coord-tag button {
  background: none;
  border: none;
  color: var(--danger);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>