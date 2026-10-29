import { api } from "./request";

export function getMe() {
  return api.get("/users/me");
}

// 当前微信是否已绑定社区档案（「社区档案」页据此区分绑定/补授权）
export function getMyCommunityRecord() {
  return api.get("/users/community-record");
}

export function updateMe(data) {
  return api.put("/users/me", data);
}

export function selfCheckIn() {
  return api.post("/users/check-in");
}

export function getTodayCheckIn() {
  return api.get("/users/check-in/today");
}

export function bindElderRecord(phone) {
  return api.post("/users/bind-elder-record", { phone });
}

// 微信手机号快速验证组件返回的 code，由后端换取手机号后自动匹配档案
export function bindElderRecordByPhoneCode(code) {
  return api.post("/users/bind-elder-record/wx-phone", { code });
}
