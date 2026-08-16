<template>
  <div class="dashboard-container">
    <!-- 顶部数据统计卡片 -->
    <a-row :gutter="16" class="stat-row">
      <a-col :span="6">
        <a-card class="modern-stat-card clickable-card" :bordered="false" @click="router.push('/asset-search')">
          <div class="stat-flex">
            <div class="stat-icon-box primary">
              <DatabaseOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-label">总站点数量</div>
              <div class="stat-value">{{ stats.total_assets }}</div>
            </div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="6">
        <a-card class="modern-stat-card" :bordered="false">
          <div class="stat-flex">
            <div class="stat-icon-box success">
              <SyncOutlined />
            </div>
            <div class="stat-info" style="width: 100%;">
              <div class="stat-label">今日动态</div>
              <div class="stat-split-values">
                <div class="stat-split-item" @click="router.push('/taskList')">
                  <div class="val">{{ stats.today_tasks }}</div>
                  <div class="sub-label">新增任务</div>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-split-item" @click="router.push('/asset-search')">
                  <div class="val text-primary">{{ stats.today_new_assets }}</div>
                  <div class="sub-label">新增站点</div>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="6">
        <a-card class="modern-stat-card" :bordered="false">
          <div class="stat-flex">
            <div class="stat-icon-box danger">
              <AlertOutlined />
            </div>
            <div class="stat-info" style="width: 100%;">
              <div class="stat-label">漏洞分布</div>
              <div class="stat-vuln-bar">
                <a-tooltip title="严重 (Nuclei)">
                  <div class="vuln-item critical" @click="router.push({ path: '/asset-search', query: { tab: 'nuclei_result', vuln_severity: 'critical' } })">{{ stats.vuln.nuclei_critical }}</div>
                </a-tooltip>
                <a-tooltip title="高危 (Nuclei)">
                  <div class="vuln-item high" @click="router.push({ path: '/asset-search', query: { tab: 'nuclei_result', vuln_severity: 'high' } })">{{ stats.vuln.nuclei_high }}</div>
                </a-tooltip>
                <a-tooltip title="中危 (Nuclei)">
                  <div class="vuln-item medium" @click="router.push({ path: '/asset-search', query: { tab: 'nuclei_result', vuln_severity: 'medium' } })">{{ stats.vuln.nuclei_medium }}</div>
                </a-tooltip>
                <a-tooltip title="低危 (Nuclei)">
                  <div class="vuln-item low" @click="router.push({ path: '/asset-search', query: { tab: 'nuclei_result', vuln_severity: 'low' } })">{{ stats.vuln.nuclei_low }}</div>
                </a-tooltip>
                <a-tooltip title="ARL 内部检测">
                  <div class="vuln-item arl" @click="router.push({ path: '/asset-search', query: { tab: 'vuln' } })">{{ stats.vuln.arl_total }}</div>
                </a-tooltip>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="6">
        <a-card class="modern-stat-card clickable-card" :bordered="false" @click="router.push('/GitHubTasks/GitHubTasksList')">
          <div class="stat-flex">
            <div class="stat-icon-box dark">
              <GithubOutlined />
            </div>
            <div class="stat-info" style="width: 100%;">
              <div class="stat-label">GitHub 监控动态 (今日)</div>
              <div class="stat-split-values" style="margin-top: 4px;">
                <div class="stat-split-item" @click.stop="router.push('/GitHubTasks/GitHubTasksList?tab=scheduler')">
                  <div class="val" style="color: #f5222d">{{ sysInfo.github_today?.leaks || 0 }}</div>
                  <div class="sub-label">新增泄露</div>
                </div>
                <div class="stat-divider"></div>
                <a-tooltip placement="bottom">
                  <template #title>
                    <div style="font-size: 12px; line-height: 1.5;">
                      <div style="font-weight: bold; margin-bottom: 4px; color: #faad14;">今日新增明细：</div>
                      <div>● 新增 CVE：{{ sysInfo.github_today_breakdown?.cves || 0 }}</div>
                      <div>● 追踪大佬：{{ sysInfo.github_today_breakdown?.hackers || 0 }}</div>
                      <div>● 其他情报：{{ sysInfo.github_today_breakdown?.general || 0 }}</div>
                      <div style="border-top: 1px dashed rgba(255,255,255,0.4); margin: 6px 0;"></div>
                      <div style="font-weight: bold; margin-bottom: 4px;">全库累计收录：</div>
                      <div>● 累计 CVE：{{ sysInfo.github_totals?.cves || 0 }}</div>
                      <div>● 监控工具：{{ sysInfo.github_totals?.tools || 0 }}</div>
                      <div>● 追踪大佬：{{ sysInfo.github_totals?.hackers || 0 }}</div>
                    </div>
                  </template>
                  <div class="stat-split-item" @click.stop="router.push('/GitHubTasks/GitHubTasksList?tab=cve_history')">
                    <div class="val" style="color: #faad14">{{ sysInfo.github_today?.intel || 0 }}</div>
                    <div class="sub-label">新增情报</div>
                  </div>
                </a-tooltip>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 系统状态区域 -->
    <a-row :gutter="16" style="margin-top: 16px;">
      <a-col :span="6">
        <a-card class="modern-stat-card" :bordered="false">
          <div class="sys-flex">
            <div class="sys-info">
              <div class="sys-label">CPU 占用</div>
              <div class="sys-value" :style="{ color: sysInfo.cpu_percent > 80 ? '#ff4d4f' : 'inherit' }">{{ sysInfo.cpu_percent }}%</div>
            </div>
            <a-progress type="circle" :percent="sysInfo.cpu_percent" :width="56" :strokeWidth="8" :strokeColor="sysInfo.cpu_percent > 80 ? '#ff4d4f' : 'var(--arl-theme-color)'" :showInfo="false" />
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="modern-stat-card" :bordered="false">
          <div class="sys-flex">
            <div class="sys-info">
              <div class="sys-label">内存占用</div>
              <div class="sys-value" :style="{ color: sysInfo.mem_percent > 80 ? '#ff4d4f' : 'inherit' }">{{ sysInfo.mem_percent }}%</div>
            </div>
            <a-progress type="circle" :percent="sysInfo.mem_percent" :width="56" :strokeWidth="8" :strokeColor="sysInfo.mem_percent > 80 ? '#ff4d4f' : 'var(--arl-theme-color)'" :showInfo="false" />
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="modern-stat-card" :bordered="false">
          <div class="sys-flex">
            <div class="sys-info">
              <div class="sys-label">磁盘占用</div>
              <div class="sys-value" :style="{ color: sysInfo.disk_percent > 90 ? '#ff4d4f' : 'inherit' }">{{ sysInfo.disk_percent }}%</div>
            </div>
            <a-progress type="circle" :percent="sysInfo.disk_percent" :width="56" :strokeWidth="8" :strokeColor="sysInfo.disk_percent > 90 ? '#ff4d4f' : '#52c41a'" :showInfo="false" />
          </div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="modern-stat-card" :bordered="false">
          <div class="sys-flex">
            <div class="sys-info" style="width: 100%;">
              <div class="sys-label">后台任务 (Celery)</div>
              <div class="stat-split-values" style="margin-top: 8px;">
                <div class="stat-split-item">
                  <div class="val" style="color: #52c41a">{{ sysInfo.tasks.running }}</div>
                  <div class="sub-label">运行中</div>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-split-item">
                  <div class="val" style="color: #fb8c00">{{ sysInfo.tasks.waiting }}</div>
                  <div class="sub-label">等待中</div>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 主体区域 -->
    <a-row :gutter="16" style="margin-top: 16px;">
      <!-- 左侧：趋势图表区域 -->
      <a-col :span="16">
        <a-card title="近7天站点与风险趋势" style="height: 100%;">
          <div ref="chartRef" style="width: 100%; height: 300px;"></div>
        </a-card>
      </a-col>

      <!-- 右侧：最新动态 (Log 展示) -->
      <a-col :span="8">
        <a-card title="最新系统动态 (Log)" style="height: 100%;" :bodyStyle="{ maxHeight: '400px', overflowY: 'auto' }">
          <a-timeline>
            <a-timeline-item 
              v-for="(log, index) in logs" 
              :key="index" 
              :color="getLogColor(log.level)"
              class="clickable-log"
              @click="showLogDetail(log)">
              <p>
                <strong>[{{ log.title || (log.level === 'error' ? '异常' : '通知') }}]</strong> 
                {{ log.create_time }}
              </p>
              <p>{{ log.message }}</p>
            </a-timeline-item>
            <a-empty v-if="logs.length === 0" description="暂无系统动态" />
          </a-timeline>
        </a-card>
      </a-col>
    </a-row>

    <!-- 日志详情弹窗 -->
    <a-modal
      v-model:visible="isLogModalVisible"
      title="系统动态详情"
      :footer="null"
      width="600px"
    >
      <div v-if="currentLog" class="log-detail-content">
        <p><strong>【级别】</strong> <a-tag :color="getLogColor(currentLog.level)">{{ currentLog.level }}</a-tag></p>
        <p><strong>【时间】</strong> {{ currentLog.create_time }}</p>
        <p><strong>【标题】</strong> {{ currentLog.title || (currentLog.level === 'error' ? '异常' : '通知') }}</p>
        <div style="margin-top: 16px;">
          <strong>【详细信息】</strong>
          <div class="log-message-box">
            {{ currentLog.message }}
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { 
  DatabaseOutlined, 
  SyncOutlined, 
  AlertOutlined, 
  GithubOutlined 
} from '@ant-design/icons-vue';
import * as echarts from 'echarts/core';
import { LineChart, BarChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  LineChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  CanvasRenderer
]);
import request from '@/utils/request';

const router = useRouter();

const isDarkMode = ref(localStorage.getItem('arl_dark_mode') === 'true');
const handleThemeChange = () => {
  isDarkMode.value = localStorage.getItem('arl_dark_mode') === 'true';
  initChart();
};

onMounted(() => {
  window.addEventListener('theme-changed', handleThemeChange);
});
onUnmounted(() => {
  window.removeEventListener('theme-changed', handleThemeChange);
});

const chartRef = ref(null);
let myChart = null;

// 日志弹窗相关状态
const isLogModalVisible = ref(false);
const currentLog = ref(null);

const showLogDetail = (log) => {
  currentLog.value = log;
  isLogModalVisible.value = true;
};

// 响应式数据绑定
const stats = ref({
  total_assets: 0,
  today_tasks: 0,
  today_new_assets: 0,
  vuln: { arl_total: 0, nuclei_critical: 0, nuclei_high: 0, nuclei_medium: 0, nuclei_low: 0 },
  github_monitors: 0
});

const sysInfo = ref({
  cpu_percent: 0,
  mem_percent: 0,
  disk_percent: 0,
  tasks: { running: 0, waiting: 0 },
  github_today: { leaks: 0, intel: 0 },
  github_today_breakdown: { cves: 0, hackers: 0, general: 0 },
  github_totals: { cves: 0, tools: 0, hackers: 0 }
});

const logs = ref([]);

// 动态获取颜色
const getLogColor = (level) => {
  const map = {
    'info': 'blue',
    'success': 'green',
    'warning': 'orange',
    'error': 'red'
  };
  return map[level] || 'gray';
};

const fetchStats = async () => {
  try {
    const res = await request.get('/api/dashboard/stats');
    if (res.code === 200) {
      stats.value = res.data;
    }
  } catch (error) {
    console.error('Failed to fetch stats:', error);
  }
};

const fetchSysInfo = async () => {
  try {
    const res = await request.get('/api/dashboard/sysinfo');
    if (res.code === 200) {
      sysInfo.value = res.data;
    }
  } catch (error) {
    console.error('Failed to fetch sysinfo:', error);
  }
};

const fetchLogs = async () => {
  try {
    const res = await request.get('/api/dashboard/logs');
    if (res.code === 200) {
      logs.value = res.data.logs;
    }
  } catch (error) {
    console.error('Failed to fetch logs:', error);
  }
};

const fetchTrendAndRender = async () => {
  try {
    const res = await request.get('/api/dashboard/trend');
    if (res.code === 200 && myChart) {
      const { days, assets, vulns, leaks, cves } = res.data;
      
      const themeColor = getComputedStyle(document.documentElement).getPropertyValue('--arl-theme-color').trim() || '#1890ff';
      const isDark = isDarkMode.value;

      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: { 
            type: 'line',
            lineStyle: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', width: 1 }
          },
          backgroundColor: isDark ? 'rgba(17, 17, 17, 0.75)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? '#333333' : '#e2e8f0',
          textStyle: { color: isDark ? 'rgba(255, 255, 255, 0.85)' : '#333333' },
          extraCssText: 'backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);',
          padding: 12
        },
        legend: {
          data: ['新增站点', '漏洞', '代码泄露', 'CVE'],
          top: 0,
          textStyle: { color: isDark ? 'rgba(255, 255, 255, 0.65)' : '#666', fontWeight: 500 }
        },
        grid: {
          left: '2%',
          right: '2%',
          bottom: '2%',
          top: '15%',
          containLabel: true
        },
        xAxis: [
          {
            type: 'category',
            data: days,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: isDark ? 'rgba(255, 255, 255, 0.45)' : '#999', margin: 16 }
          }
        ],
        yAxis: [
          {
            type: 'value',
            name: '站点数量',
            nameTextStyle: { color: isDark ? 'rgba(255, 255, 255, 0.45)' : '#999', padding: [0, 0, 0, 20] },
            axisLabel: { color: isDark ? 'rgba(255, 255, 255, 0.45)' : '#999' },
            splitLine: { show: false },
            axisLine: { show: false },
            axisTick: { show: false }
          },
          {
            type: 'value',
            name: '风险/事件数量',
            nameTextStyle: { color: isDark ? 'rgba(255, 255, 255, 0.45)' : '#999', padding: [0, 20, 0, 0] },
            axisLabel: { color: isDark ? 'rgba(255, 255, 255, 0.45)' : '#999' },
            splitLine: { show: false },
            axisLine: { show: false },
            axisTick: { show: false }
          }
        ],
        series: [
          {
            name: '新增站点',
            type: 'line',
            smooth: true,
            symbol: 'none',
            data: assets,
            itemStyle: { color: themeColor },
            lineStyle: { width: 3, color: themeColor },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: themeColor.replace('rgb', 'rgba').replace(')', ', 0.3)') || 'rgba(24,144,255,0.3)' },
                { offset: 1, color: themeColor.replace('rgb', 'rgba').replace(')', ', 0.0)') || 'rgba(24,144,255,0)' }
              ])
            }
          },
          {
            name: '漏洞',
            type: 'bar',
            yAxisIndex: 1,
            barMaxWidth: 8,
            itemStyle: { 
              color: isDark ? '#444444' : '#d9d9d9',
              borderRadius: [4, 4, 0, 0] 
            },
            data: vulns
          },
          {
            name: '代码泄露',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            symbol: 'none',
            data: leaks || [],
            itemStyle: { color: isDark ? '#888888' : '#8c8c8c' },
            lineStyle: { width: 2, type: 'dashed' }
          },
          {
            name: 'CVE',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            symbol: 'none',
            data: cves || [],
            itemStyle: { color: isDark ? '#cccccc' : '#595959' },
            lineStyle: { width: 2 }
          }
        ]
      };
      
      myChart.setOption(option);
    }
  } catch (error) {
    console.error('Failed to fetch trend:', error);
  }
};

let sysInfoTimer = null;

onMounted(() => {
  if (chartRef.value) {
    myChart = echarts.init(chartRef.value);
    
    const handleResize = () => {
      myChart.resize();
    };
    window.addEventListener('resize', handleResize);
    myChart.__resizeHandler = handleResize;
  }
  
  // 并发请求所有数据
  Promise.all([
    fetchStats(),
    fetchLogs(),
    fetchTrendAndRender(),
    fetchSysInfo()
  ]);
  
  // 每 5 秒自动刷新一次系统状态
  sysInfoTimer = setInterval(() => {
    fetchSysInfo();
  }, 5000);
});

onUnmounted(() => {
  if (sysInfoTimer) clearInterval(sysInfoTimer);
  
  if (myChart) {
    if (myChart.__resizeHandler) {
      window.removeEventListener('resize', myChart.__resizeHandler);
    }
    myChart.dispose();
  }
});
</script>

<style scoped>
.dashboard-container {
  padding: 16px;
  background: var(--arl-bg-layout);
  min-height: calc(100vh - 64px - 48px);
}
.stat-row {
  display: flex;
  align-items: stretch;
}
.stat-row .ant-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-radius: 8px;
  
  transition: all 0.3s ease;
}
.stat-row .ant-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.stat-row .clickable-card {
  cursor: pointer;
}
.stat-row .clickable-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.1) !important;
}
.clickable-log {
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background-color 0.3s;
}
.clickable-log:hover {
  background-color: var(--arl-bg-light);
}

.interactive-item {
  transition: all 0.25s cubic-bezier(0.645, 0.045, 0.355, 1);
  border-radius: 6px;
  padding: 4px;
}
.interactive-item:hover {
  background-color: rgba(24, 144, 255, 0.08);
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* ========================================================
   现代数据卡片 (Modern Stat Cards)
   ======================================================== */
.modern-stat-card {
  height: 100%;
  border-radius: 12px;
  transition: all 0.3s ease;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.modern-stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}
.modern-stat-card :deep(.ant-card-body) {
  padding: 20px;
  display: flex;
  align-items: center;
  height: 100%;
}
.stat-flex, .sys-flex {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 16px;
}
.sys-flex {
  justify-content: space-between;
}
.stat-icon-box {
  width: 54px;
  height: 54px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}
.stat-icon-box.primary {
  background: rgba(24, 144, 255, 0.1);
  color: var(--arl-theme-color);
}
.stat-icon-box.success {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
}
.stat-icon-box.danger {
  background: rgba(245, 34, 45, 0.1);
  color: #f5222d;
}
.stat-icon-box.dark {
  background: var(--arl-border-color);
  color: var(--arl-text-color);
}
.stat-info, .sys-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.stat-label, .sys-label {
  font-size: 14px;
  color: var(--arl-text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}
.stat-value, .sys-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--arl-text-color);
  line-height: 1.2;
}

/* 分割数值区域 (Split Values) */
.stat-split-values {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.stat-split-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.3s;
}
.stat-split-item:hover {
  background: var(--arl-bg-light);
}
.stat-split-item .val {
  font-size: 18px;
  font-weight: 600;
  color: var(--arl-text-color);
}
.stat-split-item .val.text-primary {
  color: var(--arl-theme-color);
}
.stat-split-item .sub-label {
  font-size: 12px;
  color: var(--arl-text-color);
  opacity: 0.45;
}
.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--arl-border-color);
  margin: 0 8px;
}

/* 漏洞分布条 (Vuln Bar) */
.stat-vuln-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}
.vuln-item {
  flex: 1;
  text-align: center;
  padding: 4px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  transition: all 0.3s;
}
.vuln-item:hover {
  transform: translateY(-2px);
  filter: brightness(1.1);
}
.vuln-item.critical { background: #e53935; }
.vuln-item.high { background: #f4511e; }
.vuln-item.medium { background: #fb8c00; }
.vuln-item.low { background: #1e88e5; }
.vuln-item.arl { background: #8e24aa; }

.log-message-box {
  margin-top: 8px;
  padding: 12px;
  background-color: var(--arl-bg-light);
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--arl-text-color);
}
.interactive-item {
  transition: transform 0.2s, opacity 0.2s;
}
.interactive-item:hover {
  transform: scale(1.05);
  opacity: 0.85;
}
</style>
