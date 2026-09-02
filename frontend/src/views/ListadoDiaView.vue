<template>
  <div class="page">
    <PageHeader title="Mi día" back="/" back-label="Registro">
      <template #right>
        <span class="badge badge-success" v-if="totalDia > 0">{{ formatEur(totalDia) }}</span>
      </template>
    </PageHeader>

    <!-- Pestañas -->
    <div class="tab-bar" style="padding:0 1rem; margin-top:1rem">
      <button class="tab-btn" :class="{ active: tab === 'aportaciones' }" @click="tab = 'aportaciones'">Mis aportaciones</button>
      <button class="tab-btn" :class="{ active: tab === 'reintentos' }" @click="tab = 'reintentos'">Reintentos</button>
    </div>

    <div v-if="tab === 'aportaciones'" class="stack" style="margin-top:1rem">
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
              <div v-if="a.vivienda" style="font-weight:500;margin-top:0.3rem">
                {{ a.vivienda.calle?.nombre }} {{ a.vivienda.portal }}
                <span v-if="a.vivienda.piso">{{ a.vivienda.piso }}</span>
                <span v-if="a.vivienda.puerta">{{ a.vivienda.puerta }}</span>
              </div>
              <div v-else-if="a.nombre_persona" style="font-weight:500;margin-top:0.3rem">
                👤 {{ a.nombre_persona }}
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
    </div>

    <!-- Pestaña Reintentos -->
    <div v-if="tab === 'reintentos'" class="stack" style="margin-top:1rem">
      <div class="card row" style="margin-bottom:1rem">
        <div>
          <label for="fecha-reintentos">Día de la visita original</label>
          <input id="fecha-reintentos" class="input" type="date" v-model="fechaReintentos" @change="cargarReintentos" />
        </div>
      </div>
      
      <div v-if="cargandoReintentos" style="display:flex;justify-content:center;padding:2rem">
        <div class="spinner"></div>
      </div>
      
      <div v-else-if="!visitasReintentar.length" class="card" style="text-align:center;color:var(--clr-muted);padding:2rem">
        No hay viviendas a las que volver este día
      </div>
      
      <div v-else class="stack">
        <div v-for="v in visitasReintentar" :key="v.id" class="card">
          <div style="font-weight:600; font-size:1.1rem">
            {{ v.vivienda?.calle?.nombre }} {{ v.vivienda?.portal }}
            <span v-if="v.vivienda?.piso">{{ v.vivienda.piso }}</span>
            <span v-if="v.vivienda?.puerta">{{ v.vivienda.puerta }}</span>
          </div>
          <div style="font-size:0.8rem;color:var(--clr-muted);margin-top:0.2rem">
            Anotado a las {{ v.creado_en ? new Date(v.creado_en).toLocaleTimeString('es-ES', {hour:'2-digit',minute:'2-digit'}) : '' }}
          </div>
          <div v-if="v.observaciones" style="margin-top:0.4rem; padding:0.5rem; background:var(--clr-surface2); border-radius:var(--radius); font-size:0.9rem">
            {{ v.observaciones }}
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
        
        <!-- Cambiar dirección o nombre -->
        <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--clr-border)" v-if="editando.vivienda">
          <label style="display:flex;align-items:center;gap:0.5rem;cursor:pointer">
            <input type="checkbox" v-model="cambiarDireccion" />
            <span>Cambiar dirección</span>
          </label>
          
          <div v-if="cambiarDireccion" style="margin-top:0.5rem" class="stack">
            <div>
              <label>1. Calle</label>
              <BuscadorCalle v-model="calle" />
            </div>
            <div v-if="calle">
              <label>2. Vivienda</label>
              <SelectorVivienda v-model="vivienda" />
            </div>
          </div>
        </div>

        <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--clr-border)" v-else-if="editando.nombre_persona">
          <label for="edit-nombre">Nombre de la persona</label>
          <input id="edit-nombre" class="input" type="text" v-model="editForm.nombre_persona" />
        </div>
        
        <div class="row" style="margin-top:1rem">
          <button class="btn btn-ghost" @click="editando = null">Cancelar</button>
          <button class="btn btn-primary" @click="guardarEdicion">
            <span v-if="guardandoEdicion" class="spinner" style="width:16px;height:16px"></span>
            <span v-else>Guardar</span>
          </button>
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
import { ref, computed, onMounted, watch } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import BuscadorCalle from '../components/BuscadorCalle.vue'
import SelectorVivienda from '../components/SelectorVivienda.vue'
import api from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const tab = ref('aportaciones')

const aportaciones = ref([])
const cargando = ref(false)
const editando = ref(null)
const editForm = ref({})
const guardandoEdicion = ref(false)
const cambiarDireccion = ref(false)
const calle = ref(null)
const vivienda = ref({ portal: '', piso: '', puerta: '' })
const borrandoId = ref(null)
const toast = ref('')
const toastError = ref(false)

const visitasReintentar = ref([])
const cargandoReintentos = ref(false)
const fechaReintentos = ref(new Date().toISOString().slice(0, 10))

const totalDia = computed(() => {
  if (tab.value !== 'aportaciones') return 0
  return aportaciones.value.reduce((s, a) => s + Number(a.importe), 0)
})

function formatEur(n) {
  return Number(n).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

onMounted(() => {
  cargar()
  cargarReintentos()
})

watch(tab, (t) => {
  if (t === 'reintentos' && !visitasReintentar.value.length) cargarReintentos()
})

async function cargarReintentos() {
  cargandoReintentos.value = true
  try {
    const res = await api.get('/visitas', { 
      params: { fecha_inicio: fechaReintentos.value, fecha_fin: fechaReintentos.value, resultado: 'reintentar' } 
    })
    visitasReintentar.value = res.data
  } finally {
    cargandoReintentos.value = false
  }
}

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
  if (a.nombre_persona) {
    editForm.value.nombre_persona = a.nombre_persona
  }
  cambiarDireccion.value = false
  calle.value = null
  vivienda.value = { portal: '', piso: '', puerta: '' }
}

async function guardarEdicion() {
  guardandoEdicion.value = true
  try {
    let body = { ...editForm.value }
    
    // Si quiere cambiar de dirección y es válida
    if (cambiarDireccion.value && calle.value && vivienda.value.portal) {
      // 1. Obtener o crear vivienda
      let vId = null
      try {
        const resBusqueda = await api.get('/viviendas', {
          params: {
            calle_id: calle.value.id,
            portal: vivienda.value.portal,
            piso: vivienda.value.piso || undefined,
            puerta: vivienda.value.puerta || undefined,
          }
        })
        if (resBusqueda.data.length > 0) vId = resBusqueda.data[0].id
      } catch { /* ignorar */ }
      
      if (!vId) {
        const resCrear = await api.post('/viviendas', {
          calle_id: calle.value.id,
          portal: vivienda.value.portal,
          piso: vivienda.value.piso || null,
          puerta: vivienda.value.puerta || null,
        })
        vId = resCrear.data.id
      }
      body.vivienda_id = vId
    }

    await api.patch(`/aportaciones/${editando.value.id}`, body)
    editando.value = null
    mostrarToast('Guardado')
    cargar()
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error al guardar', true)
  } finally {
    guardandoEdicion.value = false
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

<style scoped>
.tab-bar { display: flex; gap: 0.4rem; overflow-x: auto; padding-bottom: 2px; }
.tab-btn {
  padding: 0.5rem 0.9rem; border-radius: var(--radius);
  border: 1.5px solid var(--clr-border);
  background: transparent; color: var(--clr-muted);
  font-size: 0.85rem; font-weight: 600; cursor: pointer;
  white-space: nowrap; transition: all var(--transition);
}
.tab-btn.active { background: var(--clr-primary); border-color: var(--clr-primary); color: #fff; }
</style>
