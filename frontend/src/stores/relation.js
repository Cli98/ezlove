import { defineStore } from "pinia";
import { ref } from "vue";
import { getRelations, createInvite, bindByCode, deleteRelation } from "@/api/relation";

export const useRelationStore = defineStore("relation", () => {
  const relations = ref([]);
  const loading = ref(false);

  async function loadRelations() {
    loading.value = true;
    try {
      relations.value = await getRelations();
    } finally {
      loading.value = false;
    }
  }

  async function generateInvite() {
    return await createInvite();
  }

  async function bind(code) {
    const result = await bindByCode(code);
    await loadRelations();
    return result;
  }

  async function remove(id) {
    await deleteRelation(id);
    relations.value = relations.value.filter((r) => r.id !== id);
  }

  return { relations, loading, loadRelations, generateInvite, bind, remove };
});
