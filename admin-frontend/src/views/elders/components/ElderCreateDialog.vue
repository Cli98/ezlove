<template>
  <div v-if="open" class="dialog-layer">
    <div class="dialog-backdrop" @click="$emit('close')"></div>
    <section class="dialog-card">
      <header><h3>{{ isEdit ? '编辑老人信息' : '新增老人' }}</h3></header>
      <div class="dialog-form">
        <label v-if="!isEdit">老人ID（UUID）<input v-model="form.elder_id" placeholder="输入老人的用户ID" /></label>
        <div v-else class="identity-fields"><label>姓名<input v-model="form.name" maxlength="32" placeholder="输入老人姓名" /></label><label>性别<InlineSelect v-model="form.gender" class="gender-select" aria-label="选择性别" :options="genderOptions" /></label></div>
        <div><b>关怀分级</b><div class="level-options"><button v-for="level in ['A','B','C']" :key="level" :class="{ active: form.care_level === level }" @click="form.care_level = level">{{ level }}级</button></div></div>
        <label>楼栋/门牌<input v-model="form.address" placeholder="例：和谐社区1号楼203室" /></label>
        <label>健康备注<textarea v-model="form.health_notes" rows="3" placeholder="如：高血压、行动不便等"></textarea></label>
        <div class="contact-fields"><label>紧急联系人<input v-model="form.emergency_contact_name" placeholder="联系人姓名" /></label><label>联系电话<input v-model="form.emergency_contact_phone" placeholder="联系人手机号" /></label></div>
      </div>
      <footer><button @click="$emit('close')">取消</button><button class="primary" :disabled="submitting" @click="submit">{{ submitting ? '提交中…' : isEdit ? '保存修改' : '确认添加' }}</button></footer>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import InlineSelect from '@/components/InlineSelect.vue'

const props = defineProps({ open: Boolean, submitting: Boolean, mode: { type: String, default: 'create' }, initial: { type: Object, default: () => ({}) } })
const emit = defineEmits(['close', 'submit'])
const isEdit = computed(() => props.mode === 'edit')
const genderOptions = [{ value: '', label: '未填写' }, { value: '男', label: '男' }, { value: '女', label: '女' }, { value: '其他', label: '其他' }]
const form = reactive({ elder_id: '', name: '', gender: '', care_level: 'B', address: '', health_notes: '', emergency_contact_name: '', emergency_contact_phone: '' })

watch(() => props.open, open => {
  if (!open) return
  const contact = props.initial.emergency_contact || {}
  Object.assign(form, {
    elder_id: '', name: props.initial.name || '', gender: props.initial.gender || '', care_level: props.initial.care_level || 'B',
    address: props.initial.address || '', health_notes: props.initial.health_notes || '',
    emergency_contact_name: contact.name || '', emergency_contact_phone: contact.phone || '',
  })
})

function submit() {
  if (!isEdit.value && !form.elder_id) return ElMessage.warning('请填写老人ID')
  if (isEdit.value && !form.name.trim()) return ElMessage.warning('请填写老人姓名')
  const payload = { ...form }
  if (isEdit.value) delete payload.elder_id
  else delete payload.name
  if (!payload.gender) delete payload.gender
  emit('submit', payload)
}
</script>

<style scoped>
.dialog-layer { position: fixed; z-index: 200; inset: 0; display: grid; place-items: center; }.dialog-backdrop { position: absolute; inset: 0; background: rgba(35,31,28,.42); backdrop-filter: blur(3px); }.dialog-card { position: relative; width: min(500px,calc(100vw - 40px)); overflow: hidden; border-radius: 18px; background: #fff; box-shadow: 0 24px 70px rgba(35,28,22,.24); animation: dialog-in .25s ease-out; }.dialog-card header, .dialog-card footer { display: flex; align-items: center; padding: 16px 22px; border-bottom: 1px solid #eee8e2; }.dialog-card h3 { margin: 0; color: #292724; font: 700 20px 'Songti SC','STSong',serif; }.dialog-form { display: grid; gap: 16px; padding: 20px 22px; }.dialog-form label, .dialog-form > div { display: grid; gap: 7px; color: #403e3b; font-size: 13px; font-weight: 700; }.dialog-form input, .dialog-form textarea { width: 100%; padding: 10px 12px; border: 1px solid #ddd5cd; border-radius: 8px; outline: 0; color: #333; background: #fff; font: 13px sans-serif; resize: none; }.dialog-form input:focus, .dialog-form textarea:focus { border-color: rgba(196,77,62,.65); }.gender-select { display: inline-flex!important; width: 100%; height: 39px; font: 13px sans-serif; }.identity-fields { display: grid!important; grid-template-columns: minmax(0,2fr) minmax(120px,1fr); gap: 12px!important; }.level-options { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; }.level-options button { height: 38px; border: 1px solid #ddd5cd; border-radius: 8px; color: #666; background: #fff; cursor: pointer; }.level-options button.active { color: #c44d3e; border-color: #c44d3e; background: #fbede8; }.dialog-card footer { justify-content: flex-end; gap: 10px; border-top: 1px solid #eee8e2; border-bottom: 0; }.dialog-card footer button { height: 38px; padding: 0 18px; border: 0; border-radius: 7px; color: #666; background: transparent; cursor: pointer; }.dialog-card footer .primary { color: #fff; background: #c6533d; }.dialog-card footer button:disabled { opacity: .55; cursor: default; }
@keyframes dialog-in { from { opacity: 0; transform: translateY(10px); } }
.contact-fields { display: grid!important; grid-template-columns: 1fr 1fr; gap: 12px!important; }
</style>
