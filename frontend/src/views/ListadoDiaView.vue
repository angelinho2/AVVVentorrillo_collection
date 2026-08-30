<template>
  <div class="page">
    <PageHeader title="Mi día" back="/" back-label="Registro">
      <template #right>
        <span class="badge badge-success" v-if="totalDia > 0">{{ formatEur(totalDia) }}</span>
      </template>
    </PageHeader>

    <div v-if="cargando" style="display:flex;justify-content:center;padding:2rem">
      <div class="spinner"></div>
    </div>

    <div v-else-if="!aportaciones.length" class="card" style="text-align:center;color:var(--clr-muted);padding:2rem">
      No hay aportaciones registradas hoy
    </div>

    <div v-else class="stack">
      <div v-for="a in aportaciones" :key="a.id" class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div>
            <div style="font-weight:600">{{ formatEur(a.importe) }}
              <span class="badge" :class="a.forma_pago === 'bizum' ? 'badge-warning' : 'badge-muted'" style="margin-left:0.4rem">
                {{ a.forma_pago === 'bizum' ? '📱' : '💵' }} {{ a.forma_pago }}
              </span>
            </div>
            <div style="font-size:0.8rem;color:var(--clr-muted);margin-top:0.2rem">
              {{ a.creado_en ? new Date(a.creado_en).toLocaleTimeString('es-ES', {hour:'2-digit',minute:'2-digit'}) : '' }}
              · {{ a.origen === 'local' ? 'Local' : 'Puerta' }}
            </div>
            <div v-if="a.observaciones" style="font-size:0.8rem;color:var(--clr-muted)">{{ a.observaciones }}</div>
          </div>
          <div style="display:flex;gap:0.4rem">
            <button class="btn btn-ghost btn-sm" @click="editar(a)">✏️</button>
            <button class="btn btn-ghost btn-sm" style="color:var(--clr-danger)" @click="confirmarBorrar(a)">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal edición -->
    <div v-if="editando" class="modal-overlay" @click.self="editando = null">
      <div class="modal-box stack">
        <h2>Editar aportación</h2>
        <div>
          <label for="edit-importe">Importe (€)</label>
          <input id="edit-importe" class="input" type="number" step="0.01" v-model="editForm.importe" />
        </div>
        <div>
          <label for="edit-pago">Forma de pago</label>
          <select id="edit-pago" class="select" v-model="editForm.forma_pago">
            <option value="efectivo">💵 Efectivo</option>
            <option value="bizum">📱 Bizum</option>
          </select>
        </div>
        <div>
          <label for="edit-obs">Observaciones</label>
          <input id="edit-obs" class="input" type="text" v-model="editForm.observaciones" />
        </div>
        <div class="row">
          <button class="btn btn-ghost" @click="editando = null">Cancelar</button>
          <button class="btn btn-primary" @click="guardarEdicion">Guardar</button>
        </div>
      </div>
    </div>

    <!-- Confirmar borrar -->
    <div v-if="borrandoId" class="modal-overlay" @click.self="borrandoId = null">
      <div class="modal-box stack">
        <h2>¿Borrar aportación?</h2>
        <p style="color:var(--clr-muted)">Esta acción no se puede deshacer.</p>
        <div class="row">
          <button class="btn btn-ghost" @click="borrandoId = null">Cancelar</button>
          <button class="btn btn-danger" @click="borrar">Borrar</button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast" :class="{ error: toastError }">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import api from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const aportaciones = ref([])
const cargando = ref(false)
const editando = ref(null)
const editForm = ref({})
const borrandoId = ref(null)
const toast = ref('')
const toastError = ref(false)

const totalDia = computed(() => aportaciones.value.reduce((s, a) => s + Number(a.importe), 0))

function formatEur(n) {
  return Number(n).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

onMounted(cargar)

async function cargar() {
  cargando.value = true
  try {
    const hoy = new Date().toISOString().slice(0, 10)
    const res = await api.get('/aportaciones', { params: { fecha: hoy, equipo_id: auth.equipoId } })
    aportaciones.value = res.data
  } finally {
    cargando.value = false
  }
}

function editar(a) {
  editando.value = a
  editForm.value = { importe: a.importe, forma_pago: a.forma_pago, observaciones: a.observaciones || '' }
}

async function guardarEdicion() {
  try {
    await api.patch(`/aportaciones/${editando.value.id}`, editForm.value)
    editando.value = null
    mostrarToast('Guardado')
    cargar()
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error', true)
  }
}

function confirmarBorrar(a) { borrandoId.value = a.id }

async function borrar() {
  try {
    await api.delete(`/aportaciones/${borrandoId.value}`)
    borrandoId.value = null
    mostrarToast('Borrado')
    cargar()
  } catch {
    mostrarToast('Error al borrar', true)
  }
}

function mostrarToast(msg, esError = false) {
  toast.value = msg; toastError.value = esError
  setTimeout(() => { toast.value = '' }, 2500)
}
</script>
