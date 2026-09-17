import { createSSRApp } from "vue";
import { createPinia } from "pinia";
import uviewPlus from "uview-plus";
import App from "./App.vue";

export function createApp() {
  const app = createSSRApp(App);
  app.use(createPinia());
  app.use(uviewPlus);
  return { app };
}
