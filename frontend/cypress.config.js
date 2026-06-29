import { defineConfig } from 'cypress'
import dotenv from 'dotenv'

dotenv.config({ path: '../.env' })

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost',
    env: {
      ADMIN_PASSWORD: process.env.ADMIN_PASSWORD,
    },
  },
})
