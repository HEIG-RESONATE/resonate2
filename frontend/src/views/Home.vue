<template>
  <div class="home">
    <div id="map"></div>

    <div v-if="events.length >= 2" class="timeline">
      <div class="timeline-controls">
        <button class="timeline-btn" @click="prevEvent">← Prev</button>
        <button class="timeline-btn play-btn" @click="playTimeline">
          {{ isPlaying ? '⏹ Stop' : '▶ Play' }}
        </button>
        <button class="timeline-btn" @click="nextEvent">Next →</button>
      </div>
      <div class="timeline-dates">
        <button
          v-for="(event, index) in events"
          :key="event.id"
          class="timeline-item"
          :class="{ active: selectedEvent?.id === event.id }"
          @click="selectEventByIndex(index)"
        >
          <span class="timeline-date">{{ formatTimelineDate(event.date) }}</span>
          <span class="timeline-title">{{ event.title }}</span>
        </button>
      </div>
    </div>

    <aside class="sidebar">
      <template v-if="selectedEvent">
        <button class="back-btn" @click="clearSelection">← Back to all events</button>

        <h2 class="event-detail-title">{{ selectedEvent.title }}</h2>

        <div class="event-detail">
          <div class="detail-row">
            <span class="detail-label">Date</span>
            <span class="detail-value">{{ formatDate(selectedEvent.date) }}</span>
          </div>

          <div v-if="selectedEvent.points && selectedEvent.points.coordinates" class="detail-row">
            <span class="detail-label">Coordinates</span>
            <span class="detail-value">
              {{ selectedEvent.points.coordinates.map(c => `${c[0]}, ${c[1]}`).join('; ') }}
            </span>
          </div>

          <div v-if="selectedEvent.extra && Object.keys(selectedEvent.extra).length > 0" class="detail-extra">
            <span class="detail-label">Extra Info</span>
            <div v-for="(value, key) in selectedEvent.extra" :key="key" class="extra-item">
              <span class="extra-key">{{ key }}:</span>
              <span class="extra-value">{{ value }}</span>
            </div>
          </div>

          <div v-if="selectedEvent.images && selectedEvent.images.length > 0" class="detail-images">
            <span class="detail-label">Satellite Images</span>
            <div v-for="img in selectedEvent.images" :key="img.filename" class="image-item">
              <label class="toggle-label">
                <input type="checkbox" v-model="showRaster[img.filename]" @change="toggleRaster(img)" />
              </label>
              <span class="image-name">{{ img.name }}</span>
              <span class="image-type">({{ img.image_type }})</span>
              <button v-if="img.bounds" class="image-badge" @click="zoomToImage(img.bounds)">
                Zoom
              </button>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <h2 class="sidebar-title">Events</h2>
        <div v-if="loading" class="loading">Loading...</div>
        <div v-else-if="events.length === 0" class="empty">No events yet</div>
        <ul v-else class="event-list">
          <li v-for="event in events" :key="event.id" class="event-item" @click="selectEvent(event)">
            <span class="event-title">{{ event.title }}</span>
            <span class="event-date">{{ formatDate(event.date) }}</span>
          </li>
        </ul>
      </template>
    </aside>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

delete L.Icon.Default.prototype._getIconUrl

L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const events = ref([])
const loading = ref(true)
const selectedEvent = ref(null)
let map = null
let imageOverlay = null
const showRaster = ref({})

const isPlaying = ref(false)
const currentIndex = ref(0)
let playInterval = null

onMounted(async () => {
  try {
    const res = await fetch('/api/public/events')
    events.value = await res.json()
  } catch (e) {
    console.error('Failed to load events:', e)
  }
  loading.value = false

  map = L.map('map').setView([46.5197, 7.0], 13)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
  }).addTo(map)

  showAllMarkers()
})

function showAllMarkers() {
  const allCoords = []
  events.value.forEach(event => {
    if (event.points && event.points.coordinates) {
      event.points.coordinates.forEach(coord => {
        L.marker([coord[0], coord[1]])
          .bindPopup(`<strong>${event.title}</strong><br>${formatDate(event.date)}`)
          .addTo(map)
        allCoords.push(coord)
      })
    }
  })

  fitMapToCoords(allCoords)
}

function selectEvent(event) {
  selectedEvent.value = event

  // Clear existing markers and image overlay
  map.eachLayer(layer => {
    if (layer instanceof L.Marker) {
      map.removeLayer(layer)
    }
  })
  clearImageOverlay()

  // Show only this event's markers
  if (event.points && event.points.coordinates) {
    const coords = []
    event.points.coordinates.forEach(coord => {
      L.marker([coord[0], coord[1]])
        .bindPopup(`<strong>${event.title}</strong><br>${formatDate(event.date)}`)
        .addTo(map)
      coords.push(coord)
    })

    fitMapToCoords(coords)
  }

  // Reset showRaster state for new event
  showRaster.value = {}
}

function clearImageOverlay() {
  if (imageOverlay) {
    map.removeLayer(imageOverlay)
    imageOverlay = null
  }
}

function clearSelection() {
  selectedEvent.value = null
  stopTimeline()

  // Clear markers and image overlay
  map.eachLayer(layer => {
    if (layer instanceof L.Marker) {
      map.removeLayer(layer)
    }
  })
  clearImageOverlay()

  // Show all markers
  showAllMarkers()
}

function fitMapToCoords(coords) {
  if (coords.length === 0) return

  if (coords.length === 1) {
    map.setView(coords[0], 10)
  } else {
    const bounds = L.latLngBounds(coords)
    map.fitBounds(bounds, { padding: [50, 50] })
  }
}

function zoomToImage(bounds) {
  const imageBounds = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
  map.fitBounds(imageBounds, { padding: [50, 50] })
}

function toggleRaster(img) {
  if (!img.bounds || !img.preview) return

  const baseUrl = window.location.origin
  const imageUrl = `${baseUrl}/images/${img.preview}`
  const bounds = img.bounds
  const imageBounds = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]

  // Clear existing overlay for this specific image
  if (imageOverlay) {
    map.removeLayer(imageOverlay)
    imageOverlay = null
  }

  if (showRaster.value[img.filename]) {
    imageOverlay = L.imageOverlay(imageUrl, imageBounds, { opacity: 0.7 }).addTo(map)
  }
}

function playTimeline() {
  if (events.value.length < 2) return

  if (isPlaying.value) {
    stopTimeline()
    return
  }

  isPlaying.value = true
  currentIndex.value = 0
  selectEventByIndex(0)

  playInterval = setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % events.value.length
    selectEventByIndex(currentIndex.value)
  }, 3000)
}

function stopTimeline() {
  isPlaying.value = false
  if (playInterval) {
    clearInterval(playInterval)
    playInterval = null
  }
}

function prevEvent() {
  stopTimeline()
  if (events.value.length === 0) return

  if (!selectedEvent.value) {
    currentIndex.value = 0
  } else {
    const currentIdx = events.value.findIndex(e => e.id === selectedEvent.value.id)
    currentIndex.value = currentIdx > 0 ? currentIdx - 1 : events.value.length - 1
  }
  selectEventByIndex(currentIndex.value)
}

function nextEvent() {
  stopTimeline()
  if (events.value.length === 0) return

  if (!selectedEvent.value) {
    currentIndex.value = 0
  } else {
    const currentIdx = events.value.findIndex(e => e.id === selectedEvent.value.id)
    currentIndex.value = (currentIdx + 1) % events.value.length
  }
  selectEventByIndex(currentIndex.value)
}

function selectEventByIndex(index) {
  const event = events.value[index]
  if (event) {
    selectedEvent.value = event
    showRaster.value = {}

    map.eachLayer(layer => {
      if (layer instanceof L.Marker) {
        map.removeLayer(layer)
      }
    })
    clearImageOverlay()

    if (event.points && event.points.coordinates) {
      const coords = []
      event.points.coordinates.forEach(coord => {
        L.marker([coord[0], coord[1]])
          .bindPopup(`<strong>${event.title}</strong><br>${formatDate(event.date)}`)
          .addTo(map)
        coords.push(coord)
      })
      fitMapToCoords(coords)
    }
  }
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatTimelineDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}
</script>

<style scoped>
.timeline {
  position: absolute;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  background: white;
  border-radius: 12px;
  padding: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  max-width: 90vw;
  width: 600px;
}

.timeline-controls {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.timeline-btn {
  padding: 0.4rem 0.8rem;
  border: 1px solid #ccc;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.timeline-btn:hover {
  background: #f0f0f0;
}

.play-btn {
  background: #84a98c;
  color: white;
  border-color: #84a98c;
  min-width: 80px;
}

.play-btn:hover {
  background: #6b8e73;
}

.timeline-dates {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  padding-bottom: 0.25rem;
}

.timeline-item {
  flex-shrink: 0;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  text-align: center;
  min-width: 100px;
  transition: all 0.2s;
}

.timeline-item:hover {
  border-color: #84a98c;
  background: #f8fdf8;
}

.timeline-item.active {
  background: #84a98c;
  color: white;
  border-color: #84a98c;
}

.timeline-date {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.timeline-title {
  display: block;
  font-size: 0.7rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}

.home {
  display: flex;
  height: 100vh;
  width: 100%;
}

#map {
  flex: 1;
  height: 100%;
}

.sidebar {
  width: 320px;
  background-color: #84a98c;
  color: white;
  padding: 1.5rem;
  overflow-y: auto;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.15);
  font-family: "Lexend", sans-serif;
}

.sidebar-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid rgba(255, 255, 255, 0.3);
}

.back-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 1rem;
  font-family: inherit;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.event-detail-title {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid rgba(255, 255, 255, 0.3);
}

.event-detail {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  opacity: 0.7;
  font-weight: 600;
}

.detail-value {
  font-size: 0.95rem;
}

.detail-extra {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.extra-item {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.extra-key {
  font-weight: 600;
}

.detail-images {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.images-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.8);
}

.toggle-label input {
  cursor: pointer;
}

.image-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.image-name {
  font-weight: 500;
}

.image-type {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.875rem;
}

.image-badge {
  margin-left: auto;
  padding: 0.3rem 0.6rem;
  background: #84a98c;
  border-radius: 4px;
  font-size: 0.75rem;
  color: white;
  cursor: pointer;
  border: none;
  font-family: inherit;
}

.image-badge:hover {
  background: #6b8e73;
}

.loading, .empty {
  text-align: center;
  padding: 2rem;
  opacity: 0.8;
}

.event-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.event-item {
  padding: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
  transition: background 0.2s;
  cursor: pointer;
}

.event-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.event-title {
  display: block;
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.event-date {
  display: block;
  font-size: 0.8rem;
  opacity: 0.8;
}
</style>