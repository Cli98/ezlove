import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  submitCanteen, getCanteenRecords, correctCanteenRecord,
  generateMenu, getMenus, updateMenu, publishMenu, deleteMenu,
} from '@/api/canteen'

export const useCanteenStore = defineStore('canteen', () => {
  const records = ref([])
  const loading = ref(false)
  const submitting = ref(false)
  const error = ref(null)

  const menus = ref([])
  const menuLoading = ref(false)
  const generating = ref(false)

  async function load() {
    loading.value = true
    error.value = null
    try {
      records.value = await getCanteenRecords()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function submit(formData) {
    submitting.value = true
    error.value = null
    try {
      const result = await submitCanteen(formData)
      await load()
      return result
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '提交失败'
      throw e
    } finally {
      submitting.value = false
    }
  }

  async function correct(id, data) {
    error.value = null
    try {
      await correctCanteenRecord(id, data)
      await load()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '更正失败'
      throw e
    }
  }

  async function loadMenus() {
    menuLoading.value = true
    try {
      menus.value = await getMenus()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载菜单失败'
    } finally {
      menuLoading.value = false
    }
  }

  async function generate(mealType = 'lunch', menuDate = null) {
    generating.value = true
    error.value = null
    try {
      const fd = new FormData()
      fd.append('meal_type', mealType)
      if (menuDate) fd.append('menu_date', menuDate)
      const result = await generateMenu(fd)
      await loadMenus()
      return result
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '生成失败'
      throw e
    } finally {
      generating.value = false
    }
  }

  async function updateDishes(id, dishes) {
    try {
      await updateMenu(id, { dishes })
      await loadMenus()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '更新失败'
      throw e
    }
  }

  async function publish(id) {
    try {
      await publishMenu(id)
      await loadMenus()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '发布失败'
      throw e
    }
  }

  async function remove(id) {
    try {
      await deleteMenu(id)
      await loadMenus()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '删除失败'
      throw e
    }
  }

  return {
    records, loading, submitting, error, load, submit, correct,
    menus, menuLoading, generating, loadMenus, generate, updateDishes, publish, remove,
  }
})
