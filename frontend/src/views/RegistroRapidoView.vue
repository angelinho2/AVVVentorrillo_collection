<template>
  <div class="page">
    <!-- Cabecera -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem">
      <h1>Registro rápido</h1>
      <div style="text-align:right">
        <div style="font-size:0.75rem;color:var(--clr-muted)">{{ auth.usuario?.nombre_usuario }}</div>
        <button class="btn btn-ghost btn-sm" @click="mostrarCambioEquipo = true">
          {{ equipoNombre }} ▾
        </button>
      </div>
    </div>

    <!-- Fecha de registro -->
    <div class="card stack" style="margin-bottom:0.75rem">
      <label for="fecha-visita" class="section-title" style="margin-bottom:0.2rem">Fecha del registro</label>
      <input id="fecha-visita" class="input" type="date" v-model="fechaRegistro" />
    </div>

    <!-- 1. Calle -->
    <div class="card stack" style="margin-bottom:0.75rem">
      <p class="section-title">1. Calle</p>
      <BuscadorCalle v-model="calle" />
    </div>

    <!-- 2. Vivienda -->
    <div class="card stack" style="margin-bottom:0.75rem" v-if="calle">
      <p class="section-title">2. Vivienda</p>
      <SelectorVivienda v-model="vivienda" />
      <button class="btn btn-ghost btn-sm" @click="buscarVivienda" :disabled="!vivienda.portal">
        🔍 Buscar vivienda
      </button>
    </div>

    <!-- Histórico compacto -->
    <div style="margin-bottom:0.75rem" v-if="viviendaId">
      <HistoricoVivienda :vivienda-id="viviendaId" />
    </div>

    <!-- 3. Resultado -->
    <div class="card stack" style="margin-bottom:0.75rem" v-if="calle && vivienda.portal">
      <p class="section-title">3. Resultado de la visita</p>
      <div class="resultado-grid">
        <button
          v-for="r in RESULTADOS"
          :key="r.value"
          class="btn-resultado"
          :class="[r.value, { activo: resultado === r.value }]"
          @click="resultado = r.value"
        >
          {{ r.label }}
        </button>
      </div>
    </div>

    <!-- 4. Aportación (solo si resultado = aporta) -->
    <div class="card stack" style="margin-bottom:0.75rem" v-if="resultado === 'aporta'">
      <p class="section-title">4. Datos de la aportación</p>
      <div>
        <label for="importe">Importe (€)</label>
        <input id="importe" class="input" type="number" step="0.01" min="0.01"
               v-model="importeStr" placeholder="0.00" />
      </div>
      <div>
        <label for="forma-pago">Forma de pago</label>
        <select id="forma-pago" class="select" v-model="formaPago">
          <option value="efectivo">💵 Efectivo</option>
          <option value="bizum">📱 Bizum</option>
        </select>
      </div>
      <div>
        <label for="obs-aporta">Observaciones</label>
        <input id="obs-aporta" class="input" type="text" v-model="observaciones" placeholder="Opcional" />
      </div>
    </div>

    <!-- Observaciones generales -->
    <div class="card" style="margin-bottom:0.75rem" v-if="resultado && resultado !== 'aporta'">
      <label for="obs-general">Observaciones</label>
      <input id="obs-general" class="input" type="text" v-model="observaciones" placeholder="Opcional" />
    </div>

    <!-- Botón guardar -->
    <button
      v-if="resultado"
      class="btn btn-primary btn-full btn-lg"
      @click="guardar"
      :disabled="guardando || !puedeGuardar"
    >
      <span v-if="guardando" class="spinner" style="width:18px;height:18px;border-width:2px"></span>
      <span v-else>✅ Guardar visita</span>
    </button>

    <!-- Toast -->
    <div v-if="toast" class="toast" :class="{ error: toastError }">{{ toast }}</div>

    <!-- Modal cambio de equipo -->
    <div v-if="mostrarCambioEquipo" class="modal-overlay" @click.self="mostrarCambioEquipo = false">
      <div class="modal-box">
        <h2 style="margin-bottom:1rem">Cambiar equipo</h2>
        <div class="stack">
          <button
            v-for="e in equipos"
            :key="e.id"
            class="btn btn-ghost"
            :class="{ 'btn-primary': e.id === auth.equipoId }"
            @click="cambiarEquipo(e)"
          >{{ e.nombre }}</button>
          <button class="btn btn-ghost" style="color:var(--clr-danger)" @click="auth.logout(); router.push('/login')">
            🚪 Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BuscadorCalle from '../components/BuscadorCalle.vue'
import SelectorVivienda from '../components/SelectorVivienda.vue'
import HistoricoVivienda from '../components/HistoricoVivienda.vue'
import api from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()

const RESULTADOS = [
  { value: 'aporta',           label: '💰 Aporta' },
  { value: 'no_abre',          label: '🚪 No abre' },
  { value: 'no_aporta',        label: '❌ No aporta' },
  { value: 'reintentar',       label: '🔄 Reintentar' },
  { value: 'pasara_por_local', label: '🏛️ Pasará por el local' },
]

const calle = ref(null)
const fechaRegistro = ref(new Date().toISOString().slice(0, 10))
const vivienda = ref({ portal: '', piso: '', puerta: '' })
const viviendaId = ref(null)
const resultado = ref('')
const importeStr = ref('')
const formaPago = ref('efectivo')
const observaciones = ref('')
const guardando = ref(false)
const toast = ref('')
const toastError = ref(false)
const mostrarCambioEquipo = ref(false)
const equipos = ref([])
const equipoNombre = computed(() => {
  const e = equipos.value.find(e => e.id === auth.equipoId)
  return e ? e.nombre : 'Equipo'
})

const puedeGuardar = computed(() => {
  if (!resultado.value) return false
  if (resultado.value === 'aporta' && (!importeStr.value || Number(importeStr.value) <= 0)) return false
  return true
})

onMounted(async () => {
  const res = await api.get('/equipos', { params: { solo_activos: true } })
  equipos.value = res.data
})

async function buscarVivienda() {
  if (!calle.value || !vivienda.value.portal) return
  viviendaId.value = null
  try {
    const res = await api.get('/viviendas', {
      params: {
        calle_id: calle.value.id,
        portal: vivienda.value.portal,
        piso: vivienda.value.piso || undefined,
        puerta: vivienda.value.puerta || undefined,
      }
    })
    if (res.data.length > 0) viviendaId.value = res.data[0].id
  } catch { /* ignorar */ }
}

async function guardar() {
  guardando.value = true
  try {
    // Obtener o crear vivienda
    let vId = viviendaId.value
    if (!vId) {
      const res = await api.post('/viviendas', {
        calle_id: calle.value.id,
        portal: vivienda.value.portal,
        piso: vivienda.value.piso || null,
        puerta: vivienda.value.puerta || null,
      })
      vId = res.data.id
    }

    const body = {
      vivienda_id: vId,
      equipo_id: auth.equipoId,
      fecha: fechaRegistro.value,
      resultado: resultado.value,
      observaciones: observaciones.value || null,
    }

    if (resultado.value === 'aporta') {
      body.aportacion = {
        importe: Number(importeStr.value),
        forma_pago: formaPago.value,
        observaciones: observaciones.value || null,
      }
    }

    await api.post('/visitas', body)
    mostrarToast('✅ Visita guardada correctamente')
    resetForm()
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error al guardar', true)
  } finally {
    guardando.value = false
  }
}

function resetForm() {
  calle.value = null
  vivienda.value = { portal: '', piso: '', puerta: '' }
  viviendaId.value = null
  resultado.value = ''
  importeStr.value = ''
  formaPago.value = 'efectivo'
  observaciones.value = ''
}

function mostrarToast(msg, esError = false) {
  toast.value = msg
  toastError.value = esError
  setTimeout(() => { toast.value = '' }, 2700)
}

async function cambiarEquipo(e) {
  await auth.cambiarEquipo(e.id)
  mostrarCambioEquipo.value = false
}
</script>
