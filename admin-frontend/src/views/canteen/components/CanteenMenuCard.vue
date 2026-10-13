<template>
  <AppPanel class="menu-card">
    <header>
      <h2>今日菜单</h2>
      <div class="menu-controls">
        <InlineSelect :model-value="mealType" :options="mealOptions" class="meal-select" @change="$emit('update:mealType', $event)" />
        <div class="date-switcher">
          <button aria-label="前一天" @click="$emit('shift', -1)">‹</button>
          <span>{{ dateLabel }}</span>
          <button aria-label="后一天" @click="$emit('shift', 1)">›</button>
        </div>
      </div>
    </header>
    <div v-if="menu" class="menu-status">{{ menu.status === 'published' ? '已发布' : '草稿' }}</div>
    <div v-if="menu" class="dish-grid">
      <article v-for="dish in menu.dishes?.items || []" :key="dish.name">
        <i :class="dish.category === '荤菜' ? 'meat' : 'vegetable'"></i>
        <div><strong>{{ dish.name }}</strong><p>{{ dish.description }}</p></div>
      </article>
    </div>
    <div v-else class="menu-empty">该餐次暂无菜单</div>
    <div v-if="menu" class="menu-extras">
      <span v-if="menu.dishes?.soup"><b>汤</b>{{ menu.dishes.soup }}</span>
      <span v-if="menu.dishes?.staple"><b class="material-symbols-outlined">rice_bowl</b>{{ menu.dishes.staple }}</span>
    </div>
    <footer>
      <AppButton block size="sm" class="publish" :disabled="busy" @click="$emit('publish')">{{ busy ? '处理中…' : menu?.status === 'published' ? '已发布' : '发布' }}</AppButton>
      <AppButton variant="danger-outline" size="sm" icon-only class="delete" :disabled="!menu" aria-label="删除菜单" @click="$emit('delete')"><span class="material-symbols-outlined">delete</span></AppButton>
    </footer>
  </AppPanel>
</template>

<script setup>
import InlineSelect from '@/components/InlineSelect.vue'
import AppButton from '@/components/AppButton.vue'
import AppPanel from '@/components/AppPanel.vue'

defineProps({ menu: { type: Object, default: null }, mealType: { type: String, default: 'lunch' }, dateLabel: { type: String, default: '' }, busy: Boolean })
defineEmits(['update:mealType', 'shift', 'publish', 'delete'])
const mealOptions = [{ value: 'lunch', label: '午餐' }, { value: 'dinner', label: '晚餐' }]
</script>

<style scoped>
.menu-card { position: relative; display: flex; flex-direction: column; overflow-y: auto; padding: 16px 18px; }.menu-card header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.menu-card h2 { margin: 0; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }.menu-controls { display: flex; align-items: center; gap: 9px; }.meal-select { height: 32px!important; padding: 0 10px; font-size: 11px; }.date-switcher { display: grid; width: 176px; height: 32px; grid-template-columns: 34px 1fr 34px; align-items: stretch; border: 1px solid #e2dcd5; border-radius: 7px; background: #fff; }.date-switcher button { display: grid; padding: 0; place-items: center; border: 0; color: #34445c; background: transparent; font-size: 24px; line-height: 1; cursor: pointer; }.date-switcher span { display: grid; place-items: center; color: #4d5c74; font-size: 12px; }.menu-status { align-self: end; margin: 8px 0 5px; padding: 4px 15px; border-radius: 7px; color: #b07a22; background: #fbf0dc; font-size: 10px; }.dish-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }.dish-grid article { display: flex; min-height: 67px; align-items: center; gap: 12px; padding: 9px 13px; border-radius: 7px; background: linear-gradient(105deg,#fbf4ee,#faf8f5); }.dish-grid i { width: 12px; height: 12px; flex: none; border-radius: 50%; background: #70a58c; }.dish-grid i.meat { background: #d45a40; }.dish-grid strong { color: #172942; font: 700 14px 'Songti SC','STSong',serif; }.dish-grid p { margin: 4px 0 0; color: #778195; font-size: 10px; }.menu-extras { display: flex; min-height: 35px; align-items: center; gap: 24px; margin-top: 8px; padding: 5px 13px; border-radius: 7px; color: #34445c; background: linear-gradient(105deg,#fbf4ee,#faf8f5); font-size: 11px; }.menu-extras span { display: flex; min-width: 0; align-items: center; gap: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.menu-extras b { color: #c75a42; font-size: 12px; }.menu-extras .material-symbols-outlined { color: #172942; font-size: 20px; }.menu-empty { display: grid; min-height: 190px; place-items: center; color: #91867c; font-size: 13px; }.menu-card footer { display: grid; grid-template-columns: 1fr 52px; gap: 10px; margin-top: auto; padding-top: 10px; }.publish, .delete { border-radius: 6px; }
</style>
