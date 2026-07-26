const { VITE_HIDE_HOME } = import.meta.env;
const Layout = () => import("@/layout/index.vue");

export default {
  path: "/",
  name: "Home",
  component: Layout,
  redirect: "/dashboard",
  meta: {
    icon: "ep/monitor",
    title: "HomeHub",
    rank: 0
  },
  children: [
    {
      path: "/dashboard",
      name: "Welcome",
      component: () => import("@/views/welcome/index.vue"),
      meta: {
        title: "系统总览",
        showLink: VITE_HIDE_HOME === "true" ? false : true
      }
    }
  ]
} satisfies RouteConfigsTable;
