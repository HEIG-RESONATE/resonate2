<template>
  <div class="home">
    <div class="main-area">
      <div id="map"></div>

      <div v-if="filteredEvents.length >= 1" class="timeline">
        <div class="timeline-top">
          <label class="filter-label filter-left">
            From
            <input type="date" v-model="filterFrom" class="filter-input" />
          </label>
          <div class="timeline-controls">
            <button class="timeline-btn" @click="prevEvent" :disabled="filteredEvents.length === 0">←</button>
            <button class="timeline-btn play-btn" @click="playTimeline">
              {{ isPlaying ? '⏹' : '▶' }}
            </button>
            <button class="timeline-btn" @click="nextEvent" :disabled="filteredEvents.length === 0">→</button>
          </div>
          <label class="filter-label filter-right">
            To
            <input type="date" v-model="filterTo" class="filter-input" />
          </label>
        </div>
        <div class="timeline-viewport">
          <div class="timeline-track" :style="{ transform: `translateX(${trackOffset}px)` }">
            <button
              v-for="(event, index) in filteredEvents"
              :key="event.id"
              class="timeline-item"
              :class="{ active: selectedEvent?.id === event.id }"
              @click="selectFilteredEvent(index)"
            >
              <span class="timeline-dot"></span>
              <span class="timeline-date">{{ formatTimelineDate(event.date) }}</span>
              <span class="timeline-title">{{ event.title }}</span>
            </button>
          </div>
        </div>
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
              <label class="toggle-switch">
                <input type="checkbox" v-model="showRaster[img.filename]" @change="toggleRaster(img)" />
                <span class="toggle-slider"></span>
              </label>
              <span class="image-name">{{ img.name }}</span>
              <span class="image-type">({{ img.image_type }})</span>
              <button v-if="img.bounds" class="image-badge" @click="zoomToImage(img.bounds)">
                Zoom
              </button>
            </div>
          </div>

          <div v-if="selectedEvent.news && selectedEvent.news.length > 0" class="detail-news">
            <span class="detail-label">Related News</span>
            <div v-for="(item, i) in selectedEvent.news" :key="i" class="news-item">
              <span class="news-title">{{ item.title }}</span>
              <div v-if="item.extra && Object.keys(item.extra).length > 0" class="news-extra">
                <div v-for="(value, key) in item.extra" :key="key" class="extra-item">
                  <span class="extra-key">{{ key }}:</span>
                  <span class="extra-value">{{ value }}</span>
                </div>
              </div>
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
import { ref, computed, onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

delete L.Icon.Default.prototype._getIconUrl

L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const ITEM_WIDTH = 120
const VISIBLE_COUNT = 5

const events = ref([])
const loading = ref(true)
const selectedEvent = ref(null)
let map = null
let imageOverlay = null
const showRaster = ref({})

const isPlaying = ref(false)
const activeIndex = ref(0)
let playInterval = null

const filterFrom = ref('')
const filterTo = ref('')

const filteredEvents = computed(() => {
  return events.value.filter(e => {
    const d = new Date(e.date)
    if (filterFrom.value && d < new Date(filterFrom.value)) return false
    if (filterTo.value) {
      const to = new Date(filterTo.value)
      to.setHours(23, 59, 59, 999)
      if (d > to) return false
    }
    return true
  })
})

const trackOffset = computed(() => {
  const viewportWidth = ITEM_WIDTH * VISIBLE_COUNT
  const centerOffset = viewportWidth / 2 - ITEM_WIDTH / 2
  return centerOffset - activeIndex.value * ITEM_WIDTH
})

watch(filterFrom, () => { activeIndex.value = 0 })
watch(filterTo, () => { activeIndex.value = 0 })

onMounted(async () => {
  try {
    const res = await fetch('/api/public/events')
    const data = await res.json()
    events.value = data.sort((a, b) => new Date(a.date) - new Date(b.date))
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
  activeIndex.value = 0
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
  if (filteredEvents.value.length < 2) return

  if (isPlaying.value) {
    stopTimeline()
    return
  }

  isPlaying.value = true
  activeIndex.value = 0
  selectFilteredEvent(0)

  playInterval = setInterval(() => {
    activeIndex.value = (activeIndex.value + 1) % filteredEvents.value.length
    selectFilteredEvent(activeIndex.value)
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
  if (filteredEvents.value.length === 0) return
  activeIndex.value = activeIndex.value > 0
    ? activeIndex.value - 1
    : filteredEvents.value.length - 1
  selectFilteredEvent(activeIndex.value)
}

function nextEvent() {
  stopTimeline()
  if (filteredEvents.value.length === 0) return
  activeIndex.value = (activeIndex.value + 1) % filteredEvents.value.length
  selectFilteredEvent(activeIndex.value)
}

function selectFilteredEvent(index) {
  const event = filteredEvents.value[index]
  if (event) {
    activeIndex.value = index
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

<style>
html, body {
  margin: 0;
  padding: 0;
}
</style>

<style scoped>
.home {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

#map {
  flex: 1;
}

.timeline {
  background: white;
  padding: 0.6rem 1.5rem 0.75rem;
  border-top: 1px solid #e0e0e0;
  font-family: "Lexend", sans-serif;
}

.timeline-top {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  margin-bottom: 0.4rem;
}

.filter-left {
  justify-self: right;
  margin-right: 10px;
}

.filter-right {
  justify-self: left;
  margin-left: 10px;
}

.filter-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #555;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.filter-input {
  padding: 0.2rem 0.4rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.75rem;
  font-family: "Lexend", sans-serif;
}

.timeline-controls {
  display: flex;
  gap: 0.4rem;
}

.timeline-btn {
  padding: 0.3rem 0.7rem;
  border: 1px solid #ccc;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.timeline-btn:hover:not(:disabled) {
  background: #f0f0f0;
}

.timeline-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.play-btn {
  background: #2d5a3f;
  color: white;
  border-color: #2d5a3f;
  min-width: 42px;
}

.play-btn:hover:not(:disabled) {
  background: #1e3d2a;
}

.timeline-viewport {
  overflow: hidden;
  width: 600px;
  margin: 0 auto;
}

.timeline-track {
  display: flex;
  transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1);
  will-change: transform;
}

.timeline-item {
  flex-shrink: 0;
  width: 120px;
  box-sizing: border-box;
  padding: 0.4rem 0.5rem;
  padding-top: 1.5rem;
  border: none;
  background: white;
  cursor: pointer;
  text-align: center;
  transition: background 0.2s;
  position: relative;
}

.timeline-item:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 12px;
  right: 0;
  width: 50%;
  height: 2px;
  background: #ddd;
  z-index: 0;
}

.timeline-item:not(:first-child)::before {
  content: '';
  position: absolute;
  top: 12px;
  left: 0;
  width: 50%;
  height: 2px;
  background: #ddd;
  z-index: 0;
}

.timeline-dot {
  position: absolute;
  top: 6px;
  left: 50%;
  transform: translateX(-50%);
  width: 12px;
  height: 12px;
  background: #ddd;
  border-radius: 50%;
  border: 2px solid white;
  z-index: 1;
  transition: all 0.2s;
}

.timeline-item:hover {
  background: #f0f7f2;
}

.timeline-item:hover .timeline-dot {
  background: #2d5a3f;
}

.timeline-item.active {
  background: #2d5a3f;
  color: white;
}

.timeline-item.active .timeline-dot {
  background: #4ade80;
  border-color: #2d5a3f;
}

.timeline-date {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.15rem;
}

.timeline-title {
  display: block;
  font-size: 0.7rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.sidebar {
  width: 320px;
  background-color: #2d5a3f;
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
  border-bottom: 2px solid rgba(255, 255, 255, 0.5);
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
  border-bottom: 2px solid rgba(255, 255, 255, 0.5);
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
  opacity: 0.9;
  font-weight: 600;
}

.detail-value {
  font-size: 0.95rem;
}

.detail-extra {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.4);
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
  border-top: 1px solid rgba(255, 255, 255, 0.4);
}

.detail-news {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.4);
}

.news-item {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
}

.news-title {
  font-weight: 600;
  display: block;
  margin-bottom: 0.25rem;
}

.news-extra {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.images-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.3);
  transition: 0.3s;
  border-radius: 20px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #4ade80;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(16px);
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
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.875rem;
}

.image-badge {
  margin-left: auto;
  padding: 0.3rem 0.6rem;
  background: #2d5a3f;
  border-radius: 4px;
  font-size: 0.75rem;
  color: white;
  cursor: pointer;
  border: none;
  font-family: inherit;
}

.image-badge:hover {
  background: #1e3d2a;
}

.loading, .empty {
  text-align: center;
  padding: 2rem;
  opacity: 0.9;
}

.event-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.event-item {
  padding: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
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
  opacity: 0.9;
}
</style>