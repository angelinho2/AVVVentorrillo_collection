<template>
  <div class="stack">
    <div class="row">
      <div>
        <label for="portal">Portal</label>
        <input id="portal" class="input" type="text" v-model="local.portal" placeholder="Nº portal" />
      </div>
      <div>
        <label for="piso">Piso</label>
        <select id="piso" class="select" v-model="local.piso">
          <option value="">—</option>
          <option v-for="p in PISOS" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>
    </div>
    <div>
      <label for="puerta">Puerta</label>
      <select id="puerta" class="select" v-model="local.puerta">
        <option value="">—</option>
        <option v-for="p in PUERTAS" :key="p" :value="p">{{ p }}</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const PISOS = ['0','1','2','3','4','5','6','7','8','9','10','11','12']
const PUERTAS = ['Izquierda','Centro-izquierda','Centro','Centro-derecha','Derecha',
                 'A','B','C','D','E','F','G','H','I','J','K']

const props = defineProps({
  modelValue: { type: Object, default: () => ({ portal: '', piso: '', puerta: '' }) },
})
const emit = defineEmits(['update:modelValue'])

const local = reactive({ ...props.modelValue })

watch(local, (val) => emit('update:modelValue', { ...val }))
watch(() => props.modelValue, (val) => Object.assign(local, val))
</script>
