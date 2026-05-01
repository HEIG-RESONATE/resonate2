<template>
  <div class="home">
    <div id="map"></div>
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

  // Clear existing markers
  map.eachLayer(layer => {
    if (layer instanceof L.Marker) {
      map.removeLayer(layer)
    }
  })

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
}

function clearSelection() {
  selectedEvent.value = null

  // Clear markers
  map.eachLayer(layer => {
    if (layer instanceof L.Marker) {
      map.removeLayer(layer)
    }
  })

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
</script>

<style scoped>
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