<template>
  <button :type="type" :class="['app-button', `app-button--${variant}`, `app-button--${size}`, { 'app-button--block': block, 'app-button--wide': wide, 'app-button--icon': iconOnly }]">
    <slot />
  </button>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'button' },
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'md' },
  block: Boolean,
  wide: Boolean,
  iconOnly: Boolean,
})
</script>

<style scoped>
.app-button { display: inline-flex; flex-shrink: 0; align-items: center; justify-content: center; gap: 8px; padding: 0 16px; border: 1px solid transparent; border-radius: 7px; font-size: 13px; font-weight: 700; white-space: nowrap; cursor: pointer; transition: opacity .2s, background .2s, border-color .2s; }.app-button :deep(.material-symbols-outlined) { font-size: 19px; }.app-button--md { height: 44px; }.app-button--sm { height: 40px; }.app-button--xs { height: 32px; padding: 0 8px; font-size: 11px; }.app-button--block { width: 100%; }.app-button--wide { min-width: 128px; }.app-button--icon { width: 44px; padding: 0; }.app-button--primary { color: #fff; border-color: #c6533d; background: #c6533d; box-shadow: 0 5px 12px rgba(198,83,61,.12); }.app-button--outline { color: #c6533d; border-color: #cf624d; background: rgba(255,255,255,.68); }.app-button--danger-outline { color: #c6533d; border-color: #e7ddd7; background: rgba(255,255,255,.7); }.app-button--ghost { color: #52617a; border-color: transparent; background: transparent; font-weight: 500; }.app-button--link { height: auto; padding: 0; color: #c44d3e; border: 0; background: transparent; text-decoration: underline; text-underline-offset: 3px; }.app-button:disabled { opacity: .55; cursor: default; }
</style>
