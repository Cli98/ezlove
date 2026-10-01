<template>
  <label class="inline-select">
    <span>{{ selected?.label || placeholder }}</span>
    <DashboardIcon name="chevron-down" />
    <select :value="selectedIndex" :aria-label="ariaLabel" :disabled="disabled" @change="change">
      <option v-for="(option,index) in options" :key="`${index}-${option.label}`" :value="index">{{ option.label }}</option>
    </select>
  </label>
</template>

<script setup>
import { computed } from 'vue'
import DashboardIcon from '@/components/DashboardIcon.vue'

const props = defineProps({
  modelValue: { default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择' },
  ariaLabel: { type: String, default: '选择选项' },
  disabled: Boolean,
})
const emit = defineEmits(['update:modelValue', 'change'])
const selectedIndex = computed(() => Math.max(0, props.options.findIndex(option => Object.is(option.value, props.modelValue))))
const selected = computed(() => props.options[selectedIndex.value])

function change(event) {
  const value = props.options[Number(event.target.value)]?.value
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped>
.inline-select { position: relative; display: inline-flex; min-width: 0; height: 42px; align-items: center; gap: 7px; padding: 0 12px; border: 1px solid #ddd5cd; border-radius: 8px; color: #4e5868; background: #fff; white-space: nowrap; cursor: pointer; }
.inline-select > span { overflow: hidden; text-overflow: ellipsis; }.inline-select :deep(.dashboard-icon) { flex: none; font-size: 13px; }.inline-select select { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }.inline-select:focus-within { border-color: rgba(196,77,62,.65); }.inline-select:has(select:disabled) { opacity: .5; cursor: default; }
</style>
