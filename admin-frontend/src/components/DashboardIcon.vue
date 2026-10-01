<template>
  <svg
    class="dashboard-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'home'">
      <path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9"/><path d="M9 20v-7h6v7"/>
    </template>
    <template v-else-if="name === 'archive'">
      <rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>
    </template>
    <template v-else-if="name === 'bowl'">
      <path d="M3 11h18c0 5-3.2 8-9 8s-9-3-9-8Z"/><path d="M7 22h10M7 7c-1.5-1.4-1.5-2.8 0-4M12 7c-1.5-1.4-1.5-2.8 0-4M17 7c-1.5-1.4-1.5-2.8 0-4"/>
    </template>
    <template v-else-if="name === 'heart'">
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>
    </template>
    <template v-else-if="name === 'people'">
      <circle cx="9" cy="8" r="3"/><path d="M3.5 20v-2a5.5 5.5 0 0 1 11 0v2M16 5.3a3 3 0 0 1 0 5.8M17.5 13.6A5 5 0 0 1 21 18.4V20"/>
    </template>
    <template v-else-if="name === 'sparkle'">
      <path d="M12 2c.6 5.4 3.2 8 8 8-4.8 0-7.4 2.6-8 8-.6-5.4-3.2-8-8-8 4.8 0 7.4-2.6 8-8Z"/><path d="M19 16c.2 2 1.2 3 3 3-1.8 0-2.8 1-3 3-.2-2-1.2-3-3-3 1.8 0 2.8-1 3-3Z"/>
    </template>
    <template v-else-if="name === 'sun'">
      <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>
    </template>
    <template v-else-if="name === 'bell'">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>
    </template>
    <template v-else-if="name === 'clipboard'">
      <rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4a3 3 0 0 1 6 0v2H9V4ZM9 11h6M9 15h6"/>
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>
    </template>
    <template v-else-if="name === 'check-circle'">
      <circle cx="12" cy="12" r="9"/><path d="m8 12 2.7 2.7L16.5 9"/>
    </template>
    <template v-else-if="name === 'shield-check'">
      <path d="M12 3 5 6v5c0 4.6 2.7 8.1 7 10 4.3-1.9 7-5.4 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/>
    </template>
    <template v-else-if="name === 'filter'">
      <path d="M4 6h16M7 11h10M10 16h4"/>
    </template>
    <template v-else-if="name === 'chevron-right'">
      <path d="m9 18 6-6-6-6"/>
    </template>
    <template v-else-if="name === 'chevron-down'">
      <path d="m6 9 6 6 6-6"/>
    </template>
    <template v-else-if="name === 'walk'">
      <circle cx="14" cy="4" r="2"/><path d="m10 21 2-7-3-2 2-5 4 2 3 3M12 14l4 2 2 5M9 12l-3 4"/>
    </template>
  </svg>
</template>

<script setup>
defineProps({ name: { type: String, required: true } })
</script>

<style scoped>
.dashboard-icon { width: 1em; height: 1em; display: block; flex: none; }
</style>
