<template>
  <DashboardIcon v-if="icon === 'voice'" name="voice" />
  <!-- 内联字号覆盖字体类的 24px，跟容器字号保持一致 -->
  <span v-else class="material-symbols-outlined" style="font-size: 1em">{{ icon }}</span>
</template>

<script setup>
import { computed } from 'vue'
import DashboardIcon from './DashboardIcon.vue'
import { deviceIcon } from '@/utils/device-icons'

const props = defineProps({
  type: { type: [Number, String], default: null },
})

const icon = computed(() => deviceIcon(props.type))
</script>