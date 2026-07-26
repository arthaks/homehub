<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { getDashboard, getPublicConfig } from "./api";
import type {
  DashboardResponse,
  HealthState,
  PublicConfig,
  ResourceUsage
} from "./types";

defineOptions({ name: "Welcome" });

const dashboard = ref<DashboardResponse>();
const config = ref<PublicConfig>({
  serverDisplayName: "Home Server",
  timezone: "Asia/Shanghai",
  refreshIntervalSeconds: 15
});
const loading = ref(true);
const refreshing = ref(false);
const error = ref("");
let timer: number | undefined;

const stateMeta: Record<HealthState, { label: string; type: string }> = {
  healthy: { label: "正常", type: "success" },
  warning: { label: "警告", type: "warning" },
  down: { label: "故障", type: "danger" },
  unknown: { label: "未知", type: "info" }
};

const formatBytes = (bytes: number) => {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit > 2 ? 1 : 0)} ${units[unit]}`;
};

const percentage = (usage: ResourceUsage) =>
  usage.totalBytes ? Math.round((usage.usedBytes / usage.totalBytes) * 100) : 0;

const formatDuration = (seconds: number) => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return [
    days ? `${days}天` : "",
    hours ? `${hours}小时` : "",
    `${minutes}分钟`
  ]
    .filter(Boolean)
    .join(" ");
};

const formattedGeneratedAt = computed(() => {
  if (!dashboard.value) return "尚未获取";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: config.value.timezone
  }).format(new Date(dashboard.value.generatedAt));
});

const overallStatus = computed<HealthState>(() => {
  if (!dashboard.value) return "unknown";
  if (dashboard.value.freshness === "stale") return "down";
  if (dashboard.value.freshness === "delayed") return "warning";
  const states = [
    ...dashboard.value.services.map(item => item.status),
    ...dashboard.value.applications.map(item => item.status)
  ];
  if (states.includes("down")) return "down";
  if (states.includes("warning")) return "warning";
  return "healthy";
});

async function refresh(showMessage = false) {
  refreshing.value = true;
  try {
    dashboard.value = await getDashboard();
    error.value = "";
    if (showMessage) ElMessage.success("状态已刷新");
  } catch (requestError) {
    error.value = "暂时无法获取服务器状态，请检查 HomeHub API 或状态采集器。";
    if (showMessage) ElMessage.error(error.value);
    console.error(requestError);
  } finally {
    refreshing.value = false;
    loading.value = false;
  }
}

function startPolling() {
  if (timer) window.clearInterval(timer);
  timer = window.setInterval(() => {
    if (document.visibilityState === "visible") refresh();
  }, config.value.refreshIntervalSeconds * 1000);
}

function handleVisibility() {
  if (document.visibilityState === "visible") refresh();
}

onMounted(async () => {
  try {
    config.value = await getPublicConfig();
  } catch (requestError) {
    console.warn("Using default public configuration", requestError);
  }
  await refresh();
  startPolling();
  document.addEventListener("visibilitychange", handleVisibility);
});

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
  document.removeEventListener("visibilitychange", handleVisibility);
});
</script>

<template>
  <div class="homehub-page">
    <header class="hero-panel">
      <div>
        <p class="eyebrow">HOMEHUB · READ ONLY</p>
        <h1>{{ config.serverDisplayName }}</h1>
        <p class="subtitle">
          {{ dashboard?.system.hostname || "正在连接家庭服务器" }}
          <span v-if="dashboard?.system.ipv4">
            · {{ dashboard.system.ipv4 }}</span
          >
        </p>
      </div>
      <div class="hero-actions">
        <el-tag
          :type="stateMeta[overallStatus].type as any"
          effect="dark"
          round
        >
          {{ stateMeta[overallStatus].label }}
        </el-tag>
        <el-button :loading="refreshing" @click="refresh(true)"
          >立即刷新</el-button
        >
      </div>
    </header>

    <el-alert
      v-if="error"
      class="status-alert"
      :title="error"
      type="error"
      show-icon
      :closable="false"
    />
    <el-alert
      v-else-if="dashboard && dashboard.freshness !== 'fresh'"
      class="status-alert"
      :title="
        dashboard.freshness === 'stale'
          ? '状态数据已经过期'
          : '状态数据刷新延迟'
      "
      :description="`最近快照生成于 ${formattedGeneratedAt}，请检查 homehub-collector.timer。`"
      :type="dashboard.freshness === 'stale' ? 'error' : 'warning'"
      show-icon
      :closable="false"
    />

    <el-skeleton :loading="loading" animated :rows="8">
      <template v-if="dashboard">
        <section class="metric-grid">
          <article class="metric-card metric-blue">
            <div class="metric-heading">
              <span>CPU</span
              ><strong>{{ dashboard.system.cpuPercent }}%</strong>
            </div>
            <el-progress
              :percentage="dashboard.system.cpuPercent"
              :show-text="false"
            />
            <p>负载 {{ dashboard.system.loadAverage.join(" / ") }}</p>
          </article>
          <article class="metric-card metric-purple">
            <div class="metric-heading">
              <span>内存</span
              ><strong>{{ percentage(dashboard.system.memory) }}%</strong>
            </div>
            <el-progress
              :percentage="percentage(dashboard.system.memory)"
              :show-text="false"
            />
            <p>
              {{ formatBytes(dashboard.system.memory.usedBytes) }} /
              {{ formatBytes(dashboard.system.memory.totalBytes) }}
            </p>
          </article>
          <article class="metric-card metric-green">
            <div class="metric-heading">
              <span>系统磁盘</span
              ><strong>{{ percentage(dashboard.system.disk) }}%</strong>
            </div>
            <el-progress
              :percentage="percentage(dashboard.system.disk)"
              :show-text="false"
            />
            <p>
              {{ formatBytes(dashboard.system.disk.usedBytes) }} /
              {{ formatBytes(dashboard.system.disk.totalBytes) }}
            </p>
          </article>
          <article class="metric-card metric-orange">
            <div class="metric-heading">
              <span>运行时间</span
              ><strong
                >{{ dashboard.system.temperatureCelsius ?? "--" }}°C</strong
              >
            </div>
            <p class="uptime">
              {{ formatDuration(dashboard.system.uptimeSeconds) }}
            </p>
            <p>{{ dashboard.system.kernel }}</p>
          </article>
        </section>

        <section class="content-grid">
          <el-card shadow="never" class="panel services-panel">
            <template #header>
              <div class="panel-header">
                <div>
                  <h2>关键服务</h2>
                  <p>systemd 与本地健康检查</p>
                </div>
                <span>{{ dashboard.services.length }} 项</span>
              </div>
            </template>
            <div class="service-list">
              <div
                v-for="service in dashboard.services"
                :key="service.id"
                class="service-row"
              >
                <span :class="['state-dot', `state-${service.status}`]" />
                <div class="service-copy">
                  <strong>{{ service.name }}</strong
                  ><small>{{
                    service.detail || service.systemdState || "无详情"
                  }}</small>
                </div>
                <div class="service-meta">
                  <span v-if="service.version">{{ service.version }}</span
                  ><el-tag
                    size="small"
                    :type="stateMeta[service.status].type as any"
                    >{{ stateMeta[service.status].label }}</el-tag
                  >
                </div>
              </div>
            </div>
          </el-card>

          <el-card shadow="never" class="panel system-panel">
            <template #header
              ><div class="panel-header">
                <div>
                  <h2>系统信息</h2>
                  <p>有限且不含敏感信息</p>
                </div>
              </div></template
            >
            <dl class="info-list">
              <div>
                <dt>操作系统</dt>
                <dd>{{ dashboard.system.os }}</dd>
              </div>
              <div>
                <dt>主机名</dt>
                <dd>{{ dashboard.system.hostname }}</dd>
              </div>
              <div>
                <dt>IPv4</dt>
                <dd>{{ dashboard.system.ipv4 || "未识别" }}</dd>
              </div>
              <div>
                <dt>数据生成</dt>
                <dd>{{ formattedGeneratedAt }}</dd>
              </div>
              <div>
                <dt>数据年龄</dt>
                <dd>{{ dashboard.ageSeconds }} 秒</dd>
              </div>
            </dl>
          </el-card>
        </section>

        <section class="content-grid lower-grid">
          <el-card shadow="never" class="panel">
            <template #header
              ><div class="panel-header">
                <div>
                  <h2>家庭应用</h2>
                  <p>运行状态与部署版本</p>
                </div>
              </div></template
            >
            <div v-if="dashboard.applications.length" class="application-grid">
              <a
                v-for="app in dashboard.applications"
                :key="app.id"
                class="application-card"
                :href="app.url || undefined"
                target="_blank"
                rel="noopener noreferrer"
              >
                <div>
                  <span
                    :class="['state-dot', `state-${app.status}`]"
                  /><strong>{{ app.name }}</strong>
                </div>
                <p>
                  {{ app.version || "开发版本" }} ·
                  {{ app.commit?.slice(0, 8) || "commit 未记录" }}
                </p>
                <small>{{ app.deployedAt || "部署时间未记录" }}</small>
              </a>
            </div>
            <el-empty v-else description="尚未登记其他应用" :image-size="72" />
          </el-card>

          <el-card shadow="never" class="panel">
            <template #header
              ><div class="panel-header">
                <div>
                  <h2>快捷入口</h2>
                  <p>家庭服务与开发资源</p>
                </div>
              </div></template
            >
            <div class="link-grid">
              <a
                v-for="link in dashboard.links"
                :key="link.id"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="quick-link"
              >
                <strong>{{ link.name }}</strong>
                <p>{{ link.description || link.category }}</p>
                <span>打开 ↗</span>
              </a>
            </div>
          </el-card>
        </section>
      </template>
    </el-skeleton>
  </div>
</template>

<style scoped lang="scss">
.homehub-page {
  padding: 24px;
  min-height: 100%;
  background: radial-gradient(
    circle at top right,
    rgb(64 158 255 / 10%),
    transparent 28%
  );
}
.hero-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 26px 30px;
  margin-bottom: 18px;
  color: white;
  border-radius: 18px;
  background: linear-gradient(125deg, #14213d, #1f4d7a 62%, #2878a9);
  box-shadow: 0 16px 40px rgb(15 40 70 / 18%);
}
.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: #8bd3ff;
}
h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.1;
}
.subtitle {
  margin: 10px 0 0;
  color: rgb(255 255 255 / 72%);
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.status-alert {
  margin-bottom: 18px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.metric-card {
  padding: 20px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  background: var(--el-bg-color);
  box-shadow: 0 8px 24px rgb(20 33 61 / 6%);
}
.metric-heading {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
}
.metric-heading span {
  color: var(--el-text-color-secondary);
  font-weight: 600;
}
.metric-heading strong {
  font-size: 25px;
}
.metric-card p {
  margin: 13px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.metric-card .uptime {
  color: var(--el-text-color-primary);
  font-size: 17px;
  font-weight: 600;
}
.metric-blue {
  border-top: 3px solid #409eff;
}
.metric-purple {
  border-top: 3px solid #8b5cf6;
}
.metric-green {
  border-top: 3px solid #22c55e;
}
.metric-orange {
  border-top: 3px solid #f59e0b;
}
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.8fr);
  gap: 16px;
  margin-bottom: 16px;
}
.lower-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-header h2 {
  margin: 0;
  font-size: 17px;
}
.panel-header p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.service-row {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 13px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.service-row:last-child {
  border-bottom: 0;
}
.state-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgb(144 147 153 / 10%);
}
.state-healthy {
  background: #22c55e;
}
.state-warning {
  background: #f59e0b;
}
.state-down {
  background: #ef4444;
}
.state-unknown {
  background: #909399;
}
.service-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}
.service-copy small {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.service-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.info-list {
  margin: 0;
}
.info-list div {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 11px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.info-list div:last-child {
  border-bottom: 0;
}
.info-list dt {
  color: var(--el-text-color-secondary);
}
.info-list dd {
  margin: 0;
  text-align: right;
  word-break: break-word;
}
.application-grid,
.link-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.application-card,
.quick-link {
  padding: 16px;
  color: inherit;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  text-decoration: none;
  transition: 0.2s ease;
}
.application-card:hover,
.quick-link:hover {
  border-color: var(--el-color-primary-light-5);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgb(64 158 255 / 10%);
}
.application-card > div {
  display: flex;
  align-items: center;
  gap: 9px;
}
.application-card p,
.quick-link p {
  margin: 9px 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.application-card small {
  color: var(--el-text-color-placeholder);
}
.quick-link span {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}
@media (max-width: 1100px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .content-grid,
  .lower-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .homehub-page {
    padding: 12px;
  }
  .hero-panel {
    align-items: flex-start;
    padding: 22px;
    flex-direction: column;
  }
  .hero-actions {
    width: 100%;
    justify-content: space-between;
  }
  .metric-grid {
    grid-template-columns: 1fr;
  }
  .application-grid,
  .link-grid {
    grid-template-columns: 1fr;
  }
  .service-meta > span {
    display: none;
  }
}
</style>
