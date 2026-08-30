<template>
  <div class="page-header">
    <button v-if="back" class="btn-back" @click="goBack">
      ← {{ backLabel }}
    </button>
    <h1 class="page-title">{{ title }}</h1>
    <div class="header-right">
      <slot name="right" />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  title: { type: String, required: true },
  back: { type: String, default: null },      // ruta a la que volver, ej: '/'
  backLabel: { type: String, default: 'Volver' },
})

const router = useRouter()

function goBack() {
  if (props.back) {
    router.push(props.back)
  } else {
    router.back()
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.2rem;
  min-height: 2.5rem;
}
.btn-back {
  background: none;
  border: 1px solid var(--clr-border);
  border-radius: 8px;
  padding: 0.35rem 0.75rem;
  font-size: 0.85rem;
  color: var(--clr-muted);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition);
  font-family: inherit;
}
.btn-back:hover {
  color: var(--clr-primary);
  border-color: var(--clr-primary);
  background: color-mix(in srgb, var(--clr-primary) 8%, transparent);
}
.page-title {
  flex: 1;
  font-size: 1.2rem;
  font-weight: 700;
  margin: 0;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
