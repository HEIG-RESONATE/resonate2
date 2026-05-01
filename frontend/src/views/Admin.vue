<template>
  <div v-if="authenticated" class="admin">
    <nav>
      <RouterLink to="/">Map</RouterLink>
      <span>Admin</span>
    </nav>
    <main>
      <h1>Events</h1>

      <form @submit.prevent="saveEvent" class="event-form">
        <input v-model="form.title" placeholder="Title" required />
        <input type="datetime-local" v-model="form.date" required />
        <div class="points-input">
          <label>Points (lat,lng pairs separated by semicolons):</label>
          <input
            v-model="form.pointsStr"
            placeholder="46.5197,7.0;46.52,7.01"
          />
        </div>
        <button type="submit">{{ editing ? 'Update' : 'Add' }}</button>
        <button v-if="editing" type="button" @click="cancelEdit">Cancel</button>
      </form>

      <table v-if="events.length">
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
              <span v-else>-</span>
            </td>
            <td>
              <button @click="editEvent(event)">Edit</button>
              <button @click="deleteEvent(event.id)" class="danger">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else>No events yet.</p>
    </main>
  </div>
  <form v-else class="login" @submit.prevent="login">
    <input v-model="password" type="password" placeholder="Password" required />
    <button type="submit">Login</button>
    <p v-if="error" class="error">{{ error }}</p>
  </form>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const password = ref('')
const authenticated = ref(false)
const error = ref('')
const events = ref([])
const editing = ref(null)
const form = ref({ title: '', date: '', pointsStr: '' })

onMounted(async () => {
  if (sessionStorage.getItem('adminToken')) {
    authenticated.value = true
    await loadEvents()
  }
})

async function loadEvents() {
  const res = await fetch('/api/events', {
    headers: { 'Authorization': `Bearer ${sessionStorage.getItem('adminToken')}` },
  })
  events.value = await res.json()
}

function resetForm() {
  form.value = { title: '', date: '', pointsStr: '' }
  editing.value = null
}

function editEvent(event) {
  editing.value = event.id
  form.value = {
    title: event.title,
    date: event.date.slice(0, 16),
    pointsStr: event.points?.coordinates?.map(c => c.join(',')).join(';') || '',
  }
}

async function saveEvent() {
  const points = form.value.pointsStr
    ? form.value.pointsStr.split(';').map(pair => pair.split(',').map(Number))
    : null

  const payload = {
    title: form.value.title,
    date: new Date(form.value.date).toISOString(),
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
</script>

<style scoped>
.admin {
  min-height: 100vh;
  padding: 2rem;
}

nav {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

nav a {
  color: #333;
  text-decoration: none;
}

nav span {
  font-weight: bold;
}

.event-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.event-form input {
  padding: 0.5rem;
  font-size: 1rem;
}

.points-input {
  flex: 1;
  min-width: 200px;
}

.points-input label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
}

button {
  padding: 0.5rem 1rem;
  font-size: 1rem;
  cursor: pointer;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background: #f5f5f5;
}

.danger {
  color: red;
  border-color: red;
}

.login {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  gap: 1rem;
  flex-direction: column;
}

.error {
  color: red;
}
</style>
