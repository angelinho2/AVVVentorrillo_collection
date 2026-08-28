<template>
  <div class="autocomplete" ref="wrapper">
    <input
      id="buscador-calle"
      class="input"
      type="text"
      :placeholder="placeholder"
      v-model="query"
      @input="onInput"
      @focus="abierto = resultados.length > 0"
      autocomplete="off"
    />
    <ul v-if="abierto && resultados.length" class="dropdown">
      <li
        v-for="c in resultados"
        :key="c.id"
        class="dropdown-item"
        @mousedown.prevent="seleccionar(c)"
      >
        {{ c.nombre }}
      </li>
    </ul>
    <p v-if="query.length >= 2 && !cargando && !resultados.length && abierto" class="no-results">
      Sin resultados
    </p>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import api from '../api/client.js'

const props = defineProps({
  modelValue: { type: Object, default: null },
  placeholder: { type: String, default: 'Buscar calle...' },
})
const emit = defineEmits(['update:modelValue'])

const query = ref(props.modelValue?.nombre || '')
const resultados = ref([])
const abierto = ref(false)
const cargando = ref(false)
let timer = null

watch(() => props.modelValue, (val) => {
  query.value = val?.nombre || ''
})

function onInput() {
  emit('update:modelValue', null)
  clearTimeout(timer)
  if (query.value.length < 2) {
    resultados.value = []
    abierto.value = false
    return
  }
  timer = setTimeout(buscar, 300)
}

async function buscar() {
  cargando.value = true
  try {
    const res = await api.get('/calles', { params: { q: query.value } })
    resultados.value = res.data
    abierto.value = true
  } finally {
    cargando.value = false
  }
}

function seleccionar(calle) {
  query.value = calle.nombre
  emit('update:modelValue', calle)
  abierto.value = false
  resultados.value = []
}
</script>

<style scoped>
.autocomplete { position: relative; }
.dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 200;
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-radius: var(--radius);
  list-style: none;
  max-height: 220px;
  overflow-y: auto;
  box-shadow: var(--shadow);
  margin-top: 4px;
}
.dropdown-item {
  padding: 0.65rem 0.9rem;
  cursor: pointer;
  transition: background var(--transition);
}
.dropdown-item:hover { background: var(--clr-surface2); }
.no-results { font-size: 0.85rem; color: var(--clr-muted); padding: 0.4rem 0; }
</style>
