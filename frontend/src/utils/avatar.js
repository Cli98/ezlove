import { getFullUrl } from "@/api/config";

const AVATAR_BASE_URL = "https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788/avatars";

export const DEFAULT_AVATAR = `${AVATAR_BASE_URL}/default-avatar.png`;

export function getPresetAvatars(role) {
  const prefix = role === "elder" ? "elder" : "family";
  return ["female", "male"].flatMap((gender) =>
    [1, 2, 3].map((index) => `${AVATAR_BASE_URL}/${prefix}-${gender}-${index}.png`)
  );
}

export const getFamilyAvatar = (person = {}) =>
  getFullUrl(person?.sender_avatar_url || person?.family_avatar_url || person?.avatar_url) || DEFAULT_AVATAR;

export const getElderAvatar = (person = {}) =>
  getFullUrl(person?.elder_avatar_url || person?.avatar_url) || DEFAULT_AVATAR;
