<template>
  <div class="page-topbar">
    <div class="page-topbar__greeting">
      <DashboardIcon name="sun" />
      <strong>{{ greeting }}，{{ workerName }}</strong>
      <i></i>
      <span>{{ dateText }}</span>
    </div>
    <div class="page-topbar__actions">
      <label class="page-topbar__search">
        <DashboardIcon name="search" />
        <input
          :value="search"
          :placeholder="placeholder"
          @input="$emit('update:search', $event.target.value)"
          @keyup.enter="$emit('search')"
        />
      </label>
      <button class="page-topbar__notice" aria-label="查看关怀事件" @click="$emit('events')">
        <DashboardIcon name="bell" />
        <b v-if="pendingEvents"></b>
      </button>
      <img class="page-topbar__avatar" src="@/assets/dashboard-reference/worker-avatar.png" :alt="workerName" />
      <div class="page-topbar__profile">
        <strong>{{ workerName }}</strong>
        <small>和社区，一起守护</small>
      </div>
      <DashboardIcon class="page-topbar__chevron" name="chevron-down" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import DashboardIcon from '@/components/DashboardIcon.vue'

defineEmits(['events', 'search', 'update:search'])
defineProps({
  workerName: { type: String, default: '社工' },
  pendingEvents: { type: Number, default: 0 },
  search: { type: String, default: '' },
  placeholder: { type: String, default: '搜索老人姓名、楼栋或关键词…' },
})

const now = new Date()
const weekday = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][now.getDay()]
const dateText = `${now.getMonth() + 1}月${now.getDate()}日  ${weekday}`
const greeting = computed(() => now.getHours() < 12 ? '早上好' : now.getHours() < 18 ? '下午好' : '晚上好')
</script>

<style scoped>
.page-topbar { position: relative; z-index: 3; display: flex; min-height: 54px; align-items: center; justify-content: space-between; gap: 24px; }
.page-topbar__greeting, .page-topbar__actions { display: flex; align-items: center; }
.page-topbar__greeting { gap: 13px; color: #292724; }
.page-topbar__greeting :deep(.dashboard-icon) { color: #df861f; font-size: 26px; }
.page-topbar__greeting strong { display: inline-block; margin-right: -10px; color: #292724; font: 900 21px/1.2 'Songti SC','STSong','Noto Serif SC',serif; letter-spacing: -.01em; transform: scaleX(.94); transform-origin: left center; }
.page-topbar__greeting i { width: 1px; height: 22px; margin-left: 3px; background: #e6dfd7; }
.page-topbar__greeting span { color: #6d6d70; font-size: 12px; }
.page-topbar__actions { gap: 13px; transform: translateX(-5px); }
.page-topbar__search { display: flex; width: 296px; height: 44px; align-items: center; gap: 9px; padding: 0 14px; color: #667080; border: 1px solid #d8d0c8; border-radius: 12px; background: rgba(255,255,255,.78); }
.page-topbar__search :deep(.dashboard-icon) { font-size: 17px; }
.page-topbar__search input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: #302e2b; font-size: 12.5px; }
.page-topbar__search input::placeholder { color: #92929a; }
.page-topbar__notice { position: relative; display: grid; width: 38px; height: 38px; place-items: center; border: 0; color: #2f302f; background: transparent; cursor: pointer; }
.page-topbar__notice :deep(.dashboard-icon) { font-size: 21px; }
.page-topbar__notice b { position: absolute; top: 4px; right: 4px; width: 7px; height: 7px; border: 1px solid #fff; border-radius: 50%; background: #c64f3a; }
.page-topbar__avatar { width: 51px; height: 51px; object-fit: cover; border: 1px solid rgba(255,255,255,.9); border-radius: 50%; box-shadow: 0 1px 5px rgba(50,40,32,.09); }
.page-topbar__profile { display: grid; width: 82px; gap: 3px; margin-left: -5px; white-space: nowrap; }
.page-topbar__profile strong { color: #272625; font-size: 13px; }.page-topbar__profile small { color: #8d8a86; font-size: 10.5px; }
.page-topbar__chevron { color: #65707c; font-size: 13px; transform: scale(1.2); }
@media (max-width: 1180px) { .page-topbar__search { width: 235px; }.page-topbar__profile, .page-topbar__chevron { display: none; } }
@media (max-width: 860px) { .page-topbar__search { display: none; } }
</style>
