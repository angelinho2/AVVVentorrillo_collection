<template>
  <div v-if="historico.length">
    <!-- Línea compacta: año más reciente -->
    <div class="historico-compact">
      <div>
        <span class="anio">{{ historico[0].anio_campania }}</span>
        <span class="importe"> {{ formatEur(historico[0].total) }}</span>
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
            <tr v-for="h in historico" :key="h.anio_campania">
              <td>{{ h.anio_campania }}</td>
              <td>{{ h.num_aportaciones }}</td>
              <td><strong>{{ formatEur(h.total) }}</strong></td>
            </tr>
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

watch(() => props.viviendaId, async (id) => {
  historico.value = []
  if (!id) return
  cargando.value = true
  try {
    const res = await api.get(`/viviendas/${id}/historico`)
    historico.value = res.data
  } finally {
    cargando.value = false
  }
}, { immediate: true })

function formatEur(n) {
  return Number(n).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}
</script>
