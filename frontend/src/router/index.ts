import { getConfig } from "@/config";
import NProgress from "@/utils/progress";
import { buildHierarchyTree } from "@/utils/tree";
import { cloneDeep, isUrl, openLink } from "@pureadmin/utils";
import {
  createRouter,
  type RouteComponent,
  type RouteRecordRaw
} from "vue-router";
import remainingRouter from "./modules/remaining";
import {
  ascending,
  formatFlatteningRoutes,
  formatTwoStageRoutes,
  getHistoryMode
} from "./utils";

const modules: Record<string, any> = import.meta.glob(
  ["./modules/**/*.ts", "!./modules/**/remaining.ts"],
  { eager: true }
);

const routes: RouteRecordRaw[] = Object.values(modules).map(
  module => module.default
);

export const constantRoutes: RouteRecordRaw[] = formatTwoStageRoutes(
  formatFlatteningRoutes(buildHierarchyTree(ascending(routes.flat(Infinity))))
);

const initConstantRoutes = cloneDeep(constantRoutes);

export const constantMenus: RouteComponent[] = ascending(
  routes.flat(Infinity)
).concat(...remainingRouter);

export const remainingPaths = Object.keys(remainingRouter).map(
  key => remainingRouter[key].path
);

export const router = createRouter({
  history: getHistoryMode(import.meta.env.VITE_ROUTER_HISTORY),
  routes: constantRoutes.concat(...(remainingRouter as any)),
  strict: true,
  scrollBehavior: () => ({ left: 0, top: 0 })
});

const loadedPaths = new Set<string>();

export function resetLoadedPaths() {
  loadedPaths.clear();
}

export function resetRouter() {
  router.clearRoutes();
  for (const route of initConstantRoutes.concat(...(remainingRouter as any))) {
    router.addRoute(route);
  }
  resetLoadedPaths();
}

router.beforeEach(to => {
  to.meta.loaded = loadedPaths.has(to.path);
  if (!to.meta.loaded) NProgress.start();

  if (to.meta.title) {
    const platformTitle = getConfig().Title;
    document.title = platformTitle
      ? `${String(to.meta.title)} | ${platformTitle}`
      : String(to.meta.title);
  }

  if (isUrl(to.name as string)) {
    openLink(to.name as string);
    NProgress.done();
    return false;
  }
  return true;
});

router.afterEach(to => {
  loadedPaths.add(to.path);
  NProgress.done();
});

export default router;
