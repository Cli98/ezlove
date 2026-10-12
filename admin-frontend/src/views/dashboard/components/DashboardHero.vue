<template>
  <section class="hero">
    <PageTopbar
      :search="search"
      :worker-name="workerName"
      :pending-events="pendingEvents"
      @events="$emit('events')"
      @search="$emit('search')"
      @update:search="$emit('update:search', $event)"
    />

    <div class="hero__copy">
      <h1>今天的关怀重点</h1>
      <p>从日常信号里，找到需要多问一句的人</p>
    </div>
    <img class="hero__art" src="@/assets/dashboard-composite/hero-community-art-v2.png" alt="温暖社区水彩插画" />
  </section>
</template>

<script setup>
import PageTopbar from '@/components/PageTopbar.vue'

defineEmits(['events', 'search', 'update:search'])
defineProps({
  workerName: { type: String, default: '社工' },
  pendingEvents: { type: Number, default: 0 },
  search: { type: String, default: '' },
})

</script>

<style scoped>
.hero { position: relative; min-height: 170px; margin-bottom: 12px; overflow: hidden; isolation: isolate; }
.hero__copy { position: absolute; z-index: 2; top: 54px; bottom: 0; left: 12px; display: flex; width: 50%; flex-direction: column; justify-content: flex-end; padding: 0 0 8px; }
.hero__copy h1 { align-self: flex-start; margin: 0; color: #292724; font: 900 30px/1.18 'Songti SC', 'STSong', 'Noto Serif SC', serif; letter-spacing: -.01em; transform: scaleX(.94); transform-origin: left center; }
.hero__copy p { margin: 9px 0 0; color: #6e737b; font-size: 13px; letter-spacing: .02em; }
.hero__art { position: absolute; z-index: 0; right: -28px; bottom: 0; width: min(62%, 900px); height: auto; pointer-events: none; }
@media (max-width: 1180px) {
  .hero__art { right: -70px; width: 62%; }
}
@media (max-width: 860px) {
  .hero__art { width: 64%; opacity: .5; }
  .hero__copy { width: 70%; }
}
</style>
