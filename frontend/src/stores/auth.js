import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('avv_token') || null)
  const usuario = ref(JSON.parse(localStorage.getItem('avv_usuario') || 'null'))
  const equipoId = ref(Number(localStorage.getItem('avv_equipo_id')) || null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => usuario.value?.es_admin === true)

  async function login(nombreUsuario, password, equipo_id) {
    const res = await api.post('/auth/login', { nombre_usuario: nombreUsuario, password, equipo_id })
    _setSession(res.data)
  }

  async function cambiarEquipo(equipo_id) {
    const res = await api.post('/auth/cambiar-equipo', { equipo_id })
    _setSession(res.data)
  }

  function _setSession(data) {
    token.value = data.access_token
    usuario.value = data.usuario
    equipoId.value = data.equipo_id
    localStorage.setItem('avv_token', data.access_token)
    localStorage.setItem('avv_usuario', JSON.stringify(data.usuario))
    localStorage.setItem('avv_equipo_id', data.equipo_id)
  }

  function logout() {
    token.value = null
    usuario.value = null
    equipoId.value = null
    localStorage.removeItem('avv_token')
    localStorage.removeItem('avv_usuario')
    localStorage.removeItem('avv_equipo_id')
  }

  return { token, usuario, equipoId, isLoggedIn, isAdmin, login, cambiarEquipo, logout }
})
