import { createRouter, createWebHistory } from "vue-router";

// Create router without store dependency at initialization
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("../views/HomeView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("../views/RegisterView.vue"),
    },
    {
      path: "/crew-sheets",
      name: "crewSheets",
      component: () => import("../views/CrewSheetListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/crew-sheets/:id",
      name: "crewSheet",
      component: () => import("../views/CrewSheetDetailView.vue"),
      meta: { requiresAuth: true },
      props: true,
    },
    {
      path: "/upload",
      name: "upload",
      component: () => import("../views/UploadView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/analytics",
      name: "analytics",
      component: () => import("../views/AnalyticsDashboard.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

// Add navigation guard after router is created
router.beforeEach((to, from, next) => {
  // Check authentication by directly accessing localStorage instead of using store
  const hasToken = !!localStorage.getItem("accessToken");

  if (to.meta.requiresAuth && !hasToken) {
    next("/login");
  } else {
    next();
  }
});

export default router;
