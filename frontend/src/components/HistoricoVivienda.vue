<template>
  <div v-if="historico.length">
    <!-- Línea compacta: año más reciente -->
    <div class="historico-compact">
      <div>
        <span class="anio">{{ historico[0].anio_campania }}</span>
        <span class="importe" v-if="historico[0].num_aportaciones > 0"> {{ formatEur(historico[0].total) }}</span>
        <span class="importe" v-else-if="historico[0].observaciones && historico[0].observaciones.length" style="color:var(--clr-danger);font-size:0.9rem;margin-left:4px">
          {{ historico[0].observaciones[0].texto.split('-')[0].replace(/\[|\]/g, '').trim() }}
        </span>
        <span class="importe" v-else> 0,00 €</span>
      </div>
      <button v-if="historico.length > 1" class="btn btn-ghost btn-sm" @click="abierto = true">
        Ver más años
      </button>
    </div>

    <!-- Modal con historial completo -->
    <div v-if="abierto" class="modal-overlay" @click.self="abierto = false">
      <div class="modal-box">
        <h2 style="margin-bottom:1rem">Histórico de aportaciones</h2>
        <table class="tabla">
          <thead>
            <tr>
              <th>Año</th>
              <th>Aportaciones</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="h in historico" :key="h.anio_campania">
              <tr>
                <td>{{ h.anio_campania }}</td>
                <td>{{ h.num_aportaciones }}</td>
                <td>
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong v-if="h.num_aportaciones > 0">{{ formatEur(h.total) }}</strong>
                    <strong v-else-if="h.observaciones && h.observaciones.length" style="color:var(--clr-danger); font-size:0.9rem">
                      {{ h.observaciones[0].texto.split('-')[0].replace(/\[|\]/g, '').trim() }}
                    </strong>
                    <strong v-else style="color:var(--clr-muted)">0,00 €</strong>
                    <button v-if="tieneObservacionesReales(h.observaciones)" 
                            class="btn btn-ghost btn-sm" 
                            @click="toggleObservaciones(h.anio_campania)"
                            style="padding:0.2rem 0.5rem; height:auto; font-size:0.75rem"
                            title="Ver observaciones">
                      {{ verObservaciones[h.anio_campania] ? 'Ocultar' : '💬 Notas' }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="verObservaciones[h.anio_campania] && tieneObservacionesReales(h.observaciones)">
                <td colspan="3" style="background:var(--clr-surface2); padding:0.75rem; border-bottom:1px solid var(--clr-border);">
                  <div style="font-size:0.85rem; color:var(--clr-text)">
                    <div v-for="(obs, idx) in observacionesReales(h.observaciones)" :key="idx" :style="idx > 0 ? 'margin-top:0.4rem' : ''">
                      <span style="color:var(--clr-muted); font-weight:600; margin-right:0.3rem">{{ formatDate(obs.fecha) }}:</span>
                      <span>{{ obs.texto }}</span>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <button class="btn btn-ghost btn-full" style="margin-top:1rem" @click="abierto = false">
          Cerrar
        </button>
      </div>
    </div>
  </div>
  <div v-else-if="cargando" class="spinner" style="margin:0.5rem 0"></div>
</template>

<script setup>
import { ref, watch } from 'vue'
import api from '../api/client.js'

const props = defineProps({ viviendaId: { type: Number, default: null } })
const historico = ref([])
const abierto = ref(false)
const cargando = ref(false)
const verObservaciones = ref({})

watch(() => props.viviendaId, async (id) => {
  historico.value = []
  verObservaciones.value = {}
  if (!id) return
  cargando.value = true
  try {
    const res = await api.get(`/viviendas/${id}/historico`)
    historico.value = res.data
  } finally {
    cargando.value = false
  }
}, { immediate: true })

function toggleObservaciones(anio) {
  verObservaciones.value[anio] = !verObservaciones.value[anio]
}

function observacionesReales(obsList) {
  if (!obsList) return []
  return obsList.filter(o => !o.texto.match(/^\[[A-Za-z áéíóú]+\]$/))
}

function tieneObservacionesReales(obsList) {
  return observacionesReales(obsList).length > 0
}

function formatEur(n) {
  return Number(n).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
</script>
