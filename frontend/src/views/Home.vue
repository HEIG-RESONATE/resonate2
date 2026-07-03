<template>
  <div class="home">
    <button class="chat-toggle" :class="{ active: chatOpen }" @click="toggleChat">
      {{ chatOpen ? 'Close chat' : 'Open chat' }}
    </button>

    <div class="main-area">
      <div id="map"></div>

      <div class="timeline">
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
          <div v-if="filteredEvents.length > 0" class="timeline-track" :style="{ transform: `translateX(${trackOffset}px)` }">
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
          <div v-else class="timeline-empty">No events in this date range</div>
        </div>
      </div>
    </div>

    <aside class="sidebar">
      <template v-if="selectedEvent">
        <button class="back-btn" @click="clearSelection">← Back to all events</button>

        <h2 class="event-detail-title">{{ selectedEvent.title }}</h2>

        <div class="event-detail">
          <section class="detail-section detail-section-hero">
            <div class="detail-row">
              <span class="detail-label">Date</span>
              <span class="detail-value">{{ formatDate(selectedEvent.date) }}</span>
            </div>

            <div v-if="selectedEvent.points && selectedEvent.points.coordinates" class="detail-row">
              <div class="detail-heading-row">
                <span class="detail-label">Coordinates</span>
                <span class="detail-badge">{{ selectedEvent.points.coordinates.length }} point{{ selectedEvent.points.coordinates.length > 1 ? 's' : '' }}</span>
              </div>
              <div class="coordinate-list">
                <div v-for="(coord, index) in selectedEvent.points.coordinates" :key="`${coord[0]}-${coord[1]}-${index}`" class="coordinate-chip">
                  {{ formatCoordinate(coord) }}
                </div>
              </div>
            </div>
          </section>

          <section v-if="hasPrimitiveExtra" class="detail-section">
            <div class="detail-heading-row">
              <span class="detail-label">Key Facts</span>
              <span class="detail-badge">{{ primitiveExtraEntries.length }}</span>
            </div>
            <div class="fact-grid">
              <div v-for="([key, value]) in primitiveExtraEntries" :key="key" class="fact-card">
                <span class="fact-key">{{ formatLabel(key) }}</span>
                <span class="fact-value">{{ formatPrimitive(value) }}</span>
              </div>
            </div>
          </section>

          <section v-if="hasStructuredExtra" class="detail-section">
            <details class="structured-details">
              <summary class="structured-summary">
                <span class="detail-label">Structured Data</span>
                <span class="detail-badge">{{ structuredExtraEntries.length }} section{{ structuredExtraEntries.length > 1 ? 's' : '' }}</span>
              </summary>

              <div class="structured-groups">
                <div v-for="([key, value]) in structuredExtraEntries" :key="key" class="structured-group">
                  <div class="structured-group-header">
                    <span class="structured-group-title">{{ formatLabel(key) }}</span>
                    <span class="structured-group-meta">{{ summarizeStructuredValue(value) }}</span>
                  </div>

                  <div v-if="isPrimitiveArray(value)" class="structured-list">
                    <div v-for="(item, index) in value" :key="`${key}-${index}`" class="structured-pill">
                      {{ formatPrimitive(item) }}
                    </div>
                  </div>

                  <div v-else-if="isObjectArray(value)" class="structured-stack">
                    <div v-for="(item, index) in value" :key="`${key}-${index}`" class="structured-card">
                      <div class="structured-card-index">{{ key.slice(0, -1) || 'item' }} {{ index + 1 }}</div>
                      <div v-for="(childValue, childKey) in item" :key="`${key}-${index}-${childKey}`" class="structured-row">
                        <span class="structured-key">{{ formatLabel(childKey) }}</span>
                        <span v-if="isPrimitive(childValue)" class="structured-value">{{ formatPrimitive(childValue) }}</span>
                        <div v-else class="structured-json">{{ formatJson(childValue) }}</div>
                      </div>
                    </div>
                  </div>

                  <div v-else-if="isPlainObject(value)" class="structured-card">
                    <div v-for="(childValue, childKey) in value" :key="`${key}-${childKey}`" class="structured-row">
                      <span class="structured-key">{{ formatLabel(childKey) }}</span>
                      <span v-if="isPrimitive(childValue)" class="structured-value">{{ formatPrimitive(childValue) }}</span>
                      <div v-else class="structured-json">{{ formatJson(childValue) }}</div>
                    </div>
                  </div>

                  <div v-else class="structured-json">{{ formatJson(value) }}</div>
                </div>
              </div>
            </details>
          </section>

          <div v-if="selectedEvent.images && selectedEvent.images.length > 0" class="detail-section detail-images">
            <div class="detail-heading-row">
              <span class="detail-label">Satellite Images</span>
              <span class="detail-badge">{{ selectedEvent.images.length }}</span>
            </div>
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

          <div v-if="selectedEvent.carousel_images && selectedEvent.carousel_images.length > 0" class="detail-section detail-carousel">
            <div class="detail-heading-row">
              <span class="detail-label">Images</span>
              <span class="detail-badge">{{ selectedEvent.carousel_images.length }}</span>
            </div>
            <div class="carousel">
              <div class="carousel-image-wrapper">
                <img :src="carouselImages[carouselIndex].url" alt="Event image" class="carousel-image" @click="lightboxUrl = carouselImages[carouselIndex].url" />
              </div>
              <div class="carousel-meta">
                <a v-if="carouselImages[carouselIndex].source_url && carouselImages[carouselIndex].description" :href="carouselImages[carouselIndex].source_url" target="_blank" rel="noopener noreferrer" class="carousel-description-link">{{ carouselImages[carouselIndex].description }}</a>
                <p v-else-if="carouselImages[carouselIndex].description" class="carousel-description">{{ carouselImages[carouselIndex].description }}</p>
                <a v-if="carouselImages[carouselIndex].source_url && !carouselImages[carouselIndex].description" :href="carouselImages[carouselIndex].source_url" target="_blank" rel="noopener noreferrer" class="carousel-source-link">View source ↗</a>
              </div>
              <div class="carousel-controls">
                <button class="carousel-btn" @click="prevCarousel" :disabled="carouselIndex === 0">←</button>
                <span class="carousel-counter">{{ carouselIndex + 1 }} / {{ carouselImages.length }}</span>
                <button class="carousel-btn" @click="nextCarousel" :disabled="carouselIndex === carouselImages.length - 1">→</button>
              </div>
            </div>
          </div>

          <div v-if="selectedEvent.news && selectedEvent.news.length > 0" class="detail-section detail-news">
            <div class="detail-heading-row">
              <span class="detail-label">Related News</span>
              <span class="detail-badge">{{ selectedEvent.news.length }}</span>
            </div>
            <div v-for="(item, i) in selectedEvent.news" :key="i" class="news-item">
              <a v-if="item.url" :href="item.url" target="_blank" rel="noopener noreferrer" class="news-link">
                <span class="news-title">{{ item.title }}</span>
                <span class="news-external-icon">↗</span>
              </a>
              <span v-else class="news-title">{{ item.title }}</span>
              <span v-if="item.author" class="news-author">— {{ item.author }}</span>
              <div v-if="item.extra && Object.keys(item.extra).length > 0" class="news-extra">
                <div v-for="(value, key) in item.extra" :key="key" class="structured-row">
                  <span class="structured-key">{{ formatLabel(key) }}</span>
                  <span v-if="isPrimitive(value)" class="structured-value">{{ formatPrimitive(value) }}</span>
                  <div v-else class="structured-json">{{ formatJson(value) }}</div>
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
          <li v-for="event in filteredEvents" :key="event.id" class="event-item" @click="selectEvent(event)">
            <span class="event-title">{{ event.title }}</span>
            <span class="event-date">{{ formatDate(event.date) }}</span>
          </li>
        </ul>
      </template>
    </aside>

    <transition name="chat-drawer">
      <div v-show="chatOpen" class="chat-shell">
        <button class="chat-backdrop" @click="chatOpen = false" aria-label="Close chat"></button>
        <aside class="chat-drawer" aria-label="Agent chat">
          <div class="chat-header">
            <div>
              <p class="chat-eyebrow">Agent</p>
              <h2 class="chat-title">Chat Assistant</h2>
              <p class="chat-subtitle">
                {{ selectedEvent ? `Context: ${selectedEvent.title}` : 'Monitoring event changes and refreshing the map automatically.' }}
              </p>
            </div>
            <div class="chat-actions">
              <button class="chat-action-btn" @click="refreshEvents">Refresh data</button>
              <button class="chat-close-btn" @click="chatOpen = false" aria-label="Close chat">×</button>
            </div>
          </div>

          <div class="chat-status">
            <span>{{ refreshStatus }}</span>
            <span class="chat-dot"></span>
            <span>{{ chatOriginLabel }}</span>
          </div>

          <iframe
            class="chat-frame"
            :src="chatUrl"
            title="Agent chat"
            referrerpolicy="strict-origin-when-cross-origin"
          ></iframe>
        </aside>
      </div>
    </transition>

    <div v-if="lightboxUrl" class="lightbox" @click.self="lightboxUrl = null">
      <div class="lightbox-content">
        <img :src="lightboxUrl" class="lightbox-image" />
      </div>
      <button class="lightbox-close" @click="lightboxUrl = null">×</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
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
const CHAT_REFRESH_EVENT = 'resonate:refresh'
const CHAT_REFRESH_POLL_MS = 15000
const DEFAULT_CHAT_URL = 'http://localhost:8001'

const events = ref([])
const loading = ref(true)
const selectedEvent = ref(null)
let map = null
let imageOverlays = {}
const showRaster = ref({})
const carouselIndex = ref(0)
const carouselImages = computed(() => selectedEvent.value?.carousel_images || [])
const lightboxUrl = ref(null)
const chatOpen = ref(false)
const refreshStatus = ref('Idle')
const selectedExtraEntries = computed(() => Object.entries(selectedEvent.value?.extra || {}))
const primitiveExtraEntries = computed(() =>
  selectedExtraEntries.value.filter(([, value]) => isPrimitive(value)),
)
const structuredExtraEntries = computed(() =>
  selectedExtraEntries.value.filter(([, value]) => !isPrimitive(value)),
)
const hasPrimitiveExtra = computed(() => primitiveExtraEntries.value.length > 0)
const hasStructuredExtra = computed(() => structuredExtraEntries.value.length > 0)

const isPlaying = ref(false)
const activeIndex = ref(0)
let playInterval = null
let chatRefreshInterval = null

const filterFrom = ref('')
const filterTo = ref('')
const chatUrl = import.meta.env.VITE_CHAINLIT_URL || DEFAULT_CHAT_URL
const chatOrigin = (() => {
  try {
    return new URL(chatUrl, window.location.origin).origin
  } catch {
    return window.location.origin
  }
})()
const chatOriginLabel = computed(() => {
  try {
    return new URL(chatUrl, window.location.origin).host
  } catch {
    return 'embedded chat'
  }
})

function isPrimitive(value) {
  return value === null || ['string', 'number', 'boolean'].includes(typeof value)
}

function isPrimitiveArray(value) {
  return Array.isArray(value) && value.every(item => isPrimitive(item))
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isObjectArray(value) {
  return Array.isArray(value) && value.every(item => isPlainObject(item))
}

function formatPrimitive(value) {
  if (value === null) return 'None'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

function formatLabel(value) {
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
}

function formatJson(value) {
  return JSON.stringify(value, null, 2)
}

function summarizeStructuredValue(value) {
  if (isPrimitiveArray(value)) {
    return `${value.length} item${value.length === 1 ? '' : 's'}`
  }
  if (isObjectArray(value)) {
    return `${value.length} record${value.length === 1 ? '' : 's'}`
  }
  if (isPlainObject(value)) {
    const count = Object.keys(value).length
    return `${count} field${count === 1 ? '' : 's'}`
  }
  return 'structured'
}

function formatCoordinate(coord) {
  return `${Number(coord[1]).toFixed(4)}, ${Number(coord[0]).toFixed(4)}`
}

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

watch(filterFrom, () => { activeIndex.value = 0; refreshMarkers() })
watch(filterTo, () => { activeIndex.value = 0; refreshMarkers() })
watch(chatOpen, (isOpen) => {
  if (isOpen) {
    refreshEvents()
    startChatRefreshPolling()
  } else {
    stopChatRefreshPolling()
  }
})

async function loadEvents() {
  const res = await fetch('/api/public/events')
  const data = await res.json()
  events.value = data.sort((a, b) => new Date(a.date) - new Date(b.date))
}

async function refreshEvents() {
  if (!map) return

  refreshStatus.value = 'Refreshing map data...'

  try {
    await loadEvents()
    syncSelectedEvent()
    refreshStatus.value = `Updated ${new Date().toLocaleTimeString()}`
  } catch (e) {
    console.error('Failed to refresh events:', e)
    refreshStatus.value = 'Refresh failed'
  }
}

function syncSelectedEvent() {
  if (!selectedEvent.value) {
    refreshMarkers()
    return
  }

  const updated = events.value.find(event => event.id === selectedEvent.value.id)
  if (!updated) {
    clearSelection()
    return
  }

  const visibleRasters = Object.entries(showRaster.value)
    .filter(([, isVisible]) => isVisible)
    .map(([filename]) => filename)

  selectedEvent.value = updated
  carouselIndex.value = Math.min(carouselIndex.value, Math.max(carouselImages.value.length - 1, 0))
  focusEventOnMap(updated)

  if (updated.images?.length) {
    visibleRasters.forEach(filename => {
      const image = updated.images.find(item => item.filename === filename)
      if (image) {
        showRaster.value[filename] = true
        toggleRaster(image)
      }
    })
  }
}

function refreshMarkers() {
  if (!map) return
  map.eachLayer(layer => {
    if (layer instanceof L.Marker) {
      map.removeLayer(layer)
    }
  })
  clearImageOverlay()
  if (!selectedEvent.value) {
    showAllMarkers()
  }
}

onMounted(async () => {
  try {
    await loadEvents()
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

  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('message', handleChatMessage)
})

onBeforeUnmount(() => {
  stopTimeline()
  stopChatRefreshPolling()
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('message', handleChatMessage)
})

function showAllMarkers() {
  const allCoords = []
  filteredEvents.value.forEach(event => {
    if (event.points && event.points.coordinates) {
      event.points.coordinates.forEach(coord => {
        L.marker([coord[1], coord[0]])
          .bindPopup(`<strong>${event.title}</strong><br>${formatDate(event.date)}`)
          .addTo(map)
        allCoords.push([coord[1], coord[0]])
      })
    }
  })

  fitMapToCoords(allCoords)
}

function selectEvent(event) {
  selectedEvent.value = event
  carouselIndex.value = 0
  focusEventOnMap(event)
}

function focusEventOnMap(event) {
  if (!map) return

  map.eachLayer(layer => {
    if (layer instanceof L.Marker) {
      map.removeLayer(layer)
    }
  })
  clearImageOverlay()

  if (event.points && event.points.coordinates) {
    const coords = []
    event.points.coordinates.forEach(coord => {
      L.marker([coord[1], coord[0]])
        .bindPopup(`<strong>${event.title}</strong><br>${formatDate(event.date)}`)
        .addTo(map)
      coords.push([coord[1], coord[0]])
    })

    fitMapToCoords(coords)
  }

  showRaster.value = {}
}

function clearImageOverlay() {
  Object.values(imageOverlays).forEach(overlay => {
    map.removeLayer(overlay)
  })
  imageOverlays = {}
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

function nextCarousel() {
  if (carouselIndex.value < carouselImages.value.length - 1) {
    carouselIndex.value++
  }
}

function prevCarousel() {
  if (carouselIndex.value > 0) {
    carouselIndex.value--
  }
}

function toggleRaster(img) {
  if (!img.bounds || !img.preview) return

  const baseUrl = window.location.origin
  const imageUrl = `${baseUrl}/images/${img.preview}`
  const bounds = img.bounds
  const imageBounds = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]

  // Toggle this specific image
  if (showRaster.value[img.filename]) {
    if (!imageOverlays[img.filename]) {
      imageOverlays[img.filename] = L.imageOverlay(imageUrl, imageBounds, { opacity: 1.0 }).addTo(map)
    }
  } else {
    if (imageOverlays[img.filename]) {
      map.removeLayer(imageOverlays[img.filename])
      delete imageOverlays[img.filename]
    }
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
    carouselIndex.value = 0
    focusEventOnMap(event)
  }
}

function toggleChat() {
  chatOpen.value = !chatOpen.value
}

function startChatRefreshPolling() {
  stopChatRefreshPolling()
  chatRefreshInterval = window.setInterval(() => {
    refreshEvents()
  }, CHAT_REFRESH_POLL_MS)
}

function stopChatRefreshPolling() {
  if (chatRefreshInterval) {
    window.clearInterval(chatRefreshInterval)
    chatRefreshInterval = null
  }
}

function handleChatMessage(event) {
  if (event.origin !== chatOrigin) return

  const payload = typeof event.data === 'string'
    ? event.data
    : event.data?.type || event.data?.message

  if (payload === CHAT_REFRESH_EVENT) {
    refreshEvents()
  }
}

function handleKeydown(event) {
  if (event.key !== 'Escape') return

  if (lightboxUrl.value) {
    lightboxUrl.value = null
    return
  }

  if (chatOpen.value) {
    chatOpen.value = false
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
  position: relative;
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

.chat-toggle {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 1200;
  border: none;
  border-radius: 999px;
  background: rgba(24, 34, 29, 0.9);
  color: white;
  padding: 0.8rem 1.1rem;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  cursor: pointer;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  transition: transform 0.2s ease, background 0.2s ease;
}

.chat-toggle:hover {
  transform: translateY(-1px);
  background: rgba(34, 51, 43, 0.96);
}

.chat-toggle.active {
  background: #ffffff;
  color: #1f3328;
}

.chat-shell {
  position: absolute;
  inset: 0;
  z-index: 1300;
  pointer-events: none;
}

.chat-backdrop {
  position: absolute;
  inset: 0;
  border: none;
  background: rgba(6, 10, 8, 0.14);
  backdrop-filter: blur(2px);
  pointer-events: auto;
}

.chat-drawer {
  position: absolute;
  top: 0;
  right: 0;
  width: min(440px, calc(100vw - 2rem));
  height: 100%;
  background: #f4f2ea;
  color: #17231d;
  box-shadow: -18px 0 48px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  pointer-events: auto;
}

.chat-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1rem 0.75rem;
  border-bottom: 1px solid rgba(23, 35, 29, 0.1);
}

.chat-eyebrow {
  margin: 0 0 0.3rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #516256;
}

.chat-title {
  margin: 0;
  font-size: 1.15rem;
}

.chat-subtitle {
  margin: 0.35rem 0 0;
  font-size: 0.85rem;
  line-height: 1.4;
  color: #4d5d52;
}

.chat-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chat-action-btn,
.chat-close-btn {
  border: 1px solid rgba(23, 35, 29, 0.12);
  background: white;
  color: #17231d;
  border-radius: 999px;
  cursor: pointer;
}

.chat-action-btn {
  padding: 0.55rem 0.9rem;
  font-size: 0.8rem;
  font-weight: 600;
}

.chat-close-btn {
  width: 2.2rem;
  height: 2.2rem;
  font-size: 1.3rem;
}

.chat-status {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.55);
  border-bottom: 1px solid rgba(23, 35, 29, 0.08);
  font-size: 0.76rem;
  color: #5f6e64;
}

.chat-dot {
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: currentColor;
}

.chat-frame {
  flex: 1;
  width: 100%;
  border: none;
  background: white;
}

.chat-drawer-enter-active,
.chat-drawer-leave-active {
  transition: opacity 0.2s ease;
}

.chat-drawer-enter-active .chat-drawer,
.chat-drawer-leave-active .chat-drawer {
  transition: transform 0.25s ease;
}

.chat-drawer-enter-from,
.chat-drawer-leave-to {
  opacity: 0;
}

.chat-drawer-enter-from .chat-drawer,
.chat-drawer-leave-to .chat-drawer {
  transform: translateX(100%);
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

.timeline-empty {
  text-align: center;
  padding: 0.5rem;
  color: #888;
  font-size: 0.8rem;
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
  border-radius: 10px;
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

.detail-section {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 1rem;
}

.detail-section-hero {
  background: rgba(255, 255, 255, 0.12);
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
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

.detail-heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.detail-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.72rem;
  font-weight: 600;
}

.coordinate-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.coordinate-chip {
  padding: 0.45rem 0.65rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  font-size: 0.84rem;
  line-height: 1.2;
}

.fact-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
}

.fact-card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.8rem 0.9rem;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.14);
}

.fact-key {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  opacity: 0.75;
  font-weight: 700;
}

.fact-value {
  font-size: 0.95rem;
  line-height: 1.45;
  word-break: break-word;
}

.structured-details {
  width: 100%;
}

.structured-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  cursor: pointer;
  list-style: none;
}

.structured-summary::-webkit-details-marker {
  display: none;
}

.structured-groups {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-top: 0.95rem;
}

.structured-group {
  padding-top: 0.85rem;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.structured-group:first-child {
  padding-top: 0;
  border-top: none;
}

.structured-group-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
}

.structured-group-title {
  font-size: 0.92rem;
  font-weight: 700;
}

.structured-group-meta {
  font-size: 0.74rem;
  opacity: 0.72;
  text-transform: uppercase;
}

.structured-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.structured-pill {
  padding: 0.4rem 0.55rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 0.82rem;
}

.structured-stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.structured-card {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 0.85rem;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.14);
}

.structured-card-index {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 700;
  opacity: 0.72;
}

.structured-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.structured-key {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  opacity: 0.72;
  font-weight: 600;
}

.structured-value {
  font-size: 0.94rem;
  line-height: 1.45;
  word-break: break-word;
}

.structured-json {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.82rem;
  line-height: 1.45;
  padding: 0.7rem 0.8rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  font-family: "IBM Plex Mono", monospace;
}

.news-item {
  margin-top: 0.8rem;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.14);
  border-radius: 12px;
}

.news-title {
  font-weight: 600;
  display: block;
  margin-bottom: 0.25rem;
}

.news-link {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #4ade80;
  text-decoration: none;
  font-weight: 600;
  transition: opacity 0.2s;
}

.news-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.news-external-icon {
  font-size: 0.8rem;
}

.news-author {
  display: block;
  font-size: 0.85rem;
  opacity: 0.75;
  margin-top: 0.15rem;
}

.detail-carousel {
  gap: 0.75rem;
}

.carousel {
  display: flex;
  flex-direction: column;
  height: 300px;
}

.carousel-image-wrapper {
  flex: 1;
  min-height: 0;
}

.carousel-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.carousel-meta {
  min-height: 2.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.carousel-source-link {
  display: inline-block;
  margin-top: 0.35rem;
  font-size: 0.8rem;
  color: #4ade80;
  text-decoration: none;
}

.carousel-source-link:hover {
  text-decoration: underline;
}

.carousel-description,
.carousel-description-link {
  margin-top: 0.35rem;
  font-size: 0.85rem;
  opacity: 0.85;
  line-height: 1.4;
}

.carousel-description-link {
  color: #4ade80;
  text-decoration: none;
}

.carousel-description-link:hover {
  text-decoration: underline;
}

.carousel-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 0.5rem;
}

.carousel-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 0.3rem 0.7rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.carousel-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
}

.carousel-btn:disabled {
  opacity: 0.3;
  cursor: default;
}

.carousel-counter {
  font-size: 0.85rem;
  opacity: 0.75;
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

.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  cursor: pointer;
}

.lightbox-content {
  width: 90vw;
  height: 90vh;
}

.lightbox-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: default;
}

.lightbox-close {
  position: absolute;
  top: 1rem;
  right: 1.5rem;
  background: none;
  border: none;
  color: #fff;
  font-size: 2.5rem;
  cursor: pointer;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.lightbox-close:hover {
  opacity: 1;
}
</style>
