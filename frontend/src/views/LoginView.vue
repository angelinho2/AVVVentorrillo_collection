<template>
  <div class="login-bg">
    <div class="login-card">
      <div class="login-logo">🏘️</div>
      <h1 class="login-title">AVV Ventorrillo</h1>
      <p class="login-sub">Contribuciones vecinales</p>

      <form @submit.prevent="onSubmit" class="stack" style="margin-top:1.5rem">
        <div>
          <label for="usuario">Usuario</label>
          <input id="usuario" class="input" type="text" v-model="form.usuario"
                 placeholder="nombre_usuario" autocomplete="username" required />
        </div>
        <div style="position:relative; text-align:left">
          <label for="password">Contraseña</label>
          <div style="position:relative">
            <input id="password" class="input" :type="mostrarPassword ? 'text' : 'password'" v-model="form.password"
                   placeholder="••••••••" autocomplete="current-password" required style="padding-right: 2.5rem;" />
            <button type="button" @click="mostrarPassword = !mostrarPassword" style="position:absolute; right:0.5rem; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; font-size:1.2rem; color:var(--clr-muted)">
              {{ mostrarPassword ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>
        <div>
          <label for="equipo">Equipo de cobro</label>
          <select id="equipo" class="select" v-model="form.equipo_id" required>
            <option value="" disabled>Selecciona equipo</option>
            <option v-for="e in equipos" :key="e.id" :value="e.id">{{ e.nombre }}</option>
          </select>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>

        <button class="btn btn-primary btn-full btn-lg" type="submit" :disabled="cargando">
          <span v-if="cargando" class="spinner" style="width:18px;height:18px;border-width:2px"></span>
          <span v-else>Entrar</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()
const equipos = ref([])
const cargando = ref(false)
const error = ref('')
const form = ref({ usuario: '', password: '', equipo_id: '' })
const mostrarPassword = ref(false)

onMounted(async () => {
  try {
    const res = await api.get('/equipos', { params: { solo_activos: true } })
    equipos.value = res.data
  } catch {
    // Si falla (sin token), no hay problema: el endpoint de equipos permite solo_activos sin auth
    // En este caso bootstrap inicial: mostrar vacío y el primer login creará sesión
  }
})

async function onSubmit() {
  error.value = ''
  // Los cobradores necesitan equipo; el admin puede omitirlo si no hay equipos aún
  if (!form.value.equipo_id && equipos.value.length > 0) {
    error.value = 'Selecciona un equipo'
    return
  }
  cargando.value = true
  try {
    await auth.login(form.value.usuario, form.value.password, form.value.equipo_id ? Number(form.value.equipo_id) : null)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Error al iniciar sesión'
  } finally {
    cargando.value = false
  }
}
</script>

<style scoped>
.login-bg {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(ellipse at top, #1e3a5f 0%, var(--clr-bg) 60%);
  padding: 1.5rem;
}
.login-card {
  width: 100%;
  max-width: 380px;
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-radius: var(--radius-lg);
  padding: 2rem;
  box-shadow: var(--shadow);
  text-align: center;
}
.login-logo { font-size: 3rem; margin-bottom: 0.5rem; }
.login-title { font-size: 1.4rem; font-weight: 700; }
.login-sub { color: var(--clr-muted); font-size: 0.9rem; margin-top: 0.2rem; }
.error-msg { color: var(--clr-danger); font-size: 0.9rem; text-align: center; }
</style>
