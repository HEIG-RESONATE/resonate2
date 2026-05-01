<template>
  <div class="home">
    <div id="map"></div>
    <aside class="sidebar">
      <h2 class="sidebar-title">Events</h2>
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else-if="events.length === 0" class="empty">No events yet</div>
      <ul v-else class="event-list">
        <li v-for="event in events" :key="event.id" class="event-item">
          <span class="event-title">{{ event.title }}</span>
          <span class="event-date">{{ formatDate(event.date) }}</span>
        </li>
      </ul>
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
let map = null

onMounted(async () => {
  // Fetch events
  try {
    const res = await fetch('/api/public/events')
    events.value = await res.json()
  } catch (e) {
    console.error('Failed to load events:', e)
  }
  loading.value = false

  // Initialize map
  map = L.map('map').setView([46.5197, 7.0], 13)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
  }).addTo(map)

  // Add markers for events with points
  events.value.forEach(event => {
    if (event.points && event.points.coordinates) {
      event.points.coordinates.forEach(coord => {
        L.marker([coord[0], coord[1]])
          .bindPopup(`<strong>${event.title}</strong><br>${formatDate(event.date)}`)
          .addTo(map)
      })
    }
  })
})

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
}

.event-item:hover {
  background: rgba(255, 255, 255, 0.1);
  cursor: pointer;
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