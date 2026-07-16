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

        <div class="form-group">
          <label>Extra Fields</label>
          <div class="extra-fields">
            <div v-for="(field, i) in extraFields" :key="i" class="extra-field-row">
              <input v-model="field.key" placeholder="Field name" />
              <input v-model="field.value" placeholder="Value" />
              <button type="button" class="btn-remove" @click="removeExtraField(i)">×</button>
            </div>
            <button type="button" class="btn-small" @click="addExtraField">+ Add field</button>
          </div>
        </div>

        <div class="form-group">
          <label>Related News</label>
          <div class="news-list">
            <div v-for="(item, i) in newsItems" :key="i" class="news-item">
              <input v-model="item.title" placeholder="News title" class="news-title-input" />
              <input v-model="item.url" placeholder="URL (optional)" class="news-url-input" />
              <input v-model="item.author" placeholder="Author (optional)" class="news-author-input" />
              <div class="news-extra-fields">
                <div v-for="(field, j) in item.extraFields" :key="j" class="extra-field-row">
                  <input v-model="field.key" placeholder="Field name" />
                  <input v-model="field.value" placeholder="Value" />
                  <button type="button" class="btn-remove" @click="removeNewsExtraField(i, j)">×</button>
                </div>
                <button type="button" class="btn-small" @click="addNewsExtraField(i)">+ Add field</button>
              </div>
              <button type="button" class="btn-remove" @click="removeNewsItem(i)">Remove news</button>
            </div>
            <button type="button" class="btn-small" @click="addNewsItem">+ Add news</button>
          </div>
        </div>

        <div class="form-group">
          <label>Carousel Images</label>
          <div v-if="editing" class="carousel-images-section">
            <div v-for="(img, i) in carouselImages" :key="i" class="carousel-image-row">
              <input v-model="img.url" placeholder="Image URL" class="carousel-url-input" />
              <input v-model="img.description" placeholder="Description (optional)" class="carousel-desc-input" />
              <input v-model="img.source_url" placeholder="Source URL (optional)" class="carousel-source-input" />
              <button type="button" class="btn-remove" @click="removeCarouselImage(i)">×</button>
            </div>
            <button type="button" class="btn-small" @click="addCarouselImage">+ Add image</button>
          </div>
          <div v-else class="text-muted">Save the event first to add images</div>
        </div>

        <div v-if="editing && eventImages.length" class="form-group">
          <label>Satellite Images</label>
          <div class="image-list">
            <div v-for="(img, i) in eventImages" :key="i" class="image-item">
              <span>{{ img.name }} ({{ img.image_type }})</span>
              <button type="button" class="btn-remove" @click="deleteImage(editing, img.filename)">Delete</button>
            </div>
          </div>
        </div>

        <div v-if="editing" class="form-group">
          <label>Upload Satellite Image</label>
          <div class="upload-form">
            <input type="file" @change="e => uploadFile = e.target.files[0]" accept=".png,.jpg,.jpeg" />
            <input v-model="uploadName" placeholder="Image name (e.g., Before 2024)" />
            <select v-model="uploadType">
              <option value="optical">Optical</option>
              <option value="sar">SAR</option>
            </select>
            <div class="bounds-inputs">
              <input v-model="uploadBoundsWest" type="number" step="any" placeholder="West" />
              <input v-model="uploadBoundsSouth" type="number" step="any" placeholder="South" />
              <input v-model="uploadBoundsEast" type="number" step="any" placeholder="East" />
              <input v-model="uploadBoundsNorth" type="number" step="any" placeholder="North" />
            </div>
            <button type="button" class="btn-small" :disabled="uploading" @click="uploadImage(editing)">
              {{ uploading ? 'Uploading...' : 'Upload' }}
            </button>
          </div>
          <p v-if="uploadSuccess" class="success">Image uploaded successfully!</p>
        </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary">{{ editing ? 'Update Event' : 'Create Event' }}</button>
            <button v-if="editing" type="button" class="btn-secondary" @click="cancelEdit">Cancel</button>
          </div>
        </form>

        <div class="admin-sort-controls">
          <label>Sort by <select v-model="sortBy"><option value="date">Event date</option><option value="added">Date added</option></select></label>
          <label>Order <select v-model="sortDirection"><option value="asc">Ascending</option><option value="desc">Descending</option></select></label>
        </div>
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
              <td>{{ event.title }} <span v-if="event.is_latest" class="new-badge">New!</span></td>
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
          <button type="button" class="btn-secondary" @click="showMapPicker = false; pickerInitialCenter.value = null; pickerPoints.value = []; editingPoints.value = null">Cancel</button>
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
const sortBy = ref('date')
const sortDirection = ref('desc')
const editing = ref(null)
const showMapPicker = ref(false)
const pickerPoints = ref([])
const pickerInitialCenter = ref(null)

const form = reactive({
  title: '',
  date: '',
  pointsStr: '',
  extra: {},
})

const extraFields = ref([{ key: '', value: '' }])
const newsItems = ref([{ title: '', url: '', author: '', extraFields: [{ key: '', value: '' }] }])
const editingPoints = ref(null)
const eventImages = ref([])
const carouselImages = ref([])
const uploadFile = ref(null)
const uploadName = ref('')
const uploadType = ref('optical')
const uploadBoundsWest = ref('')
const uploadBoundsSouth = ref('')
const uploadBoundsEast = ref('')
const uploadBoundsNorth = ref('')
const uploading = ref(false)
const uploadSuccess = ref(false)

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
  const query = new URLSearchParams({ sort_by: sortBy.value, direction: sortDirection.value })
  const res = await fetch(`/api/events?${query}`, {
    headers: { 'Authorization': `Bearer ${sessionStorage.getItem('adminToken')}` },
  })
  events.value = await res.json()
}

watch([sortBy, sortDirection], loadEvents)

function resetForm() {
  form.title = ''
  form.date = ''
  form.pointsStr = ''
  form.extra = {}
  errors.date = ''
  errors.points = ''
  editing.value = null
  extraFields.value = [{ key: '', value: '' }]
  newsItems.value = [{ title: '', url: '', author: '', extraFields: [{ key: '', value: '' }] }]
  carouselImages.value = []
}

function addExtraField() {
  extraFields.value.push({ key: '', value: '' })
}

function removeExtraField(i) {
  extraFields.value.splice(i, 1)
}

function loadExtraFields(extra) {
  if (extra && Object.keys(extra).length > 0) {
    extraFields.value = Object.entries(extra).map(([key, value]) => ({
      key,
      value: String(value)
    }))
  } else {
    extraFields.value = [{ key: '', value: '' }]
  }
}

function addNewsItem() {
  newsItems.value.push({ title: '', url: '', author: '', extraFields: [{ key: '', value: '' }] })
}

function removeNewsItem(i) {
  newsItems.value.splice(i, 1)
}

function addNewsExtraField(i) {
  newsItems.value[i].extraFields.push({ key: '', value: '' })
}

function removeNewsExtraField(i, j) {
  newsItems.value[i].extraFields.splice(j, 1)
}

function loadNewsItems(news) {
  if (news && news.length > 0) {
    newsItems.value = news.map(item => ({
      title: item.title,
      url: item.url || '',
      author: item.author || '',
      extraFields: item.extra && Object.keys(item.extra).length > 0
        ? Object.entries(item.extra).map(([key, value]) => ({ key, value: String(value) }))
        : [{ key: '', value: '' }]
    }))
  } else {
    newsItems.value = [{ title: '', url: '', author: '', extraFields: [{ key: '', value: '' }] }]
  }
}

function addCarouselImage() {
  carouselImages.value.push({ url: '', description: '', source_url: '' })
}

function removeCarouselImage(i) {
  carouselImages.value.splice(i, 1)
}

function editEvent(event) {
  editing.value = event.id
  form.title = event.title
  form.date = event.date.slice(0, 16)
  form.pointsStr = event.points?.coordinates?.map(c => [c[1], c[0]].join(',')).join(';') || ''
  form.extra = event.extra || {}
  loadExtraFields(event.extra)
  loadNewsItems(event.news)
  eventImages.value = event.images || []
  carouselImages.value = (event.carousel_images || []).map(img => ({ url: img.url, description: img.description || '', source_url: img.source_url || '' }))

  // Store points for map picker
  if (event.points && event.points.coordinates && event.points.coordinates.length > 0) {
    editingPoints.value = event.points.coordinates.map(c => [c[1], c[0]])
  } else {
    editingPoints.value = null
  }

  // Reset map picker state
  pickerInitialCenter.value = null
  pickerPoints.value = []
}

async function saveEvent() {
  if (!validateDate() || !validatePoints()) return

  const points = form.pointsStr
    ? form.pointsStr.split(';').map(pair => pair.split(',').map(Number))
    : null

  // Build extra fields object from form
  const extra = {}
  extraFields.value.forEach(f => {
    if (f.key.trim()) {
      extra[f.key.trim()] = f.value
    }
  })

  // Build news items from form
  const news = newsItems.value
    .filter(item => item.title.trim())
    .map(item => {
      const itemExtra = {}
      item.extraFields.forEach(f => {
        if (f.key.trim()) {
          itemExtra[f.key.trim()] = f.value
        }
      })
      return {
        title: item.title.trim(),
        url: item.url.trim() || undefined,
        author: item.author.trim() || undefined,
        extra: Object.keys(itemExtra).length > 0 ? itemExtra : null,
      }
    })

  const carouselImgs = carouselImages.value
    .filter(img => img.url.trim())
    .map(img => ({
      url: img.url.trim(),
      description: img.description.trim() || undefined,
      source_url: img.source_url.trim() || undefined,
    }))

  const payload = {
    title: form.title,
    date: new Date(form.date).toISOString(),
    points: points ? { type: 'MultiPoint', coordinates: points.map(p => [p[1], p[0]]) } : null,
    extra: Object.keys(extra).length > 0 ? extra : null,
    carousel_images: carouselImgs.length > 0 ? carouselImgs : undefined,
    news: news.length > 0 ? news : null,
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

  const data = await res.json()

  if (!editing.value) {
    // Created new event - switch to edit mode with the new event
    editing.value = data.id
    eventImages.value = data.images || []
    await loadEvents()
    // Update the event in the list to get latest data
    const event = events.value.find(e => e.id === data.id)
    if (event) {
      eventImages.value = event.images || []
    }
  } else {
    resetForm()
    await loadEvents()
  }
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

async function uploadImage(eventId) {
  if (!uploadFile.value || !uploadName.value) return

  uploading.value = true
  uploadSuccess.value = false
  const formData = new FormData()
  formData.append('file', uploadFile.value)
  formData.append('name', uploadName.value)
  formData.append('image_type', uploadType.value)

  const bounds = [
    uploadBoundsWest.value,
    uploadBoundsSouth.value,
    uploadBoundsEast.value,
    uploadBoundsNorth.value,
  ]
  if (bounds.every(v => v !== '')) {
    formData.append('bounds', bounds.join(','))
  }

  try {
    const res = await fetch(`/api/events/${eventId}/images`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sessionStorage.getItem('adminToken')}`,
      },
      body: formData,
    })

    if (res.ok) {
      const data = await res.json()
      uploadFile.value = null
      uploadName.value = ''
      uploadType.value = 'optical'
      uploadBoundsWest.value = ''
      uploadBoundsSouth.value = ''
      uploadBoundsEast.value = ''
      uploadBoundsNorth.value = ''
      uploadSuccess.value = true
      setTimeout(() => { uploadSuccess.value = false }, 3000)
      await loadEvents()
      // Update eventImages with new data
      const event = events.value.find(e => e.id === eventId)
      if (event) {
        eventImages.value = event.images || []
      }
    } else {
      error.value = 'Upload failed'
    }
  } finally {
    uploading.value = false
  }
}

async function deleteImage(eventId, imageFilename) {
  if (!confirm('Delete this image?')) return

  const event = events.value.find(e => e.id === eventId)
  if (!event || !event.images) return

  const newImages = event.images.filter(img => img.filename !== imageFilename)

  try {
    const res = await fetch(`/api/events/${eventId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${sessionStorage.getItem('adminToken')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title: event.title,
        date: event.date,
        points: event.points,
        extra: event.extra,
        images: newImages,
      }),
    })

    if (res.ok) {
      await loadEvents()
      const updatedEvent = events.value.find(e => e.id === eventId)
      if (updatedEvent) {
        eventImages.value = updatedEvent.images || []
      }
    } else {
      error.value = 'Delete failed'
    }
  } catch (e) {
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

    if (res.status === 429) {
      error.value = 'Too many login attempts. Please wait a minute and try again.'
      return
    }

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
  // If no current points but editing, load from editingPoints
  if (pickerPoints.value.length === 0 && editingPoints.value) {
    pickerPoints.value = [...editingPoints.value]
  }

  setTimeout(() => {
    const container = document.getElementById('picker-map')
    if (!container) return

    // Remove existing map if any
    if (pickerMap) {
      pickerMap.remove()
      pickerMap = null
    }

    // Determine center and fit bounds
    let center = [46.5197, 7.0]
    let bounds = null

    if (pickerPoints.value.length > 0) {
      bounds = L.latLngBounds(pickerPoints.value)
      center = bounds.getCenter()
    } else if (pickerInitialCenter.value) {
      center = pickerInitialCenter.value
    }

    pickerMap = L.map('picker-map', { center, zoom: 8 })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(pickerMap)

    // Add markers for existing points
    pickerPoints.value.forEach((pt, i) => {
      const marker = L.marker(pt).addTo(pickerMap)
      marker.bindPopup(`Point ${i + 1}`)
    })

    // Fit bounds to show all markers
    if (bounds && pickerPoints.value.length > 1) {
      pickerMap.fitBounds(bounds, { padding: [50, 50] })
    } else if (pickerPoints.value.length === 1) {
      pickerMap.setZoom(12)
    }

    pickerMap.on('click', function (e) {
      pickerPoints.value.push([e.latlng.lat, e.latlng.lng])
      const marker = L.marker([e.latlng.lat, e.latlng.lng]).addTo(pickerMap)
      marker.bindPopup(`Point ${pickerPoints.value.length}`)
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
  pickerInitialCenter.value = null
  pickerPoints.value = []
  editingPoints.value = null
}

watch(showMapPicker, (val) => {
  if (val) {
    openMapPicker()
  }
})
</script>

<style>
:root {
  --primary: #2d5a3f;
  --primary-hover: #1e3d2a;
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
  font-family: 'Lexend', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
  overflow-y: auto;
  height: 100vh;
  box-sizing: border-box;
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

.extra-fields {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.extra-field-row {
  display: flex;
  gap: 0.5rem;
}

.extra-field-row input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.news-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--bg);
  border-radius: var(--radius);
  border: 1px solid var(--border);
}

.news-title-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-weight: 600;
}

.news-extra-fields {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-remove {
  background: var(--danger);
  color: white;
  border: none;
  border-radius: var(--radius);
  padding: 0.4rem 0.8rem;
  cursor: pointer;
  font-size: 0.75rem;
  white-space: nowrap;
}

.error {
  color: var(--danger);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.success {
  color: #2c5f2d;
  font-size: 0.9rem;
  margin-top: 0.5rem;
  font-weight: 600;
  padding: 0.5rem;
  background: #e8f5e9;
  border-radius: var(--radius);
  border: 1px solid #2c5f2d;
}

.image-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.image-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: 0.875rem;
}

.image-item button {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.carousel-images-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.carousel-image-row {
  display: flex;
  gap: 0.35rem;
  align-items: center;
}

.carousel-url-input {
  flex: 2;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.85rem;
}

.carousel-desc-input {
  flex: 1.5;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.85rem;
}

.carousel-source-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.85rem;
}

.upload-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.upload-form input[type="file"] {
  flex: 1;
  min-width: 200px;
}

.upload-form input[type="text"] {
  flex: 1;
  min-width: 150px;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.upload-form select {
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.bounds-inputs {
  display: flex;
  gap: 0.35rem;
  width: 100%;
}

.bounds-inputs input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.85rem;
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

.admin-sort-controls {
  display: flex;
  gap: 1rem;
  margin: 1.5rem 0 0.75rem;
}

.admin-sort-controls label {
  display: grid;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.admin-sort-controls select {
  padding: 0.45rem;
  border: 1px solid var(--border);
  border-radius: 4px;
}

.new-badge {
  display: inline-block;
  background: #f7d354;
  color: #17231d;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  vertical-align: middle;
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
