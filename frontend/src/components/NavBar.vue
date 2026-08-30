<template>
  <nav class="navbar">
    <RouterLink to="/" class="nav-item" :class="{ active: route.path === '/' }">
      <span class="nav-icon">🏠</span>
      <span>Registro</span>
    </RouterLink>
    <RouterLink to="/local" class="nav-item" :class="{ active: route.path === '/local' }">
      <span class="nav-icon">🏛️</span>
      <span>Local</span>
    </RouterLink>
    <RouterLink to="/dia" class="nav-item" :class="{ active: route.path === '/dia' }">
      <span class="nav-icon">📋</span>
      <span>Mi día</span>
    </RouterLink>
    <RouterLink v-if="auth.isAdmin" to="/admin" class="nav-item" :class="{ active: route.path === '/admin' }">
      <span class="nav-icon">⚙️</span>
      <span>Admin</span>
    </RouterLink>
    <button class="nav-item nav-logout" @click="cerrarSesion" title="Cerrar sesión">
      <span class="nav-icon">🚪</span>
      <span>Salir</span>
    </button>
  </nav>
</template>

<script setup>
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

function cerrarSesion() {
  if (confirm('¿Cerrar sesión?')) {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.navbar {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: var(--clr-surface);
  border-top: 1px solid var(--clr-border);
  display: flex;
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom);
}
.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.6rem 0.4rem 0.5rem;
  text-decoration: none;
  color: var(--clr-muted);
  font-size: 0.72rem;
  font-weight: 500;
  transition: color var(--transition);
  gap: 0.2rem;
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
}
.nav-item:hover, .nav-item.active { color: var(--clr-primary); }
.nav-logout:hover { color: var(--clr-danger, #e53e3e); }
.nav-icon { font-size: 1.3rem; }
</style>
