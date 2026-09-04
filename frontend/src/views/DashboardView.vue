<template>
  <div class="page">
    <PageHeader title="Panel Admin" back="/" back-label="Registro" />

    <!-- Pestañas -->
    <div class="tab-bar">
      <button v-for="t in tabs" :key="t.key"
              class="tab-btn" :class="{ active: tab === t.key }"
              @click="tab = t.key">{{ t.label }}</button>
    </div>

    <!-- ── REPORTE ─────────────────────────────────────────── -->
    <div v-if="tab === 'reporte'" class="stack" style="margin-top:1rem">
      <div class="card">
        <p class="section-title">Informe diario</p>
        <div class="row" style="margin-bottom:0.5rem">
          <div>
            <label for="fecha-reporte">Fecha</label>
            <input id="fecha-reporte" class="input" type="date" v-model="fechaReporte" />
          </div>
          <div style="display:flex;align-items:flex-end">
            <button class="btn btn-primary" @click="cargarReporte">Ver</button>
          </div>
        </div>
        <div v-if="reporte">
          <table class="tabla">
            <thead><tr><th>Equipo</th><th>Aportaciones</th><th>Total</th></tr></thead>
            <tbody>
              <tr v-for="e in reporte.por_equipo" :key="e.equipo">
                <td>{{ e.equipo }}</td>
                <td>{{ e.num_aportaciones }}</td>
                <td><strong>{{ formatEur(e.total) }}</strong></td>
              </tr>
              <tr style="border-top:2px solid var(--clr-border)">
                <td><strong>TOTAL</strong></td>
                <td><strong>{{ reporte.total_general.num_aportaciones }}</strong></td>
                <td><strong>{{ formatEur(reporte.total_general.total) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Dashboard por año -->
      <div class="card">
        <p class="section-title">Dashboard por año</p>
        <div class="row" style="margin-bottom:0.5rem">
          <div>
            <label for="anio-dash">Año campaña</label>
            <select id="anio-dash" class="select" v-model="anioDash">
              <option value="">Todos</option>
              <option v-for="y in anios" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
          <div style="display:flex;align-items:flex-end;gap:0.5rem">
            <button class="btn btn-primary" @click="cargarDashboard">Ver</button>
            <a class="btn btn-success" :href="`/api/reportes/exportar-excel${anioDash ? '?anio='+anioDash : ''}`"
               :style="{ pointerEvents: !auth.token ? 'none' : 'auto' }"
               @click.prevent="exportarExcel">
              📊 Excel
            </a>
          </div>
        </div>
        <div v-if="dashboard">
          <div class="stat-cards" style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin-bottom:0.8rem">
            <div class="card" style="text-align:center">
              <div style="font-size:1.6rem;font-weight:700;color:var(--clr-success)">
                {{ formatEur(dashboard.total) }}
              </div>
              <div style="font-size:0.8rem;color:var(--clr-muted)">Total recaudado</div>
            </div>
            <div class="card" style="text-align:center">
              <div style="font-size:1.6rem;font-weight:700;color:var(--clr-primary)">
                {{ dashboard.por_anio.reduce((s,r) => s + r.num_aportaciones, 0) }}
              </div>
              <div style="font-size:0.8rem;color:var(--clr-muted)">Aportaciones</div>
            </div>
          </div>
          <table class="tabla">
            <thead><tr><th>Año</th><th>Aportaciones</th><th>Total</th></tr></thead>
            <tbody>
              <tr v-for="r in dashboard.por_anio" :key="r.anio">
                <td>{{ r.anio }}</td>
                <td>{{ r.num_aportaciones }}</td>
                <td><strong>{{ formatEur(r.total) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── EQUIPOS ─────────────────────────────────────────── -->
    <div v-if="tab === 'equipos'" class="stack" style="margin-top:1rem">
      <div class="card stack">
        <p class="section-title">Crear equipo</p>
        <div class="row">
          <input id="nuevo-equipo" class="input" type="text" v-model="nuevoEquipo" placeholder="Nombre del equipo" />
          <button class="btn btn-primary" @click="crearEquipo" :disabled="!nuevoEquipo.trim()">Crear</button>
        </div>
      </div>
      <div class="card">
        <p class="section-title">Equipos</p>
        <div v-for="e in equipos" :key="e.id" class="item-row">
          <span :style="{ opacity: e.activo ? 1 : 0.45 }">{{ e.nombre }}</span>
          <div style="display:flex;gap:0.4rem">
            <button class="btn btn-ghost btn-sm" @click="editarEquipo(e)" title="Renombrar equipo">
              ✏️
            </button>
            <button class="btn btn-ghost btn-sm" @click="toggleEquipo(e)">
              {{ e.activo ? '🟢 Activo' : '🔴 Inactivo' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── COBRADORES ──────────────────────────────────────── -->
    <div v-if="tab === 'usuarios'" class="stack" style="margin-top:1rem">
      <div class="card stack">
        <p class="section-title">Nuevo cobrador</p>
        <div>
          <label for="nu-usuario">Nombre de usuario</label>
          <input id="nu-usuario" class="input" type="text" v-model="nuevoUser.nombre_usuario" placeholder="nombre_usuario" />
        </div>
        <div>
          <label for="nu-pass">Contraseña inicial</label>
          <input id="nu-pass" class="input" type="password" v-model="nuevoUser.password" placeholder="••••••••" />
        </div>
        <div style="display:flex;align-items:center;gap:0.5rem">
          <input id="nu-admin" type="checkbox" v-model="nuevoUser.es_admin" />
          <label for="nu-admin" style="margin:0;font-size:0.9rem">Administrador</label>
        </div>
        <button class="btn btn-primary" @click="crearUsuario"
                :disabled="!nuevoUser.nombre_usuario || !nuevoUser.password">
          Crear usuario
        </button>
      </div>
      <div class="card">
        <p class="section-title">Usuarios</p>
        <div v-for="u in usuarios" :key="u.id" class="item-row">
          <div>
            <span :style="{ opacity: u.activo ? 1 : 0.45 }">{{ u.nombre_usuario }}</span>
            <span v-if="u.es_admin" class="badge badge-warning" style="margin-left:0.4rem;font-size:0.7rem">admin</span>
          </div>
          <div style="display: flex; gap: 0.5rem">
            <button class="btn btn-ghost btn-sm" @click="resetPassword(u)" title="Restablecer contraseña">
              🔑
            </button>
            <button class="btn btn-ghost btn-sm" @click="toggleAdmin(u)" :title="u.es_admin ? 'Quitar administrador' : 'Hacer administrador'">
              👑
            </button>
            <button class="btn btn-ghost btn-sm" @click="toggleUsuario(u)">
              {{ u.activo ? 'Desactivar' : 'Activar' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── CALLES ──────────────────────────────────────────── -->
    <div v-if="tab === 'calles'" class="stack" style="margin-top:1rem">
      <div class="card stack">
        <p class="section-title">Nueva calle</p>
        <div class="row">
          <input id="nueva-calle" class="input" type="text" v-model="nuevaCalle" placeholder="Nombre de la calle" />
          <button class="btn btn-primary" @click="crearCalle" :disabled="!nuevaCalle.trim()">Crear</button>
        </div>
      </div>
      <div class="card">
        <p class="section-title">Calles registradas ({{ calles.length }})</p>
        <div v-for="c in calles" :key="c.id" class="item-row">
          <span>{{ c.nombre }}</span>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast" :class="{ error: toastError }">{{ toast }}</div>

    <!-- ── HISTORIAL DIARIO GLOBAL ─────────────────────────── -->
    <div v-if="tab === 'historial'" class="stack" style="margin-top:1rem">
      <div class="card">
        <div class="row" style="margin-bottom:1rem">
          <div>
            <label for="fecha-hist">Día a visualizar</label>
            <input id="fecha-hist" class="input" type="date" v-model="fechaHistorial" @change="cargarHistorial(true)" />
          </div>
        </div>

        <div v-if="historialAportaciones.length === 0 && !historialCargando" style="text-align:center;color:var(--clr-muted);padding:2rem 0">
          No hay registros para este día
        </div>
        
        <div v-else class="stack">
          <div v-for="a in historialAportaciones" :key="a.id" class="card" style="padding:0.75rem;display:flex;justify-content:space-between;align-items:center">
            <div>
              <div v-if="a.vivienda" style="font-weight:600">{{ a.vivienda.calle.nombre }} {{ a.vivienda.portal }} <span v-if="a.vivienda.piso">{{ a.vivienda.piso }}</span> <span v-if="a.vivienda.puerta">{{ a.vivienda.puerta }}</span></div>
              <div v-else-if="a.nombre_persona" style="font-weight:600">{{ a.nombre_persona }} (Local)</div>
              
              <div style="font-size:0.8rem;color:var(--clr-muted);display:flex;gap:0.4rem;align-items:center;margin-top:0.2rem">
                <span class="badge" style="background:var(--clr-surface2)">{{ (equipos.find(e => e.id === a.equipo_id) || {}).nombre || 'Equipo ' + a.equipo_id }}</span>
                <span>• {{ formatEur(a.importe) }} ({{ a.forma_pago }})</span>
              </div>
            </div>
            <div style="display:flex;gap:0.4rem">
              <button class="btn btn-ghost btn-sm" @click="histEditar(a)">✏️</button>
              <button class="btn btn-ghost btn-sm" style="color:var(--clr-danger)" @click="histBorrandoId = a.id">🗑️</button>
            </div>
          </div>
          
          <button v-if="historialTieneMas" class="btn btn-ghost" style="margin-top:1rem" @click="cargarHistorial(false)">
            <span v-if="historialCargando" class="spinner" style="width:16px;height:16px"></span>
            <span v-else>Cargar más (50)</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal edición Historial -->
    <div v-if="histEditando" class="modal-overlay" @click.self="histEditando = null">
      <div class="modal-box stack">
        <h2>Editar aportación</h2>
        <div>
          <label for="edit-importe">Importe (€)</label>
          <input id="edit-importe" class="input" type="number" step="0.01" v-model="histEditForm.importe" />
        </div>
        <div>
          <label for="edit-pago">Forma de pago</label>
          <select id="edit-pago" class="select" v-model="histEditForm.forma_pago">
            <option value="efectivo">💵 Efectivo</option>
            <option value="bizum">📱 Bizum</option>
          </select>
        </div>
        <div>
          <label for="edit-obs">Observaciones</label>
          <input id="edit-obs" class="input" type="text" v-model="histEditForm.observaciones" />
        </div>
        
        <!-- Cambiar dirección o nombre -->
        <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--clr-border)" v-if="histEditando.vivienda">
          <label style="display:flex;align-items:center;gap:0.5rem;cursor:pointer">
            <input type="checkbox" v-model="histCambiarDireccion" />
            <span>Cambiar dirección</span>
          </label>
          
          <div v-if="histCambiarDireccion" style="margin-top:0.5rem" class="stack">
            <div>
              <label>1. Calle</label>
              <BuscadorCalle v-model="histCalle" />
            </div>
            <div v-if="histCalle">
              <label>2. Vivienda</label>
              <SelectorVivienda v-model="histVivienda" />
            </div>
          </div>
        </div>

        <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--clr-border)" v-else-if="histEditando.nombre_persona">
          <label for="edit-nombre">Nombre de la persona</label>
          <input id="edit-nombre" class="input" type="text" v-model="histEditForm.nombre_persona" />
        </div>
        
        <div class="row" style="margin-top:1rem">
          <button class="btn btn-ghost" @click="histEditando = null">Cancelar</button>
          <button class="btn btn-primary" @click="histGuardarEdicion">
            <span v-if="histGuardandoEdicion" class="spinner" style="width:16px;height:16px"></span>
            <span v-else>Guardar</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Borrar Historial -->
    <div v-if="histBorrandoId" class="modal-overlay" @click.self="histBorrandoId = null">
      <div class="modal-box stack">
        <h2>¿Borrar aportación?</h2>
        <p style="color:var(--clr-muted)">Esta acción no se puede deshacer.</p>
        <div class="row">
          <button class="btn btn-ghost" @click="histBorrandoId = null">Cancelar</button>
          <button class="btn btn-danger" @click="histBorrar">Borrar</button>
        </div>
      </div>
    </div>

    <!-- ── SEGUIMIENTO VISITAS ─────────────────────────────────────────── -->
    <div v-if="tab === 'seguimiento'" class="stack" style="margin-top:1rem">
      <div class="card row" style="margin-bottom:1rem">
        <div>
          <label for="fecha-inicio-seg">Fecha Inicio</label>
          <input id="fecha-inicio-seg" class="input" type="date" v-model="segFechaInicio" />
        </div>
        <div>
          <label for="fecha-fin-seg">Fecha Fin</label>
          <input id="fecha-fin-seg" class="input" type="date" v-model="segFechaFin" />
        </div>
        <div>
          <label for="resultado-seg">Resultado</label>
          <select id="resultado-seg" class="select" v-model="segResultado">
            <option value="">Todos (sin aportar)</option>
            <option value="no_aporta">No aporta</option>
            <option value="no_abre">No abre</option>
            <option value="reintentar">Reintentar</option>
            <option value="pasara_por_local">Pasará por local</option>
          </select>
        </div>
        <div style="display:flex;align-items:flex-end">
          <button class="btn btn-primary" @click="cargarSeguimiento">Filtrar</button>
        </div>
      </div>

      <div v-if="segCargando" style="display:flex;justify-content:center;padding:2rem">
        <div class="spinner"></div>
      </div>

      <div v-else-if="!segVisitas.length" class="card" style="text-align:center;color:var(--clr-muted);padding:2rem">
        No se han encontrado visitas
      </div>

      <div v-else class="stack">
        <div v-for="v in segVisitas" :key="v.id" class="card">
          <div style="font-weight:600; font-size:1.1rem">
            {{ v.vivienda?.calle?.nombre }} {{ v.vivienda?.portal }}
            <span v-if="v.vivienda?.piso">{{ v.vivienda.piso }}</span>
            <span v-if="v.vivienda?.puerta">{{ v.vivienda.puerta }}</span>
            <span class="badge" style="margin-left:0.5rem" :class="{
              'badge-warning': v.resultado === 'reintentar',
              'badge-danger': v.resultado === 'no_aporta',
              'badge-muted': v.resultado === 'no_abre'
            }">{{ v.resultado.replace('_', ' ') }}</span>
          </div>
          <div style="font-size:0.8rem;color:var(--clr-muted);margin-top:0.2rem">
            Anotado el {{ new Date(v.fecha).toLocaleDateString('es-ES') }} 
            <span v-if="v.creado_en"> a las {{ new Date(v.creado_en).toLocaleTimeString('es-ES', {hour:'2-digit',minute:'2-digit'}) }}</span>
          </div>
          <div v-if="v.observaciones" style="margin-top:0.4rem; padding:0.5rem; background:var(--clr-surface2); border-radius:var(--radius); font-size:0.9rem">
            {{ v.observaciones }}
          </div>
        </div>
      </div>
    </div>

    <button class="btn btn-ghost btn-sm" style="color:var(--clr-danger);margin-top:1.5rem"
            @click="auth.logout(); router.push('/login')">
      🚪 Cerrar sesión
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import BuscadorCalle from '../components/BuscadorCalle.vue'
import SelectorVivienda from '../components/SelectorVivienda.vue'
import api from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()

const tabs = [
  { key: 'reporte', label: '📊 Reportes' },
  { key: 'historial', label: '📖 Historial' },
  { key: 'seguimiento', label: '🔍 Seguimiento' },
  { key: 'equipos', label: '👥 Equipos' },
  { key: 'usuarios', label: '🙋 Cobradores' },
  { key: 'calles',  label: '🛣️ Calles' },
]
const tab = ref('reporte')

const anios = ref([2024, 2025, 2026])
const fechaReporte = ref(new Date().toISOString().slice(0, 10))
const anioDash = ref(new Date().getFullYear())
const reporte = ref(null)
const dashboard = ref(null)
const equipos = ref([])
const usuarios = ref([])
const calles = ref([])
const nuevoEquipo = ref('')
const nuevaCalle = ref('')
const nuevoUser = ref({ nombre_usuario: '', password: '', es_admin: false })
const toast = ref('')
const toastError = ref(false)

const fechaHistorial = ref(new Date().toISOString().slice(0, 10))
const historialAportaciones = ref([])
const historialCargando = ref(false)
const historialOffset = ref(0)
const historialTieneMas = ref(true)

const histEditando = ref(null)
const histEditForm = ref({})
const histGuardandoEdicion = ref(false)
const histCambiarDireccion = ref(false)
const histCalle = ref(null)
const histVivienda = ref({ portal: '', piso: '', puerta: '' })
const histBorrandoId = ref(null)

function formatEur(n) {
  return Number(n).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

onMounted(async () => {
  await Promise.all([cargarEquipos(), cargarUsuarios(), cargarCalles(), cargarHistorial(true)])
  await cargarReporte()
  await cargarDashboard()
})

async function cargarReporte() {
  const res = await api.get('/reportes/diario', { params: { fecha: fechaReporte.value } })
  reporte.value = res.data
}
async function cargarDashboard() {
  const res = await api.get('/reportes/dashboard', { params: { anio: anioDash.value || undefined } })
  dashboard.value = res.data
}
async function cargarEquipos() {
  const res = await api.get('/equipos')
  equipos.value = res.data
}
async function cargarUsuarios() {
  const res = await api.get('/usuarios')
  usuarios.value = res.data
}
async function cargarCalles() {
  const res = await api.get('/calles')
  calles.value = res.data
}

async function crearEquipo() {
  try {
    await api.post('/equipos', { nombre: nuevoEquipo.value.trim() })
    nuevoEquipo.value = ''
    cargarEquipos()
  } catch (e) { mostrarToast(e.response?.data?.detail || 'Error', true) }
}
async function editarEquipo(e) {
  const newName = prompt(`Introduce el nuevo nombre para el equipo "${e.nombre}":`, e.nombre);
  if (!newName || newName.trim() === '' || newName.trim() === e.nombre) return;
  try {
    await api.patch(`/equipos/${e.id}`, { nombre: newName.trim() });
    cargarEquipos();
  } catch (err) {
    mostrarToast(err.response?.data?.detail || 'Error al renombrar', true);
  }
}
async function toggleEquipo(e) {
  await api.patch(`/equipos/${e.id}`, { activo: !e.activo })
  cargarEquipos()
}
async function crearUsuario() {
  try {
    await api.post('/usuarios', { ...nuevoUser.value })
    nuevoUser.value = { nombre_usuario: '', password: '', es_admin: false }
    mostrarToast('Usuario creado')
    cargarUsuarios()
  } catch (e) { mostrarToast(e.response?.data?.detail || 'Error', true) }
}
async function resetPassword(u) {
  const pwd = prompt(`Introduce la nueva contraseña para el usuario ${u.nombre_usuario}:`);
  if (!pwd) return;
  try {
    await api.patch(`/usuarios/${u.id}`, { password: pwd });
    mostrarToast('Contraseña restablecida correctamente');
  } catch(e) {
    mostrarToast(e.response?.data?.detail || 'Error al cambiar contraseña', true);
  }
}

async function toggleUsuario(u) {
  const action = u.activo ? 'desactivar' : 'activar';
  if (!confirm(`¿Estás seguro de que deseas ${action} al usuario ${u.nombre_usuario}?`)) return;
  await api.patch(`/usuarios/${u.id}`, { activo: !u.activo })
  cargarUsuarios()
}
async function toggleAdmin(u) {
  const action = u.es_admin ? 'quitar los privilegios de administrador a' : 'hacer administrador a';
  if (!confirm(`¿Estás seguro de que deseas ${action} ${u.nombre_usuario}?`)) return;
  try {
    await api.patch(`/usuarios/${u.id}`, { es_admin: !u.es_admin });
    mostrarToast(u.es_admin ? 'Privilegios de administrador retirados' : 'Privilegios de administrador concedidos');
    cargarUsuarios();
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error al cambiar privilegios', true);
  }
}
async function crearCalle() {
  try {
    await api.post('/calles', { nombre: nuevaCalle.value.trim() })
    nuevaCalle.value = ''
    mostrarToast('Calle creada')
    cargarCalles()
  } catch (e) { mostrarToast(e.response?.data?.detail || 'Error', true) }
}

async function cargarHistorial(reset = true) {
  if (reset) {
    historialOffset.value = 0
    historialAportaciones.value = []
    historialTieneMas.value = true
  }
  if (!historialTieneMas.value) return
  
  historialCargando.value = true
  try {
    const res = await api.get('/aportaciones', {
      params: {
        fecha: fechaHistorial.value,
        limit: 50,
        offset: historialOffset.value
      }
    })
    if (res.data.length < 50) historialTieneMas.value = false
    historialAportaciones.value.push(...res.data)
    historialOffset.value += 50
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error al cargar historial', true)
  } finally {
    historialCargando.value = false
  }
}

function histEditar(a) {
  histEditando.value = a
  histEditForm.value = { importe: a.importe, forma_pago: a.forma_pago, observaciones: a.observaciones || '' }
  if (a.nombre_persona) {
    histEditForm.value.nombre_persona = a.nombre_persona
  }
  histCambiarDireccion.value = false
  histCalle.value = null
  histVivienda.value = { portal: '', piso: '', puerta: '' }
}

async function histGuardarEdicion() {
  histGuardandoEdicion.value = true
  try {
    let body = { ...histEditForm.value }
    if (histCambiarDireccion.value && histCalle.value && histVivienda.value.portal) {
      let vId = null
      try {
        const resBusqueda = await api.get('/viviendas', {
          params: { calle_id: histCalle.value.id, portal: histVivienda.value.portal, piso: histVivienda.value.piso || undefined, puerta: histVivienda.value.puerta || undefined }
        })
        if (resBusqueda.data.length > 0) vId = resBusqueda.data[0].id
      } catch { /* ignorar */ }
      
      if (!vId) {
        const resCrear = await api.post('/viviendas', {
          calle_id: histCalle.value.id, portal: histVivienda.value.portal, piso: histVivienda.value.piso || null, puerta: histVivienda.value.puerta || null
        })
        vId = resCrear.data.id
      }
      body.vivienda_id = vId
    }

    await api.patch(`/aportaciones/${histEditando.value.id}`, body)
    histEditando.value = null
    mostrarToast('Aportación guardada')
    // Recargar solo ese item en local o refrescar la lista completa (optamos por recargar la lista)
    cargarHistorial(true)
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error al guardar', true)
  } finally {
    histGuardandoEdicion.value = false
  }
}

async function histBorrar() {
  try {
    await api.delete(`/aportaciones/${histBorrandoId.value}`)
    histBorrandoId.value = null
    cargarHistorial(true)
  } catch (e) {
    mostrarToast(e.response?.data?.detail || 'Error al borrar', true)
  }
}

// ==========================================
// SEGUIMIENTO VISITAS
// ==========================================
const segVisitas = ref([])
const segCargando = ref(false)
const segFechaInicio = ref(new Date().toISOString().slice(0, 10))
const segFechaFin = ref(new Date().toISOString().slice(0, 10))
const segResultado = ref('')

async function cargarSeguimiento() {
  segCargando.value = true
  try {
    const params = { fecha_inicio: segFechaInicio.value, fecha_fin: segFechaFin.value }
    if (segResultado.value) params.resultado = segResultado.value
    const res = await api.get('/visitas', { params })
    if (!segResultado.value) {
      segVisitas.value = res.data.filter(v => v.resultado !== 'aporta')
    } else {
      segVisitas.value = res.data
    }
  } finally {
    segCargando.value = false
  }
}

watch(tab, (t) => {
  if (t === 'seguimiento' && !segVisitas.value.length) cargarSeguimiento()
})

async function exportarExcel() {
  try {
    const url = `/reportes/exportar-excel${anioDash.value ? '?anio=' + anioDash.value : ''}`
    const res = await api.get(url, { responseType: 'blob' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(res.data)
    a.download = `aportaciones_${anioDash.value || 'todos'}.xlsx`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    mostrarToast('Error al descargar Excel', true)
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
.item-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.55rem 0; border-bottom: 1px solid var(--clr-surface2);
}
.item-row:last-child { border-bottom: none; }
</style>
