import { getFullUrl } from "@/api/config";

export const DEFAULT_AVATAR = "https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/avatars/default-avatar.png";

export function getPresetAvatars(role) {
  const prefix = role === "elder" ? "elder" : "family";
  return ["female", "male"].flatMap((gender) =>
    [1, 2, 3].map((index) => `/static/avatars/${prefix}-${gender}-${index}.png`)
  );
}

export const getFamilyAvatar = (person = {}) =>
  getFullUrl(person?.sender_avatar_url || person?.family_avatar_url || person?.avatar_url) || DEFAULT_AVATAR;

export const getElderAvatar = (person = {}) =>
  getFullUrl(person?.elder_avatar_url || person?.avatar_url) || DEFAULT_AVATAR;
