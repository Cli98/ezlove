import { BASE_URL } from "./config";

let refreshPromise = null;

function getToken() {
  return uni.getStorageSync("access_token");
}

function clearAuthState() {
  uni.removeStorageSync("access_token");
  uni.removeStorageSync("refresh_token");
  uni.removeStorageSync("user_profile");
}

function authError(message) {
  const error = new Error(message);
  error.authInvalid = true;
  return error;
}

export function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;

  const refreshToken = uni.getStorageSync("refresh_token");
  if (!refreshToken) {
    expireSession();
    return Promise.reject(authError("登录已过期"));
  }

  refreshPromise = new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}/auth/refresh`,
      method: "POST",
      data: { refresh_token: refreshToken },
      header: { "Content-Type": "application/json" },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data?.access_token) {
          uni.setStorageSync("access_token", res.data.access_token);
          if (res.data.refresh_token) {
            uni.setStorageSync("refresh_token", res.data.refresh_token);
          }
          resolve(res.data.access_token);
          return;
        }
        if (res.statusCode === 400 || res.statusCode === 401 || res.statusCode === 403) {
          reject(authError("登录已过期"));
          return;
        }
        reject(new Error("登录续期失败"));
      },
      fail: (err) => reject(new Error(err?.errMsg || "登录续期失败")),
    });
  })
    .catch((error) => {
      if (error.authInvalid) expireSession();
      throw error;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

function expireSession() {
  clearAuthState();
  uni.reLaunch({ url: "/pages/login/index" });
}

export function request(options, retried = false) {
  const { url, method = "GET", data, header = {}, noAuth = false } = options;
  const requestHeader = { ...header };
  if (!noAuth) {
    const token = getToken();
    if (token) {
      requestHeader["Authorization"] = `Bearer ${token}`;
    }
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: { "Content-Type": "application/json", ...requestHeader },
      success: async (res) => {
        if (res.statusCode === 401) {
          if (!noAuth && !retried) {
            try {
              await refreshAccessToken();
              resolve(request(options, true));
            } catch (error) {
              reject(error);
            }
            return;
          }
          if (!noAuth) expireSession();
          reject(new Error("Unauthorized"));
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          const detail = res.data?.detail;
          let msg = `[${res.statusCode}] `;
          if (typeof detail === "string") {
            msg += detail;
          } else if (Array.isArray(detail)) {
            msg += detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
          } else {
            msg += "请求失败";
          }
          reject(new Error(msg));
        }
      },
      fail: (err) => {
        reject(new Error(err?.errMsg || "网络请求失败"));
      },
    });
  });
}

export const api = {
  get: (url, data) => request({ url, method: "GET", data }),
  post: (url, data) => request({ url, method: "POST", data }),
  put: (url, data) => request({ url, method: "PUT", data }),
  delete: (url) => request({ url, method: "DELETE" }),
};
