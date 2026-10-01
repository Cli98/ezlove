<template>
  <AppPanel class="entry-card">
    <h2>录入就餐数据</h2>
    <label>文本描述</label>
    <div class="text-entry">
      <textarea :value="rawText" maxlength="500" placeholder="例：今天中午食堂，张大爷来了，李奶奶没来……" @input="$emit('update:rawText', $event.target.value)"></textarea>
      <span>{{ rawText.length }}/500</span>
    </div>
    <label>或上传 Excel 文件</label>
    <button class="file-drop" @click="fileInput.click()" @dragover.prevent @drop.prevent="pickDroppedFile">
      <span class="material-symbols-outlined">upload_file</span>
      <span>{{ fileName || '将文件拖拽到此处，或' }} <u v-if="!fileName">点击选择</u></span>
    </button>
    <input ref="fileInput" type="file" accept=".xlsx,.xls" hidden @change="pickFile" />
    <AppButton block size="sm" class="primary-action" :disabled="submitting" @click="$emit('submit')">
      {{ submitting ? '解析中…' : 'AI 解析并提交' }}
    </AppButton>
  </AppPanel>
</template>

<script setup>
import { ref } from 'vue'
import AppButton from '@/components/AppButton.vue'
import AppPanel from '@/components/AppPanel.vue'

defineProps({ rawText: { type: String, default: '' }, fileName: { type: String, default: '' }, submitting: Boolean })
const emit = defineEmits(['update:rawText', 'file', 'submit'])
const fileInput = ref(null)

function choose(file) {
  if (file && /\.xlsx?$/i.test(file.name)) emit('file', file)
}
function pickFile(event) { choose(event.target.files?.[0]) }
function pickDroppedFile(event) { choose(event.dataTransfer?.files?.[0]) }
</script>

<style scoped>
.entry-card { display: flex; flex-direction: column; overflow-y: auto; padding: 16px 20px; }.entry-card h2 { margin: 0 0 16px; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }.entry-card label { margin: 0 0 7px; color: #45546b; font-size: 13px; }.text-entry { position: relative; min-height: 96px; margin-bottom: 16px; }.text-entry textarea { box-sizing: border-box; width: 100%; height: 100%; min-height: 96px; padding: 12px 14px 27px; resize: none; border: 1px solid #ded7d0; border-radius: 7px; outline: 0; color: #3f506a; background: rgba(255,255,255,.72); font-size: 12.5px; }.text-entry textarea:focus { border-color: rgba(196,77,62,.55); }.text-entry span { position: absolute; right: 10px; bottom: 8px; color: #71809a; font-size: 10px; }.file-drop { display: flex; min-height: 72px; align-items: center; justify-content: center; gap: 12px; border: 1px dashed #d9b7aa; border-radius: 7px; color: #344056; background: rgba(255,255,255,.48); cursor: pointer; }.file-drop .material-symbols-outlined { font-size: 27px; }.file-drop span:last-child { overflow: hidden; max-width: calc(100% - 70px); text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }.file-drop u { margin-left: 5px; color: #d04e38; }.primary-action { margin-top: 14px; border-radius: 5px; }
</style>
