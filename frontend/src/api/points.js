import { api } from "./request";

/** 查询积分余额 */
export function getPointBalance() {
  return api.get("/points/balance");
}

/** 查询积分流水 */
export function getPointHistory() {
  return api.get("/points/history");
}
