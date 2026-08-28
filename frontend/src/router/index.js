import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/',      component: () => import('../views/RegistroRapidoView.vue'), meta: { requiresAuth: true } },
  { path: '/local', component: () => import('../views/AportacionLocalView.vue'), meta: { requiresAuth: true } },
  { path: '/dia',   component: () => import('../views/ListadoDiaView.vue'), meta: { requiresAuth: true } },
  { path: '/admin', component: () => import('../views/DashboardView.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) return '/login'
  if (to.meta.requiresAdmin && !auth.isAdmin) return '/'
  if (to.meta.public && auth.isLoggedIn) return '/'
  return true
})

export default router
