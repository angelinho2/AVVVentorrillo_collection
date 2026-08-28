<template>
  <RouterView />
  <NavBar v-if="auth.isLoggedIn" />
</template>

<script setup>
import { RouterView } from 'vue-router'
import NavBar from './components/NavBar.vue'
import { useAuthStore } from './stores/auth.js'

const auth = useAuthStore()
</script>
