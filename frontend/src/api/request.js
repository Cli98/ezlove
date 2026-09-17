import { BASE_URL } from "./config";

function getToken() {
  return uni.getStorageSync("access_token");
}

function clearAuthState() {
  uni.removeStorageSync("access_token");
  uni.removeStorageSync("refresh_token");
  uni.removeStorageSync("user_profile");
}

export function request(options) {
  const { url, method = "GET", data, header = {}, noAuth = false } = options;
  if (!noAuth) {
    const token = getToken();
    if (token) {
      header["Authorization"] = `Bearer ${token}`;
    }
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: { "Content-Type": "application/json", ...header },
      success: (res) => {
        if (res.statusCode === 401) {
          clearAuthState();
          uni.reLaunch({ url: "/pages/login/index" });
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
