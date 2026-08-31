<template>
  <div class="page">
    <PageHeader title="Aportación en el local" back="/" back-label="Registro" />

    <div class="card stack">
      <!-- Fecha de registro -->
      <div>
        <label for="fecha-local" class="section-title" style="margin-bottom:0.2rem">Fecha del registro</label>
        <input id="fecha-local" class="input" type="date" v-model="fechaRegistro" style="margin-bottom: 1rem" />
      </div>

      <!-- Buscar por vivienda o nombre libre -->
      <div>
        <p class="section-title">Origen</p>
        <div class="row" style="gap:0.5rem;margin-bottom:0.5rem">
          <button class="btn" :class="modo === 'vivienda' ? 'btn-primary' : 'btn-ghost'"
                  @click="modo = 'vivienda'">Por vivienda</button>
          <button class="btn" :class="modo === 'persona' ? 'btn-primary' : 'btn-ghost'"
                  @click="modo = 'persona'">Sin domicilio</button>
        </div>
      </div>

      <template v-if="modo === 'vivienda'">
        <div>
          <label>Calle</label>
          <BuscadorCalle v-model="calle" />
        </div>
        <SelectorVivienda v-if="calle" v-model="vivienda" />
      </template>

      <template v-else>
        <div>
          <label for="nombre-persona">Nombre de la persona</label>
          <input id="nombre-persona" class="input" type="text" v-model="nombrePersona"
                 placeholder="Nombre y apellidos" required />
        </div>
      </template>

      <!-- Datos de la aportación -->
      <div>
        <label for="importe-local">Importe (€)</label>
        <input id="importe-local" class="input" type="number" step="0.01" min="0.01"
               v-model="importeStr" placeholder="0.00" />
      </div>
      <div>
        <label for="pago-local">Forma de pago</label>
        <select id="pago-local" class="select" v-model="formaPago">
          <option value="efectivo">💵 Efectivo</option>
          <option value="bizum">📱 Bizum</option>
        </select>
      </div>
      <div>
        <label for="obs-local">Observaciones</label>
        <input id="obs-local" class="input" type="text" v-model="observaciones" placeholder="Opcional" />
      </div>

      <button class="btn btn-primary btn-full btn-lg" @click="guardar"
              :disabled="guardando || !puedeGuardar">
        <span v-if="guardando" class="spinner" style="width:18px;height:18px;border-width:2px"></span>
        <span v-else>✅ Registrar aportación</span>
      </button>
    </div>

    <div v-if="toast" class="toast" :class="{ error: toastError }">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import BuscadorCalle from '../components/BuscadorCalle.vue'
import SelectorVivienda from '../components/SelectorVivienda.vue'
import api from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const modo = ref('vivienda')
const fechaRegistro = ref(new Date().toISOString().slice(0, 10))
const calle = ref(null)
const vivienda = ref({ portal: '', piso: '', puerta: '' })
const nombrePersona = ref('')
const importeStr = ref('')
const formaPago = ref('efectivo')
const observaciones = ref('')
const guardando = ref(false)
const toast = ref('')
const toastError = ref(false)

const puedeGuardar = computed(() => {
  if (!importeStr.value || Number(importeStr.value) <= 0) return false
  if (modo.value === 'persona' && !nombrePersona.value.trim()) return false
  return true
})

async function guardar() {
  guardando.value = true
  try {
    const body = {
      origen: 'local',
      equipo_id: auth.equipoId,
      importe: Number(importeStr.value),
      forma_pago: formaPago.value,
      fecha: fechaRegistro.value,
      anio_campania: Number(fechaRegistro.value.slice(0, 4)),
      observaciones: observaciones.value || null,
    }

    if (modo.value === 'vivienda' && calle.value && vivienda.value.portal) {
      // Obtener o crear vivienda
      const resV = await api.post('/viviendas', {
        calle_id: calle.value.id,
        portal: vivienda.value.portal,
        piso: vivienda.value.piso || null,
        puerta: vivienda.value.puerta || null,
      })
      body.vivienda_id = resV.data.id
    } else if (modo.value === 'persona') {
      body.nombre_persona = nombrePersona.value.trim()
    }

    await api.post('/aportaciones', body)
    mostrarToast('✅ Aportación registrada')
    resetForm()
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error al registrar', true)
  } finally {
    guardando.value = false
  }
}

function resetForm() {
  calle.value = null
  vivienda.value = { portal: '', piso: '', puerta: '' }
  nombrePersona.value = ''
  importeStr.value = ''
  formaPago.value = 'efectivo'
  observaciones.value = ''
}

function mostrarToast(msg, esError = false) {
  toast.value = msg
  toastError.value = esError
  setTimeout(() => { toast.value = '' }, 2700)
}
</script>
