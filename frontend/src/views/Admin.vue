<template>
  <div v-if="authenticated" class="admin">
    <nav>
      <RouterLink to="/">Map</RouterLink>
      <span>Admin</span>
    </nav>
    <main>
      <h1>Admin</h1>
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

onMounted(() => {
  if (sessionStorage.getItem('adminToken')) {
    authenticated.value = true
  }
})

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

.login {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  gap: 1rem;
  flex-direction: column;
}

input {
  padding: 0.5rem;
  font-size: 1rem;
}

button {
  padding: 0.5rem 1rem;
  font-size: 1rem;
  cursor: pointer;
}

.error {
  color: red;
}
</style>
