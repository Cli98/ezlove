<template>
  <main class="flex min-h-screen w-full overflow-hidden">
    <!-- Left Side: Brand Section (44%) -->
    <section class="relative hidden md:flex flex-col justify-center items-center w-[44%] bg-login-gradient p-12 overflow-hidden">
      <!-- Decorative Elements -->
      <div class="decorative-circle w-[600px] h-[600px] -top-20 -left-20"></div>
      <div class="decorative-circle w-[400px] h-[400px] -bottom-40 -right-10"></div>
      <div class="decorative-circle w-[300px] h-[300px] top-1/2 left-1/4"></div>
      <div class="relative z-10 flex flex-col items-center text-center max-w-md">
        <div class="mb-8 p-1 bg-white/10 rounded-2xl">
          <div class="w-24 h-24 rounded-2xl glass-effect flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-5xl">home_health</span>
          </div>
        </div>
        <h1 class="font-headline text-5xl font-bold text-white mb-4 tracking-tight">易挂念</h1>
        <p class="text-white/60 text-lg font-medium mb-10 tracking-widest uppercase">社区关爱管理平台</p>
        <div class="space-y-4 pt-10 border-t border-white/10 w-full">
          <p class="text-white/80 text-lg font-light leading-relaxed">
            "让关心自然流动，让牵挂被看见"
          </p>
          <p class="text-white/60 text-sm font-light leading-relaxed">
            连接家庭与社区，守护每一位长者
          </p>
        </div>
      </div>
      <!-- Footer indicator -->
      <div class="absolute bottom-8 left-12">
        <span class="text-white/20 text-xs tracking-tighter uppercase font-label">Designed for Human Connection</span>
      </div>
    </section>

    <!-- Right Side: Login Form Section (56%) -->
    <section class="flex flex-col justify-center items-center w-full md:w-[56%] bg-surface px-6 sm:px-12 lg:px-24">
      <div class="w-full max-w-md">
        <!-- Mobile Branding -->
        <div class="md:hidden flex flex-col items-center mb-12">
          <div class="w-16 h-16 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-primary text-3xl">home_health</span>
          </div>
          <h1 class="font-headline text-3xl font-bold text-charcoal">易挂念</h1>
        </div>

        <header class="mb-10 text-center md:text-left">
          <h2 class="font-display text-4xl font-bold text-charcoal mb-2">欢迎回来</h2>
          <p class="text-on-surface-variant font-light">请登录您的社区管理账号</p>
        </header>

        <form class="space-y-6" @submit.prevent="handleLogin">
          <!-- Phone Input -->
          <div class="space-y-1.5">
            <label class="text-sm font-semibold text-charcoal ml-1" for="phone">手机号码</label>
            <div class="relative group">
              <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors">phone</span>
              <input
                v-model="form.phone"
                class="w-full pl-12 pr-4 py-4 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all duration-200 shadow-sm"
                id="phone"
                name="phone"
                placeholder="请输入手机号"
                type="tel"
                autofocus
              />
            </div>
            <p v-if="errors.phone" class="text-xs text-primary ml-1 mt-1">{{ errors.phone }}</p>
          </div>

          <!-- Password Input -->
          <div class="space-y-1.5">
            <label class="text-sm font-semibold text-charcoal ml-1" for="password">登录密码</label>
            <div class="relative group">
              <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors">lock</span>
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="w-full pl-12 pr-12 py-4 bg-white border border-outline-variant rounded-xl text-charcoal placeholder:text-outline-variant/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all duration-200 shadow-sm"
                id="password"
                name="password"
                placeholder="请输入密码"
              />
              <button
                class="absolute right-4 top-1/2 -translate-y-1/2 text-outline-variant hover:text-charcoal transition-colors"
                type="button"
                @click="showPassword = !showPassword"
              >
                <span class="material-symbols-outlined">{{ showPassword ? 'visibility_off' : 'visibility' }}</span>
              </button>
            </div>
            <p v-if="errors.password" class="text-xs text-primary ml-1 mt-1">{{ errors.password }}</p>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-between pt-2">
            <label class="flex items-center space-x-2 cursor-pointer group">
              <input class="w-4 h-4 rounded border-outline-variant text-primary focus:ring-primary/20" type="checkbox" />
              <span class="text-sm text-on-surface-variant group-hover:text-charcoal transition-colors">记住账号</span>
            </label>
            <a class="text-sm text-primary hover:underline font-medium transition-all cursor-not-allowed opacity-50" title="暂未开放">短信验证码登录</a>
          </div>

          <!-- Submit Button -->
          <button
            :disabled="loading"
            :class="{ 'opacity-80 cursor-not-allowed': loading }"
            class="w-full py-4 bg-primary text-white font-semibold rounded-full shadow-lg shadow-primary/20 hover:bg-terracotta hover:shadow-xl hover:-translate-y-0.5 active:scale-95 transition-all duration-200"
            type="submit"
          >
            {{ loading ? '登录中...' : '立即登录' }}
          </button>
        </form>

        <footer class="mt-12 text-center">
          <p class="text-xs text-outline font-light">
            忘记密码？<a class="text-on-surface-variant hover:text-charcoal hover:underline font-medium transition-colors" href="#">联系系统管理员</a>
          </p>
          <div class="mt-12 flex justify-center space-x-6">
            <span class="text-[10px] text-outline-variant uppercase tracking-widest">&copy; 2026 EZLove Technology</span>
          </div>
        </footer>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)
const showPassword = ref(false)
const form = reactive({ phone: '', password: '' })
const errors = reactive({ phone: '', password: '' })

function validate() {
  let valid = true
  errors.phone = ''
  errors.password = ''

  if (!form.phone) {
    errors.phone = '请输入手机号'
    valid = false
  } else if (!/^1\d{10}$/.test(form.phone)) {
    errors.phone = '请输入正确的11位手机号'
    valid = false
  }

  if (!form.password) {
    errors.password = '请输入密码'
    valid = false
  } else if (form.password.length < 6) {
    errors.password = '密码至少6个字符'
    valid = false
  }

  return valid
}

async function handleLogin() {
  if (!validate()) return
  loading.value = true
  try {
    await userStore.login(form.phone, form.password)
  } catch (e) {
    // error handled in request interceptor
  } finally {
    loading.value = false
  }
}
</script>
